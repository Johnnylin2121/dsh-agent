# restore-plugins.ps1 — 从备份恢复 DSH web profile 插件
# 用法: pwsh plugins/restore-plugins.ps1
#
# 行为（2026-09-15 修订）：
#   1) 按备份 package.json 的 dependencies 逐个安装（支持 github: / link: / file: / npm: 别名 spec）
#   2) **把 dsh.profile.bundles 同步成备份里的那份** —— 只装依赖不写 bundles 会「装了但不加载」，
#      这是历史上反复踩的根因；harness 的依赖→bundles 自动同步并不可靠。
#   3) 提示哪些东西本仓库不含、需要人工重建（profile cordis.patch.yml、密钥环境变量）。

$ErrorActionPreference = "Stop"
$profileDir = "$HOME/.dsh/profiles/web"
$profilePkg = Join-Path $profileDir "package.json"
$backupPkg = "$PSScriptRoot\package.json"

if (!(Test-Path $backupPkg)) {
    Write-Error "找不到备份文件: $backupPkg"
    exit 1
}

Write-Host "=== DSH 插件恢复 ===" -ForegroundColor Cyan
Write-Host "备份来源: $backupPkg"
Write-Host "目标目录: $profileDir"
Write-Host ""

$backup = Get-Content $backupPkg -Raw | ConvertFrom-Json
$plugins = $backup.dependencies.PSObject.Properties

Write-Host "待安装插件 ($($plugins.Count) 个):" -ForegroundColor Yellow
foreach ($p in $plugins) {
    Write-Host "  - $($p.Name) = $($p.Value)"
}
Write-Host ""

# 0) 备份目标 profile 的 package.json
if (Test-Path $profilePkg) {
    $bak = "$profilePkg.bak-restore-$(Get-Date -Format yyyyMMdd-HHmmss)"
    Copy-Item $profilePkg $bak -Force
    Write-Host "已备份目标 package.json -> $bak" -ForegroundColor DarkGray
}

# 1) 逐个安装
foreach ($p in $plugins) {
    $name = $p.Name
    $spec = $p.Value
    Write-Host "安装 $name ..." -ForegroundColor Green

    # github: / link: / file: / npm: 前缀用原始 spec，否则按 name@version
    if ($spec -match "^(github:|link:|file:|npm:)") {
        dsh plugin --profile web add $spec
    } else {
        dsh plugin --profile web add "$name@$spec"
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Warning "安装 $name 失败 (exit $LASTEXITCODE)，跳过"
    }
}

# 2) 同步 dsh.profile.bundles（关键步骤）
Write-Host ""
Write-Host "=== 同步 dsh.profile.bundles ===" -ForegroundColor Cyan
$sync = @'
const fs = require('fs');
const [backupPath, targetPath] = process.argv.slice(1);
const backup = JSON.parse(fs.readFileSync(backupPath, 'utf8'));
const target = JSON.parse(fs.readFileSync(targetPath, 'utf8'));
const want = backup?.dsh?.profile?.bundles ?? [];
if (!want.length) { console.error('备份里没有 dsh.profile.bundles，跳过'); process.exit(0); }
target.dsh = target.dsh ?? {};
target.dsh.profile = target.dsh.profile ?? {};
const before = target.dsh.profile.bundles ?? [];
target.dsh.profile.bundles = want;
fs.writeFileSync(targetPath, JSON.stringify(target, null, 2) + '\n', 'utf8');
console.log('bundles: ' + before.length + ' -> ' + want.length);
for (const b of want) console.log('  ' + b);
'@
$sync | node - $backupPkg $profilePkg

Write-Host ""
Write-Host "=== 重铺本地补丁 ===" -ForegroundColor Cyan
$reapply = Join-Path $PSScriptRoot 'dsh-patches/reapply-all.ps1'
if (Test-Path $reapply) { & $reapply } else { Write-Warning "未找到 $reapply，请手动重铺 dsh-patches 下的补丁" }

Write-Host ""
Write-Host "=== 恢复完成 ===" -ForegroundColor Cyan
Write-Host "仍需人工处理（本仓库不含）：" -ForegroundColor Yellow
Write-Host "  1. profile cordis.patch.yml —— rss-digest 落盘路径、DeepEye 视觉后端(baseUrl/model)、excel-kit 等配置"
Write-Host "  2. DeepEye 的密钥走环境变量：setx DEEPEYE_API_KEY `"<key>`"（重启 dsh web 后生效）"
Write-Host "  3. 重启 dsh web 使插件与补丁生效"
