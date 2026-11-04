import urllib.parse
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

def resolve_store_search_term(search_query: str) -> str:
    """Resolve an optimal search keyword for Finnish stores (Prisma, Tokmanni)."""
    q = search_query.lower()
    if "soija" in q or "soy" in q:
        return "soijaproteiini"
    elif any(w in q for w in ["whey", "protein", "proteiini"]):
        if any(w in q for w in ["patukka", "bar", "батончик"]):
            return "proteiinipatukka"
        elif any(w in q for w in ["pannukakku", "pancake", "блин"]):
            return "proteiinipannukakkujauhe"
        else:
            return "proteiinijauhe"
    elif any(w in q for w in ["kreatiini", "creatine"]):
        if "mono" in q:
            return "kreatiinimonohydraatti"
        return "kreatiini"
    elif any(w in q for w in ["kahvikone", "kahvinkeitin", "espressokeitin", "kapselikahvikone", "moccamaster"]):
        return search_query
    elif any(w in q for w in ["gainer", "гейнер"]):
        return "mass gainer"
    elif any(w in q for w in ["kollageeni", "collagen", "коллаген"]):
        return "kollageeni"
    elif any(w in q for w in ["bcaa", "всаа", "бцаа"]):
        return "bcaa"
    return search_query

def get_product_card_kb(
    product_idx: str,
    best_store_name: str,
    best_store_link: str,
    hinta_url: str,
    has_more_offers: bool = True,
    search_query: str | None = None
) -> InlineKeyboardMarkup:
    """Keyboard under a search result card."""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"🛒 Купить в {best_store_name}",
                url=best_store_link
            )
        ]
    ]
    
    # Fast store comparison buttons (Prisma & Tokmanni)
    if search_query:
        skaupat_term = resolve_store_search_term(search_query)
        encoded_skaupat = urllib.parse.quote_plus(skaupat_term)
        buttons.append([
            InlineKeyboardButton(
                text="🛒 Prisma (S-Kaupat)",
                url=f"https://www.s-kaupat.fi/hakutulokset?queryString={encoded_skaupat}"
            ),
            InlineKeyboardButton(
                text="🛒 Tokmanni",
                url=f"https://www.tokmanni.fi/search?q={encoded_skaupat}"
            )
        ])
        
    if hinta_url and "hinta.fi" in hinta_url:
        buttons.append([
            InlineKeyboardButton(
                text="📊 Сравнение на Hinta.fi",
                url=hinta_url
            )
        ])
        
    buttons.append([
        InlineKeyboardButton(
            text="🔔 Отслеживать лучшую цену",
            callback_data=f"track:{product_idx}"
        )
    ])
    
    if has_more_offers:
        buttons.append([
            InlineKeyboardButton(
                text="📋 Список всех вариантов в боте",
                callback_data=f"offers:{product_idx}"
            )
        ])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_offers_list_kb(product_idx: str, offers_data: list, hinta_url: str, search_query: str | None = None) -> InlineKeyboardMarkup:
    """Keyboard showing top offers with direct purchase links."""
    buttons = []
    for offer in offers_data[:6]:
        deliv = f"+{offer.delivery_fee:.2f}€" if offer.delivery_fee > 0 else "беспл."
        prod_suffix = f" - {offer.product_title[:20]}..." if offer.product_title and offer.product_title != offer.store_name else ""
        text = f"{offer.store_name}{prod_suffix}: {offer.total_price:.2f}€ ({deliv})"
        buttons.append([InlineKeyboardButton(text=text, url=offer.link)])
    
    if search_query:
        skaupat_term = resolve_store_search_term(search_query)
        encoded_skaupat = urllib.parse.quote_plus(skaupat_term)
        buttons.append([
            InlineKeyboardButton(
                text="🛒 Prisma (S-Kaupat)",
                url=f"https://www.s-kaupat.fi/hakutulokset?queryString={encoded_skaupat}"
            ),
            InlineKeyboardButton(
                text="🛒 Tokmanni",
                url=f"https://www.tokmanni.fi/search?q={encoded_skaupat}"
            )
        ])
        
    if hinta_url and "hinta.fi" in hinta_url:
        buttons.append([
            InlineKeyboardButton(text="📊 Сравнение на Hinta.fi", url=hinta_url)
        ])
        
    buttons.append([
        InlineKeyboardButton(
            text="🔔 Отслеживать лучшую цену",
            callback_data=f"track:{product_idx}"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_tracked_item_kb(product_id: int, store_link: str) -> InlineKeyboardMarkup:
    """Keyboard under a tracked item in /tracked list."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛒 В магазин", url=store_link),
                InlineKeyboardButton(text="❌ Удалить", callback_data=f"untrack:{product_id}")
            ]
        ]
    )

def get_main_menu_kb() -> ReplyKeyboardMarkup:
    """Persistent bottom reply keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 Мои товары"),
                KeyboardButton(text="🔄 Проверить цены сейчас")
            ],
            [
                KeyboardButton(text="ℹ️ Помощь"),
                KeyboardButton(text="📍 Моя локация")
            ]
        ],
        resize_keyboard=True
    )
