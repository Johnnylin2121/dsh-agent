#!/usr/bin/env node
// dsh-rss-digest 补丁 reapply 脚本（2026-09-13）
//
// 背景：DSH 宿主进程内 fetch Response 的 .body 流 getter 为 null（流式读取不可用），
// 同根因见 dsh-xueqiu 补丁（xueqiu 已改用 res.text()）。dsh-rss-digest 的
// lib/fetcher.js readBody() 对 body===null 返回空串 → 解析报
// "document contains no root element"，rss_fetch 永久失败。
// 修复：fetchOne 中 body 为 null 时退回 await response.text()。
// 插件更新/重装会还原 node_modules，本脚本把 .patched 版本重新铺回。
//
// 用法：
//   node patch-rss-digest.mjs          # 幂等：已打补丁则跳过，版本变化则警告
//   node patch-rss-digest.mjs --force  # 无视版本差异强制覆盖
//   node patch-rss-digest.mjs --check  # 仅检查状态
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const HOME = process.env.USERPROFILE || process.env.HOME
const PLUGIN = path.join(HOME, '.dsh', 'profiles', 'web', 'node_modules', 'dsh-rss-digest')
const SENTINEL = '本机 patch 2026-09-13'
const TARGET = 'lib/fetcher.js'

function status() {
  const f = path.join(PLUGIN, TARGET)
  if (!fs.existsSync(f)) { console.log(`MISSING ${TARGET}`); return }
  console.log(`${fs.readFileSync(f, 'utf8').includes(SENTINEL) ? 'PATCHED  ' : 'VANILLA  '} ${TARGET}`)
}

const force = process.argv.includes('--force')
const checkOnly = process.argv.includes('--check')
if (checkOnly) { status(); process.exit(0) }

let version
try { version = JSON.parse(fs.readFileSync(path.join(PLUGIN, 'package.json'), 'utf8')).version } catch { version = null }
if (version !== '0.1.0' && !force) {
  console.log(`⚠️ 插件版本变化：备份时 0.1.0，当前 ${version || '未知'}。已跳过（确认后用 --force 覆盖）。`)
  process.exit(2)
}

const f = path.join(PLUGIN, TARGET)
if (!fs.existsSync(f)) { console.log(`SKIP ${TARGET}（不存在，可能插件已卸载）`); process.exit(0) }
if (fs.readFileSync(f, 'utf8').includes(SENTINEL)) { console.log(`SKIP ${TARGET}（已打补丁）`); process.exit(0) }
fs.copyFileSync(path.join(__dirname, 'fetcher.js.patched'), f)
console.log(`PATCH ${TARGET} ✓ 完成。重启 dsh web 宿主生效。`)
