---
name: notion-api
description: Notion REST API integration for macOS/zsh environments. Use when working with Notion pages, databases, or blocks — creating, reading, updating, or searching content. Handles authentication, UTF-8 encoding for Chinese content, and reliable JSON construction with jq.
---

# Notion API Integration

## Quick Start

### Authentication

Notion API requires an Internal Integration Token (static, no OAuth refresh needed for basic operations).

**Token location**: Stored in project MEMORY.md under `## Discovered durable knowledge`.

**Header format**:
```
Authorization: Bearer <token>
Notion-Version: 2022-06-28
Content-Type: application/json
```

### Critical JSON Encoding Rule

**Never manually concatenate JSON strings for Notion API requests with Chinese content.** Use `jq` for reliable, properly-encoded JSON.

**Correct approach**: Use `jq` to build JSON and `curl` to send:

```bash
# 1. Build JSON with jq (properly handles Chinese characters)
jq -n '{
  parent: {page_id: "your-page-id"},
  properties: {
    title: {title: [{text: {content: "标题"}}]}
  }
}' > /tmp/notion_request.json

# 2. Send with curl
curl -s -X POST https://api.notion.com/v1/pages /
  -H "Authorization: Bearer ntn_YOUR_TOKEN" /
  -H "Notion-Version: 2022-06-28" /
  -H "Content-Type: application/json" /
  -d @/tmp/notion_request.json
```

## Common Operations

### Search Pages

```bash
jq -n '{query: "search term", filter: {property: "object", value: "page"}}' > /tmp/notion_search.json
curl -s -X POST https://api.notion.com/v1/search /
  -H "Authorization: Bearer $NOTION_TOKEN" /
  -H "Notion-Version: 2022-06-28" /
  -H "Content-Type: application/json" /
  -d @/tmp/notion_search.json
```

### Create Page

```bash
jq -n '{
  parent: {page_id: "parent-page-id"},
  properties: {
    title: {title: [{text: {content: "Page Title"}}]}
  },
  children: [
    {
      object: "block",
      type: "paragraph",
      paragraph: {rich_text: [{type: "text", text: {content: "Content here"}}]}
    }
  ]
}' > /tmp/notion_create.json

curl -s -X POST https://api.notion.com/v1/pages /
  -H "Authorization: Bearer $NOTION_TOKEN" /
  -H "Notion-Version: 2022-06-28" /
  -H "Content-Type: application/json" /
  -d @/tmp/notion_create.json
```

### Update Block (Append Children)

```bash
# Body: JSON array of block objects
curl -s -X PATCH https://api.notion.com/v1/blocks/{block_id}/children /
  -H "Authorization: Bearer $NOTION_TOKEN" /
  -H "Notion-Version: 2022-06-28" /
  -H "Content-Type: application/json" /
  -d @/tmp/notion_blocks.json
```

### Get Page Content

```bash
curl -s https://api.notion.com/v1/blocks/{block_id}/children /
  -H "Authorization: Bearer $NOTION_TOKEN" /
  -H "Notion-Version: 2022-06-28"
```

## Block Types Reference

| Type | Structure |
|------|-----------|
| Paragraph | `paragraph.rich_text[]` |
| Heading 1/2/3 | `heading_1/2/3.rich_text[]` |
| Bulleted list | `bulleted_list_item.rich_text[]` |
| Numbered list | `numbered_list_item.rich_text[]` |
| Divider | `divider = {}` |
| Code | `code.rich_text[]`, `code.language` |
| Image | `image.external.url` or `image.file.url` |

## Rich Text Format

```json
{
    "type": "text",
    "text": {
        "content": "Text content",
        "link": { "url": "https://example.com" }
    },
    "annotations": {
        "bold": true,
        "italic": false,
        "code": false
    }
}
```

## Known Gotchas

1. **Chinese encoding**: Always use `jq` for JSON construction — never manually concatenate JSON strings
2. **Depth limit**: Use `jq` with `--depth` for deeply nested structures
3. **Rate limits**: Notion API allows ~3 requests/second
4. **Block limit**: Max 100 children per `append blocks` call
5. **Page size**: Max 2000 characters per rich_text block

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `401 Unauthorized` | Invalid/expired token | Check token in MEMORY.md |
| `400 Bad Request` | Malformed JSON | Use UTF-8 file approach |
| `409 Conflict` | Concurrent edit | Retry after delay |
| `429 Too Many Requests` | Rate limit | Wait 1 second and retry |
