from flask import Flask
from threading import Thread
import requests
import json
import os
import asyncio
import time
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# === FLASK KEEP ALIVE SERVER ===
app = Flask('')

@app.route('/')
def home():
    return "✅ BaseMeme Auto Listing Bot aktif dan berjalan nonstop!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Jalankan Flask di thread terpisah agar Replit tidak tidur
Thread(target=run_flask).start()

# === CONFIG ===
API_URL = "https://api.base.meme/coin/list?sort=block_create_time&chain_id=8453&offset=0&limit=24"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "8123953445:AAFS40idb3HGaoZjjeInuuU5etGjxjOBmo4"
TELEGRAM_CHANNEL_ID = os.getenv("CHANNEL_ID") or "@basememelisting"
LAST_SEEN_FILE = "last_seen.json"

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# === UTILITAS SIMPAN TOKEN TERAKHIR ===
def load_last_seen():
    if os.path.exists(LAST_SEEN_FILE):
        with open(LAST_SEEN_FILE, "r") as f:
            return json.load(f)
    return {"last_contract": "", "last_block_time": 0}

def save_last_seen(contract, block_time):
    with open(LAST_SEEN_FILE, "w") as f:
        json.dump({"last_contract": contract, "last_block_time": block_time}, f)

# === FETCH DATA DARI BASE.MEME API ===
def fetch_latest_token():
    try:
        res = requests.get(API_URL, timeout=5)
        data = res.json()
        if "data" in data and "data_list" in data["data"]:
            tokens = data["data"]["data_list"]
            return tokens[0] if tokens else None
        else:
            print("⚠️ API tidak mengembalikan format data_list yang diharapkan.")
            return None
    except Exception as e:
        print("❌ Error fetch:", e)
        return None

# === FORMAT PESAN TELEGRAM ===
def format_caption(token):
    name = token.get("name", "Unknown")
    symbol = token.get("symbol", "")
    desc = token.get("description", "No description available.")
    creator = token.get("owner_info", {}).get("username") or token.get("creator_address", "Unknown")
    contract = token.get("contract_address", "N/A")

    website = token.get("website_url", "-")
    twitter = token.get("x_url", "-")
    telegram = token.get("telegram_url", "-")
    market_cap = token.get("market_cap", "0")

    # Escape karakter berbahaya buat Markdown
    for ch in ["-", "(", ")", ".", "_", "[", "]", "~", "`", ">", "#", "+", "=", "|", "{", "}", "!"]:
        name = name.replace(ch, f"\\{ch}")
        symbol = symbol.replace(ch, f"\\{ch}")
        desc = desc.replace(ch, f"\\{ch}")
        creator = str(creator).replace(ch, f"\\{ch}")

    caption = f"""
🌟 *NEW TOKEN ON BASE*

🪙 *Name:* {name} ({symbol})
📜 *Contract:* `{contract}`
👤 *Creator:* {creator}
💰 *Market Cap:* ${market_cap}
📝 *Description:* {desc}

🌐 *Website:* {website}
🐦 *Twitter:* {twitter}
💬 *Telegram:* {telegram}

🔗 [View on Base.Meme](https://base.meme/token/{contract})
"""
    return caption.strip()

# === KIRIM KE TELEGRAM ===
async def post_to_telegram(token):
    caption = format_caption(token)
    image = token.get("image_url") or token.get("quick_url")
    contract = token.get("contract_address")
    trade_url = f"https://t.me/based_eth_bot?start=r_basememe_b_{contract}"

    keyboard = [[InlineKeyboardButton("🔹 Trade Now", url=trade_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if image:
            await bot.send_photo(
                chat_id=TELEGRAM_CHANNEL_ID,
                photo=image,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="MarkdownV2"
            )
        else:
            await bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=caption,
                reply_markup=reply_markup,
                parse_mode="MarkdownV2"
            )
        print(f"✅ Posted new token: {token.get('name')} ({token.get('symbol')})")
    except Exception as e:
        print("❌ Gagal kirim ke Telegram:", e)

# === LOOP UTAMA ===
async def main():
    last_seen = load_last_seen()
    print("🚀 Auto-listing bot aktif (INSTANT MODE ⚡ tanpa duplikat)...")

    posted_contracts = set()  # cache di memori agar gak dobel

    while True:
        try:
            token = fetch_latest_token()
            if token:
                contract = token.get("contract_address")
                block_time = token.get("block_create_time", 0)

                # Cegah posting dobel
                if (
                    contract != last_seen["last_contract"]
                    and block_time > last_seen["last_block_time"]
                    and contract not in posted_contracts
                ):
                    await post_to_telegram(token)
                    save_last_seen(contract, block_time)
                    posted_contracts.add(contract)
                else:
                    print("⏳ Belum ada token baru...")
            else:
                print("⚠️ Tidak ada data token ditemukan.")
        except Exception as e:
            print(f"⚠️ Error di main loop: {e}")
        await asyncio.sleep(1)  # cepat tanggap

if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            print(f"💥 Terjadi error utama: {e}, restart dalam 3 detik...")
            time.sleep(3)
