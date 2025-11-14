import os
import yfinance as yf
import requests
from datetime import datetime, timezone

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def get_stock_info(ticker: str):
    stock = yf.Ticker(ticker)
    info = stock.info

    data = {
        "銘柄名": info.get("shortName"),
        "ティッカーコード": ticker,
        "現在株価": info.get("regularMarketPrice"),
        "前日比(%)": round(
            (info.get("regularMarketPrice") - info.get("regularMarketPreviousClose"))
            / info.get("regularMarketPreviousClose")
            * 100,
            2,
        )
        if info.get("regularMarketPreviousClose")
        else None,
        "配当利回り": round(info.get("dividendYield", 0) * 100, 2)
        if info.get("dividendYield")
        else None,
        "PER": info.get("trailingPE"),
        "時価総額": info.get("marketCap"),
        "配当日": None,
        "決算日": None,
    }

    # 次回配当日
    if info.get("exDividendDate"):
        data["配当日"] = datetime.fromtimestamp(info["exDividendDate"]).isoformat()

    # 次回決算日
    try:
        earnings_dates = stock.earnings_dates
        if not earnings_dates.empty:
            data["決算日"] = earnings_dates.index[-1].to_pydatetime().isoformat()
    except Exception:
        pass

    return data


def upsert_notion_stock(data):
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "銘柄名": {"title": [{"text": {"content": data["銘柄名"]}}]},
            "ティッカーコード": {"rich_text": [{"text": {"content": data["ティッカーコード"]}}]},
            "現在株価": {"number": data["現在株価"]},
            "前日比(%)": {"number": data["前日比(%)"]},
            "配当利回り": {"number": data["配当利回り"]},
            "PER": {"number": data["PER"]},
            "時価総額": {"number": data["時価総額"]},
            "配当日": {"date": {"start": data["配当日"]} if data["配当日"] else None},
            "決算日": {"date": {"start": data["決算日"]} if data["決算日"] else None},
            "最終更新": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
        },
    }

    requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)


if __name__ == "__main__":
    TICKERS = ["7203.T", "6758.T", "9984.T"]  # 例：トヨタ, ソニー, ソフトバンク
    for t in TICKERS:
        info = get_stock_info(t)
        upsert_notion_stock(info)
        print(f"✅ {info['銘柄名']} を更新しました。")
