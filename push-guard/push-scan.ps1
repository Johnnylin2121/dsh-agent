# push-scan.ps1 — git pre-push 隐私泄露扫描引擎
# 用途: 在 push 前扫描待推送内容，拦截 API key/token/持仓记录/本机路径/PII
# 调用方式:
#   由 pre-push hook:  push-scan.ps1 -LocalSha <sha> -RemoteSha <sha>
#   手动全历史:        push-scan.ps1 -Full
#   暂存区扫描:        push-scan.ps1 -Staged
#   指定范围:          push-scan.ps1 -Range "abc123..def456"
# 退出码: 0=干净, 1=发现泄露(阻止), 2=内部错误(不阻止,报告)
[CmdletBinding()]
param(
  [string]$LocalSha,
  [string]$RemoteSha,
  [string]$Range,
  [switch]$Full,
  [switch]$Staged
)

$ErrorActionPreference = 'Stop'
$repoRoot = (git rev-parse --show-toplevel 2>$null)
if (-not $repoRoot) { Write-Error 'not a git repo'; exit 2 }

# ── 逃生舱: git config pushscan.skip true 跳过本仓库 ──
$skip = git config --bool --get pushscan.skip 2>$null
if ($skip -eq 'true') { exit 0 }

# ── 确定扫描范围 ──
$rangeDesc = ''
if ($Staged) {
  $rangeDesc = 'staged changes'
  $patch = git diff --cached
} elseif ($Full) {
  $rangeDesc = 'FULL history'
  $patch = git log -p --all
} elseif ($Range) {
  $rangeDesc = "range $Range"
  $patch = git log -p $Range
} elseif ($LocalSha -and $RemoteSha) {
  $zero = '0' * 40
  if ($LocalSha -eq $zero) { exit 0 }  # 删除远程分支, 无内容推送
  if ($RemoteSha -eq $zero) {
    # 新分支: 仓库小直接全历史; 大仓库退化为最近30提交
    $count = [int](git rev-list --count HEAD 2>$null)
    if ($count -le 60) { $rangeDesc = "new branch, FULL history ($count commits)"; $patch = git log -p HEAD }
    else { $rangeDesc = "new branch, last 30 commits"; $patch = git log -p -30 HEAD }
  } else {
    git cat-file -e "$RemoteSha" 2>$null; if ($LASTEXITCODE -ne 0) { $RemoteSha = '' }
    if ($RemoteSha) { $rangeDesc = "range $RemoteSha..$LocalSha"; $patch = git log -p "$RemoteSha..$LocalSha" }
    else { $rangeDesc = "FULL history (remote sha unknown)"; $patch = git log -p --all }
  }
} else {
  Write-Host '[push-scan] no scan target'; exit 0
}

$patchFile = Join-Path $env:TEMP ("pushscan-" + [guid]::NewGuid().ToString('N') + ".patch")
$patch | Set-Content -Path $patchFile -Encoding UTF8
$findings = New-Object System.Collections.Generic.List[string]

