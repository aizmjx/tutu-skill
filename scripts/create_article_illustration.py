#!/usr/bin/env python3
"""
SuperTuTu — 文章配图脚本
用法:
    python create_article_illustration.py --content "文章正文（≥300字）" [--count 4] [--style warm_illustration] [--ratio 3:4]
环境变量:
    SUPERTUTU_API_KEY   必填，ak_ 开头的 API Key

风格可选值:
    workplace           职场 / 商务
    warm_illustration   温暖 / 治愈（默认）
    rednote             小红书
    infographic         知识图 / 信息图
    humor               幽默 / 搞笑
    narrative           故事 / 叙事
    literary            文艺 / 文学
    cute                可爱 / Q版
"""
import argparse
import json
import os
import sys
import time

try:
    import requests
except ImportError:
    sys.exit("缺少依赖：pip install requests")

BASE_URL = "https://tutu.aizmjx.com/api/v1/openapi"
POLL_INTERVAL = 4
MAX_POLLS = 150  # 10 分钟：配图多张并发，比漫画慢

VALID_STYLES = {
    "workplace", "warm_illustration", "rednote", "infographic",
    "humor", "narrative", "literary", "cute",
}


def headers():
    key = os.environ.get("SUPERTUTU_API_KEY", "")
    if not key:
        sys.exit("❌ 未设置 SUPERTUTU_API_KEY 环境变量")
    return {"X-API-KEY": key, "Content-Type": "application/json"}


def submit(content, image_count, style, aspect_ratio):
    if len(content) < 300:
        sys.exit(f"❌ 文章内容过短（{len(content)} 字），需要至少 300 字")
    if style not in VALID_STYLES:
        sys.exit(f"❌ 无效风格 '{style}'，可选：{', '.join(sorted(VALID_STYLES))}")

    body = {
        "articleContent": content,
        "imageCount": image_count,
        "illustrationStyle": style,
        "aspectRatio": aspect_ratio,
        "generationMode": "pure_image",
        "referenceImageUrls": [],
    }

    r = requests.post(f"{BASE_URL}/article-illustration", json=body, headers=headers(), timeout=120)
    r.raise_for_status()
    data = r.json()
    if data.get("code") != 200:
        sys.exit(f"❌ 提交失败：{data.get('message')}")
    return data["data"]["workId"]


def poll(work_id):
    print(f"⏳ workId={work_id}，轮询中…", file=sys.stderr)
    for i in range(MAX_POLLS):
        time.sleep(POLL_INTERVAL)
        r = requests.get(f"{BASE_URL}/work/{work_id}", headers=headers(), timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get("code") != 200:
            sys.exit(f"❌ 查询失败：{data.get('message')}")

        work = data["data"]
        status = work.get("status")
        print(f"  [{i+1}/{MAX_POLLS}] status={status}", file=sys.stderr)

        if status == "completed":
            return work
        if status == "failed":
            sys.exit("❌ 生成失败")

    # 超时但有部分完成的 shots，优雅退出而不是报错
    print(f"⚠️  超时（{MAX_POLLS * POLL_INTERVAL}s），workId={work_id}，返回已完成的 shots", file=sys.stderr)
    return work


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--content", required=True, help="文章正文（≥300字，≤5000字）")
    ap.add_argument("--count", type=int, default=4, help="生成张数，默认 4")
    ap.add_argument("--style", default="warm_illustration", help="风格，默认 warm_illustration")
    ap.add_argument("--ratio", default="3:4", help="比例，默认 3:4（小红书/公众号竖图）")
    args = ap.parse_args()

    print("📤 提交文章配图任务…", file=sys.stderr)
    work_id = submit(args.content, args.count, args.style, args.ratio)

    work = poll(work_id)

    shots = work.get("shots", [])
    urls = [s["imageUrl"] for s in shots if s.get("imageUrl")]

    result = {
        "workId": work_id,
        "title": work.get("title", ""),
        "imageUrls": urls,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
