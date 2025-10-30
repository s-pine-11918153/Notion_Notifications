import os
import requests
import time
import json
from datetime import datetime, timezone

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
GITHUB_TOKEN = os.getenv("GH_PAT")
REPO = os.getenv("REPO")
ISSUE_NUMBER = os.getenv("ISSUE_NUMBER", "1")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

COMMENT_TAG = "<!-- notion-check -->"

def fetch_database_pages():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    response = requests.post(url, headers=HEADERS)
    response.raise_for_status()
    return response.json().get("results", [])

def get_last_check_from_issue():
    url = f"https://api.github.com/repos/{REPO}/issues/{ISSUE_NUMBER}/comments"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    comments = res.json()

    for c in reversed(comments):  # 新しい順
        body = c.get("body", "")
        if COMMENT_TAG in body:
            try:
                ts = body.split(COMMENT_TAG)[-1].strip()
                return datetime.fromisoformat(ts), c["id"]
            except Exception:
                return None, c["id"]
    return None, None

def update_check_comment(new_time, comment_id=None):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    body = f"{COMMENT_TAG}\n{new_time.isoformat()}"
    if comment_id:
        # 既存コメントを更新
        url = f"https://api.github.com/repos/{REPO}/issues/comments/{comment_id}"
        res = requests.patch(url, headers=headers, json={"body": body})
    else:
        # 新規コメント
        url = f"https://api.github.com/repos/{REPO}/issues/{ISSUE_NUMBER}/comments"
        res = requests.post(url, headers=headers, json={"body": body})
    res.raise_for_status()

def extract_title(page):
    prop = page["properties"].get("Page")
    if prop and prop["type"] == "title" and prop["title"]:
        return prop["title"][0].get("plain_text", "（テキストなし）")
    return "（Page プロパティなし）"

def extract_update_information(page):
    prop = page["properties"].get("Update_informations")
    if prop and prop["type"] == "rich_text" and prop["rich_text"]:
        return "".join([rt.get("plain_text", "") for rt in prop["rich_text"]])
    return "（Update_informations プロパティなし）"

def send_discord_notification(title, update_info, url):
