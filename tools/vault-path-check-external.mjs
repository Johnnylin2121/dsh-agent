#!/usr/bin/env node
/**
 * vault 路径活性门禁 · 外部源版
 *
 * 为什么要有这个：tools/validate-repo.mjs 只能扫本仓（skills 仓）的 git 跟踪文件，
 * 而 2026-09-30 实际发生的两条 P0 事故——workflow_migration 里 3 个 Python 常量
 * 与 ~/.dsh/timer-agent/jobs.json 里 2 个定时任务 prompt——都在本仓之外，
 * 门禁一律放行。其中 daily_calibration.py 会 mkdir(parents=True)，
 * 每天 15:10 的定时任务会建出孤儿目录，属静默且会累积的失败。
 *
 * 用法：
 *   node tools/vault-path-check-external.mjs            # 扫描并报告，退出码 1 = 有失效
 *   node tools/vault-path-check-external.mjs -Fix       # 自动修能自动修的（不实现，留口）
 *
 * 退出码：0 全部有效 / 1 存在失效引用 / 2 清单缺失或源不存在（无法判断）
 *
 * 不入库 vault 的任何绝对路径：本脚本只读源文件，输出的是 vault **相对路径**。
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

// 本机真实 vault 路径**不入库**（仓库策略：提交里只放 {VAULT_PATH} 占位符，
// push-scan 会拦真实路径）。必须由环境变量显式传入。
const VAULT_ROOT = process.env.VAULT_PATH || '';
const SKILL_ROOT = path.join(os.homedir(), '.dsh', 'skills');
const DSH_HOME = process.env.DSH_HOME || path.join(os.homedir(), '.dsh');

// 本机上的外部源。每一项都标注了为什么它会漏过本仓门禁。
const SOURCES = [
  {
    id: 'workflow_migration',
    why: '主仓 workflow_migration 的 Python 常量，vault 目录重组后最易失效且会 mkdir',
    collect() {
      const dir = 'E:\\3.deepseek-harness\\workflow_migration';
      if (!fs.existsSync(dir)) return { files: [], note: `目录不存在：${dir}` };
      return {
        files: fs.readdirSync(dir)
          .filter(f => /\.(py|mjs|ps1)$/i.test(f) && !f.startsWith('_'))
          .map(f => path.join(dir, f)),
      };
    },
  },
  {
    id: 'timer-agent',
    why: '定时任务 prompt 内嵌 vault 绝对路径，无人值守时失效=静默失败',
    collect() {
      const p = path.join(DSH_HOME, 'timer-agent', 'jobs.json');
      if (!fs.existsSync(p)) return { files: [], note: `jobs.json 不存在：${p}` };
      return { files: [p] };
    },
  },
  {
    id: 'dsh-home-config',
    why: '~/.dsh 下的配置与 skill 外挂脚本（不含 skills/ 本身，那已由本仓门禁覆盖）',
    collect() {
      const files = [];
      for (const rel of ['MEMORY.md', 'cordis.patch.yml']) {
        const p = path.join(DSH_HOME, rel);
        if (fs.existsSync(p)) files.push(p);
      }
      const shared = path.join(DSH_HOME, 'skills', '_shared');
      if (fs.existsSync(shared)) {
        for (const f of fs.readdirSync(shared)) {
          if (/\.(mjs|js|ps1)$/i.test(f)) files.push(path.join(shared, f));
        }
      }
      return { files };
    },
  },
];

// 灵敏度测试入口：`GATE_PROBE=<file>` 会把该文件并入扫描。
// 存在的理由：本门禁曾因正则拼接漏括号（`a|b` + `[\\/]x` 只绑到最后一个分支）
// 而**静默只检查一个顶层域**却报"通过"——绿色结果不等于检查生效。
// 改动本脚本的提取逻辑后，必须用它确认「已知坏路径仍被抓出、正文列举仍被忽略」。
if (process.env.GATE_PROBE && fs.existsSync(process.env.GATE_PROBE)) {
  SOURCES.push({
    id: 'probe',
    why: 'GATE_PROBE 灵敏度测试注入',
    collect: () => ({ files: [process.env.GATE_PROBE] }),
  });
}

// 抽出 vault 相对路径引用。**只在真路径语境下提取**——
//   ① vault 绝对路径（Python/PS 里的 Path / 正则）之后的部分
//   ② `{VAULT_PATH}/` 之后的部分
//   ③ 反引号内、且以已知顶层域开头的串
// 不满足以上任一的不提取：`（分析报告/listing/选品/附件/记忆）` 这类类别列举
// 会被正则误捕成 `附件/记忆`，噪声会淹没真问题。
const TOP_DIRS = ['交易体系', '附件', '工作', 'wiki', 'wiki-work', '_系统'];
// ⚠️ 拼装正则时踩过两次坑，都表现为「绿色通过但实际没检查」：
//   ① `a|b` + `[\\/]x` —— `|` 优先级低于字符类，路径部分只绑到最后一个分支
//   ② `${ALT}[\\/]${TAIL}` 不带括号 —— 捕获组只圈住顶层域名，路径部分落在组外
// 所以这里把「顶层域 + 至少一层子路径 + 尾巴」整体做成一个**带括号的捕获单元**。
const TOP_ALT = `(${TOP_DIRS.join('|')})`;
const SEP = '[\\\\/]+';                                  // 一个或多个分隔符（JSON 里是 \\ ）
const TAIL_POSIX = '[^\\\\\\s"\'\\x60（）、，。；:：|…]+'; // markdown 风格：只认正斜杠
const TAIL_WIN   = '[^\\s"\'\\x60（）、，。；:：|…]+';     // Windows 绝对路径：反斜杠是路径的一部分
const BT = '\\x60';                                     // 反引号，避免模板字面量转义把代码写坏
// ① vault 绝对路径（Python/PS/JSON 里的 Windows 路径，反斜杠可出现在路径中）
const RE_ABS = new RegExp(`ObsidianVault${SEP}(${TOP_ALT}${SEP}${TAIL_WIN})`, 'g');
// ② {VAULT_PATH}/ 占位
const RE_PH = new RegExp(`\\{VAULT_PATH\\}${SEP}?(${TOP_ALT}${SEP}${TAIL_POSIX})`, 'g');
// ③ 反引号内
const RE_TICK = new RegExp(`${BT}(${TOP_ALT}${SEP}${TAIL_POSIX})${BT}`, 'g');

function extractRefs(line) {
  const out = [];
  for (const re of [RE_ABS, RE_PH, RE_TICK]) {
    re.lastIndex = 0;
    for (const m of line.matchAll(re)) out.push(m[1]);
  }
  return out;
}

function toVaultAbs(rel) {
  return path.join(VAULT_ROOT, rel.replace(/\//g, path.sep));
}

/** 命名模板而非真实文件：`YYYY-MM-DD-交易记忆-主题.md`、`{日期}.md`、`第N周` 之类 */
const TEMPLATE = /\{|YYYY|MM-DD|\{\{|<[A-Za-z一-龥]+>|\bN\b(?=\b)|…|\*|\?/;

/**
 * 逐级前缀回溯：整条不存在时，找出「实际最近存在的是哪一级」，
 * 这样报错能直接给出改法，而不是只说"不存在"。
 */
function resolveDeepestExisting(rel) {
  const segs = rel.split(/[\\/]/).filter(Boolean);
  for (let n = segs.length - 1; n >= 1; n--) {
    const prefix = segs.slice(0, n).join('/');
    if (fs.existsSync(toVaultAbs(prefix))) {
      return { ok: false, deepest: prefix, missingFrom: segs.slice(n).join('/') };
    }
  }
  return { ok: false, deepest: null, missingFrom: rel };
}

function main() {
  if (!VAULT_ROOT) {
    console.error('[external] ✗ 未设置 VAULT_PATH 环境变量。');
    console.error('        本仓库不保存真实 vault 路径（push-scan 会拦），故必须显式传入：');
    console.error('          $env:VAULT_PATH = "<你的 vault 绝对路径>"   # PowerShell');
    console.error('          VAULT_PATH="<你的 vault 绝对路径>" node tools/vault-path-check-external.mjs');
    return 2;
  }
  if (!fs.existsSync(VAULT_ROOT)) {
    console.error(`[external] ✗ vault 不存在：${VAULT_ROOT}`);
    console.error('        检查 VAULT_PATH 是否指向真实 vault 根目录。');
    return 2;
  }

  const problems = [];
  const notes = [];
  let checked = 0;

  for (const src of SOURCES) {
    let got;
    try { got = src.collect(); } catch (e) {
      notes.push(`${src.id}: 收集失败 — ${e.message}`);
      continue;
    }
    if (got.note) notes.push(`${src.id}: ${got.note}`);
    if (!got.files.length) { notes.push(`${src.id}: 无可扫文件`); continue; }

    let srcCount = 0;
    for (const f of got.files) {
      let text;
      try { text = fs.readFileSync(f, 'utf8'); } catch { continue; }
      // JSON 里 prompt 的换行是**字面 \n 转义**，不解开的话整段挤成一行，
      // 行级跳过规则（更正说明/禁令句）会连整条 prompt 一起跳过。
      if (f.endsWith('.json')) text = text.replace(/\\r\\n|\\n/g, '\n');
      // 跳过更正说明/历史记录/禁令句里的示例路径：这类引用是"讲历史"或"明令禁止"，
      // 不是"要用这个路径"，按字面判失效会淹没真问题。
      const SKIP_LINE = /^\s*[>#|*]|更正|已作废|原写作|原值|旧路径|已废弃|历史归档|作废|禁止|不得|勿|不可|应避免|勿再/;
      const lines = text.split(/\r?\n/);
      lines.forEach((line, i) => {
        if (SKIP_LINE.test(line)) return;
        for (const rel of extractRefs(line)) {
          // 截到 shell/代码参数边界：`交易体系\交易记忆 -File` 的 " -File" 不是路径一部分
          const clean = rel.replace(/(?:\s+-{1,2}[A-Za-z][\w-]*).*$/, '').replace(/[…\-]+$/, '');
          if (TEMPLATE.test(clean)) continue;            // 命名模板/通配，不是真实路径
          const abs = toVaultAbs(clean);
          srcCount++; checked++;
          if (fs.existsSync(abs)) continue;
          const d = resolveDeepestExisting(clean);
          const hint = d.deepest ? `（实际最近存在：\`${d.deepest}\`，缺 "${d.missingFrom}"）` : '';
          problems.push(`${clean}${hint}  ←  ${f}:${i + 1}`);
        }
      });
    }
    console.log(`[external] ${src.id.padEnd(18)} ${String(srcCount).padStart(4)} 处引用`);
    console.log(`             ${src.why}`);
  }

  if (notes.length) {
    console.log('\n说明：');
    for (const n of notes) console.log(`  · ${n}`);
  }

  console.log('');
  if (problems.length) {
    console.error(`❌ 阻塞项 ${problems.length} 条（外部源）：`);
    for (const p of problems) console.error(`   - vault 路径不存在: ${p}`);
    console.error('\n结论：不通过');
    return 1;
  }
  console.log(`✅ 外部源无阻塞项（共比对 ${checked} 处引用）`);
  return 0;
}

process.exit(main());
