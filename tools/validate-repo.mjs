#!/usr/bin/env node
/**
 * validate-repo.mjs — 跨端仓库体检（零依赖，Windows / macOS / Linux 通用）
 *
 * 目的：把"只推非限制性内容"这条双端约定变成可执行的门槛。
 * 双端工作制下，任何一端推的内容另一端都要能直接用或简单适配——本脚本负责在 push 前/CI 里
 * 抓出平台强绑定、密钥、垃圾文件与体积问题。
 *
 * 用法：node tools/validate-repo.mjs        （退出码：0 通过，1 有阻塞项）
 * CI：.github/workflows/validate.yml 在 push/PR 时自动跑
 */
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const ROOT = process.cwd();
const problems = [];
const warnings = [];

// ── 约定：这些路径允许保留本机构建路径（本地补丁副本，非跨端内容）──
const ABS_PATH_ALLOW = [
  /^plugins\/dsh-patches\//,      // 本地插件补丁副本（含某台机器的 tsconfig paths）
  /^tools\/validate-repo\.mjs$/,  // 本脚本自身的规则字面量
];

// 文本文件判定（排除二进制）
const BINARY = /\.(png|jpe?g|gif|webp|ico|pdf|zip|gz|tgz|woff2?|ttf|otf|wasm|mp4|mov)$/i;
const JUNK = /(^|\/)(__pycache__|\.DS_Store|Thumbs\.db|node_modules)(\/|$)/;
const DATA = /\.(xlsx|xls|csv|pyc|log|tmp)$/i;

// ── 1. skill 目录结构 ──
const NON_SKILL_DIRS = new Set(['_shared', 'plugins', 'push-guard', 'tools', 'docs', '.github', '.git']);
for (const e of fs.readdirSync(ROOT, { withFileTypes: true })) {
  if (!e.isDirectory() || e.name.startsWith('.') || NON_SKILL_DIRS.has(e.name)) continue;
  const skillFile = path.join(ROOT, e.name, 'SKILL.md');
  if (!fs.existsSync(skillFile)) { warnings.push(`${e.name}/: 目录内没有 SKILL.md（若非 skill 目录请加入 NON_SKILL_DIRS）`); continue; }
  const text = fs.readFileSync(skillFile, 'utf8');
  const fm = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!fm) { problems.push(`${e.name}/SKILL.md: 缺 YAML frontmatter`); continue; }
  if (!/\bname:\s*\S/.test(fm[1])) problems.push(`${e.name}/SKILL.md: frontmatter 缺 name`);
  if (!/\bdescription:/.test(fm[1])) problems.push(`${e.name}/SKILL.md: frontmatter 缺 description`);
}

// ── 2. 逐文件检查（以 git 跟踪清单为准）──
let files = [];
try {
  files = execFileSync('git', ['ls-files'], { cwd: ROOT, encoding: 'utf8' }).split('\n').filter(Boolean);
} catch {
  console.error('无法读取 git 跟踪清单（必须在 git 仓库内运行）');
  process.exit(2);
}

const WIN_ABS = /c:[\\/]users[\\/][a-z0-9_.\-]+/i;
const MAC_ABS = /\/users\/[a-z0-9_.\-]+/i;
const SECRET = /sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----/;

for (const f of files) {
  if (JUNK.test(f)) problems.push(`垃圾/缓存文件被跟踪: ${f}`);
  if (DATA.test(f)) warnings.push(`数据类文件被跟踪（双端易冲突）: ${f}`);

  const abs = path.join(ROOT, f);
  let size = 0;
  try { size = fs.statSync(abs).size; } catch { continue; }
  if (size > 1024 * 1024) warnings.push(`大文件 ${(size / 1048576).toFixed(1)}MB（双端同步/克隆成本）: ${f}`);
  if (BINARY.test(f)) continue;

  let text = '';
  try { text = fs.readFileSync(abs, 'utf8'); } catch { continue; }

  const allowed = ABS_PATH_ALLOW.some((re) => re.test(f));
  if (!allowed) {
    if (WIN_ABS.test(text)) problems.push(`Windows 用户绝对路径（跨端不可用）: ${f}`);
    if (MAC_ABS.test(text)) problems.push(`macOS 用户绝对路径（跨端不可用）: ${f}`);
  }
  if (SECRET.test(text)) problems.push(`疑似密钥/令牌: ${f}`);
  if (text.includes('\r\n')) warnings.push(`含 CRLF 换行（.gitattributes 已固定 LF，建议跑一次规范化）: ${f}`);
}

// ── 3. 报告 ──
const line = (s) => console.log(s);
line(`仓库：${ROOT}`);
line(`跟踪文件：${files.length}`);
line('');
if (problems.length) {
  line(`❌ 阻塞项 ${problems.length} 条：`);
  for (const p of problems) line('   - ' + p);
} else line('✅ 无阻塞项');
if (warnings.length) {
  line('');
  line(`⚠️  提醒 ${warnings.length} 条：`);
  for (const w of warnings) line('   - ' + w);
}
line('');
if (problems.length) { line('结论：不通过（修掉阻塞项后再推）'); process.exit(1); }
line('结论：通过（跨端内容合规）');
