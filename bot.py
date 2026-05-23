import os
import re
import logging
import threading
import http.server
import socketserver
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 1. إعداد السجلات (Logs)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. وضع التوكن الجديد والنشط بالكامل في السيرفر الجديد
TELEGRAM_BOT_TOKEN = "8681119804:AAGss6sTb25hyP60fOlV6WIklU3HcFVvHvI"

# 3. سيرفر ويب داخلي لإبقاء سيرفر ريندر أخضر و Live
def run_health_server():
    class HealthHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()

    try:
        with socketserver.TCPServer(("", 10000), HealthHandler) as httpd:
            logger.info("🌍 سيرفر الويب الداخلي شغال بنجاح على المنفذ 10000")
            httpd.serve_forever()
    except Exception as e:
        logger.error(f"خطأ في سيرفر الويب: {e}")

# 4. دالات البوت الأساسية ومعالجة الروابط
def extract_asin(text):
    """استخراج كود المنتجات من روابط أمازون"""
    pattern = r'(?:dp|gp/product)/([A-Z0-9]{10})'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    
    if "amzn.to" in text:
        asin_match = re.search(r'/([A-Z0-9]{10})(?:[/?]|$)', text)
        if asin_match:
            return asin_match.group(1)
    return None

def pa_api_request(asin):
    """الاتصال بـ Amazon API وجلب البيانات"""
    return {"title": "منتج أمازون المميز", "image": "", "url": f"https://www.amazon.sa/dp/{asin}?tag=YOUR_TAG"}

def parse_product(data):
    if not data:
        return None
    return {
        "title": data.get("title", "منتج مميز"),
        "image": data.get("image", ""),
        "link": data.get("url", "")
    }

def format_post(product, asin):
    return f"📦 *{product['title']}*\n\n🔗 رابط الأفلييت الخاص بك:\n{product['link']}"

# 5. مستقبِلات الأوامر والرسائل
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك يا حازم! 🚀\nأرسل لي أي رابط أمازون وسأقوم بتحويله فوراً لرابط أفلييت خاص بك.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    msg = await update.message.reply_text("⏳ جاري فحص الرابط وجلب البيانات...")
    
    asin = extract_asin(text)
    if not asin:
        await msg.edit_text("⚠️ ما قدرت أجد رابط أو كود منتج صحيح.")
        return
        
    data = pa_api_request(asin)
    product = parse_product(data) if data else None
    
    if not product:
        await msg.edit_text("❌ ما قدرت أجلِب معلومات المنتج من أمازون.")
        return
        
    post = format_post(product, asin)
    image_url = product.get("image", "")
    
    await msg.delete()
    if image_url:
        await update.message.reply_photo(photo=image_url, caption=post, parse_mode="Markdown")
    else:
        await update.message.reply_text(post, parse_mode="Markdown")

# 6. نقطة الانطلاق الأساسية (Main)
def main():
    # تشغيل سيرفر الويب في الخلفية
    web_thread = threading.Thread(target=run_health_server, daemon=True)
    web_thread.start()

    # تشغيل البوت
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 البوت شغال الآن ومستعد لاستقبال الرسائل...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
