from PIL import Image, ImageDraw, ImageFont
import io

def create_stats_card(user_data: dict, rank: int = None) -> bytes:
    """Создание красивой карточки статистики пользователя"""
    
    # Параметры изображения
    width, height = 800, 400
    bg_color = (30, 30, 40)
    card_color = (50, 50, 70)
    accent_color = (100, 150, 255)
    text_color = (255, 255, 255)
    secondary_text = (180, 180, 200)
    
    # Создаем изображение
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Рисуем основную карточку
    draw.rounded_rectangle([(50, 50), (750, 350)], radius=20, fill=card_color)
    
    # Рисуем акцентную полосу слева
    draw.rounded_rectangle([(50, 50), (70, 350)], radius=20, fill=accent_color)
    
    # Попытка загрузить шрифт
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        stat_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except:
        title_font = ImageFont.load_default()
        stat_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Имя пользователя
    username = user_data.get('username', 'Unknown User')
    draw.text((100, 80), username, font=title_font, fill=text_color)
    
    # Уровень
    level = user_data.get('level', 1)
    draw.text((100, 140), f"Уровень {level}", font=stat_font, fill=accent_color)
    
    # Опыт
    exp = user_data.get('experience', 0)
    next_level_exp = int(((level) ** 2) * 100)
    draw.text((100, 190), f"Опыт: {exp} / {next_level_exp}", font=stat_font, fill=text_color)
    
    # Прогресс бар
    bar_width = 400
    bar_height = 20
    bar_x = 100
    bar_y = 230
    
    if next_level_exp > 0:
        progress = min(exp / next_level_exp, 1.0)
    else:
        progress = 0
    
    # Фон прогресс бара
    draw.rounded_rectangle([(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)], 
                          radius=10, fill=(70, 70, 90))
    
    # Заполнение прогресс бара
    fill_width = int(bar_width * progress)
    if fill_width > 0:
        draw.rounded_rectangle([(bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height)], 
                              radius=10, fill=accent_color)
    
    # Статистика справа
    stats_x = 450
    stats_y = 140
    
    messages = user_data.get('messages_count', 0)
    voice_mins = user_data.get('voice_minutes', 0)
    money = user_data.get('money', 0.0)
    
    draw.text((stats_x, stats_y), f"💬 Сообщения: {messages}", font=stat_font, fill=text_color)
    draw.text((stats_x, stats_y + 50), f"🎤 Голос: {voice_mins} мин", font=stat_font, fill=text_color)
    draw.text((stats_x, stats_y + 100), f"💰 Деньги: ${money:.2f}", font=stat_font, fill=text_color)
    
    # Ранг
    if rank:
        draw.text((stats_x, stats_y + 160), f"🏆 Ранг: #{rank}", font=stat_font, fill=accent_color)
    
    # Сохраняем в буфер
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return buffer.getvalue()
