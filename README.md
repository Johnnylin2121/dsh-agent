# dsh-agent

个人 DSH（DeepSeek Harness）技能与插件配置仓库。跨会话持久化，换机器一键恢复。

> **双端工作制**（Windows 主机 + macOS 笔记本，长期）：先读这两份再动手
> - `DUAL-END.md` — 双端同步模型、Mac 端接入清单、推送协议、并发冲突规则、两端差异豁免
> - `_shared/PORTABILITY.md` — 跨端内容写作规范（占位符、解释器、命令两端写法、常见坑）
> - `REPO-MAP.md` — 仓库地图：5 个远端仓、本地副本映射、**什么内容放哪里**、缺口清单
> - 自动门禁：`node tools/validate-repo.mjs`（本地）+ `.github/workflows/validate.yml`（push/PR 自动跑）；隐私扫描由 `push-guard/` 钩子负责
> - 许可：MIT（见 `LICENSE`）

## 包含什么

### Skills（21 个）

| 类别 | 技能 | 用途 |
|------|------|------|
| **交易** | `trading-daily-review` | A股每日复盘全流程（盘前→盘中→盘后） |
| | `trading-contradiction-check` | 盘后矛盾检测（预判vs实际、持仓逻辑一致性） |
| | `trading-policy-impact` | 政策/事件影响链路分析 |
| | `trading-stock-scan` | 个股深度研究（公告/评级/资金/技术面） |
| | `trading-value-investing` | 价值投资体系（Mr.Dang功法） |
| | `trading-briefing-fetch` | 财经早报数据抓取（akshare商品/美股/快讯→标准md草稿，六类关注方向规则初筛+LLM终筛） |
| | `trading-briefing-review` | 早读复核（数据四态判定 + 主观判断审阅 + 盲区标记） |
| | `trading-memory-consolidate` | 交易记忆批量审阅与八区记忆总表生成 |
| **Amazon** | `amazon-ad-analysis` | 广告数据分析与经营分析 |
| | `amazon-listing` | Listing优化（竞品关键词→标题≤75+商品亮点≤125→五点→后台搜索词，2026-07新政策） |
| | `amazon-product-selection` | 选品分析（卖家精灵/ABA关键词趋势） |
| **知识库** | `obsidian-vault-sync` | 文件同步到Obsidian vault |
| | `obsidian-reconcile` | 检测vault中的矛盾信息 |
| | `domain-memory` | 跨会话领域记忆管理 |
| **效率** | `caveman` | 极简输出模式（省token，与 dsh-peak-cost-mode 插件分工：插件管高峰自动、caveman 管用户主动） |
| | `caveman-commit` | 极简commit信息生成 |
| | `caveman-compress` | 压缩记忆文件省token（DSH 无 Claude 环境时模型手工压缩） |
| | `caveman-help` | caveman模式速查 |
| | `caveman-review` | 极简代码审查 |
| **通用** | `grill-me` | 苏格拉底式提问 |
| **仓库运维** | `skill-sync` | 与 GitHub 的同步流程 + 强制隐私扫描（push-guard） |

> 📍 **仓库地图**：`REPO-MAP.md` —— 5 个远端仓的巡检简报、本地副本映射、**"什么内容放哪个仓库/目录"** 的放置规则、推送链路与缺口清单。管理/推送前先看它。

> 2026-08 已移除：`notion-api`（macOS/zsh+jq+curl 写法，Windows 全链不可用；Notion 写入已由 trading-daily-review 内置集成承担）。

### Plugins（备份）

`plugins/` 目录备份 DSH web profile 的插件配置（`package.json` + 一键恢复脚本 `restore-plugins.ps1`）。`plugins/dsh-patches/` 额外备份两个**本地补丁**（context-doctor 原生 fetch 版 + dsh-xueqiu TLS 规避/浮窗隐藏补丁），来历与恢复方法见其 README；备份根因是本机 schannel TLS 损坏（详见 `plugins/dsh-patches/README.md`）。

当前插件：`dsh-plugin-deepeye`（视觉，后端 opencode-go mimo-v2.5，见 profile cordis.patch.yml）· `dsh-peak-cost-mode`（高峰省流）· `dsh-find-plugin` · `dshmarket` · `dsh-xueqiu` · `dsh-obsidian` · `dsh-context-doctor`（本地补丁 link:）· `@liustack/modsearch`（网页/X读取）· `@wxg-prc-cpg/browser-skill-dsh-plugin`（浏览器自动化，六工具为**惰性揭示**：先 `skill browser-skill` 才出现）· `dsh-rss-digest`（RSS→每日简报，早报数据源之一）· `dsh-timer-agent`（Host 常驻 cron 定时任务，工具 `timer_agent`）· `dsh-notifier`（多渠道通知，工具 `notify`/`notify_test`，需先配渠道）· `dsh-cost-meter`（会话/当日费用、预算、余额、历史、峰谷计价；补 peak-cost 台账不落盘的缺口）· `dsh-excel-kit`（只读 Excel 分析，工具 `excel_describe`/`excel_filter`/`excel_pivot`）。

