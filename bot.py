async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "amazon" in url or "amzn" in url:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        title, price_now, price_before, img, link, auto_offers = get_amazon_details(url)
        
        # 1. اسم المنتج
        msg = f"{title}\n\n"
        
        # دمج العروض للبحث بداخلها
        all_offers_text = " ".join(auto_offers).lower()
        is_savings_week = "توفير" in all_offers_text or "خصم" in all_offers_text or "coupon" in all_offers_text or "توفير" in title.lower()
        
        # 2. تجهيز نص الأسعار بأمان
        price_posted = False
        
        if is_savings_week and price_now:
            try:
                clean_num = "".join(re.findall(r'\d+', price_now))
                if clean_num:
                    discounted_price = round(float(clean_num) * 0.80)
                    if price_before:
                        msg += f"❌ كان {price_before} ريال \n"
                    msg += f"✅ والان {discounted_price} ريال 🤩\n\n"
                    msg += "🔣 بعد خصم اسبوع التوفير 20%\n\n"
                    price_posted = True
            except Exception as e:
                logger.error(f"Error calculating discount: {e}")

        if not price_posted:
            if price_before and price_now:
                msg += f"❌ كان {price_before} ريال \n"
                msg += f"✅ والان {price_now} ريال 🤩\n\n"
            elif price_now:
                msg += f"✅ والان {price_now} ريال 🤩\n\n"
        
        # 3. الرابط في النهاية
        msg += f"{link}"

        # --------------------------------------------------
        # الجزء الأول: الرد في الشات الخاص عندك (مضمون ومفصول تماماً)
        # --------------------------------------------------
        try:
            if img:
                await update.message.reply_photo(photo=img, caption=msg)
            else:
                await update.message.reply_text(msg)
        except Exception as e:
            logger.error(f"Error replying in private chat: {e}")

        # --------------------------------------------------
        # الجزء الثاني: الإرسال التلقائي للقناة (معزول تماماً لو فشل ما يخرب الخاص)
        # --------------------------------------------------
        try:
            # تأكد أن المعرف مكتوب صح فوق TARGET_CHANNEL = "@smartshophazim"
            if img:
                await context.bot.send_photo(chat_id=TARGET_CHANNEL, photo=img, caption=msg)
            else:
                await context.bot.send_message(chat_id=TARGET_CHANNEL, text=msg)
        except Exception as e:
            # لو في مشكلة بالقناة (مثل البوت مو مشرف)، بيسجل الخطأ هنا بالخفاء بدون ما يعلق البوت عندك
            logger.error(f"Error sending to channel {TARGET_CHANNEL}: {e}")
