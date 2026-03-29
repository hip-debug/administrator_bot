"""Database configuration and connection management."""

import asyncpg
import os
from typing import Optional


class Database:
    """Manages PostgreSQL database connections and operations."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self, database_url: str) -> None:
        """Create a connection pool to the database."""
        self.pool = await asyncpg.create_pool(database_url)
        print("✅ Database connection established")
    
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
                    user_id BIGINT PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    username TEXT NOT NULL,
                    level INTEGER DEFAULT 1,
                    xp INTEGER DEFAULT 0,
                    xp_to_next_level INTEGER DEFAULT 100,
                    messages_count INTEGER DEFAULT 0,
                    voice_minutes INTEGER DEFAULT 0,
                    money INTEGER DEFAULT 0,
                    roles TEXT[] DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Leaderboard cache table for faster queries
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS leaderboard_cache (
                    guild_id BIGINT PRIMARY KEY,
                    top_users JSONB,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Voice sessions tracking
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS voice_sessions (
                    session_id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    guild_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    duration_seconds INTEGER
                )
            """)
            
            print("✅ Database tables initialized")
    
    async def get_user(self, user_id: int, guild_id: int) -> Optional[dict]:
        """Get user data from the database."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM User_data WHERE user_id = $1 AND guild_id = $2",
                user_id, guild_id
            )
            return dict(row) if row else None
    
    async def create_user(self, user_id: int, guild_id: int, username: str) -> None:
        """Create a new user entry in the database."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO User_data (user_id, guild_id, username) 
                   VALUES ($1, $2, $3)
                   ON CONFLICT (user_id) DO UPDATE SET 
                   guild_id = EXCLUDED.guild_id, 
                   username = EXCLUDED.username,
                   updated_at = CURRENT_TIMESTAMP""",
                user_id, guild_id, username
            )
    
    async def update_xp(self, user_id: int, guild_id: int, xp_amount: int) -> dict:
        """Update user XP and return updated user data."""
        async with self.pool.acquire() as conn:
            # Get current user data
            user = await conn.fetchrow(
                "SELECT * FROM User_data WHERE user_id = $1 AND guild_id = $2",
                user_id, guild_id
            )
            
            if not user:
                return None
            
            new_xp = user['xp'] + xp_amount
            new_level = user['level']
            new_xp_to_next = user['xp_to_next_level']
            leveled_up = False
            
            # Level up logic
            while new_xp >= new_xp_to_next:
                new_xp -= new_xp_to_next
                new_level += 1
                new_xp_to_next = int(new_xp_to_next * 1.5)  # XP curve
                leveled_up = True
            
            await conn.execute(
                """UPDATE User_data 
                   SET xp = $1, level = $2, xp_to_next_level = $3, 
                       messages_count = messages_count + 1,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = $4 AND guild_id = $5""",
                new_xp, new_level, new_xp_to_next, user_id, guild_id
            )
            
            result = {
                'level': new_level,
                'xp': new_xp,
                'xp_to_next': new_xp_to_next,
                'leveled_up': leveled_up
            }
            
            return result
    
    async def update_voice_time(self, user_id: int, guild_id: int, minutes: int) -> dict:
        """Update user voice time and return updated data."""
        async with self.pool.acquire() as conn:
            xp_gained = minutes * 2  # 2 XP per minute in voice
            
            await conn.execute(
                """UPDATE User_data 
                   SET voice_minutes = voice_minutes + $1,
                       xp = xp + $2,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = $3 AND guild_id = $4""",
                minutes, xp_gained, user_id, guild_id
            )
            
            user = await conn.fetchrow(
                "SELECT * FROM User_data WHERE user_id = $1 AND guild_id = $2",
                user_id, guild_id
            )
            
            return dict(user) if user else None
    
    async def get_leaderboard(self, guild_id: int, limit: int = 10) -> list:
        """Get top users by level for the leaderboard."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT user_id, username, level, xp, messages_count, voice_minutes
                   FROM User_data 
                   WHERE guild_id = $1 
                   ORDER BY level DESC, xp DESC 
                   LIMIT $2""",
                guild_id, limit
            )
            return [dict(row) for row in rows]
    
    async def add_money(self, user_id: int, guild_id: int, amount: int) -> None:
        """Add money to user's balance."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE User_data 
                   SET money = money + $1, updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = $2 AND guild_id = $3""",
                amount, user_id, guild_id
            )
    
    async def set_money(self, user_id: int, guild_id: int, amount: int) -> None:
        """Set user's money balance."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE User_data 
                   SET money = $1, updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = $2 AND guild_id = $3""",
                amount, user_id, guild_id
            )
    
    async def assign_role(self, user_id: int, guild_id: int, role_id: int) -> None:
        """Assign a role ID to user's record (for tracking, actual Discord role assignment done separately)."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE User_data 
                   SET roles = array_append(COALESCE(roles, '{}'), $1),
                       updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = $2 AND guild_id = $3""",
                str(role_id), user_id, guild_id
            )


# Global database instance
db = Database()
