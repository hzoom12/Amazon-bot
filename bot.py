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

# 2. التوكن الجديد والنشط بالكامل 
TELEGRAM_BOT_TOKEN = "8681119804:AAEOWDZgqsMlTRRH4qS_rwL4qL2sf5ErwnI"

# 3. سيرفر ويب داخلي سريع لإبقاء ريندر المجاني Live
class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"OK")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, format, *args):
        return  # كتم السجلات لتخفيف الضغط

def run_health_server():
    try:
        port = int(os.environ.get("PORT", 10000))
        with socketserver.TCPServer(("", port), HealthHandler) as httpd:
            logger.info(f"🌍 سيرفر الويب شغال بنجاح على المنفذ {port}")
            httpd.serve_forever()
    except Exception as e:
        logger.error(f"خطأ في سيرفر الويب: {e}")

# 4. دالات البوت الأساسية
def extract_asin(text):
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
    return {"title": "منتج أمازون المميز", "image": "", "url": f"https://www.amazon.sa/dp/{asin}?tag=YOUR_TAG"}

def parse_product(data):
    if not data:
        return None
    return {"title": data.get("title", "منتج مميز"), "image": data.get("image", ""), "link": data.get("url", "")}

def format_post(product, asin):
    return f"📦 *{product['title']}*\n\n🔗 رابط الأفلييت الخاص بك:\n{product['link']}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك يا حازم! 🚀\nأرسل لي أي رابط أمازون وسأقوم بتحويله فوراً لرابط أفلييت خاص بك.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    msg = await update.message.reply_text("⏳ جاري فحص الرابط...")
    asin = extract_asin(text)
    if not asin:
        await msg.edit_text("⚠️ لم أجد كود منتج صحيح.")
        return
    data = pa_api_request(asin)
    product = parse_product(data) if data else None
    if not product:
        await msg.edit_text("❌ فشل جلب البيانات.")
        return
    post = format_post(product, asin)
    await msg.delete()
    await update.message.reply_text(post, parse_mode="Markdown")

# 5. تشغيل البوت مع ميزة الحماية وإسقاط الطوابير القديمة
def main():
    web_thread = threading.Thread(target=run_health_server, daemon=True)
    web_thread.start()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 البوت ينطلق الآن بنظام حماية الطابور...")
    
    # ميزة drop_pending_updates تسحق أي رسائل أو تراكمات قديمة تسبب تعليق السيرفر
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=False
    )

if __name__ == "__main__":
    main()
