import requests

token = "ntn_r130561954663G3bzIVfIaztGkKoHWA47MsUXw50875cHk"  # 稼働中のトークンを直接ここに貼る
database = "2ab04dd22c5a8062a7b8c49fd7d63c27"

res = requests.get(
    f"https://api.notion.com/v1/databases/2ab04dd22c5a8062a7b8c49fd7d63c27",
    headers={
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
    },
)

print(res.status_code)
print(res.text)
