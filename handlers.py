import html
import logging
from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from database import Database
from keyboards import get_main_menu_kb, get_offers_list_kb, get_product_card_kb, get_tracked_item_kb
from query_parser import parse_user_query
from scheduler import check_single_product
from scraper import OfferItem, ProductItem, scraper

logger = logging.getLogger(__name__)

router = Router()

# In-memory session cache for recent search results (maps session_id -> data)
SEARCH_CACHE: dict[str, dict] = {}

def get_db(bot: Bot) -> Database:
    if hasattr(bot, "db"):
        return bot.db
    if isinstance(bot, dict) and "db" in bot:
        return bot["db"]
    raise RuntimeError("Database instance not found in Bot context")

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    db = get_db(bot)
    user = message.from_user
    await db.get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    welcome_text = (
        f"👋 <b>Привет, {html.escape(user.first_name or 'друг')}!</b>\n\n"
        f"Я бот для поиска <b>самых выгодных цен</b> на любые товары и спортпит в Финляндии.\n\n"
        f"🇫🇮 <b>Магазины в поиске:</b>\n"
        f"• <b>Спорт, здоровье и добавки</b>: Fitnesstukku.fi, Kärkkäinen, Prisma (S-Kaupat), Tokmanni, Verkkokauppa.\n"
        f"• <b>Электроника и товары для дома</b>: Verkkokauppa, Gigantti, Power, DNA, Elisa, Proshop, Kärkkäinen и др.\n\n"
        f"💡 <b>Как я работаю:</b>\n"
        f"• Сравниваю цены <b>вместе со стоимостью доставки</b> по Финляндии.\n"
        f"• Нажав <b>«🔔 Отслеживать лучшую цену»</b>, вы получаете ежедневный мониторинг скидок.\n\n"
        f"🔍 <i>Напишите название любого товара прямо сейчас (например: <code>kreatiini</code>, <code>whey 80</code>, <code>iPhone 15</code>).</i>"
    )
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=get_main_menu_kb())

@router.message(F.text == "ℹ️ Помощь")
@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📖 <b>Инструкция по использованию бота:</b>\n\n"
        "1️⃣ <b>Поиск товара:</b>\n"
        "Просто напишите в чат название товара, спортпита или модели:\n"
        "• <code>kreatiini</code> или <code>creatine 500g</code>\n"
        "• <code>whey 80</code> или <code>proteiinijauhe</code>\n"
        "• <code>AirPods Pro 2</code> или <code>PlayStation 5</code>\n\n"
        "2️⃣ <b>Сравнение цен между магазинами:</b>\n"
        "Бот ищет одновременно в <b>Kärkkäinen</b>, <b>Fitnesstukku</b>, <b>Hinta.fi (Verkkokauppa, Gigantti и др.)</b> "
        "и добавляет кнопки для моментального сравнения с <b>Prisma (S-Kaupat)</b> и <b>Tokmanni</b>.\n\n"
        "3️⃣ <b>Учет доставки:</b>\n"
        "Бот сразу суммирует цену товара и доставку, чтобы показать честную финальную стоимость.\n\n"
        "4️⃣ <b>Ежедневный мониторинг:</b>\n"
        "Нажмите <b>«🔔 Отслеживать лучшую цену»</b>. Раз в день бот проверяет все магазины и присылает уведомление при скидке."
    )
    await message.answer(help_text, parse_mode="HTML")

@router.message(F.text == "📍 Моя локация")
@router.message(Command("location"))
async def cmd_location(message: Message):
    text = (
        "📍 <b>Текущая локация поиска: 🇫🇮 Финляндия / ЕС</b>\n\n"
        "Бот проверяет предложения с доставкой по Финляндии:\n"
        "• <b>Спортивное питание и здоровье</b>: Fitnesstukku.fi, Kärkkäinen, Prisma (S-Kaupat), Tokmanni\n"
        "• <b>Финские гипермаркеты и сети</b>: Verkkokauppa.com, Gigantti, Power, DNA, Elisa, Telia, Veikon Kone\n"
        "• <b>Скандинавские ритейлеры</b>: Proshop, MaxGaming, Datatronic\n\n"
        "Все цены рассчитываются с учетом доставки."
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "📋 Мои товары")
@router.message(Command("tracked"))
async def cmd_tracked(message: Message, bot: Bot):
    db = get_db(bot)
    items = await db.get_user_tracked_products(message.from_user.id)
    
    if not items:
        await message.answer(
            "📋 <b>Ваш список отслеживания пуст.</b>\n\n"
            "Чтобы добавить товар, просто напишите его название в чат и нажмите кнопку «🔔 Отслеживать цену».",
            parse_mode="HTML"
        )
        return

    await message.answer(f"📋 <b>Отслеживаемые товары ({len(items)}):</b>", parse_mode="HTML")
    
    for item in items:
        deliv_str = f"+ {item.delivery_fee:.2f} € доставка" if item.delivery_fee and item.delivery_fee > 0 else "бесплатная доставка"
        text = (
            f"📦 <b>{html.escape(item.product_name)}</b>\n"
            f"💰 Лучшая цена: <b>{item.best_price:.2f} €</b> ({deliv_str})\n"
            f"🏪 Магазин: <b>{html.escape(item.store_name)}</b>\n"
            f"🕒 Проверено: {item.last_checked.strftime('%d.%m.%Y %H:%M') if item.last_checked else 'Недавно'}"
        )
        kb = get_tracked_item_kb(item.id, item.store_link)
        await message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.message(F.text == "🔄 Проверить цены сейчас")
