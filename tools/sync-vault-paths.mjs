#!/usr/bin/env node
/**
 * sync-vault-paths.mjs — 刷新 `tools/vault-paths.json`（vault 路径基线清单）
 *
 * 为什么需要：validate-repo.mjs 抓得住"平台绝对路径/密钥/垃圾文件"，抓不住
 * **vault 重组后 skill 里的路径失效**——2026-09-30 那次实战就是连续两轮复发
 * （index.md 改名、研究/ 合并、附件编号重排、存档层统一），其中两条会让
 * `Move-Item` 目标不存在而**运行时直接抛错**。格式合规门禁管不了路径活性。
 *
 * CI 跑在 ubuntu-latest 上，**拿不到本机 vault**，所以这里把"vault 里实际存在
 * 哪些路径"固化成一份**只含 vault 相对路径**的 JSON 入库；门禁据此比对 skill
 * 引用。清单里**不含任何绝对路径**，因此不会触发 push-scan 的 LOCAL-PATH/VAULT-PATH。
 *
 * ⚠️ **隐私边界（2026-09-30 踩坑后定）**：清单**只收目录名**，不自动收录文件名——
 * vault 里存在以商品编号（ASIN，形态为 B0 开头共 10 位字母数字）命名的实体页，
 * 自动收录会把业务标识符带进仓库并被 push-scan 拦下。文件级只收
 * `CURATED_FILES` 这几个**改名高发、且不含敏感信息**的稳定文件名。
 *
 * 用法：
 *   node tools/sync-vault-paths.mjs                 # 自动从 ~/.dsh/MEMORY.md 找 vault
 *   node tools/sync-vault-paths.mjs --vault "<vault 根>"
 *   node tools/sync-vault-paths.mjs --dry
 *
 * 何时该跑：vault 发生目录重组/改名/合并后，跑一次并把清单一起提交。
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const args = process.argv.slice(2);
const dry = args.includes('--dry');
const vIdx = args.indexOf('--vault');
let vault = vIdx >= 0 ? args[vIdx + 1] : process.env.VAULT_PATH;

/** 约定与 MEMORY.md 的「Obsidian Vault」行一致：`- **Obsidian Vault**：`<路径>` */
function vaultFromMemory() {
  const p = path.join(os.homedir(), '.dsh', 'MEMORY.md');
  if (!fs.existsSync(p)) return null;
  const m = fs.readFileSync(p, 'utf8').match(/Obsidian Vault\*\*[：:]\s*`?([^`\r\n]+)`?/);
  return m ? m[1].trim() : null;
}
if (!vault) vault = vaultFromMemory();
if (!vault || !fs.existsSync(vault)) {
  console.error('[sync-vault-paths] 找不到 vault。用 --vault <路径> 指定，或检查 ~/.dsh/MEMORY.md');
  process.exit(2);
}
vault = path.resolve(vault.replace(/^~(?=$|[\\/])/, os.homedir()));

// 不进清单的目录：工具/缓存/归档备份/插件运行时
const SKIP_DIRS = new Set([
  '.obsidian', '.trash', '.git', 'node_modules', '__pycache__',
  '.plugin-manager', '.DS_Store', '_backup', 'backups', '.dsh-patches',
]);
const MAX_DEPTH = 6;              // 清单体积控制
// 隐私：任何含 ASIN 形态的路径段一律不入库（业务标识符不能进仓库）
const ASIN_SEG = /^B0[A-Z0-9]{8}$/i;
// 文件级只认这几个「改名高发 + 不含敏感信息」的稳定文件名
const CURATED_FILES = [
  'wiki/Wiki索引.md',
  'wiki-work/工作知识索引.md',
  'wiki-reading/读书知识索引.md',
  '交易体系/07.交易记忆/00-交易记忆总表.md',
];

const dirs = [];
const files = CURATED_FILES.slice();

(function walk(abs, rel, depth) {
  if (depth > MAX_DEPTH) return;
  let entries;
  try { entries = fs.readdirSync(abs, { withFileTypes: true }); } catch { return; }
  for (const e of entries) {
    if (e.name.startsWith('.') && e.name !== '.system') continue;
    if (SKIP_DIRS.has(e.name)) continue;
    if (ASIN_SEG.test(e.name)) continue;           // 隐私：不收录 ASIN 命名项
    const r = rel ? `${rel}/${e.name}` : e.name;
    if (e.isDirectory()) {
      dirs.push(r);
      walk(path.join(abs, e.name), r, depth + 1);
    }
  }
})(vault, '', 1);

// 手工维护的文件名条目要校验其真实存在，否则基线本身会说谎
const files2 = files.filter((r) => fs.existsSync(path.join(vault, ...r.split('/'))));

dirs.sort();
files2.sort();

const out = path.join(process.cwd(), 'tools', 'vault-paths.json');
// 刷新时保留人工维护的白名单
let oldManifest = {};
try { if (fs.existsSync(out)) oldManifest = JSON.parse(fs.readFileSync(out, 'utf8')); } catch { /* 损坏则当空 */ }

const manifest = {
  $comment: 'vault 路径基线 —— 由 tools/sync-vault-paths.mjs 生成，勿手改。只含 vault 相对路径。',
  generatedAt: new Date().toISOString().slice(0, 19).replace('T', ' '),
  generatedFrom: 'local vault（绝对路径不入库）',
  counts: { dirs: dirs.length, files: files2.length },
  // 下面两项是**人工维护**的，刷新时原样保留（不要清空）
  exempt: oldManifest.exempt || [],
  plannedDirs: oldManifest.plannedDirs || [],
  dirs,
  files: files2,
};

const out2 = path.join(process.cwd(), 'tools', 'vault-paths.json');
const json = JSON.stringify(manifest, null, 1) + '\n';
if (dry) {
  console.log(json.slice(0, 2000));
  console.log(`\n[dry] 将写入 ${out2}（dirs=${dirs.length}, files=${files.length}）`);
} else {
  fs.writeFileSync(out2, json, 'utf8');
  console.log(`[sync-vault-paths] 已写入 ${out2}`);
  console.log(`  dirs=${dirs.length} files=${files.length} 字节=${json.length}`);
}
