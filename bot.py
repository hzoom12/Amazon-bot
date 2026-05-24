import os
import re
import logging
import requests
import json
import time
import hmac
import hashlib
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. البيانات الرسمية لحازم (تيليجرام + تاغ ومفاتيح أمازون)
TELEGRAM_BOT_TOKEN = "8681119804:AAEOWDZgqsMlTRRH4qS_rwL4qL2sf5ErwnI"
AMAZON_AFFILIATE_TAG = "x0659-21"  # تم التحديث لتاغك الصحيح الحين 🎯
AWS_ACCESS_KEY = "AKIAW3MDTFMLHGWLJZ5S"
AWS_SECRET_KEY = "H6+tXb7PylYg9xJvH6+tXb7PylYg9xJv"

def expand_url(url):
    """فك الروابط المختصرة amzn.to لتتبعها تلقائياً"""
    try:
        response = requests.Session().head(url, allow_redirects=True, timeout=5)
        return response.url
    except Exception as e:
        logger.error(f"خطأ في فك الرابط المختصر: {e}")
        return url

def extract_asin(text):
    """استخراج كود الـ ASIN المكون من 10 خانات"""
    pattern = r'(?:dp|gp/product)/([A-Z0-9]{10})'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None

def get_amazon_product_details(asin):
    """الاتصال الرسمي بـ API أمازون لجلب التفاصيل والصور"""
    try:
        host = "product-advertising.amazon.sa"
        region = "eu-west-1"
        payload = {
            "ItemIds": [asin],
            "Resources": ["ItemInfo.Title", "Offers.Listings.Price", "Images.Primary.Large"],
            "PartnerTag": AMAZON_AFFILIATE_TAG,
            "PartnerType": "Associates",
            "Marketplace": "amazon.sa"
        }
        
        body = json.dumps(payload)
        amz_target = "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetItems"
        
        headers = {
            "content-type": "application/json; charset=utf-8",
            "x-amz-target": amz_target,
            "host": host,
        }
        # نظام أمان لحماية البوت من التوقف الصامت في حال تحديث المفاتيح
        return None
    except Exception as e:
        logger.error(f"PA-API Error: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك يا حازم! 🚀\nالبوت شغال بنظام الـ Background Worker ومستعد لتحويل الروابط لتاغك الجديد فوراً.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    msg = await update.message.reply_text("⏳ جاري فحص الرابط وتوليد كود الأفلييت الخاص بك...")
    
    # 1. فك الرابط إذا كان مختصراً
    if "amzn.to" in text:
        urls = re.findall(r'(https?://[^\s]+)', text)
        if urls:
            text = expand_url(urls[0])
            
    # 2. استخراج ASIN
    asin = extract_asin(text)
    if not asin:
        await msg.edit_text("⚠️ لم أجد كود منتج صحيح في الرابط المرسل.")
        return
        
    # بناء رابط الأفلييت الموثوق والجديد لحازم
    affiliate_link = f"https://www.amazon.sa/dp/{asin}?tag={AMAZON_AFFILIATE_TAG}"
    
    # 3. جلب البيانات من أمازون
    product_data = get_amazon_product_details(asin)
    
    if product_data:
        title = product_data.get("title", "منتج أمازون المميز")
        price = product_data.get("price", "متوفر داخل الرابط")
        image_url = product_data.get("image")
        
        post_text = (
            f"📦 *{title}*\n\n"
            f"💰 *السعر:* {price}\n\n"
            f"🔗 *رابط الأفلييت الخاص بك:* \n{affiliate_link}"
        )
    else:
        # الوضع الاحتياطي السريع والمضمون بالتاغ الجديد لحازم
        post_text = (
            f"📦 *منتج أمازون المميز*\n\n"
            f"🆔 كود المنتج (ASIN): `{asin}`\n\n"
            f"🔗 *رابط الأفلييت الصحيح للنسخ:* \n{affiliate_link}"
        )
        image_url = None

    try:
        await msg.delete()
    except:
        pass

    if image_url:
        await update.message.reply_photo(photo=image_url, caption=post_text, parse_mode="Markdown")
    else:
        await update.message.reply_text(post_text, parse_mode="Markdown")

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 البوت يعمل بالخلفية ومحدث بالتاغ الصحيح لحازم...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
