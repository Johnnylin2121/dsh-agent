# 领域记忆模板

## 模板说明

所有领域记忆文件使用**统一 frontmatter 元数据**（跨域检索用），body 按领域差异化。
文件命名：`YYYY-MM-DD-<领域>-<简述>.md`
存放路径：`D:/OneDrive/ObsidianVault/<领域目录>/`

---

## 统一 Frontmatter（所有领域通用）

```yaml
---
type: domain-memory
domain: trading | amazon-ad | amazon-listing | amazon-selection | general
created: 2026-07-28
tags: [标签1, 标签2]          # 自由标签，检索用
related: [
  "[[YYYY-MM-DD 每日复盘]]",   # 关联的复盘/分析/决策文件
  "[[当前持仓]]"
]
rules: [规则A, 规则B]          # 本条记忆影响/修正了哪些规则
confidence: high | medium | low  # 这条记忆的可靠程度
---
```

---

## 领域模板：Trading（交易）

路径：`交易体系/交易记忆/YYYY-MM-DD-交易记忆.md`

### Body 结构

```markdown
---
type: domain-memory
domain: trading
created: 2026-07-28
tags: [复盘, 规则修正, 左侧交易, 量能]
related: ["[[2026-07-28 每日复盘]]", "[[当前持仓]]"]
rules: [量能硬门槛, 右侧交易优先]
confidence: high
---

## 预测/假设
- 上证：预计反弹至 3350，量能不足 2.5 万亿
- 科创芯片：认为 1.16 是支撑位

## 实际结果
- 上证：跌至 3280，量能 1.8 万亿 ✅ 量能判断正确
- 科创芯片：1.159 入场 → 1.092 止损 ❌ 左侧猜底

## 偏差分析
- **根因**：违反了"量能<2.5万亿不参与反弹"的原则
- **触发因素**：盘前看到科创芯片利好，情绪上放弃了量能纪律
- **可避免吗**：可以。如果严格执行盘前决策树，不会入场

## 规则修正
- [新增] `量能不足时，即使有技术面信号也不入场`
- [强化] `右侧交易优先：等量能确认+止跌反转`
- [废弃] (none)

## 关联规则
- 查看 `MEMORY.md §交易纪律` → 规则已更新
- 影响持仓：588200 已止损，暂无持仓违反此规则
```

### 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| 预测/假设 | 是 | 入场前的判断，尽量量化 |
| 实际结果 | 是 | 实际走势，标记 ✅/❌/⚠️ |
| 偏差分析 | 是 | 诚实归因：根因 + 触发因素 + 可避免性 |
| 规则修正 | 是 | 本次修正的规则，[新增]/[强化]/[废弃] |
| 关联规则 | 否 | 影响的持仓、其他规则条目 |

---

## 领域模板：Amazon 广告（amazon-ad）

路径：`工作/记忆管理/广告记忆/YYYY-MM-DD-广告记忆.md`

### Body 结构

```markdown
---
type: domain-memory
domain: amazon-ad
created: 2026-07-28
tags: [广告策略, ACOS, 否定词, 竞价]
related: ["[[2026-W30 广告分析]]"]
rules: [否定词优先级, 品牌广告加权]
confidence: high
---

## 策略/假设
- 搜索词 "wireless charger" ACOS 180%，认为应直接否定
- 品牌广告预算从 $50/天 提到 $80/天，预计 ROAS 提升 20%

## 实际效果
- "wireless charger" 否定后，该 ASIN 整体 ACOS 从 45% 降至 32% ✅
- 品牌广告预算提升后 ROAS 从 2.1 降到 1.8 ❌

## 偏差分析
- **根因**：品牌广告预算增加后进入了更宽泛的受众，转化率下降
- **教训**：品牌广告不应当单纯提预算，而应优化受众定向

## 规则修正
- [新增] `品牌广告预算调整前，先检查受众定向的精准度`
- [强化] `否定词优先级：P0(W4 ACOS>150%+花费>$20) > P1(...)`
- [废弃] (none)

## 影响的分析模板
- 广告分析报告模板已更新 §品牌广告章节
```

---

## 领域模板：Amazon Listing（amazon-listing）

路径：`工作/记忆管理/Listing记忆/YYYY-MM-DD-Listing记忆.md`

