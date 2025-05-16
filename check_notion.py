import os
import requests
from datetime import datetime, timezone

import time

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
GITHUB_TOKEN = os.getenv("GH_PAT")
REPO = os.getenv("REPO")
ISSUE_NUMBER = 1

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def fetch_database_pages():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    response = requests.post(url, headers=HEADERS)
    response.raise_for_status()
    return response.json().get("results", [])

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

def post_last_check_to_issue(dt):
    url = f"https://api.github.com/repos/{REPO}/issues/{ISSUE_NUMBER}/comments"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    data = {"body": dt.isoformat()}
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()


def send_discord_notification(title, url):
    data = {
        "content": f"📢 Notionページが更新されました：**{title}**\n🔗 {url}"
    }

    for attempt in range(3):
        try:
            response = requests.post(DISCORD_WEBHOOK_URL, json=data)
            print(f"[Discord] Status Code: {response.status_code}")
            if response.status_code == 204:
                print("✅ 通知成功")
                return
            elif response.status_code == 429:
                retry_after = response.json().get("retry_after", 5)
                print(f"⚠️ レート制限: {retry_after}秒待機")
                time.sleep(retry_after)
            else:
                response.raise_for_status()
                return
        except Exception as e:
            print(f"🚨 通知失敗: {e}")
            time.sleep(3)

    raise Exception("Failed to send notification after multiple retries.")
def main():
    last_check = get_last_check_from_issue()
    pages = fetch_database_pages()

    latest_time = last_check

    for page in pages:
        updated_time_str = page.get("last_edited_time")
        updated_time = datetime.fromisoformat(updated_time_str.rstrip("Z")).replace(tzinfo=timezone.utc)

        if last_check is None or updated_time > last_check:
            title_prop = page["properties"].get("Name")
            if title_prop and title_prop.get("title"):
                title = title_prop["title"][0]["plain_text"]
            else:
                title = "タイトルなし"

            page_url = page.get("url", "URLなし")
            send_discord_notification(title, page_url)

            if latest_time is None or updated_time > latest_time:
                latest_time = updated_time

    if latest_time:
        post_last_check_to_issue(latest_time)

if __name__ == "__main__":
    main()
