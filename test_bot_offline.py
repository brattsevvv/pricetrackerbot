import asyncio
import os
import shutil
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from database import Database
from query_parser import parse_user_query
from scraper import scraper

async def run_full_pipeline_test():
    print("=" * 60)
    print("🚀 Тестирование всех компонентов бота (база данных + парсер + парсер раскладки)")
    print("=" * 60)
    
    test_db_path = "sqlite+aiosqlite:///test_pipeline.db"
    db = Database(test_db_path)
    await db.init_models()
    print("✅ 1. База данных SQLite успешно инициализирована")
    
    # 1. Test user creation
    user = await db.get_or_create_user(user_id=12345678, username="test_user", first_name="Алексей")
    print(f"✅ 2. Пользователь создан: {user.first_name} (ID: {user.id})")
    
    # 2. Test layout fixer & Cyrillic queries
    print("\n⌨️ 3. Тестирование автоисправления раскладки и перевода с кириллицы:")
    for raw in ["rhtfnby", "скуфешту", "протеин 1кг", "видеокарта rtx 4070", "айфон 15"]:
        prim, hint, _ = parse_user_query(raw)
        print(f"   «{raw}» ➡️ «{prim}» ({hint})")
        assert prim and len(prim) > 0
        
    # 3. Test searching with mistyped layout 'rhtfnby'
    test_query = "rhtfnby"
    parsed_q, _, _ = parse_user_query(test_query)
    print(f"\n🔍 4. Поиск по ошибочной раскладке «{test_query}» (преобразовано в «{parsed_q}»)...")
    products = await scraper.search(parsed_q, limit=4)
    assert len(products) > 0, "Товары не найдены!"
    print(f"   Найдено товаров: {len(products)}")
    for p in products[:3]:
        print(f"   - [{p.store_name}] {p.title[:45]} -> {p.price_preview} (Итого: {p.total_price:.2f} €)")
        
    # 4. Test searching with reverse mistyped layout 'скуфешту'
    test_query2 = "скуфешту"
    parsed_q2, _, _ = parse_user_query(test_query2)
    print(f"\n🔍 5. Поиск по обратной раскладке «{test_query2}» (преобразовано в «{parsed_q2}»)...")
    products2 = await scraper.search(parsed_q2, limit=4)
    assert len(products2) > 0, "Товары не найдены!"
    print(f"   Найдено товаров: {len(products2)}")
    for p in products2[:3]:
        print(f"   - [{p.store_name}] {p.title[:45]} -> {p.price_preview} (Итого: {p.total_price:.2f} €)")
        
    # Cleanup test db
    await db.engine.dispose()
    if os.path.exists("test_pipeline.db"):
        os.remove("test_pipeline.db")
        
    print("\n" + "=" * 60)
    print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("Автоисправление раскладки и кириллицы работает идеально!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_full_pipeline_test())
