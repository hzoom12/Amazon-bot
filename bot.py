import re
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# التوكن النظيف والنشط الخاص بك
TELEGRAM_BOT_TOKEN = "8681119804:AAEOWDZgqsMlTRRH4qS_rwL4qL2sf5ErwnI"
# ضع تاغ الأفلييت الخاص بك هنا
AMAZON_AFFILIATE_TAG = "smartshoppi0d-21" 

def expand_url(url):
    """دالة لفك الروابط المختصرة وتتبعها للوصول للرابط الأصلي الطويل"""
    try:
        response = requests.Session().head(url, allow_redirects=True, timeout=5)
        return response.url
    except Exception as e:
        logger.error(f"خطأ في فك الرابط المختصر: {e}")
        return url

def extract_asin(text):
    """استخراج كود المنتج المكون من 10 خانات من الرابط الطويل"""
    # البحث في النصوص أو الروابط الطويلة
    pattern = r'(?:dp|gp/product)/([A-Z0-9]{10})'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك يا حازم! 🚀\nأرسل لي أي رابط أمازون (طويل أو مختصر) وسأقوم بتحويله فوراً لرابط أفلييت خاص بك.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    msg = await update.message.reply_text("⏳ جاري فحص الرابط وتتبع المنتج...")
    
    # 1. التحقق إذا كان الرابط مختصراً وفكه
    if "amzn.to" in text:
        # استخراج الرابط من النص
        urls = re.findall(r'(https?://[^\s]+)', text)
        if urls:
            text = expand_url(urls[0])
            
    # 2. استخراج كود المنتج ASIN
    asin = extract_asin(text)
    if not asin:
        await msg.edit_text("⚠️ لم أجد كود منتج صحيح في هذا الرابط. تأكد أنه رابط لمنتج أمازون.")
        return
        
    # 3. بناء رابط الأفلييت الخاص بك مباشرة لضمان عدم حدوث خطأ
    affiliate_link = f"https://www.amazon.sa/dp/{asin}?tag={AMAZON_AFFILIATE_TAG}"
    
    # 4. إرسال المنشور الجاهز
    post_text = (
        f"📦 *منتج أمازون المميز*\n\n"
        f"🆔 كود المنتج: `{asin}`\n\n"
        f"🔗 رابط الأفلييت الخاص بك للنسخ:\n{affiliate_link}"
    )
    
    try:
        await msg.delete() # حذف رسالة الانتظار
    except:
        pass
        
    await update.message.reply_text(post_text, parse_mode="Markdown")

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 البوت شغال رسميًا بنظام الـ Background Worker المستقر...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
