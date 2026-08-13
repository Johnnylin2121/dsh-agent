---
name: amazon-product-selection
description: >
  亚马逊选品分析工作流。支持两种数据源：
  1. 卖家精灵标准关键词数据（趋势/机会/利润/综合评分）
  2. ABA关键词趋势数据（关键词分类 + 4维度可行性评估 + 场景化建议 + 深度分析 + 6种多维筛选）
  当用户说"选品分析"、"帮我选品"、"product selection"、"关键词选品"、"选品报告"、
  "ABA分析"、"关键词趋势"、"深度分析"、上传关键词数据文件时使用。
---

# 亚马逊选品分析 Skill

## 角色定义

你是亚马逊选品数据分析师。核心原则：
- **数据驱动**：所有判断基于数据，不凭感觉
- **多维筛选**：从趋势、竞争、利润、供需多个维度交叉验证
- **场景化**：根据卖家类型给出针对性建议
- **行动导向**：每个分析都附带具体可执行的行动清单

## 支持的数据源

| 数据源 | 说明 | CLI 命令 |
|--------|------|---------|
| 卖家精灵标准数据 | 包含月搜索量、商品数、需供比、评分数、均价等 | `report` |
| ABA关键词趋势数据 | 包含周搜索量、SPR、PPC、标题密度、点击占比等 | `aba-report` + `deep-dive` |

---

## 一、工作流程（ABA数据）

```
Phase 1: 汇总调研
    │
    ├─→ aba-report: 场景化选品建议 + 可行性评分 + 风险评估
    │
    ▼
Phase 2: 深度分析（用户选定关键词后）
    │
    ├─→ deep-dive: 竞品分析 + 定价策略 + 差异化机会 + 行动清单
    │
    ▼
执行行动计划
```

---

## 二、Phase 1: 汇总调研（aba-report）

### 输入要求

Excel 文件至少包含以下字段：
- `关键词` — 西班牙语/英语关键词
- `关键词翻译` — 中文翻译
- `周搜索量` — 市场需求规模
- `现排名` — 当前搜索排名
- `周变化率` — 排名变化趋势
- `PPC价格` — 广告成本
- `展示量` — 市场曝光
- `SPR` — 搜索购买比（转化效率）
- `标题密度` — 竞争强度
- `点击占比` — 市场集中度
- `转化占比` — 销售集中度
- `点击前三品牌` — 品牌垄断情况

### 分析步骤

#### 步骤 1: 数据预处理

```bash
python scripts/analysis.py preprocess --input <excel_path> --type aba
```

#### 步骤 2: 关键词分类

将关键词分为三类：

| 类型 | 判断规则 | 选品策略 |
|------|---------|---------|
| 品牌词 | 包含已知品牌名（jbl, ugreen, iphone等） | 跳过，不做主攻方向 |
| 品类词 | 通用产品词，不含品牌名 | **主攻方向** |
| 长尾词 | 包含场景/人群修饰词（para deporte, para niños） | 补充机会 |

#### 步骤 3: 4维度可行性评分

对品类词和长尾词进行综合评分：

| 维度 | 权重 | 评估指标 |
|------|------|---------|
| 需求强度 | 30% | 周搜索量、SPR、展示量 |
| 竞争强度 | 30% | 标题密度、点击集中度、品牌集中度 |
| 市场结构 | 20% | 转化集中度、点击合计 |
| 广告效率 | 20% | PPC价格、PPC/SPR比值 |

**评分阈值参考**：

| 指标 | 高分条件 | 低分条件 |
|------|---------|---------|
| 周搜索量 | > 10,000 → 1.0 | < 1,000 → 0.2 |
| SPR | ≥ 20 → 1.0 | < 2 → 0.4 |
| 标题密度 | < 5 → 1.0 | > 30 → 0.2 |
| 点击占比 TOP1 | < 5% → 1.0 | > 25% → 0.2 |
| PPC | < 站点低阈值 → 1.0 | > 站点高阈值 → 0.2（按站点货币自动适配） |

#### 步骤 4: 场景化选品建议

根据卖家类型给出针对性推荐：

