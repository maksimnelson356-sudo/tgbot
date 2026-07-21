"""Generate welcome card images using Pillow."""
import io
import random

from PIL import Image, ImageDraw, ImageFont


async def create_welcome_card(name: str, chat_title: str) -> io.BytesIO:
    """Generate a welcome card image."""
    w, h = 600, 250
    colors = [
        (70, 130, 180), (60, 90, 150), (100, 70, 140),
        (50, 120, 100), (140, 80, 60), (80, 60, 120),
    ]
    bg = random.choice(colors)

    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    # Decorative circles
    for _ in range(random.randint(3, 6)):
        cx = random.randint(50, w - 50)
        cy = random.randint(50, h - 50)
        cr = random.randint(30, 80)
        color = (random.randint(120, 255), random.randint(120, 255), random.randint(120, 255))
        draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=color, outline=None)

    # Welcome text overlay
    try:
        font_big = ImageFont.truetype("arial.ttf", size=48)
        font_small = ImageFont.truetype("arial.ttf", size=28)
    except (IOError, OSError):
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

    welcome = f"Welcome!"
    name_text = name
    chat_text = f"to {chat_title}"

    # Center text
    for text, font in [(welcome, font_big), (name_text, font_big), (chat_text, font_small)]:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (w - tw) // 2
        y = 30 + list([welcome, name_text, chat_text]).index(text) * 60
        y = min(y, h - th - 20)
        draw.text((x + 2, y + 2), text, fill=(0, 0, 0, 60), font=font)
        draw.text((x, y), text, fill=(255, 255, 255), font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
