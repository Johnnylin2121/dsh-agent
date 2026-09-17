# DUAL-END — 双端工作制（Windows 主机 ⇄ macOS 笔记本）

> 本约定长期有效。两端各有一个 DSH agent 在同一套仓库上工作；本文说明**同步模型、各端接入、推送协议、冲突规则、差异豁免**。
> 写作规范（跨端内容要求）见 `_shared/PORTABILITY.md`；仓库/内容归属见 `REPO-MAP.md`。

---

## 1. 同步模型：三条通道，各管一段

| 通道 | 载体 | 同步范围 | 注意 |
|---|---|---|---|
| **A. 知识/业务产物** | Obsidian vault（OneDrive 同步） | 交易体系、亚马逊产物、wiki、模板 | 两端**路径不同** → 一律用 `{VAULT_PATH}`，取各机 `~/.dsh/MEMORY.md` |
| **B. 技能与配置** | git 仓库 `dsh-agent`（+ `dsh-agent-presets`） | skills、plugins 清单、补丁、push 防护、文档 | 这是**真源**；两端各自 clone 到 `~/.dsh/skills` |
| **C. 机器本地状态** | 各机 `~/.dsh`（**不同步**） | `MEMORY.md`、`settings.yaml`、`.credentials.yaml`、`profiles/`、插件运行时、`git-hooks/` | 换机需按文档重建；密钥用环境变量/凭据库 |

**推论**：不要指望 A 通道传代码、也不要指望 C 通道跨端（`MEMORY.md` 是各自一份）。

## 2. 各端需要具备什么

**Windows（当前主机，已完成）**
- `~/.dsh/skills` = dsh-agent 工作副本（SSH）
- 防护：`core.hooksPath = ~/.dsh/git-hooks`（pre-push → push-scan.ps1）
- `gh` 已登录、`gh auth setup-git` 已配（HTTPS 仓复用 token）
- 本地插件补丁：`reapply-all.ps1` 一键重铺（deepeye / xueqiu / rss-digest）

**macOS（接入清单）**
0. ⚠️ **先查旧 clone**：若 `~/.dsh/skills/.git` 已存在，先 `git fetch origin` 并比对 `HEAD` vs `origin/main`——不一致说明是 2026-09-15 历史重写前的旧克隆，**只许 `git reset --hard origin/main`（先备份），禁止 pull/push**
1. `git clone git@github.com:Johnnylin2121/dsh-agent.git ~/.dsh/skills`（GitHub 上先加该机 SSH key；或用 `gh auth login` 后 `gh auth setup-git` 走 HTTPS）
   - 另克隆 preset 真源：`git clone git@github.com:Johnnylin2121/dsh-agent-presets.git ~/.dsh/.agent-presets`
2. 装 DSH 本体 + `dsh web`；插件用 `pwsh ~/.dsh/skills/plugins/restore-plugins.ps1` 恢复（脚本会同步 bundles 并重铺补丁）
   - 需要 PowerShell：`brew install --cask powershell`；**`brew install ripgrep` 必装**（缺则扫描引擎降级/报错）；`gitleaks` 可选
3. 防护：**先落盘再指路**——`mkdir -p ~/.dsh/git-hooks && cp ~/.dsh/skills/push-guard/pre-push ~/.dsh/skills/push-guard/push-scan.ps1 ~/.dsh/git-hooks/ && chmod +x ~/.dsh/git-hooks/pre-push`，然后 `git config --global core.hooksPath "$HOME/.dsh/git-hooks"`，最后 `pwsh ~/.dsh/skills/push-guard/check-drift.ps1` 必须输出「一致 ✅」
   - ⚠️ `core.hooksPath` 指向空目录时 git **静默跳过** pre-push = 裸推
   - `pre-push` 是 `/bin/sh` 脚本且**已做跨端判断**：无 `pwsh` 时会放行并警告（fail-open）
   - 退出码语义：引擎 `0`=放行 / `1`=命中泄露并阻止 / `2+`=引擎错误（未完成扫描）→ hook **放行 + 告警**，需人工 `push-scan.ps1 -Full` 补扫