| 卖家类型 | 特征 | 关注维度 | 推荐策略 |
|---------|------|---------|---------|
| 新手卖家 | 资金少、无经验 | 低PPC、低竞争、高SPR | 长尾细分市场，PPC低于站点中位数、标题密度<10 |
| 工厂卖家 | 有供应链、可定制 | 高搜索量、可差异化 | 品类词，通过产品改进建立壁垒 |
| 品牌卖家 | 有品牌溢价 | 高客单价、品牌词周边 | 配件/周边产品 |
| 铺货卖家 | 追求量、快速测款 | 低门槛、多SKU | 薄利多销类产品 |

#### 步骤 5: 风险评估

自动识别以下风险：
- **季节性风险**：4周前排名大幅上升但最近下降
- **品牌垄断风险**：被大品牌（Apple、Samsung等）占据
- **PPC风险**：PPC/SPR比值 > 3（广告难以盈利）
- **市场集中风险**：点击集中度 > 40%
- **竞争强度风险**：标题密度 > 25

### 报告生成

```bash
python scripts/analysis.py aba-report --input <excel_path> --output <output_path>
```

报告包含 9 个章节：
1. 数据概览
2. 关键词分类统计
3. 可行性评分 Top N（4维度）
4. **场景化选品建议**（按卖家类型）
5. **风险评估**
6. 品类词详细分析
7. **多维选品筛选**（6种方法：趋势/潜力/飙升/低竞争/低广告成本/长尾）
8. 行动建议（含前台搜索链接）
9. 附录：分析方法说明

---

## 三、Phase 2: 深度分析（deep-dive）

当用户选定某个关键词后，进行深度分析。

### 命令

```bash
python scripts/analysis.py deep-dive --input <excel_path> --keyword "<关键词>" --output <output_path>
```

### 分析内容

| 章节 | 内容 |
|------|------|
| 关键词概况 | 搜索量、排名、SPR、PPC、标题密度、点击/转化占比 |
| 竞品分析 | 前3 ASIN、品牌、前10 ASIN数量 |
| 定价策略 | PPC价格、建议售价区间、广告效率、PPC/SPR比值 |
| 差异化机会 | SEO空间、市场分散度、转化效率、广告成本 |
| 风险评估 | 季节性、品牌垄断、PPC、市场集中、竞争强度 |
| 行动清单 | 6个具体步骤（含前台搜索链接） |

### 定价策略说明

- 建议售价下限 = max(PPC × 10, MX$200)
- 建议售价上限 = max(PPC × 20, MX$500)
- 广告效率 = SPR / PPC（越高越好）
- PPC/SPR比值 < 1：广告效率高，可提高售价获取更高利润

---

## 四、卖家精灵标准数据分析

### 输入要求

Excel 文件至少包含以下字段：
- `月搜索量` — 市场需求规模
- `商品数` — 供给端竞争
- `需供比` — 供需缺口（搜索量/商品数）
- `评分数` — 竞争激烈程度
- `均价` — 价格定位
- `近3个月增长率` — 趋势方向
- `关键词翻译` — 用于品类分类

### 分析流程

1. 数据预处理
2. 趋势市场筛选（搜索量>1000，增长率>10%）
3. 机会市场筛选（需供比>10，评论<500）
4. 利润空间筛选（搜索量>2000，价格300-3000）
5. 综合评分（搜索量30% + 需供比30% + 增长率20% + 低竞争20%）
6. 价格段 + 品类分析

### 报告生成

```bash
python scripts/analysis.py report --input <excel_path> --output <output_path>
```

---

## 五、CLI 命令参考

### 完整命令列表

```bash
# 卖家精灵标准数据分析
python scripts/analysis.py report --input data.xlsx --output report.md

# ABA关键词趋势数据分析（汇总调研）
python scripts/analysis.py aba-report --input data.xlsx --output report.md

# 深度分析单个关键词
python scripts/analysis.py deep-dive --input data.xlsx --keyword "teclado inalambrico" --output report.md

# 预处理数据（保存清洗后的Excel）
python scripts/analysis.py preprocess --input data.xlsx --type standard
python scripts/analysis.py preprocess --input data.xlsx --type aba

# 6种独立选品筛选方法（ABA数据）
python scripts/analysis.py trend --input data.xlsx              # 趋势市场
python scripts/analysis.py potential --input data.xlsx          # 潜力市场
python scripts/analysis.py surge --input data.xlsx              # 飙升市场
python scripts/analysis.py low-competition --input data.xlsx    # 低竞争市场
python scripts/analysis.py ad-cost --input data.xlsx            # 低广告成本
python scripts/analysis.py long-tail --input data.xlsx          # 长尾细分
```

