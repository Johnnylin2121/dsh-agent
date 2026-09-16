# reapply-all.ps1 — 一键重铺所有本地插件补丁
# 何时跑：`dsh plugin add/remove/update` 之后、任何插件升级之后、换机恢复之后、或发现 xueqiu/RSS/视觉 行为异常时。
# 背景：pnpm 会重装 node_modules 内的包文件，导致就地补丁被洗掉（2026-09-16 实测：deepeye 补丁被洗 → 视觉 400 MissingSessionID）。
# 注意：补丁改的是宿主启动时加载的模块文件，铺完必须重启 dsh web 才生效。

$ErrorActionPreference = 'Continue'
$patches = $PSScriptRoot
$nm = Join-Path $HOME '.dsh/profiles/web/node_modules'
$lines = New-Object System.Collections.Generic.List[string]

Write-Host '=== 本地补丁重铺 ===' -ForegroundColor Cyan

# ---- 1) deepeye：视觉请求会话头补丁（无哨兵脚本，直接覆盖比对 hash）----
$src = Join-Path $patches 'dsh-plugin-deepeye/index.mjs.patched'
$dst = Join-Path $nm 'dsh-plugin-deepeye/lib/index.mjs'
if ((Test-Path $src) -and (Test-Path $dst)) {
    if ((Get-FileHash $src).Hash -eq (Get-FileHash $dst).Hash) {
        $lines.Add('OK    deepeye       已是补丁版')
    } else {
        Copy-Item $src $dst -Force
        $ok = (Get-FileHash $src).Hash -eq (Get-FileHash $dst).Hash
        $lines.Add($(if ($ok) { 'FIX   deepeye       已重铺' } else { 'FAIL  deepeye       覆盖后校验不一致' }))
    }
} else {
    $lines.Add('SKIP  deepeye       源或目标缺失（插件未安装？）')
}

# ---- 2) xueqiu：TLS 规避 + 浮窗隐藏（幂等脚本）----
$d = Join-Path $patches 'dsh-xueqiu'
if (Test-Path (Join-Path $d 'patch-xueqiu.mjs')) {
    Push-Location $d
    $out = node patch-xueqiu.mjs 2>&1
    $code = $LASTEXITCODE
    Pop-Location
    $tail = ($out | Where-Object { $_ -match 'PATCHED|SKIP|OK|version|拒绝|force' } | Select-Object -Last 6) -join ' / '
    $lines.Add(("{0} xueqiu        {1}" -f $(if ($code -eq 0) { 'OK   ' } else { 'FAIL ' }), $tail))
} else { $lines.Add('SKIP  xueqiu       无 patch-xueqiu.mjs') }

# ---- 3) rss-digest：宿主内 response.text() 读法（幂等脚本）----
$d = Join-Path $patches 'dsh-rss-digest'
if (Test-Path (Join-Path $d 'patch-rss-digest.mjs')) {
    Push-Location $d
    $out = node patch-rss-digest.mjs 2>&1
    $code = $LASTEXITCODE
    Pop-Location
    $tail = ($out | Where-Object { $_ -match 'PATCHED|SKIP|OK|version|拒绝|force' } | Select-Object -Last 6) -join ' / '
    $lines.Add(("{0} rss-digest    {1}" -f $(if ($code -eq 0) { 'OK   ' } else { 'FAIL ' }), $tail))
} else { $lines.Add('SKIP  rss-digest   无 patch-rss-digest.mjs') }

# ---- 4) context-doctor：link: 指向工作区补丁版，不需要铺，只校验可达 ----
$cd = Join-Path $nm 'dsh-context-doctor'
$lines.Add(("{0} context-doctor link 可达={1}" -f $(if (Test-Path (Join-Path $cd 'lib/index.js')) { 'OK   ' } else { 'FAIL ' }), (Test-Path (Join-Path $cd 'lib/index.js'))))

Write-Host ''
$lines | ForEach-Object { Write-Host $_ }
Write-Host ''
Write-Host '铺完请重启 dsh web（模块在启动时加载，改文件不热生效）。' -ForegroundColor Yellow
Write-Host 'xueqiu 若提示版本不符而拒绝：确认版本差异后加 --force 重跑本目录 patch-xueqiu.mjs。' -ForegroundColor DarkGray