try {
  # ── 引擎1: gitleaks (若安装; winget 安装后新进程 PATH 可能未刷新, 做路径回退) ──
  $gitleaks = Get-Command gitleaks -ErrorAction SilentlyContinue
  if (-not $gitleaks) {
    $cand = @(
      "$env:LOCALAPPDATA\Microsoft\WinGet\Links\gitleaks.exe",
      "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gitleaks.Gitleaks_Microsoft.Winget.Source_8wekyb3d8bbwe\gitleaks.exe",
      'C:\Program Files\Gitleaks\gitleaks.exe'
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($cand) { $gitleaks = $cand }
  }
  if ($gitleaks) {
    $glOut = & $gitleaks dir $patchFile --no-banner --redact -f json 2>$null
    if ($LASTEXITCODE -ne 0 -and $glOut) {
      try {
        $json = ($glOut -join "`n") | ConvertFrom-Json
        foreach ($f in $json) {
          $findings.Add("GITLEAKS  rule=$($f.RuleID)  file=$($f.File):$($f.StartLine)  secret=[REDACTED]")
        }
      } catch { $findings.Add("GITLEAKS  检测到泄露(输出解析失败), 请手动运行: gitleaks dir $patchFile") }
    }
  }

  # ── 引擎2: 自定义正则 (中文隐私场景) ──
  # 注意: rg(Rust regex) 不支持 lookahead/lookbehind, 排除逻辑放后置过滤
  $patterns = @(
    @{ id='PRICE-ACTION';  re='(\d+\.\d{1,3})\s*(入场|止损|止盈|买入|卖出)|(入场价|止损价|成本价|买入价|卖出价)\s*[:：=]?\s*\d' }
    @{ id='STOCK-HOLDING'; re='((?:SH|SZ|sh|sz|bj|BJ)\d{6})[^.\n]{0,40}(持仓|仓位|已止损|入场|清仓|买入成本)|((持仓|仓位)[^.\n]{0,30}(SH|SZ|sh|sz)\d{6})' }
    @{ id='LOCAL-PATH';    re='(?i)c:[\\/]+users[\\/]+[a-z0-9_.\- ]+[\\/]';  exclude='(?i)c:[\\/]+users[\\/]+(public|default)[\\/]' }
    @{ id='VAULT-PATH';    re='(?i)[a-z]:[\\/]+onedrive[\\/]+obsidian[a-z]*|(?i)onedrive[\\/]+obsidianvault' }
    @{ id='ASIN';          re='\bB0[A-Z0-9]{8}\b' }
    @{ id='CN-MOBILE';     re='(^|[^0-9])1[3-9]\d{9}([^0-9]|$)' }
    @{ id='CN-IDCARD';     re='\b\d{6}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b' }
    @{ id='CAPITAL';       re='(本金|账户余额)\s*[:：=]?\s*[\d,]{4,}' }
    @{ id='KEY-FALLBACK';  re='sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{36}|AKIA[0-9A-Z]{16}|ntn_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|xq_a_token=[A-Za-z0-9%_-]{20,}' }
  )
  foreach ($p in $patterns) {
    $hits = & rg -N --no-heading -e $p.re $patchFile 2>$null
    if ($LASTEXITCODE -eq 0 -and $hits) {
      if ($p.exclude) { $hits = @($hits | Where-Object { $h = $_; $h -notmatch $p.exclude }) }
      foreach ($h in $hits) { $findings.Add("REGEX     rule=$($p.id)  $h") }
    }
  }

  # ── 白名单过滤 (repo 根 .pushscan-allow + 全局 pushscan-allow-global, 每行一条正则) ──
  $allowRes = @()
  foreach ($af in @((Join-Path $repoRoot '.pushscan-allow'), (Join-Path $HOME '.dsh\git-hooks\pushscan-allow-global'))) {
    if (Test-Path $af) { $allowRes += (Get-Content $af | Where-Object { $_ -and $_ -notmatch '^\s*#' }) }
  }
  if ($allowRes) {
    $kept = @($findings | Where-Object { $f = $_; @($allowRes | Where-Object { $f -match $_ }).Count -eq 0 })
    $findings = New-Object System.Collections.Generic.List[string]
    foreach ($k in $kept) { $findings.Add($k) }
  }

  # ── 报告 ──
  if ($findings.Count -gt 0) {
    Write-Host ''
    Write-Host '===== PUSH 被拦截: 检测到疑似敏感信息 =====' -ForegroundColor Red
    Write-Host "扫描范围: $rangeDesc"
    Write-Host ''
    foreach ($f in $findings) { Write-Host "  $f" -ForegroundColor Yellow }
    Write-Host ''
    Write-Host '处置指引:'
    Write-Host '  1. 真泄露   → 删除/脱敏后重新 commit (已进历史的内容需 git filter-repo 重写)'
    Write-Host '  2. 误报     → 仓库根建 .pushscan-allow, 每行一条正则排除'
    Write-Host '  3. 确认无误 → git push --no-verify 跳过本次 (需人工确认)'
    exit 1
  }

  Write-Host "[push-scan] OK $rangeDesc (gitleaks: $(if($gitleaks){'on'}else{'off'}), 正则: $($patterns.Count) 条)"
  exit 0
} catch {
  Write-Host "[push-scan] 引擎错误(未拦截): $_" -ForegroundColor DarkYellow
  exit 2
} finally {
  Remove-Item $patchFile -ErrorAction SilentlyContinue
}
