import os
import requests
import time
from datetime import datetime, timezone

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

# --- NotionデータベースからNotify=ONのページを取得 ---
def fetch_notify_on_pages():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    payload = {
        "filter": {
            "property": "Notify",
            "checkbox": {"equals": True}
        }
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    response.raise_for_status()
    return response.json().get("results", [])

# --- NotifyをOFFにする ---
def turn_off_notify(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {"properties": {"Notify": {"checkbox": False}}}
    response = requests.patch(url, headers=HEADERS, json=payload)
    if response.status_code != 200:
        print(f"Failed to turn off Notify for {page_id}: {response.text}")

# --- Notionページタイトル取得 ---
def extract_title(page):
    prop = page["properties"].get("Page")
    if prop and prop["type"] == "title" and prop["title"]:
        return prop["title"][0].get("plain_text", "（テキストなし）")
    return "（Page プロパティなし）"

# --- Update情報取得 ---
def extract_update_information(page):
    prop = page["properties"].get("Update_informations")
    if prop and prop["type"] == "rich_text" and prop["rich_text"]:
        return "".join([rt.get("plain_text", "") for rt in prop["rich_text"]])
    return "（Update_informations プロパティなし）"

# --- Discord通知 ---
def send_discord_notification(title, update_info, url):
    if not DISCORD_WEBHOOK_URL:
        return
    content = f"📢 Notionページ更新通知\n📝 **{title}**\n🔗 {url}\n\n{update_info}"
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
            print(f"Discord通知失敗: {e}")
            time.sleep(3)
    print("Failed to send Discord notification after multiple retries.")

# --- 古いワークフロー削除 ---
def cleanup_old_workflow_runs():
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    wf_resp = requests.get(f"https://api.github.com/repos/{REPO}/actions/workflows", headers=headers)
    wf_resp.raise_for_status()
    workflows = wf_resp.json().get("workflows", [])
    workflow_id = None
    for wf in workflows:
        if wf["name"] == WORKFLOW_NAME:
            workflow_id = wf["id"]
            break
    if not workflow_id:
        print(f"Workflow '{WORKFLOW_NAME}' not found")
        return

    runs_resp = requests.get(
        f"https://api.github.com/repos/{REPO}/actions/workflows/{workflow_id}/runs?per_page=100",
        headers=headers
    )
    runs_resp.raise_for_status()
    runs = runs_resp.json().get("workflow_runs", [])

    for run in runs[10:]:
        run_id = run["id"]
        del_resp = requests.delete(
            f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}",
            headers=headers
        )
        if del_resp.status_code not in (204, 200):
            print(f"Failed to delete run {run_id}: {del_resp.status_code}")

# --- メイン ---
def main():
    pages = fetch_notify_on_pages()
    if not pages:
        print("通知対象のページはありません。")
        return

    for page in pages:
        title = extract_title(page)
        update_info = extract_update_information(page)
        page_url = page.get("url", "URLなし")

        send_discord_notification(title, update_info, page_url)
        turn_off_notify(page["id"])  # 通知後に自動でOFF

    cleanup_old_workflow_runs()

if __name__ == "__main__":
    main()
