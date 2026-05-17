#!/usr/bin/env python3
"""SuperTuTu — 仅生成分镜提示词（不生图）。

用法:
    python create_prompt.py --content "故事文案" [--title "标题"]
                            [--shots 4] [--style-id 12]
                            [--api-key ak_xxx]

适合"想先看 prompt 再决定要不要生图"或"拿提示词去别的图像服务"的场景。
轮询到 shots[].status == "ready" 即终止，比走完整生图省时省积分。

API Key 两种传入方式（任选其一）：
    1) 命令行参数：--api-key ak_xxx
    2) 环境变量：  export SUPERTUTU_API_KEY=ak_xxx

输出（stdout，JSON 格式）：
    {
      "workId": "...",
      "title": "...",
      "status": "completed|failed|timeout",
      "shots": [
        {"shotIndex": 0, "prompt": "...", "caption": "..."},
        ...
      ]
    }
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _client import failure_hint, poll_until_done, post, resolve_api_key  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="SuperTuTu 仅生成分镜提示词")
    ap.add_argument("--content", required=True, help="故事文案（≤5000 字）")
    ap.add_argument("--title", default="", help="标题（可选）")
    ap.add_argument("--shots", type=int, default=4, help="格数 1-8（默认 4）")
    ap.add_argument("--style-id", type=int, default=None,
                    help="风格 ID（workspace_types.id）")
    ap.add_argument("--api-key", default=None,
                    help="API Key（优先于 SUPERTUTU_API_KEY 环境变量）")
    args = ap.parse_args()

    api_key = resolve_api_key(args.api_key)

    body: dict = {
        "content": args.content,
        "shotCount": args.shots,
    }
    if args.title:
        body["title"] = args.title
    if args.style_id is not None:
        body["styleTypeId"] = args.style_id

    print("📤 提交分镜提示词生成任务…", file=sys.stderr)
    data = post("/prompt", body, api_key)
    work_id = data.get("workId")
    if not work_id:
        sys.exit(f"❌ 后端未返回 workId：{data}")

    # ready_means_done=True：shots 全部到 ready 即视为完成（不必等图像生成）
    work, status = poll_until_done(work_id, api_key, ready_means_done=True)

    shots_out = []
    for s in sorted(work.get("shots") or [], key=lambda x: x.get("shotIndex") or 0):
        if s.get("prompt"):
            shots_out.append({
                "shotIndex": s.get("shotIndex"),
                "prompt": s.get("prompt"),
                "caption": s.get("caption") or "",
            })

    if status == "failed":
        print(f"\n❌ 提示词生成失败。{failure_hint(work_id, work)}", file=sys.stderr)
    elif status == "timeout":
        print(f"\n⚠️  超时但保留 {len(shots_out)} 个已就绪分镜。{failure_hint(work_id, work)}", file=sys.stderr)

    result = {
        "workId": work_id,
        "title": work.get("title", ""),
        "status": status,
        "shots": shots_out,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if status == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
