# =========================================================
# 1. رقعة برمجية ذكية متوافقة تماماً مع بايثون 3.14 وقوانينه الجديدة
# =========================================================
import telegram.ext._updater
if not hasattr(telegram.ext._updater.Updater, '__dict__'):
    telegram.ext._updater.Updater.__dict__ = {}
if not hasattr(telegram.ext._updater.Updater, '_Updater__polling_cleanup_cb'):
    try:
        type(telegram.ext._updater.Updater).__setattr__(telegram.ext._updater.Updater, '_Updater__polling_cleanup_cb', None)
    except Exception:
        pass

# =========================================================
# 2. استيراد المكتبات الأساسية
# =========================================================
import os
import re
import logging
import threading
import http.server
import socketserver
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد السجلات (Logs)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================================================
# 3. إعدادات التوكن وسيرفر الويب الداخلي لـ Render
# =========================================================
# الكود سيبحث عن التوكن في الـ Environment Variables لـ Render باسم TELEGRAM_BOT_TOKEN
TELEGRAM_BOT_TOKEN = "8681119804:AAFNa4VekRGp7ERiMh9ke8ZOfsqYYM6eTig"

def run_health_server():
    """سيرفر ويب داخلي خفيف لإبقاء Render سعيداً والخدمة Live"""
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
            logger.info("🌍 سيرفر الويب الداخلي شغال على المنفذ 10000")
            httpd.serve_forever()
    except Exception as e:
        logger.error(f"خطأ في سيرفر الويب: {e}")

# =========================================================
# 4. دالات البوت الأساسية (استخراج الروابط ومعالجتها)
# =========================================================
def extract_asin(text):
    """دالة استخراج الـ ASIN من روابط أمازون"""
    # تعبير نمطي للبحث عن كود المنتجات في أمازون
    pattern = r'(?:dp|gp/product)/([A-Z0-9]{10})'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    
    # دعم الروابط المختصرة (amzn.to)
    if "amzn.to" in text:
        # هنا يمكنك وضع دالة فك الروابط المختصرة لو كانت مدعومة بكودك السابق
        # كحل مؤقت سنحاول البحث عن أي كود مكون من 10 خانات
        asin_match = re.search(r'/([A-Z0-9]{10})(?:[/?]|$)', text)
        if asin_match:
            return asin_match.group(1)
    return None

def pa_api_request(asin):
    """هنا تضع كود الاتصال بـ Amazon PA-API لجلب معلومات المنتج"""
    # كود تجريبي سريع (يجب أن يحتوي على أزرار وربط مفاتيح الأفلييت الخاصة بك)
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

# =========================================================
# 5. مستقبِلات أوامر وتحديثات تيليغرام (Handlers)
# =========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البدء /start"""
    await update.message.reply_text("أهلاً بك يا حازم في بوت الأفلييت الذكي! 🚀\nأرسل لي أي رابط أمازون وسأقوم بتحويله فوراً لرابط أفلييت خاص بك.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل الواردة"""
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

# =========================================================
# 6. نقطة الانطلاق والتشغيل (Main)
# =========================================================
def main():
    # تأكيد وجود التوكن
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("❌ خطأ: لم يتم العثور على TELEGRAM_BOT_TOKEN في إعدادات ريندر!")
        return

    # 1. تشغيل سيرفر الويب في الخلفية كخيط مستقل (Thread) لعدم تعطيل البوت
    web_thread = threading.Thread(target=run_health_server, daemon=True)
    web_thread.start()

    # 2. تشغيل محرك البوت الأساسي
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # ربط الأوامر والرسائل
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 البوت شغال الآن بكامل طاقته ومستعد لاستقبال الرسائل...")
    
    # بدء استقبال الرسائل (Polling)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
