# REPO-MAP — DSH 资产与 GitHub 仓库地图

> 生成：2026-09-16（`gh` 登录后首版）· 更新：2026-09-16 第二轮（补元数据 / 冻结旧仓 / 防护漂移校验）
> 数据来源：`gh` API 实时查询 + 本地 git 状态 + 目录实测
> 用途：一眼看清**哪些内容归哪个仓库/目录**、**推送走哪条链**、**当前有哪些缺口**
> 本文件自身也在版本管理内：改动走 push-guard（`git push` 会被扫描）

## 0. 占位符约定

| 占位符 | 含义 |
|---|---|
| `{DSH_HOME}` | `~/.dsh`（本机即 `%USERPROFILE%\.dsh`） |
| `{WORKSPACE}` | 本机工作区 `E:\3.deepseek-harness`（**不是** git 仓库） |
| `{UPSTREAM}` | DSH 上游源码副本 `%USERPROFILE%\deepseek-harness` |
| `{VAULT_PATH}` | Obsidian vault 根；**实路径见 `{DSH_HOME}/MEMORY.md`，不入仓库** |

---

## 1. 远端仓库一览（`gh` 实时）

| 仓库 | 定位 | 规模 | 最后推送 | 状态 |
|---|---|---|---|---|
| **dsh-agent** | 主力：DSH skills + 插件配置/补丁备份 + push 防护 | 143 blobs / 1.4 MB | 活跃（每日） | ✅ 有 description + topics（`deepseek-harness`/`dsh-plugin`/`agent-skills`/`ai-agents`/`skills`） |
| **agent-skill** | 旧 MiMoCode 技能集，仅历史对照 | 75 blobs / 15.5 MB | 2026-09-16（冻结说明） | 🔒 **已归档（archived）**，README 顶部有冻结说明 |
| **dsh-agent-presets** | agent preset 源（amazon-desk / trading-desk） | 6 blobs / 6 KB | 2026-09-16 | ✅ 有 description + topics；本地已提交同步 |
| **AI-story** | 另一项目：小说 + docx 脚本 + skills | 371 blobs / 735 KB | 2026-08-06 | ✅ 有 description + topics；与 DSH 资产解耦 |
| **mood-notes** | 玩具单页 | 1 blob / 4 KB | 2026-06-18 | ✅ 已删遗留 `master` 分支，仅 `main` |

5 仓全部 public、0 star/0 fork、0 issue/0 PR/0 release；仅 `mood-notes` 有 1 个 workflow，其余无 CI。

---

## 2. 巡检简报（逐仓）

### 2.1 dsh-agent — 唯一活跃仓 ✅
- 内容：**21 个 skill** + `plugins/`（插件清单备份 + `dsh-patches/` 本地补丁与铺回脚本）+ `push-guard/`（pre-push、`push-scan.ps1`、`check-drift.ps1`、INSTALL.md）+ `_shared/`（2 个共享脚本）+ `README.md` + 本文件
- 本地副本 `{DSH_HOME}/skills`：`main`、clean、0 ahead / 0 behind
- 传输：`git@github.com:Johnnylin2121/dsh-agent.git`（**SSH**）
- 工作流：`skill-sync`（注册表已含 5 仓）

### 2.2 agent-skill — 已冻结归档 🔒
- 冻结说明已推送（`README.md` 顶部）；GitHub 侧 `archived=true`（只读，可 `gh repo unarchive` 反悔）
- 仅此仓有的 8 个 skill 已定性：6 个弃用（`active-notes`/`cavecrew`/`caveman-stats`/`goal-drift`/`notion-api`/`plan-lock`），2 个被新命名取代（`trading-价值投资功法`→`trading-value-investing`、`trading-每日复盘`→`trading-daily-review`）
- 注意：**归档后 API 只读**——要改内容/描述须先 `gh repo unarchive`

### 2.3 dsh-agent-presets — preset 唯一真源 ✅
- 本地 `{DSH_HOME}/.agent-presets` 此前的 dirty 已提交并推送（`59b5198`：`persona` 配置键 `text`→`prefix`，`dsh-persona` schema 中 `prefix` 为必填）
- 传输：SSH

### 2.4 AI-story、2.5 mood-notes — 非 DSH 资产
- `AI-story`：`novel/` + `skills/` + docx 脚本 + `install.ps1`
- `mood-notes`：单文件 `index.html`；`master` 已删（与 `main` 当时完全同点）

---

## 3. 地图：内容放哪里（放置规则）

