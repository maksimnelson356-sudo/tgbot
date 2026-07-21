"""Content filtering: phone numbers, emails, forwarded messages."""
import re

# Phone number patterns (international)
PHONE_RE = re.compile(
    r"(?:\+?7|8|(?:\+?1[-\s]?)?\d{1,4})[-\s]?\(?\d{1,4}\)?[-\s]?\d{1,4}[-\s]?\d{1,4}[-\s]?\d{1,4}"
)

# Email pattern
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def has_phone(text: str) -> bool:
    """Check if text contains a phone number."""
    return bool(PHONE_RE.search(text))


def has_email(text: str) -> bool:
    """Check if text contains an email address."""
    return bool(EMAIL_RE.search(text))
