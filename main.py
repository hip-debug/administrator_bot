import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from dotenv import load_dotenv
import sys

# Добавляем путь для импортов
sys.path.append('/workspace')

from database.db_manager import Database

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

class ManagerBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            description="Бот для управления сервером с системой уровней"
        )
        self.db = Database()

    async def setup_hook(self):
        """Инициализация при запуске"""
        # Подключение к базе данных
        db_connected = await self.db.connect()
        if not db_connected:
            print("❌ Критическая ошибка: не удалось подключиться к БД")
            return
        
        # Загрузка модулей (cogs)
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and filename != '__init__.py':
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"✅ Loaded cog: cogs.{filename[:-3]}")
                except Exception as e:
                    print(f"❌ Failed to load cog cogs.{filename[:-3]}: {e}")
        
        # Синхронизация команд
        if self.guilds:
            self.tree.copy_global_to(guild=self.guilds[0])
            synced = await self.tree.sync(guild=self.guilds[0])
            print(f"✅ Synced {len(synced)} slash command(s) for guild: {self.guilds[0].name}")
        else:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} global slash command(s)")

    async def on_ready(self):
        """Бот готов к работе"""
        print(f"\n✅ Logged in as {self.user.name} (ID: {self.user.id})")
        print(f"🔗 Connected to {len(self.guilds)} guild(s)")
        print("\n🎉 Bot is ready! Use / commands in your Discord server.\n")

    async def on_command_error(self, context, error):
        """Обработка ошибок команд"""
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingPermissions):
            await context.send("❌ У вас нет прав для использования этой команды", ephemeral=True)
        else:
            print(f"❌ Command error: {error}")
            await context.send(f"❌ Произошла ошибка: {str(error)}", ephemeral=True)


async def main():
    token = os.getenv("DISCORD_TOKEN")
    
    if not token:
        print("❌ DISCORD_TOKEN not found in .env file!")
        return
    
    bot = ManagerBot()
    
    try:
        await bot.start(token)
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
    finally:
        await bot.db.close()


if __name__ == "__main__":
    asyncio.run(main())
