---
name: supertutu-creator
description: >
  Use this skill to create AI-generated comics, article illustrations, and custom images
  via the SuperTuTu Open Platform API. Trigger whenever the user wants to generate a comic
  (漫画), article illustration (文章配图), or a custom image using a prompt — even if they
  don't say "SuperTuTu" explicitly. Also use this skill to check the status of ongoing
  generation tasks or browse previously created works. This skill handles the full async
  flow: submit a job, poll until complete, and return the final image URLs.
---

# SuperTuTu Creator Skill

SuperTuTu is an AI creative platform for Chinese content creators. This skill lets you
create comics, article illustrations, and custom images via its Open Platform API, then
poll until the results are ready.

## Configuration

```
BASE_URL = http://localhost:10001/api/v1/openapi
API_KEY  = YOUR_API_KEY
```

All requests require:
```
X-API-KEY: <API_KEY>
Content-Type: application/json
```

All responses follow the envelope:
```json
{ "code": 200, "message": "...", "data": { ... } }
```
A `code` other than 200 means failure — surface the `message` to the user.

---

## Endpoints

### POST /comic — 漫画生成

Submit a comic generation job. The LLM first generates per-panel prompts, then auto-triggers
image generation. No second call needed.

**Request body:**
```json
{
  "content":     "故事文案（必填，300字以上效果更佳，≤5000字）",
  "title":       "标题（可选，留空 AI 自动生成）",
  "shotCount":   4,        // 分镜格数 1-8，默认 4
  "aspectRatio": "1:1",   // 默认 1:1
  "styleTypeId": null      // workspace_types.id，不填用默认风格
}
```

**Result location:** `shots[].imageUrl` (poll `GET /work/{workId}` until completed)

---

### POST /article-illustration — 文章配图

Generate illustrations to accompany an article.

**⚠️ articleContent must be at least 300 characters.** If the user's snippet is shorter, ask for
the full article text before submitting.

**Request body:**
```json
{
  "articleContent":      "文章正文（必填，≥300字，≤5000字）",
  "imageCount":          4,
  "illustrationStyleId": null,
  "illustrationStyle":   "warm_illustration",
  "aspectRatio":         "3:4",
  "generationMode":      "pure_image",
  "characterId":         null,
  "referenceImageUrls":  []
}
```

Must provide either `illustrationStyleId` OR `illustrationStyle`.

**Style key mapping:**
| User says | illustrationStyle |
|---|---|
| 职场 / 商务 / 工作 | `workplace` |
| 温暖 / 治愈 / 插画 | `warm_illustration` |
| 小红书 / 红薯 | `rednote` |
| 知识 / 信息图 / 图解 | `infographic` |
| 幽默 / 搞笑 | `humor` |
| 故事 / 叙事 | `narrative` |
| 文艺 / 文学 | `literary` |
| 可爱 / Q版 | `cute` |

**Result location:** `shots[].imageUrl`

---

### POST /image — 自定义生图

Direct image generation from a prompt — no LLM phase, fastest option.
Seedream 5.0 works best with English prompts.

**Request body:**
```json
{
  "prompt":      "提示词（必填，≤2000字符）",
  "title":       "标题（可选）",
  "aspectRatio": "1:1",
  "seed":        null
}
```

**⚠️ Result location differs:** image is in `coverImageUrl` at the work level, NOT in `shots[]`.
Poll `GET /work/{workId}` until `status = "completed"`, then read `data.coverImageUrl`.

---

### POST /prompt — 仅生成分镜提示词（不生图）

```json
{
  "content":     "故事文案（必填，≤5000字）",
  "title":       "标题（可选）",
  "shotCount":   4,
  "styleTypeId": null
}
```

After polling: `shots[].status = "ready"` means the prompt is in `shots[].prompt`.

---

### GET /work/{workId} — 查询作品状态

Poll every 4s until `status = "completed"` or `"failed"`.

**Response:**
```json
{
  "workId":        "uuid",
  "status":        "generating | completed | failed",
  "coverImageUrl": "https://...",
  "shots": [
    {
      "shotIndex": 0,
      "status":    "generating | ready | completed | failed",
      "imageUrl":  "https://...",
      "prompt":    "...",
      "caption":   "..."
    }
  ]
}
```

- `comic` / `article_illustration`: results in `shots[].imageUrl`
- `custom_image`: result in `coverImageUrl` (shots is empty)

---

### GET /works — 查询作品列表

Params: `page` (default 1), `pageSize` (1-50), `type` (comic / article_illustration / custom_image)

---

## Polling Flow

All creation endpoints are async — they return a `workId` immediately.

```
1. Call creation endpoint → get workId from response.data.workId
2. Tell user: "已提交，正在生成，稍等片刻…"
3. Loop (every 4s):
   a. GET /work/{workId}
   b. status == "completed" → done
   c. status == "failed"    → tell user, offer retry
   d. else                  → keep polling
4. Return results:
   - comic / article_illustration: list shots[].imageUrl in order
   - custom_image: data.coverImageUrl
```

Timeout: After 5 minutes (75 polls), stop and share the workId with the user.

---

## Error Handling

| Error | Action |
|---|---|
| code ≠ 200 | Surface `message` to user |
| status = "failed" | Tell user, offer to retry |
| HTTP 401 | API key invalid |
| "当前已有 N 个作品" | Max 3 concurrent jobs — wait before submitting new one |
| articleContent < 300 chars | Ask user for full article text |

---

## Aspect Ratios

`1:1` square · `3:4` portrait/小红书 · `4:3` landscape · `16:9` wide · `9:16` vertical
