async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "amazon" in url or "amzn" in url:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        title, price_now, price_before, img, link, auto_offers = get_amazon_details(url)
        
        # صياغة النص بنظام Markdown العادي اللي كان شغال عندك
        msg = f"📦 *{title}*\n\n"
        
        try:
            if price_before and price_now and int(price_before) > int(price_now):
                msg += f"❌ كان {price_before} ريال \n"
                msg += f"✅ والان {price_now} ريال 🤩\n\n"
            elif price_now:
                msg += f"✅ السعر الآن: {price_now} ريال 🤩\n\n"
        except:
            if price_now:
                msg += f"✅ السعر الآن: {price_now} ريال 🤩\n\n"
        
        msg += "🔣بعد خصم اسبوع التوفير20% \n\n"
        msg += f"{link}"

        # 1. إرسال الرد لك في الخاص للتأكيد
        if img:
            try:
                await update.message.reply_photo(photo=img, caption=msg, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Failed to reply with photo: {e}")
                await update.message.reply_text(msg, parse_mode='Markdown')
        else:
            await update.message.reply_text(msg, parse_mode='Markdown')

        # 2. التوجيه التلقائي إلى قناتك
        try:
            if img:
                await context.bot.send_photo(chat_id=TARGET_CHANNEL, photo=img, caption=msg, parse_mode='Markdown')
            else:
                await context.bot.send_message(chat_id=TARGET_CHANNEL, text=msg, parse_mode='Markdown')
            logger.info(f"Successfully posted to channel: {TARGET_CHANNEL}")
        except Exception as e:
            logger.error(f"Could not send automatically to channel. Error: {e}")
            await update.message.reply_text(f"⚠️ تنبيه: لم أتمكن من النشر تلقائياً في القناة. تأكد من إضافة البوت كمشرف.")
