---
name: amazon-listing
description: >
  Amazon listing optimization workflow. Use when the user wants to analyze competitor
  listings to extract core keywords, write an optimized title + Item Highlights +
  bullet points with keyword embedding, and generate backend search terms.
  Implements the 2026-07 title policy (title ≤75 chars, Item Highlights ≤125 chars,
  combined ≤200). Supports any Amazon marketplace. Crawling via read_page/web_fetch,
  BrowserSkill browser automation (fallback for truncation/CAPTCHA/login-state), or
  manual paste. Triggered by "亚马逊 listing", "竞品分析",
  "listing 核心关键词", "竞品关键词", "标题五点", "商品亮点", "后台搜索词", or similar.
---

# Amazon Listing Optimization Workflow (2026-07 Policy)

## Overview

Six-step workflow. Pause at the end of each step for user review before continuing.

**Step 0** — Confirm marketplace + title policy applicability
**Step 1** — Collect competitor listings (Jina/manual), extract top 10 core keywords (via scripts/kw_analysis.py)
**Step 2** — Write Title (≤75 chars) + Item Highlights (≤125 chars total)
**Step 3** — Write 5 bullet points (≤500 chars each)
**Step 4** — Generate backend search terms (≤249 bytes)
**Step 5** — Post-launch ad feedback loop (1-2 weeks later)

Output: single progressively-built `.md` file written to `{VAULT_PATH}/工作/亚马逊工作管理/链接listing/<ASIN>-<product>-listing.md` (DSH: read the vault path from `~/.dsh/MEMORY.md` — never hardcode it). **All Amazon-related outputs must live under `{VAULT_PATH}/工作/亚马逊工作管理/`** — never create top-level `{VAULT_PATH}/工作/亚马逊分析/` or similar new folders.

## Amazon Listing Rules (Hardcoded, 2026-07-27 policy, all categories except media)

### Field Limits
| Field | Limit | Notes |
|-------|-------|-------|
| Title (商品名称) | 75 characters incl. spaces | Hard cap; some categories stricter (apparel 60). Highlights render ONLY when title < 75 — keep safety margin ≤ 73 |
| Item Highlights (商品亮点) | 125 characters TOTAL for the whole field | Separate searchable field shown below title (search results + PDP). Up to ~10 attribute phrases inside the 125-char budget |
| Title + Highlights combined | 200 characters | Hard combined cap |
| Bullet point | 500 characters per bullet | 5 bullets total |
| Backend search terms | 249 bytes | Bytes, NOT characters. Non-ASCII chars use 2+ bytes |

### Item Highlights Rules (NEW field — generated in Step 2)
- Attribute/benefit-driven **phrases, NOT full sentences** (e.g. "Compatible con PS5, Xbox Series X", not "This cable works with PS5")
- **Do NOT repeat information already in the Title** — never reuse the same terms; express residual claims as benefit phrasing
- Reserved for: compatibility lists, use cases, materials, benefits that don't fit the 75-char title
- Field is **searchable** — treat leftover non-title core keywords as highlight candidates
- Priority: unverifiable claims (certifications, codecs) must be marked `[待确认]` unless user confirms the product actually supports them. Never copy competitor claims blindly.

### Prohibited Content (Title & Bullets & Highlights)
- ❌ Promotional claims: "best seller", "#1", "top rated", "100% quality"
- ❌ Price mentions: "cheap", "affordable", "discount", "on sale"
- ❌ Guarantee/refund language: "money back", "satisfaction guaranteed"
- ❌ Subjective superlatives: "amazing", "incredible", "fantastic", "perfect"
- ❌ Shipping/time claims: "free shipping", "fast delivery", "2-day arrival"
- ❌ Contact info: email, phone, URLs, external site references
- ❌ New policy banned chars in title: `! $ ? _ { } ^ ¬ ¦` (em-dash/separators avoided too)
- ❌ ALL CAPS words (except standard abbreviations: USB, HDMI, LED, HDR, eARC. 8K@60Hz-style resolutions keep standard caps)
- ❌ Same word more than twice in a title (exceptions: prepositions, articles, conjunctions)

### Backend Search Terms Rules
- ❌ Do NOT repeat any word already present in Title, Highlights, or Bullets (exclusion set = all three)
- ❌ No brand names / ASINs / promotional terms
- ❌ No commas, semicolons, or separators — single spaces only
- ❌ Singular covers plural; don't include both; case-insensitive lowercase
- ✅ Include: synonyms, alternate names, misspellings, alternate-language terms, complementary product terms, long-tail phrases

### Title Capitalization by Marketplace
- **Amazon.com / .co.uk**: Capitalize first letter of each word (except articles/prepositions ≤ 3 letters)
- **Amazon.de**: German rules (nouns capitalized)
- **Amazon.co.jp**: Japanese conventions
- **Amazon.fr / .es / .it / .com.mx**: language conventions (Spanish: only first word + proper nouns capitalized)

