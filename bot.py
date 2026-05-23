# رقعة برمجية لحل مشكلة التوافق مع بايثون 3.14
import telegram.ext._updater
if not hasattr(telegram.ext._updater.Updater, '_Updater__polling_cleanup_cb'):
    telegram.ext._updater.Updater._Updater__polling_cleanup_cb = None
import logging
import hmac
import hashlib
import datetime
import json
import re
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TELEGRAM_BOT_TOKEN   = "8681119804:AAEw9nDZTPkQzIO58-_Li6zS-2h-dbTWjYE"
AMAZON_ACCESS_KEY    = "AKPANDTX2Z1778330583"
AMAZON_SECRET_KEY    = "aE1cKjKmpNN1gL7hCvH0NzcNkq30FPJ"
AMAZON_AFFILIATE_TAG = "x0659-21"
HOST                 = "webservices.amazon.sa"
MARKETPLACE          = "www.amazon.sa"
REGION_AWS           = "eu-west-1"
SERVICE              = "ProductAdvertisingAPI"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def expand_url(url):
    try:
        r = requests.head(url, allow_redirects=True, timeout=10)
        return r.url
    except Exception:
        return url

def pa_api_request(asin):
    target = "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetItems"
    content_type = "application/json; charset=UTF-8"
    now = datetime.datetime.now(datetime.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    payload = json.dumps({
        "ItemIds": [asin],
        "Resources": ["Images.Primary.Large","ItemInfo.Title","ItemInfo.Features","Offers.Listings.Price","Offers.Listings.SavingBasis"],
        "PartnerTag": AMAZON_AFFILIATE_TAG,
        "PartnerType": "Associates",
        "Marketplace": MARKETPLACE,
    }, separators=(",",":"))
    signed_headers = "content-encoding;content-type;host;x-amz-date;x-amz-target"
    canonical_headers = "content-encoding:amz-1.0\ncontent-type:" + content_type + "\nhost:" + HOST + "\nx-amz-date:" + amz_date + "\nx-amz-target:" + target + "\n"
    payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    canonical_request = "\n".join(["POST","/paapi5/getitems","",canonical_headers,signed_headers,payload_hash])
    credential_scope = date_stamp + "/" + REGION_AWS + "/" + SERVICE + "/aws4_request"
    string_to_sign = "\n".join(["AWS4-HMAC-SHA256",amz_date,credential_scope,hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()])
    def s(k, m):
        return hmac.new(k, m.encode("utf-8"), hashlib.sha256).digest()
    k = s(s(s(s(("AWS4"+AMAZON_SECRET_KEY).encode("utf-8"),date_stamp),REGION_AWS),SERVICE),"aws4_request")
    signature = hmac.new(k, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = "AWS4-HMAC-SHA256 Credential=" + AMAZON_ACCESS_KEY + "/" + credential_scope + ", SignedHeaders=" + signed_headers + ", Signature=" + signature
    headers = {
        "content-encoding": "amz-1.0",
        "content-type": content_type,
        "host": HOST,
        "x-amz-date": amz_date,
        "x-amz-target": target,
        "Authorization": authorization,
    }
    try:
        resp = requests.post("https://" + HOST + "/paapi5/getitems", data=payload, headers=headers, timeout=15)
        logger.info("PA-API status: " + str(resp.status_code))
        if resp.status_code != 200:
            logger.error("PA-API error: " + resp.text[:300])
            return None
        return resp.json()
    except Exception as e:
        logger.error("PA-API exception: " + str(e))
        return None

def extract_asin(text):
    expanded = expand_url(text.strip())
    for pattern in [r"/dp/([A-Z0-9]{10})", r"/product/([A-Z0-9]{10})"]:
        m = re.search(pattern, expanded)
        if m:
            return m.group(1)
    return None

def build_affiliate_link(asin):
    return "https://" + MARKETPLACE + "/dp/" + asin + "?tag=" + AMAZON_AFFILIATE_TAG

def parse_product(data):
    try:
        item = data["ItemsResult"]["Items"][0]
        title = item["ItemInfo"]["Title"]["DisplayValue"]
        features = item.get("ItemInfo",{}).get("Features",{}).get("DisplayValues",[])[:3]
        image = item.get("Images",{}).get("Primary",{}).get("Large",{}).get("URL","")
        listings = item.get("Offers",{}).get("Listings",[])
        price = ""
        old_price = ""
        if listings:
            price = listings[0].get("Price",{}).get("DisplayAmount","")
            old_price = listings[0].get("SavingBasis",{}).get("DisplayAmount","")
        return {"title":title,"features":features,"image":image,"price":price,"old_price":old_price}
    except Exception as e:
        logger.error("parse error: " + str(e))
        return None

def format_post(product, asin):
    lines = ["*" + product["title"] + "*\n"]
    if product["price"]:
        if product["old_price"] and product["old_price"] != product["price"]:
            lines.append("~~" + product["old_price"] + "~~ " + product["price"] + " \U0001f525")
        else:
            lines.append("\U0001f4b0 " + product["price"])
        lines.append("")
    if product["features"]:
        lines.append("\u2728 *\u0627\u0644\u0645\u0645\u064a\u0632\u0627\u062a:*")
        for f in product["features"]:
            lines.append("\u2022 " + f)
        lines.append("")
    lines.append("[\U0001f6d2 \u0627\u0634\u062a\u0631\u064a \u0627\u0644\u0622\u0646](" + build_affiliate_link(asin) + ")")
    lines.append("\n_\u0631\u0627\u0628\u0637 \u0623\u0641\u0644\u064a\u064a\u062a_ \U0001f91d")
    return "\n".join(lines)

async def start(update, context):
    await update.message.reply_text("\U0001f44b \u0623\u0647\u0644\u0627\u064b! \u0623\u0631\u0633\u0644 \u0631\u0627\u0628\u0637 \u0623\u0645\u0627\u0632\u0648\u0646 \U0001f680")

async def handle_message(update, context):
    text = update.message.text.strip()
    msg = await update.message.reply_text("\u23f3 \u062c\u0627\u0631\u064a \u062c\u0644\u0628 \u0645\u0639\u0644\u0648\u0645\u0627\u062a \u0627\u0644\u0645\u0646\u062a\u062c...")
    asin = extract_asin(text)
    if not asin:
        await msg.edit_text("\u26a0\ufe0f \u0645\u0627 \u0642\u062f\u0631\u062a \u0623\u062c\u062f \u0631\u0627\u0628\u0637 \u0635\u062d\u064a\u062d")
        return
    data = pa_api_request(asin)
    product = parse_product(data) if data else None
    if not product:
        await msg.edit_text("\u274c \u0645\u0627 \u0642\u062f\u0631\u062a \u0623\u062c\u0644\u0628 \u0645\u0639\u0644\u0648\u0645\u0627\u062a \u0627\u0644\u0645\u0646\u062a\u062c")
        return
    post = format_post(product, asin)
    image_url = product.get("image","")
    await msg.delete()
    if image_url:
        await update.message.reply_photo(photo=image_url, caption=post, parse_mode="Markdown")
    else:
        await update.message.reply_text(post, parse_mode="Markdown")
import threading
import http.server
import socketserver

def run_health_server():
    class HealthHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()

    # تشغيل سيرفر الويب الداخلي على المنفذ 10000 المطلوب من ريندر
    with socketserver.TCPServer(("", 10000), HealthHandler) as httpd:
        httpd.serve_forever()

def main():
    # 1. تشغيل سيرفر الويب في خلفية الكود كخيط مستقل (Thread)
    web_thread = threading.Thread(target=run_health_server, daemon=True)
    web_thread.start()

    # 2. تشغيل البوت الأساسي
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🤖 البوت شغال وسيرفر الويب مستقر...")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
