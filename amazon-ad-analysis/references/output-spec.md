# 产出规格 v2.0（权威来源）

> 生效：2026-09-17 ｜ 适用：`amazon-ad-analysis` 全部产出（全店 + ASIN 深挖）
> 本文件是**唯一规格来源**。SKILL.md Phase 7 与 `references/templates/*` 只引用本文件；
> 两者冲突时**以本文件为准**。旧版 sheet 列表（Overall Summary / Product Overview 等）已废弃。
> 改动本文件必须：① 升 `schema_version` ② 同步 `scripts/validate_output.py` 的 `SPEC` ③ 在 CHANGELOG 追加一行。

---

## 0. 设计原则（判断"该不该加一列"的标尺）

1. **决策优先**：每一节 / 每个 sheet 对应**一个决策**，不是指标陈列。加列前先回答"这列会改变哪个动作"。
2. **动作可抄**：所有建议必须能直接抄进后台（含对象 + 动作 + 数值 + 时间）。禁止"建议优化"这类无宾语表述。
3. **闭环强制**：上一期动作的实际结果必须出现在本期报告里；没有回填就不算完成。
4. **口径显式**：每个表带口径与**数据级别（A/B/C）**声明；任何降级必须写明，禁止静默降级。
5. **契约固定**：sheet 名与列名由本文件锁定 + 版本号；容器（全店/单品）共用同一 schema，消除多套规格漂移。
6. **空表也要有表头**：某 sheet 无数据时**仍须存在**（只有表头）+ 在 `_Meta.degradations` 说明原因 —— 这样"缺失"可被脚本检出。

---

## 1. 交付物清单

| # | 交付物 | 路径 | 读者 |
|---|--------|------|------|
| 1 | Markdown 报告 | `{VAULT_PATH}/工作/亚马逊工作管理/亚马逊分析/{日期}/{日期} {店铺} 全店分析报告.md`<br>`{VAULT_PATH}/工作/亚马逊工作管理/亚马逊分析/{日期}/{ASIN} 分析报告.md` | 人（Obsidian 阅读） |
| 2 | Excel 工作簿 | 全店：`{VAULT_PATH}/工作/亚马逊工作管理/附件/3.全店分析报告/{日期} {店铺} 分析数据.xlsx`<br>单品：`{VAULT_PATH}/工作/亚马逊工作管理/附件/4.ASIN深入分析/{ASIN} 分析数据.xlsx` | 人（筛选）+ 脚本（校验） |
| 3 | 阈值校准台账 | `{VAULT_PATH}/工作/亚马逊工作管理/记忆管理/阈值校准台账.md` | 阈值迭代 |

> 多店铺：目录名用 `{日期}-{店铺名}`；日期一律用**分析时间**（非数据时间）。

---

## 2. Markdown 报告骨架（6 节，顺序不可变）

### 0. 元数据头（必需）
```
> 数据范围：YYYY-MM-DD ~ YYYY-MM-DD ｜ 店铺：{店铺} ｜ 分析时间：{日期}
> 口径：{Phase 0 确认摘要}
> 数据级别：A / B / C ｜ 降级项：{列出或"无"}

📎 附件：[[{相对路径}|显示名]]
```

### 1. 决策摘要（≤5 条动作卡）—— **最重要，写不清等于没做**

每条动作卡固定七字段（缺一不可）：

| 字段 | 要求 |
|------|------|
| 动作 | 动词开头、可执行（如"暂停""降出价 20%""把 X 词加入标题"） |
| 标的 | ASIN / 广告活动名 / 关键词，指名道姓 |
| 数字依据 | 引用的指标与数值（可追溯） |
| 预期影响 | 量化（如"花费 -$X/周，订单保持 ≥N"） |
| 验证日 | 具体日期 |
| 回滚条件 | 触发回滚的明确条件 |
| 难度 | P0-P4（P0=今天，P4=30 天） |

**无动作时**：必须写"本期无动作 + 理由（引数据）"。空白视为未完成。

### 2. 经营快照与变化
- 全店健康度：**只列会改变决策的指标**（其余进 Excel）
- 与上期环比（首次分析写"基准期"）
- 结构标记：集中度 🔴/🟡/🟢 + 生命周期阶段分布

### 3. ASIN 决策矩阵（**按动作分组，不按指标排序**）

分组固定 6 类：`立即止损` / `降价优化` / `加投` / `修 Listing` / `观察` / `停售`

每组一张表：ASIN | 档位 | 阶段 | 关键指标 | 依据 | 建议动作

### 4. 结构与词诊断（6 小节，全为新增判据）
| 小节 | 来源 | 数据级别 |
|------|------|----------|
| 4.1 广告集中度 | SKILL Phase 2D（top1_ratio / hhi_ratio） | A |
| 4.2 付费-自然资产化四象限 | SKILL Phase 5.4-A | A |
| 4.3 核心词自然位缺口 | SKILL Phase 5.4-B | **B**（需 Sorftime 面板） |
| 4.4 词四态分层 | SKILL Phase 5.4-C | A/B |
| 4.5 否定词执行清单 | SKILL Phase 5.2 | A |
| 4.6 关键词覆盖缺口 | SKILL Phase 5.3 | A（4A 为 jina 档时限缩） |

