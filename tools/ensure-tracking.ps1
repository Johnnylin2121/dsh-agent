#!/usr/bin/env pwsh
# ensure-tracking.ps1 — 巡检/修复 git 仓的 upstream 跟踪配置
#
# 背景（2026-09-24 起因）：dsh-agent 的 main 一度丢失 `branch.main.remote` /
#   `branch.main.merge`，`git status` 只显示 `## main`（看不到 ahead/behind），
#   推送前才发现与远端已分叉。实测 **`git rebase` 不会**导致该丢失（已复现验证），
#   真因是某次 `git remote remove/add`、`git branch --unset-upstream` 之类的命令
#   —— 本仓多会话（DSH / MiMo Desktop / OpenCode）并发写入时容易发生。
#   症状隐蔽、无报错，所以需要一个可随手跑的巡检脚本。
#
# 用法：
#   pwsh -NoProfile -File tools/ensure-tracking.ps1          # 只检查（发现漂移 exit 1）
#   pwsh -NoProfile -File tools/ensure-tracking.ps1 -Fix     # 自动修复后再复核
#   pwsh -NoProfile -File tools/ensure-tracking.ps1 -Path D:\some\repo   # 追加检查任意仓
#
# 退出码：0 = 全部正常（或已修复）；1 = 发现漂移且未 -Fix；2 = 参数/环境错误

[CmdletBinding()]
param(
  [switch]$Fix,
  [string[]]$Path
)

$ErrorActionPreference = 'Stop'

# 默认巡检本机受管副本（不存在则跳过，不视为错误）
$default = @(
  (Join-Path $HOME '.dsh/skills'),            # dsh-agent
  (Join-Path $HOME '.dsh/.agent-presets')     # dsh-agent-presets
)
$targets = @($default) + @($Path)

$results = @()

foreach ($repo in $targets) {
  if (-not $repo) { continue }
  $repo = [Environment]::ExpandEnvironmentVariables($repo)
  if (-not (Test-Path (Join-Path $repo '.git'))) { continue }

  Push-Location $repo
  try {
    $name = Split-Path (git rev-parse --show-toplevel) -Leaf
    $branch = git branch --show-current
    $remotes = @(git remote)
    $status = (git status --short --branch | Select-Object -First 1)

    if (-not $branch) {
      $results += [pscustomobject]@{ Repo = $name; State = 'DETACHED'; Detail = 'HEAD 游离（detached），无分支可跟踪' }
      continue
    }
    if ($remotes.Count -eq 0) {
      $results += [pscustomobject]@{ Repo = $name; State = 'NO-REMOTE'; Detail = '无 remote，无法跟踪' }
      continue
    }

    # 期望：branch.<b>.remote 存在且其上存在 <remote>/<branch>
    $curRemote = git config --get "branch.$branch.remote"
    $curMerge  = git config --get "branch.$branch.merge"
    $remote = if ($remotes -contains 'origin') { 'origin' } else { $remotes[0] }

    # 该 remote 上是否真有同名分支
    git ls-remote --exit-code --heads $remote "refs/heads/$branch" 2>$null | Out-Null
    $hasRemoteBranch = ($LASTEXITCODE -eq 0)

    if (-not $hasRemoteBranch) {
      $results += [pscustomobject]@{ Repo = $name; State = 'NO-REMOTE-BRANCH'; Detail = "$remote/$branch 在远端不存在，不做跟踪" }
      continue
    }

    $expectedMerge = "refs/heads/$branch"
    if ($curRemote -eq $remote -and $curMerge -eq $expectedMerge) {
      $div = (git rev-list --left-right --count "$branch...$remote/$branch" 2>$null)
      $results += [pscustomobject]@{ Repo = $name; State = 'OK'; Detail = "$branch → $remote/$branch（ahead/behind: $div）" }
      continue
    }

    # 漂移：缺 tracking 或指向错误
    $before = if ($curRemote) { "$curRemote/$($curMerge -replace 'refs/heads/', '')" } else { '(无)' }
    if ($Fix) {
      git branch --set-upstream-to="$remote/$branch" $branch | Out-Null
      $after = git config --get "branch.$branch.remote"
      $ok = ($after -eq $remote)
      $results += [pscustomobject]@{
        Repo = $name; State = $(if ($ok) { 'FIXED' } else { 'FIX-FAILED' })
        Detail = "$branch：$before → $remote/$branch"
      }
    } else {
      $results += [pscustomobject]@{
        Repo = $name; State = 'DRIFT'; Detail = "$branch：当前 $before，期望 $remote/$branch（-Fix 可自动修复）"
      }
    }
  } finally {
    Pop-Location
  }
}

if ($results.Count -eq 0) {
  Write-Host '[ensure-tracking] 未找到受管 git 仓（跳过）'
  exit 0
}

Write-Host ''
Write-Host '=== upstream 跟踪巡检 ==='
$results | Format-Table -AutoSize | Out-String | Write-Host

$bad = @($results | Where-Object { $_.State -in @('DRIFT', 'FIX-FAILED', 'DETACHED', 'NO-REMOTE') })
$warn = @($results | Where-Object { $_.State -eq 'NO-REMOTE-BRANCH' })

if ($bad.Count -gt 0) {
  Write-Host "结果：存在漂移/异常 $($bad.Count) 项 —— 修复命令：pwsh -NoProfile -File tools/ensure-tracking.ps1 -Fix" -ForegroundColor Red
  exit 1
}
if ($warn.Count -gt 0) {
  Write-Host "结果：主体正常，$($warn.Count) 项为远端无同名分支（按新分支处理）"
  exit 0
}
Write-Host '结果：全部正常 ✅'
exit 0
