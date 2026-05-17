#!/usr/bin/env python3
"""SuperTuTu — 文章配图脚本。

用法:
    python create_article_illustration.py --content "文章正文（≥300 字）"
                                          [--count 4] [--style warm_illustration]
                                          [--ratio 3:4] [--mode pure_image]
                                          [--character-id 12] [--ref-image URL ...]
                                          [--api-key ak_xxx]

API Key 两种传入方式（任选其一）：
    1) 命令行参数：--api-key ak_xxx
    2) 环境变量：  export SUPERTUTU_API_KEY=ak_xxx

风格可选值（--style）：
    workplace           职场 / 商务
    warm_illustration   温暖 / 治愈（默认）
    rednote             小红书
    infographic         知识图 / 信息图
    humor               幽默 / 搞笑
    narrative           故事 / 叙事
    literary            文艺 / 文学
    cute                可爱 / Q 版

输出（stdout，JSON 格式）：
    {"workId": "...", "title": "...", "imageUrls": [...], "status": "completed|failed|timeout"}
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _client import collect_image_urls, failure_hint, poll_until_done, post, resolve_api_key  # noqa: E402

VALID_STYLES = {
    "workplace", "warm_illustration", "rednote", "infographic",
    "humor", "narrative", "literary", "cute",
}
VALID_MODES = {"pure_image", "text_blend"}
# 配图含 LLM 提示词阶段 + 图像派发，慢于漫画／自定义；轮询上限放宽到 ≈ 15 分钟
ARTICLE_MAX_POLLS = 150


def main() -> None:
    ap = argparse.ArgumentParser(description="SuperTuTu 文章配图（提交并轮询到完成）")
    ap.add_argument("--content", required=True, help="文章正文（≥300 字，≤5000 字）")
    ap.add_argument("--count", type=int, default=4, help="生成张数 1-10（默认 4）")
    ap.add_argument("--style", default="warm_illustration",
                    help=f"风格 key（默认 warm_illustration），可选：{', '.join(sorted(VALID_STYLES))}")
    ap.add_argument("--style-id", type=int, default=None,
                    help="风格 ID（workspace_types.id；若指定则覆盖 --style）")
    ap.add_argument("--ratio", default="3:4", help="画面比例（默认 3:4，小红书/公众号竖图）")
    ap.add_argument("--mode", default="pure_image",
                    help=f"生成模式（默认 pure_image），可选：{', '.join(sorted(VALID_MODES))}")
    ap.add_argument("--character-id", type=int, default=None,
                    help="角色模板 ID（可选，跨张保持角色一致）")
    ap.add_argument("--ref-image", action="append", default=[],
                    help="风格参考图 URL，可重复，最多 3 张")
    ap.add_argument("--api-key", default=None,
                    help="API Key（优先于 SUPERTUTU_API_KEY 环境变量）")
    args = ap.parse_args()

    # 参数校验
    if len(args.content) < 300:
        sys.exit(f"❌ 文章内容过短（{len(args.content)} 字），需要至少 300 字")
    if args.style not in VALID_STYLES:
        sys.exit(f"❌ 无效风格 '{args.style}'，可选：{', '.join(sorted(VALID_STYLES))}")
    if args.mode not in VALID_MODES:
        sys.exit(f"❌ 无效模式 '{args.mode}'，可选：{', '.join(sorted(VALID_MODES))}")
    if len(args.ref_image) > 3:
        sys.exit(f"❌ 参考图最多 3 张，当前 {len(args.ref_image)} 张")

    api_key = resolve_api_key(args.api_key)

    body: dict = {
        "articleContent": args.content,
        "imageCount": args.count,
        "aspectRatio": args.ratio,
        "generationMode": args.mode,
        "referenceImageUrls": args.ref_image,
    }
    if args.style_id is not None:
        body["illustrationStyleId"] = args.style_id
    else:
        body["illustrationStyle"] = args.style
    if args.character_id is not None:
        body["characterId"] = args.character_id

    print("📤 提交文章配图任务…", file=sys.stderr)
    data = post("/article-illustration", body, api_key)
    work_id = data.get("workId")
    if not work_id:
        sys.exit(f"❌ 后端未返回 workId：{data}")

    work, status = poll_until_done(work_id, api_key, max_polls=ARTICLE_MAX_POLLS)
    urls = collect_image_urls(work)

    if status == "failed":
        print(f"\n❌ 配图生成失败。{failure_hint(work_id, work)}", file=sys.stderr)
    elif status == "timeout":
        print(f"\n⚠️  超时但保留 {len(urls)} 张已完成的配图。{failure_hint(work_id, work)}", file=sys.stderr)

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
