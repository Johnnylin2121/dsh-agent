# REPO-MAP — DSH 资产与 GitHub 仓库地图

> 生成：2026-09-16（`gh` 登录后首版）· 数据来源：`gh` API 实时查询 + 本地 git 状态 + 目录实测
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

## 1. 远端仓库一览（`gh` 实时，2026-09-16）

| 仓库 | 定位 | 规模 | 最后推送 | 默认分支 | 主要缺口 |
|---|---|---|---|---|---|
| **dsh-agent** | 主力：DSH skills + 插件配置/补丁备份 + push 防护 | 143 blobs / 1.4 MB | 2026-09-16 | main | 无 description/topics/license；无 CI |
| **agent-skill** | 旧技能集（MiMoCode 时代），仅历史对照 | 75 blobs / **15.5 MB** | 2026-09-08 | main | 与 dsh-agent 大量重叠；未冻结标注 |
| **dsh-agent-presets** | agent preset 源（amazon-desk / trading-desk） | 6 blobs / 6 KB | 2026-08-14 | main | 本地副本有未提交改动 |
| **AI-story** | 另一项目：小说 + docx 脚本 + skills | 371 blobs / 735 KB | 2026-08-06 | main | 与 DSH 资产无关，勿混仓 |
| **mood-notes** | 玩具单页 | 1 blob / 4 KB | 2026-06-18 | main | 残留 `master` 分支 |

5 仓全部 **public、0 star/0 fork、0 issue/0 PR/0 release**；仅 `mood-notes` 有 1 个 workflow，其余无 CI。

---

## 2. 巡检简报（逐仓）

### 2.1 dsh-agent — 唯一活跃仓 ✅
- 内容：**21 个 skill** + `plugins/`（67 文件：插件清单备份 + `dsh-patches/` 本地补丁与铺回脚本）+ `push-guard/`（3 文件）+ `_shared/`（2 个共享脚本）+ `README.md`
- 本地副本 `{DSH_HOME}/skills`：branch `main`、**clean**、`0 ahead / 0 behind`、tip `3093f73`
- 传输：`git@github.com:Johnnylin2121/dsh-agent.git`（**SSH**，`~/.ssh/id_ed25519` 实测已认证）
- 状态：健康。skill-sync 默认目标就是它

### 2.2 agent-skill — 历史对照，建议冻结 ⚠️
- 24 个 skill、15.5 MB（体积是 dsh-agent 的 10 倍，疑有历史资产/图片）
- 与 dsh-agent 重叠 16 个；**仅此仓有 8 个**：
  - 有意剔除（DSH 无 hook 不可用）：`active-notes`、`cavecrew`、`caveman-stats`、`goal-drift`、`notion-api`、`plan-lock`
  - 被 dsh-agent 新命名取代：`trading-价值投资功法` → `trading-value-investing`、`trading-每日复盘` → `trading-daily-review`
- **仅 dsh-agent 有 5 个**：`trading-briefing-fetch`、`trading-briefing-review`、`trading-daily-review`、`trading-memory-consolidate`、`trading-value-investing`
- 结论：**不再双写**；建议 README 顶部标注 archived（或用 GitHub archive 标记）

### 2.3 dsh-agent-presets — preset 唯一真源
- `amazon-desk/`、`trading-desk/`（各含 `agent.cordis.yml` + `preset.yml`）+ README
- 本地副本 `{DSH_HOME}/.agent-presets`：**dirty（有未提交改动）**，`0/0`
- 行动：确认本地改动是否要提交

### 2.4 AI-story、2.5 mood-notes — 非 DSH 资产
- `AI-story`：`novel/` + `skills/` + `make_docx.py` / `make_ch1_docx.py` / `install.ps1`
- `mood-notes`：单文件 `index.html`，历史遗留 `master` 分支
- 行动：与 DSH 管理解耦；`mood-notes` 收敛分支或 archive

---

## 3. 地图：内容放哪里（放置规则）

