---
name: trading-briefing-fetch
description: 早报自动层数据抓取（akshare+快讯）。商品价格表/美股指数/财联社系快讯 → 输出自动层 markdown 到 交易体系/早读复核/，作为「早读复核」（trading-briefing-review）的自动数据源与人工参考。用户说"跑早报"、"抓今天数据"、"生成早报草稿"时使用。
---

# 早报自动层数据抓取 (briefing-fetch)

## 定位
为「早读复核」提供**自动数据层**：抓取行情与快讯，与人工正式早读（`交易体系/财经早读/`）交叉印证。数据层本身不做观点、不做审阅结论——复核判断走 `trading-briefing-review`。

## 触发
用户说：跑早报 / 抓今天的数据 / 生成早报草稿 / 数据表自动化

## 执行步骤
1. 运行 `pwsh -NoProfile -File "D:\OneDrive\ObsidianVault\_系统\scripts\fetch-briefing.ps1"`（可加 `-Date YYYY-MM-DD` 指定日期）
2. 读取输出 `交易体系/早读复核/YYYY-MM-DD-财经早报-自动草稿.md`
3. 呈现给用户：商品表（含 A50）/美股表/要闻筛选三块，标注 [待补] 项
4. 会话内可做要闻初筛排序（六类关注方向），但**终筛结论与复核判断属于 trading-briefing-review**，此处不产出审阅结论

## 关键约定
- **输出目录**：`交易体系/早读复核/`（2026-09-08 由"早报草稿"改名；与正式 `交易体系/财经早读/` 隔离）
- 文件头部带"自动数据层、未经人工审核"标记；**不自动入库，永不回写正式早读**
- 数据口径：商品/美股 = 最近两根日线收盘（与人工版"15:00→次日6:30"口径不同，复核时按 trading-briefing-review 的四态规则判定）；A50 = 新浪 hq.sinajs.cn hf_CHA50CFD（实时快照，字段0=最新/7=昨收）
- **复核触发**：正式早读入库后由用户手动触发"复核早读"（trading-briefing-review）；本 skill 不自动触发复核
- 依赖：Python 3.12 + akshare（`C:\Users\johnn\AppData\Local\Programs\Python\Python312\python.exe`）——Python312 全路径为实测正确（2026-09 实测 akshare 1.18.64；默认 `python` 是无 akshare 的 venv 3.11.15，勿改用裸 python）；接口偶发失效时重试 1 次并保留 [待补]

## 配套
- RSS 全球财经简报：dsh-rss-digest 插件每日 07:00 自动生成 → `交易体系/早报数据/rss-digest/digests/`，自动层第二信息源
- 复核流程：`trading-briefing-review` skill

## 脚本
- 抓取核心: `_系统/scripts/fetch-briefing.py`
- 入口: `_系统/scripts/fetch-briefing.ps1`
