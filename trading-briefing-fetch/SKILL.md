---
name: trading-briefing-fetch
description: 早报自动层数据抓取（akshare+快讯）。商品价格表/美股指数/财联社系快讯 → 输出自动层 markdown 到 交易体系/09.新闻资讯/早读复核/，作为「早读复核」（trading-briefing-review）的自动数据源与人工参考。用户说"跑早报"、"抓今天数据"、"生成早报草稿"时使用。
---

# 早报自动层数据抓取 (briefing-fetch)
> ## ⚠️ 写入 vault 前必做（AGENTS 硬规则，优先于本 skill 下文任何旧表述）
>
> 1. **先读规范**：`{VAULT_PATH}/_系统/管理规则/AGENTS.md`
>    （旧位置 `_系统/AGENTS.md` 已随 2026-09-28 重组失效）
> 2. **再核对路径**：本 skill 里的 vault 路径可能已过期。落盘前
>    `Test-Path` 确认目标存在——**不要因为"路径看起来对"就 mkdir**。
>    复验：`node ~/.dsh/skills/tools/vault-path-check-external.mjs`（需设 VAULT_PATH）
> 3. **写完记审计**：`{VAULT_PATH}/_系统/日志/log.md` 追加七字段（写入者/带时区时间/
>    操作/目标/来源/摘要/验证）。旧路径 `_系统/log.md` 已失效。
> 4. **文件签名**：新建 vault 文档首行下方写 `[agent: DSH | <ISO8601 带时区>]`。
>    签名缺失 = 违规，**与内容对错无关**。

> ⚠️ **已降级（2026-09-28）**：本 skill 纯搬运、judgment=0，且**已被下游绕过**——
> 09-17 草稿缺失时 briefing-review 直接用 dsh-market+RSS 完成全部 13 项对照。
> **仅作为可选 command job 保留**：用户明确要求"跑早报数据表"时才用。
> 日常复核流程不依赖本 skill；review 缺失自动层时用 `dsh-market` + `rss-digest` 替代。

> **环境适配（2026-09-22）**：①每轮 ≤3 tool；write/subagent 分轮。②脚本失败→重试 1 次后保留 [待补]，禁止捆绑多阶段。③不使用 `xueqiu_*`（交易政策永久禁用）。④会话内不重复 read 本 SKILL。

## 定位
为「早读复核」提供**自动数据层**：抓取行情与快讯，与人工正式早读（`交易体系/01.财经早读/`）交叉印证。数据层本身不做观点、不做审阅结论——复核判断走 `trading-briefing-review`。

## 触发
用户说：跑早报 / 抓今天的数据 / 生成早报草稿 / 数据表自动化

## 执行步骤
1. 运行 `pwsh -NoProfile -File "{VAULT_PATH}\_系统\scripts\fetch-briefing.ps1"`（可加 `-Date YYYY-MM-DD` 指定日期）
2. 读取输出 `交易体系/09.新闻资讯/早读复核/YYYY-MM-DD-财经早报-自动草稿.md`
3. 呈现给用户：商品表（含 A50）/美股表/要闻筛选三块，标注 [待补] 项
4. 会话内可做要闻初筛排序（六类关注方向），但**终筛结论与复核判断属于 trading-briefing-review**，此处不产出审阅结论

## 关键约定
- **输出目录**：`交易体系/09.新闻资讯/早读复核/`（2026-09-08 由"早报草稿"改名、2026-09-24 补 `09.` 归档编号前缀；与正式 `交易体系/01.财经早读/` 隔离）
- 文件头部带"自动数据层、未经人工审核"标记；**不自动入库，永不回写正式早读**
- 数据口径：商品/美股 = 最近两根日线收盘（与人工版"15:00→次日6:30"口径不同，复核时按 trading-briefing-review 的四态规则判定）；A50 = 新浪 hq.sinajs.cn hf_CHA50CFD（实时快照，字段0=最新/7=昨收）
- **复核触发**：正式早读入库后由用户手动触发"复核早读"（trading-briefing-review）；本 skill 不自动触发复核
- 依赖：Python 3.12 + akshare。Windows 用 `$env:LOCALAPPDATA\Programs\Python\Python312\python.exe`（本机裸 `python` 是无 akshare 的 venv 3.11.15，勿改用裸 python）；macOS 用 `python3` + `pip3 install akshare`。跨端对照见 `_shared/PORTABILITY.md`。2026-09 实测 akshare 1.18.64；接口偶发失效时重试 1 次并保留 [待补]

## 配套
- RSS 全球财经简报：dsh-rss-digest 插件每日 07:00 自动生成 → `交易体系/09.新闻资讯/早读复核/rss-digest/digests/`，自动层第二信息源
  - 落盘路径由 profile `cordis.patch.yml` 的 `rss-digest.dataPath` 决定（**不在本仓库**，机器本地配置；改后需重启 dsh web）；`digests/` 由 `dataPath` 上级目录推导
- 复核流程：`trading-briefing-review` skill

## 脚本
- 抓取核心: `_系统/scripts/fetch-briefing.py`
- 入口: `_系统/scripts/fetch-briefing.ps1`
