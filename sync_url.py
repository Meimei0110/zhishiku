#!/usr/bin/env python3
"""
同步知识库URL到 config.json
每次知识库部署后运行此脚本，自动更新 GitHub config.json 中的 url 字段
"""

import urllib.request
import urllib.error
import json
import base64
import os
import sys

# ── 配置 ──────────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_OWNER = "Meimei0110"
REPO_NAME = "zhishiku"
BRANCH = "main"
CONFIG_FILE = "config.json"
TARGET_KEY = "max"  # 要更新的 config.json 中的 key

# URL 可以通过参数传入，也支持从文件读取（方便 CI 传入）
NEW_URL = sys.argv[1] if len(sys.argv) > 1 else None

if not GITHUB_TOKEN:
    print("ERROR: GITHUB_TOKEN 环境变量未设置")
    sys.exit(1)

if not NEW_URL:
    print("ERROR: 请提供新URL作为参数，例如：python3 sync_url.py https://xxx.space.minimaxi.com")
    sys.exit(1)


def github_api(method, path, data=None, headers_extra=None):
    """通用的 GitHub API 请求"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/{path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    if headers_extra:
        headers.update(headers_extra)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    if data and method != "GET":
        req.data = data
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read()) if resp.read() else {}
    except urllib.error.HTTPError as e:
        print(f"API Error {e.code}: {e.reason}")
        print(e.read().decode())
        sys.exit(1)


def get_file_sha(path):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}?ref={BRANCH}"
    req = urllib.request.Request(url, headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())["sha"]


def main():
    print(f"📦 目标仓库: {REPO_OWNER}/{REPO_NAME}")
    print(f"🔗 新URL:   {NEW_URL}")

    # 1. 获取当前 config.json SHA
    sha = get_file_sha(CONFIG_FILE)
    print(f"✅ 当前SHA: {sha}")

    # 2. 下载并解析 config.json
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{CONFIG_FILE}?ref={BRANCH}"
    req = urllib.request.Request(url, headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"})
    resp = urllib.request.urlopen(req)
    config = json.loads(resp.read())

    # 解码内容
    file_content = json.loads(base64.b64decode(config["content"]).decode("utf-8"))
    print(f"📄 当前URL: {file_content.get(TARGET_KEY, {}).get('url', '(空)')}")

    # 3. 更新 URL 和日期
    from datetime import date
    file_content[TARGET_KEY]["url"] = NEW_URL
    file_content[TARGET_KEY]["updatedAt"] = str(date.today())

    print(f"✅ 新URL:   {file_content[TARGET_KEY]['url']}")
    print(f"📅 更新日期: {file_content[TARGET_KEY]['updatedAt']}")

    # 4. 写入 GitHub
    encoded = base64.b64encode(json.dumps(file_content, ensure_ascii=False, indent=2).encode("utf-8")).decode()
    payload = json.dumps({
        "message": f"chore: 自动同步知识库URL → {NEW_URL} ({str(date.today())})",
        "content": encoded,
        "sha": sha,
        "branch": BRANCH,
    }).encode()

    req2 = urllib.request.Request(
        f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{CONFIG_FILE}",
        data=payload,
        headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"},
        method="PUT"
    )
    resp2 = urllib.request.urlopen(req2)
    result = json.loads(resp2.read())

    print(f"🎉 推送成功！")
    print(f"   Commit: {result['commit']['html_url']}")


if __name__ == "__main__":
    main()
