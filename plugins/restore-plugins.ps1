# restore-plugins.ps1 — 从备份恢复 DSH web profile 插件
# 用法: pwsh plugins/restore-plugins.ps1

$ErrorActionPreference = "Stop"
$profileDir = "$HOME\.dsh\profiles\web"
$backupPkg = "$PSScriptRoot\package.json"

if (!(Test-Path $backupPkg)) {
    Write-Error "找不到备份文件: $backupPkg"
    exit 1
}

Write-Host "=== DSH 插件恢复 ===" -ForegroundColor Cyan
Write-Host "备份来源: $backupPkg"
Write-Host "目标目录: $profileDir"
Write-Host ""

# 读取备份的 dependencies
$backup = Get-Content $backupPkg -Raw | ConvertFrom-Json
$plugins = $backup.dependencies.PSObject.Properties

Write-Host "待安装插件 ($($plugins.Count) 个):" -ForegroundColor Yellow
foreach ($p in $plugins) {
    Write-Host "  - $($p.Name)@$($p.Value)"
}
Write-Host ""

# 逐个安装
foreach ($p in $plugins) {
    $name = $p.Name
    $spec = $p.Value
    Write-Host "安装 $name ..." -ForegroundColor Green
    
    # github: 前缀的用原始 spec，否则用 npm 格式
    if ($spec -match "^github:") {
        dsh plugin --profile web add $spec
    } else {
        dsh plugin --profile web add "$name@$spec"
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "安装 $name 失败 (exit $LASTEXITCODE)，跳过"
    }
}

Write-Host ""
Write-Host "=== 恢复完成 ===" -ForegroundColor Cyan
Write-Host "请重启 dsh web 使插件生效"
