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

## 注意：link: 本地补丁依赖

`dsh-context-doctor` 当前使用 `link:` 指向本机补丁目录
`E:\3.deepseek-harness\.dsh-patches\context-doctor-0.6.1`（本地 patched 版）。
在新机器上恢复时该目录不存在，脚本会跳过该插件；二选一：

1. 先把补丁目录拷到新机同路径，再跑恢复脚本；
2. 或临时改回 git 源：`dsh plugin --profile web add github:Zhenyu98/dsh-context-doctor#main`（注意会丢本地补丁改动）。

## 更新备份

每次增删插件后，运行：

```powershell
Copy-Item "$HOME\.dsh\profiles\web\package.json" "$HOME\.dsh\skills\plugins\package.json" -Force
cd "$HOME\.dsh\skills"; git add -A; git commit -m "chore(plugins): update backup"; git push
```

或让 agent 执行"更新插件备份"。
