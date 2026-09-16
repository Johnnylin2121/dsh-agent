# PORTABILITY — 跨端内容规范（Windows ⇄ macOS）

> 双端工作制（Windows 主机 + macOS 笔记本）下，**任何一端推进仓库的内容，另一端必须能直接用或简单适配后用**。
> 本文件是写作规范；仓库地图见 `REPO-MAP.md`，双端协作流程见 `DUAL-END.md`。
> 规范由 `tools/validate-repo.mjs` + `.github/workflows/validate.yml` 自动把关。

---

## 1. 三条硬规则

| # | 规则 | 禁止 | 应该写成 |
|---|---|---|---|
| 1 | **不写死平台绝对路径** | `C:\Users\<用户>\...`、`/Users/<用户>/...`、云盘里的 vault 绝对路径 | `{VAULT_PATH}`、`{DSH_HOME}`、`~/.dsh/...`、`$HOME/...`、`%USERPROFILE%`、`$env:USERPROFILE` |
| 2 | **不写死解释器/程序路径** | 只给一个平台的 `python.exe` 全路径 | 给两端等价写法（见 §3），或写"先检测再执行" |
| 3 | **不推平台/环境产物** | 密钥、token、`*.xlsx/csv`、`__pycache__`、`.DS_Store`、>1 MB 二进制、机器专属配置 | 用 `plugins/package.json` 之类**可重建的清单**代替产物；数据进 vault |

> 规则 1/2 由体检脚本判为**阻塞项**（exit 1，CI 红）；规则 3 中垃圾文件是阻塞项，数据/大文件是提醒。

## 2. 占位符表（写文档/脚本时统一使用）

| 占位符 | 含义 | 各端取值来源 |
|---|---|---|
| `{VAULT_PATH}` | Obsidian vault 根 | **各机自己的 `~/.dsh/MEMORY.md` 的「Obsidian Vault」行**（两端路径不同，绝不入库） |
| `{DSH_HOME}` | DSH 主目录 | 两端都是 `~/.dsh` |
| `{WORKSPACE}` | 该机工作区 | 各机不同（Windows 常为 `E:\...`，macOS 常为 `~/...`） |
| `{UPSTREAM}` | DSH 上游源码副本 | 各机不同 |
| `{SKILL_DIR}` | 当前 skill 目录 | `~/.dsh/skills/<skill-name>`（两端一致） |

## 3. 平台对照表（写命令时对照）

| 场景 | Windows（pwsh） | macOS（zsh/bash） |
|---|---|---|
| Python 解释器 | `$PY = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"`（本机裸 `python` 指向无库的旧 venv、`python3` 是无效 stub） | `PY="$(command -v python3)"`（依赖：`pip3 install pandas openpyxl akshare`） |
| 调用脚本 | `& $PY "$SKILL/scripts/x.py" args` | `"$PY" "$SKILL/scripts/x.py" args` |
| 当前时间 | `Get-Date -Format 'yyyy-MM-dd dddd'` | `date '+%Y-%m-%d %A'` |
| 环境变量（本会话） | `$env:FOO = "bar"` | `export FOO=bar` |
| 环境变量（持久化） | `setx FOO "bar"`（新进程生效） | 写进 `~/.zshrc`：`export FOO=bar` |
| 列目录/查找 | `Get-ChildItem` / `Select-String` | `ls` / `grep` |
| 空设备 | `$null` | `/dev/null` |
| 路径分隔符 | `\` 或 `/`（pwsh 都吃） | `/` |
| 文件权限位 | 无概念 | 脚本需 `chmod +x`（如 `~/.dsh/git-hooks/pre-push`） |
| 编码 | UTF-8（无 BOM）；控制台需 UTF-8 | UTF-8 默认 |
| 换行 | 仓库统一 **LF**（`.gitattributes` 已固定，`core.autocrlf=false` 更省心） | LF 天然 |

**每个命令块的建议写法**：先给一段"平台中立变量初始化"，再给两端调用形式，例如

```powershell
# Windows PowerShell
$PY = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"; $SKILL = "$env:USERPROFILE\.dsh\skills\<skill>"
& $PY "$SKILL/scripts/x.py" --input data.xlsx
```
```bash
# macOS
PY="$(command -v python3)"; SKILL="$HOME/.dsh/skills/<skill>"
"$PY" "$SKILL/scripts/x.py" --input data.xlsx
```

## 4. 自动门禁

```bash
node tools/validate-repo.mjs      # 本地：退出码 1 = 有阻塞项，别推
```
CI 在 push / PR 时自动跑同一脚本（`.github/workflows/validate.yml`，ubuntu-latest + Node 20）。
本地 git 钩子另有 `push-scan.ps1`（gitleaks + 隐私正则）负责**密钥/PII**这一类。

## 5. 开发侧常见坑（双端特有）

| 坑 | 现象 | 处理 |
|---|---|---|
| CRLF/LF 混用 | diff 全文件飘红、mac 端脚本报 `\r` 错 | 仓库已 `.gitattributes: eol=lf`；一次性规范化：`git add --renormalize .` |
| macOS 文件名 NFD 规范化 | 同名文件出现"两份"（NFC/NFD 码点不同） | mac 端 `git config core.precomposeunicode true`（默认多为 true） |
| 大小写不敏感文件系统 | 只改大小写文件名，git 不识别；CI（Linux，区分大小写）反而报错 | 用两步 `git mv a tmp && git mv tmp B` |
| 权限位 | mac 上克隆后发现钩子/脚本不可执行 | `chmod +x`（Windows 上克隆不会带可执行位，两端各自设一次） |
| OneDrive 占位符/按需下载 | 读到空文件或锁冲突 | 批量写入分批；必要时对 vault 目录"始终保留在此设备" |
| 平台专属补丁 | 把某端才需要的补丁当成通用 | 见 `DUAL-END.md` §5「两端差异与豁免」 |

## 6. 提交前检查清单（两端 agent 都跑）

1. `node tools/validate-repo.mjs` → 无阻塞项
2. `git status --short` → 只提交该提交的内容（无临时文件、无数据文件）
3. 文档中的命令：**两端各能跑**（或明确标注"仅 Windows/仅 macOS"）
4. 路径一律占位符；解释器一律两端写法
5. `pwsh "$HOME/.dsh/git-hooks/push-scan.ps1" -Range origin/main..HEAD` → OK（或依赖 pre-push 钩子自动拦）
