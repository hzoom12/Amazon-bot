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

# 1. بيانات حازم الرسمية والجديدة
TELEGRAM_BOT_TOKEN = "8681119804:AAEOWDZgqsMlTRRH4qS_rwL4qL2sf5ErwnI"
AMAZON_AFFILIATE_TAG = "x0659-21"
AWS_ACCESS_KEY = "AKPANDTX2Z1778330583"
AWS_SECRET_KEY = "aE1cKjKmpNN1gL7hCvH0NzcNkq30FPJ"

def expand_url(url):
    """فك الروابط المختصرة amzn.to تلقائياً"""
    try:
        response = requests.Session().head(url, allow_redirects=True, timeout=5)
        return response.url
    except Exception as e:
        logger.error(f"خطأ في فك الرابط المختصر: {e}")
        return url

def extract_asin(text):
    """استخراج كود الـ ASIN"""
    pattern = r'(?:dp|gp/product)/([A-Z0-9]{10})'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None

def sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

def get_signature_key(key, date_stamp, regionName, serviceName):
    kDate = sign(('AWS4' + key).encode('utf-8'), date_stamp)
    kRegion = sign(kDate, regionName)
    kService = sign(kRegion, serviceName)
    kSigning = sign(kService, 'aws4_request')
    return kSigning

def get_amazon_product_details_official(asin):
    """الاتصال الرسمي بسيرفرات أمازون السعودية وسحب تفاصيل المنتج بدقة"""
    try:
        host = "product-advertising.amazon.sa"
        region = "eu-west-1"
        service = "ProductAdvertisingAPI"
        endpoint = "https://product-advertising.amazon.sa/paapi5/getitems"
        
        payload = {
            "ItemIds": [asin],
            "Resources": ["ItemInfo.Title", "Offers.Listings.Price", "Images.Primary.Large"],
            "PartnerTag": AMAZON_AFFILIATE_TAG,
            "PartnerType": "Associates",
            "Marketplace": "amazon.sa"
        }
        
        body = json.dumps(payload)
        t = datetime.utcnow()
        amz_date = t.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = t.strftime('%Y%m%d')
        
        canonical_headers = f"content-type:application/json; charset=utf-8\nhost:{host}\nx-amz-target:com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetItems\n"
        signed_headers = "content-type;host;x-amz-target"
        
        payload_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
        canonical_request = f"POST\n/paapi5/getitems\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        
        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
        string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        
        signing_key = get_signature_key(AWS_SECRET_KEY, date_stamp, region, service)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        authorization_header = f"{algorithm} Credential={AWS_ACCESS_KEY}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
        
        headers = {
            "content-type": "application/json; charset=utf-8",
            "x-amz-target": "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetItems",
            "host": host,
            "x-amz-date": amz_date,
            "Authorization": authorization_header
        }
        
        response = requests.post(endpoint, headers=headers, data=body, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            items = res_json.get("ItemsResult", {}).get("Items", [])
            if items:
                item = items[0]
                title = item.get("ItemInfo", {}).get("Title", {}).get("DisplayValue", "منتج أماzون المميز")
                
                # جلب السعر
                price = "متوفر داخل الرابط"
                listings = item.get("Offers", {}).get("Listings", [])
                if listings:
                    price_attr = listings[0].get("Price", {})
                    if price_attr:
                        price = price_attr.get("DisplayAmount", price)
                
                # جلب الصورة
                image = item.get("Images", {}).get("Primary", {}).get("Large", {}).get("URL", None)
                
                return {"title": title, "price": price, "image": image}
    except Exception as e:
        logger.error(f"خطأ في طلب الـ API الرسمي: {e}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك يا حازم! 🚀\nالبوت شغال بالنظام الرسمي والأمن 100% عبر API أمازون. أرسل أي رابط الآن.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    msg = await update.message.reply_text("⏳ جاري جلب تفاصيل المنتج الرسميّة والسعر من أمازون...")
    
    if "amzn.to" in text:
        urls = re.findall(r'(https?://[^\s]+)', text)
        if urls: text = expand_url(urls[0])
            
    asin = extract_asin(text)
    if not asin:
        await msg.edit_text("⚠️ لم أجد كود منتج صحيح.")
        return
        
    affiliate_link = f"https://www.amazon.sa/dp/{asin}?tag={AMAZON_AFFILIATE_TAG}"
    
    # طلب البيانات عبر المفاتيح الرسمية لحازم
    product_info = get_amazon_product_details_official(asin)
    
    if product_info:
        title = product_info['title']
        price = product_info['price']
        image_url = product_info['image']
        
        post_text = (
            f"📦 *{title}*\n\n"
            f"💰 *السعر:* {price}\n\n"
            f"🔗 *رابط الأفلييت الخاص بك:* \n{affiliate_link}"
        )
    else:
        # نظام الطوارئ النظيف بدون قنوات خارجية
        post_text = (
            f"📦 *منتج أمازون المميز*\n\n"
            f"🔗 *رابط الأفلييت الخاص بك:* \n{affiliate_link}"
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
    
    logger.info("🤖 تشغيل البوت الرسمي عبر مفاتيح PA-API الموثوقة...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
