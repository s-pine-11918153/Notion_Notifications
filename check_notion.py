import os
import requests
import time
from datetime import datetime, timezone, timedelta

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

# --- Notionデータベースから Notify=ON のページを取得（ページネーション対応） ---
def fetch_notify_on_pages():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    all_results = []
    payload = {
        "filter": {"property": "Notify", "checkbox": {"equals": True}}
    }

    print("[DEBUG] Query URL:", url)
    print("[DEBUG] Payload:", payload)

    while True:
        response = requests.post(url, headers=HEADERS, json=payload)
        print("[DEBUG] Raw Response Code:", response.status_code)

        response.raise_for_status()
        data = response.json()
        print("[DEBUG] Response keys:", list(data.keys()))

        results = data.get("results", [])
        print(f"[DEBUG] Retrieved {len(results)} pages in this batch")

        for p in results:
            print(f"[DEBUG] Page ID: {p.get('id')} Notify={p['properties'].get('Notify') if p.get('properties') else None}")

        all_results.extend(results)

        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]

    print(f"[INFO] Notify=ON ページ総取得件数: {len(all_results)}")
    return all_results

# --- NotifyをOFFにする ---
def turn_off_notify(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {"properties": {"Notify": {"checkbox": False}}}
    response = requests.patch(url, headers=HEADERS, json=payload)
    if response.status_code != 200:
        print(f"[WARN] Failed to turn off Notify for {page_id}: {response.text}")

# --- ページタイトルを取得 ---
def extract_title(page):
    prop = page["properties"].get("Page")
    if prop and prop["type"] == "title" and prop["title"]:
        return prop["title"][0].get("plain_text", "（テキストなし）")
    return "（Page プロパティなし）"

# --- 更新情報を取得 ---
def extract_update_information(page):
    prop = page["properties"].get("Update_information")
    if prop and prop["type"] == "rich_text" and prop["rich_text"]:
        return "".join([rt.get("plain_text", "") for rt in prop["rich_text"]])
    return "（Update_information プロパティなし）"

# --- 最終更新日時 ---
def extract_update_data(page):
    raw_time = page.get("last_edited_time")
    if not raw_time:
        return "（last_edited_time が存在しません）"
    try:
        t = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        jst = t.astimezone(timezone(timedelta(hours=9)))
        return jst.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"[WARN] 時刻変換エラー: {e}")
        return raw_time

# --- Discord通知 ---
def send_discord_notification(title, update_info, update_data, url):
    if not DISCORD_WEBHOOK_URL:
        print("[WARN] Discord Webhook 未設定。通知スキップ。")
        return

    content = (
        f"📢 **Notionページ更新通知**\n"
        f"📝 {title}\n"
        f"🔗 {url}\n"
        f"⌛ {update_data}\n"
        f"📄 {update_info}"
    )
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
        except Exception as e:
            print(f"[ERROR] Discord通知失敗: {e}")
            time.sleep(3)
    print("[ERROR] Failed to send Discord notification after multiple retries.")

# --- 古いワークフロー削除（定義だけ残す / 使用しない） ---
def cleanup_old_workflow_runs():
    print("[DEBUG] cleanup_old_workflow_runs() skipped (intentionally disabled)")

# --- メイン処理 ---
def main():
    pages = fetch_notify_on_pages()
    if not pages:
        print("[INFO] 通知対象のページはありません。")
        return

    print("=== Debug Page List ===")

    for page in pages:
        # --------------------------
        # 🔥 フルページDBは除外
        # --------------------------
        if page.get("object") == "database":
            print(f"[SKIP] Database object detected: {page.get('id')}")
            continue

        properties = page.get("properties", {})
        notify_flag = properties.get("Notify", {}).get("checkbox", False)

        print(f"[DEBUG] Notify flag: {notify_flag} ID: {page.get('id')}")

        if not notify_flag:
            continue

        title = extract_title(page)
        update_info = extract_update_information(page)
        update_data = extract_update_data(page)
        page_url = page.get("url", "URLなし")

        print(f"[INFO] 通知中: {title}")
        send_discord_notification(title, update_info, update_data, page_url)
        turn_off_notify(page["id"])

    # cleanup_old_workflow_runs() ←必要なら再度有効化


if __name__ == "__main__":
    main()
