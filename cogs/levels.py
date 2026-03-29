"""Level system cog - handles XP, levels, and role rewards."""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import asyncio

from database import db


class LevelSystem(commands.Cog):
    """Handles level system functionality including XP, levels, and role rewards."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.xp_cooldown = {}  # Track message cooldowns
        self.voice_sessions = {}  # Track voice session start times
        
        # Configuration - customize these values as needed
        self.xp_per_message = 15  # XP gained per message
        self.xp_per_voice_minute = 2  # XP gained per minute in voice chat
        self.message_cooldown = 60  # Seconds between XP gains from messages
        
        # Level roles configuration - modify this dict to set up level roles
        # Format: {level: role_id}
        self.level_roles = {
            5: None,   # Replace None with actual role ID
            10: None,  # Replace None with actual role ID
            20: None,  # Replace None with actual role ID
            30: None,  # Replace None with actual role ID
            50: None,  # Replace None with actual role ID
            100: None, # Replace None with actual role ID
        }
    
    async def ensure_user_exists(self, user: discord.Member) -> None:
        """Ensure user exists in the database."""
        existing = await db.db.get_user(user.id, user.guild.id, user.name)
        if not existing:
            # User will be created automatically by get_user
            pass
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle message events for XP gain."""
        if message.author.bot or not message.guild:
            return
        
        # Check cooldown
        now = asyncio.get_event_loop().time()
        user_key = (message.author.id, message.guild.id)
        
        if user_key in self.xp_cooldown:
            if now - self.xp_cooldown[user_key] < self.message_cooldown:
                return
        
        # Update cooldown
        self.xp_cooldown[user_key] = now
        
        # Ensure user exists in DB
        await self.ensure_user_exists(message.author)
        
        # Add XP
        result = await db.db.add_experience(
            message.author.id,
            message.guild.id,
            self.xp_per_message,
            message.author.name
        )
        
        if result:
            # Check for level up
            current_xp = result.get('experience', 0)
            current_level = result.get('level', 1)
            
            # Calculate new level based on XP (formula: level = sqrt(xp / 100))
            calculated_level = int((current_xp / 100) ** 0.5) + 1
            
            if calculated_level > current_level:
                # Level up!
                await db.db.update_user(
                    message.author.id,
                    message.guild.id,
                    level=calculated_level
                )
                await self.handle_level_up(message.author, calculated_level)
    
    @commands.Cog.listener()
    async def on_voice_state_update(
        self, 
        member: discord.Member, 
        before: discord.VoiceState, 
        after: discord.VoiceState
    ):
        """Handle voice channel joins/leaves for XP tracking."""
        if member.bot or not member.guild:
            return
        
        user_key = (member.id, member.guild.id)
        
        # Joined a voice channel
        if after.channel and not before.channel:
            self.voice_sessions[user_key] = asyncio.get_event_loop().time()
            await self.ensure_user_exists(member)
        
        # Left a voice channel
        elif not after.channel and before.channel:
            if user_key in self.voice_sessions:
                duration = asyncio.get_event_loop().time() - self.voice_sessions[user_key]
                minutes = int(duration / 60)
                
                if minutes > 0:
                    # Add XP for voice time (2 XP per minute)
                    xp_gained = minutes * self.xp_per_voice_minute
                    
                    result = await db.db.add_experience(
                        member.id,
                        member.guild.id,
                        xp_gained,
                        member.name
                    )
                    
                    # Also update voice minutes
                    if result:
                        await db.db.update_user(
                            member.id,
                            member.guild.id,
                            voice_minutes=result.get('voice_minutes', 0) + minutes
                        )
                        
                        # Check for level up
                        current_xp = result.get('experience', 0)
                        current_level = result.get('level', 1)
                        
                        # Calculate new level based on XP
                        calculated_level = int((current_xp / 100) ** 0.5) + 1
                        
                        if calculated_level > current_level:
                            await db.db.update_user(
                                member.id,
                                member.guild.id,
                                level=calculated_level
                            )
                            await self.handle_level_up(member, calculated_level)
                
                del self.voice_sessions[user_key]
    
    async def handle_level_up(self, member: discord.Member, new_level: int) -> None:
        """Handle level up events including role assignment."""
        # Send notification
        try:
            channel = member.guild.system_channel or member.guild.text_channels[0]
            embed = discord.Embed(
                title="🎉 Level Up!",
                description=f"{member.mention} reached **Level {new_level}**!",
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)
        except Exception:
            pass  # Ignore errors sending level up message
        
        # Assign level role if configured
        await self.assign_level_role(member, new_level)
        
        # Update database with new level info
        try:
            user_data = await db.db.get_user(member.id, member.guild.id)
            if user_data:
                current_xp = user_data.get('experience', 0)
                
                await db.db.update_user(
                    member.id,
                    member.guild.id,
                    experience=current_xp  # Keep current XP
                )
        except Exception as e:
            print(f"Error updating DB on level up: {e}")
    
    async def assign_level_role(self, member: discord.Member, level: int) -> None:
        """Assign role based on level if configured."""
        guild = member.guild
        
        # Check if we have a role for this level
        role_id = self.level_roles.get(level)
        if not role_id:
            return
        
        # Get the role from Discord
        try:
            role = guild.get_role(role_id)
            if role:
                # Check if member already has this role
                if role not in member.roles:
                    await member.add_roles(role, reason=f"Level {level} reward")
                    
                    # Update database record
                    await db.db.assign_role(member.id, guild.id, role_id)
        except discord.Forbidden:
            # Bot doesn't have permission to add roles
            print(f"⚠️ Cannot assign role to {member.name}: Missing permissions")
        except Exception as e:
            print(f"Error assigning level role: {e}")
    
    @app_commands.command(name="stats", description="View your statistics card")
    async def stats(self, interaction: discord.Interaction):
        """Show user's statistics as a beautiful image card."""
        await interaction.response.defer()
        
        user = interaction.user
        guild = interaction.guild
        
        # Ensure user exists in DB
        await self.ensure_user_exists(user)
        
        # Get user data
        user_data = await db.db.get_user(user.id, guild.id, user.name)
        
        if not user_data:
            await interaction.followup.send("❌ Could not retrieve your stats.", ephemeral=True)
            return
        
        # Get leaderboard rank
        leaderboard = await db.db.get_leaderboard(guild.id, limit=100)
        rank = next((i + 1 for i, u in enumerate(leaderboard) if u['user_id'] == user.id), len(leaderboard) + 1)
        
        # Calculate XP needed for next level
        current_level = user_data.get('level', 1)
        current_xp = user_data.get('experience', 0)
        xp_to_next = (current_level + 1) ** 2 * 100  # Formula: (level+1)^2 * 100
        
        # Generate stats card
        from utils import image_gen
        
        avatar_url = user.display_avatar.url if user.display_avatar else None
        
        try:
            card_buffer = await image_gen.generate_stats_card(
                username=user.display_name,
                level=current_level,
                xp=current_xp,
                xp_to_next=xp_to_next,
                messages_count=user_data.get('messages_count', 0),
                voice_minutes=user_data.get('voice_minutes', 0),
                money=user_data.get('dollar', 0),
                rank=rank,
                avatar_url=avatar_url
            )
            
            file = discord.File(card_buffer, filename=f"stats_{user.id}.png")
            
            embed = discord.Embed(
                title=f"📊 {user.display_name}'s Stats",
                color=discord.Color.blue()
            )
            
            await interaction.followup.send(file=file, embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error generating stats card: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="rank", description="View your current rank and level")
    async def rank(self, interaction: discord.Interaction):
        """Show user's current rank and level information."""
        user = interaction.user
        guild = interaction.guild
        
        await self.ensure_user_exists(user)
        user_data = await db.db.get_user(user.id, guild.id, user.name)
        
        if not user_data:
            await interaction.response.send_message("❌ Could not retrieve your rank.", ephemeral=True)
            return
        
        # Calculate rank
        leaderboard = await db.db.get_leaderboard(guild.id, limit=100)
        rank = next((i + 1 for i, u in enumerate(leaderboard) if u['user_id'] == user.id), len(leaderboard) + 1)
        
        # Calculate XP values
        current_level = user_data.get('level', 1)
        current_xp = user_data.get('experience', 0)
        xp_to_next = (current_level + 1) ** 2 * 100
        
        embed = discord.Embed(
            title=f"🏆 {user.display_name}'s Rank",
            color=discord.Color.gold()
        )
        embed.add_field(name="Level", value=str(current_level), inline=True)
        embed.add_field(name="XP", value=f"{current_xp} / {xp_to_next}", inline=True)
        embed.add_field(name="Rank", value=f"#{rank}", inline=True)
        embed.add_field(name="Messages", value=str(user_data.get('messages_count', 0)), inline=True)
        embed.add_field(
            name="Voice Time", 
            value=f"{user_data.get('voice_minutes', 0) // 60}h {user_data.get('voice_minutes', 0) % 60}m", 
            inline=True
        )
        embed.add_field(name="Money", value=f"${user_data.get('dollar', 0):,}", inline=True)
        
        # Progress bar visualization
        progress = current_xp / xp_to_next * 10
        bar = "█" * int(progress) + "░" * (10 - int(progress))
        embed.add_field(name="Progress", value=f"[{bar}] {progress:.1f}%", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="leaderboard", description="View the server leaderboard")
    async def leaderboard(self, interaction: discord.Interaction, limit: int = 10):
        """Show the top users by level on the server."""
        guild = interaction.guild
        
        if limit < 1 or limit > 50:
            limit = 10
        
        leaderboard = await db.db.get_leaderboard(guild.id, limit=limit)
        
        if not leaderboard:
            await interaction.response.send_message("❌ No data available yet.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🏆 Server Leaderboard",
            description=f"Top {len(leaderboard)} users by level",
            color=discord.Color.gold()
        )
        
        for i, user_data in enumerate(leaderboard, 1):
            # Try to get Discord user object
            discord_user = guild.get_member(user_data['user_id'])
            username = discord_user.display_name if discord_user else user_data.get('username', 'Unknown')
            
            medals = ["🥇", "🥈", "🥉"]
            medal = medals[i - 1] if i <= 3 else f"{i}."
            
            level = user_data.get('level', 1)
            xp = user_data.get('experience', 0)
            messages = user_data.get('messages_count', 0)
            voice = user_data.get('voice_minutes', 0)
            
            embed.add_field(
                name=f"{medal} {username}",
                value=f"Level {level} • {xp} XP\n"
                      f"📝 {messages} msgs • 🎤 {voice} min",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="levelroles", description="Configure level roles (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def levelroles(self, interaction: discord.Interaction, level: int, role: discord.Role):
        """Set which role to award at a specific level."""
        self.level_roles[level] = role.id
        
        embed = discord.Embed(
            title="✅ Level Role Configured",
            description=f"Role **{role.name}** will be awarded at **Level {level}**",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def giverole(self, ctx: commands.Context, member: discord.Member, amount: int):
        """Give money to a user (text command for admins)."""
        await db.db.update_user(member.id, ctx.guild.id, dollar=amount)
        await ctx.send(f"✅ Gave ${amount:,} to {member.mention}")
    
    @giverole.error
    async def giverole_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need administrator permissions to use this command.")


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(LevelSystem(bot))
