# test_connection.py
import asyncio
import asyncpg

async def test():
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='12345678',
            database='delivery_db'
        )
        print("✅ Подключение успешно!")
        
        # Проверка версии
        version = await conn.fetchval("SELECT version()")
        print(f"Версия PostgreSQL: {version[:50]}...")
        
        # Проверка таблиц
        tables = await conn.fetch("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        print(f"Таблицы в БД: {[t['tablename'] for t in tables]}")
        
        await conn.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test())