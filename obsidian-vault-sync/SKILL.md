---
name: obsidian-vault-sync
description: 自动将文件同步到Obsidian知识库，包括复制文件、创建/更新wiki entities和topics。Use when user says "添加到知识库", "同步到Obsidian", "更新wiki", "把文件放到vault里", "归档", "添加到vault", or asks to organize files into the knowledge base.
---
⚠️ **OneDrive 同步提醒**：本 skill 写入的 Vault 位于 OneDrive，大量/频繁写入可能触发同步延迟与文件锁，建议分批操作。
# Obsidian Vault Sync

自动将文件同步到Obsidian知识库，完成文件复制、entity创建/更新、topic关联更新。

## 工具优先级（已安装 dsh-obsidian 插件后适用）

若检测到 `obsidian_*` 原生工具已注册（dsh-obsidian 插件），本 skill 的 Vault 读写**优先使用原生工具**，pwsh/文件工具降级为兜底：

| 操作 | 优先工具 | 兜底 |
|------|---------|------|
| 全文检索/定位笔记 | `obsidian_search` | grep/glob |
| 读取笔记（正文+frontmatter） | `obsidian_read` | read |
| 新建/覆盖笔记（含自动建父目录） | `obsidian_write` | write |
| 追加内容（如实体动态追加） | `obsidian_append` | edit 追加 |
| 移动/重命名（自动同步 `[[链接]]`） | `obsidian_move` | fs 移动 |
| 删除 | `obsidian_delete`（移入 `.trash/` 可逆） | 不可逆删除【禁用】 |
| 断链检查（Step 6） | `obsidian_backlinks` + `obsidian_search` | 手动 grep `[[` |
| 标签汇总 | `obsidian_tags` | 手动统计 |
| frontmatter 读写 | `obsidian_frontmatter` / `obsidian_set_property` | 手工编辑 YAML |

**规则**：
- 路径参数一律相对 vault 根（如 `wiki/entities/证监会.md`），工具自会防越界。
- 删除一律用 `obsidian_delete`（进 `.trash/`），绝不永久删除——符合"历史文件必须保留"规则。
- `obsidian_*` 工具不可用时才走 pwsh/文件工具路径，并按本文件原有 {VAULT_PATH} 逻辑执行。
- 无论用哪种工具，OneDrive 批量写入仍须分批，避免触发同步锁。

## 触发条件

用户说以下任一短语时触发：
- "添加到知识库"
- "同步到Obsidian"
- "更新wiki"
- "把文件放到vault里"
- "归档"
- "添加到vault"

## 工作流程

### Step 0: 领域路由（新增）

根据源文件所在目录，判定目标知识网络：

| 源文件位置 | 目标知识网络 | 实体/主题写入位置 | 索引 |
|-----------|-------------|------------------|------|
| `交易体系/`、`附件/1.Mr.dang`、`研究/` | 交易体系 | `wiki/entities/`、`wiki/topics/` | `wiki/index.md` |
| `工作/` | 工作领域 | `wiki-work/entities/`、`wiki-work/topics/` | `wiki-work/index.md` |
| `读书/` | 读书领域 | `wiki-reading/entities/`、`wiki-reading/topics/` | `wiki-reading/index.md` |
| 不确定 | 询问用户 | — | — |

**规则：绝不跨域写入**。交易资料只写 `wiki/`，工作资料只写 `wiki-work/`，读书资料只写 `wiki-reading/`。`related:` 中的 `[[wikilink]]` 可跨域引用。

### Step 1: 确定源文件和目标位置

读取用户提供的文件路径，根据文件名判断类型：

| 文件名模式 | 目标位置 |
|-----------|---------|
| `*财经早读*` 或 `*财经早餐*` | `交易体系/财经早读/` + `附件/2.财经早读/` + `wiki/sources/` |
| `*复盘*` | `交易体系/复盘/` |
| 其他 | 按 Step 0 领域路由，或询问用户目标位置 |

### Step 2: 复制文件

```
# MD文件 → 交易体系/财经早读/YYYY-MM-DD-财经早读.md
# DOCX文件 → 附件/2.财经早读/YYYY年M月D日财经早餐.docx
# 同时创建wiki source文件 → wiki/sources/YYYY-MM-DD-财经早读-关键词.md
```

### Step 3: 解析内容，提取关键词

从文件内容中提取：
- **公司名**：如"华友钴业"、"三一重工"、"中国建筑"
- **人名/机构**：如"证监会"、"花旗"、"DeepSeek"
- **主题**：如"回购增持"、"科技股"、"大宗商品"
- **事件**：如"胡塞武装禁运"、"V4峰谷定价"

