import os
import re
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- البيانات 🎯 ---
BOT_TOKEN ="8681119804:AAEUxT-KGYU871uMXQr6VKW8ybnCQC1XA18"
MY_TAG = "x0659-21"
TARGET_CHANNEL = "@smartshophazim"

def expand_url(url):
    """فك الروابط المختصرة القادمة من تطبيق الجوال"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        if "amzn.to" in url or "amzn.eu" in url:
            response = requests.Session().head(url, headers=headers, allow_redirects=True, timeout=10)
            return response.url
        return url
    except Exception as e:
        logger.error(f"Error expanding URL: {e}")
        return url

def clean_price(price_str):
    """تنظيف السعر وإرجاع الأرقام فقط بدون أجزاء عشرية أو فواصل"""
    if not price_str: return ""
    # حذف أي فواصل أو نقاط أو رموز وأخذ الأرقام الصحيحة الأولى
    clean = re.sub(r'[^\d]', '', price_str.split('.')[0])
    return clean

def get_amazon_details(url):
    expanded_url = expand_url(url)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "ar-SA,ar;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Device-Memory": "8",
        "Viewport-Width": "1920"
    }
    
    try:
        asin_match = re.search(r'(?:dp|gp/product)/([A-Z0-9]{10})', expanded_url)
        if asin_match:
            asin = asin_match.group(1)
            final_link = f"https://www.amazon.sa/dp/{asin}?tag={MY_TAG}"
        else:
            final_link = expanded_url.split("?")[0] + f"?tag={MY_TAG}" if "?" in expanded_url else expanded_url + f"?tag={MY_TAG}"
            
        session = requests.Session()
        res = session.get(final_link, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, "html.parser")
        
        # 1. العنوان
        title_tag = soup.find("span", {"id": "productTitle"}) or soup.find("h1", {"id": "title"})
        title = title_tag.get_text().strip() if title_tag else "منتج من أمازون"
        
        # 2. السعر الحالي (بدون فواصل أو أجزاء عشرية)
        price_now = ""
        price_whole = soup.find("span", {"class": "a-price-whole"})
        if price_whole:
            price_now = clean_price(price_whole.get_text())
        else:
            p_offscreen = soup.find("span", {"class": "a-offscreen"})
            if p_offscreen:
                price_now = clean_price(p_offscreen.get_text())

        # 3. السعر السابق (بدون فواصل أو أجزاء عشرية)
        price_before = ""
        p_before_tag = soup.find("span", {"class": "a-text-price"}) or soup.find("span", {"class": "basisPrice"})
        if p_before_tag:
            offscreen = p_before_tag.find("span", {"class": "a-offscreen"})
            if offscreen:
                price_before = clean_price(offscreen.get_text())

        # 4. رابط الصورة
        img_url = ""
        img_tag = soup.find("img", {"id": "landingImage"}) or soup.find("img", {"id": "imgBlkFront"})
        if img_tag:
            img_url = img_tag.get("data-old-hires") or img_tag.get("src") or ""

        return title, price_now, price_before, img_url
    except Exception as e:
        logger.error(f"Error fetching details: {e}")
        return None, None, None, None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    original_url = update.message.text.strip()
    if "amazon" in original_url or "amzn" in original_url:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        title, price_now, price_before, img = get_amazon_details(original_url)
        
        emoji_star = chr(0x2728)
        
        msg = f"{title}\n\n"
        
        if price_before and price_now:
            msg += f"❌ كان ~{price_before} ريال~\n"
            msg += f"✅ *والآن {price_now} ريال* 🔥\n\n"
        elif price_now:
            msg += f"✅ *والآن {price_now} ريال* 🔥\n\n"
            
        # إعادة الرابط الأصلي الذي تم إرساله من المستخدم بالضبط
        msg += f"{original_url}\n\n"
        msg += f"{emoji_star}\n"

        # الإرسال للخاص
        if img:
            try:
                await update.message.reply_photo(photo=img, caption=msg)
            except:
                await update.message.reply_text(msg)
        else:
            await update.message.reply_text(msg)

        # الإرسال للقناة
        try:
            if img:
                await context.bot.send_photo(chat_id=TARGET_CHANNEL, photo=img, caption=msg)
            else:
                await context.bot.send_message(chat_id=TARGET_CHANNEL, text=msg)
        except Exception as e:
            logger.error(f"Error sending to channel: {e}")

def main():
    logger.info("Starting bot...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
