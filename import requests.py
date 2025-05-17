import requests
import json

# 必要な情報
database_id = "181efe8418b2452fa6a4ffef9e721e44"
token = "ntn_r130561954663G3bzIVfIaztGkKoHWA47MsUXw50875cHk"

# APIエンドポイント
url = f"https://api.notion.com/v1/databases/{database_id}"

# ヘッダー
headers = {
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-06-28"
}

# APIリクエスト
response = requests.get(url, headers=headers)
data = response.json()

# プロパティ情報を見やすく表示
print("全プロパティオブジェクト:")
for name, prop_obj in data["properties"].items():
    print(f"\nプロパティ名: {name}")
    print(json.dumps(prop_obj, indent=2, ensure_ascii=False))