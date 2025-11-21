import os
import requests
import time
from datetime import datetime, timezone, timedelta

# --- 環境変数 ---
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")  # 親ページID
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
GITHUB_TOKEN = os.getenv("GH_PAT")
REPO = os.getenv("REPO")
WORKFLOW_NAME = "Notion Update Check"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# --- ページタイトル取得 ---
def extract_title(page):
    for name, prop in page["properties"].items():
        if prop.get("type") == "title":
            title_list = prop.get("title", [])
            if title_list:
                return title_list[0].get("plain_text", "").strip()
            else:
                return f"（タイトル空, プロパティ名: {name}）"
    return "（タイトルプロパティなし）"

# --- Update_information取得 ---
def extract_update_information(page):
    prop = page["properties"].get("Update_information")
    if prop and prop.get("type") == "rich_text" and prop.get("rich_text"):
        return "\n".join([rt.get("plain_text", "") for rt in prop["rich_text"]])
    return "（Update_information プロパティなし）"

# --- 最終更新日時取得(JST) ---
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

# --- Notify=ON ページを取得（child_database対応） ---
def fetch_notify_on_pages():
    all_pages = []

    try:
        url = f"https://api.notion.com/v1/blocks/{NOTION_DATABASE_ID}/children?page_size=100"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        blocks = resp.json().get("results", [])
        child_db_ids = [b["id"] for b in blocks if b["type"] == "child_database"]

        for db_id in child_db_ids:
            start_cursor = None
            while True:
                payload = {"page_size": 100, "filter": {"property": "Notify", "checkbox": {"equals": True}}}
                if start_cursor:
                    payload["start_cursor"] = start_cursor
                q_resp = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query", headers=HEADERS, json=payload, timeout=10)
                q_resp.raise_for_status()
                data = q_resp.json()
                all_pages.extend(data.get("results", []))
                if not data.get("has_more"):
                    break
                start_cursor = data.get("next_cursor")
    except Exception as e:
        print(f"[WARN] child_database 取得失敗: {e}")

    print(f"[INFO] Notify=ON ページ総取得件数: {len(all_pages)}")
    return all_pages

# --- Notify OFF ---
def turn_off_notify(page_id):
    payload = {"properties": {"Notify": {"checkbox": False}}}
    try:
        res = requests.patch(f"https://api.notion.com/v1/pages/{page_id}", headers=HEADERS, json=payload, timeout=10)
        if res.status_code not in (200, 204):
            print(f"[WARN] Failed to turn off Notify for {page_id}: {res.text}")
    except Exception as e:
        print(f"[WARN] turn_off_notify エラー: {e}")

# --- Discord通知(Embed版) ---
def send_discord_notification(title, update_info, update_data, page_url):
    if not DISCORD_WEBHOOK_URL:
        print("[WARN] Discord Webhook 未設定。通知スキップ。")
        return
    payload = {
        "embeds": [{
            "title": title,
            "url": page_url,
            "description": update_info,
            "fields": [{"name": "最終更新", "value": update_data}]
        }]
    }
    for _ in range(5):
        try:
            res = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            if res.status_code in (200, 204):
                return
            elif res.status_code == 429:
                retry = res.json().get("retry_after", 5)
                time.sleep(retry)
            else:
                res.raise_for_status()
        except Exception as e:
            print(f"[ERROR] Discord通知失敗: {e}")
            time.sleep(3)
    print("[ERROR] Discord通知失敗(複数回)")

# --- 古いワークフロー削除 ---
def cleanup_old_workflow_runs():
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    wf_resp = requests.get(f"https://api.github.com/repos/{REPO}/actions/workflows", headers=headers)
    wf_resp.raise_for_status()
    workflows = wf_resp.json().get("workflows", [])
    workflow_id = next((wf["id"] for wf in workflows if wf["name"] == WORKFLOW_NAME), None)
    if not workflow_id:
        print(f"[WARN] Workflow '{WORKFLOW_NAME}' not found")
        return
    runs_resp = requests.get(f"https://api.github.com/repos/{REPO}/actions/workflows/{workflow_id}/runs?per_page=100", headers=headers)
    runs_resp.raise_for_status()
    runs = runs_resp.json().get("workflow_runs", [])
    for run in runs[1:]:
        run_id = run["id"]
        del_resp = requests.delete(f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}", headers=headers)
        if del_resp.status_code not in (200, 204):
            print(f"[WARN] Failed to delete run {run_id}: {del_resp.status_code}")

# --- メイン ---
def main():
    pages = fetch_notify_on_pages()
    if not pages:
        print("[INFO] 通知対象のページはありません。")
        return

    print("=== Notify=ON 取得ページ一覧 ===")
    for page in pages:
        print(f" - {extract_title(page)}")

    print("=== 通知開始 ===")
    for page in pages:
        title = extract_title(page)
        update_info = extract_update_information(page)
        update_data = extract_update_data(page)
        page_url = page.get("url", "URLなし")

        print(f"[INFO] 通知中: {title}")
        send_discord_notification(title, update_info, update_data, page_url)
        turn_off_notify(page["id"])

    cleanup_old_workflow_runs()

if __name__ == "__main__":
    main()
