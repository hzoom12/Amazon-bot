from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8681119804:AAGhNgJfeliEEK3JCKGZSbFcjpJneadoCPk"

async def reply_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # البوت بس يرد عليك بنفس الكلام اللي كتبته عشان نتأكد إنه عايش
    await update.message.reply_text(f"أنا شغال وأسمعك! وهذا كلامك: {update.message.text}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_test))
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
