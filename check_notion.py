import os
import requests
from datetime import datetime, timezone
import requests

REPO = "ユーザー名/リポジトリ名"
ISSUE_NUMBER = 1
GITHUB_TOKEN = os.getenv("GH_PAT")

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

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

LAST_CHECK_FILE = "last_check.txt"

def fetch_database_pages():
    url = f"https://api.notion.com/v1/databases/61a1dd55f5584{NOTION_DATABASE_ID}/query"
    response = requests.post(url, headers=HEADERS)
    response.raise_for_status()
    return response.json().get("results", [])

def load_last_check():
    return get_last_check_from_issue()

def save_last_check(dt):
    post_last_check_to_issue(dt)

def send_discord_notification(title, url):
    data = {
        "content": f"📢 Notionのページが更新されました！\nタイトル: {title}\nURL: {url}"
    }
    requests.post(DISCORD_WEBHOOK_URL, json=data)

def main():
    last_check = load_last_check()
    pages = fetch_database_pages()

    latest_time = last_check

    for page in pages:
        updated_time_str = page.get("last_edited_time")
        updated_time = datetime.fromisoformat(updated_time_str.rstrip("Z")).replace(tzinfo=timezone.utc)

        if last_check is None or updated_time > last_check:
            # ページタイトルを取得（プロパティ名が「Page」の場合）
            title_prop = page["properties"].get("Page")
            if title_prop and title_prop.get("title"):
                title = title_prop["title"][0]["plain_text"]
            else:
                title = "タイトルなし"

            page_url = page.get("url", "URLなし")
            send_discord_notification(title, page_url)

            if latest_time is None or updated_time > latest_time:
                latest_time = updated_time

    if latest_time:
        save_last_check(latest_time)

if __name__ == "__main__":
    main()
