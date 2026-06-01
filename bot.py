def get_amazon_details(url):
    url = expand_url(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept-Language": "ar-SA,en-US;q=0.9"
    }
    try:
        asin_match = re.search(r'(?:dp|gp/product)/([A-Z0-9]{10})', url)
        if asin_match:
            asin = asin_match.group(1)
            final_link = f"https://www.amazon.sa/dp/{asin}?tag={MY_TAG}"
        else:
            final_link = url.split("?")[0] + f"?tag={MY_TAG}" if "?" in url else url + f"?tag={MY_TAG}"
            
        res = requests.get(final_link, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, "html.parser")
        
        # 1. الاسم
        title_tag = soup.find("span", {"id": "productTitle"})
        title = title_tag.get_text().strip() if title_tag else "منتج من أمازون"
        
        # 2. السعر الحالي
        price_now = ""
        p_now_tag = soup.find("span", {"class": "a-price-whole"})
        if p_now_tag:
            price_now = clean_price(p_now_tag.get_text().strip())

        # 3. السعر قبل
        price_before = ""
        p_before_tag = soup.find("span", {"class": "basisPrice"}) or soup.find("span", {"class": "a-text-strike"})
        if p_before_tag:
            price_before = clean_price(p_before_tag.get_text().strip())

        # 4. العروض التلقائية (أضفنا فحص العروض الجديدة هنا بأمان)
        auto_offers = []
        coupon_tag = soup.find("label", {"id": "vpc_coupon_label"}) or soup.find("span", {"class": "promoPriceHighlight"})
        if coupon_tag:
            offer_text = coupon_tag.get_text().strip()
            if offer_text: auto_offers.append(offer_text)
            
        promo_tag = soup.find("div", {"id": "item_benefit_description"}) or soup.find("span", {"class": "a-truncate-full"}) or soup.find("div", {"id": "apex_desktop_qualifiedBuybox_promotions"})
        if promo_tag:
            promo_text = promo_tag.get_text().strip()
            if len(promo_text) < 150: auto_offers.append(promo_text)

        # فحص إضافي بالخفاء: لو النص داخل الصفحة يحتوي على عروض التوفير
        page_text = res.text.lower()
        if "توفير" in page_text or "saving" in page_text or "coupon" in page_text:
            auto_offers.append("savings_detected")

        # 5. رابط الصورة
        img_tag = soup.find("img", {"id": "landingImage"}) or soup.find("img", {"id": "main-image"})
        img_url = img_tag.get("src") if img_tag else ""

        return title, price_now, price_before, img_url, final_link, auto_offers
    except Exception as e:
        logger.error(f"Error fetching details: {e}")
        return None, None, None, None, url, []


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "amazon" in url or "amzn" in url:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        title, price_now, price_before, img, link, auto_offers = get_amazon_details(url)
        
        # تنسيق النص الأساسي
        msg = f"{title}\n\n"
        
        # إذا لقط أي إشارة للعرض في صفحة أمازون
        if auto_offers and price_now:
            try:
                # تنظيف السعر من أي رموز عشان الحسبة ما تضرب الكود
                clean_num = "".join(re.findall(r'\d+', price_now))
                discounted_price = round(int(clean_num) * 0.80)
                
                if price_before:
                    msg += f"❌ كان {price_before} ريال \n"
                msg += f"✅ والان {discounted_price} ريال 🤩\n\n"
                msg += "🔣بعد خصم اسبوع التوفير20% \n\n"
            except:
                if price_before:
                    msg += f"❌ كان {price_before} ريال \n"
                msg += f"✅ والان {price_now} ريال 🤩\n\n"
        else:
            if price_before and price_now:
                msg += f"❌ كان {price_before} ريال \n"
                msg += f"✅ والان {price_now} ريال 🤩\n\n"
            elif price_now:
                msg += f"✅ والان {price_now} ريال 🤩\n\n"
        
        msg += f"{link}"

        # إرسال الرد في الخاص بنفس الطريقة المضمونة
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