4. `git config core.autocrlf false`（仓库已 `.gitattributes: text=auto eol=lf`）；`git config core.precomposeunicode true`
5. 本机 `~/.dsh/MEMORY.md`：本机重建（vault 路径、shell、python 等按 macOS 填）；**Windows 端的 MEMORY.md/settings.yaml 不在同步范围，不要拷**
6. 密钥：`setx` 不可用 → 写 `~/.zshrc`，例如 `export DEEPEYE_API_KEY=...`（行首留空格避免进 history）

## 3. 推送协议（两端一致）

```
改 → git status → 只 add 需要的内容 → commit（type(scope): 摘要）
   → node tools/validate-repo.mjs            # 跨端合规（阻塞项必须清零）
   → pwsh ~/.dsh/git-hooks/push-scan.ps1 -Range origin/main..HEAD   # 隐私（钩子也会自动跑）
   → git pull --rebase origin main           # 先并远端，避免非快进
   → git push origin main
```

- **默认只操作 `dsh-agent`**（真源）；跨仓（`dsh-agent-presets` 等）单独确认后再动
- `gh` 的 API 写操作（PR/issue/workflow/release/repo 设置）**不经过 push-scan** → 一律先人工确认
- 不用 `--force`（历史重写类操作必须单独确认，且两端都要重新 clone/reset）

## 4. 并发与冲突规则（双端同时工作时）

1. **同一文件避免两端同时改**：改动前先 `git pull --rebase`；改完尽快推
2. **小步提交**：一个逻辑一件事，减少冲突面
3. 冲突时**以仓库当前 `main` + 业务事实**为准，不用 `--force` 覆盖对方
4. 机器本地状态（C 通道）冲突**无解也无所谓**：它是每端私有的，别纳入 git
5. 长任务（如批量复盘、批量分析）**在一端做完再同步**，别两端并行改同一批文件

## 5. 两端差异与豁免（务实版）

| 项 | Windows | macOS | 处理 |
|---|---|---|---|
| schannel TLS 损坏 → `curl.exe` 不可用 | 有 | 无 | 通用原则"**用宿主原生 fetch / node 脚本，不用 curl**"两端都遵守（已写进各 skill） |
| `dsh-xueqiu` TLS 补丁 | 必需 | 非必需（可打，无害） | 补丁脚本幂等；Mac 端可只打"浮窗隐藏"那部分 |
| `dsh-rss-digest` 用 `response.text()` 补丁 | 需要（DSH 宿主流读取不可靠） | 同样需要 | 与平台无关，两端都要铺 |
| `dsh-plugin-deepeye` 的 `x-opencode-session` 头 | 需要 | 需要 | 网关要求，与平台无关；用 `reapply-all.ps1` 铺 |
| `plugins/dsh-patches/context-doctor-0.6.1/tsconfig.json` 里的机器路径 | 本机构建用 | 无效 | **体检脚本已豁免该目录**；换机时按需重建 paths |
| Python 依赖 | Python312 全路径 | `python3` + pip3 | 见 `_shared/PORTABILITY.md` §3 |
| 插件运行时 | `node_modules`（pnpm） | 同 | 不入库，靠 `plugins/package.json` 重建 |

## 6. 每次动手前后（两端 checklist）

**动前**：`git pull --rebase` → `node tools/validate-repo.mjs`（基线）→ 确认 `{VAULT_PATH}` 从本机 MEMORY.md 取
**动后**：`node tools/validate-repo.mjs` 无阻塞项 → 隐私扫描 OK → 推送 → 更新 `REPO-MAP.md`（若有结构性变化）

## 7. 变更记录

- **2026-09-16** 首版：随 Windows 端仓库治理一起落地（`.gitattributes` LF、`tools/validate-repo.mjs` + CI、`LICENSE`、跨端文档、技能内 Windows 绝对路径清理）
