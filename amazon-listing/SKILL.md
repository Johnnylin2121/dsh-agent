---
name: amazon-listing
description: >
  Amazon listing optimization workflow. Use when the user wants to analyze competitor
  listings to extract core keywords, write optimized titles + bullet points with keyword
  embedding, and generate backend search terms. Supports any Amazon marketplace.
  Handles browser-based crawling, keyword frequency/position analysis, and listing
  localization. Triggered when user mentions "亚马逊 listing", "竞品分析", "关键词",
  "标题五点", "后台搜索词", or similar requests.
---

# Amazon Listing Optimization Workflow

## Overview

Four-step workflow for Amazon listing creation from competitor analysis:

**Step 0** — Confirm target marketplace
**Step 1** — Crawl competitor listings, extract top 10 core keywords
**Step 2** — Write title + 5 bullet points with keyword embedding
**Step 3** — Generate backend search terms

The user expects a **single unified `.md` file** on their desktop at the end of each step (progressively built), with 4 sections. Pause at the end of each step for user review before continuing.

## Amazon Listing Rules (Hardcoded)

These constraints are non-negotiable and must be applied at every step.

### Character/Bytes Limits
| Field | Limit | Notes |
|-------|-------|-------|
| Title | 200 characters | Some categories cap at 80 or 150; ask if unsure |
| Bullet point | 500 characters per bullet | 5 bullets total |
| Backend search terms | 249 bytes | Bytes, NOT characters. Non-ASCII chars use 2+ bytes |

### Prohibited Content (Title & Bullets)
- ❌ Promotional claims: "best seller", "#1", "top rated", "100% quality"
- ❌ Price mentions: "cheap", "affordable", "discount", "on sale"
- ❌ Guarantee/refund language: "money back", "satisfaction guaranteed"
- ❌ Subjective superlatives: "amazing", "incredible", "fantastic", "perfect"
- ❌ Shipping/time claims: "free shipping", "fast delivery", "2-day arrival"
- ❌ Contact info: email, phone, URLs, external site references
- ❌ HTML tags, emojis, special symbols (®, ™, © are OK)
- ❌ ALL CAPS words (except for standard abbreviations like USB, HDMI, LED)

### Backend Search Terms Rules
- ❌ Do NOT repeat any word already present in Title or Bullets
- ❌ No brand names
- ❌ No ASINs
- ❌ No promotional/subjective terms
- ❌ No commas, semicolons, or separators — use single spaces
- ❌ Singular covers plural; don't include both
- ❌ Case-insensitive; use lowercase
- ✅ Include: synonyms, alternate names, common misspellings, alternate-language terms (e.g. Spanish for US market), complementary product terms

### Title Capitalization by Marketplace
- **Amazon.com (US)**: Capitalize first letter of each word (except articles/prepositions ≤ 3 letters)
- **Amazon.co.uk (UK)**: Same as US
- **Amazon.de (DE)**: German capitalization rules (nouns capitalized)
- **Amazon.co.jp (JP)**: Japanese conventions; no English capitalization rules apply to JP text
- **Amazon.fr / .es / .it**: Follow respective language conventions

---

## Step 0 — Confirm Target Marketplace

Ask the user which marketplace (site) they intend to list on. If the user does not specify, default to the marketplace of the competitor links they provide.

Examples: `Amazon.com` (US), `Amazon.co.uk` (UK), `Amazon.de` (Germany), `Amazon.co.jp` (Japan), `Amazon.ca` (Canada), `Amazon.fr` (France), `Amazon.es` (Spain), `Amazon.it` (Italy), `Amazon.com.au` (Australia)

Once confirmed, proceed to Step 1.

---

## Step 1 — Extract Top 10 Core Keywords

### Input
User provides 1–5 Amazon competitor ASINs or full product URLs (all same marketplace as Step 0).

### Crawling Methodology

**Preferred when dsh-shop-assistant is installed**: use `shop_page_snapshot` on each competitor's **public product URL** to fetch title + description + visible price clues. This is the first choice for public (buyer-visible) pages — apply the snapshot, then skip straight to keyword analysis. Do NOT ask the user to log into a seller console, and do not invent stock/promotions.

**Primary (no shop plugin, or seller-only pages)**: Browser automation via playwright (Node.js):

```bash
# If playwright not installed:
npm init -y  (in a temp dir like {TEMP}/amz-scrape)
npm install playwright
npx playwright install chromium

# Scrape each URL — extract the page text (title, bullets, description)
# Use playwright to navigate, wait for content load, then extract:
# - document.querySelector('#productTitle') -> title
# - document.querySelectorAll('#feature-bullets .a-list-item') -> bullets
```

