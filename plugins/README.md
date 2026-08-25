# DSH 插件备份

本目录备份 DSH web profile 的插件配置。

## 文件

- `package.json` — 插件列表（从 `~/.dsh/profiles/web/package.json` 复制）
- `restore-plugins.ps1` — 一键恢复脚本

## 恢复方法

```powershell
pwsh plugins/restore-plugins.ps1
```

恢复后重启 `dsh web` 即可。

## 更新备份

每次增删插件后，运行：

```powershell
Copy-Item "$HOME\.dsh\profiles\web\package.json" "$HOME\.dsh\skills\plugins\package.json" -Force
cd "$HOME\.dsh\skills"; git add -A; git commit -m "chore(plugins): update backup"; git push
```

或让 agent 执行"更新插件备份"。
