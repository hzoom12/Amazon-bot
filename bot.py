import asyncio
import logging
import os
import re
import time

import requests
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
# يمنع طباعة التوكن في السجلات
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- الإعدادات (كلها من متغيرات Render وليست من الكود) ---
BOT_TOKEN = os.environ["BOT_TOKEN"]
MY_TAG = os.environ.get("MY_TAG", "x0659-21")
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL", "@smartshophazim")

# بيانات Creators API من Associates Central
CREDENTIAL_ID = os.environ["CREATORS_CREDENTIAL_ID"]
CREDENTIAL_SECRET = os.environ["CREATORS_CREDENTIAL_SECRET"]
# السعودية ضمن منطقة أوروبا (Version 3.2)
TOKEN_URL = os.environ.get(
    "CREATORS_TOKEN_URL", "https://api.amazon.co.uk/auth/o2/token"
)
API_URL = "https://creatorsapi.amazon/catalog/v1/getItems"
MARKETPLACE = "www.amazon.sa"

SHORT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ar-SA,ar;q=0.9,en-US;q=0.8,en;q=0.7",
}

_token_cache = {"value": None, "expires": 0.0}


def get_token(force=False):
    """يجلب توكن OAuth ويحتفظ به لمدة ساعة"""
    if (
        not force
        and _token_cache["value"]
        and time.time() < _token_cache["expires"] - 60
    ):
        return _token_cache["value"]
    res = requests.post(
        TOKEN_URL,
        json={
            "grant_type": "client_credentials",
            "client_id": CREDENTIAL_ID,
            "client_secret": CREDENTIAL_SECRET,
            "scope": "creatorsapi::default",
        },
        timeout=15,
    )
    if res.status_code != 200:
        logger.error(f"Token error {res.status_code}: {res.text[:300]}")
        res.raise_for_status()
    data = res.json()
    _token_cache["value"] = data["access_token"]
    _token_cache["expires"] = time.time() + int(data.get("expires_in", 3600))
    return _token_cache["value"]


def expand_url(url):
    """فك الروابط المختصرة (link.amazon / amzn.to ...) لمعرفة رقم المنتج"""
    try:
        if not re.search(r"(?:dp|gp/product)/[A-Z0-9]{10}", url):
            response = requests.get(
                url,
                allow_redirects=True,
                timeout=10,
                headers=SHORT_HEADERS,
                stream=True,
            )
            final = response.url
            response.close()
            return final
        return url
    except Exception as e:
        logger.error(f"Error expanding URL: {e}")
        return url


def extract_asin(url):
    m = re.search(r"(?:dp|gp/product|gp/aw/d)/([A-Z0-9]{10})", url)
    if m:
        return m.group(1)
    m = re.search(r"/([A-Z0-9]{10})(?:[/?]|$)", url)
    return m.group(1) if m else ""


def fmt(amount):
    if amount is None:
        return ""
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return ""
    return str(int(amount)) if amount.is_integer() else f"{amount:.2f}"


def call_get_items(asin, token):
    payload = {
        "itemIds": [asin],
        "itemIdType": "ASIN",
        "marketplace": MARKETPLACE,
        "partnerTag": MY_TAG,
        "resources": [
            "images.primary.large",
            "itemInfo.title",
            "offersV2.listings.price",
            "offersV2.listings.availability",
        ],
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-marketplace": MARKETPLACE,
    }
    return requests.post(API_URL, json=payload, headers=headers, timeout=20)


def get_item_details(url):
    """يرجع (title, price_now, price_before, img_url, final_link)
    وإذا فشل الجلب يكون title = None"""
    expanded = expand_url(url)
    asin = extract_asin(expanded) or extract_asin(url)
    final_link = f"https://www.amazon.sa/dp/{asin}?tag={MY_TAG}" if asin else url
    if not asin:
        logger.error(f"No ASIN found: {url} -> {expanded}")
        return None, "", "", "", final_link

    try:
        res = call_get_items(asin, get_token())
        if res.status_code == 401:
            res = call_get_items(asin, get_token(force=True))
        if res.status_code != 200:
            logger.error(
                f"GetItems error {res.status_code} for {asin}: {res.text[:400]}"
            )
            return None, "", "", "", final_link
        data = res.json()
    except Exception as e:
        logger.error(f"Creators API failure for {asin}: {e}")
        return None, "", "", "", final_link

    items = (data.get("itemsResult") or {}).get("items") or []
    if not items:
        logger.error(f"No items returned for {asin}: {str(data)[:400]}")
        return None, "", "", "", final_link
    item = items[0]

    title = ((item.get("itemInfo") or {}).get("title") or {}).get(
        "displayValue", ""
    )
    if not title:
        logger.error(f"No title for {asin}")
        return None, "", "", "", final_link

    img_url = (
        ((item.get("images") or {}).get("primary") or {}).get("large") or {}
    ).get("url", "")

    price_now = ""
    price_before = ""
    listings = (item.get("offersV2") or {}).get("listings") or []
    if listings:
        listing = next(
            (l for l in listings if l.get("isBuyBoxWinner")), listings[0]
        )
        price = listing.get("price") or {}
        now = (price.get("money") or {}).get("amount")
        before = ((price.get("savingBasis") or {}).get("money") or {}).get(
            "amount"
        )
        price_now = fmt(now)
        if now is not None and before is not None and float(before) > float(now):
            price_before = fmt(before)

    return title, price_now, price_before, img_url, final_link


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    url_match = re.search(r"https?://\S+", text)
    if not url_match:
        return
    original_url = url_match.group(0)
    if not (
        "amazon" in original_url or "amzn" in original_url or "a.co" in original_url
    ):
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    # يشتغل في خيط منفصل عشان ما يوقف البوت أثناء الانتظار
    title, price_now, price_before, img, final_link = await asyncio.to_thread(
        get_item_details, original_url
    )

    # فشل الجلب: ننبّهك فقط ولا ننشر شيئاً في القناة
    if not title:
        await update.message.reply_text(
            "⚠️ ما قدرت أجلب تفاصيل المنتج.\n"
            "تقدر تنشره يدوياً بهذا الرابط:\n" + final_link
        )
        return

    msg = f"{original_url}\n\n"
    msg += f"{title}\n\n"

    if price_before and price_now:
        msg += f"❌ كان ~{price_before} ريال~ \n"
        msg += f"✅ *والان {price_now} ريال* 🔥\n\n"
    elif price_now:
        msg += f"✅ *والان {price_now} ريال* 🔥\n\n"

    msg += "------"

    # الرد في الخاص
    if img:
        try:
            await update.message.reply_photo(photo=img, caption=msg)
        except Exception:
            await update.message.reply_text(msg)
    else:
        await update.message.reply_text(msg)

    # نفس الرسالة للقناة
    try:
        if img:
            await context.bot.send_photo(
                chat_id=TARGET_CHANNEL, photo=img, caption=msg
            )
        else:
            await context.bot.send_message(chat_id=TARGET_CHANNEL, text=msg)
    except Exception as e:
        logger.error(f"Error sending to channel: {e}")


async def on_error(update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Unhandled error: {context.error}")


def main():
    logger.info("Starting bot...")
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .build()
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    app.add_error_handler(on_error)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