| 内容类型 | 归属位置 | 入库？ |
|---|---|---|
| DSH skill 定义（`SKILL.md` + `references/` + `scripts/`） | `dsh-agent/<skill-name>/` | ✅ |
| 跨 skill 共享脚本 | `dsh-agent/_shared/` | ✅ |
| profile 插件清单备份 | `dsh-agent/plugins/package.json` | ✅ |
| 本地插件补丁 + 铺回脚本 | `dsh-agent/plugins/dsh-patches/` | ✅ |
| push 防护脚本（pre-push / push-scan） | `dsh-agent/push-guard/`，镜像到 `{DSH_HOME}/git-hooks`（两份必须逐字节一致） | ✅ |
| agent preset 源 | `{DSH_HOME}/.agent-presets` ↔ 仓 `dsh-agent-presets` | ✅（另一仓） |
| 插件运行时本体 | `{DSH_HOME}/profiles/web/node_modules/` | ❌ 靠 `plugins/package.json` + `restore-plugins.ps1` 重建 |
| profile 配置 `cordis.patch.yml` | 本地（机器相关 + 含密钥） | ❌ |
| 全局记忆 / 设置 / 凭据：`MEMORY.md`、`settings.yaml`、`.credentials.yaml` | `{DSH_HOME}/` | ❌（PII / 密钥） |
| 交易、亚马逊业务产物（复盘、早读、ASIN 分析、选品报告…） | `{VAULT_PATH}` | ❌（vault 自带同步） |
| 工作区脚本与中间产物（`*.py`、`analysis_results/`、`processed_data/`、`_listing_tmp/`…） | `{WORKSPACE}` | ❌（当前无版本控制，见缺口 6） |

---

## 4. 推送与同步路径

```
改动产生  →  {DSH_HOME}/skills（= dsh-agent 工作副本，SSH）
          →  skill-sync 流程：status → add → commit → push-scan → push → 复核
          →  全局钩子：core.hooksPath = {DSH_HOME}/git-hooks
             └─ pre-push → push-scan.ps1（gitleaks + 9 条自定义正则 + .pushscan-allow）
```

- **dsh-agent**：SSH（`id_ed25519`）；工作副本 = `{DSH_HOME}/skills`；唯一工作流封装 = `skill-sync`
- **agent-skill / upstream**：HTTPS（无显式 `credential.helper`，走 Git for Windows 默认凭据）
- **`gh`**：已登录 `Johnnylin2121`（scopes `repo, read:org, gist, workflow`，协议 ssh）
- **边界（重要）**：push-guard **只拦 `git push`**；`gh` 的 API 写操作（建/合 PR、改 issue、改 workflow、发 release）**不经过扫描** → API 写操作一律先人工确认
- 标准命令：
  ```powershell
  cd "$HOME\.dsh\skills"
  git status --short
  git add -A; git commit -m "type(scope): 摘要"
  pwsh "$HOME\.dsh\git-hooks\push-scan.ps1" -Range "origin/main..HEAD"   # 必要时先扫
  git push origin main
  ```

---

## 5. 缺口清单（按优先级）

**P0 一致性/安全**
1. `{DSH_HOME}/.agent-presets` 处于 dirty：确认改动后提交，避免 preset 漂移
2. `git-hooks/` 与仓内 `push-guard/` 目前 hash 一致，但**没有自动校验**——建议把"两份一致性检查"并入 `plugins/dsh-patches/reapply-all.ps1` 同级的维护脚本

**P1 可管理性**
3. 5 个仓全部缺 `description` / `topics` / `license`：可用 `gh repo edit` 一次性补齐（写操作，需确认）
4. `agent-skill` 15.5 MB 且与 dsh-agent 重叠：冻结/归档，README 标注
5. `mood-notes` 残留 `master` 分支：收敛或归档

**P2 可选**
6. `{WORKSPACE}` 约 108 MB 无版本控制（含 amazon 产物、`.dsh-patches`）：明确归档策略（进 vault 或建私仓）
7. 无 CI：可在 dsh-agent 加最小 workflow（跑 push-scan + skill 结构校验）——注意会执行仓库内脚本
8. `skill-sync` 注册表原只登记 3 仓：已在本轮补齐为 5 仓 + "默认不操作"标注

---

## 6. 变更记录

- **2026-09-16** 首版：`gh` 登录后全量巡检 5 仓 + 本地 4 个副本 + 未纳管资产；补齐 skill-sync 注册表
