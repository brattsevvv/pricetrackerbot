import asyncio
import json
import logging
import os
import sys
import webbrowser
from pathlib import Path
from aiohttp import web

# Fix encoding on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)

from config import settings
from database import Database
from query_parser import parse_user_query
from scraper import PriceScraper
from keyboards import resolve_store_search_term
import urllib.parse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("price_tracker_web")

scraper = PriceScraper()
db = Database(settings.DB_URL)
WEB_USER_ID = 1  # Default local user ID for web app

async def handle_search(request: web.Request) -> web.Response:
    query = request.query.get("q", "").strip()
    if not query or len(query) < 2:
        return web.json_response({"error": "Введите запрос для поиска (минимум 2 символа)"}, status=400)
    
    limit = int(request.query.get("limit", 12))
    parsed_query, hint_text, fallback_queries = parse_user_query(query)
    
    logger.info(f"Search request: '{query}' -> parsed: '{parsed_query}'")
    
    try:
        products = await scraper.search(parsed_query, limit=limit)
        if not products and fallback_queries:
            for alt_q in fallback_queries:
                alt_products = await scraper.search(alt_q, limit=limit)
                if alt_products:
                    products = alt_products
                    parsed_query = alt_q
                    break
        
        # Prepare products data
        results = []
        for p in products:
            results.append({
                "title": p.title,
                "url": p.url,
                "price_preview": p.price_preview,
                "store_name": p.store_name,
                "base_price": p.base_price,
                "delivery_fee": p.delivery_fee,
                "total_price": p.total_price,
                "image_url": p.image_url or ""
            })
            
        # External direct store links (Prisma, Tokmanni)
        store_term = resolve_store_search_term(parsed_query)
        encoded_term = urllib.parse.quote_plus(store_term)
        
        external_links = {
            "prisma_url": f"https://www.s-kaupat.fi/hakutulokset?queryString={encoded_term}",
            "tokmanni_url": f"https://www.tokmanni.fi/search?q={encoded_term}",
            "store_term": store_term
        }
        
        return web.json_response({
            "query": query,
            "parsed_query": parsed_query,
            "hint": hint_text,
            "count": len(results),
            "products": results,
            "external_links": external_links
        })
    except Exception as e:
        logger.error(f"Search failed for '{query}': {e}", exc_info=True)
        return web.json_response({"error": f"Ошибка поиска: {str(e)}"}, status=500)

async def handle_get_tracked(request: web.Request) -> web.Response:
    try:
        items = await db.get_user_tracked_products(WEB_USER_ID)
        data = []
        for item in items:
            data.append({
                "id": item.id,
                "product_name": item.product_name,
                "product_url": item.product_url,
                "best_price": item.best_price,
                "base_price": item.base_price,
                "delivery_fee": item.delivery_fee,
                "store_name": item.store_name,
                "store_link": item.store_link,
                "last_checked": item.last_checked.isoformat() if item.last_checked else None,
                "created_at": item.created_at.isoformat() if item.created_at else None
            })
        return web.json_response({"tracked": data})
    except Exception as e:
        logger.error(f"Failed to get tracked products: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def handle_add_tracked(request: web.Request) -> web.Response:
    try:
        body = await request.json()
        await db.get_or_create_user(WEB_USER_ID, "WebUser", "Пользователь ПК")
        
        product = await db.add_tracked_product(
            user_id=WEB_USER_ID,
            product_name=body.get("product_name", "Товар"),
            product_url=body.get("product_url", ""),
            best_price=float(body.get("best_price", 0.0)),
            base_price=float(body.get("base_price", 0.0)) if body.get("base_price") is not None else None,
            delivery_fee=float(body.get("delivery_fee", 0.0)) if body.get("delivery_fee") is not None else None,
            store_name=body.get("store_name", "Магазин"),
            store_link=body.get("store_link", body.get("product_url", ""))
        )
        return web.json_response({"success": True, "id": product.id})
    except Exception as e:
        logger.error(f"Failed to add tracked product: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def handle_delete_tracked(request: web.Request) -> web.Response:
    try:
        item_id = int(request.match_info["id"])
        success = await db.delete_tracked_product(item_id, WEB_USER_ID)
        return web.json_response({"success": success})
    except Exception as e:
        logger.error(f"Failed to delete tracked product: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def handle_check_tracked(request: web.Request) -> web.Response:
    """Re-check live prices for all tracked products."""
    try:
        items = await db.get_user_tracked_products(WEB_USER_ID)
        updated = []
        for item in items:
            title, img, offers = await scraper.get_offers(item.product_url)
            if offers:
                best = offers[0]
                price_dropped = best.total_price < item.best_price
                old_price = item.best_price
                
                await db.update_product_price(
                    product_id=item.id,
                    new_price=best.total_price,
                    base_price=best.base_price,
                    delivery_fee=best.delivery_fee,
                    store_name=best.store_name,
                    store_link=best.link
                )
                updated.append({
                    "id": item.id,
                    "product_name": item.product_name,
                    "old_price": old_price,
                    "new_price": best.total_price,
                    "price_dropped": price_dropped,
                    "store_name": best.store_name
                })
        return web.json_response({"success": True, "updated": updated})
    except Exception as e:
        logger.error(f"Failed to check tracked products: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def handle_index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(STATIC_DIR / "index.html")

def create_app() -> web.Application:
    app = web.Application()
    
    # API endpoints
    app.router.add_get("/api/search", handle_search)
    app.router.add_get("/api/tracked", handle_get_tracked)
    app.router.add_post("/api/track", handle_add_tracked)
    app.router.add_delete("/api/track/{id}", handle_delete_tracked)
    app.router.add_post("/api/check_tracked", handle_check_tracked)
    
    # Serve index and static assets
    app.router.add_get("/", handle_index)
    app.router.add_static("/static/", path=str(STATIC_DIR), name="static")
    
    # Special routes for PWA
    app.router.add_get("/manifest.json", lambda r: web.FileResponse(STATIC_DIR / "manifest.json"))
    app.router.add_get("/sw.js", lambda r: web.FileResponse(STATIC_DIR / "sw.js"))
    
    return app

def get_local_ip() -> str:
    """Find local network IP address to display QR/URL for phone access."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

async def start_server():
    await db.init_models()
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    local_ip = get_local_ip()
    print("=" * 65)
    print("🚀 ПРИЛОЖЕНИЕ УСПЕШНО ЗАПУЩЕНО!")
    print(f"💻 На компьютере в браузере:  http://localhost:{port}")
    print(f"📱 На телефоне (в сети Wi-Fi): http://{local_ip}:{port}")
    print("=" * 65)
    print("Нажмите Ctrl+C для остановки сервера.")
    
    # Auto-open browser on PC
    if not os.environ.get("NO_BROWSER"):
        try:
            webbrowser.open(f"http://localhost:{port}")
        except Exception:
            pass

    # Keep running forever
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except (KeyboardInterrupt, SystemExit):
        print("\nСервер остановлен.")
