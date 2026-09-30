# vault 路径双门禁

vault 在 2026-09-28 / 09-30 两次重组后，"skill 文档里写的路径 ≠ 磁盘上真实路径"
这一类问题连续复发。单靠人扫会漏，故设两道门禁。

## 门禁一：`validate-repo.mjs`（CI 自动跑）

- **范围**：本仓（skills）所有 git 跟踪文件
- **基线**：`tools/vault-paths.json`（由 `sync-vault-paths.mjs` 从本机 vault 生成）
- **触发**：push / PR → `.github/workflows/validate.yml`
- **为什么基线要入库**：CI 跑在 ubuntu，拿不到本机 vault，只能比对相对路径

```bash
node tools/validate-repo.mjs
```

## 门禁二：`vault-path-check-external.mjs`（本机手动跑）

- **范围**：**本仓之外**的三处
  | 源 | 为什么需要它 |
  |----|------------|
  | `E:\3.deepseek-harness\workflow_migration\*.py\|mjs\|ps1` | 目录重组后最易失效，且 `LEDGER_DIR` 会 `mkdir(parents=True)`——每工作日 15:10 的定时任务会凭空分叉出第二个账本目录 |
  | `~/.dsh/timer-agent/jobs.json` | 定时任务 prompt 内嵌 vault 绝对路径，**无人值守**，失效即静默失败 |
  | `~/.dsh/MEMORY.md`、`cordis.patch.yml`、`skills/_shared/*` | agent 的前置必读配置 |

```bash
# 真实 vault 路径不入库（仓库策略），必须显式传入
export VAULT_PATH="/path/to/your/vault"        # bash
$env:VAULT_PATH = "D:\path\to\your\vault"      # PowerShell

node tools/vault-path-check-external.mjs
# 退出码 0 通过 / 1 有失效 / 2 未设 VAULT_PATH 或 vault 不可用
```

## ⚠️ 改提取逻辑后必须做灵敏度自测

本门禁在开发中出过两次同类事故，**两次都表现为"绿色通过但实际没检查"**：

1. `a|b` 直接拼 `[\\/]x` —— `|` 优先级低于字符类，路径部分只绑到最后一个分支，
   于是**只有 `_系统` 一个顶层域被检查**
2. `${ALT}[\\/]${TAIL}` 漏了外层括号 —— 捕获组只圈住顶层域名，路径部分落在组外，
   `m[1]` 只拿到 `交易体系` 而非完整路径

两者的共同教训：**标记/状态显示"已启用"不等于检查真的生效。**
所以改过 `TOP_ALT` / `TAIL` / `REL_CAPT` 任一行，都要用探针自测：

```bash
# 探针应含：1 条反引号坏路径、1 条 {VAULT_PATH} 坏路径、1 条绝对路径坏路径，
#          外加正文列举 / 命名模板 / 更正说明 / 禁令句各一行（这些应被忽略）
GATE_PROBE=<探针文件> node tools/vault-path-check-external.mjs
```

判定标准：**坏路径 3/3 抓到，且 4 类噪声全部忽略**，才算通过。
只看到 `✅ 外部源无阻塞项` 就收工，等于没测。

## 误报来源（已知的合法噪声）

| 形态 | 处理 |
|------|------|
| 正文列举 `（分析报告/选品/附件/记忆）` | 不在反引号/`{VAULT_PATH}`/绝对路径语境 → 不提取 |
| 命名模板 `YYYY-MM-DD-主题.md`、`{日期}.md` | `TEMPLATE` 规则跳过 |
| 更正说明行「原写作 ……」 | `SKIP_LINE` 跳过 |
| 禁令句「禁止新建 ……」 | `SKIP_LINE` 跳过 |
| shell 参数 `Get-ChildItem X -File` | 截到 `-` 参数边界 |

**注意副作用**：写"更正说明"时不能把旧路径写成连续字面量，
否则会被自己写的门禁判为失效引用——这也是好事，它逼更正说明用描述性表述。

## 刷新基线

vault 重组后需要重新生成：

```bash
node tools/sync-vault-paths.mjs    # 人工维护的 exempt/plannedDirs 会在刷新时保留
node tools/validate-repo.mjs       # 复验
```
