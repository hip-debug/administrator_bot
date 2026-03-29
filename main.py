"""Main entry point for the Discord bot."""

import os
import asyncio
from dotenv import load_dotenv

import discord
from discord.ext import commands

from database import db


# Load environment variables
load_dotenv()

# Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

if not DISCORD_TOKEN:
    raise ValueError("No Discord token found! Please set DISCORD_TOKEN in your .env file")

if not DATABASE_URL:
    raise ValueError("No database URL found! Please set DATABASE_URL in your .env file")


# Bot setup with all necessary intents
intents = discord.Intents.default()
intents.message_content = True  # Required for message-based XP tracking
intents.members = True  # Required for member events
intents.voice_states = True  # Required for voice channel tracking

bot = commands.Bot(
    command_prefix="!",  # Prefix for traditional commands (slash commands don't use this)
    intents=intents,
    help_command=None  # We'll create a custom help command later if needed
)


@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord."""
    print(f"✅ Logged in as {bot.user.name} (ID: {bot.user.id})")
    print(f"🔗 Connected to {len(bot.guilds)} guild(s)")
    
    # Initialize database connection
    try:
        await db.connect(DATABASE_URL)
        await db.initialize_tables()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"⚠️ Failed to sync commands: {e}")
    
    print("\n🎉 Bot is ready! Use / commands in your Discord server.")


@bot.event
async def on_guild_join(guild: discord.Guild):
    """Handle bot joining a new guild."""
    print(f"🎉 Joined new guild: {guild.name} (ID: {guild.id})")
    
    # Ensure database tables exist for new guild
    try:
        await db.initialize_tables()
    except Exception as e:
        print(f"Error initializing tables for new guild: {e}")


@bot.event
async def on_guild_remove(guild: discord.Guild):
    """Handle bot leaving a guild."""
    print(f"👋 Left guild: {guild.name} (ID: {guild.id})")


async def load_cogs():
    """Load all cogs (modules) for the bot."""
    cog_dir = "cogs"
    
    if not os.path.exists(cog_dir):
        print(f"⚠️ Cogs directory '{cog_dir}' not found!")
        return
    
    for filename in os.listdir(cog_dir):
        if filename.endswith('.py') and not filename.startswith('_'):
            cog_name = f"{cog_dir}.{filename[:-3]}"  # Remove .py extension
            try:
                await bot.load_extension(cog_name)
                print(f"✅ Loaded cog: {cog_name}")
            except Exception as e:
                print(f"❌ Failed to load cog {cog_name}: {e}")


async def main():
    """Main async function to run the bot."""
    async with bot:
        # Load all cogs
        await load_cogs()
        
        # Start the bot
        try:
            await bot.start(DISCORD_TOKEN)
        except discord.LoginFailure:
            print("❌ Invalid bot token! Please check your DISCORD_TOKEN in .env file")
        except Exception as e:
            print(f"❌ Error starting bot: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
        # Cleanup database connection
        asyncio.run(db.disconnect())