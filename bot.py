import logging
import hmac
import hashlib
import datetime
import json
import re
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

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
    target       = "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetItems"
    content_type = "application/json; charset=UTF-8"
    now          = datetime.datetime.now(datetime.timezone.utc)
    amz_date     = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp   = now.strftime("%Y%m%d")
    payload = json.dumps({
        "ItemIds":    [asin],
        "Resources":  ["Images.Primary.Large","ItemInfo.Title","ItemInfo.Features","Offers.Listings.Price","Offers.Listings.SavingBasis"],
        "PartnerTag":  AMAZON_AFFILIATE_TAG,
        "PartnerType": "Associates",
        "Marketplace": MARKETPLACE,
    }, separators=(",", ":"))
    signed_headers    = "content-encoding;content-type;host;x-amz-date;x-amz-target"
    canonical_headers = (
        "content-encoding:amz-1.0\n"
        f"content-type:{content_type}\n"
        f"host:{HOST}\n"
        f"x-amz-date:{amz_date}\n"
        f"x-amz-target:{target}\n"
    )
    payload_hash      = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    canonical_request = "\n".join(["POST","/paapi5/getitems","",canonical_headers,signed_headers,payload_hash])
    credential_scope  = f"{date_stamp}/{REGION_AWS}/{SERVICE}/aws4_request"
    string_to_sign    = "\n".join(["AWS4-HMAC-SHA256",amz_date,credential_scope,hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()])
    def s(k, m):
        return hmac.new(k, m.encode("utf-8"), hashlib.sha256).digest()
    k = s(s(s(s(("AWS4"+AMAZON_SECRET_KEY).encode("utf-8"),date_stamp),REGION_AWS),SERVICE),"aws4_request")
    signature         = hmac.new(k, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization     = f"AWS4-HMAC-SHA256 Credential={AMAZON_ACCESS_KEY}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
    headers = {
        "content-encoding": "amz-1.0",
        "content-type":     content_type,
        "host":             HOST,
        "x-amz-date":       amz_date,
        "x-amz-target":     target,
        "Authorization":    authorization,
    }
    try:
        resp = requests.post(f"https://{HOST}/paapi5/getitems", data=payload, headers=headers, timeout=15)
        logger.info(f"PA-API status: {resp.status_code}")
        if resp.status_code != 200:
            logger.error(f"PA-API error: {resp.text[:300]}")
            return None
        return resp.json()
    except Exception as e:
        logger.error(f"PA-API exception: {e}")
        return None

def extract_asin(text):
    expanded = expand_url(text.strip())
    for pattern in [r"/dp/([A-Z0-9]{10})", r"/product/([A-Z0-9]{10})"]:
        m = re.search(pattern, expanded)
        if m:
            return m.group(1)
    return None

def build_affiliate_link(asin):
    return f"https://{MARKETPLACE}/dp/{asin}?tag={AMAZON_AFFILIATE_TAG}"

def parse_product(data):
    try:
        item      = data["ItemsResult"]["Items"][0]
        title     = item["ItemInfo"]["Title"]["DisplayValue"]
        features  = item.get("ItemInfo",{}).get("Features",{}).get("DisplayValues",[])[:3]
        image     = item.get("Images",{}).get("Primary",{}).get("Large",{}).get("URL","")
        listings  = item.get("Offers",{}).get("Listings",[])
        price = old_price = ""
        if listings:
            price     = listings[0].get("Price",{}).get("DisplayAmount","")
            old_price = listings[0].get("SavingBasis",{}).get("DisplayAmount","")
        return {"title":title,"features":features,"image":image,"price":price,"old_price":old_price}
    except Exception as e:
        logger.error(f"parse error: {e}")
        return None

def format_post(product, asin):
    lines = [f"*{product['title']}*\n"]
    if product["price"]:
        if product["old_price"] and product["old_price"] != product["price"]:
            lines.append(f"~~{product['old_price']}~~ {product['price']} \U0001f525")
        else:
            lines.append(f"\U0001f4b0 {product['price']}")
        lines.append("")
    if product["features"]:
        lines.append("\u2728 *\u0627\u0644\u0645\u0645\u064a\u0632\u0627\u062a:*")
        for f in product["features"]:
            lines.append(f"\u2022 {f}")
        lines.append("")
    lines.append(f"[\U0001f6d2 \u0627\u0634\u062a\u0631\u064a \u0627\u0644\u0622\u0646 \u0645\u0646 \u0623\u0645\u0627\u0632\u0648\u0646]({build_affiliate_link(asin)})")
    lines.append("\n_\u0631\u0627\u0628\u0637 \u0623\u0641\u0644\u064a\u064a\u062a_ \U0001f91d")
    return "\n".join(lines)

async def start(update, context):
    await update.message.reply_text("\U0001f44b \u0623\u0647\u0644\u0627\u064b!\n\n\u0623\u0631\u0633\u0644 \u0644\u064a \u0631\u0627\u0628\u0637 \u0623\u064a \u0645\u0646\u062a\u062c \u0623\u0645\u0627\u0632\u0648\u0646 \u0648\u0633\u0623\u062d\u0648\u0644\u0647 \u0625\u0644\u0649 \u0645\u0646\u0634\u0648\u0631 \u062c\u0627\u0647\u0632 \u0644\u0644\u0646\u0634\u0631 \U0001f680")

async def handle_message(update, context):
    text = update.message.text.strip()
    msg  = await update.message.reply_text("\u23f3 \u062c\u0627\u0631\u064a \u062c\u0644\u0628 \u0645\u0639\u0644\u0648\u0645\u0627\u062a \u0627\u0644\u0645\u0646\u062a\u062c...")
    asin = extract_asin(text)
    if not asin:
        await msg.edit_text("\u26a0\ufe0f \u0645\u0627 \u0642\u062f\u0631\u062a \u0623\u062c\u062f \u0631\u0627\u0628\u0637 \u0623\u0645\u0627\u0632\u0648\u0646 \u0635\u062d\u064a\u062d\u060c \u062c\u0631\u0628 \u0645\u0631\u0629 \u062b\u0627\u0646\u064a\u0629.")
        return
    data    = pa_api_request(asin)
    product = parse_product(data) if data else None
    if not product:
        await msg.edit_text("\u274c \u0645\u0627 \u0642\u062f\u0631\u062a \u0623\u062c\u0644\u0628 \u0645\u0639\u0644\u0648\u0645\u0627\u062a \u0627\u0644\u0645\u0646\u062a\u062c\u060c \u062a\u0623\u0643\u062f \u0645\u0646 \u0627\u0644\u0631\u0627\u0628\u0637.")
        return
    post      = format_post(product, asin)
    image_url = product.get("image","")
    await msg.delete()
    if image_url:
        await update.message.reply_photo(photo=image_url, caption=post, parse_mode="Markdown")
    else:
        await update.message.reply_text(post, parse_mode="Markdown")

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).updater(None).build()
app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("\U0001f916 \u0627\u0644\u0628\u0648\u062a \u0634\u063a\u0627\u0644...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
