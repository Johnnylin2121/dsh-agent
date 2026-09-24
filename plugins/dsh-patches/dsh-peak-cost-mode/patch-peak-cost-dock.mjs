// patch-peak-cost-dock.mjs — 隐藏 dsh-peak-cost-mode 底部状态条（composer.dock）
// 背景：底部状态条「低谷 ×1 · 正常输出 · 上次高峰省 ≈¥…」与 token 统计、雪球指数条挤在一行，
//       文字重叠截断（2026-09-24 用户反馈）。只隐藏底部条，会话标题入口 + 收益报告面板保留。
// 幂等：已打过则 SKIP。pnpm 重装插件后需重跑（也可跑 skills/plugins/dsh-patches/reapply-all.ps1）。
// 用法：node patch-peak-cost-dock.mjs [--check]

import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'

const SENTINEL = '.peak-cost-dock{display:none !important;}'
const ANCHOR = "'.peak-cost-report h3{"
const target = join(homedir(), '.dsh', 'profiles', 'web', 'node_modules', 'dsh-peak-cost-mode', 'client.js')
const checkOnly = process.argv.includes('--check')

if (!existsSync(target)) {
  console.log('SKIP  peak-cost    插件未安装')
  process.exit(0)
}

const src = readFileSync(target, 'utf8')

if (src.includes(SENTINEL)) {
  console.log('PATCHED  peak-cost  已是补丁版')
  process.exit(0)
}

if (!src.includes(ANCHOR)) {
  console.log('FAIL  peak-cost    找不到锚点，插件结构已变，需人工处理')
  process.exit(1)
}

if (checkOnly) {
  console.log('VANILLA peak-cost  未打补丁')
  process.exit(0)
}

const out = src.replace(
  ANCHOR,
  "      // 本机 patch 2026-09-01：隐藏底部状态条（composer.dock 里的「低谷 ×1 · 正常输出…」），\n" +
  '      // 避免与 token 统计/指数条挤在一行导致文字重叠截断。会话标题区入口与收益报告面板不受影响。\n' +
  "      '" + SENTINEL + "',\n      " + ANCHOR
)
writeFileSync(target, out, 'utf8')
console.log('PATCHED  peak-cost  已隐藏底部状态条')
