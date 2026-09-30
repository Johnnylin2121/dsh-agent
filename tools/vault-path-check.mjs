/**
 * vault-path-check.mjs — 比对 skill 里引用的 vault 路径与基线清单
 *
 * 由 validate-repo.mjs 调用（也可以单独 node -e 调试）。
 * 基线 = tools/vault-paths.json（由 sync-vault-paths.mjs 从真 vault 生成）。
 *
 * 三类判定：
 *   1. 目录引用 → 必须在 manifest.dirs 里（否则阻塞）
 *   2. 无占位符的文件引用 → 必须在 manifest.files 里（否则阻塞）——抓「索引改名」这类
 *   3. 带占位符/通配的文件引用 → 只校验其父目录在 dirs 里（动态产物不入清单）
 * 另外：AGENTS.md 宣布作废的旧目录名（存档/文件存档/交易存档/早读存档/研究）
 * 出现在 skill 里即阻塞——它们不含统一顶层前缀，靠路径比对抓不到。
 *
 * 豁免：含「作废/旧名/校准/并入/过时/曾用」等词的行（那是**故意**写的对照说明），
 * 以及清单里的 `exempt` 数组。
 */
import fs from 'node:fs';
import path from 'node:path';

const TOP = ['交易体系', '附件', 'wiki-work', 'wiki-reading', 'wiki', '读书', '工作', '协作规范', '_系统'];
const REF_RE = new RegExp(`(?:${TOP.join('|')})/[^\\s\`"'()（）【】\\[\\]，。；;、|]*`, 'g');
const OBSOLETE = new Set(['早读存档', '交易存档', '文件存档', '存档', '研究']);
const OBSOLETE_RE = /(?<![\w一-龥])((?:早读|交易|文件)?存档|研究)(?=[\/』」）\s]|$)/g;
// 行级豁免：故意写的对照说明 / 禁止句 / 格式示例
const EXEMPT_LINE = /(作废|旧名|已改|校准|过时|并入|曾用|历史|不再|一律不再|禁止|不得|别新建|不要新建|never|例如|举例|反例)/;
const PLACEHOLDER = /[{}*?<>]|\.\.\.|…|\bYYYY\b|M月|D日|主题|文件名|xxx|路径|名称|目录|ASIN|产品名|店铺名|关键词|日期/i;
const DATE_SEG = /\d{4}[-年]|\d{2}-\d{2}/;
const HAS_EXT = /\.[A-Za-z0-9]{1,6}$/;
// 改名高发的文件：wiki 索引、领域记忆总表
const RENAME_PRONE = /(索引|index)\.md$|^00-/i;
// 不做 vault 路径比对的目录前缀（门禁/钩子自身的规则字面量）
const SKIP_PREFIX = ['tools/', 'push-guard/'];

/** 去掉尾部占位段与省略号，得到"可落地的最末一段" */
function trimPlaceholderTail(ref) {
  const segs = ref.split('/');
  while (segs.length > 1) {
    const last = segs[segs.length - 1];
    if (last === '...' || last === '…' || PLACEHOLDER.test(last)) segs.pop();
    else break;
  }
  return segs.join('/');
}

function normalizeRef(raw) {
  let p = raw.replace(/\\/g, '/').replace(/^[.\/]+/, '').replace(/[/]+$/, '');
  return trimPlaceholderTail(p);
}

/** 反向空格匹配：目录名含空格被正则截断（`附件/1.Mr.dang` ← `附件/1.Mr.dang 交易体系学习`）。
 *  仅用于目录集合，避免把 `wiki/index.md` 这类**真错名**误判为通过。 */
function spaceTruncatedInDirs(ref, set) {
  if (ref.includes(' ')) return false;
  for (const e of set) if (e.length > ref.length && e.startsWith(ref + ' ')) return true;
  return false;
}

/** 精确命中；再退一步尝试在空格处截断（vault 目录名可含空格，如 `附件/1.Mr.dang 交易体系学习`） */
function hit(ref, set) {
  if (set.has(ref)) return true;
  const sp = ref.indexOf(' ');
  if (sp > 0 && set.has(ref.slice(0, sp))) return true;
  return false;
}

