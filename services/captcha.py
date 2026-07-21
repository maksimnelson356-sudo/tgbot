import io
import random
import string
import time
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from config import settings


# In-memory store for pending CAPTCHAs
# Structure: {(chat_id, user_id): {"answer": str, "attempts": int, "sent_at": float}}
_pending: dict[tuple[int, int], dict] = {}


def generate_challenge() -> str:
    """Generate a random N-character alphanumeric string."""
    length = random.randint(4, 6)
    chars = string.ascii_uppercase + string.digits
    # Exclude confusable chars: 0O, 1I
    chars = chars.replace("O", "").replace("I", "").replace("0", "").replace("1", "")
    return "".join(random.choices(chars, k=length))


def create_captcha_image(text: str) -> io.BytesIO:
    """Create a CAPTCHA PIL image with noise and return as BytesIO."""
    width = settings.CAPTCHA_IMAGE_WIDTH
    height = settings.CAPTCHA_IMAGE_HEIGHT

    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Try to load a font, fall back to default
    try:
        font = ImageFont.truetype("arial.ttf", size=settings.CAPTCHA_FONT_SIZE)
    except (IOError, OSError):
        font = ImageFont.load_default()

    # Draw random background noise (lines)
    for _ in range(random.randint(5, 10)):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        color = (random.randint(180, 220), random.randint(180, 220), random.randint(180, 220))
        draw.line([(x1, y1), (x2, y2)], fill=color, width=2)

    # Draw the text with random rotation per character
    x_offset = random.randint(10, 20)
    y_base = height // 2 - settings.CAPTCHA_FONT_SIZE // 3

    for char in text:
        char_color = (
            random.randint(30, 100),
            random.randint(30, 100),
            random.randint(30, 150),
        )
        rotation = random.randint(-25, 25)
        # We draw each char separately with rotation
        char_img = Image.new("RGBA", (settings.CAPTCHA_FONT_SIZE, settings.CAPTCHA_FONT_SIZE), (0, 0, 0, 0))
        char_draw = ImageDraw.Draw(char_img)
        char_draw.text((0, 0), char, fill=char_color, font=font)
        rotated = char_img.rotate(rotation, expand=1, fillcolor=(255, 255, 255, 0))
        image.paste(rotated, (x_offset, y_base + random.randint(-10, 10)), rotated)
        x_offset += rotated.size[0] - random.randint(0, 5)

    # Draw additional random dots
    for _ in range(random.randint(50, 150)):
        x = random.randint(0, width)
        y = random.randint(0, height)
        dot_color = (random.randint(100, 200), random.randint(100, 200), random.randint(100, 200))
        draw.point((x, y), fill=dot_color)

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    return buf


def create_challenge(chat_id: int, user_id: int) -> tuple[str, io.BytesIO]:
    """Generate and store a CAPTCHA challenge.

    Returns (answer text, image buffer).
    """
    answer = generate_challenge()
    image = create_captcha_image(answer)
    _pending[(chat_id, user_id)] = {
        "answer": answer,
        "attempts": 0,
        "sent_at": time.time(),
    }
    return answer, image


def verify(chat_id: int, user_id: int, user_answer: str) -> Optional[bool]:
    """Verify a CAPTCHA answer.

    Returns:
    - True if correct
    - False if wrong (tracking attempts)
    - None if no pending CAPTCHA found
    """
    pending = _pending.get((chat_id, user_id))
    if pending is None:
        return None

    # Check timeout
    if time.time() - pending["sent_at"] > settings.CAPTCHA_TIMEOUT:
        del _pending[(chat_id, user_id)]
        return None

    if user_answer.strip().upper() == pending["answer"].strip().upper():
        del _pending[(chat_id, user_id)]
        return True

    pending["attempts"] += 1
    if pending["attempts"] >= settings.CAPTCHA_MAX_ATTEMPTS:
        # Too many attempts — remove
        del _pending[(chat_id, user_id)]
        return False

    return False


def remove_challenge(chat_id: int, user_id: int) -> None:
    """Remove a pending challenge (e.g., user passed another way)."""
    _pending.pop((chat_id, user_id), None)


def has_pending(chat_id: int, user_id: int) -> bool:
    return (chat_id, user_id) in _pending
