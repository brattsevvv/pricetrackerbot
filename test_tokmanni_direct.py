import httpx
import json
import re

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

def test_tokmanni_search(query: str, limit: int = 5):
    url = "https://eucs7.ksearchnet.com/cloud-search/n-search/search"
    params = {
        "ticket": "klevu-15488592134928913",
        "term": query,
        "responseType": "json",
        "paginationStartsFrom": 0,
        "noOfResults": limit * 3
    }
    r = httpx.get(url, params=params, timeout=10.0)
    data = r.json()
    items = []
    for p in data.get("result", []):
        name = p.get("name") or ""
        sale_price = clean_price(str(p.get("salePrice") or p.get("startPrice") or p.get("price") or 0))
        if not sale_price or sale_price <= 0:
            continue
        prod_url = p.get("url") or ""
        img_url = p.get("cloudinary_image") or p.get("imageUrl") or p.get("image")
        deliv = 3.90
        total = round(sale_price + deliv, 2)
        items.append({
            "name": name,
            "base_price": sale_price,
            "deliv": deliv,
            "total": total,
            "url": prod_url,
            "img": img_url
        })
        if len(items) >= limit:
            break
    return items

print("Testing Tokmanni search for 'proteiini':")
results = test_tokmanni_search("proteiini", limit=6)
for it in results:
    print(f"- {it['name']} | Base: {it['base_price']:.2f} € | Total: {it['total']:.2f} € | URL: {it['url']}")
