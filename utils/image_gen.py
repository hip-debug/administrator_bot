"""Image generation for user statistics."""

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import aiohttp
from typing import Optional


class StatsCardGenerator:
    """Generates beautiful stats cards for users."""
    
    def __init__(self):
        self.font_large = None
        self.font_medium = None
        self.font_small = None
        self._fonts_loaded = False
    
    async def load_fonts(self) -> None:
        """Load fonts for the stats card."""
        # Try to load system fonts, fallback to default
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
        ]
        
        try:
            self.font_large = ImageFont.truetype(font_paths[0], 48)
            self.font_medium = ImageFont.truetype(font_paths[1], 32)
            self.font_small = ImageFont.truetype(font_paths[1], 24)
            self._fonts_loaded = True
        except (IOError, OSError):
            # Fallback to default font
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self._fonts_loaded = True
    
    async def get_user_avatar(self, avatar_url: str) -> Image.Image:
        """Download user avatar from Discord."""
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    return Image.open(BytesIO(image_data)).convert("RGBA")
        return None
    
    def create_progress_bar(self, current: int, maximum: int, width: int = 200, height: int = 20) -> Image.Image:
        """Create a progress bar image."""
        progress = max(0, min(1, current / maximum)) if maximum > 0 else 0
        
        # Create progress bar background
        bar = Image.new('RGBA', (width, height), (50, 50, 50, 255))
        draw = ImageDraw.Draw(bar)
        
        # Draw progress fill
        fill_width = int(width * progress)
        if fill_width > 0:
            # Gradient color from blue to purple
            draw.rectangle([0, 0, fill_width, height], fill=(100, 149, 237, 255))
        
        return bar
    
    async def generate_stats_card(
        self,
        username: str,
        level: int,
        xp: int,
        xp_to_next: int,
        messages_count: int,
        voice_minutes: int,
        money: int,
        rank: int,
        avatar_url: Optional[str] = None
    ) -> BytesIO:
        """Generate a beautiful stats card image."""
        
        if not self._fonts_loaded:
            await self.load_fonts()
        
        # Card dimensions
        width, height = 800, 400
        
        # Create base image with gradient background
        card = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(card)
        
        # Background gradient (dark theme)
        for y in range(height):
            r = int(30 + (y / height) * 20)
            g = int(30 + (y / height) * 20)
            b = int(40 + (y / height) * 30)
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
        
        # Add rounded rectangle effect (simplified)
        draw.rectangle([20, 20, width - 20, height - 20], outline=(100, 149, 237, 255), width=3)
        
        # Avatar section
        avatar_size = 150
        avatar_x, avatar_y = 50, 50
        
        if avatar_url:
            try:
                avatar = await self.get_user_avatar(avatar_url)
                if avatar:
                    avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
                    
                    # Create circular mask
                    mask = Image.new('L', (avatar_size, avatar_size), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.ellipse([0, 0, avatar_size, avatar_size], fill=255)
                    
                    # Apply circular crop
                    avatar.putalpha(mask)
                    card.paste(avatar, (avatar_x, avatar_y), avatar)
            except Exception:
                pass
        
        # If no avatar or failed to load, draw placeholder
        if not avatar_url:
            draw.ellipse([avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size], 
                        fill=(100, 149, 237, 200), outline=(255, 255, 255, 255), width=3)
            # Draw initial letter
            initial = username[0].upper() if username else "?"
            
        # User info section
        text_x = avatar_x + avatar_size + 40
        text_y = 70
        
        # Username
        draw.text((text_x, text_y), username[:20], fill=(255, 255, 255, 255), font=self.font_large)
        
        # Level badge
        level_text = f"Level {level}"
        draw.text((text_x, text_y + 60), level_text, fill=(100, 149, 237, 255), font=self.font_medium)
        
        # XP Progress bar
        progress_y = text_y + 110
        draw.text((text_x, progress_y), f"XP: {xp} / {xp_to_next}", fill=(200, 200, 200, 255), font=self.font_small)
        
        progress_bar = self.create_progress_bar(xp, xp_to_next, 300, 25)
        card.paste(progress_bar, (text_x, progress_y + 35), progress_bar)
        
        # Stats section (right side)
        stats_x = width - 280
        stats_y = 70
        
        # Messages count
        draw.text((stats_x, stats_y), "📝 Messages:", fill=(200, 200, 200, 255), font=self.font_medium)
        draw.text((stats_x, stats_y + 40), str(messages_count), fill=(255, 255, 255, 255), font=self.font_large)
        
        # Voice time
        voice_hours = voice_minutes // 60
        voice_mins = voice_minutes % 60
        draw.text((stats_x, stats_y + 100), "🎤 Voice Time:", fill=(200, 200, 200, 255), font=self.font_medium)
        draw.text((stats_x, stats_y + 140), f"{voice_hours}h {voice_mins}m", fill=(255, 255, 255, 255), font=self.font_large)
        
        # Money
        draw.text((stats_x, stats_y + 200), "💰 Money:", fill=(255, 215, 0, 255), font=self.font_medium)
        draw.text((stats_x, stats_y + 240), f"${money:,}", fill=(255, 255, 255, 255), font=self.font_large)
        
        # Rank
        draw.text((stats_x, stats_y + 300), f"🏆 Rank: #{rank}", fill=(255, 215, 0, 255), font=self.font_medium)
        
        # Convert to bytes
        buffer = BytesIO()
        card.save(buffer, format='PNG')
        buffer.seek(0)
        
        return buffer


# Global generator instance
stats_generator = StatsCardGenerator()