@router.message(Command("check_now"))
async def cmd_check_now(message: Message, bot: Bot):
    db = get_db(bot)
    items = await db.get_user_tracked_products(message.from_user.id)
    
    if not items:
        await message.answer("У вас нет отслеживаемых товаров. Добавьте товары через поиск!", parse_mode="HTML")
        return
        
    status_msg = await message.answer(f"🔄 Проверяю цены на ваши {len(items)} тов.... Пожалуйста, подождите.")
    
    price_drops = 0
    for item in items:
        dropped = await check_single_product(bot, db, item)
        if dropped:
            price_drops += 1
            
    if price_drops == 0:
        await status_msg.edit_text(
            f"✅ <b>Проверка завершена!</b>\n\n"
            f"Проверено товаров: <b>{len(items)}</b>\n"
            f"Все цены актуальны, снижений пока не найдено. Я продолжаю следить каждый день!",
            parse_mode="HTML"
        )
    else:
        await status_msg.edit_text(
            f"🎉 <b>Проверка завершена!</b> Найдено снижений цен: <b>{price_drops}</b> (детали отправлены выше).",
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("untrack:"))
async def cb_untrack(callback: CallbackQuery, bot: Bot):
    db = get_db(bot)
    product_id = int(callback.data.split(":")[1])
    success = await db.delete_tracked_product(product_id, callback.from_user.id)
    
    if success:
        await callback.answer("✅ Товар удален из отслеживания", show_alert=False)
        try:
            await callback.message.edit_text("❌ <i>Товар удален из списка отслеживания.</i>", parse_mode="HTML")
        except Exception:
            pass
    else:
        await callback.answer("Товар не найден или уже удален", show_alert=True)

@router.callback_query(F.data.startswith("track:"))
async def cb_track(callback: CallbackQuery, bot: Bot):
    db = get_db(bot)
    cache_key = callback.data.split(":", 1)[1]
    cached = SEARCH_CACHE.get(cache_key)
    
    if not cached:
        await callback.answer("Данные поиска устарели. Пожалуйста, выполните поиск заново.", show_alert=True)
        return
        
    best_offer: OfferItem = cached["best_offer"]
    product_title: str = cached["title"]
    product_url: str = cached["product_url"]
    
    await db.add_tracked_product(
        user_id=callback.from_user.id,
        product_name=product_title,
        product_url=product_url,
        best_price=best_offer.total_price,
        base_price=best_offer.base_price,
        delivery_fee=best_offer.delivery_fee,
        store_name=best_offer.store_name,
        store_link=best_offer.link
    )
    
    await callback.answer("🔔 Товар добавлен в список отслеживания!", show_alert=True)
    try:
        await callback.message.reply(
            f"✅ <b>Товар добавлен в отслеживание!</b>\n\n"
            f"📦 <b>{html.escape(product_title)}</b>\n"
            f"Текущая лучшая цена: <b>{best_offer.total_price:.2f} €</b> ({best_offer.store_name})\n\n"
            f"Я буду проверять цену раз в день и сразу пришлю уведомление при появлении более выгодного предложения.",
            parse_mode="HTML"
        )
    except Exception:
        pass

@router.callback_query(F.data.startswith("offers:"))
async def cb_all_offers(callback: CallbackQuery):
    cache_key = callback.data.split(":", 1)[1]
    cached = SEARCH_CACHE.get(cache_key)
    
    if not cached:
        await callback.answer("Данные поиска устарели. Повторите поиск.", show_alert=True)
        return
        
    offers: list[OfferItem] = cached["offers"]
    kb = get_offers_list_kb(cache_key, offers, cached["product_url"], search_query=cached.get("query"))
    await callback.message.reply(
        f"📋 <b>Все найденные варианты и предложения:</b>\n"
        f"<i>{html.escape(cached['title'])}</i>\n\n"
        f"Нажмите на кнопку с ценой для прямого перехода в магазин:",
        parse_mode="HTML",
        reply_markup=kb
    )
    await callback.answer()

