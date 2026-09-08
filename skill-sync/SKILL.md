---
name: skill-sync
description: >
  管理本地 skill 与 GitHub 远程仓库的同步, 内置 push 前隐私泄露扫描
  (API key/token/持仓记录/本机路径/PII)。
  所有平台共用 `main` 分支, 平台差异在 skill 内部通过运行时检测处理。
  当用户说"同步 skill"、"推送到 GitHub"、"skill 更新了吗"、"检查 skill 版本"、
  "安装 push 防护"、"skill-sync"时使用。
---

# Skill Sync

管理本地 skill 目录与 GitHub 远程仓库的同步。
**所有推送必须先过隐私扫描**（见 Step 3.5），扫描引擎与 git pre-push hook 配套。

---

## 仓库注册表

| 仓库 | 远程 | 用途 |
|------|------|------|
| **dsh-agent（默认）** | `git@github.com:Johnnylin2121/dsh-agent.git` | **本地 `~/.dsh/skills/` 就是它的 clone**——所有 dsh 适配 skill + push-guard 组件的真源 |
| agent-skill | `https://github.com/Johnnylin2121/agent-skill.git` | 旧技能集仓库（mimocode 时代），与 dsh-agent 内容部分重复，仅历史参考 |
| dsh-agent-presets | `https://github.com/Johnnylin2121/dsh-agent-presets.git` | agent preset 配置 |

**规则**：默认操作 dsh-agent（即当前目录本身）；跨仓库操作前先向用户确认。
**单份真相**：skill 内容只在 dsh-agent 维护，不向 agent-skill 双写（避免漂移）。

---

## 前置检查（每次执行前必须执行）

### Step 0：确认当前分支与仓库

```bash
cd <repoDir>
git branch --show-current
git remote -v
```

**规则**：必须为 `main` 分支。如果不是，切换到 `main` 再继续。
确认 remote 属于上方注册表，避免推错仓库。

---

## 流程

### Step 1：检测版本差异

```bash
git status
git log origin/main..HEAD --oneline   # 本地有但远程没有的提交
git log HEAD..origin/main --oneline   # 远程有但本地没有的提交
```

向用户报告：
- 本地未提交的更改（modified / untracked）
- 本地领先远程的提交数
- 远程领先本地的提交数

### Step 2：处理分歧（如有）

如果远程领先本地（`git pull` 会产生合并）：
- 先执行 `git pull origin main`
- 如有冲突，列出冲突文件并提醒用户手动解决
- 如无冲突，自动完成合并

**冲突处理建议**：

| 冲突类型 | 建议 |
|---------|------|
| SKILL.md 冲突 | 保留双方内容，手动合并后 `git add` + `git commit` |
| 新增文件冲突 | 通常保留双方，不会真正冲突 |
| 删除文件冲突 | 确认哪个版本正确，手动处理 |

### Step 3：提交本地更改

如果有未提交的更改：

**自动生成提交信息**：根据变更文件自动判断提交类型和描述。

```bash
git status --porcelain
```

**提交信息生成规则**：

| 变更情况 | 提交信息格式 | 示例 |
|---------|-------------|------|
| 新增 skill 目录 | `feat: add <skill-name>` | `feat: add amazon-listing` |
| 更新单个 skill | `feat: update <skill-name> - <简述>` | `feat: update amazon-ad-analysis - add scripts/analysis.py` |
| 更新多个 skill | `feat: update skills - <简述>` | `feat: update skills - optimize 4 skills` |
| 删除 skill | `chore: remove <skill-name>` | `chore: remove last30days` |
| 新增脚本/参考文件 | `feat: add <skill-name> scripts/references` | `feat: add amazon-listing scripts` |
| 修改配置文件 | `chore: update config` | `chore: update .gitignore` |

```bash
git add -A
git commit -m "<自动生成的提交信息>"
```

### Step 3.5：隐私扫描（必须，不可跳过）

提交后、push 前，运行扫描引擎：

```bash
pwsh -NoProfile -File "$HOME/.dsh/git-hooks/push-scan.ps1" -Range "origin/main..HEAD"
```

**结果处理**：

| 结果 | 动作 |
|------|------|
| `OK`（exit 0） | 继续 Step 4 |
| 拦截（exit 1） | **停止流程**。逐条向用户展示命中项，按「处置指引」协助处理：真泄露→脱敏后 amend/新 commit；误报→写入仓库根 `.pushscan-allow`（每行一条正则）后重扫 |
| 引擎错误（exit 2） | 向用户报告错误，**默认停止**，除非用户明确指示继续 |

**红线**：
- ❌ 不得自行使用 `git push --no-verify` 绕过 hook；仅当用户明确说"跳过扫描推送"时才可用，且必须复述命中项让用户知情
- ❌ 扫描命中的内容视为已泄露风险，处理后重新扫描直到干净

### Step 4：推送到远程

```bash
git push origin main
```

**hook 拦截时**：pre-push hook 会再次扫描（与 Step 3.5 双保险）。被拦截 → 同 Step 3.5 处置。

**DSH 会话内注意**：DSH 沙箱禁止 msys sh 启动，`git push` 可能报
`couldn't create signal pipe` / `failed to execute prompt script` —— 这是沙箱限制，
不是 hook 逻辑问题。此时：Step 3.5 已完成的扫描仍然有效，但真正推送需用户在
**普通终端**执行（hook 在终端正常拦截），或经用户明确确认后 `--no-verify`。

