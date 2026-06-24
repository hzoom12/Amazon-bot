import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import re
import logging
import json

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- بيانات حازم الرسمية 🎯 ---
BOT_TOKEN = "8681119804:AAGhNgJfeliEEK3JCKGZSbFcjpJneadoCPk"
MY_TAG = "x0659-21"
TARGET_CHANNEL = "@smartshophazim"

def expand_url(url):
    try:
        if "amazon.sa" in url or "amazon.com" in url:
            return url
        if "amzn.to" in url or "amzn.eu" in url or "link.amazon" in url:
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
            })
            response = session.head(url, allow_redirects=True, timeout=5)
            return response.url
        return url
    except Exception as e:
        logger.error(f"Error expanding URL: {e}")
        return url

def clean_price(price_str):
    if not price_str: return ""
    digits = re.findall(r'\d+', price_str.replace(',', ''))
    if digits:
        half = len(digits[0]) // 2
        first_part = digits[0][:half]
        second_part = digits[0][half:]
        if first_part == second_part and len(digits[0]) > 2:
            return first_part
        return digits[0]
    return ""

def get_amazon_details(url):
    expanded_url = expand_url(url)
    
    # محاكاة متصفح أندرويد حقيقي وجديد كلياً لتفادي كشف السيرفر 📱
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ar-SA,ar;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Device-Memory": "8",
        "Downlink": "10"
    }
    
    try:
        asin_match = re.search(r'(?:dp|gp/product|link\.amazon)/([A-Z0-9]{9,10})', expanded_url)
        if not asin_match:
            asin_match = re.search(r'(?:dp|gp/product|link\.amazon)/([A-Z0-9]{9,10})', url)

        if asin_match:
            asin = asin_match.group(1)
            fetch_url = f"https://www.amazon.sa/dp/{asin}?tag={MY_TAG}&language=ar_SA"
        else:
            clean_base = expanded_url.split("?")[0]
            fetch_url = f"{clean_base}?tag={MY_TAG}&language=ar_SA"
            
        res = requests.get(fetch_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content, "html.parser")
        
        # --- 1. قشط الاسم بالتناوب الذكي ---
        title = ""
        title_tag = soup.find("span", {"id": "productTitle"})
        if title_tag:
            title = title_tag.get_text().strip()
        
        if not title:
            # محاولة جلبه من الـ og:title (بيانات السوشيال ميديا المخفية بالصفحة)
            og_title = soup.find("meta", {"property": "og:title"}) or soup.find("meta", {"name": "title"})
            if og_title and og_title.get("content"):
                title = og_title.get("content").split(":")[0].replace("Amazon.sa:", "").strip()
        
        if not title: title = "منتج مميز من أمازون"

        # --- 2. قشط الأسعار بطرق التفافية وجديدة ---
        price_now = ""
        price_before = ""
        
        # الخطة أ: البحث العادي
        price_inside_box = soup.find("div", {"id": "apex_desktop"}) or soup.find("div", {"id": "corePrice_desktop"})
        if price_inside_box:
            p_tag = price_inside_box.find("span", {"class": "a-offscreen"})
            if p_tag: price_now = clean_price(p_tag.get_text().strip())

        # الخطة ب: البحث في الأكواد الجاهزة (تويتر وفيسبوك كاردز) داخل الصفحة
        if not price_now:
            # بعض الصفحات المحمية تضع السعر في وسم تتبع مخصص
            meta_price = soup.find("meta", {"property": "product:price:amount"})
            if meta_price: price_now = clean_price(meta_price.get("content", ""))

        if not price_now:
            # البحث الأعمى في الكلاسات الشائعة
            for c in ["a-price-whole", "a-price", "apexPriceToPay", "a-color-price"]:
                p_tag = soup.find("span", {"class": c})
                if p_tag:
                    price_now = clean_price(p_tag.get_text().strip())
                    if price_now: break

        # سحب السعر القديم
        p_before_tag = soup.find("span", {"class": "basisPrice"}) or soup.find("span", {"class": "a-text-strike"}) or soup.find("span", {"class": "listPrice"})
        if p_before_tag:
            price_before = clean_price(p_before_tag.get_text().strip())

        # --- 3. قشط الصورة من المنبع ---
        img_url = ""
        img_tag = soup.find("img", {"id": "landingImage"}) or soup.find("img", {"id": "main-image"})
        if img_tag: img_url = img_tag.get("src", "")
            
        if not img_url:
            og_image = soup.find("meta", {"property": "og:image"}) or soup.find("meta", {"name": "twitter:image"})
            if og_image: img_url = og_image.get("content", "")

        return title, price_now, price_before, img_url
    except Exception as e:
        logger.error(f"Error fetching details: {e}")
        return "منتج مميز من أمازون", None, None, None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    original_url = update.message.text.strip()
    
    if any(domain in original_url for domain in ["amazon", "amzn", "link.amazon"]):
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        title, price_now, price_before, img = get_amazon_details(original_url)
        
        # طباعة الرابط الأصلي في السطر الأول للواتساب 🚀
        msg = f"{original_url}\n\n"
        msg += f"{title}\n\n"
        
        if price_before and price_now:
            msg += f"❌ كان {price_before} ريال \n"
            msg += f"✅ والان {price_now} ريال 🤩\n\n"
        elif price_now:
            msg += f"✅ والان {price_now} ريال 🤩\n\n"
            
        msg += "✨ لاتنسى كودي + خصم الراجحي \n"

        if img:
            try:
                await update.message.reply_photo(photo=img, caption=msg, parse_mode='Markdown')
            except:
                await update.message.reply_text(msg, parse_mode='Markdown')
        else:
            await update.message.reply_text(msg, parse_mode='Markdown')

        try:
            if img:
                await context.bot.send_photo(chat_id=TARGET_CHANNEL, photo=img, caption=msg, parse_mode='Markdown')
            else:
                await context.bot.send_message(chat_id=TARGET_CHANNEL, text=msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error sending to channel: {e}")

def main():
    logger.info("Starting bot...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