| 内容类型 | 归属位置 | 入库？ |
|---|---|---|
| DSH skill 定义（`SKILL.md` + `references/` + `scripts/`） | `dsh-agent/<skill-name>/` | ✅ |
| 跨 skill 共享脚本 | `dsh-agent/_shared/` | ✅ |
| profile 插件清单备份 | `dsh-agent/plugins/package.json` | ✅ |
| 本地插件补丁 + 铺回脚本 | `dsh-agent/plugins/dsh-patches/` | ✅ |
| push 防护脚本（pre-push / push-scan / check-drift） | `dsh-agent/push-guard/`，镜像到 `{DSH_HOME}/git-hooks` | ✅ |
| agent preset 源 | `{DSH_HOME}/.agent-presets` ↔ 仓 `dsh-agent-presets` | ✅（另一仓） |
| 插件运行时本体 | `{DSH_HOME}/profiles/web/node_modules/` | ❌ 靠 `plugins/package.json` + `restore-plugins.ps1` 重建 |
| profile 配置 `cordis.patch.yml` | 本地（机器相关 + 含密钥） | ❌ |
| 全局记忆 / 设置 / 凭据：`MEMORY.md`、`settings.yaml`、`.credentials.yaml` | `{DSH_HOME}/` | ❌（PII / 密钥） |
| 交易、亚马逊业务产物（复盘、早读、ASIN 分析、选品报告…） | `{VAULT_PATH}` | ❌（vault 自带同步） |
| 工作区脚本与中间产物（`*.py`、`analysis_results/`、`processed_data/`…） | `{WORKSPACE}` | ❌（当前无版本控制，见缺口 6） |

---

## 4. 推送与同步路径

```
改动产生  →  {DSH_HOME}/skills（= dsh-agent 工作副本，SSH）
          →  skill-sync 流程：status → add → commit → push-scan → push → 复核
          →  全局钩子：core.hooksPath = {DSH_HOME}/git-hooks
             └─ pre-push → push-scan.ps1（gitleaks + 9 条自定义正则 + .pushscan-allow）
```

- **dsh-agent / dsh-agent-presets**：SSH（`id_ed25519`）
- **agent-skill / upstream**：HTTPS；已执行 `gh auth setup-git`，`credential.https://github.com.helper = gh auth git-credential` → HTTPS 仓复用 gh token（agent-skill 冻结说明即以此方式推送成功）
- **`gh`**：已登录 `Johnnylin2121`（scopes `repo, read:org, gist, workflow`，协议 ssh）
- **边界（重要）**：push-guard **只拦 `git push`**；`gh` 的 API 写操作（建/合 PR、改 issue、改 workflow、发 release、改仓库设置）**不经过扫描** → API 写操作一律先人工确认
- **防护漂移校验**：`pwsh {DSH_HOME}/skills/push-guard/check-drift.ps1`（`-Fix` 以仓库版本覆盖本机）；建议每次改完钩子或换机恢复后跑一次
- 标准命令：
  ```powershell
  cd "$HOME\.dsh\skills"
  git status --short
  git add -A; git commit -m "type(scope): 摘要"
  pwsh "$HOME\.dsh\git-hooks\push-scan.ps1" -Range "origin/main..HEAD"
  git push origin main
  ```

---

## 5. 缺口清单

**已解决（2026-09-16 第二轮）**
- ✅ `.agent-presets` dirty → 已提交推送（`59b5198`）
- ✅ `git-hooks/` 与 `push-guard/` 一致性 → 新增 `push-guard/check-drift.ps1`（校验 + `-Fix`）
- ✅ 5 仓缺 description/topics → 已用 `gh repo edit` 补齐（agent-skill 因归档只读，先解档后补齐再归档）
- ✅ `agent-skill` 未冻结 → README 冻结说明 + GitHub 归档
- ✅ `mood-notes` 残留 `master` → 已删
- ✅ `skill-sync` 注册表 3 仓 → 5 仓（含"非 DSH 资产默认不动"）
- ✅ HTTPS 仓无凭据助手 → `gh auth setup-git`

**仍待决（需你拍板）**
1. **LICENSE**：5 仓均无 license（个人仓库，可继续不设；若想明确授权，加 MIT/Apache-2.0 需你选）
2. **`{WORKSPACE}` 约 108 MB 无版本控制**（amazon 产物、`.dsh-patches`、临时脚本）：归档进 vault / 建私仓 / 定期清理，三选一
3. **CI**：可在 dsh-agent 加最小 workflow（push 时跑 push-scan + skill 结构校验）；注意会执行仓库内脚本
4. **agent-skill 体积**：15.5 MB 历史资产，若确认不需要可整仓删除（归档已足够，不建议轻易删）

---

## 6. 变更记录

- **2026-09-16 第一轮**：`gh` 登录后全量巡检 5 仓 + 本地 4 个副本 + 未纳管资产；补齐 skill-sync 注册表
- **2026-09-16 第二轮**：提交并推送 preset 修复（`text`→`prefix`）；`agent-skill` 加冻结说明并归档；删除 `mood-notes` 的 `master`；5 仓补 description/topics；新增 `check-drift.ps1`；`gh auth setup-git` 打通 HTTPS 推送
