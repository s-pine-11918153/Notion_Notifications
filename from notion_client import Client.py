from notion_client import Client

# ===== 設定 =====
NOTION_TOKEN = "ntn_r130561954663G3bzIVfIaztGkKoHWA47MsUXw50875cHk"
PAGE_ID = "181efe8418b2452fa6a4ffef9e721e44"
SEARCH_KEYWORD = "50m"

# ===== 接続 =====
notion = Client(auth=NOTION_TOKEN)

# ===== ページ内ブロック取得 =====
blocks = notion.blocks.children.list(block_id=PAGE_ID)

found = False
for b in blocks["results"]:
    block_type = b.get("type")
    rich_text = b.get(block_type, {}).get("rich_text", [])
    if rich_text:
        content = "".join([t["plain_text"] for t in rich_text])
        if SEARCH_KEYWORD in content:
            print(f"✅ 見つかりました: block_id={b['id']}")
            print(f"内容: {content}\n")
            found = True

if not found:
    print("🔍 該当する文字列は見つかりませんでした。")
