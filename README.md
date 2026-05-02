# SuperTuTu Creator Skill

A [Claude Code skill](https://claude.ai/code) for the [SuperTuTu](https://tutu.aismrti.com) AI creative platform.

Enables Claude to create AI-generated comics, article illustrations, and custom images via the SuperTuTu Open Platform API (`/v1/openapi`).

## Features

- 漫画生成 — multi-panel comic strips
- 文章配图 — article illustrations (8 styles)
- 自定义生图 — direct prompt-to-image
- 分镜提示词 — prompt-only generation
- 作品查询 — list and poll generation status

## Usage

With the skill loaded, Claude handles the full async flow automatically:
1. Submits the creation job → gets `workId`
2. Polls `GET /work/{workId}` every 4s until `status = completed`
3. Returns all image URLs

## Auth

All requests use `X-API-KEY` header (SuperTuTu Open Platform API key).
