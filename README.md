# SuperTuTu Creator Skill

A [Claude Code skill](https://claude.ai/code) for the [SuperTuTu](https://tutu.aizmjx.com) AI creative platform.

Enables Claude to create AI-generated comics, article illustrations, and custom images via the SuperTuTu Open Platform API (`/v1/openapi`).

- **[SKILL.md](./SKILL.md)** — how Claude uses this skill (trigger words, decision flow, examples)
- **[API.md](./API.md)** — full Open Platform API reference (endpoints, schemas, error codes)

## Features

- **空间发现** — list "我的空间" for stable comic creation with locked parameters (`list_workspaces.py`) — **recommended entry point**
- 漫画生成 — multi-panel comic strips, supports `--workspace-id` for locked-param creation (`create_comic.py`)
- 文章配图 — article illustrations, 8 styles (`create_article_illustration.py`)
- 自定义生图 — direct prompt-to-image (`create_image.py`)
- 分镜提示词 — prompt-only, no image generation, supports `--workspace-id` (`create_prompt.py`)
- **分步精修** — review and edit each shot's caption / dialogue / prompt before image generation (`update_shot.py`)
- **续接生图** — trigger image generation using the latest (edited) prompts without re-running LLM (`render_work.py`)
- **状态智检** — query a work's full status with progress summary to avoid missing async shots (`check_work.py`)
- 风格发现 — list available comic / illustration styles (`list_styles.py`)
- 作品查询 — paginated work list (`list_works.py`)
- **帮助卡** — quick-reference card for end users (`help.py`)

## Usage

With the skill loaded, Claude handles the full async flow automatically:

1. Submits the creation job → gets `workId`
2. Polls `GET /work/{workId}` every 4–6s (adaptive backoff) until `status = completed`
3. Returns all image URLs as JSON to stdout, progress logs to stderr

Each script supports `--api-key ak_xxx` or `SUPERTUTU_API_KEY` env var (CLI flag takes precedence).

On timeout the scripts return whatever shots have already finished — they don't throw away progress.

## Auth

All requests use the `X-API-KEY` header (SuperTuTu Open Platform API key).

Get one at <https://sso.aizmjx.com/home/apikey>.

## Requirements

- Python 3.9+
- `pip install requests`

## Files

```
tutu-skill/
├── SKILL.md                              # Skill manifest + Claude usage guide
├── README.md                             # This file
└── scripts/
    ├── _client.py                        # Shared HTTP client (do not run directly)
    ├── create_comic.py                   # POST   /comic
    ├── create_article_illustration.py    # POST   /article-illustration
    ├── create_image.py                   # POST   /image
    ├── create_prompt.py                  # POST   /prompt              (prompt-only, no image)
    ├── update_shot.py                    # PATCH  /shot/{id}/caption   (per-shot precise edits)
    │                                     # PATCH  /shot/{id}/dialogue
    │                                     # PUT    /shot/{id}/prompt
    ├── render_work.py                    # POST   /work/{id}/render    (resume image generation w/ edits)
    ├── check_work.py                     # GET    /work/{id}           (smart status check, prevents missing shots)
    ├── list_workspaces.py                # GET    /workspaces          (my workspaces, recommended entry)
    ├── list_styles.py                    # GET    /styles              (style discovery)
    ├── list_works.py                     # GET    /works               (paginated list)
    └── help.py                           # —                           (quick reference card, no API key needed)
```