若 push 被拒绝（非拦截类，如 non-fast-forward）：
- 执行 `git pull origin main` 合并远程更改
- 再次 `git push origin main`
- 若仍有冲突，提示用户手动解决

### Step 5：确认结果

执行 `git status` 和 `git log --oneline -3` 确认同步成功，向用户报告最终状态。

---

## 安装 push 防护（一次性）

用户说"安装 push 防护"或 hook 未生效时执行并验证：

```bash
# 1. 全局 hooksPath（所有仓库生效, 含未来新 clone; $HOME 由 shell 展开, Windows/macOS 通用）
git config --global core.hooksPath "$HOME/.dsh/git-hooks"
# 2. 验证
git config --global --get core.hooksPath   # 应输出 $HOME/.dsh/git-hooks
Test-Path "$HOME/.dsh/git-hooks/pre-push"  # 应为 True
Test-Path "$HOME/.dsh/git-hooks/push-scan.ps1"  # 应为 True
```

**组件**：
- `~/.dsh/git-hooks/pre-push`：git hook, 从 stdin 读待推送 ref, 调用扫描引擎
- `~/.dsh/git-hooks/push-scan.ps1`：扫描引擎（gitleaks + 9 条自定义正则）
- 手动全历史深扫：`pwsh -NoProfile -File ~/.dsh/git-hooks/push-scan.ps1 -Full`
- 仓库级跳过：`git config pushscan.skip true`（私有仓库用）
- 误报白名单：仓库根 `.pushscan-allow` 或全局 `~/.dsh/git-hooks/pushscan-allow-global`

**依赖**：gitleaks（winget 装 gitleaks.gitleaks）、rg、pwsh。缺 gitleaks 时引擎自动降级为纯正则。

---

## 选择性同步

用户可以指定只同步特定 skill 或特定仓库。

**用法**：
- "同步 amazon-listing"
- "把 trading-* 推到 dsh-agent"
- "skill-sync amazon-product-selection"

**执行流程**：
1. 只 `git add` 指定目录下的文件
2. 提交信息使用该 skill 名称
3. **同样必须过 Step 3.5 扫描**
4. 推送到远程

---

## 同步状态仪表盘

用户说"检查 skill 版本"或"skill 状态"时，输出同步状态仪表盘。

**输出格式**：

```markdown
## Skill 同步状态

| Skill | 本地状态 | 远程状态 | 同步状态 |
|-------|---------|---------|---------|
| amazon-ad-analysis | ✅ 已提交 | ✅ 已同步 | 🟢 同步 |
| amazon-listing | ⚠️ 有变更 | - | 🟡 待同步 |
| trading-daily-review | ✅ 已提交 | ❌ 落后 | 🔴 需推送 |

**汇总**：
- 已同步：X 个
- 待同步：Y 个（有本地变更）
- 需推送：Z 个（本地领先远程）
- 需拉取：W 个（远程领先本地）
- 当前分支：`main`
```

**判断逻辑**：
- 有本地变更（`git status` 非空）→ 🟡 待同步
- 本地领先远程（`git log origin/main..HEAD` 有提交）→ 🔴 需推送
- 远程领先本地（`git log HEAD..origin/main` 有提交）→ 🔵 需拉取
- 都为空 → 🟢 同步

---

## 快捷模式

用户说"同步 skill"且无其他上下文时：
1. 执行 Step 0（确认分支与仓库）
2. 执行 Step 1（检测差异）
3. 若有远程分歧 → Step 2
4. 若有本地更改 → Step 3
5. **Step 3.5 隐私扫描**
6. 若有需要推送 → Step 4
7. 执行 Step 5（确认结果）

---

## 内容脱敏规范（写 skill 文档时遵守）

防止下次推送又夹带隐私：

| 禁止 | 用占位符替代 |
|------|-------------|
| 真实持仓/交易记录（价格+动作组合） | `XXXXXX X.XXX 入场`、`某ETF` |
| Windows 用户名路径（含用户目录的绝对路径） | `%LOCALAPPDATA%\...`、`~/.dsh/...` |
| 真实 Vault 路径（云同步目录绝对路径） | `{VAULT_PATH}` |
| 真实 ASIN（B0 开头 10 位产品码） | `B0########` |
| API key/token 任何形式（含"示例"） | `YOUR_TOKEN`、环境变量引用 |

---

## 禁止的操作

- ❌ 禁止使用 `git push --force`（历史重写类操作须用户逐条确认后另行执行）
- ❌ 禁止在 skill 运行时自动提交并推送（每步等用户确认）
- ❌ 禁止跳过 Step 3.5 隐私扫描
- ❌ 禁止将 `__pycache__`、`.DS_Store`、`Thumbs.db`、`*.xlsx`、`*.csv` 等数据/缓存文件提交

## 注意事项

- 不主动删除远程分支或强制推送
- push 被拒绝时先 pull 再 push，不使用 `--force`
- 每次操作前先确认当前在 `main` 分支且 remote 正确
- 选择性同步时，只提交指定目录的文件
- 自动生成提交信息时，优先使用具体 skill 名称而非通用格式
- scanned/blocked 输出中出现的内容本身可能含敏感信息，汇报时注意脱敏
