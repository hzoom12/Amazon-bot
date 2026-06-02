def get_amazon_details(url):
    url = expand_url(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept-Language": "ar-SA,en-US;q=0.9"
    }
    try:
        # 1. تنظيف الرابط فوراً وبناء رابط أفلييت نظيف خاص بحازم فقط 🎯
        asin_match = re.search(r'(?:dp|gp/product)/([A-Z0-9]{10})', url)
        if asin_match:
            asin = asin_match.group(1)
            final_link = f"https://www.amazon.sa/dp/{asin}?tag={MY_TAG}"
        else:
            # قص الرابط قبل علامة الاستفهام لمنع تسريب بيانات الأدوات الأخرى
            base_url = url.split("?")[0]
            final_link = f"{base_url}?tag={MY_TAG}"
            
        # 2. جلب الصفحة باستخدام الرابط النظيف
        res = requests.get(final_link, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, "html.parser")
        
        # الاسم
        title_tag = soup.find("span", {"id": "productTitle"})
        title = title_tag.get_text().strip() if title_tag else "منتج من أمازون"
        
        # السعر الحالي
        price_now = ""
        p_now_tag = soup.find("span", {"class": "a-price-whole"})
        if p_now_tag:
            price_now = clean_price(p_now_tag.get_text().strip())

        # السعر قبل
        price_before = ""
        p_before_tag = soup.find("span", {"class": "basisPrice"}) or soup.find("span", {"class": "a-text-strike"})
        if p_before_tag:
            price_before = clean_price(p_before_tag.get_text().strip())

        # العروض التلقائية الكوبونات (فحص دقيق داخل تاغات العروض فقط)
        auto_offers = []
        coupon_tag = soup.find("label", {"id": "vpc_coupon_label"}) or soup.find("span", {"class": "promoPriceHighlight"})
        if coupon_tag:
            offer_text = coupon_tag.get_text().strip()
            if offer_text: auto_offers.append(offer_text)
            
        promo_tag = soup.find("div", {"id": "item_benefit_description"}) or soup.find("span", {"class": "a-truncate-full"}) or soup.find("div", {"id": "apex_desktop_qualifiedBuybox_promotions"})
        if promo_tag:
            promo_text = promo_tag.get_text().strip()
            if len(promo_text) < 150 and any(keyword in promo_text.lower() for keyword in ["توفير", "خصم", "coupon", "saving", "تخفيض"]):
                auto_offers.append(promo_text)

        # رابط الصورة
        img_tag = soup.find("img", {"id": "landingImage"}) or soup.find("img", {"id": "main-image"})
        img_url = img_tag.get("src") if img_tag else ""

        return title, price_now, price_before, img_url, final_link, auto_offers
    except Exception as e:
        logger.error(f"Error fetching details: {e}")
        return None, None, None, None, url, []
