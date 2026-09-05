# DSH 插件本地补丁备份（dsh-patches）

- **来源**：`E:\3.deepseek-harness\.dsh-patches`（本机工作区，不受 git 管理，本目录为唯一异地副本）
- **备份时间**：2026-09-05 · 59 个文件 · 1.7 MB
- **已排除**：`node_modules`（可重装；且源目录内为 pnpm 循环 junction，整树复制会死循环，重新备份时务必排除）

## 共同背景：本机 schannel TLS 损坏

本机 Windows schannel 报 `SEC_E_NO_CREDENTIALS (0x8009030e)`，一切经 shell 调 `curl.exe` 的 HTTPS 请求全部失败（curl exit 35 / http 000）。受影响插件的统一修法：**改用宿主原生 fetch（Node/undici，OpenSSL 栈）**。同源规避工具还有 `../../_shared/dsh-market.mjs`（轻量市场数据获取）。

## context-doctor-0.6.1/ — dsh-context-doctor 本地补丁版

- **来历**：[Zhenyu98/dsh-context-doctor](https://github.com/Zhenyu98/dsh-context-doctor)（0.6.1）的完整本地副本 + 补丁。目录名沿用上游版本号；`package.json` 的 `version` 本地改为 `0.6.2`，作为补丁版标识。
- **改动**：客户端 web 请求改为宿主原生 `fetch()`——src 侧 `client/ContextAuditRing.tsx`（及 client 入口）与 lib 构建产物 `lib/client/ContextAuditRing.js`、`lib/client.js` 同步修改。
- **接入方式**：profile `dependencies` 用 `link:` 指向工作区路径 `link:E:/3.deepseek-harness/.dsh-patches/context-doctor-0.6.1`（见 `../package.json`）。
- **恢复新机**：① 整目录拷回新机 `<workspace>\.dsh-patches\context-doctor-0.6.1`；② 在该目录 `pnpm install` 重建 node_modules；③ 跑 `../restore-plugins.ps1`（脚本会原样传 `link:` spec）。或临时改回 git 源 `github:Zhenyu98/dsh-context-doctor#main`（会丢上述补丁）。

## dsh-xueqiu/ — dsh-xueqiu 就地补丁

- **来历**：对已安装 `dsh-xueqiu@1.22.13`（`package.json.bak` 记录备份时版本）的就地补丁，改的是 profile `node_modules` 内的安装产物，上游仓库无这些改动。
- **v1**：`curl()` / `ensureCookie()` 改宿主原生 fetch（TLS 规避）。
- **v2（2026-09-01）**：浮窗徽章隐藏（`shell.overlay` 渲染 null）+ 面板入口改为输入框上方小按钮。
- **文件对应**：

| 补丁文件 | 铺回目标（`~/.dsh/profiles/web/node_modules/dsh-xueqiu/` 内） |
| --- | --- |
| `src-index.js.patched` | `src/index.js` |
| `dynamic-host.js.patched` | `dynamic/host.js` |
| `client-src-index.js.patched` | `src/client/index.js` |
| `client-dynamic.js.patched` | `dynamic/client.js` |

- **哨兵**：补丁文件内含 `本机 patch 2026-09-01` 标识，防重复铺。
- **铺回**：`node patch-xueqiu.mjs`（幂等；`--check` 仅检查状态；插件版本与 `package.json.bak` 不一致时拒绝执行，确认后 `--force`）。
- **状态**：备份版本 1.22.13 = 当前安装版本，补丁现行有效。

## 维护约定

- `dsh-xueqiu` 插件升级后需重新核对补丁：版本号变化直接 `--force` 铺回；上游代码大改则需重新做补丁（对照本目录 `.patched` 文件与新版源码重做差异）。
- 若上游以原生方式修复 TLS 请求路径（或本机 schannel 恢复正常），可退役对应补丁，回退 npm/github 源安装。
- 重新备份本目录时：用 `robocopy /E /XJ /XD node_modules`，禁止 `Copy-Item -Recurse` 整树复制。
