#!/usr/bin/env python3
"""SuperTuTu — 自定义生图脚本（无 LLM 阶段，直接 prompt → 图）。

用法:
    python create_image.py --prompt "画面描述" [--title "标题"]
                           [--ratio 1:1] [--seed 42]
                           [--api-key ak_xxx]

API Key 两种传入方式（任选其一）：
    1) 命令行参数：--api-key ak_xxx
    2) 环境变量：  export SUPERTUTU_API_KEY=ak_xxx

提示：底层模型对英文 prompt 更敏感，中文 prompt 会先被翻译再喂模型。

注意：结果在 work.coverImageUrl，shots[] 为空 —— 这与漫画/配图不同。

输出（stdout，JSON 格式）：
    {"workId": "...", "title": "...", "imageUrl": "...", "status": "completed|failed|timeout"}
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _client import failure_hint, poll_until_done, post, resolve_api_key  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="SuperTuTu 自定义生图（提交并轮询到完成）")
    ap.add_argument("--prompt", required=True, help="图像描述（≤2000 字符，英文效果更佳）")
    ap.add_argument("--title", default="", help="标题（可选）")
    ap.add_argument("--ratio", default="1:1", help="画面比例（默认 1:1）")
    ap.add_argument("--seed", type=int, default=None, help="随机种子（可选，复现同画面用）")
    ap.add_argument("--api-key", default=None,
                    help="API Key（优先于 SUPERTUTU_API_KEY 环境变量）")
    args = ap.parse_args()

    api_key = resolve_api_key(args.api_key)

    body: dict = {"prompt": args.prompt, "aspectRatio": args.ratio}
    if args.title:
        body["title"] = args.title
    if args.seed is not None:
        body["seed"] = args.seed

    print("📤 提交自定义生图任务…", file=sys.stderr)
    data = post("/image", body, api_key)
    work_id = data.get("workId")
    if not work_id:
        sys.exit(f"❌ 后端未返回 workId：{data}")

    work, status = poll_until_done(work_id, api_key)
    cover = work.get("coverImageUrl", "") or ""

    if status == "failed":
        print(f"\n❌ 生图失败。{failure_hint(work_id, work)}", file=sys.stderr)
    elif status == "timeout":
        print(f"\n⚠️  超时但保留最后状态。{failure_hint(work_id, work)}", file=sys.stderr)

    result = {
        "workId": work_id,
        "title": work.get("title", ""),
        "imageUrl": cover,
        "status": status,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if status == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
