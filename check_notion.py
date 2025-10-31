import os
import requests
import time
from datetime import datetime, timezone

# ===== 環境変数 =====
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
GITHUB_TOKEN = os.getenv("GH_PAT")
REPO = os.getenv("REPO")
ISSUE_NUMBER = os.getenv("ISSUE_NUMBER", "1")
WORKFLOW_NAME = "Notion Update Check"

# ===== Notionヘッダー =====
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# ===== Notion DBの全ページを取得 =====
def fetch_database_pages():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    response = requests.post(url, headers=HEADERS)
    response.raise_for_status()
    return response.json().get("results", [])

# ===== GitHub Issueコメントから最後のチェック時刻を取得 =====
def get_last_check_from_issue():
    url = f"https://api.github.com/repos/{REPO}/issues/{ISSUE_NUMBER}/comments"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
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

# ===== チェック時刻コメントを更新 =====
def replace_last_check_comment(new_time):
    _, comment_id = get_last_check_from_issue()
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    if comment_id:
        delete_url = f"https://api.github.com/repos/{REPO}/issues/comments/{comment_id}"
        requests.delete(delete_url, headers=headers)
    post_url = f"https://api.github.com/repos/{REPO}/issues/{ISSUE_NUMBER}/comments"
    data = {"body": new_time.isoformat()}
    requests.post(post_url, headers=headers, json=data)

# ===== ページタイトルを取得 =====
def extract_title(page):
    prop = page["properties"].get("Page")
    if prop and prop["type"] == "title" and prop["title"]:
        return prop["title"][0].get("plain_text", "（テキストなし）")
    return "（Page プロパティなし）"

# ===== 更新情報を取得 =====
def extract_update_information(page):
    prop = page["properties"].get("Update_informations")
    if prop and prop["type"] == "rich_text" and prop["rich_text"]:
        return "".join([rt.get("plain_text", "") for rt in prop["rich_text"]])
    return "（Update_informations プロパティなし）"

# ===== Discord通知 =====
def send_discord_notification(title, update_info, url):
    if not DISCORD_WEBHOOK_URL:
        return
    content = f"📢 Notionページが更新されました：\n**{title}**\n🔗 {url}"
    payload = {"content": content}
    for _ in range(3):
        try:
            r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            if r.status_code == 204:
                return
            elif r.status_code == 429:
                time.sleep(r.json().get("retry_after", 5))
            else:
                r.raise_for_status()
                return
        except Exception:
            time.sleep(3)
    print("❌ Failed to send Discord notification after multiple retries.")

# ===== NotifyチェックをOFFにする =====
def turn_off_notify(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {"properties": {"Notify": {"checkbox": False}}}
    response = requests.patch(url, headers=HEADERS, json=data)
    if response.status_code == 200:
        print(f"✅ Notify OFF for page {page_id}")
    else:
        print(f"⚠️ Failed to update Notify for {page_id}: {response.text}")

# ===== 古いワークフローを削除（最新10件以外） =====
def cleanup_old_workflow_runs():
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    wf_resp = requests.get(f"https://api.github.com/repos/{REPO}/actions/workflows", headers=headers)
    wf_resp.raise_for_status()
    workflows = wf_resp.json().get("workflows", [])
    wf_id = next((wf["id"] for wf in workflows if wf["name"] == WORKFLOW_NAME), None)
    if not wf_id:
        print(f"Workflow '{WORKFLOW_NAME}' not found")
        return

    runs_resp = requests.get(
        f"https://api.github.com/repos/{REPO}/actions/workflows/{wf_id}/runs?per_page=100",
        headers=headers
    )
    runs_resp.raise_for_status()
    runs = runs_resp.json().get("workflow_runs", [])
    for run in runs[10:]:
        run_id = run["id"]
        del_resp = requests.delete(f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}", headers=headers)
        if del_resp.status_code not in (204, 200):
            print(f"⚠️ Failed to delete run {run_id}: {del_resp.status_code}")

# ===== メイン処理 =====
def main():
    last_check, _ = get_last_check_from_issue()
    pages = fetch_database_pages()
    latest_time = last_check

    for page in pages:
        page_id = page["id"]
        updated_time_str = page.get("last_edited_time")
        updated_time = datetime.fromisoformat(updated_time_str.rstrip("Z")).replace(tzinfo=timezone.utc)

        # ✅ Notify が ON のページだけ通知対象
        notify = page["properties"].get("Notify", {}).get("checkbox", False)

        if notify and (last_check is None or updated_time > last_check):
            title = extract_title(page)
            update_info = extract_update_information(page)
            page_url = page.get("url", "URLなし")
            send_discord_notification(title, update_info, page_url)
            turn_off_notify(page_id)  # ✅ 通知後に自動OFF
            if latest_time is None or updated_time > latest_time:
                latest_time = updated_time

    if latest_time:
        replace_last_check_comment(latest_time)

    cleanup_old_workflow_runs()

if __name__ == "__main__":
    main()
