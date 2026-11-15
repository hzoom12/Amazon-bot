import logging
import os
import re
import time

import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
# يمنع طباعة التوكن في السجلات
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- البيانات (التوكن من متغيرات Render وليس من الكود) ---
BOT_TOKEN = os.environ["BOT_TOKEN"]
MY_TAG = os.environ.get("MY_TAG", "x0659-21")
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL", "@smartshophazim")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "ar-SA,ar;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


def expand_url(url):
    """فك الروابط المختصرة القادمة من تطبيق الجوال"""
    try:
        if "amzn.to" in url or "amzn.eu" in url or "a.co" in url:
            response = requests.head(
                url, allow_redirects=True, timeout=8, headers=HEADERS
            )
            return response.url
        return url
    except Exception as e:
        logger.error(f"Error expanding URL: {e}")
        return url


def clean_price(price_str):
    if not price_str:
        return ""
    digits = re.findall(r"\d+", price_str.replace(",", ""))
    if digits:
        half = len(digits[0]) // 2
        first_part = digits[0][:half]
        second_part = digits[0][half:]
        if first_part == second_part and len(digits[0]) > 2:
            return first_part
        return digits[0]
    return ""


def is_blocked(res, soup):
    """يكتشف صفحة التحقق (captcha) أو الحجب"""
    if res.status_code != 200:
        return f"status {res.status_code}"
    if soup.find("form", {"action": "/errors/validateCaptcha"}):
        return "captcha"
    text = res.text[:5000].lower()
    if "robot check" in text or "automated access" in text:
        return "robot check"
    return ""


def fetch_page(url):
    """يجلب الصفحة مع 3 محاولات، ويرجع (soup, سبب_الفشل)"""
    reason = ""
    for attempt in range(1, 4):
        try:
            session = requests.Session()
            res = session.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.content, "html.parser")
            reason = is_blocked(res, soup)
            if not reason:
                return soup, ""
            logger.warning(f"Attempt {attempt} blocked: {reason} | {url}")
        except Exception as e:
            reason = f"exception: {e}"
            logger.warning(f"Attempt {attempt} failed: {e}")
        time.sleep(2 * attempt)
    return None, reason


def get_amazon_details(url):
    """يرجع (title, price_now, price_before, img_url, final_link)
    وإذا فشل الجلب يكون title = None"""
    expanded_url = expand_url(url)
    asin_match = re.search(r"(?:dp|gp/product)/([A-Z0-9]{10})", expanded_url)
    if asin_match:
        asin = asin_match.group(1)
        final_link = f"https://www.amazon.sa/dp/{asin}?tag={MY_TAG}"
    else:
        base = expanded_url.split("?")[0]
        final_link = f"{base}?tag={MY_TAG}"

    soup, reason = fetch_page(final_link)
    if soup is None:
        logger.error(f"Could not fetch product page ({reason}): {final_link}")
        return None, "", "", "", final_link

    # 1. الاسم (مع بدائل)
    title = ""
    title_tag = soup.find("span", {"id": "productTitle"})
    if title_tag:
        title = title_tag.get_text().strip()
    if not title:
        og = soup.find("meta", {"property": "og:title"})
        if og and og.get("content"):
            title = og["content"].strip()
    if not title and soup.title:
        title = soup.title.get_text().strip()
    if not title:
        logger.error(f"Title not found in page (layout changed?): {final_link}")
        return None, "", "", "", final_link

    # 2. السعر الحالي
    price_now = ""
    price_box = soup.find("div", {"id": "apex_desktop"})
    if price_box:
        p_tag = price_box.find("span", {"class": "a-offscreen"}) or price_box.find(
            "span", {"class": "a-price-whole"}
        )
        if p_tag:
            price_now = clean_price(p_tag.get_text().strip())
    if not price_now:
        p_now_tag = soup.find("span", {"class": "a-price-whole"})
        if p_now_tag:
            price_now = clean_price(p_now_tag.get_text().strip())

    # 3. السعر قبل
    price_before = ""
    p_before_tag = soup.find("span", {"class": "basisPrice"}) or soup.find(
        "span", {"class": "a-text-strike"}
    )
    if p_before_tag:
        price_before = clean_price(p_before_tag.get_text().strip())

    # 4. الصورة (مع بدائل)
    img_url = ""
    img_tag = soup.find("img", {"id": "landingImage"}) or soup.find(
        "img", {"id": "main-image"}
    )
    if img_tag:
        img_url = img_tag.get("data-old-hires") or img_tag.get("src") or ""
    if not img_url:
        og_img = soup.find("meta", {"property": "og:image"})
        if og_img and og_img.get("content"):
            img_url = og_img["content"]

    return title, price_now, price_before, img_url, final_link


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    url_match = re.search(r"https?://\S+", text)
    if not url_match:
        return
    original_url = url_match.group(0)
    if not ("amazon" in original_url or "amzn" in original_url or "a.co" in original_url):
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    title, price_now, price_before, img, final_link = get_amazon_details(
        original_url
    )

    # فشل الجلب: ننبّهك فقط ولا ننشر شيئاً في القناة
    if not title:
        await update.message.reply_text(
            "⚠️ ما قدرت أجلب تفاصيل المنتج (غالباً أمازون حجب الطلب).\n"
            "جرّب بعد دقيقة، أو انشره يدوياً:\n" + final_link
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


def main():
    logger.info("Starting bot...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
