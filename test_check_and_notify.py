import os
import requests
import yfinance as yf
from datetime import datetime, timezone

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# ----------------------
# 1. Notion DBから監視対象データを取得
# ----------------------
def fetch_notion_rows():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    
    payload = {
        "filter": {
            "and": [
                {"property": "条件達成", "checkbox": {"equals": False}},
                {"property": "通知期限", "date": {"on_or_after": datetime.now().strftime("%Y-%m-%d")}}
            ]
        }
    }

    res = requests.post(url, headers=NOTION_HEADERS, json=payload)
    return res.json().get("results", [])


# ----------------------
# 2. 株価取得
# ----------------------
def get_price(ticker):
    stock = yf.Ticker(ticker)
    info = stock.history(period="1d")

    if info.empty:
        return None

    return float(info["Close"].iloc[-1])


# ----------------------
# 3. 条件式を評価（例: "price > 3000"）
# ----------------------
def evaluate_condition(expr, price):
    try:
        return eval(expr, {"price": price})
    except:
        return False


# ----------------------
# 4. Discord通知
# ----------------------
def notify_discord(title, ticker, price, condition):
    message = {
        "content": f"**通知条件を達成しました！**\n"
                   f"銘柄: {title} ({ticker})\n"
                   f"現在株価: {price}\n"
                   f"条件: `{condition}`"
    }
    requests.post(DISCORD_WEBHOOK_URL, json=message)


# ----------------------
# 5. Notionデータ更新（条件達成 = True）
# ----------------------
def update_notion_row(page_id, price):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {
        "properties": {
            "現在株価": {"number": price},
            "条件達成": {"checkbox": True},
            "最終確認日時": {
                "date": {"start": datetime.now(timezone.utc).isoformat()}
            }
        }
    }
    requests.patch(url, headers=NOTION_HEADERS, json=payload)


# ----------------------
# メイン処理
# ----------------------
def main():
    rows = fetch_notion_rows()
    print(f"{len(rows)} 件の監視対象レコードを取得")

    for row in rows:
        page_id = row["id"]
        props = row["properties"]

        title = props["銘柄名"]["title"][0]["plain_text"]
        ticker = props["ティッカーコード"]["rich_text"][0]["plain_text"]
        cond = props["通知条件"]["rich_text"][0]["plain_text"]

        print(f"\n--- {title} ({ticker}) ---")
        print("通知条件:", cond)

        price = get_price(ticker)
        if price is None:
            print("株価取得に失敗")
            continue

        print("現在株価:", price)

        if evaluate_condition(cond, price):
            print("👉 条件達成！Discordへ通知します")
            notify_discord(title, ticker, price, cond)
            update_notion_row(page_id, price)
        else:
            print("条件未達成")


if __name__ == "__main__":
    main()
