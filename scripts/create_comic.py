#!/usr/bin/env python3
"""SuperTuTu — 漫画生成脚本。

用法:
    python create_comic.py --content "故事内容" [--title "标题"] [--shots 4]
                           [--ratio 1:1] [--style-id 12]
                           [--output-mode image_only|split|merged|split_with_bubble]
                           [--api-key ak_xxx]

API Key 两种传入方式（任选其一）：
    1) 命令行参数：--api-key ak_xxx
    2) 环境变量：  export SUPERTUTU_API_KEY=ak_xxx

输出（stdout，JSON 格式）：
    {"workId": "...", "title": "...", "imageUrls": [...], "status": "completed|failed|timeout"}

进度日志写到 stderr，不污染管道。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _client import collect_image_urls, failure_hint, poll_until_done, post, resolve_api_key  # noqa: E402

VALID_OUTPUT_MODES = {"image_only", "split", "merged", "split_with_bubble"}


def main() -> None:
    ap = argparse.ArgumentParser(description="SuperTuTu 漫画生成（提交并轮询到完成）")
    ap.add_argument("--content", required=True, help="故事文案（≤5000 字）")
    ap.add_argument("--title", default="", help="标题（可选，留空 AI 自动生成）")
    ap.add_argument("--shots", type=int, default=4, help="格数 1-8（默认 4）")
    ap.add_argument("--ratio", default="1:1", help="画面比例（默认 1:1）")
    ap.add_argument("--style-id", type=int, default=None,
                    help="风格 ID（workspace_types.id；用 list_styles.py 查询；不填用默认风格）")
    ap.add_argument("--output-mode", default=None,
                    help=("输出模式（可选，缺省 image_only）："
                          "image_only=纯画面 / split=画面配文（字幕条）/ "
                          "merged=气泡对话 / split_with_bubble=字幕+气泡同时"))
    ap.add_argument("--api-key", default=None,
                    help="API Key（优先于 SUPERTUTU_API_KEY 环境变量）")
    args = ap.parse_args()

    if args.output_mode and args.output_mode not in VALID_OUTPUT_MODES:
        sys.exit(f"❌ 无效 --output-mode '{args.output_mode}'，"
                 f"可选：{', '.join(sorted(VALID_OUTPUT_MODES))}")

    api_key = resolve_api_key(args.api_key)

    body: dict = {
        "content": args.content,
        "shotCount": args.shots,
        "aspectRatio": args.ratio,
    }
    if args.title:
        body["title"] = args.title
    if args.style_id is not None:
        body["styleTypeId"] = args.style_id
    if args.output_mode:
        body["outputMode"] = args.output_mode

    print("📤 提交漫画生成任务…", file=sys.stderr)
    data = post("/comic", body, api_key)
    work_id = data.get("workId")
    if not work_id:
        sys.exit(f"❌ 后端未返回 workId：{data}")

    work, status = poll_until_done(work_id, api_key)
    urls = collect_image_urls(work)

    if status == "failed":
        print(f"\n❌ 漫画生成失败。{failure_hint(work_id, work)}", file=sys.stderr)
    elif status == "timeout":
        print(f"\n⚠️  超时但保留 {len(urls)} 张已完成的分镜。{failure_hint(work_id, work)}", file=sys.stderr)

    result = {
        "workId": work_id,
        "title": work.get("title", ""),
        "imageUrls": urls,
        "status": status,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if status == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