---

## Step 0 — Confirm Marketplace & Policy

1. Ask which marketplace (default: marketplace of user's link — note: .com.mx etc.)
2. Ask class of product to confirm the 75/125/200 caps apply (media categories are exempt; apparel = 60-char title). If unsure, ask user what Seller Central shows.
3. Record the active caps in the output file header. Proceed to Step 1.

---

## Step 1 — Collect Competitor Data & Extract Top 10 Core Keywords

### Input
1–5 competitor ASINs/URLs, same marketplace (≥3 recommended; warn if fewer, still proceed).

### Crawling — priority order (NO infinite retries; max 2 attempts per source)
1. **read_page** (DSH built-in, first choice): `read_page url="https://www.<marketplace>/dp/<ASIN>"` — parse title/bullets from returned text.
2. If read_page fails or content is truncated (cloud extraction ~50k-char cap + page noise squeezing out bullets/variants — Amazon is the worst offender) / CAPTCHA'd / needs login state → **BrowserSkill plugin fallback**: `browser_session` start with the dp URL → `browser_page` wait `load` (do NOT use `networkidle` — Amazon long-polling connections time it out) → `browser_inspect` observe (get `@eN` refs; read title, bullets, variation swatches) → `browser_session` stop when done. See MEMORY.md「网页抓取路径策略」for details.
3. If the browser path is unavailable (extension disconnected / browser closed) → **stop crawling and ask the user to paste** competitor title + bullets manually (match format: title line, then bullet lines).

Do NOT install/run playwright or drive browsers via curl — the BrowserSkill plugin is the only sanctioned browser automation on this machine.

### Keyword Analysis — use the bundled script
Script: `%USERPROFILE%\.dsh\skills\amazon-listing\scripts\kw_analysis.py` — run with `python` (stdlib only; this machine's `python3` is a broken stub). Feed it the collected competitor text (each title followed by its bullets in a UTF-8 txt file; script auto-assigns alternating blocks: odd blocks = titles of 5 competitors, even = their bullets — OR simpler: pass two files: titles.txt (one per line), bullets.txt (one per line)).

```pwsh
# Recommended layout: one file, title line first, bullet lines after, blank line between competitors
python "$env:USERPROFILE\.dsh\skills\amazon-listing\scripts\kw_analysis.py" -i competitors.txt
```

Methodology — script outputs the weighted 1-gram/2-gram ranking only; the agent completes the rest on top of it:
1. Script clean: lowercase, strip punctuation, keep alphanumerics + `@` (so 8K@60Hz survives as one token), normalize unicode.
2. Script count: 1-gram + 2-gram with **title ×3 weight, bullets ×1**; output ranked list.
3. Agent completes (script does NOT implement): merge same-root variants (charger/charging → charger primary); mark terms present in ≥3 competitor titles as strong core candidates.
4. Agent takes top 10 as core keywords (mark those that define the category identity vs mere attributes).

### Output (Section 1 of the .md file)
Markdown table: Rank / Keyword / Score / Title Count / Bullet Count / Cross-Competitor, plus Variants table, plus competitor links list.

**STOP — ask user to confirm keywords before Step 2.**

---

## Step 2 — Title (≤75) + Item Highlights (≤125)

### Inputs
- Confirmed top-10 keywords (Step 1)
- Product image (vision analysis: color/material/features — optional, only if user provides)
- Product specs / claimed features (free text). **All features written into the listing must trace to user-provided claims.** Competitor-only claims (HDCP, VRR, Dolby, braided nylon, certifications...) are `[待确认]` until user confirms.

### Title writing (75-char budget)
1. Front-load: #1 keyword (category core, e.g. "Cable HDMI 2.1") in first 3–5 words, then #2/#3 (attribute keywords), then specs.
2. With 75 chars you CANNOT fit all top-10 — decide the split: what goes in title vs highlights vs bullets vs backend:
   - Title: category identity + 1–2 strong attributes + one spec (usually length/规格)
   - Highlights: compatibility list, use cases, benefits
   - Bullets: detail playground
   - Backend: leftovers (synonyms/long-tail)
3. Count chars INCLUDING spaces; target ≤ 73 (safety margin so highlights always render). Never time the exact 75.
4. Read naturally; no keyword stuffing; word repetition ≤2; all facts traceable to Step 2 inputs.

### Item Highlights writing (125-char total budget)
1. Attribute/benefit phrases separated by `;` — no full sentences, no repeated title terms.
2. Order by search value: compatibility > use case > benefit > certification.
3. Count total chars ≤ 125; combined title+highlights ≤ 200.
4. Unverified claims → `[待确认]` markers; ask user before finalizing.

### Output (Section 2 of the .md file)
```markdown
## 2. Title & Item Highlights
### Title
> [title] (chars: N/75)
### Item Highlights
> [field text] (chars: N/125)
**Combined**: N/200  |  Keywords placed: title=[...], highlights=[...]
### Title/Highlight keyword allocation table (keyword → where placed)
```
**STOP — user confirms title+highlights before Step 3.**

---

## Step 3 — Bullet Points (5 × ≤500 chars)

- Bullet 1: primary use case / core value (embed #3/#4 leftovers)
- Bullet 2: key feature (codecs, refreshrates, certification — pending user confirmation if not claimed)
- Bullet 3: material/build quality
- Bullet 4: dimensions/compatibility details
- Bullet 5: package contents / warranty / bonus
- One benefit group per bullet; never duplicate title/highlight phrasing verbatim (paraphrase to extend coverage, not to stuff).

Append Section 3 to the .md file with per-bullet char counts + keyword placement table. **STOP — confirm before Step 4.**

---

## Step 4 — Backend Search Terms (≤249 bytes) — V3 词组方案（2026-09 用户改造）

> 核心原则：后台搜索词**先于广告**完成，上架即用满字节；报表数据只做后续优化替换，不被动等待。禁止碎片词，只装**完整、有明确指向、与产品强相关**的词组。

1. **素材源（优先级，零臆造）**：
   ① 卖家精灵 overlay「自然流量词/关键词调研」——本 ASIN 真实排名词组（含流量占比/月搜索量，最高优先）
   ② ABA/关键词调研数据文件
   ③ 竞品标题词形 + 评论客户语言
2. **形态 = 完整词组（phrase）**：客户搜的是有指向的词组（如 "teclado para tablet samsung"），不是孤立碎片。**禁止**单介词/单数字/单后缀碎片（plus、con、ñ、2m 单独出现均无效）。搭配词必须组成有指向的短语。
3. **相关性门槛（橡皮/笔规则）**：词组意图必须能由本产品满足；高流量但无关的词一律不收。设备词（如 "galaxy tab a9 plus"）只有当本链接已实际出现在其搜索结果时才成立。
4. **三层落位先于后台**：真实词组优先落标题/亮点（权重高）。后台词组按 `真实搜索偏好 × 新词覆盖率` 排序装填：
   - 词组含未入位新词 → 收
   - 词组整句 100% 已被标题/亮点/五点覆盖 → 跳过（零边际值，字节让给新覆盖词组）
   - 同义/拼写变体以**完整词组**形式收（无重音变体、英文变体）
5. **上架即装满 249 字节**：不预留等待报表；剩余字节继续装下一优先级词组。无素材可装时才允许留空并在文件中说明原因。
6. **格式**：小写、单空格、无逗号分隔符；无竞品品牌/ASIN/促销词；兼容设备品牌允许（非竞品）；单复数取一；字节按 UTF-8 计（西语重音字符=2 字节）。
7. **输出**：词组字符串 + 字节数 + **每条词组出处表**（真实词/流量占比/竞品/评论）+ 相关性自检记录。

Append Section 4. Summary block at file end: marketplace / product / title chars / highlights chars / bullets avg / backend bytes / date.

---

## Step 5 — Post-Launch Feedback Loop (广告联动, delayed 1–2 weeks)

After the new listing goes live and accumulates ~1–2 weeks of ad data:
1. Pull search-term report (see amazon-ad-analysis skill): check that the new core keywords (the ones placed in title/highlights) are gaining impressions and converting.
2. High-efficiency uncovered terms → consider promoting into title/highlights on next iteration.
3. If old long-tail keywords still spend without conversion → negative-keyword them or pause ad groups.
4. Record results into the same .md file (Section 5) as a closed loop.

---

## Notes
- <3 competitor links → warn about reliability, proceed.
- No product image → skip visual analysis.
- Communicate in the user's language.
- .md is built progressively; never overwrite earlier sections.
- Marketplace not in localization table → ask user for tone/language preferences.
- 使用指南与踩坑记录：见同目录 `GUIDE.md`。

## 实战禁止清单(踩坑记录)
- 75 恰好不触发亮点展示 → 永远留余量(≤73)。
- 亮点是**单字段 125 总预算**,不是每条 125。
- 亮点与标题**逐词去重**(连 eARC/HDR 这种词也算重复,用收益表达替代)。
- 竞品高频词(HDCP/VRR/Dolby/认证)≠ 本产品支持 → 一律 `[待确认]`。
- 标题超过旧上限时,后台搜索词是唯一还能装关键词的地方→ Step 4 优先承接未入位关键词。
- **后台搜索词禁碎片词**(plus/con/单字 ñ 这类无指向碎片=无效字节)→ 必须是完整有指向词组且过产品相关性门槛(2026-09 用户实证)。
- **后台搜索词上架即用满 249B**,不得以"等广告报表回填"为由留空——报表只做后续优化替换。