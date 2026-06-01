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
        
        # 2. تجهيز نص الأسعار بأمان تام بدون تحويلات تسبب أخطاء
        price_posted = False
        
        if is_savings_week and price_now:
            try:
                # تنظيف السعر والتأكد من أنه رقم قبل الحساب
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

        # إذا لم يكن هناك عرض توفير، أو فشلت الحسبة الرياضية لأي سبب، يرسل السعر الطبيعي
        if not price_posted:
            if price_before and price_now:
                msg += f"❌ كان {price_before} ريال \n"
                msg += f"✅ والان {price_now} ريال 🤩\n\n"
            elif price_now:
                msg += f"✅ والان {price_now} ريال 🤩\n\n"
        
        # 3. الرابط في النهاية
        msg += f"{link}"

        # إرسال الرد في الشات الخاص أولاً
        if img:
            try:
                await update.message.reply_photo(photo=img, caption=msg, parse_mode='Markdown')
            except:
                await update.message.reply_text(msg, parse_mode='Markdown')
        else:
            await update.message.reply_text(msg, parse_mode='Markdown')

        # إرسال نفس الرسالة تلقائياً لقناتك المستهدفة
        try:
            if img:
                await context.bot.send_photo(chat_id=TARGET_CHANNEL, photo=img, caption=msg, parse_mode='Markdown')
            else:
                await context.bot.send_message(chat_id=TARGET_CHANNEL, text=msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error sending to channel: {e}")