### Step 4: 更新 `{知识网络}/entities`

根据 Step 0 确定的目标知识网络（`wiki/`、`wiki-work/` 或 `wiki-reading/`），对每个提取的关键词：

1. 检查 `{知识网络}/entities/{关键词}.md` 是否存在
2. **存在**：更新frontmatter中的`sources`和`updated`字段，添加新的引用
3. **不存在**：创建新entity文件，包含：
   - frontmatter（type: entity, created, updated, tags, sources, related）
   - 基本信息
   - 近期动态（从文件内容提取）

### Step 5: 更新 `{知识网络}/topics`

对每个提取的主题：

1. 检查 `{知识网络}/topics/{主题}.md` 是否存在
2. **存在**：更新frontmatter中的`sources`和`updated`字段，添加新的引用
3. **不存在**：创建新topic文件，包含：
   - frontmatter（type: topic, created, updated, tags, sources, related）
   - 概述
   - 关联

### Step 6: 操作后验证（强制）

在生成报告前，**必须**对本次操作的目标知识网络执行自检。验证清单（参考 AGENTS.md 步骤 3.5）：

1. **断链检查** — 本次新建/修改的页面中，所有 `[[wikilink]]` 是否指向已存在页面
   - 跨域解析：先查当前域，再查其他域
   - 目标不存在 → 创建该实体/主题页，或去掉 `[[]]`
2. **Index 同步** — 检查对应域的 index.md 是否包含所有新建页面
   - 交易 → `wiki/index.md`；工作 → `wiki-work/index.md`；读书 → `wiki-reading/index.md`
3. **格式合规** — 新建资源文件是否符合标准格式
4. **Frontmatter** — 新建页面是否含 `type/created/updated/tags`

发现可自动修复的问题 → 立即修复并记录；需人工判断的 → 在报告中标注。

### Step 7: 生成更新报告

输出完成的操作清单：
- 复制的文件列表
- 更新的entity文件列表
- 新建的entity文件列表
- 更新的topic文件列表
- 新建的topic文件列表

## Wiki文件格式参考

### Entity文件格式

```yaml
---
type: entity
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [标签1, 标签2]
sources: ["[[YYYY-MM-DD-财经早读-关键词]]"]
related: ["[[关联1]]", "[[关联2]]"]
---
⚠️ **OneDrive 同步提醒**：本 skill 写入的 Vault 位于 OneDrive，大量/频繁写入可能触发同步延迟与文件锁，建议分批操作。
# 实体名称

## 基本信息
- 行业：xxx
- 产业链：xxx

## 近期动态
### YYYY年M月：事件标题
- 事件描述

## 关联
- [[关联实体]]
```

### Topic文件格式

```yaml
---
type: topic
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [主题标签]
sources: ["[[YYYY-MM-DD-财经早读-关键词]]"]
related: [关联主题]
---
# 主题名称

## 概述
主题描述

## 近期动态
### YYYY-MM-DD 动态
- 动态内容

## 关联
- [[关联主题]]
```

## 文件命名规则

| 文件类型 | 命名格式 | 示例 |
|---------|---------|------|
| 财经早读(MD) | `YYYY-MM-DD-财经早读.md` | `2026-07-21-财经早读.md` |
| 财经早餐(DOCX) | `YYYY年M月D日财经早餐.docx` | `2026年7月21日财经早餐.docx` |
| Wiki Source | `YYYY-MM-DD-财经早读-关键词.md` | `2026-07-21-财经早读-监管政策与DeepSeek定价.md` |
| Entity | `{实体名称}.md` | `证监会.md` |
| Topic | `{主题名称}.md` | `科技股.md` |

## 错误处理

- **文件不存在**：提示用户确认文件路径
- **目标目录不存在**：自动创建目录
- **Entity已存在**：追加更新sources字段，不覆盖现有内容
- **关键词提取失败**：询问用户提供关键词列表

## 示例

用户说："把这个文件添加到我的Obsidian知识库：~/Desktop/2026年7月21日财经早餐.md"

操作：
1. 读取文件内容
2. 复制MD到 `交易体系/财经早读/2026-07-21-财经早读.md`
3. 复制DOCX到 `附件/2.财经早读/2026年7月21日财经早餐.docx`
4. 创建 `wiki/sources/2026-07-21-财经早读-监管政策与DeepSeek定价.md`
5. 更新/创建entities: 证监会、DeepSeek、华友钴业、三一重工、中国建筑、花旗、胡塞武装、沙特
6. 更新/创建topics: 科技股、回购与分红策略、大宗商品
7. 输出更新报告