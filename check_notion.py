import os
import requests
from datetime import datetime, timezone

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
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    response = requests.post(url, headers=HEADERS)
    response.raise_for_status()
    return response.json().get("results", [])

def load_last_check():
    if not os.path.exists(LAST_CHECK_FILE):
        return None
    with open(LAST_CHECK_FILE, "r") as f:
        return datetime.fromisoformat(f.read().strip())

def save_last_check(dt):
    with open(LAST_CHECK_FILE, "w") as f:
        f.write(dt.isoformat())

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