The scraper should extract:
1. **Title** — `#productTitle` text content
2. **Bullet points** — ALL `#feature-bullets .a-list-item` or `#feature-bullets li` text
3. **Description (optional, secondary)** — `#productDescription` or A+ content blocks

**Fallback**: If browser automation fails (CAPTCHA, blocking), ask the user to manually copy-paste the title and bullet points for each competitor. Do NOT loop indefinitely retrying.

### Keyword Analysis Methodology

After obtaining all competitor texts, perform analysis:

1. **Collect raw text**: All titles and bullets from all competitors.

2. **Clean**:
   - **EXCLUDE** brand words and store/seller names (user confirms which words are brand names if unsure; default to removing the first word(s) of each title that match across competitors as likely brand)
   - **DO NOT exclude** stop words (e.g. "for", "with", "and", "in", "on", "the", "a", "an"). These are part of natural search phrases.
   - Remove punctuation/symbols, normalize to lowercase for counting
   - Normalize unicode (full-width to half-width etc.)

3. **Word frequency analysis**:
   - Count occurrences of every word (1-gram) across all titles AND across all bullets
   - Count occurrences of every 2-word phrase (2-gram) across all titles (higher weight for 2-grams that appear in titles)
   - Count occurrences of every 3-word phrase (3-gram) that appears at least once in a title

4. **Title weight boost** (position-weighted scoring):
   - Words appearing in a competitor **title** get a **3× weight multiplier** vs words only in bullets
   - Within a title, words appearing earlier get a small additional boost (first 3 positions: 1.2×, positions 4–6: 1.1×)
   - A word/phrase appearing in 3+ competitor titles → strong core keyword candidate

5. **Merge same-root words**:
   - Group morphological variants (e.g. "charger", "charging", "charge") under the highest-frequency form as the primary keyword
   - List variants below the primary keyword in output as sub-items
   - The primary form counts toward the top-10 slot; variants are informational

6. **Score formula** (approximate):
   ```
   keyword_score = (count_in_titles × 3) + (count_in_bullets × 1) + (cross_competitor_bonus: +2 per additional competitor) + (title_position_bonus: +0.2 to +0.4)
   ```

7. **Select top 10**: Rank by score descending. These are the **core keywords**.

### Output (Section 1 of the .md file)

Write to `~/Desktop/<product-name>-listing.md` (ask user for product name for filename or use a generic placeholder).

Format:

```markdown
# Amazon Listing — [Product Name] — [Marketplace]

## 1. Core Keywords (Top 10)

| Rank | Keyword | Score | Title Count | Bullet Count | Cross-Competitor |
|------|---------|-------|-------------|--------------|------------------|
| 1    | ...     | ...   | ...         | ...          | ...              |
| 2    | ...     | ...   | ...         | ...          | ...              |
| ...  | ...     | ...   | ...         | ...          | ...              |

### Variants (same-root words merged under primary keyword)

| Primary | Variants |
|---------|----------|
| charger | charging, charge |
| ...     | ...      |

### Competitor Links Analyzed
- [link 1]
- [link 2]
- ...
```

After output, **STOP and ask the user to review/confirm** the keywords. Do NOT proceed to Step 2 until the user explicitly says to continue.

---

## Step 2 — Write Title & Bullet Points

### Input
- **Confirmed core keywords** (from Step 1)
- **Product main image** — user provides the image file. Use vision analysis to identify: product color, shape, material, key features, visible components, use scenario. Incorporate these visual findings into the listing copy to ensure accuracy.
- **Product specs/parameters** (user provides): dimensions, weight, material, color variants, included accessories, compatibility info, capacity, etc. User may provide these as free text, a spec sheet, or bullet points.

### Keyword Embedding Rules

1. **Weight-order priority embedding** (highest → lowest score):
   - Top 3 core keywords **MUST** appear in the Title
   - Keywords ranked 1–7 should appear in Title + Bullets
   - Keywords ranked 8–10 should appear in Bullets (or Title if space permits)

2. **Title embedding strategy**:
   - Place the #1 core keyword as early as possible in the title (within first 3–5 words if natural)
   - Front-load: brand (if provided by user) → #1 keyword → #2 keyword → key feature → #3 keyword → spec → variant info
   - Never exceed 200 characters
   - Read naturally to a native speaker — do not keyword-stuff

3. **Bullet points embedding strategy**:
   - 5 bullets, each ≤ 500 characters
   - First bullet: primary use case / core value prop → embed keywords #3, #4
   - Second bullet: key feature → embed keywords #4, #5
   - Third bullet: material/build quality → embed keywords #5, #6, #7
   - Fourth bullet: dimensions/compatibility → embed keywords #6, #7, #8
   - Fifth bullet: package contents / warranty / bonus info → embed keywords #8, #9, #10
   - Vary this template based on what product specs the user provides
   - Each bullet should focus on a **single benefit or feature group** — don't cram multiple unrelated facts into one bullet

