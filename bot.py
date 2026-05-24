import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import re

# --- بياناتك ---
BOT_TOKEN = "8681119804:AAFNa4VekRGp7ERiMh9ke8ZOfsqYYM6eTig"
MY_TAG = "x0659-21"

def clean_price(price_str):
    if not price_str: return ""
    digits = re.findall(r'\d+', price_str.replace(',', ''))
    if digits:
        half = len(digits[0]) // 2
        first_part = digits[0][:half]
        second_part = digits[0][half:]
        if first_part == second_part and len(digits[0]) > 2:
            return first_part
        return digits[0]
    return ""

def get_amazon_details(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept-Language": "ar-SA,en-US;q=0.9"
    }
    try:
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

        # 4. استخراج العروض التلقائية (Coupon / Promotions)
        auto_offers = []
        # البحث عن الكوبونات (وفر X%)
        coupon_tag = soup.find("label", {"id": "vpc_coupon_label"}) or soup.find("span", {"class": "promoPriceHighlight"})
        if coupon_tag:
            offer_text = coupon_tag.get_text().strip()
            if offer_text: auto_offers.append(offer_text)
            
        # البحث عن عروض البنوك أو العروض الترويجية المختصرة
        promo_tag = soup.find("div", {"id": "item_benefit_description"}) or soup.find("span", {"class": "a-truncate-full"})
        if promo_tag:
            promo_text = promo_tag.get_text().strip()
            if len(promo_text) < 100: auto_offers.append(promo_text)

        # 5. رابط الصورة
        img_tag = soup.find("img", {"id": "landingImage"}) or soup.find("img", {"id": "main-image"})
        img_url = img_tag.get("src") if img_tag else ""

        return title, price_now, price_before, img_url, final_link, auto_offers
    except:
        return None, None, None, None, url, []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "amazon.sa" in url or "amzn.eu" in url or "amzn.to" in url:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        title, price_now, price_before, img, link, auto_offers = get_amazon_details(url)
        
        msg = f"📦 *{title[:90]}...*\n\n"
        
        if price_before and price_now and int(price_before) > int(price_now):
            msg += f"❌ السعر كان: {price_before} ريال\n"
            msg += f"✅ السعر والآن: {price_now} ريال فقط! 🔥\n\n"
        elif price_now:
            msg += f"💰 السعر الحالي: {price_now} ريال\n\n"
        
        # إضافة العروض المكتشفة تلقائياً
        if auto_offers or True: # تركت True عشان نضيف العروض الثابتة حقتك دائماً
            msg += "ولسه تقدر تاخذها أقل\n"
            
            # عرض العروض اللي لقاها البوت في الموقع
            for offer in auto_offers:
                msg += f"✨ {offer}\n"
            
            # العروض الثابتة اللي تبيها دائماً تظهر
            msg += "✨ الكود اللي أرسله 15٪\n"
            msg += "✨ خصم الأهلي 25٪\n\n"
        
        msg += f"👇 للشراء والطلب من هنا:\n{link}"

        if img:
            try:
                await update.message.reply_photo(photo=img, caption=msg, parse_mode='Markdown')
            except:
                await update.message.reply_text(msg, parse_mode='Markdown')
        else:
            await update.message.reply_text(msg, parse_mode='Markdown')

if __name__ == '__main__':
    print("🚀 البوت الذكي (مستخرج العروض) شغال الآن..")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)