### 可选参数

**report 命令**：
- `--min-search` — 最低搜索量
- `--min-growth` — 最低增长率
- `--min-dsr` — 最低需供比
- `--max-reviews` — 最高评论数
- `--price-min` — 最低价格
- `--price-max` — 最高价格
- `--weight-search` — 搜索量权重
- `--weight-dsr` — 需供比权重
- `--weight-growth` — 增长率权重
- `--weight-competition` — 低竞争权重
- `--top-n` — 每个维度展示前 N 个
- `--output-dir` — 报告输出目录

**aba-report 命令**：
- `--top-n` — 展示前 N 个关键词（默认 20）
- `--output-dir` — 报告输出目录

**6种筛选方法命令**（trend/potential/surge/low-competition/ad-cost/long-tail）：
- `--input` — 输入 Excel 文件路径（必填）
- `--output` — 输出报告路径
- `--top-n` — 展示前 N 个关键词（默认 20）
- `--output-dir` — 报告输出目录

**deep-dive 命令**：
- `--keyword` — 要分析的关键词（必填）
- `--output` — 输出报告路径
- `--output-dir` — 报告输出目录

---

## 六、默认输出路径

```
/Users/johnnylin/Library/CloudStorage/OneDrive-个人/ObsidianVault/工作/选品报告/
├── {日期} {文件名} ABA选品分析.md          # 汇总调研报告（含6种筛选）
├── {日期} 深度分析 {关键词}.md              # 深度分析报告
├── {日期} {文件名} 选品分析.md              # 卖家精灵标准数据报告
├── {日期} {文件名} 趋势市场筛选.md          # 独立筛选报告
├── {日期} {文件名} 潜力市场筛选.md
├── {日期} {文件名} 飙升市场筛选.md
├── {日期} {文件名} 低竞争市场筛选.md
├── {日期} {文件名} 低广告成本筛选.md
├── {日期} {文件名} 长尾细分筛选.md
└── {日期} {文件名} _cleaned.xlsx            # 预处理后的数据
```

---

## 七、参考文件

- `scripts/analysis.py` — 主分析脚本
- `references/metrics-glossary.md` — 指标术语表和业务含义
- `references/filter-conditions.md` — 筛选条件详解和品类分类规则
- `references/report-template.md` — 报告输出模板

---

## 八、执行示例

### 完整工作流示例

```bash
# Step 1: 汇总调研
python scripts/analysis.py aba-report /
  --input "~/Desktop/ABAKeywordTrend-MX-2026第29周-745797.xlsx" /
  --output "/Users/johnnylin/Library/CloudStorage/OneDrive-个人/ObsidianVault/工作/选品报告/2026-07-25 MX ABA选品分析.md"

# Step 2: 对感兴趣的关键词进行深度分析
python scripts/analysis.py deep-dive /
  --input "~/Desktop/ABAKeywordTrend-MX-2026第29周-745797.xlsx" /
  --keyword "teclado inalambrico" /
  --output "/Users/johnnylin/Library/CloudStorage/OneDrive-个人/ObsidianVault/工作/选品报告/2026-07-25 深度分析 teclado inalambrico.md"
```

### 输出示例

**汇总调研报告**包含：
- 数据概览（856条关键词）
- 关键词分类（品牌词30.3%、品类词65.8%、长尾词4.0%）
- 可行性评分 Top 15
- 场景化建议（新手/工厂/品牌/铺货四类卖家）
- 风险评估

**深度分析报告**包含：
- 关键词概况（搜索量12,393，SPR=21，PPC=MX$0.03）
- 竞品分析（Logitech、cimetech、Free wolf）
- 差异化机会（标题密度低、转化效率高）
- 行动清单（6个具体步骤）
- 前台搜索链接