### 5. 执行清单（可直接抄后台）
按顺序列出：`对象 → 后台位置 → 操作 → 数值 → 时间`。这是给操作者的"照做单"。

### 6. 口径、数据质量与结论跟踪
- 数据级别与降级声明（逐项）
- 脏值与异常处理记录
- **上期动作回填结果**：上期每条动作 → 实际值 → 是否达标 → 继续/调整/回滚

---

## 3. Excel 工作簿契约（9 sheets，`schema_version = 2.0`）

> 列名一律**英文 snake_case**（机器稳定）；中文含义见下表。列顺序即为以下顺序，校验脚本按"必需列存在"判定（不强制顺序）。

### Sheet 0 `_Meta`
| 列 | 说明 |
|----|------|
| schema_version | 固定 `2.0` |
| generated_at | 生成时间 ISO |
| data_range_start / data_range_end | 数据范围 |
| stores | 店铺（多店铺用 `;` 分隔） |
| source_files | 输入文件名清单（`;` 分隔） |
| data_level | `A` / `B` / `C` |
| degradations | 降级项说明（无则填 `none`） |
| analysis_date | 分析日期 |
| spec_ref | `references/output-spec.md v2.0` |

### Sheet 1 `Decisions`
`priority, action, target, metric_basis, expected, verify_date, rollback, difficulty`

### Sheet 2 `ASIN_Matrix`（一行 = 一个 ASIN）
`asin, store, price, rating, reviews, units, revenue, orders, sessions, cvr, ad_spend, acos, tacos, roas, natural_order_share, ad_order_share, new_customer_share, new_customer_verdict, lifecycle_stage, position_tier, potential, campaign_count, top1_ratio, hhi_ratio, concentration_flag, action_group`

### Sheet 3 `Weekly_Trend`（一行 = ASIN × 周）
`asin, week, units, revenue, orders, sessions, cvr, ad_spend, acos, tacos, roas, natural_orders, natural_order_share`

### Sheet 4 `Ad_Structure`（一行 = 广告活动）
`asin, campaign, type, spend_28d, spend_share, cum_share, orders_28d, acos_28d, trend`

### Sheet 5 `Paid_Natural`（一行 = 词；无 B 级数据时只有表头）
`asin, keyword, ad_clicks, ad_click_share, ad_spend, ad_orders, quadrant, ad_spend_w3, ad_spend_w4, natural_orders_w3, natural_orders_w4, traffic_source, contribution_share, organic_rank, word_state, verdict, action`

### Sheet 6 `Root_Words`（一行 = 词根）
`root, root_type, demand_type, search_term_count, spend, orders, sales, cvr, acos, w1_acos, w2_acos, w3_acos, w4_acos, trend, word_state, action`

### Sheet 7 `Negations`（一行 = 否定项）
`priority, root, negate_type, sample_term, clicks, spend, orders, reason`

### Sheet 8 `Coverage`（一行 = 词根）
`root, demand_type, acos, orders, spend, front_covered, position, weight, action`

### 命名与格式细则
- **`demand_type` / `root_type` 取值**：`category|function|attribute|material|scenario|audience`（与 `amazon-listing` Step 1 六分类对齐）
- **`lifecycle_stage`**：`new|growth|mature` ｜ **`position_tier`**：`star|problem|potential|drop|pending`
- **`concentration_flag`**：`red|yellow|green` ｜ **`word_state`**：`stable|defend|weak|opportunity`
- **`new_customer_verdict`**：`acquisition|mixed|retention`
- **`action_group`**：与 Markdown 第 3 节 6 组一致
- 百分比统一**小数**（0.325 而非 32.5）；金额保留 2 位；日期 `YYYY-MM-DD`
- ACOS 脏值（>10）必须已在 Phase 1 处理，不得出现在产出中

---

## 4. 校准台账契约

路径：`{VAULT_PATH}/工作/亚马逊工作管理/记忆管理/阈值校准台账.md`
写入时机：**每次分析后**（Phase 7 强制项）。一行 = 一个 ASIN 一次分析。

| 列 | 说明 |
|----|------|
| date | 分析日期 |
| store / asin | 店铺 / ASIN |
| campaign_count | 活动数 N |
| top1_share | Top1 花费占比 |
| top1_ratio | Top1占比 × N |
| hhi / hhi_ratio | HHI 与其倍数 |
| flag | red / yellow / green |
| outcome_30d | **30 天后回填**：该 ASIN 广告曝光/订单是否出现单点塌陷（`collapse` / `stable` / `improved` / `n/a`） |
| note | 备注（如活动结构调整） |

**阈值升级规则**：累计 ≥ `calibration.min_rows_for_percentile`（默认 20）行，或距上次复核 > `calibration.review_trigger_days`（默认 60 天）→ 做一次分箱统计，若分位数方案在"召回 vs 误报"上明显优于当前锚定值，则替换 config 数值并在本文件 CHANGELOG 记录。

---

## 5. CHANGELOG

| 版本 | 日期 | 变更 |
|------|------|------|
| 2.0 | 2026-09-17 | 首版：9-sheet 契约 + 6 节报告骨架 + 决策卡七字段 + 校准台账契约；废弃旧版按容器分裂的 sheet 列表（全店 4 sheet / 单品 7 sheet） |
