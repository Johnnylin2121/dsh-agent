#!/usr/bin/env node
/**
 * vault-batch.mjs — Obsidian vault 批量整理工具（零依赖，Node >=18）
 *
 * 补齐 dsh-obsidian 缺的两块能力：
 *   1) 批量移动/重命名笔记（含整目录），并重写全库 [[wikilink]] / ![[embed]]（对齐 Obsidian rename 行为）
 *   2) 库结构统计、标签统计、孤立笔记（无入链无出链）、悬空链接（指向不存在的笔记）
 *
 * 用法：
 *   node vault-batch.mjs structure [--dir <vault相对子目录>] [--top 20] [--json]
 *   node vault-batch.mjs orphans   [--json]
 *   node vault-batch.mjs dangling  [--json]
 *   node vault-batch.mjs move "<旧路径.md|旧目录>" "<新路径>" [--dry-run]
 *   node vault-batch.mjs move-batch <map.json> [--dry-run]     # {"旧":"新", ...}
 *
 * vault 根目录：--vault <path> > 环境变量 VAULT_PATH > 从 ~/.dsh/MEMORY.md 里找含 ObsidianVault 的路径
 * 约定：路径均相对 vault 根、用正斜杠；一切写入前先加 --dry-run 看输出。
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const args = process.argv.slice(2);
const cmd = args[0];
const has = (n) => args.includes('--' + n);
const flag = (name, def) => {
  const i = args.indexOf('--' + name);
  if (i < 0) return def;
  const v = args[i + 1];
  return v && !v.startsWith('--') ? v : true;
};
const positional = args.slice(1).filter((a, i) => {
  if (a.startsWith('--')) return false;
  const prev = args[i];
  return !(prev && prev.startsWith('--'));
});

function resolveVault() {
  const explicit = flag('vault', null);
  if (explicit && explicit !== true) return String(explicit);
  if (process.env.VAULT_PATH) return process.env.VAULT_PATH;
  const mem = path.join(os.homedir(), '.dsh', 'MEMORY.md');
  if (fs.existsSync(mem)) {
    for (const line of fs.readFileSync(mem, 'utf8').split(/\r?\n/)) {
      const m = line.match(/[A-Za-z]:[\\/][^\s`'"|<>]*ObsidianVault[^\s`'"|<>]*/i);
      if (m) return m[0].replace(/\\/g, '/').replace(/\/+$/, '');
    }
  }
  return null;
}

const VAULT = resolveVault();
if (!VAULT || !fs.existsSync(VAULT)) {
  console.error(`找不到 vault：${VAULT ?? '(未解析到)'}。用 --vault <path> 或 VAULT_PATH 指定。`);
  process.exit(2);
}

