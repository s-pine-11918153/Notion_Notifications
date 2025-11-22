import os
import requests
import time
from datetime import datetime, timezone, timedelta
import json

print("[DEBUG FULL PAGE DUMP]")
print(json.dumps(results[0], indent=2, ensure_ascii=False))

# --- 環境変数 ---
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
GITHUB_TOKEN = os.getenv("GH_PAT")
REPO = os.getenv("REPO")
ISSUE_NUMBER = os.getenv("ISSUE_NUMBER", "1")
WORKFLOW_NAME = "Notion Update Check"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# --- Notionデータベースから Notify=ON ページ取得 ---
def fetch_notify_on_pages():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    all_results = []
    payload = {
        "filter": {"property": "Notify", "checkbox": {"equals": True}}
    }

    print(f"[DEBUG] Query URL: {url}")
    print(f"[DEBUG] Payload: {payload}")

    while True:
        response = requests.post(url, headers=HEADERS, json=payload)
        print(f"[DEBUG] Raw Response Code: {response.status_code}")
        response.raise_for_status()

        data = response.json()
        print(f"[DEBUG] Response keys: {list(data.keys())}")

        results = data.get("results", [])
        print(f"[DEBUG] Retrieved {len(results)} pages in this batch")

        # 各ページのidログ
        for page in results:
            print(f"[DEBUG] Page ID: {page.get('id')} Notify={page.get('properties', {}).get('Notify')}")

        all_results.extend(results)

        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]

    print(f"[INFO] Notify=ON ページ総取得件数: {len(all_results)}")
    return all_results


# --- タイトル取得（詳細デバッグ付き） ---
def extract_title(page):
    print(f"[DEBUG] extract_title(): properties keys = {list(page['properties'].keys())}")

    prop = page["properties"].get("Page")
    if prop and prop["type"] == "title":
        if prop["title"]:
            title = prop["title"][0].get("plain_text", "").strip()
            print(f"[DEBUG] extract_title(): title = {title}")
            return title
        return "（テキストなし）"

    print("[WARN] タイトルプロパティ Page が存在しない")
    return "（Page プロパティなし）"


# --- 更新情報 ---
def extract_update_information(page):
    prop = page["properties"].get("Update_informations")
    print(f"[DEBUG] Update_informations: {prop}")
    if prop and prop.get("rich_text"):
        return "".join(rt.get("plain_text", "") for rt in prop["rich_text"])
    return "（Update_informations プロパティなし）"


# --- メイン処理 ---
def main():
    pages = fetch_notify_on_pages()
    if not pages:
        print("[INFO] 通知対象のページはありません。")
        return

    print("=== Debug Page List ===")
    for p in pages:
        print(f"[DEBUG] Page: {p.get('id')} Properties: {list(p['properties'].keys())}")

    for page in pages:
        notify_flag = page["properties"].get("Notify", {}).get("checkbox", False)
        print(f"[DEBUG] Notify flag: {notify_flag} ID: {page.get('id')}")

        if not notify_flag:
            continue

        title = extract_title(page)
        update_info = extract_update_information(page)
        update_data = extract_update_data(page)
        page_url = page.get("url", "URLなし")

        print(f"[INFO] 通知中: {title}")
        print(f"[DEBUG] URL: {page_url}")
        print(f"[DEBUG] UpdateInfo: {update_info}")
        print(f"[DEBUG] UpdateData: {update_data}")

        send_discord_notification(title, update_info, update_data, page_url)
        turn_off_notify(page["id"])

    cleanup_old_workflow_runs()


if __name__ == "__main__":
    main()
