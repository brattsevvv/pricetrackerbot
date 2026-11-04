import asyncio
import json
import logging
import re
import urllib.parse
from dataclasses import dataclass
import httpx
from bs4 import BeautifulSoup
from config import settings

logger = logging.getLogger(__name__)

@dataclass
class ProductItem:
    title: str
    url: str
    price_preview: str
    store_name: str = ""
    base_price: float = 0.0
    delivery_fee: float = 0.0
    total_price: float = 0.0
    image_url: str | None = None

@dataclass
class OfferItem:
    store_name: str
    base_price: float
    delivery_fee: float
    total_price: float
    link: str
    direct_link: str | None
    availability: str
    product_title: str | None = None

def get_direct_store_url(store_name: str, product_title: str) -> str | None:
    """Generate direct store search URL for popular retailers."""
    # Remove parenthetical specs (e.g. '(Musta, 128 GB)')
    clean_title = re.sub(r"\s*\(.*?\)", "", product_title).strip()
    # Remove any price suffix like '- Hinta 126,9 €'
    clean_title = re.sub(r"\s*-\s*Hinta\s+[\d,\.]+\s*€.*$", "", clean_title, flags=re.IGNORECASE).strip()
    encoded = urllib.parse.quote_plus(clean_title)
    s = store_name.lower()
    if "maxgaming" in s:
        return f"https://www.maxgaming.fi/etsi?q={encoded}"
    if "verkkokauppa" in s:
        return f"https://www.verkkokauppa.com/fi/search?query={encoded}"
    if "gigantti" in s:
        return f"https://www.gigantti.fi/search?q={encoded}"
    if "power" in s:
        return f"https://www.power.fi/search/?q={encoded}"
    if "proshop" in s:
        return f"https://www.proshop.fi/?s={encoded}"
    if "datatronic" in s:
        return f"https://datatronic.fi/haku?controller=search&s={encoded}"
    if "veikon" in s:
        return f"https://www.veikonkone.fi/catalogsearch/result/?q={encoded}"
    if "dna" in s:
        return f"https://kauppa.dna.fi/haku?q={encoded}"
    if "elisa" in s:
        return f"https://elisa.fi/kauppa/haku?q={encoded}"
    if "telia" in s:
        return f"https://kauppa.telia.fi/kauppa/haku?q={encoded}"
    if "jimm" in s:
        return f"https://www.jimms.fi/fi/Product/Search?q={encoded}"
    if "kärkkäinen" in s or "karkkainen" in s:
        return f"https://www.karkkainen.com/verkkokauppa/search?searchTerm={encoded}"
    if "tokmanni" in s:
        return f"https://www.tokmanni.fi/search?q={encoded}"
    return None

def clean_price(price_str: str | None) -> float | None:
    if not price_str:
        return None
    if "ilmainen" in price_str.lower() or "free" in price_str.lower():
        return 0.0
    # Match the first decimal number pattern like "9.90" or "9,90" or "597"
    match = re.search(r"(\d+(?:[\.,]\d{1,2})?)", price_str.replace("\xa0", " ").replace(" ", ""))
    if match:
        try:
            return float(match.group(1).replace(",", "."))
        except ValueError:
            pass
    return None

