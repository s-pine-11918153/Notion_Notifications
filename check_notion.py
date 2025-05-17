import os
import requests
import time
import json
from datetime import datetime, timezone
import hashlib

# 環境変数の読み込み
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
GITHUB_TOKEN = os.getenv("GH_PAT")
REPO = os.getenv("REPO")
ISSUE_NUMBER = os.getenv("ISSUE_NUMBER")

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

# GitHub Issue から最後のチェック情報を取得
def get_last_check_info():
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
    latest_comment = comments[-1]["body"]
    try:
        dt_str, last_hash = latest_comment.strip().split("|", 1)
        return datetime.fromisoformat(dt_str), last_hash
    except Exception:
        return None, None

# GitHub Issue にチェック情報（時刻＋ハッシュ）を記録
def post_check_info(dt, content_hash):
    url = f"https://api.github.com/repos/{REPO}/issues/{ISSUE_NUMBER}/comments"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    data = {"body": f"{dt.isoformat()}|{content_hash}"}
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()

# タイトル取得（"名前" プロパティ）
def extract_title(page):
    prop = page["properties"].get("Page")
    if prop and prop["type"] == "title" and prop["title"]:
        return prop["title"][0]["plain_text"]
    return "（Page プロパティなし）"

# 更新内容取得（"Update_information" プロパティ）
def extract_update_information(page):
    prop = page["properties"].get("Update_informations")
    if prop and prop["type"] == "rich_text" and prop["rich_text"]:
        return "".join([rt.get("plain_text", "") for rt in prop["rich_text"]])
    return "（Update_informations プロパティなし）"

# ハッシュ生成
def hash_update_info(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

# Discord 通知
def send_discord_notification(title, update_info, url):
    data = {
        "content": f"📢 Notionページが更新されました：\nページ：**{title}**\n更新内容：**{update_info}**\n🔗 {url}"
    }
    for attempt in range(3):
        try:
            response = requests.post(DISCORD_WEBHOOK_URL, json=data)
            print(f"[Discord] Status Code: {response.status_code}")
            if response.status_code == 204:
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

# デバッグ表示（任意）
def debug_print_properties(page):
    print("🔍 Notionページのプロパティ:")
    print(json.dumps(page.get("properties", {}), indent=2, ensure_ascii=False))

# メイン処理
def main():
    last_check, last_hash = get_last_check_info()
    pages = fetch_database_pages()
    latest_time = last_check

    for page in pages:
        updated_time_str = page.get("last_edited_time")
        updated_time = datetime.fromisoformat(updated_time_str.rstrip("Z")).replace(tzinfo=timezone.utc)

        update_info = extract_update_information(page)
        current_hash = hash_update_info(update_info)

        if (last_check is None or updated_time > last_check) and current_hash != last_hash:
            debug_print_properties(page)
            title = extract_title(page)
            page_url = page.get("url", "URLなし")
            send_discord_notification(title, update_info, page_url)

            if latest_time is None or updated_time > latest_time:
                latest_time = updated_time

            post_check_info(updated_time, current_hash)
            break  # 1件のみ通知したら終了（必要に応じて削除）

if __name__ == "__main__":
    main()
