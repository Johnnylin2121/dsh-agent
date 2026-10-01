# reapply-all.ps1 — 一键重铺所有本地插件补丁
# 何时跑：`dsh plugin add/remove/update` 之后、任何插件升级之后、换机恢复之后、或发现 xueqiu/RSS/视觉 行为异常时。
# 背景：pnpm 会重装 node_modules 内的包文件，导致就地补丁被洗掉（2026-09-16 实测：deepeye 补丁被洗 → 视觉 400 MissingSessionID）。
# 注意：补丁改的是宿主启动时加载的模块文件，铺完必须重启 dsh web 才生效。

param([string]$Profile = 'web')   # 目标 profile：web（默认）或 desktop

$ErrorActionPreference = 'Continue'
$patches = $PSScriptRoot
$nm = Join-Path $HOME ".dsh/profiles/$Profile/node_modules"
$env:DSH_PATCH_PROFILE = $Profile   # 传给内层 patch-*.mjs
$lines = New-Object System.Collections.Generic.List[string]

# 版本护栏（2026-10-01）：.patched 是**特定插件版本**的派生物；盲覆盖会让另一端版本错配
# （_shared/PORTABILITY.md：另一端必须能直接用或简单适配后用）。只告警，绝不覆盖。
function Test-PatchedVersion([string]$Name) {
    $vf = Join-Path $patches "$Name/PATCHED-VERSION"
    if (-not (Test-Path $vf)) { return $true }        # 无记录 -> 放行（向后兼容）
    $want = (Get-Content $vf -Raw).Trim()
    $pj = Join-Path $nm "$Name/package.json"
    if (-not (Test-Path $pj)) { return $false }
    $have = (Get-Content $pj -Raw | ConvertFrom-Json).version
    if ($have -ne $want) {
        Write-Host "  [!] $Name 版本不符：.patched 派生自 $want，本机 $have -> 跳过（不覆盖）" -ForegroundColor Yellow
        Write-Host "      要为你的版本重新生成，改完后更新 $Name/PATCHED-VERSION。" -ForegroundColor DarkGray
        return $false
    }
    return $true
}

Write-Host '=== 本地补丁重铺 ===' -ForegroundColor Cyan

# ---- 1) deepeye：视觉请求会话头补丁（无哨兵脚本，直接覆盖比对 hash）----
$src = Join-Path $patches 'dsh-plugin-deepeye/index.mjs.patched'
$dst = Join-Path $nm 'dsh-plugin-deepeye/lib/index.mjs'
if ((Test-Path $src) -and (Test-Path $dst) -and (Test-PatchedVersion 'dsh-plugin-deepeye')) {
    if ((Get-FileHash $src).Hash -eq (Get-FileHash $dst).Hash) {
        $lines.Add('OK    deepeye       已是补丁版')
    } else {
        Copy-Item $src $dst -Force
        $ok = (Get-FileHash $src).Hash -eq (Get-FileHash $dst).Hash
        $lines.Add($(if ($ok) { 'FIX   deepeye       已重铺' } else { 'FAIL  deepeye       覆盖后校验不一致' }))
    }
} else {
    $lines.Add('SKIP  deepeye       源/目标缺失 或 版本不符（见上方告警）')
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

# ---- 4) peak-cost-mode：隐藏底部状态条（幂等脚本）----
$d = Join-Path $patches 'dsh-peak-cost-mode'
if (Test-Path (Join-Path $d 'patch-peak-cost-dock.mjs')) {
    Push-Location $d
    $out = node patch-peak-cost-dock.mjs 2>&1
    $code = $LASTEXITCODE
    Pop-Location
    $tail = ($out | Where-Object { $_ -match 'PATCHED|VANILLA|SKIP|FAIL' } | Select-Object -Last 3) -join ' / '
    $lines.Add(("{0} peak-cost     {1}" -f $(if ($code -eq 0) { 'OK   ' } else { 'FAIL ' }), $tail))
} else { $lines.Add('SKIP  peak-cost    无 patch-peak-cost-dock.mjs') }

# ---- 5) context-doctor：link: 指向工作区补丁版，不需要铺，只校验可达 ----
$cd = Join-Path $nm 'dsh-context-doctor'
$lines.Add(("{0} context-doctor link 可达={1}" -f $(if (Test-Path (Join-Path $cd 'lib/index.js')) { 'OK   ' } else { 'FAIL ' }), (Test-Path (Join-Path $cd 'lib/index.js'))))
# ---- 7) dsh-context-doctor：适配 0.2 移除的 settings.get()（同类破坏性变更，直接覆盖比对 hash）----
# 原代码 `ctx.get("settings")?.get(ns)` 只挡服务为 null，挡不住"服务在但无此方法" →
# TypeError: ctx.get(...)?.get is not a function（context_audit 工具直接不可用）。
$src = Join-Path $patches 'dsh-context-doctor/index.js.patched'
$dst = Join-Path $nm 'dsh-context-doctor/lib/index.js'
if ((Test-Path $src) -and (Test-Path $dst) -and (Test-PatchedVersion 'dsh-context-doctor')) {
    if ((Get-FileHash $src).Hash -eq (Get-FileHash $dst).Hash) {
        $lines.Add('OK    context-doctor 已是适配版')
    } else {
        Copy-Item $src $dst -Force
        $ok = (Get-FileHash $src).Hash -eq (Get-FileHash $dst).Hash
        $lines.Add($(if ($ok) { 'FIX   context-doctor 已重铺' } else { 'FAIL  context-doctor 覆盖后校验不一致' }))
    }
} else {
    $lines.Add('SKIP  context-doctor 源/目标缺失 或 版本不符（见上方告警）')
}
# ---- 6) dsh-timer-agent：适配 0.1.7+ 移除的 host.settings.installSection（直接覆盖比对 hash）----
# 背景见 ~/.dsh/MEMORY.md「0.1.5 → 0.1.7 升级实录」：0.1.7 重写 settings 服务，
# installSection/settingsScope 被彻底移除，第三方插件用旧 API 会 TypeError。
# 上游 main 截至 a2dd60e 未适配，故本地适配。插件 update 后必重打。
$src = Join-Path $patches 'dsh-timer-agent/index.js.patched'
$dst = Join-Path $nm 'dsh-timer-agent/lib/index.js'
if ((Test-Path $src) -and (Test-Path $dst) -and (Test-PatchedVersion 'dsh-timer-agent')) {
    if ((Get-FileHash $src).Hash -eq (Get-FileHash $dst).Hash) {
        $lines.Add('OK    timer-agent  已是适配版')
    } else {
        Copy-Item $src $dst -Force
        $ok = (Get-FileHash $src).Hash -eq (Get-FileHash $dst).Hash
        $lines.Add($(if ($ok) { 'FIX   timer-agent  已重铺' } else { 'FAIL  timer-agent  覆盖后校验不一致' }))
    }
} else {
    $lines.Add('SKIP  timer-agent  源/目标缺失 或 版本不符（见上方告警）')
}

Write-Host ''
$lines | ForEach-Object { Write-Host $_ }
Write-Host ''
Write-Host "铺完请重启对应端（$Profile 的宿主模块在启动时加载，改文件不热生效）。" -ForegroundColor Yellow
Write-Host 'xueqiu 若提示版本不符而拒绝：确认版本差异后加 --force 重跑本目录 patch-xueqiu.mjs。' -ForegroundColor DarkGray