def is_irrelevant_supplement_item(title: str, query: str) -> bool:
    """Filter out pet food, cat snacks, baking mixes (pancakes), and shampoos that mistakenly match supplement queries."""
    t = title.lower()
    q = query.lower()
    
    # Pet food keywords (cat, dog, snacks)
    pet_keywords = [
        "kissa", "kissan", "koira", "koiran", "lemmikki", "lemmikkien",
        "cat", "dog", "pet", "herkkupala", "purina", "latz", "whiskas",
        "pedigree", "hau-hau", "prima pet", "kissanruoka", "koiranruoka",
        "kissan hiekka", "kissanvessa", "kissanherkku", "koiranherkku"
    ]
    if any(k in t for k in pet_keywords) and not any(k in q for k in pet_keywords):
        return True
        
    # Shampoo / cosmetics keywords for creatine/protein
    hair_keywords = ["shampoo", "hoitoaine", "hiuksille", "hiusnaamio", "suihkugeeli", "seerumi", "kasvovoide"]
    supplement_keywords = ["kreatiini", "creatine", "whey", "protein", "proteiini", "proteiinijauhe", "bcaa", "gainer", "heraproteiini"]
    if any(k in q for k in supplement_keywords):
        if any(h in t for h in hair_keywords) and not any(h in q for h in hair_keywords):
            return True
            
    # Food baking mixes & snacks for protein powder queries (pancakes, pudding, porridge, bread, cookies, bars)
    baking_keywords = [
        "pannukakku", "pannukakkujauhe", "lettujauhe", "lettu", "pancake",
        "vanukas", "pudding", "puuro", "porridge", "leipä", "keksi", "cookie",
        "mysli", "muesli", "pasta", "patukka", "kaurahiutale", "hiutale"
    ]
    if any(k in q for k in supplement_keywords):
        allow_words = ["pannukakku", "pancake", "patukka", "bar", "vanukas", "pudding", "puuro", "leipä", "блин", "батончик"]
        if any(b in t for b in baking_keywords) and not any(a in q for a in allow_words):
            return True
            
    # Sauces, condiments, and snacks (e.g. soy sauce matching soy protein queries)
    condiment_keywords = [
        "kastike", "soijakastike", "soijarouhe", "öljy", "etikka", "sinappi",
        "proteiinikakku", "riisikakku", "maissikakku", "välipalakeksi"
    ]
    if any(k in q for k in supplement_keywords):
        if any(c in t for c in condiment_keywords) and not any(c in q for c in condiment_keywords):
            return True

    # Stationery, glue, crafts (e.g. 'Creative pen', 'pikaliima' matching 'creatine')
    craft_keywords = ["liima", "pikaliima", "liimapyssy", "teippi", "kynä", "pen", "sakset", "maali"]
    if any(k in q for k in supplement_keywords):
        if any(c in t for c in craft_keywords) and not any(c in q for c in craft_keywords):
            return True

    return False

def is_irrelevant_tech_item(title: str, query: str) -> bool:
    """Filter out small accessories (filters, cleaning tablets, descalers, jugs) when user searches for coffee machine/maker."""
    t = title.lower()
    q = query.lower()
    coffee_machine_keywords = [
        "kahvikone", "kahvinkeitin", "espressokeitin", "espressokone",
        "kapselikahvikone", "moccamaster", "delonghi", "philips", "melitta", "krups"
    ]
    if any(k in q for k in coffee_machine_keywords):
        coffee_acc = [
            "suodatinpaperi", "kalkinpoisto", "puhdistustablet", "vedensuodatin",
            "puhdistusjauhe", "tiiviste", "puhdistusaine", "kalkinpoistaja", "suodatinpussi",
            "harja", "kahvinkeitinharja", "kapseli", "kahvikapseli", "lasikannu",
            "suodatinsuppilo", "suodatinpidike", "brew basket", "filter holder", "kalkinpoisto"
        ]
        # Filter out replacement jugs/carafes if user is searching for coffee machine
        if ("kannu" in t or "lasikannu" in t) and not any(w in t for w in ["kahvinkeitin", "kahvikone", "espressokeitin", "termoskannulla"]):
            if not any(w in q for w in ["kannu", "lasikannu"]):
                return True

        if any(a in t for a in coffee_acc) and not any(a in q for a in coffee_acc):
            return True
    return False

class PriceScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": settings.USER_AGENT,
            "Accept-Language": "fi-FI,fi;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    async def search_hinta(self, query: str, limit: int = 5) -> list[ProductItem]:
        """Search products on Hinta.fi (electronics, appliances, tech, general goods)."""
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://hinta.fi/haku?q={encoded_query}"
        
        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=12.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []
                
                soup = BeautifulSoup(resp.text, "html.parser")
                product_links = soup.select("a.hv-prt_product-a")
                results = []
                
                for item in product_links:
                    title_el = item.select_one(".hv--name")
                    features_el = item.select_one(".hv--features")
                    img_el = item.select_one("img.hv-product-tn-img")
                    href = item.get("href")
                    
                    title = title_el.get_text(strip=True) if title_el else ""
                    features = features_el.get_text(strip=True) if features_el else ""
                    full_title = f"{title} ({features})" if features else title
                    
                    if is_irrelevant_supplement_item(full_title, query) or is_irrelevant_tech_item(full_title, query):
                        continue
                    
                    parent_row = item.find_parent("tr")
                    price_el = parent_row.select_one(".hv--price") if parent_row else None
                    price_preview = price_el.get_text(" ", strip=True) if price_el else ""
                    
                    base_price = clean_price(price_preview) or 0.0
                    tot_match = re.search(r"Toimitettuna\s+([\d\s\xa0,\.]+?)(?:€|\s*$)", price_preview, re.IGNORECASE)
                    tot_price = clean_price(tot_match.group(1)) if tot_match else base_price
                    deliv_fee = round(tot_price - base_price, 2) if tot_price >= base_price else 0.0
                    
                    image_url = None
                    if img_el and img_el.get("src"):
                        src = img_el.get("src")
                        image_url = f"https://hinta.fi{src}" if src.startswith("/") else src
                    
                    product_url = f"https://hinta.fi{href}" if href and href.startswith("/") else href
                    
                    results.append(ProductItem(
                        title=full_title,
                        url=product_url,
                        price_preview=price_preview,
                        store_name="Hinta.fi",
                        base_price=base_price,
                        delivery_fee=deliv_fee,
                        total_price=tot_price or base_price,
                        image_url=image_url
                    ))
                    if len(results) >= limit:
                        break
                    
                return results
        except Exception as e:
            logger.warning(f"Hinta.fi search failed: {e}")
            return []

    async def search_fitnesstukku(self, query: str, limit: int = 5) -> list[ProductItem]:
        """Search sports nutrition & health goods on Fitnesstukku.fi (creatine, protein, vitamins)."""
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.fitnesstukku.fi/search?q={encoded}"
        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=10.0) as client:
                r = await client.get(url)
                if r.status_code != 200:
                    return []
                soup = BeautifulSoup(r.text, "html.parser")
                tiles = soup.select(".product-tile")
                items = []
                for t in tiles:
                    link_el = t.select_one("a[href*='.html']")
                    if not link_el:
                        continue
                    href = link_el.get("href", "")
                    product_url = f"https://www.fitnesstukku.fi{href}" if href.startswith("/") else href
                    
                    title_candidates = [
                        a.get_text(strip=True) for a in t.find_all("a")
                        if a.get_text(strip=True) and not a.get("href", "").startswith("/on/demandware") and a.get_text(strip=True) != "Seuraa"
                    ]
                    title = title_candidates[0] if title_candidates else "Ravintolisä"
                    
                    brand_el = t.select_one(".brand") or t.select_one("a[href*='kaikkituotemerkit']")
                    brand = brand_el.get_text(strip=True) if brand_el else ""
                    if brand and brand.lower() not in title.lower():
                        title = f"{brand} - {title}"
                        
                    if is_irrelevant_supplement_item(title, query):
                        continue
                        
                    sales_el = t.select_one(".sales .value") or t.select_one(".sales") or t.select_one(".price")
                    price_text = sales_el.get_text(strip=True) if sales_el else ""
                    price = clean_price(price_text)
                    if not price or price <= 0:
                        continue
                        
                    img_el = t.select_one("img")
                    img_url = img_el.get("src") if img_el else None
                    
                    deliv = 0.0 if price >= 49.0 else 4.90
                    total = round(price + deliv, 2)
                    deliv_str = "ilmainen toimitus" if deliv == 0.0 else "+4,90 € toimitus"
                    price_preview = f"{price:.2f} € ({deliv_str})"
                    
                    items.append(ProductItem(
                        title=title,
                        url=product_url,
                        price_preview=price_preview,
                        store_name="Fitnesstukku",
                        base_price=price,
                        delivery_fee=deliv,
                        total_price=total,
                        image_url=img_url
                    ))
                    if len(items) >= limit:
                        break
                return items
        except Exception as e:
            logger.warning(f"Fitnesstukku search failed: {e}")
            return []

    async def search_karkkainen(self, query: str, limit: int = 5) -> list[ProductItem]:
        """Search products on Karkkainen.com (department store, fitness & sports nutrition, electronics)."""
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.karkkainen.com/verkkokauppa/search?searchTerm={encoded}"
        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=12.0) as client:
                r = await client.get(url)
                if r.status_code != 200:
                    return []
                soup = BeautifulSoup(r.text, "html.parser")
                script = soup.find("script", id="__NEXT_DATA__")
                if not script or not script.string:
                    return []
                data = json.loads(script.string)
                fallback = data.get("props", {}).get("pageProps", {}).get("fallback", {})
                items = []
                for k, v in fallback.items():
                    if "findPro" in k and isinstance(v, dict):
                        for item in v.get("contents", []):
                            name = item.get("name") or ""
                            if is_irrelevant_supplement_item(name, query) or is_irrelevant_tech_item(name, query):
                                continue
                                
                            href = item.get("seo", {}).get("href", "")
                            prices = item.get("price", [])
                            val = min([float(p["value"]) for p in prices if isinstance(p, dict) and "value" in p], default=0.0)
                            thumb = item.get("thumbnail")
                            if thumb and "h_80" in thumb:
                                thumb = thumb.replace("h_80%2Cq_auto%2Cw_80", "h_400%2Cq_auto%2Cw_400")
                            
                            if href and val > 0:
                                prod_url = f"https://www.karkkainen.com/verkkokauppa{href}"
                                deliv = 3.90
                                total = round(val + deliv, 2)
                                price_preview = f"{val:.2f} € (+{deliv:.2f} € toimitus)"
                                items.append(ProductItem(
                                    title=name,
                                    url=prod_url,
                                    price_preview=price_preview,
                                    store_name="Kärkkäinen",
                                    base_price=val,
                                    delivery_fee=deliv,
                                    total_price=total,
                                    image_url=thumb
                                ))
                                if len(items) >= limit:
                                    break
                return items
        except Exception as e:
            logger.warning(f"Karkkainen search failed: {e}")
            return []

    async def search_tokmanni(self, query: str, limit: int = 5) -> list[ProductItem]:
        """Search products on Tokmanni.fi via Klevu Cloud Search API."""
        url = "https://eucs7.ksearchnet.com/cloud-search/n-search/search"
        tokmanni_query = "proteiinijauhe" if query.lower() in ("whey", "protein", "proteiini", "whey proteiini") else query
        params = {
            "ticket": "klevu-15488592134928913",
            "term": tokmanni_query,
            "responseType": "json",
            "paginationStartsFrom": 0,
            "noOfResults": limit * 3
        }
        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=10.0) as client:
                r = await client.get(url, params=params)
                if r.status_code != 200:
                    return []
                data = r.json()
                items = []
                for p in data.get("result", []):
                    name = p.get("name") or ""
                    if is_irrelevant_supplement_item(name, query) or is_irrelevant_tech_item(name, query):
                        continue
                        
                    sale_price = clean_price(str(p.get("salePrice") or p.get("startPrice") or p.get("price") or 0))
                    if not sale_price or sale_price <= 0:
                        continue
                        
                    prod_url = p.get("url") or ""
                    img_url = p.get("cloudinary_image") or p.get("imageUrl") or p.get("image")
                    deliv = 3.90
                    total = round(sale_price + deliv, 2)
                    price_preview = f"{sale_price:.2f} € (+{deliv:.2f} € toimitus)"
                    
                    items.append(ProductItem(
                        title=name,
                        url=prod_url,
                        price_preview=price_preview,
                        store_name="Tokmanni",
                        base_price=sale_price,
                        delivery_fee=deliv,
                        total_price=total,
                        image_url=img_url
                    ))
                    if len(items) >= limit:
                        break
                return items
        except Exception as e:
            logger.warning(f"Tokmanni search failed: {e}")
            return []

    async def search(self, query: str, limit: int = 6) -> list[ProductItem]:
        """Search concurrently across Hinta.fi, Fitnesstukku.fi, Karkkainen.com, and Tokmanni.fi."""
        q_lower = query.lower()
        fitness_keywords = [
            "kreatiini", "creatine", "whey", "protein", "proteiini", "bcaa", 
            "mass", "gainer", "vitamiin", "omega", "pre workout", "pwo",
            "sportlife", "puls", "fast", "leader", "puhdistamo", "lisäravinne",
            "ravintolisä", "palautusjuoma", "booster", "proteiinijauhe", "heraproteiini",
            "soija", "soijaproteiini", "kasviproteiini", "herne", "herneproteiini"
        ]
        is_fitness_query = any(k in q_lower for k in fitness_keywords)
        
        # When user searches generic protein powder, search both general protein powder AND soy protein
        is_generic_protein = q_lower in ("proteiini", "protein", "proteiinijauhe", "whey proteiini")

        if is_generic_protein:
            t1 = self.search_tokmanni("proteiinijauhe", limit)
            t2 = self.search_tokmanni("soijaproteiini", limit)
            k1 = self.search_karkkainen("proteiinijauhe", limit)
            k2 = self.search_karkkainen("soijaproteiini", limit)
            f1 = self.search_fitnesstukku("proteiinijauhe", limit)
            f2 = self.search_fitnesstukku("soijaproteiini", limit)
            h1 = self.search_hinta("proteiinijauhe", limit)
            
            gathered = await asyncio.gather(t1, t2, k1, k2, f1, f2, h1, return_exceptions=True)
            all_supps = []
            seen_urls = set()
            for sublist in gathered:
                if isinstance(sublist, list):
                    for item in sublist:
                        if item.url not in seen_urls and item.total_price > 0:
                            seen_urls.add(item.url)
                            all_supps.append(item)
                            
            all_supps.sort(key=lambda x: x.total_price if x.total_price > 0 else 9999)
            return all_supps[:limit]
            
        elif is_fitness_query:
            hinta_task = self.search_hinta(query, limit)
            fitness_task = self.search_fitnesstukku(query, limit)
            karkkainen_task = self.search_karkkainen(query, limit)
            tokmanni_task = self.search_tokmanni(query, limit)
            
            hinta_res, fitness_res, karkkainen_res, tokmanni_res = await asyncio.gather(
                hinta_task, fitness_task, karkkainen_task, tokmanni_task, return_exceptions=True
            )
            hinta_items = hinta_res if isinstance(hinta_res, list) else []
            fitness_items = fitness_res if isinstance(fitness_res, list) else []
            karkkainen_items = karkkainen_res if isinstance(karkkainen_res, list) else []
            tokmanni_items = tokmanni_res if isinstance(tokmanni_res, list) else []
            
            supplements = sorted(
                fitness_items + karkkainen_items + tokmanni_items,
                key=lambda x: x.total_price if x.total_price > 0 else 9999
            )
            return (supplements + hinta_items)[:limit]
        else:
            # Coffee machines, tech, and appliances
            hinta_task = self.search_hinta(query, limit)
            karkkainen_task = self.search_karkkainen(query, limit)
            tokmanni_task = self.search_tokmanni(query, limit)
            
            hinta_res, karkkainen_res, tokmanni_res = await asyncio.gather(
                hinta_task, karkkainen_task, tokmanni_task, return_exceptions=True
            )
            hinta_items = hinta_res if isinstance(hinta_res, list) else []
            karkkainen_items = karkkainen_res if isinstance(karkkainen_res, list) else []
            tokmanni_items = tokmanni_res if isinstance(tokmanni_res, list) else []
            
            results = []
            seen = set()
            is_coffee_or_appliance = any(k in q_lower for k in [
                "kahvikone", "kahvinkeitin", "espressokeitin", "moccamaster", "delonghi",
                "philips", "melitta", "krups", "jura", "wilfa", "imuri", "robotti"
            ])
            if is_coffee_or_appliance:
                all_tech = sorted(
                    [i for i in (hinta_items + karkkainen_items + tokmanni_items) if i.total_price > 0],
                    key=lambda x: x.total_price
                )
                for item in all_tech:
                    if item.url not in seen:
                        seen.add(item.url)
                        results.append(item)
            else:
                for item in (hinta_items + karkkainen_items + tokmanni_items):
                    if item.url not in seen:
                        seen.add(item.url)
                        results.append(item)
                        
            return results[:limit]

    async def get_fitnesstukku_offers(self, product_url: str) -> tuple[str, str | None, list[OfferItem]]:
        """Fetch offer details for a Fitnesstukku product URL."""
        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=12.0) as client:
                r = await client.get(product_url)
                if r.status_code != 200:
                    return "", None, []
                soup = BeautifulSoup(r.text, "html.parser")
                
                title_el = soup.select_one("h1.product-name") or soup.find("h1") or soup.select_one("title")
                title = title_el.get_text(strip=True) if title_el else "Ravintolisä"
                title = re.sub(r"\s*\|\s*Fitnesstukku.*$", "", title, flags=re.IGNORECASE).strip()
                
                img_el = soup.select_one("meta[property='og:image']") or soup.select_one(".primary-image")
                img_url = img_el.get("content") if img_el and img_el.name == "meta" else (img_el.get("src") if img_el else None)
                
                price_el = soup.select_one(".price-sales") or soup.select_one(".prices .sales") or soup.select_one(".price")
                price = clean_price(price_el.get_text(strip=True)) if price_el else 0.0
                if price <= 0:
                    return title, img_url, []
                    
                deliv = 0.0 if price >= 49.0 else 4.90
                total = round(price + deliv, 2)
                
                offer = OfferItem(
                    store_name="Fitnesstukku.fi",
                    base_price=price,
                    delivery_fee=deliv,
                    total_price=total,
                    link=product_url,
                    direct_link=product_url,
                    availability="В наличии",
                    product_title=title
                )
                return title, img_url, [offer]
        except Exception as e:
            logger.warning(f"Fitnesstukku get_offers failed: {e}")
            return "", None, []

    async def get_karkkainen_offers(self, product_url: str) -> tuple[str, str | None, list[OfferItem]]:
        """Fetch offer details for a Karkkainen product URL."""
        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=12.0) as client:
                r = await client.get(product_url)
                if r.status_code != 200:
                    return "", None, []
                soup = BeautifulSoup(r.text, "html.parser")
                title = None
                price = None
                avail = "В наличии"
                for s in soup.find_all("script", type="application/ld+json"):
                    try:
                        d = json.loads(s.string)
                        if isinstance(d, dict) and d.get("@type") == "Product":
                            title = d.get("name")
                            offers = d.get("offers", {})
                            if isinstance(offers, dict):
                                price = float(offers.get("price", 0))
                                if "OutOfStock" in str(offers.get("availability", "")):
                                    avail = "Нет в наличии"
                            break
                    except Exception:
                        pass
                if not title:
                    h1 = soup.find("h1")
                    title = h1.get_text(strip=True) if h1 else "Tuote"
                
                meta_img = soup.find("meta", property="og:image")
                img_url = meta_img.get("content") if meta_img else None
                
                if not price or price <= 0:
                    price_el = soup.select_one(".price") or soup.select_one("[itemprop='price']")
                    price = clean_price(price_el.get_text(strip=True)) if price_el else 0.0
                    
                if not price or price <= 0:
                    return title, img_url, []
                    
                deliv = 3.90
                total = round(price + deliv, 2)
                offer = OfferItem(
                    store_name="Kärkkäinen",
                    base_price=price,
                    delivery_fee=deliv,
                    total_price=total,
                    link=product_url,
                    direct_link=product_url,
                    availability=avail,
                    product_title=title
                )
                return title, img_url, [offer]
        except Exception as e:
            logger.warning(f"Karkkainen get_offers failed: {e}")
            return "", None, []

    async def get_tokmanni_offers(self, product_url: str) -> tuple[str, str | None, list[OfferItem]]:
        """Fetch offer details for a Tokmanni product URL."""
        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=12.0) as client:
                r = await client.get(product_url)
                if r.status_code != 200:
                    return "", None, []
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
                    
                if not price or price <= 0:
                    return title, img_url, []
                    
                deliv = 3.90
                total = round(price + deliv, 2)
                offer = OfferItem(
                    store_name="Tokmanni",
                    base_price=price,
                    delivery_fee=deliv,
                    total_price=total,
                    link=product_url,
                    direct_link=product_url,
                    availability=avail,
                    product_title=title
                )
                return title, img_url, [offer]
        except Exception as e:
            logger.warning(f"Tokmanni get_offers failed: {e}")
            return "", None, []

    async def get_offers(self, product_url: str) -> tuple[str, str | None, list[OfferItem]]:
        """Fetch offers for a product URL from Hinta.fi, Fitnesstukku.fi, Karkkainen.com, or Tokmanni.fi."""
        if "fitnesstukku.fi" in product_url:
            return await self.get_fitnesstukku_offers(product_url)
        elif "karkkainen.com" in product_url:
            return await self.get_karkkainen_offers(product_url)
        elif "tokmanni.fi" in product_url:
            return await self.get_tokmanni_offers(product_url)
            
        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=15.0) as client:
            resp = await client.get(product_url)
            if resp.status_code != 200:
                return "", None, []
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Product title
            title_el = soup.select_one("h1.hv-content-hd-h") or soup.find("h1") or soup.select_one("title")
            title = title_el.get_text(strip=True) if title_el else "Товар"
            title = re.sub(r"\s*-\s*Hinta\s+[\d,\.]+\s*€.*$", "", title, flags=re.IGNORECASE).strip()
            title = re.sub(r"\s*-\s*Hinta\.fi.*$", "", title, flags=re.IGNORECASE).strip()
            
            # Image
            img_el = soup.select_one(".hv-pdi-img img") or soup.select_one("meta[property='og:image']")
            image_url = None
            if img_el:
                src = img_el.get("content") if img_el.name == "meta" else img_el.get("src")
                if src:
                    image_url = f"https://hinta.fi{src}" if src.startswith("/") else src
                    
            offers: list[OfferItem] = []
            offer_rows = soup.select("tr.hv-oft-tr")
            
            for row in offer_rows:
                # Store Name
                store_el = row.select_one(".hv--store .hv-visual-hide") or row.select_one(".hv--store a")
                store_name = store_el.get_text(strip=True) if store_el else "Магазин"
                if not store_name and store_el and store_el.get("title"):
                    store_name = store_el.get("title").replace("Siirry kauppaan: ", "").strip()
                
                # Direct Store Link and Canonical Product Page
                direct_link = get_direct_store_url(store_name, title)
                store_link = direct_link or product_url
                
                # Price extraction
                raw_price = row.get("data-price") or (row.select_one(".hv--price").get_text(strip=True) if row.select_one(".hv--price") else "")
                raw_total = row.get("data-price-total") or ""
                raw_delivery = row.get("data-delivery-fee") or ""
                
                base_price = clean_price(raw_price) or 0.0
                delivery_fee = clean_price(raw_delivery) or 0.0
                total_price = clean_price(raw_total)
                if total_price is None or total_price == 0.0:
                    total_price = round(base_price + delivery_fee, 2)
                    
                # Availability
                avail_el = row.select_one(".hv-aic")
                availability = avail_el.get("title") if avail_el and avail_el.get("title") else "В наличии"
                if "Varastossa" in availability:
                    availability = "В наличии"
                elif "Saatavuus:" in availability:
                    availability = availability.replace("Saatavuus:", "").strip()
                    
                if base_price > 0:
                    offers.append(OfferItem(
                        store_name=store_name,
                        base_price=base_price,
                        delivery_fee=delivery_fee,
                        total_price=total_price,
                        link=store_link,
                        direct_link=direct_link,
                        availability=availability,
                        product_title=title
                    ))
                    
            offers.sort(key=lambda x: x.total_price)
            return title, image_url, offers

scraper = PriceScraper()