### Body 结构

```markdown
---
type: domain-memory
domain: amazon-listing
created: 2026-07-28
tags: [Listing优化, 标题, 关键词, 埋词]
related: ["[[B0DZCFQ3FH Listing分析]]"]
rules: [语义短语优先, 埋词密度]
confidence: medium
---

## 版本/策略
- 版本 A：标题 "Wireless Charger Fast Charging 15W for iPhone"
- 版本 B：标题 "15W Fast Wireless Charger for iPhone 15/14/13 - Qi Certified"

## 实际效果
- 版本 B 上架 2 周后，自然排名从 #85 升至 #42
- 版本 A → B 转化率提升 12%

## 偏差分析
- **成功归因**：版本 B 增加了具体型号 + "Qi Certified" 信任信号
- **意外发现**：加 "iPhone 15" 带来的流量远大于预期

## 规则修正
- [新增] `Listing 标题中必须包含至少 3 个具体兼容型号`
- [强化] `认证标识（Qi Certified / FCC）应放在标题后半段`
- [废弃] (none)
```

---

## 领域模板：Amazon 选品（amazon-selection）

路径：`工作/记忆管理/选品记忆/YYYY-MM-DD-选品记忆.md`

### Body 结构

```markdown
---
type: domain-memory
domain: amazon-selection
created: 2026-07-28
tags: [选品, 关键词, 市场容量, PPC]
related: ["[[2026-07-28 选品分析-WL]]"]
rules: [PPC门槛, 市场容量]
confidence: medium
---

## 假设/判断
- 关键词 "cargador inalámbrico" 月搜索量 8500，PPC $0.03
- 判断：低 PPC 但搜索量不足以支撑新品

## 实际验证
- 前 5 名 ASIN 平均月销 320 单，月搜索量 8500 → SPR 约 26
- 判断基本正确，但未考虑"品牌词引流"效应

## 偏差分析
- **不足**：只看了核心关键词搜索量，未考虑关联词聚合流量
- **修正**：选品时应计算"关键词组"聚合搜索量，而非单个词

## 规则修正
- [新增] `选品时按"关键词组"聚合搜索量，而非单个关键词`
- [强化] `PPC 极低 (<$0.10) 时要警惕：可能是市场本身不活跃`

## 影响的分析模板
- 选品报告模板已更新 §关键词聚合计算
```

---

## 通用模板：决策/经验（general）

不绑定特定领域，记录跨领域的通用经验。

路径：`通用/决策记忆/YYYY-MM-DD-决策记忆.md`

```markdown
---
type: domain-memory
domain: general
created: 2026-07-28
tags: [方法论, 决策, 反思]
related: []
rules: []
confidence: medium
---

## 情境
- 在做 {某事} 时，发现 {某情况}

## 发现
- {具体发现}

## 影响
- 此经验适用于：{场景列表}
- 不适用于：{排除场景}

## 下次应用
- 做 {某类事} 之前，先问自己：{检查问题}
```

---

## 文件目录结构总览

```
D:/OneDrive/ObsidianVault/
├── 交易体系/
│   ├── 每日复盘/          ← 已有
│   ├── 盘前预测/          ← 已有
│   ├── 交易计划/          ← 已有
│   └── 交易记忆/          ← 新增
│       ├── 2026-07-28-交易记忆.md
│       └── 2026-07-29-交易记忆.md
├── 工作/
│   └── 记忆管理/          ← 新增
│       ├── 广告记忆/       ← Amazon 广告记忆
│       ├── Listing记忆/    ← Amazon Listing 记忆
│       └── 选品记忆/       ← Amazon 选品记忆
└── 通用/
    └── 决策记忆/          ← 新增
```

---

## 检索接口

当需要查询记忆时，按以下逻辑：

1. **按领域 + 标签**：`grep "domain: trading" 交易记忆/*.md | grep "tags:.*量能"`
2. **按时间范围**：文件命名 `YYYY-MM-DD`，按文件名排序即可
3. **按关联规则**：`grep "rules: /[量能硬门槛" 交易记忆/*.md`
4. **跨域搜索**：`grep "tags:.*止损" 交易记忆/*.md 广告记忆/*.md 选品记忆/*.md`