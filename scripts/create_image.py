#!/usr/bin/env python3
"""
SuperTuTu — 自定义生图脚本
用法:
    python create_image.py --prompt "画面描述" [--title "标题"] [--ratio 1:1] [--seed 42]
环境变量:
    SUPERTUTU_API_KEY   必填，ak_ 开头的 API Key

注意: 结果在 coverImageUrl，shots[] 为空——这与漫画/配图不同。
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
MAX_POLLS = 75


def headers():
    key = os.environ.get("SUPERTUTU_API_KEY", "")
    if not key:
        sys.exit("❌ 未设置 SUPERTUTU_API_KEY 环境变量")
    return {"X-API-KEY": key, "Content-Type": "application/json"}


def submit(prompt, title, aspect_ratio, seed):
    body = {"prompt": prompt, "aspectRatio": aspect_ratio}
    if title:
        body["title"] = title
    if seed is not None:
        body["seed"] = seed

    r = requests.post(f"{BASE_URL}/image", json=body, headers=headers(), timeout=120)
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
    ap.add_argument("--prompt", required=True, help="图像描述（≤2000字符，英文效果更佳）")
    ap.add_argument("--title", default="", help="标题（可选）")
    ap.add_argument("--ratio", default="1:1", help="比例，默认 1:1")
    ap.add_argument("--seed", type=int, default=None, help="随机种子（可选，复现用）")
    args = ap.parse_args()

    print("📤 提交自定义生图任务…", file=sys.stderr)
    work_id = submit(args.prompt, args.title, args.ratio, args.seed)

    work = poll(work_id)

    # custom_image 结果在 coverImageUrl，shots[] 为空
    cover = work.get("coverImageUrl", "")
    result = {
        "workId": work_id,
        "title": work.get("title", ""),
        "imageUrl": cover,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
