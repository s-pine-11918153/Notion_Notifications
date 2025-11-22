import os
import requests
from datetime import datetime, timezone, timedelta

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def query_database(database_id):
    """再帰的にDBを探索し Notify=True のページを返す"""
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    payload = {
        "filter": {
            "property": "Notify",
            "checkbox": {
                "equals": True
            }
        }
    }

    print(f"[DEBUG] Query: {database_id}")
    res = requests.post(url, headers=HEADERS, json=payload)
    data = res.json()

    results = []

    for r in data.get("results", []):
        obj_type = r["object"]
        print(f"[DEBUG] ID={r['id']} type={obj_type}")

        # --- DBなら再帰で下層を探索 ---
        if obj_type == "database":
            print(f"[INFO] Nested DB found → {r['id']}")
            nested = query_database(r["id"])
            results.extend(nested)
            continue

        # --- ページなら Notify をチェック ---
        notify = (
            r.get("properties", {})
             .get("Notify", {})
             .get("checkbox", False)
        )

        if notify:
            print(f"[MATCH] Notify=True: {r['id']}")
            results.append(r)

    return results


if __name__ == "__main__":
    pages = query_database(DATABASE_ID)

    print("===== Final Result =====")
    for p in pages:
        title = p["properties"]["Page"]["title"][0]["plain_text"] \
            if p["properties"]["Page"]["title"] else "No Title"
        print(p["id"], title)

    print(f"Notify一致ページ総数: {len(pages)}")
