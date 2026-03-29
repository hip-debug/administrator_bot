import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        """Подключение к базе данных"""
        try:
            self.pool = await asyncpg.create_pool(
                host=os.getenv("DB_HOST"),
                port=int(os.getenv("DB_PORT")),
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                min_size=5,
                max_size=10
            )
            print("✅ Database connection established")
            
            # Создаем таблицу если не существует
            await self.init_db()
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False

    async def init_db(self):
        """Создание таблицы User_data"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS User_data (
                    user_id BIGINT PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    username TEXT,
                    level INTEGER DEFAULT 1,
                    experience INTEGER DEFAULT 0,
                    messages_count INTEGER DEFAULT 0,
                    voice_minutes INTEGER DEFAULT 0,
                    money DECIMAL(15, 2) DEFAULT 0.00,
                    last_message_time TIMESTAMP DEFAULT NOW(),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            print("✅ Table User_data checked/created")

    async def get_user(self, user_id: int, guild_id: int, username: str = None):
        """Получить или создать пользователя"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM User_data WHERE user_id = $1 AND guild_id = $2",
                user_id, guild_id
            )
            
            if not row:
                await conn.execute(
                    """INSERT INTO User_data (user_id, guild_id, username) 
                       VALUES ($1, $2, $3)""",
                    user_id, guild_id, username
                )
                row = await conn.fetchrow(
                    "SELECT * FROM User_data WHERE user_id = $1 AND guild_id = $2",
                    user_id, guild_id
                )
            return dict(row) if row else None

    async def update_user(self, user_id: int, guild_id: int, **kwargs):
        """Обновить данные пользователя"""
        async with self.pool.acquire() as conn:
            set_clause = ", ".join([f"{k} = ${i+3}" for i, k in enumerate(kwargs.keys())])
            values = list(kwargs.values())
            
            query = f"""
                UPDATE User_data 
                SET {set_clause} 
                WHERE user_id = $1 AND guild_id = $2
                RETURNING *
            """
            
            row = await conn.fetchrow(query, user_id, guild_id, *values)
            return dict(row) if row else None

    async def add_experience(self, user_id: int, guild_id: int, exp_amount: int):
        """Добавить опыт пользователю"""
        async with self.pool.acquire() as conn:
            # Получаем текущие данные
            row = await conn.fetchrow(
                "SELECT level, experience FROM User_data WHERE user_id = $1 AND guild_id = $2",
                user_id, guild_id
            )
            
            if not row:
                return None, False
            
            current_exp = row['experience']
            current_level = row['level']
            new_exp = current_exp + exp_amount
            
            # Формула уровня: уровень = корень из (опыт / 100)
            new_level = int((new_exp / 100) ** 0.5) + 1
            
            leveled_up = new_level > current_level
            
            await conn.execute(
                """UPDATE User_data 
                   SET experience = $1, level = $2 
                   WHERE user_id = $3 AND guild_id = $4""",
                new_exp, new_level, user_id, guild_id
            )
            
            return {"level": new_level, "experience": new_exp}, leveled_up

    async def get_leaderboard(self, guild_id: int, limit: int = 10):
        """Получить топ пользователей"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT user_id, username, level, experience, messages_count, voice_minutes, money
                   FROM User_data 
                   WHERE guild_id = $1 
                   ORDER BY experience DESC 
                   LIMIT $2""",
                guild_id, limit
            )
            return [dict(row) for row in rows]

    async def add_money(self, user_id: int, guild_id: int, amount: float):
        """Добавить деньги пользователю"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE User_data 
                   SET money = money + $1 
                   WHERE user_id = $2 AND guild_id = $3""",
                amount, user_id, guild_id
            )

    async def close(self):
        """Закрытие подключения"""
        if self.pool:
            await self.pool.close()
