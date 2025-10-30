import os
import requests
import time
from datetime import datetime, timezone

# 環境変数
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
        return None, None
    latest_comment = comments[-1]
    try:
        return datetime.fromisoformat(latest_comment["body"].strip()), latest_comment["id"]
    except ValueError:
        return None, latest_comment["id"]

def replace_last_check_comment(new_time):
    _, comment_id = get_last_check_from_issue()
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    if comment_id:
        delete_url = f"https://api.github.com/repos/{REPO}/issues/comments/{comment_id}"
        requests.delete(delete_url, headers=headers)
    post_url = f"https://api.github.com/repos/{REPO}/issues/{ISSUE_NUMBER}/comments"
    data = {"body": new_time.isoformat()}
    response = requests.post(post_url, headers=headers, json=data)
    response.raise_for_status()

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
    if not DISCORD_WEBHOOK_URL:
        return
    #content = f"📢 Notionページが更新されました：\n**{title}**\n{update_info}\n🔗 {url}"
    content = f"📢 Notionページが更新されました：\n🔗 {url}"
    payload = {"content": content}
    for _ in range(3):
        try:
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            if response.status_code == 204:
                return
            elif response.status_code == 429:
                time.sleep(response.json().get("retry_after", 5))
            else:
                response.raise_for_status()
                return
        except Exception:
            time.sleep(3)
    print("Failed to send Discord notification after multiple retries.")

def main():
    last_check, _ = get_last_check_from_issue()
    pages = fetch_database_pages()
    latest_time = last_check

    for page in pages:
        updated_time_str = page.get("last_edited_time")
        updated_time = datetime.fromisoformat(updated_time_str.rstrip("Z")).replace(tzinfo=timezone.utc)

        if last_check is None or updated_time > last_check:
            title = extract_title(page)
            update_info = extract_update_information(page)
            page_url = page.get("url", "URLなし")
            send_discord_notification(title, update_info, page_url)

            if latest_time is None or updated_time > latest_time:
                latest_time = updated_time

    if latest_time:
        replace_last_check_comment(latest_time)

if __name__ == "__main__":
    main()
