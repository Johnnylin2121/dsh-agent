#!/usr/bin/env node
// dsh-xueqiu 插件修复补丁 reapply 脚本（2026-09-01，v2：纳入浮窗隐藏补丁）
//
// 背景：本机 Windows schannel TLS 损坏（SEC_E_NO_CREDENTIALS 0x8009030e），
// 插件原先经 shell.run("curl.exe") 访问雪球全部失败（curl exit 35 http=000）。
// 已手工将 curl()/ensureCookie() 改为宿主原生 fetch（Node/undici，走 OpenSSL）。
// v2（2026-09-01）：浮窗徽章隐藏（shell.overlay 渲染 null）+ 面板入口改为输入框上方小按钮。
// 插件更新或 DSH 重装会还原 node_modules，本脚本把 .patched 版本重新铺回。
//
// 用法：
//   node patch-xueqiu.mjs          # 幂等：已打补丁则跳过，版本变化则警告
//   node patch-xueqiu.mjs --force  # 无视版本差异强制覆盖
//   node patch-xueqiu.mjs --check  # 仅检查状态
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const HOME = process.env.USERPROFILE || process.env.HOME
const PLUGIN = path.join(HOME, '.dsh', 'profiles', 'web', 'node_modules', 'dsh-xueqiu')
const BACKED_VERSION = JSON.parse(fs.readFileSync(path.join(__dirname, 'package.json.bak'), 'utf8')).version
const SENTINEL = '本机 patch 2026-09-01'

const targets = [
  { name: 'src/index.js', patched: 'src-index.js.patched' },
  { name: 'dynamic/host.js', patched: 'dynamic-host.js.patched' },
  { name: 'src/client/index.js', patched: 'client-src-index.js.patched' },
  { name: 'dynamic/client.js', patched: 'client-dynamic.js.patched' },
]

const force = process.argv.includes('--force')
const checkOnly = process.argv.includes('--check')

function status() {
  for (const t of targets) {
    const f = path.join(PLUGIN, t.name)
    if (!fs.existsSync(f)) { console.log(`MISSING ${t.name}`); continue }
    const src = fs.readFileSync(f, 'utf8')
    console.log(`${src.includes(SENTINEL) ? 'PATCHED  ' : 'VANILLA  '} ${t.name}`)
  }
}

if (checkOnly) { status(); process.exit(0) }

let version
try { version = JSON.parse(fs.readFileSync(path.join(PLUGIN, 'package.json'), 'utf8')).version } catch { version = null }
if (version !== BACKED_VERSION) {
  const msg = `⚠️ 插件版本变化：备份时 ${BACKED_VERSION}，当前 ${version || '未知'}。`
  if (!force) { console.log(msg + ' 已跳过（避免破坏新版代码）。确认后可用 --force 覆盖。'); process.exit(2) }
  console.log(msg + ' 用户确认 --force，继续覆盖。')
}

let changed = 0
for (const t of targets) {
  const f = path.join(PLUGIN, t.name)
  if (!fs.existsSync(f)) { console.log(`SKIP ${t.name}（不存在，可能插件已卸载）`); continue }
  const cur = fs.readFileSync(f, 'utf8')
  if (cur.includes(SENTINEL)) { console.log(`SKIP ${t.name}（已打补丁）`); continue }
  fs.copyFileSync(path.join(__dirname, t.patched), f)
  console.log(`PATCH ${t.name} ✓`)
  changed++
}
console.log(changed ? `完成：${changed} 个文件已铺回。重启 DSH web 宿主生效。` : '无需修改。')