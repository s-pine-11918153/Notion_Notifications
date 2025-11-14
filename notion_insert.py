import os
import requests
from datetime import datetime

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

url = "https://api.notion.com/v1/pages"
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

data = {
    "parent": {"database_id": DATABASE_ID},
    "properties": {
        "銘柄名": {
            "title": [{"text": {"content": "Stock"}}]
        },
        "ティッカーコード": {
            "rich_text": [{"text": {"content": "Ticker"}}]
        },
        "通知条件": {
            "rich_text": [{"text": {"content": "price > 3000"}}]
        },
        "通知期限": {
            "date": {"start": "2025-12-31"}
        }
    }
}

response = requests.post(url, headers=headers, json=data)
print("Status:", response.status_code)
print(response.text)
