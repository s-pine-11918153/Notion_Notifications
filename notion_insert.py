import os
import requests
from datetime import datetime

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID_FOR_TRADE")

url = "https://api.notion.com/v1/pages"
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# テスト用に最小限のデータで挿入
data = {
    "parent": {"database_id": DATABASE_ID},
    "properties": {
        "Stock": {
            "title": [{"text": {"content": "Test Stock"}}]
        },
        "Ticker": {
            "rich_text": [{"text": {"content": "TST"}}]
        },
        "condition": {
            "select": {"name": "price > 3000"}
        },
        "Deadline_Date": {
            "date": {"start": "2025-12-31"}
        }
    }
}

response = requests.post(url, headers=headers, json=data)
print("Status code:", response.status_code)
print(response.text)
