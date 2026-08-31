# dsh-agent

个人 DSH（DeepSeek Harness）技能与插件配置仓库。跨会话持久化，换机器一键恢复。

## 包含什么

### Skills（18 个）

| 类别 | 技能 | 用途 |
|------|------|------|
| **交易** | `trading-daily-review` | A股每日复盘全流程（盘前→盘中→盘后） |
| | `trading-contradiction-check` | 盘后矛盾检测（预判vs实际、持仓逻辑一致性） |
| | `trading-policy-impact` | 政策/事件影响链路分析 |
| | `trading-stock-scan` | 个股深度研究（公告/评级/资金/技术面） |
| | `trading-value-investing` | 价值投资体系（Mr.Dang功法） |
| | `briefing-fetch` | 财经早报数据抓取（akshare商品/美股/快讯→标准md草稿，六类关注方向规则初筛+LLM终筛） |
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

> 2026-08 已移除：`notion-api`（macOS/zsh+jq+curl 写法，Windows 全链不可用；Notion 写入已由 trading-daily-review 内置集成承担）。

### Plugins（备份）

`plugins/` 目录备份 DSH web profile 的插件配置，含一键恢复脚本。

当前插件：`dsh-plugin-deepeye`（视觉）· `dsh-peak-cost-mode`（高峰省流）· `dsh-find-plugin` · `dshmarket` · `dsh-xueqiu` · `dsh-obsidian` · `dsh-context-doctor` · `@dickpy/dsh-imagegen`（生图）· `@liustack/modsearch`（网页/X读取）· `@vectorize-io/hindsight-coding-agents`（记忆）等。

### 共享工具

`_shared/dsh-market.mjs` — 轻量市场数据获取工具（替代curl，规避Windows Schannel问题）。

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
