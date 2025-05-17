import os
import requests
import time
import json
from datetime import datetime, timezone

# 環境変数の読み込み
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
GITHUB_TOKEN = os.getenv("GH_PAT")
REPO = os.getenv("REPO")
ISSUE_NUMBER = 1

# Notion API ヘッダー
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# データベース全件取得
def fetch_database_pages():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    response = requests.post(url, headers=HEADERS)
    response.raise_for_status()
    return response.json().get("results", [])

# GitHub Issue から最後のチェック日時を取得
def get_last_check_from_issue():
    url = f"https://api.github.com/repos/{REPO}/issues/{ISSUE_NUMBER}/comments"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    comments = response.json()
    if not comments:
        return None
    latest_comment = comments[-1]["body"]
    try:
        return datetime.fromisoformat(latest_comment.strip())
    except ValueError:
        return None

# GitHub Issue に最終チェック時刻を記録
def post_last_check_to_issue(dt):
    url = f"https://api.github.com/repos/{REPO}/issues/{ISSUE_NUMBER}/comments"
    headers = {
        "Author
