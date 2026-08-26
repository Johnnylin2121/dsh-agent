---
name: amazon-listing
description: >
  Amazon listing optimization workflow. Use when the user wants to analyze competitor
  listings to extract core keywords, write an optimized title + Item Highlights +
  bullet points with keyword embedding, and generate backend search terms.
  Implements the 2026-07 title policy (title ≤75 chars, Item Highlights ≤125 chars,
  combined ≤200). Supports any Amazon marketplace. Crawling via Jina Reader or
  manual paste (no browser automation). Triggered by "亚马逊 listing", "竞品分析",
  "关键词", "标题五点", "商品亮点", "后台搜索词", or similar.
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

Output: single progressively-built `.md` file written to `{VAULT_PATH}/工作/亚马逊分析/<ASIN>-<product>-listing.md` (DSH: read the vault path from `~/.dsh/MEMORY.md` — never hardcode it).

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
1. **Jina Reader** (DSH standard): `curl -s "https://r.jina.ai/https://www.<marketplace>/dp/<ASIN>"` — parse title/bullets from returned text.
2. If Jina unreachable or CAPTCHA'd → try one direct `curl -A "<desktop UA>"` once; if it returns a robot-check page → **stop crawling and ask the user to paste** competitor title + bullets manually (match format: title line, then bullet lines).

Do NOT install/run playwright unless the host explicitly provides a browser automation setup.

### Keyword Analysis — use the bundled script
Script: `scripts/kw_analysis.py` (python3). Feed it the collected competitor text (each title followed by its bullets in a UTF-8 txt file; script auto-assigns alternating blocks: odd blocks = titles of 5 competitors, even = their bullets — OR simpler: pass two files: titles.txt (one per line), bullets.txt (one per line)).

```bash
# Recommended layout: one file, title line first, bullet lines after, blank line between competitors
python3 scripts/kw_analysis.py -i competitors.txt
```

Methodology (script implements):
1. Clean: lowercase, strip punctuation, keep alphanumerics + `@` (so 8K@60Hz survives as one token), normalize unicode.
2. 1-gram + 2-gram counting with **title ×3 weight, bullets ×1**; 3+ competitor titles containing a term → strong core candidate.
3. Merge same-root variants (charger/charging → charger primary).
4. Output ranked list → take top 10 as core keywords (mark those that define the category identity vs mere attributes).

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

## Step 4 — Backend Search Terms (≤249 bytes)

1. Exclusion set = all unique words in Title + Highlights + Bullets.
2. Candidates: unplaced core keywords, synonyms, misspellings, alternate-language terms, complementary terms, long-tail phrases.
3. Filter: drop anything containing an excluded word; drop brands/ASINs/promo.
4. Assemble: single spaces, no separators; truncate ≤249 **bytes** (verify byte length — accent-marked Spanish chars count 2 bytes).
5. Output flat string + byte count + terms-source table + exclusion set.

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

## 实战禁止清单(踩坑记录)
- 75 恰好不触发亮点展示 → 永远留余量(≤73)。
- 亮点是**单字段 125 总预算**,不是每条 125。
- 亮点与标题**逐词去重**(连 eARC/HDR 这种词也算重复,用收益表达替代)。
- 竞品高频词(HDCP/VRR/Dolby/认证)≠ 本产品支持 → 一律 `[待确认]`。
- 标题超过旧上限时,后台搜索词是唯一还能装关键词的地方→ Step 4 优先承接未入位关键词。