@router.message(F.text)
async def handle_search_query(message: Message, bot: Bot):
    raw_query = message.text.strip()
    if len(raw_query) < 2:
        await message.answer("Пожалуйста, введите более точное название товара.")
        return
        
    # Smart query parsing: handles wrong layout (rhtfnby -> kreatiini, скуфешту -> creatine) & Cyrillic translation
    search_query, hint_text, fallback_queries = parse_user_query(raw_query)
    
    status_text = f"🔍 Ищу предложения для «<b>{html.escape(search_query)}</b>»..."
    if hint_text:
        status_text = f"💡 <i>{hint_text}</i>\n{status_text}"
        
    status_msg = await message.answer(status_text, parse_mode="HTML")
    
    try:
        products = await scraper.search(search_query, limit=6)
        # If no products found and we have fallback queries, try them
        if not products and fallback_queries:
            for alt_q in fallback_queries:
                alt_products = await scraper.search(alt_q, limit=6)
                if alt_products:
                    products = alt_products
                    search_query = alt_q
                    break
                    
        if not products:
            await status_msg.edit_text(
                f"😔 По запросу «<b>{html.escape(search_query)}</b>» ничего не найдено.\n\n"
                f"💡 Попробуйте ввести точное название модели на английском или финском.\n"
                f"Также вы можете проверить наличие напрямую в Prisma или Tokmanni:",
                parse_mode="HTML",
                reply_markup=get_offers_list_kb("empty", [], "", search_query=search_query)
            )
            return
            
        target_product = products[0]
        title, image_url, offers = await scraper.get_offers(target_product.url)
        
        # If target product didn't return offers, construct one from product preview
        if not offers and target_product.total_price > 0:
            offers = [OfferItem(
                store_name=target_product.store_name or "Магазин",
                base_price=target_product.base_price,
                delivery_fee=target_product.delivery_fee,
                total_price=target_product.total_price,
                link=target_product.url,
                direct_link=target_product.url,
                availability="В наличии",
                product_title=target_product.title
            )]
            
        # Merge alternative products from other stores so user sees full multi-store comparison
        if len(products) > 1:
            existing_urls = {o.link for o in offers}
            for alt_p in products[1:]:
                if alt_p.url not in existing_urls and alt_p.total_price > 0:
                    offers.append(OfferItem(
                        store_name=alt_p.store_name or "Магазин",
                        base_price=alt_p.base_price,
                        delivery_fee=alt_p.delivery_fee,
                        total_price=alt_p.total_price,
                        link=alt_p.url,
                        direct_link=alt_p.url,
                        availability="В наличии",
                        product_title=alt_p.title
                    ))
                    existing_urls.add(alt_p.url)
                    
        offers.sort(key=lambda x: x.total_price)
        
        if not offers:
            await status_msg.edit_text(
                f"Найдено: <b>{html.escape(target_product.title)}</b>, но сейчас нет активных предложений с ценами в наличии.",
                parse_mode="HTML"
            )
            return
            
        best_offer = offers[0]
        
        # Save to search cache
        cache_id = str(abs(hash(target_product.url)))
        SEARCH_CACHE[cache_id] = {
            "title": title or target_product.title,
            "product_url": target_product.url,
            "best_offer": best_offer,
            "offers": offers,
            "query": search_query
        }
        
        # Format response
        deliv_text = (
            f"+ {best_offer.delivery_fee:.2f} € доставка" 
            if best_offer.delivery_fee > 0 
            else "бесплатная доставка"
        )
        
        display_title = best_offer.product_title or title or target_product.title
        header_hint = f"💡 <i>{hint_text}</i>\n\n" if hint_text else ""
        
        msg_text = (
            f"{header_hint}"
            f"📦 <b>{html.escape(display_title)}</b>\n\n"
            f"🥇 <b>Лучшая цена с доставкой:</b>\n"
            f"🔥 <b>{best_offer.total_price:.2f} €</b> ({best_offer.base_price:.2f} € {deliv_text})\n"
            f"🏪 Магазин: <b>{html.escape(best_offer.store_name)}</b>\n"
            f"📦 Статус: <i>{html.escape(best_offer.availability)}</i>\n\n"
        )
        
        # Show other stores / variants found
        if len(offers) > 1:
            msg_text += "<b>Другие магазины и варианты:</b>\n"
            for alt in offers[1:4]:
                alt_deliv = f"+{alt.delivery_fee:.2f}€" if alt.delivery_fee > 0 else "беспл."
                item_name = f" - <i>{html.escape(alt.product_title[:28])}...</i>" if alt.product_title and alt.product_title != display_title else ""
                msg_text += f"• <b>{html.escape(alt.store_name)}</b>{item_name}: <b>{alt.total_price:.2f} €</b> ({alt_deliv})\n"
            msg_text += "\n"
            
        msg_text += "<i>💡 Быстро проверить цены в Prisma и Tokmanni можно кнопками ниже.</i>"
        
        kb = get_product_card_kb(
            product_idx=cache_id,
            best_store_name=best_offer.store_name,
            best_store_link=best_offer.link,
            hinta_url=target_product.url,
            has_more_offers=len(offers) > 1,
            search_query=search_query
        )
        
        await status_msg.delete()
        
        target_img = image_url or target_product.image_url
        if target_img:
            try:
                await message.answer_photo(
                    photo=target_img,
                    caption=msg_text,
                    parse_mode="HTML",
                    reply_markup=kb
                )
                return
            except Exception as e:
                logger.warning(f"Could not send photo: {e}")
                
        await message.answer(msg_text, parse_mode="HTML", reply_markup=kb)
        
    except Exception as e:
        logger.error(f"Error handling search: {e}", exc_info=True)
        await status_msg.edit_text("⚠️ Произошла ошибка при поиске. Попробуйте еще раз через минуту.")