> ⚠️ **两处非标准依赖写法（恢复时别踩）**：
> 1. `dsh-excel-kit` 是 **npm 别名依赖**：`"dsh-excel-kit": "npm:@helibeiqi/dsh-excel-kit@^0.1.1"`。原因：该插件自带的 bundle patch 用**裸名** `dsh-excel-kit` 作模块说明符，而 npm 上没有同名非作用域包；用别名让依赖键=裸名，裸名即可解析，bundles 里也写 `dsh-excel-kit`（**不要**写 `@helibeiqi/dsh-excel-kit`，否则合成树里同一 id 会出现两行、其一是解析不了的裸名）。`restore-plugins.ps1` 会照别名 spec 安装。
> 2. DeepEye 的 API key **不再内联**在 profile `cordis.patch.yml`：该文件里是 `apiKey: ''`，插件按 `config.apiKey > provider 专属 env > DEEPEYE_API_KEY` 回退，`provider: custom` 时读 `process.env.DEEPEYE_API_KEY`（用 `setx DEEPEYE_API_KEY "<key>"` 写入用户环境，**重启 dsh web 后生效**）。rss-digest 落盘配置仍在 profile `cordis.patch.yml`（不含密钥）。

> 2026-09-15 已移除：`@linxin666/dsh-client-ui-task-board`（任务看板 cron 托管——装后从未真正建过/触发过任务，数据目录已清）、`dsh-whale-widget`（余额挂件，早前已卸）。**定时托管改由 `dsh-timer-agent`（`timer_agent` 工具）承接，提醒推送由 `dsh-notifier`（`notify` 工具）承接**，用法见 `trading-daily-review` 阶段二「无人值守提醒」。

> 2026-09-13 已移除：`@vectorize-io/hindsight-coding-agents`（用户评估后不符合预期，未配 token 即弃用；配置目录 `~/.hindsight` 已删）、`@dickpy/dsh-imagegen`（本机无生图渠道/opencode-go 无 images 端点，用户弃用；数据目录 `~/.dsh/dsh-imagegen` 暂留以防复装）。DeepEye 视觉后端已配置为 opencode-go `mimo-v2.5`（用户指定；minimax-m3 实测可用作备选）。

### 共享工具

`_shared/dsh-market.mjs` — 轻量市场数据获取工具（替代curl，规避Windows Schannel问题）。

`_shared/vault-batch.mjs` — Obsidian vault 批量整理（零依赖，Node >=18）。补齐 `dsh-obsidian` 没有的两块：① 批量移动/重命名笔记或整个目录，并重写全库 `[[wikilink]]`／`![[embed]]`（保留 `|别名`、`#锚点`、`^块引用`，链接风格保持「路径式仍路径、裸名仍裸名」，移动后清理空目录）；② 库结构 + 标签统计、孤立笔记（无入链无出链）、悬空链接（指向不存在的笔记）。

```powershell
$vb = "$HOME/.dsh/skills/_shared/vault-batch.mjs"
node $vb structure                        # 结构/标签/孤立/悬空
node $vb orphans                          # 仅孤立笔记
node $vb dangling                         # 仅悬空链接
node $vb move "旧路径.md" "新路径" --dry-run   # 也支持整目录；先 dry-run
node $vb move-batch map.json --dry-run    # map.json: {"旧":"新", ...}，裸文件名可唯一定位
```

vault 根目录解析顺序：`--vault <path>` > 环境变量 `VAULT_PATH` > 从 `MEMORY.md` 中匹配含 `ObsidianVault` 的路径。

---

## 快速开始

### 全新安装（换机器）

```powershell
# 1. 克隆到 DSH skill 目录
git clone git@github.com:Johnnylin2121/dsh-agent.git "$HOME\.dsh\skills"

# 2. 恢复插件
pwsh "$HOME\.dsh\skills\plugins\restore-plugins.ps1"

# 3. 重启 dsh web
```

### 日常使用

技能在 DSH 会话中自动加载，无需手动操作。当 agent 检测到对应场景（如"帮我分析广告数据"）时会自动调用对应 skill。

### 更新

```powershell
cd "$HOME\.dsh\skills"
git pull origin main
```

---

## 维护指南

### 修改 skill 后推送

agent 会自动执行。手动操作：

```powershell
cd "$HOME\.dsh\skills"
git add -A
git commit -m "feat(skill-name): 描述"
git push origin main
```

### 增删插件后更新备份

```powershell
Copy-Item "$HOME\.dsh\profiles\web\package.json" "$HOME\.dsh\skills\plugins\package.json" -Force
cd "$HOME\.dsh\skills"
git add -A
git commit -m "chore(plugins): add/remove xxx"
git push origin main
```

或直接让 agent 执行"更新插件备份"。

---

## 注意事项

- **Vault 路径**：skill 中使用 `{VAULT_PATH}` 占位符，agent 执行时从 `MEMORY.md` 读取本机实际路径替换
- **Shell**：Windows 用 pwsh，skill 中的 bash 代码块由 agent 自动改写
- **分支**：始终使用 main 分支，禁止 force push
- **密钥**：API key 等敏感信息不存入本仓库，通过环境变量读取

## License

个人配置仓库，仅供参考。
