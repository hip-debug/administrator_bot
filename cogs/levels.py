import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import sys
sys.path.append('/workspace')

from database.db_manager import Database
from utils.image_gen import generate_stats_card

class Levels(commands.Cog):
    """Система уровней и статистики"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db: Database = bot.db
        self.xp_per_message = 15
        self.xp_per_voice_minute = 10
        self.cooldown = {}  #Cooldown для сообщений (60 секунд)
        self.voice_tracking = {}  #Отслеживание времени в голосе
        
        # Роли за уровни: {уровень: ID_роли}
        # Замените ID на свои при настройке
        self.level_roles = {
            5: None,   # Пример: 123456789012345678
            10: None,
            15: None,
            20: None,
        }

    async def check_level_up(self, user_id: int, guild_id: int, new_level: int, old_level: int):
        """Проверка и выдача ролей при повышении уровня"""
        if new_level <= old_level:
            return
        
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        
        member = guild.get_member(user_id)
        if not member:
            return
        
        # Проверяем роли для всех уровней от старого до нового
        for level in range(old_level + 1, new_level + 1):
            role_id = self.level_roles.get(level)
            if role_id:
                role = guild.get_role(role_id)
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role, reason=f"Повышение до {level} уровня")
                    except discord.Forbidden:
                        print(f"❌ Нет прав для выдачи роли {role.name}")
                    except Exception as e:
                        print(f"❌ Ошибка при выдаче роли: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Начисление XP за сообщения"""
        if message.author.bot or not message.guild:
            return
        
        user_id = message.author.id
        guild_id = message.guild.id
        now = datetime.now()
        
        # Проверка cooldown (60 секунд)
        last_time = self.cooldown.get(user_id)
        if last_time and (now - last_time).total_seconds() < 60:
            return
        
        self.cooldown[user_id] = now
        
        # Обновляем данные пользователя
        user_data = await self.db.get_user(user_id, guild_id, message.author.name)
        
        # Добавляем счетчик сообщений
        await self.db.update_user(
            user_id, guild_id,
            messages_count=user_data['messages_count'] + 1
        )
        
        # Добавляем опыт
        result, leveled_up = await self.db.add_experience(user_id, guild_id, self.xp_per_message)
        
        if leveled_up and result:
            new_level = result['level']
            old_level = user_data['level']
            
            # Уведомление о повышении
            channel = message.channel
            embed = discord.Embed(
                title="🎉 Повышение уровня!",
                description=f"{message.author.mention} достиг **{new_level} уровня**!",
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            await channel.send(embed=embed)
            
            # Выдача ролей
            await self.check_level_up(user_id, guild_id, new_level, old_level)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Отслеживание времени в голосовых каналах"""
        if member.bot or not member.guild:
            return
        
        user_id = member.id
        guild_id = member.guild.id
        
        # Если зашел в голосовой канал
        if before.channel is None and after.channel is not None:
            self.voice_tracking[user_id] = datetime.now()
        
        # Если вышел из голосового канала
        elif before.channel is not None and after.channel is None:
            if user_id in self.voice_tracking:
                start_time = self.voice_tracking.pop(user_id)
                minutes = int((datetime.now() - start_time).total_seconds() / 60)
                
                if minutes > 0:
                    # Получаем или создаем пользователя
                    user_data = await self.db.get_user(user_id, guild_id, member.name)
                    
                    # Обновляем время в голосе
                    await self.db.update_user(
                        user_id, guild_id,
                        voice_minutes=user_data['voice_minutes'] + minutes
                    )
                    
                    # Добавляем опыт за голос
                    xp_gain = minutes * self.xp_per_voice_minute
                    result, leveled_up = await self.db.add_experience(user_id, guild_id, xp_gain)
                    
                    if leveled_up and result:
                        new_level = result['level']
                        old_level = user_data['level']
                        
                        # Уведомление (в ЛС или чат)
                        try:
                            embed = discord.Embed(
                                title="🎉 Повышение уровня!",
                                description=f"{member.mention} достиг **{new_level} уровня**!",
                                color=discord.Color.gold()
                            )
                            await member.send(embed=embed)
                        except:
                            pass
                        
                        # Выдача ролей
                        await self.check_level_up(user_id, guild_id, new_level, old_level)

    @app_commands.command(name="stats", description="Показать вашу статистику")
    async def stats(self, interaction: discord.Interaction, member: discord.Member = None):
        """Показать красивую карточку статистики"""
        await interaction.response.defer()
        
        target = member or interaction.user
        
        try:
            user_data = await self.db.get_user(target.id, interaction.guild.id, target.name)
            
            if not user_data:
                await interaction.followup.send("❌ Пользователь не найден в базе данных", ephemeral=True)
                return
            
            # Получаем ранг пользователя
            leaderboard = await self.db.get_leaderboard(interaction.guild.id, 100)
            rank = next((i + 1 for i, u in enumerate(leaderboard) if u['user_id'] == target.id), None)
            
            # Форматируем данные для генерации
            card_data = {
                'level': user_data['level'],
                'xp': user_data['experience'],
                'max_xp': int((user_data['level'] ** 2) * 100),
                'messages': user_data['messages_count'],
                'voice': user_data['voice_minutes'],
                'money': float(user_data['money']),
                'rank': rank
            }
            
            # Генерируем изображение
            image_data = await generate_stats_card(card_data, target.name, str(target.display_avatar.url))
            
            file = discord.File(fp=image_data, filename="stats_card.png")
            
            embed = discord.Embed(
                title=f"📊 Статистика: {target.name}",
                color=discord.Color.blue()
            )
            
            await interaction.followup.send(file=file, embed=embed)
            
        except Exception as e:
            print(f"❌ Ошибка при генерации stats: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ Произошла ошибка: {str(e)}", ephemeral=True)

    @app_commands.command(name="rank", description="Показать ваш текущий уровень")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        """Показать текущий уровень и прогресс"""
        await interaction.response.defer()
        
        target = member or interaction.user
        
        try:
            user_data = await self.db.get_user(target.id, interaction.guild.id, target.name)
            
            if not user_data:
                await interaction.followup.send("❌ Пользователь не найден", ephemeral=True)
                return
            
            level = user_data['level']
            exp = user_data['experience']
            next_level_exp = int((level ** 2) * 100)
            progress = min(exp / next_level_exp, 1.0) if next_level_exp > 0 else 0
            
            # Получаем ранг
            leaderboard = await self.db.get_leaderboard(interaction.guild.id, 100)
            rank = next((i + 1 for i, u in enumerate(leaderboard) if u['user_id'] == target.id), None)
            
            embed = discord.Embed(
                title=f"📈 Ранг: {target.name}",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=target.display_avatar.url)
            embed.add_field(name="Уровень", value=f"**{level}**", inline=True)
            embed.add_field(
                name="Опыт",
                value=f"{exp} / {next_level_exp} ({progress*100:.1f}%)",
                inline=True
            )
            if rank:
                embed.add_field(name="Ранг на сервере", value=f"**#{rank}**", inline=True)
            
            embed.add_field(name="💬 Сообщения", value=str(user_data['messages_count']), inline=True)
            embed.add_field(name="🎤 Голос", value=f"{user_data['voice_minutes']} мин", inline=True)
            embed.add_field(name="💰 Деньги", value=f"${float(user_data['money']):.2f}", inline=True)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            print(f"❌ Ошибка rank: {e}")
            await interaction.followup.send(f"❌ Ошибка: {str(e)}", ephemeral=True)

    @app_commands.command(name="leaderboard", description="Топ пользователей сервера")
    async def leaderboard(self, interaction: discord.Interaction, limit: int = 10):
        """Показать топ пользователей по опыту"""
        await interaction.response.defer()
        
        if limit < 1 or limit > 50:
            limit = 10
        
        try:
            top_users = await self.db.get_leaderboard(interaction.guild.id, limit)
            
            if not top_users:
                await interaction.followup.send("❌ Нет данных в лидерборде", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🏆 Топ пользователей",
                description=f"Топ {len(top_users)} по опыту",
                color=discord.Color.gold()
            )
            
            for i, user in enumerate(top_users, 1):
                user_id = user['user_id']
                username = user['username'] or f"User_{user_id}"
                level = user['level']
                exp = user['experience']
                
                # Пытаемся получить упоминание
                member = interaction.guild.get_member(user_id)
                mention = member.mention if member else username
                
                embed.add_field(
                    name=f"#{i} {mention}",
                    value=f"Уровень {level} • {exp} XP",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            print(f"❌ Ошибка leaderboard: {e}")
            await interaction.followup.send(f"❌ Ошибка: {str(e)}", ephemeral=True)

    @app_commands.command(name="levelroles", description="Настроить роли за уровни (только администраторы)")
    @app_commands.describe(level="Уровень для получения роли", role="Роль которую выдавать")
    async def levelroles(self, interaction: discord.Interaction, level: int, role: discord.Role):
        """Настройка ролей за уровни"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Только администраторы могут использовать эту команду", ephemeral=True)
            return
        
        self.level_roles[level] = role.id
        
        embed = discord.Embed(
            title="✅ Роль настроена",
            description=f"При достижении **{level} уровня** пользователи будут получать роль {role.mention}",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Levels(bot))
