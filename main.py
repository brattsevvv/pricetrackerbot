import asyncio
import logging
import socket
import sys

# Force UTF-8 output on Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import settings
from database import Database
from handlers import router
from scheduler import daily_price_checker_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("price_bot")

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="tracked", description="Мои отслеживаемые товары"),
        BotCommand(command="check_now", description="Проверить цены сейчас"),
        BotCommand(command="location", description="Локация поиска (Финляндия / ЕС)"),
        BotCommand(command="help", description="Инструкция и помощь"),
    ]
    await bot.set_my_commands(commands)

async def main():
    if not settings.BOT_TOKEN or settings.BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error(
            "\n" + "=" * 60 + "\n"
            "⚠️ ВНИМАНИЕ: BOT_TOKEN не указан в файле .env!\n\n"
            "1. Откройте файл .env\n"
            "2. Вставьте ваш токен от @BotFather в строку BOT_TOKEN=...\n"
            "3. Запустите main.py снова!\n" + "=" * 60
        )
        return

    logger.info("Инициализация базы данных...")
    db = Database(settings.DB_URL)
    await db.init_models()

    # Configure robust session (IPv4 forced on Windows, optional proxy)
    session = AiohttpSession(proxy=settings.TELEGRAM_PROXY or None)
    if not settings.TELEGRAM_PROXY:
        session._connector_init["family"] = socket.AF_INET
    if settings.TELEGRAM_PROXY:
        logger.info(f"Используется прокси для Telegram: {settings.TELEGRAM_PROXY}")

    bot = Bot(
        token=settings.BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    bot.db = db

    dp = Dispatcher()
    dp["db"] = db
    dp.include_router(router)

    # APScheduler for daily checks
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        daily_price_checker_job,
        trigger="cron",
        hour=settings.CHECK_HOUR_UTC,
        minute=0,
        args=[bot, db],
        name="daily_price_check"
    )
    scheduler.start()
    logger.info(f"Планировщик запущен: проверка раз в день в {settings.CHECK_HOUR_UTC:02d}:00 UTC")

    try:
        await set_bot_commands(bot)
    except Exception as e:
        logger.warning(f"Не удалось обновить меню команд (некритично): {e}")

    logger.info("Бот успешно запущен и готов к поиску цен!")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(
            f"\n" + "=" * 60 + "\n"
            f"❌ Ошибка подключения к Telegram: {e}\n\n"
            f"Если провайдер или сеть блокирует api.telegram.org:\n"
            f"1. Включите VPN (любой европейский регион)\n"
            f"2. Либо укажите прокси в файле .env (например: TELEGRAM_PROXY=http://127.0.0.1:10809)\n"
            f"=" * 60
        )
        raise
    finally:
        scheduler.shutdown()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
