import os
import re
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# بيانات حازم الرسمية
TELEGRAM_BOT_TOKEN = "8681119804:AAEOWDZgqsMlTRRH4qS_rwL4qL2sf5ErwnI"
AMAZON_AFFILIATE_TAG = "x0659-21"

def expand_url(url):
    """فك الروابط المختصرة amzn.to بشكل مباشر ونقي"""
    try:
        session = requests.Session()
        # ترويسة حقيقية لفك الرابط دون اعتراضه
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        })
        response = session.head(url, allow_redirects=True, timeout=7)
        return response.url
    except Exception as e:
        logger.error(f"خطأ في فك الرابط المختصر: {e}")
        return url

def extract_asin(text):
    """استخراج كود الـ ASIN من الرابط الطويل"""
    pattern = r'(?:dp|gp/product)/([A-Z0-9]{10})'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None

def scrape_amazon_product_clean(asin):
    """كشط نقي ومباشر من أمازون السعودية كمتصفح حقيقي 100% بدون وسيط"""
    try:
        url = f"https://www.amazon.sa/dp/{asin}"
        # ترويسة متصفح كروم حديثة ومكتملة لتخطي الحجب تلقائياً وبأمان
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ar-AE,ar;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # محاولة قراءة عنوان المنتج من أكثر من مكان مخصص في أمازون لضمان النجاح
            title_element = soup.find("span", {"id": "productTitle"})
            if not title_element:
                title_element = soup.find("meta", {"name": "title"})
                if title_element:
                    return {"title": title_element.get("content", "").strip()}
            
            if title_element:
                title = title_element.get_text().strip()
                return {"title": title}
    except Exception as e:
        logger.error(f"خطأ في الكشط النقي: {e}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك يا حازم! 🚀\nتم تنظيف البوت بالكامل، أرسل لي أي رابط أمازون الآن وسأحوله لتاغك فوراً وبشكل مستقل.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    msg = await update.message.reply_text("⏳ جاري قراءة تفاصيل المنتج وتحويل الرابط...")
    
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
    
    # 3. جلب الاسم بالكشط النظيف الجديد
    product_info = scrape_amazon_product_clean(asin)
    
    if product_info and product_info['title'] != "منتج أمازون المميز":
        title = product_info['title']
        post_text = (
            f"📦 *{title}*\n\n"
            f"🔗 *رابط الأفلييت الخاص بك:* \n{affiliate_link}"
        )
    else:
        # الوضع الاحتياطي الذكي والمباشر بـ تاغك لو كانت الصفحة محمية
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
    
    logger.info("🤖 البوت يعمل بالنسخة المستقلة والنقية 100%...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
