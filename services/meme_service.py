"""Generate meme images locally using Pillow — no external dependencies."""
import io
import random

from PIL import Image, ImageDraw, ImageFont

_RU_TEXTS = [
    "Жиза", "Когда всё хорошо", "Мем дня", "Ну такое",
    "Бывает", "🤷‍♂️", "Сложно", "Понедельник",
]
_EN_TEXTS = [
    "When it hits different", "Mood", "Relatable",
    "Same energy", "🤷‍♂️", "This is fine", "Okay",
]

_BG_COLORS = [
    (45, 55, 70), (60, 40, 60), (30, 70, 50),
    (80, 50, 40), (40, 60, 80), (70, 70, 40),
]


async def get_random_meme_bytes(lang: str = "en") -> io.BytesIO:
    """Generate a random meme image using Pillow."""
    texts = _RU_TEXTS if lang == "ru" else _EN_TEXTS
    w, h = 500, 400
    bg = random.choice(_BG_COLORS)
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    # Decorative circles
    for _ in range(random.randint(3, 6)):
        cx = random.randint(50, w - 50)
        cy = random.randint(50, h - 50)
        cr = random.randint(30, 80)
        color = (
            random.randint(80, 220),
            random.randint(80, 220),
            random.randint(80, 220),
        )
        draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=color, outline=None)

    # Text
    try:
        font = ImageFont.truetype("arial.ttf", size=40)
    except (IOError, OSError):
        font = ImageFont.load_default()

    text = random.choice(texts)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (w - tw) // 2
    y = (h - th) // 2
    # Shadow
    draw.text((x + 2, y + 2), text, fill=(0, 0, 0, 100), font=font)
    draw.text((x, y), text, fill=(255, 255, 255), font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
