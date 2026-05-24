import os
import re
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. البيانات الثابتة الخاصة بك
TELEGRAM_BOT_TOKEN = "8681119804:AAEOWDZgqsMlTRRH4qS_rwL4qL2sf5ErwnI"
AMAZON_AFFILIATE_TAG = "x0659-21"

def expand_url(url):
    """فك الروابط المختصرة amzn.to"""
    try:
        response = requests.Session().head(url, allow_redirects=True, timeout=5)
        return response.url
    except Exception as e:
        logger.error(f"خطأ في فك الرابط المختصر: {e}")
        return url

def extract_asin(text):
    """استخراج كود المنتج ASIN"""
    pattern = r'(?:dp|gp/product)/([A-Z0-9]{10})'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None

def scrape_amazon_product(asin):
    """قراءة صفحة المنتج مباشرة لجلب الاسم بدون الحاجة لمفاتيح الـ API"""
    try:
        url = f"https://www.amazon.sa/dp/{asin}"
        # إرسال ترويسة متصفح حقيقي لتجنب حظر أمازون للـ Bots
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Accept-Language": "ar-AE,ar;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # محاولة استخراج عنوان المنتج
            title_element = soup.find("span", {"id": "productTitle"})
            title = title_element.get_text().strip() if title_element else "منتج أمازون المميز"
            
            return {"title": title}
    except Exception as e:
        logger.error(f"خطأ أثناء قراءة صفحة المنتج: {e}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك يا حازم! 🚀\nأرسل لي أي رابط أمازون وسأجلب لك اسمه ورابط الأفلييت الخاص بك فوراً.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    msg = await update.message.reply_text("⏳ جاري فحص الرابط وسحب اسم المنتج...")
    
    # 1. فك الرابط إذا كان مختصراً
    if "amzn.to" in text:
        urls = re.findall(r'(https?://[^\s]+)', text)
        if urls:
            text = expand_url(urls[0])
            
    # 2. استخراج ASIN
    asin = extract_asin(text)
    if not asin:
        await msg.edit_text("⚠️ لم أجد كود منتج صحيح في الرابط.")
        return
        
    affiliate_link = f"https://www.amazon.sa/dp/{asin}?tag={AMAZON_AFFILIATE_TAG}"
    
    # 3. جلب البيانات عبر الكشط (Scraping)
    product_info = scrape_amazon_product(asin)
    
    if product_info:
        title = product_info['title']
        post_text = (
            f"📦 *{title}*\n\n"
            f"🔗 *رابط الأفلييت الخاص بك:* \n{affiliate_link}"
        )
    else:
        # وضع احتياطي في حال فرضت أمازون حماية مؤقتة على الصفحة
        post_text = (
            f"📦 *منتج أمازون المميز*\n\n"
            f"🆔 كود المنتج (ASIN): `{asin}`\n\n"
            f"🔗 *رابط الأفلييت الخاص بك:* \n{affiliate_link}"
        )

    try:
        await msg.delete()
    except:
        pass

    await update.message.reply_text(post_text, parse_mode="Markdown")

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 البوت يعمل بالخلفية بنظام الـ Scraping المباشر...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
