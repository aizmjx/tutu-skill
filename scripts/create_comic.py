#!/usr/bin/env python3
"""
SuperTuTu — 漫画生成脚本
用法:
    python create_comic.py --content "故事内容" [--title "标题"] [--shots 4] [--ratio 1:1] [--style-id 12]
环境变量:
    SUPERTUTU_API_KEY   必填，ak_ 开头的 API Key
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
POLL_INTERVAL = 4   # 秒
MAX_POLLS = 75      # 5 分钟超时


def headers():
    key = os.environ.get("SUPERTUTU_API_KEY", "")
    if not key:
        sys.exit("❌ 未设置 SUPERTUTU_API_KEY 环境变量")
    return {"X-API-KEY": key, "Content-Type": "application/json"}


def submit(content, title, shot_count, aspect_ratio, style_type_id):
    body = {
        "content": content,
        "shotCount": shot_count,
        "aspectRatio": aspect_ratio,
    }
    if title:
        body["title"] = title
    if style_type_id:
        body["styleTypeId"] = style_type_id

    r = requests.post(f"{BASE_URL}/comic", json=body, headers=headers(), timeout=30)
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

    sys.exit(f"⏰ 超时（{MAX_POLLS * POLL_INTERVAL}s），workId={work_id}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--content", required=True, help="故事文案（≤5000字）")
    ap.add_argument("--title", default="", help="标题（可选，AI 自动生成）")
    ap.add_argument("--shots", type=int, default=4, help="格数 1-8，默认 4")
    ap.add_argument("--ratio", default="1:1", help="比例，默认 1:1")
    ap.add_argument("--style-id", type=int, default=None, help="风格 ID（workspace_types.id）")
    args = ap.parse_args()

    print("📤 提交漫画生成任务…", file=sys.stderr)
    work_id = submit(args.content, args.title, args.shots, args.ratio, args.style_id)

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
