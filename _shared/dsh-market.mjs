#!/usr/bin/env node
/**
 * dsh-market.mjs — node-fetch 版行情取数工具（替代 curl，绕开 schannel 出站 TLS 故障）
 *
 * 用法（在 pwsh/bash 中）：
 *   node "$HOME/.dsh/skills/_shared/dsh-market.mjs" index [secids]        # 指数/多标的多字段
 *   node "$HOME/.dsh/skills/_shared/dsh-market.mjs" stocks "1.688017,0.300718"   # 个股（东财）
 *   node "$HOME/.dsh/skills/_shared/dsh-market.mjs" sector [pz]          # 板块资金流向（东财）
 *   node "$HOME/.dsh/skills/_shared/dsh-market.mjs" sina "sh600519,sz000001"     # 新浪实时（GBK）
 *   node "$HOME/.dsh/skills/_shared/dsh-market.mjs" kline "SH600519" [period=101] [limit=120] [fqt=1]
 *
 * 所有输出为纯文本/JSON，便于 agent 直接解析。node 用内置 OpenSSL 证书链，不受 Windows schannel 影响。
 */

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

async function jget(url, headers = {}) {
  const r = await fetch(url, { headers: { 'User-Agent': UA, ...headers }, signal: AbortSignal.timeout(15000) })
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`)
  const buf = Buffer.from(await r.arrayBuffer())
  return buf.toString('utf8')
}

function decodeGbk(buf) {
  try {
    return new TextDecoder('gbk').decode(buf)
  } catch {
    return buf.toString('latin1')
  }
}

async function cmdIndex(secidsArg) {
  const secids = secidsArg || '1.000001,0.399001,0.399006,1.000300,1.000688'
  const url = `https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&fields=f2,f3,f4,f6,f12,f14&secids=${secids}`
  const txt = await jget(url)
  const j = JSON.parse(txt)
  const rows = (j.data && j.data.diff) || []
  console.log(JSON.stringify(rows.map(r => ({
    code: r.f12, name: r.f14, price: r.f2, pct: r.f3, change: r.f4, amountYuan: r.f6,
  })), null, 0))
}

async function cmdStocks(secidsArg) {
  const secids = secidsArg || '1.688017,1.601689,0.300718,0.002050'
  const url = `https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&fields=f2,f3,f4,f5,f6,f7,f8,f10,f12,f14,f15,f16,f17,f18&secids=${secids}`
  const txt = await jget(url)
  const j = JSON.parse(txt)
  const rows = (j.data && j.data.diff) || []
  console.log(JSON.stringify(rows.map(r => ({
    code: r.f12, name: r.f14, price: r.f2, pct: r.f3, change: r.f4, high: r.f15, low: r.f16,
    open: r.f17, prevClose: r.f18, volume: r.f5, amountYuan: r.f6, turnoverPct: r.f8, volumeRatio: r.f10,
  })), null, 0))
}

async function cmdSector(pzArg) {
  const pz = pzArg || '20'
  const url = `https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=${pz}&po=1&np=1&fltt=2&invt=2&fid=f62&fs=m:90+t:2&fields=f12,f14,f62,f184,f3`
  const txt = await jget(url)
  const j = JSON.parse(txt)
  const rows = (j.data && j.data.diff) || []
  console.log(JSON.stringify(rows.map(r => ({
    code: r.f12, name: r.f14, mainInflowYuan: r.f62, mainInflowPct: r.f184, pct: r.f3,
  })), null, 0))
}

async function cmdSina(symbolsArg) {
  const sym = (symbolsArg || 'sh600519').replace(/\s+/g, '')
  const r = await fetch(`https://hq.sinajs.cn/list=${sym}`, {
    headers: { 'User-Agent': UA, 'Referer': 'https://finance.sina.com.cn/' },
    signal: AbortSignal.timeout(15000),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  const buf = Buffer.from(await r.arrayBuffer())
  const text = decodeGbk(buf)
  const out = []
  for (const line of text.split('\n').filter(Boolean)) {
    const m = line.match(/var hq_str_(\w+)="([^"]*)"/)
    if (!m) continue
    const [name, open, prevClose, price, high, low, bid, ask, volume, amount] = m[2].split(',')
    const pct = prevClose ? (((price - prevClose) / prevClose) * 100).toFixed(2) : null
    out.push({ symbol: m[1], name, open, prevClose, price, high, low, bid, ask, volume, amountYuan: amount, pct })
  }
  console.log(JSON.stringify(out, null, 0))
}

async function cmdKline(symArg, periodArg, limitArg, fqtArg) {
  const raw = (symArg || 'SH600519').toUpperCase()
  let mkt, code
  if (/^SH|SZ|BJ/.test(raw)) { mkt = raw.slice(0, 2); code = raw.slice(2) }
  else if (/^\d{6}$/.test(raw)) { mkt = raw.startsWith('6') || raw.startsWith('9') ? '1' : '0'; code = raw }
  else throw new Error('bad symbol ' + symArg)
  const secid = (mkt === '1' || mkt === 'SH') ? '1.' + code : (mkt === 'BJ' ? '0.' + code : '0.' + code)
  const period = periodArg || '101'
  const limit = parseInt(limitArg || '120', 10)
  const fqt = fqtArg || '1'
  // lmt 需配合 beg/end 日期窗口才可靠（纯 lmt 会返回空）；按 limit 反推日历窗口
  const days = Math.max(limit + 40, 80)
  const end = new Date()
  const beg = new Date(end.getTime() - days * 24 * 3600 * 1000)
  const d = (dt) => `${dt.getFullYear()}${String(dt.getMonth() + 1).padStart(2, '0')}${String(dt.getDate()).padStart(2, '0')}`
  const url = `https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=${secid}&klt=${period}&fqt=${fqt}&beg=${d(beg)}&end=${d(end)}&lmt=${limit}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57`
  const txt = await jget(url)
  const j = JSON.parse(txt)
  const kl = (j.data && j.data.klines) || []
  console.log(JSON.stringify({ name: j.data && j.data.name, code, klines: kl }, null, 0))
}

async function cmdGet(urlArg) {
  // 通用抓取任意 https URL 并转为纯文本（参考文献/公告/研报页）
  if (!urlArg) throw new Error('usage: get <url> [--gbk]')
  const gbk = process.argv.includes('--gbk')
  const r = await fetch(urlArg, {
    headers: { 'User-Agent': UA, 'Referer': 'https://www.eastmoney.com/' },
    signal: AbortSignal.timeout(20000),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  const buf = Buffer.from(await r.arrayBuffer())
  let text = gbk ? decodeGbk(buf) : buf.toString('utf8')
  text = text
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
    .replace(/\s+/g, ' ')
    .replace(/\s*\n\s*/g, '\n')
    .trim()
  console.log(text.slice(0, 60000))
}

const [, , cmd, ...rest] = process.argv
;(async () => {
  try {
    switch (cmd) {
      case 'index': await cmdIndex(rest[0]); break
      case 'stocks': await cmdStocks(rest[0]); break
      case 'sector': await cmdSector(rest[0]); break
      case 'sina': await cmdSina(rest[0]); break
      case 'kline': await cmdKline(rest[0], rest[1], rest[2], rest[3]); break
      case 'get': await cmdGet(rest[0]); break
      default:
        console.log('用法: dsh-market.mjs <index|stocks|sector|sina|kline|get> [args]')
        process.exit(2)
    }
  } catch (e) {
    console.error('ERR: ' + e.message)
    process.exit(1)
  }
})()
