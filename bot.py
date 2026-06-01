async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "amazon" in url or "amzn" in url:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        title, price_now, price_before, img, link, auto_offers = get_amazon_details(url)
        
        # 1. اسم المنتج
        msg = f"{title}\n\n"
        
        # تحويل العروض التلقائية لنص واحد للبحث بداخلها
        all_offers_text = " ".join(auto_offers).lower()
        
        # فحص هل المنتج يشمله خصم أسبوع التوفير (بناءً على الكلمات المفتاحية في أمازون)
        is_savings_week = "توفير" in all_offers_text or "خصم" in all_offers_text or "coupon" in all_offers_text or "توفير" in title
        
        try:
            if price_before and price_now and int(price_before) > int(price_now):
                msg += f"❌ كان {price_before} ريال \n"
                
                # إذا يشمله الخصم، نحسب السعر الجديد بعد خصم الـ 20% الإضافي
                if is_savings_week:
                    discounted_price = round(int(price_now) * 0.80) # خصم 20%
                    msg += f"✅ والان {discounted_price} ريال 🤩\n\n"
                    msg += "🔣 بعد خصم اسبوع التوفير 20%\n\n"
                else:
                    msg += f"✅ والان {price_now} ريال 🤩\n\n"
                    
            elif price_now:
                if is_savings_week:
                    discounted_price = round(int(price_now) * 0.80)
                    msg += f"✅ والان {discounted_price} ريال 🤩\n\n"
                    msg += "🔣 بعد خصم اسبوع التوفير 20%\n\n"
                else:
                    msg += f"✅ والان {price_now} ريال 🤩\n\n"
        except:
            # في حال واجه الكود مشكلة في الحسابات الرياضية، يرجع للسعر الأساسي المستخرج بأمان
            if price_now:
                msg += f"✅ والان {price_now} ريال 🤩\n\n"
        
        # 4. الرابط مباشرة في النهاية
        msg += f"{link}"

        # إرسال الرد لك في الشات الخاص أولاً
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
