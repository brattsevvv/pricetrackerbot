from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    BOT_TOKEN: str = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
    DB_URL: str = f"sqlite+aiosqlite:///{BASE_DIR / 'bot.db'}"
    CHECK_HOUR_UTC: int = 7  # 07:00 UTC = 09:00 or 10:00 local time
    TELEGRAM_PROXY: str | None = None  # e.g. "socks5://127.0.0.1:10808" or "http://127.0.0.1:10809"
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
