# Discord Bot - Level System with PostgreSQL

Многофункциональный Discord бот с системой уровней, голосовым трекингом и визуализацией статистики.

## 📋 Требования

- Python 3.9+
- PostgreSQL база данных (локальная или облачная)
- Discord Bot Token

## 🚀 Установка

### 1. Установите зависимости

```bash
pip install -r requirements.txt
```

### 2. Настройте переменные окружения

Откройте файл `.env` и заполните следующие поля:

```env
DISCORD_TOKEN=your_bot_token_here
DATABASE_URL=postgresql://username:password@host:port/database_name
```

**Где взять токен бота:**
1. Перейдите на [Discord Developer Portal](https://discord.com/developers/applications)
2. Создайте новое приложение или выберите существующее
3. Перейдите в раздел "Bot"
4. Нажмите "Reset Token" и скопируйте токен

**Примеры DATABASE_URL:**
- **PostgreSQL Cloud (Neon):** `postgresql://user:pass@ep-xxx.region.aws.neon.tech/dbname?sslmode=require`
- **Supabase:** `postgresql://postgres:pass@db.xxx.supabase.co:5432/postgres`
- **Railway:** `postgresql://user:pass@railway.app:port/dbname`
- **Локальный PostgreSQL:** `postgresql://postgres:password@localhost:5432/mydb`

### 3. Пригласите бота на сервер

Используйте следующую ссылку для приглашения бота (замените `YOUR_CLIENT_ID` на ID вашего бота):

```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands
```

**Важно:** Боту требуются права администратора для:
- Назначения ролей за уровни
- Чтения сообщений для подсчёта XP
- Отслеживания голосовых каналов

## 🎮 Команды бота

### Slash команды (/)

| Команда | Описание |
|---------|----------|
| `/stats` | Показать вашу статистику в виде красивой карточки с изображением |
| `/rank` | Показать ваш текущий уровень и позицию в рейтинге |
| `/leaderboard [limit]` | Показать топ пользователей сервера (по умолчанию 10) |
| `/levelroles <level> <role>` | Настроить роль для определённого уровня (только администраторы) |

### Текстовые команды

| Команда | Описание |
|---------|----------|
| `!giverole @user <amount>` | Выдать деньги пользователю (только администраторы) |

## ⚙️ Настройка системы уровней

### Конфигурация в cogs/levels.py

Откройте файл `cogs/levels.py` и измените следующие параметры:

```python
# Настройки получения опыта
self.xp_per_message = 15              # XP за сообщение
self.xp_per_voice_minute = 2          # XP за минуту в голосовом канале
self.message_cooldown = 60            # Задержка между получением XP (секунды)

# Роли за уровни
self.level_roles = {
    5: 123456789012345678,   # ID роли для 5 уровня
    10: 123456789012345679,  # ID роли для 10 уровня
    20: 123456789012345680,  # ID роли для 20 уровня
    # Добавьте свои уровни и роли
}
```

**Как получить ID роли:**
1. Включите режим разработчика в Discord (Настройки → Дополнительно → Режим разработчика)
2. Кликните правой кнопкой мыши на роли
3. Выберите "Копировать ID"

## 🗄️ Структура базы данных

Бот автоматически создаст следующие таблицы при первом запуске:

### User_data (основная таблица)
- `user_id` - ID пользователя Discord
- `guild_id` - ID сервера
- `username` - имя пользователя
- `level` - текущий уровень
- `xp` - текущий опыт
- `xp_to_next_level` - опыт до следующего уровня
- `messages_count` - количество сообщений
- `voice_minutes` - минуты в голосовых каналах
- `money` - баланс пользователя (для будущей экономики)
- `roles` - массив ID полученных ролей
- `created_at` - дата создания записи
- `updated_at` - дата последнего обновления

## 🛠️ Модульная структура

```
/workspace
├── main.py                 # Точка входа бота
├── .env                    # Файл с токенами и настройками
├── requirements.txt        # Зависимости Python
├── database/
│   ├── __init__.py
│   └── db_manager.py       # Управление базой данных
├── cogs/
│   ├── __init__.py
│   └── levels.py           # Модуль системы уровней
└── utils/
    ├── __init__.py
    └── image_gen.py        # Генерация изображений статистики
```

## 🔧 Расширение функционала

### Добавление новой команды

1. Создайте новый файл в папке `cogs/`, например `economy.py`
2. Реализуйте класс Cog с командами
3. Добавьте функцию `setup(bot)` в конце файла
4. Бот автоматически загрузит новый модуль при запуске

### Пример добавления экономической системы

Создайте `cogs/economy.py`:

```python
from discord import app_commands
from discord.ext import commands
from database import db

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="balance", description="Check your balance")
    async def balance(self, interaction):
        user_data = await db.db.get_user(interaction.user.id, interaction.guild.id)
        await interaction.response.send_message(f"Your balance: ${user_data['money']}")

async def setup(bot):
    await bot.add_cog(Economy(bot))
```

## 🐛 Решение проблем

### Бот не запускается
- Проверьте правильность токена в `.env`
- Убедитесь, что все зависимости установлены: `pip install -r requirements.txt`
- Проверьте подключение к базе данных

### Команды не появляются в Discord
- Убедитесь, что бот имеет право `applications.commands`
- Подождите несколько минут (синхронизация команд может занять время)
- Перезапустите бота

### Ошибки с базой данных
- Проверьте правильность `DATABASE_URL`
- Убедитесь, что PostgreSQL доступен из сети
- Для облачных баз проверьте настройки SSL

## 📝 Лицензия

Этот проект создан для личного использования. Вы можете модифицировать его по своему усмотрению.

## 💡 Будущие улучшения

- [ ] Полноценная экономическая система
- [ ] Магазин ролей и предметов
- [ ] Система достижений
- [ ] Ежедневные награды
- [ ] Система репутации
- [ ] Интеграция с другими ботами через общую базу данных
