import asyncio
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import Database
from scraper import scraper

logger = logging.getLogger(__name__)

async def check_single_product(bot: Bot, db: Database, item) -> bool:
    """Check a single product for price drop. Returns True if price dropped."""
    try:
        title, img, offers = await scraper.get_offers(item.product_url)
        if not offers:
            return False
        
        best_offer = offers[0]
        old_price = item.best_price
        new_price = best_offer.total_price
        
        # Check if price dropped by at least 0.05 € (to filter minor rounding)
        if new_price < old_price - 0.05:
            savings = old_price - new_price
            delivery_text = (
                f"+ {best_offer.delivery_fee:.2f} € доставка" 
                if best_offer.delivery_fee > 0 
                else "бесплатная доставка"
            )
            
            text = (
                f"🎉 <b>Цена снизилась!</b>\n\n"
                f"📦 <b>{item.product_name}</b>\n\n"
                f"Старая цена: <s>{old_price:.2f} €</s>\n"
                f"🔥 <b>Новая цена: {new_price:.2f} €</b> (скидка {savings:.2f} €!)\n"
                f"🏪 Магазин: <b>{best_offer.store_name}</b> ({delivery_text})\n"
                f"Статус: {best_offer.availability}"
            )
            
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=f"🛒 Купить в {best_offer.store_name}", url=best_offer.link)],
                    [InlineKeyboardButton(text="❌ Перестать отслеживать", callback_data=f"untrack:{item.id}")]
                ]
            )
            
            try:
                await bot.send_message(chat_id=item.user_id, text=text, parse_mode="HTML", reply_markup=kb)
            except Exception as e:
                logger.error(f"Failed to send alert to user {item.user_id}: {e}")
                
            await db.update_product_price(
                product_id=item.id,
                new_price=new_price,
                base_price=best_offer.base_price,
                delivery_fee=best_offer.delivery_fee,
                store_name=best_offer.store_name,
                store_link=best_offer.link
            )
            return True
        else:
            # Just update last checked time
            await db.update_product_price(
                product_id=item.id,
                new_price=old_price,
                base_price=item.base_price,
                delivery_fee=item.delivery_fee,
                store_name=item.store_name,
                store_link=item.store_link
            )
            return False
    except Exception as e:
        logger.error(f"Error checking product {item.id} ({item.product_url}): {e}")
        return False

async def daily_price_checker_job(bot: Bot, db: Database):
    """Background daily job to check all tracked products."""
    logger.info("Starting daily price check job...")
    products = await db.get_all_tracked_products()
    logger.info(f"Checking {len(products)} tracked products...")
    
    dropped_count = 0
    for product in products:
        dropped = await check_single_product(bot, db, product)
        if dropped:
            dropped_count += 1
        # Sleep 2 seconds between scraping requests to be gentle to servers
        await asyncio.sleep(2)
        
    logger.info(f"Daily price check finished. Price drops found: {dropped_count}")
