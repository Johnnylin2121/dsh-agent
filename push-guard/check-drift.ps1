# check-drift.ps1 — 校验本机 push 防护 与 仓库内备份 是否一致
# 用法：
#   pwsh push-guard/check-drift.ps1            # 只检查，漂移时退出码 1
#   pwsh push-guard/check-drift.ps1 -Fix       # 以仓库版本覆盖本机（旧文件先备份）
#
# 背景：push 防护有"两份真相"——本机钩子目录（实际生效）与仓库 push-guard/（跨机恢复用）。
# 两者若漂移，换机恢复出来的防护就和你现在跑的规则不一样，故纳入日常维护。
# 退出码：0 = 一致（或已 -Fix 修好）；1 = 存在漂移；2 = 环境异常

param([switch]$Fix)

$ErrorActionPreference = 'Continue'
$live  = Join-Path $HOME '.dsh\git-hooks'
$guard = $PSScriptRoot                      # 本脚本就在 push-guard/ 内
$files = @('pre-push', 'push-scan.ps1')

Write-Host '=== push 防护一致性检查 ===' -ForegroundColor Cyan
Write-Host ("本机: " + $live)
Write-Host ("仓内: " + $guard)
Write-Host ''

$drift = 0
foreach ($f in $files) {
    $a = Join-Path $guard $f
    $b = Join-Path $live  $f

    if (-not (Test-Path $a)) { Write-Host ("MISSING  仓内缺 $f") -ForegroundColor Yellow; $drift = 1; continue }
    if (-not (Test-Path $b)) {
        Write-Host ("MISSING  本机缺 $f") -ForegroundColor Yellow
        $drift = 1
        if ($Fix) {
            New-Item -ItemType Directory -Force -Path $live | Out-Null
            Copy-Item $a $b -Force
            Write-Host ("  FIX    已从仓库铺到本机")
        }
        continue
    }

    $ha = (Get-FileHash $a).Hash
    $hb = (Get-FileHash $b).Hash
    if ($ha -eq $hb) {
        Write-Host ("OK       {0}  {1}" -f $f, $ha.Substring(0, 12))
    } else {
        $drift = 1
        Write-Host ("DRIFT    {0}  仓内={1}  本机={2}" -f $f, $ha.Substring(0, 12), $hb.Substring(0, 12)) -ForegroundColor Yellow
        if ($Fix) {
            Copy-Item $b "$b.bak-$(Get-Date -Format yyyyMMdd-HHmmss)" -Force
            Copy-Item $a $b -Force
            Write-Host ("  FIX    已用仓库版本覆盖本机（旧文件已备份为 *.bak-*）")
        }
    }
}

Write-Host ''
if ($drift -eq 0) { Write-Host '结果：一致 ✅' -ForegroundColor Green; exit 0 }
if ($Fix)         { Write-Host '结果：已修复，请重跑一次复核' -ForegroundColor Cyan; exit 0 }
Write-Host '结果：存在漂移。处理方式：' -ForegroundColor Red
Write-Host '  · 本机版本才是你想要的 → 把本机文件复制进 push-guard/ 并提交；'
Write-Host '  · 仓库版本才是你想要的 → 加 -Fix 用仓库版本覆盖本机。'
exit 1