export function loadManifest(root) {
  const p = path.join(root, 'tools', 'vault-paths.json');
  if (!fs.existsSync(p)) return null;
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; }
}

export function checkVaultPaths(root, files) {
  const manifest = loadManifest(root);
  const problems = [];
  const warnings = [];
  if (!manifest) {
    warnings.push('tools/vault-paths.json 缺失 → 跳过 vault 路径活性检查（跑 node tools/sync-vault-paths.mjs 生成）');
    return { problems, warnings, checked: 0, enabled: false };
  }
  const dirs = new Set(manifest.dirs || []);
  const known = new Set(manifest.files || []);
  const exempt = new Set(manifest.exempt || []);
  // 按需创建的输出根（skill 运行时会自建），当前不存在不算失效
  const planned = new Set(manifest.plannedDirs || []);

  let checked = 0;
  for (const f of files) {
    if (!/\.(md|ps1|mjs|js)$/i.test(f)) continue;
    // tools/ 与 push-guard/ 是门禁与钩子自身，其中的路径字面量是**规则定义**
    // （如本文件的 `wiki/index.md` 反例、`sync-vault-paths.mjs` 的作废名注释），不是 skill 指令
    if (SKIP_PREFIX.some((p) => f.startsWith(p))) continue;
    let text;
    try { text = fs.readFileSync(path.join(root, f), 'utf8'); } catch { continue; }
    const lines = text.split(/\r?\n/);

    lines.forEach((line, i) => {
      if (EXEMPT_LINE.test(line)) return;

      OBSOLETE_RE.lastIndex = 0;
      let m;
      while ((m = OBSOLETE_RE.exec(line)) !== null) {
        if (exempt.has(m[1])) continue;
        problems.push(`作废目录名 \`${m[1]}/\`（旧归档层/已合并目录，见 vault AGENTS.md 目录树的作废声明）: ${f}:${i + 1}`);
      }

      REF_RE.lastIndex = 0;
      let r;
      while ((r = REF_RE.exec(line)) !== null) {
        const ref = normalizeRef(r[0]);
        if (!ref || exempt.has(ref) || planned.has(ref)) continue;
        checked++;
        const hasExt = HAS_EXT.test(ref);
        if (!hasExt) {
          // 日期段目录（如 选品报告/2026-07-25）按父目录校验
          const parent = ref.includes('/') ? ref.slice(0, ref.lastIndexOf('/')) : '';
          if (DATE_SEG.test(path.basename(ref)) && parent && hit(parent, dirs)) continue;
          if (!hit(ref, dirs)) problems.push(`vault 路径不存在（目录）: \`${ref}\` ← ${f}:${i + 1}`);
          continue;
        }
        // 文件：带日期或动态命名的只校验父目录
        if (DATE_SEG.test(path.basename(ref)) || PLACEHOLDER.test(path.basename(ref))) {
          const parent = ref.slice(0, ref.lastIndexOf('/'));
          if (parent && hit(parent, dirs)) continue;
          if (parent && planned.has(parent)) continue;   // 父目录是按需创建的输出根
          problems.push(`vault 路径不存在（产物所在目录）: \`${parent || ref}\` ← ${f}:${i + 1}`);
          continue;
        }
        // 文件级：只校验「改名高发」的那几类（索引 / 00- 总表）。其余稳定文件名
        // 不在基线里（如 `当前持仓.md`）——基线不收录文件名是为隐私（vault 里有
        // ASIN 命名的实体页），因此不能对全部文件做存在性断言。
        if (!known.has(ref)) {
          if (!RENAME_PRONE.test(path.basename(ref))) continue;   // 不在检查范围
          const parent2 = ref.includes('/') ? ref.slice(0, ref.lastIndexOf('/')) : '';
          if (spaceTruncatedInDirs(ref, dirs)) continue;
          if (parent2 && planned.has(parent2)) continue;
          problems.push(`vault 路径不存在（文件，改名高发）: \`${ref}\` ← ${f}:${i + 1}`);
        }
      }
    });
  }
  return { problems, warnings, checked, enabled: true };
}