const EXCLUDE = ['.obsidian', '.trash', '.git'];
const posix = (p) => String(p).replace(/\\/g, '/');
const stripMd = (p) => String(p).replace(/\.md$/i, '');
const norm = (p) => posix(path.posix.normalize(posix(p))).replace(/^\.\//, '').replace(/\/+$/, '');
const LINK_RE = /(!?)\[\[([^\[\]]+)\]\]/g;

function listNotes(root, sub = '') {
  const out = [];
  for (const e of fs.readdirSync(path.join(root, sub), { withFileTypes: true })) {
    const rel = sub ? `${sub}/${e.name}` : e.name;
    if (e.isDirectory()) {
      if (EXCLUDE.includes(e.name)) continue;
      out.push(...listNotes(root, rel));
    } else if (e.name.toLowerCase().endsWith('.md')) out.push(norm(rel));
  }
  return out;
}

function splitTarget(raw) {
  let alias = '';
  let rest = raw;
  const bar = raw.indexOf('|');
  if (bar >= 0) { alias = raw.slice(bar); rest = raw.slice(0, bar); }
  let anchor = '';
  const h = rest.search(/[#^]/);
  if (h >= 0) { anchor = rest.slice(h); rest = rest.slice(0, h); }
  return { target: rest.trim(), alias, anchor };
}

function parseTags(text) {
  const fm = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  const fmText = fm ? fm[1] : '';
  const tags = [];
  const arr = fmText.match(/tags:\s*\[([^\]]*)\]/);
  if (arr) tags.push(...arr[1].split(',').map((s) => s.trim().replace(/^['"]|['"]$/g, '')).filter(Boolean));
  else {
    const block = fmText.match(/tags:\s*\n((?:\s*-\s*.+\r?\n?)+)/);
    if (block) tags.push(...block[1].split(/\r?\n/).map((s) => s.replace(/^\s*-\s*/, '').trim()).filter(Boolean));
  }
  const body = fm ? text.slice(fm[0].length) : text;
  let inFence = false;
  for (const line of body.split(/\r?\n/)) {
    if (/^\s*(```|~~~)/.test(line)) { inFence = !inFence; continue; }
    if (inFence) continue;
    for (const t of line.matchAll(/(^|\s)#([\p{L}\p{N}_/-]+)/gu)) tags.push(t[2]);
  }
  return [...new Set(tags)];
}

function build() {
  const notes = listNotes(VAULT).map((rel) => {
    const text = fs.readFileSync(path.join(VAULT, rel), 'utf8');
    const links = [...text.matchAll(LINK_RE)].map((m) => ({ embed: m[1] === '!', raw: m[2], ...splitTarget(m[2]) }));
    return { rel, text, links, tags: parseTags(text) };
  });
  const byRel = new Map();
  const byBase = new Map();
  for (const n of notes) {
    byRel.set(stripMd(n.rel), n);
    byRel.set(n.rel, n);
    const base = path.posix.basename(stripMd(n.rel)).toLowerCase();
    if (!byBase.has(base)) byBase.set(base, []);
    byBase.get(base).push(n);
  }
  return { notes, byRel, byBase };
}

/** 解析一条链接；返回 {resolved|ambiguous|dangling|attachment} 及改写结果 */
function resolveLink(note, link, idx, moves) {
  const noteDir = path.posix.dirname(note.rel);
  const rawTarget = posix(link.target);
  let t = norm(rawTarget);
  let asPath = false;
  if (/^\.{1,2}\//.test(rawTarget)) { t = norm(path.posix.join(noteDir, rawTarget)); asPath = true; }
  if (/\.[a-z0-9]{1,6}$/i.test(t) && fs.existsSync(path.join(VAULT, t))) return { attachment: true };
  let target = null;
  if (idx.byRel.has(t)) { target = idx.byRel.get(t); asPath = true; }
  else if (idx.byRel.has(t + '.md')) { target = idx.byRel.get(t + '.md'); asPath = true; }
  else {
    if (fs.existsSync(path.join(VAULT, t))) return { attachment: true };
    const cand = idx.byBase.get(path.posix.basename(t).toLowerCase());
    if (cand && cand.length === 1) target = cand[0];
    else if (cand && cand.length > 1) return { ambiguous: link.target };
    else return { dangling: link.target };
  }
  const newRel = moves.get(target.rel);
  const origRaw = `${link.embed ? '!' : ''}[[${link.raw}]]`;
  if (!newRel) return { resolved: target };
  const rewritten = asPath || link.target.includes('/') ? stripMd(newRel) : path.posix.basename(stripMd(newRel));
  return { resolved: target, origRaw, becomes: `${link.embed ? '!' : ''}[[${rewritten}${link.anchor}${link.alias}]]` };
}

function rewrite(idx, moves, dryRun) {
  let touched = 0;
  let links = 0;
  const details = [];
  for (const note of idx.notes) {
    const edits = [];
    for (const l of note.links) {
      const r = resolveLink(note, l, idx, moves);
      if (r.becomes && r.becomes !== r.origRaw) edits.push(r);
    }
    if (!edits.length) continue;
    let out = note.text;
    for (const e of edits) out = out.split(e.origRaw).join(e.becomes);
    if (!dryRun) fs.writeFileSync(path.join(VAULT, note.rel), out, 'utf8');
    touched++;
    links += edits.length;
    details.push({ rel: note.rel, count: edits.length });
  }
  return { touched, links, details };
}

/** 源路径定位：完整相对路径优先；否则按唯一裸文件名（可省 .md）解析 */
function locate(p) {
  if (fs.existsSync(path.join(VAULT, p))) return p;
  const base = path.posix.basename(p).toLowerCase();
  const hits = listNotes(VAULT).filter((r) => {
    const b = path.posix.basename(r).toLowerCase();
    return b === base || b === base + '.md';
  });
  if (hits.length === 1) return hits[0];
  if (hits.length > 1) throw new Error(`"${p}" 在库中不唯一（${hits.length} 处），请写完整路径：${hits.join(' | ')}`);
  throw new Error(`源不存在: ${p}`);
}

/** 目标没有扩展名时保留源扩展名（对齐 Obsidian 重命名行为） */
function keepExt(from, to) {
  const srcExt = path.posix.extname(from);
  const dstBase = path.posix.basename(to);
  return srcExt && !dstBase.includes('.') ? to + srcExt : to;
}

function pruneEmptyDirs(startRel) {
  let dir = path.posix.dirname(startRel);
  while (dir && dir !== '.' && dir !== '/') {
    const abs = path.join(VAULT, dir);
    if (!fs.existsSync(abs) || fs.readdirSync(abs).length) break;
    fs.rmdirSync(abs);
    dir = path.posix.dirname(dir);
  }
}

function doMove(fromRaw, to, dryRun) {
  const from = locate(fromRaw);
  const src = path.join(VAULT, from);
  if (!fs.existsSync(src)) throw new Error(`源不存在: ${from}`);
  const moves = new Map();
  if (fs.statSync(src).isDirectory()) {
    const prefix = from.replace(/\/+$/, '');
    for (const rel of listNotes(VAULT, prefix)) moves.set(rel, `${to.replace(/\/+$/, '')}/${rel.slice(prefix.length + 1)}`);
  } else moves.set(from, keepExt(from, to));
  const idx = build();
  const { touched, links, details } = rewrite(idx, moves, dryRun);
  for (const [o, n] of moves) {
    if (dryRun) continue;
    const dst = path.join(VAULT, n);
    fs.mkdirSync(path.dirname(dst), { recursive: true });
    try { fs.renameSync(path.join(VAULT, o), dst); }
    catch { fs.copyFileSync(path.join(VAULT, o), dst); fs.unlinkSync(path.join(VAULT, o)); }
  }
  if (!dryRun) for (const o of moves.keys()) pruneEmptyDirs(o);
  return { moved: moves.size, touched, links, details, dryRun };
}

function structure(idx, sub, top) {
  const scope = sub ? idx.notes.filter((n) => n.rel.startsWith(norm(sub) + '/')) : idx.notes;
  const inScope = new Set(scope.map((n) => n.rel));
  const counts = new Map();
  for (const n of scope) {
    const parts = n.rel.split('/');
    const key = parts.length > 1 ? `${parts[0]}/` : '(根目录)';
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  const inbound = new Map();
  const outbound = new Map();
  const dangling = [];
  for (const n of idx.notes) {
    const outs = new Set();
    for (const l of n.links) {
      const r = resolveLink(n, l, idx, new Map());
      if (r.resolved) { outs.add(r.resolved.rel); if (inScope.has(n.rel)) inbound.set(r.resolved.rel, (inbound.get(r.resolved.rel) || 0) + 1); }
      else if (r.dangling && inScope.has(n.rel)) dangling.push({ from: n.rel, target: r.dangling });
    }
    if (inScope.has(n.rel)) outbound.set(n.rel, outs.size);
  }
  const orphans = scope.filter((n) => !inbound.get(n.rel) && !outbound.get(n.rel)).map((n) => n.rel);
  const tags = new Map();
  for (const n of scope) for (const t of n.tags) tags.set(t, (tags.get(t) || 0) + 1);
  return {
    notes: scope.length,
    dirs: [...counts.entries()].sort((a, b) => b[1] - a[1]),
    tags: [...tags.entries()].sort((a, b) => b[1] - a[1]).slice(0, Number(top) || 20),
    orphans,
    dangling,
  };
}

const json = has('json');
const dry = has('dry-run') || has('dryrun');
const out = (obj, lines) => console.log(json ? JSON.stringify(obj, null, 2) : lines.join('\n'));

try {
  if (cmd === 'structure' || cmd === 'orphans' || cmd === 'dangling') {
    const idx = build();
    const dir = flag('dir', null);
    const s = structure(idx, dir === true ? null : dir, flag('top', 20));
    if (cmd === 'orphans') { out({ vault: VAULT, orphans: s.orphans }, [`vault: ${VAULT}`, `孤立笔记 ${s.orphans.length} 篇:`, ...s.orphans.map((o) => '  ' + o)]); }
    else if (cmd === 'dangling') { out({ vault: VAULT, dangling: s.dangling }, [`悬空链接 ${s.dangling.length} 条:`, ...s.dangling.map((d) => `  ${d.from} -> [[${d.target}]]`)]); }
    else {
      out({ vault: VAULT, ...s }, [
        `vault: ${VAULT}`,
        `笔记 ${s.notes} 篇`,
        '-- 目录分布 --', ...s.dirs.slice(0, 15).map(([k, v]) => `  ${k} ${v}`),
        `-- 标签 Top ${s.tags.length} --`, ...s.tags.map(([k, v]) => `  #${k} ${v}`),
        `-- 孤立笔记 ${s.orphans.length} --`, ...s.orphans.slice(0, 20).map((o) => '  ' + o),
        `-- 悬空链接 ${s.dangling.length} --`, ...s.dangling.slice(0, 20).map((d) => `  ${d.from} -> [[${d.target}]]`),
      ]);
    }
  } else if (cmd === 'move') {
    const [from, to] = positional;
    if (!from || !to) { console.error('用法: move "<旧路径.md|旧目录>" "<新路径>" [--dry-run]'); process.exit(2); }
    const r = doMove(norm(from), norm(to), dry);
    out(r, [`${r.dryRun ? '[dry-run] ' : ''}移动 ${r.moved} 个文件；重写 ${r.links} 处链接（涉及 ${r.touched} 篇）`, ...r.details.map((d) => `  ${d.rel}: ${d.count} 处`)]);
  } else if (cmd === 'move-batch') {
    const mapFile = positional[0];
    if (!mapFile) { console.error('用法: move-batch <map.json> [--dry-run]'); process.exit(2); }
    const map = JSON.parse(fs.readFileSync(mapFile, 'utf8'));
    const agg = { moved: 0, links: 0, touched: 0, details: new Map(), dryRun: dry };
    for (const [from, to] of Object.entries(map)) {
      const plan = doMove(norm(from), norm(to), true);
      agg.moved += plan.moved; agg.links += plan.links;
      for (const d of plan.details) agg.details.set(d.rel, (agg.details.get(d.rel) || 0) + d.count);
      if (!dry) doMove(norm(from), norm(to), false);
    }
    agg.touched = agg.details.size;
    out({ ...agg, details: [...agg.details].map(([rel, count]) => ({ rel, count })) }, [`${dry ? '[dry-run] ' : ''}批量移动 ${agg.moved} 个文件；重写 ${agg.links} 处链接（涉及 ${agg.touched} 篇）`, ...[...agg.details].map(([rel, count]) => `  ${rel}: ${count} 处`)]);
  } else {
    console.error(`未知命令: ${cmd ?? '(空)'}\n可用: structure | orphans | dangling | move | move-batch`);
    process.exit(2);
  }
} catch (e) {
  console.error('错误: ' + (e && e.message));
  process.exit(1);
}
