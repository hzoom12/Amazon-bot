import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import re
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- بيانات حازم الرسمية والنظيفة 🎯 ---
BOT_TOKEN = "8681119804:AAGhNgJfeliEEK3JCKGZSbFcjpJneadoCPk"
MY_TAG = "x0659-21"
TARGET_CHANNEL = "@smartshophazim"

def expand_url(url):
    """فك الروابط المختصرة القادمة من تطبيق الجوال"""
    try:
        if "amzn.to" in url or "amzn.eu" in url:
            response = requests.Session().head(url, allow_redirects=True, timeout=7)
            return response.url
        return url
    except Exception as e:
        logger.error(f"Error expanding URL: {e}")
        return url

def clean_price(price_str):
    if not price_str: return ""
    # تنظيف النص من أي كلام ونبقي فقط على الأرقام والنقاط (مثل 39.95)
    price_match = re.search(r'\d+(?:\.\d+)?', price_str.replace(',', ''))
    if price_match:
        return price_match.group(0)
    return ""

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
        
        # 2. السعر الحالي (لقط أدق وعزل الفراغات)
        price_now = ""
        price_container = soup.find("span", {"class": "a-price"})
        if price_container:
            p_text = price_container.find("span", {"class": "a-offscreen"})
            if p_text:
                price_now = clean_price(p_text.get_text().strip())
        
        if not price_now:
            p_now_tag = soup.find("span", {"class": "a-price-whole"})
            if p_now_tag:
                price_now = clean_price(p_now_tag.get_text().strip())

        # 3. السعر قبل
        price_before = ""
        p_before_tag = soup.find("span", {"class": "basisPrice"}) or soup.find("span", {"class": "a-text-strike"})
        if p_before_tag:
            price_before = clean_price(p_before_tag.get_text().strip())

        # 4. العروض التلقائية
        auto_offers = []
        coupon_tag = soup.find("label", {"id": "vpc_coupon_label"}) or soup.find("span", {"class": "promoPriceHighlight"})
        if coupon_tag:
            offer_text = coupon_tag.get_text().strip()
            if offer_text: auto_offers.append(offer_text)
            
        promo_tag = soup.find("div", {"id": "item_benefit_description"}) or soup.find("span", {"class": "a-truncate-full"})
        if promo_tag:
            promo_text = promo_tag.get_text().strip()
            if len(promo_text) < 100: auto_offers.append(promo_text)

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
        
        # فحص الحسبة الذكية وحساب الـ 20% لو في عروض
        if auto_offers and price_now:
            try:
                # تحويل السعر لرقم عشري وحساب الخصم بدقة وتقريبه لأقرب رقم صحيح
                base_p = float(price_now)
                discounted_price = round(base_p * 0.80)
                
                # السعر قبل الخصم الكلي بيصير هو السعر الحالي المعروض بـ أمازون قبل كود التوفير
                msg += f"❌ كان {round(base_p)} ريال \n"
                msg += f"✅ والان {discounted_price} ريال 🤩\n\n"
                msg += "🔹 يشملها خصم اسبوع التوفير20٪ \n\n"
            except:
                if price_before and price_now:
                    msg += f"❌ كان {round(float(price_before))} ريال \n"
                    msg += f"✅ والان {round(float(price_now))} ريال 🤩\n\n"
                elif price_now:
                    msg += f"✅ والان {round(float(price_now))} ريال 🤩\n\n"
        else:
            # إذا ما في عرض توفير، يطبع الأسعار الطبيعية بشكل نظيف ومقرب
            if price_before and price_now:
                msg += f"❌ كان {round(float(price_before))} ريال \n"
                msg += f"✅ والان {round(float(price_now))} ريال 🤩\n\n"
            elif price_now:
                msg += f"✅ والان {round(float(price_now))} ريال 🤩\n\n"
        
        msg += f"{link}"

        # إرسال الرد في الخاص
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

def main():
    logger.info("Starting bot...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
