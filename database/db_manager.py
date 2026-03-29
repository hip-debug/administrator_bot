"""Database configuration and connection management."""

import asyncpg
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Database:
    """Manages PostgreSQL database connections and operations."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.host = os.getenv("DB_HOST")
        self.port = os.getenv("DB_PORT")
        self.database = os.getenv("DB_NAME")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
    
    async def connect(self) -> None:
        """Create a connection pool to the database."""
        if not all([self.host, self.port, self.database, self.user, self.password]):
            raise ValueError("Missing database configuration in .env file")
        
        connection_string = (
            f"postgresql://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )
        self.pool = await asyncpg.create_pool(connection_string)
        print("✅ Database connection established")
        await self.initialize_tables()
    
    async def disconnect(self) -> None:
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            print("🔌 Database connection closed")
    
    async def initialize_tables(self) -> None:
        """Create necessary tables if they don't exist."""
        async with self.pool.acquire() as conn:
            # Main user data table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS User_data (
                    user_id BIGINT NOT NULL,
                    guild_id BIGINT NOT NULL,
                    username TEXT,
                    level INTEGER DEFAULT 1,
                    experience INTEGER DEFAULT 0,
                    dollar REAL DEFAULT 0,
                    messages_count INTEGER DEFAULT 0,
                    voice_minutes INTEGER DEFAULT 0,
                    last_message_time TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (user_id, guild_id)
                )
            """)
            
            print("✅ Table User_data checked/created")
    
    async def get_user(self, user_id: int, guild_id: int, username: str = None) -> Optional[dict]:
        """Get user data from the database."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM User_data WHERE user_id = $1 AND guild_id = $2",
                user_id, guild_id
            )
            
            if not row and username:
                # Create user if doesn't exist
                await conn.execute(
                    """
                    INSERT INTO User_data (user_id, guild_id, username, level, experience, dollar, messages_count, voice_minutes)
                    VALUES ($1, $2, $3, 1, 0, 0, 0, 0)
                    ON CONFLICT (user_id, guild_id) DO NOTHING
                    """,
                    user_id, guild_id, username
                )
                row = await conn.fetchrow(
                    "SELECT * FROM User_data WHERE user_id = $1 AND guild_id = $2",
                    user_id, guild_id
                )
            
            return dict(row) if row else None
    
    async def update_user(self, user_id: int, guild_id: int, **kwargs) -> Optional[dict]:
        """Update user data and return updated record."""
        async with self.pool.acquire() as conn:
            sets = []
            values = []
            for i, (key, value) in enumerate(kwargs.items(), 1):
                sets.append(f"{key} = ${i+2}")
                values.append(value)
            
            if not sets:
                return await self.get_user(user_id, guild_id)
            
            query = f"""
                UPDATE User_data 
                SET {', '.join(sets)}
                WHERE user_id = $1 AND guild_id = $2
                RETURNING *
            """
            row = await conn.fetchrow(query, user_id, guild_id, *values)
            return dict(row) if row else None
    
    async def add_experience(self, user_id: int, guild_id: int, amount: int, username: str = None) -> Optional[dict]:
        """Add XP to user and return updated data."""
        async with self.pool.acquire() as conn:
            # Ensure user exists
            await conn.execute(
                """
                INSERT INTO User_data (user_id, guild_id, username, level, experience, dollar, messages_count, voice_minutes)
                VALUES ($1, $2, $3, 1, 0, 0, 0, 0)
                ON CONFLICT (user_id, guild_id) DO NOTHING
                """,
                user_id, guild_id, username
            )
            
            # Update XP and messages count
            row = await conn.fetchrow(
                """
                UPDATE User_data 
                SET experience = experience + $3, messages_count = messages_count + 1
                WHERE user_id = $1 AND guild_id = $2
                RETURNING *
                """,
                user_id, guild_id, amount
            )
            return dict(row) if row else None
    
    async def get_leaderboard(self, guild_id: int, limit: int = 10) -> list:
        """Get top users by experience for the leaderboard."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_id, username, level, experience, dollar, messages_count, voice_minutes
                FROM User_data
                WHERE guild_id = $1
                ORDER BY experience DESC
                LIMIT $2
                """,
                guild_id, limit
            )
            return [dict(row) for row in rows]


# Global database instance
db = Database()
