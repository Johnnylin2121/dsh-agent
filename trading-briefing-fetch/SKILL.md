---
name: trading-briefing-fetch
description: 财经早报数据自动抓取（akshare）。商品价格表/美股指数/财联社系快讯 → 生成标准格式 markdown 草稿到 交易体系/早报草稿/（与正式早读隔离）。用户说"跑早报"、"抓今天数据"、"生成早报草稿"时使用。
---

# 财经早报抓取 (briefing-fetch)

## 触发
用户说：跑早报 / 抓今天的数据 / 生成早报草稿 / 数据表自动化

## 执行步骤
1. 运行 `pwsh -NoProfile -File "D:\OneDrive\ObsidianVault\_系统\scripts\fetch-briefing.ps1"`（可加 `-Date YYYY-MM-DD` 指定日期）
2. 读取输出 `交易体系/早报草稿/YYYY-MM-DD-财经早报-自动草稿.md`
3. 呈现给用户：商品表（含 A50）/美股表/要闻筛选三块，标注 [待补] 项
4. **LLM 终筛**（会话内执行）：对要闻筛选节，按六类关注方向 + 估值视角（PE分位/息差/汇率敏感性/中签率/相关性轮动/持仓关联）打分，选出 5~8 条作为正式稿要闻，剔除情绪化/无关噪音

## 关键约定
- **输出目录**：`交易体系/早报草稿/`（独立文件夹，不与正式 交易体系/财经早读/ 混放）
- 草稿头部带"自动生成、未经人工审核"标记；**不自动入库**
- 人工审核通过后，走现有 ingest 流程（obsidian-vault-sync skill）转正式文件
- 数据口径：商品/美股 = 最近两根日线收盘（与人工版"15:00→次日6:30"口径不同，需人工校准）；A50 = 新浪 hq.sinajs.cn hf_CHA50CFD（实时快照，字段0=最新/7=昨收）
- 依赖：Python 3.12 + akshare（`C:\Users\johnn\AppData\Local\Programs\Python\Python312\python.exe`）；接口偶发失效时重试 1 次并保留 [待补]

## 脚本
- 抓取核心: `_系统/scripts/fetch-briefing.py`
- 入口: `_系统/scripts/fetch-briefing.ps1`
