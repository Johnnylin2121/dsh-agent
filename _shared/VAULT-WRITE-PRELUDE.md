# 统一 vault 写入前置（2026-09-30 加入全部写 vault 的 skill）
# 原因：vault 在 09-28/09-30 两次重组后，skill 文档里的路径大面积失效，
# 而写 vault 的 skill 没有一个要求先读 vault 自己的写入规范——
# 规范存在但无人读，等于不存在。审计时 22 个 skill 中 0 个提到它。

> ## ⚠️ 写入 vault 前必做（AGENTS 硬规则，优先于本 skill 下文任何旧表述）
>
> 1. **先读规范**：`{VAULT_PATH}/_系统/管理规则/AGENTS.md`
>    （注意路径——旧位置 `_系统/AGENTS.md` 已随 2026-09-28 重组失效）
> 2. **再核对路径**：本 skill 里写的 vault 路径可能已过期。
>    落盘前用 `node ~/.dsh/skills/tools/vault-path-check-external.mjs` 验一遍，
>    或直接 `Test-Path` 确认目标目录存在——**不要因为"路径看起来对"就 mkdir**。
> 3. **写完记审计**：在 `{VAULT_PATH}/_系统/日志/log.md` 追加一条，含七字段：
>    写入者身份 / 带时区时间 / 操作 / 目标 / 来源 / 摘要 / 验证。
>    旧路径 `_系统/log.md` 已失效，正确是 `_系统/日志/log.md`。
> 4. **文件签名**：新建的 vault 文档首行下方写 `[agent: DSH | <ISO8601 带时区>]`。
>    签名缺失 = 违规，**与内容对错无关**。