4. **Natural language priority**: NEVER sacrifice readability for keyword density. If a keyword feels forced, drop it rather than creating unnatural copy.

### Localization

Adapt the listing copy to the target marketplace's native language:

| Marketplace | Language | Tone |
|-------------|----------|------|
| .com | US English | Direct, benefit-driven, professional |
| .co.uk | UK English | Similar to US but with UK spelling (colour, metre, aluminium, etc.) |
| .de | German | Formal, technical, precise; ALL nouns capitalized per German rules |
| .co.jp | Japanese | Polite, detailed, trust-building; use katakana for foreign words |
| .ca | English (or French for QC) | Similar to US English |
| .fr | French | Formal, elegant, feature-focused |
| .es | Spanish | Warm, benefit-driven |
| .it | Italian | Stylish, design-conscious |
| .com.au | Australian English | Similar to UK English with AU spelling |

If the marketplace uses a language you are not confident in, warn the user and suggest manual review by a native speaker.

### Output (Section 2 of the .md file)

Append to the same `.md` file:

```markdown
## 2. Title & Bullet Points

### Title
> [Full title text, character count: N]

### Bullet Points
- **Bullet 1**: [text] (chars: N) [Keywords embedded: ...]
- **Bullet 2**: [text] (chars: N) [Keywords embedded: ...]
- **Bullet 3**: [text] (chars: N) [Keywords embedded: ...]
- **Bullet 4**: [text] (chars: N) [Keywords embedded: ...]
- **Bullet 5**: [text] (chars: N) [Keywords embedded: ...]

### Keyword Embedding Summary
| Keyword (Rank) | In Title? | In Bullets? | Bullet # |
|----------------|-----------|-------------|----------|
| kw1 (1)        | ✅        | ✅          | 1,2      |
| kw2 (2)        | ✅        | ✅          | 1,3      |
| ...            | ...       | ...         | ...      |
```

After output, **STOP and ask the user to review/confirm** the title and bullets. Do NOT proceed to Step 3 until the user explicitly says to continue.

---

## Step 3 — Generate Backend Search Terms

### Input
- Core keywords (Step 1)
- Finalized title and bullets (Step 2) — specifically all words already used

### Methodology

1. **Collect used words**: Extract all unique lowercase words from the finalized Title and Bullets. This is the "exclusion set" — these words CANNOT appear in backend search terms.

2. **Generate candidates** from these sources:
   - Core keywords NOT fully embedded in the listing
   - Synonyms of core keywords (especially those visible in competitor listings)
   - Common alternate names for the product/category
   - Common misspellings (e.g., "bluetooth" → "blutooth", "charger" → "chargre")
   - Complementary product terms (e.g., if product is a phone case, add "screen protector", "tempered glass" — related items buyers might search for together)
   - Alternate-language terms relevant to the marketplace (e.g., for Amazon.com US, include common Spanish terms; for Amazon.ca, include French terms)
   - Long-tail phrases not already embedded

3. **Filter**:
   - Remove all words/phrases that contain any word from the exclusion set
   - Remove brand names
   - Remove promotional/subjective terms
   - Remove ASINs or identifiers

4. **Assemble**:
   - Combine remaining terms with single spaces (no commas, no separators)
   - Prioritize: synonyms > misspellings > alternate-language > complementary > low-priority long-tail
   - Truncate to ≤ 249 **bytes** (check byte length, not character length)
   - Don't pad with filler — only meaningful terms

### Output (Section 3 of the .md file)

Append to the same `.md` file:

```markdown
## 3. Backend Search Terms

> [flat space-separated search terms string]

**Byte count**: N / 249

### Terms Included
| Term | Source | Reason |
|------|--------|--------|
| ...  | ...    | ...    |

### Exclusion Set (words already in listing)
[comma-separated list of excluded words]
```

### Final Summary

At the end of the .md file, add a short summary block:

```markdown
---
**Marketplace**: [marketplace]
**Product**: [product name]
**Core Keywords**: [top 3 comma-separated]
**Title chars**: N / 200
**Bullet avg chars**: N / 500
**Backend bytes**: N / 249
**Generated**: [date]
---
```

---

## Notes

- If the user provides less than 3 competitor links, warn that keyword analysis may be less statistically reliable, but proceed.
- If the user does NOT have a product image, proceed with specs only; skip visual analysis.
- Always communicate in the same language as the user.
- The .md file is progressively built — don't overwrite previous sections.
- If a marketplace is not listed in the localization table above, ask the user for tone/language preferences.