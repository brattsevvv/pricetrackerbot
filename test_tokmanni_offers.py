import httpx
import json
import re
from bs4 import BeautifulSoup

def clean_price(price_str: str | None) -> float | None:
    if not price_str:
        return None
    match = re.search(r"(\d+(?:[\.,]\d{1,2})?)", str(price_str).replace("\xa0", " ").replace(" ", ""))
    if match:
        try:
            return float(match.group(1).replace(",", "."))
        except ValueError:
            pass
    return None

def test_get_tokmanni_offers(product_url: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = httpx.get(product_url, headers=headers, follow_redirects=True, timeout=12.0)
    soup = BeautifulSoup(r.text, "html.parser")
    title = None
    price = None
    avail = "В наличии"
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            d = json.loads(s.string)
            if isinstance(d, dict) and d.get("@type") in ("Product", "AggregateOffer"):
                title = d.get("name")
                offers = d.get("offers", {})
                if isinstance(offers, dict):
                    price = clean_price(str(offers.get("lowPrice") or offers.get("price") or 0))
                    if "OutOfStock" in str(offers.get("availability", "")):
                        avail = "Нет в наличии"
                elif isinstance(offers, list) and offers:
                    price = clean_price(str(offers[0].get("price") or 0))
                break
        except Exception:
            pass
    if not title:
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else "Tokmanni tuote"
        
    meta_img = soup.find("meta", property="og:image")
    img_url = meta_img.get("content") if meta_img else None
    
    if not price or price <= 0:
        meta_p = soup.find("meta", property="product:price:amount")
        price = clean_price(meta_p.get("content")) if meta_p else 0.0
        
    deliv = 3.90
    total = round(price + deliv, 2)
    return title, img_url, price, deliv, total, avail

print("Testing get_tokmanni_offers:")
url = "https://www.tokmanni.fi/proteiinijauhe-sportlife-700-g-whey100-6419860544755"
res = test_get_tokmanni_offers(url)
print("Title:", res[0])
print("Price:", res[2], "EUR")
print("Total:", res[4], "EUR")
print("Avail:", res[5])
