import re
from typing import Optional


class SpamResult:
    """Result of a spam check."""

    def __init__(
        self, is_spam: bool = False, reason: Optional[str] = None, score: float = 0.0
    ) -> None:
        self.is_spam = is_spam
        self.reason = reason
        self.score = score

    def __bool__(self) -> bool:
        return self.is_spam


class SpamDetector:
    """Heuristic-based spam detector.

    Checks:
    - Excessive caps (>70% of message)
    - Repeated characters (e.g. "привеееееет")
    - Too many @mentions
    - Repeated messages (same text sent multiple times)
    """

    def __init__(self) -> None:
        self.recent_messages: dict[int, list[tuple[str, float]]] = {}
        self._caps_re = re.compile(r"[A-ZА-ЯЁ]", re.UNICODE)
        self._repeat_re = re.compile(r"(.)\1{4,}")

    def check(self, text: Optional[str], user_id: Optional[int] = None) -> SpamResult:
        if not text:
            return SpamResult()

        score = 0.0
        reasons: list[str] = []

        # 1. Excessive caps
        total_letters = len([c for c in text if c.isalpha()])
        if total_letters > 5:
            caps_count = len(self._caps_re.findall(text))
            caps_ratio = caps_count / total_letters
            if caps_ratio > 0.7:
                score += 0.5
                reasons.append("CapsLock > 70%")
                if caps_ratio > 0.9:
                    score += 0.3

        # 2. Repeated characters
        repeats = self._repeat_re.findall(text)
        if repeats:
            repeat_score = min(len(repeats) * 0.2, 0.6)
            score += repeat_score
            reasons.append(f"Repeated chars: {len(repeats)}")

        # 3. Too many @mentions
        mentions = text.count("@")
        if mentions > 3:
            mention_score = min((mentions - 3) * 0.15, 0.5)
            score += mention_score
            reasons.append(f"Too many mentions: {mentions}")

        # 4. Too many links
        links = len(re.findall(r"https?://\S+", text))
        if links > 2:
            link_score = min((links - 2) * 0.2, 0.6)
            score += link_score
            reasons.append(f"Too many links: {links}")

        # 5. Repeated message
        if user_id is not None:
            import time

            now = time.monotonic()
            user_msgs = self.recent_messages.get(user_id, [])
            # Keep only last 60 seconds (increased from 10)
            user_msgs = [m for m in user_msgs if now - m[1] < 60]
            same_count = sum(1 for m in user_msgs if m[0] == text)
            user_msgs.append((text, now))
            # Per-user cap: keep only last 100 messages
            if len(user_msgs) > 100:
                user_msgs = user_msgs[-100:]
            self.recent_messages[user_id] = user_msgs
            if same_count >= 3:
                score += 0.7
                reasons.append("Message repetition")

            # Prune user key if list is empty
            if not user_msgs:
                self.recent_messages.pop(user_id, None)

        # Global cap: limit total users tracked to 1000
        if len(self.recent_messages) > 1000:
            # Remove oldest user(s) based on earliest timestamp
            oldest_users = sorted(
                self.recent_messages.items(),
                key=lambda x: x[1][0][1] if x[1] else float('inf')
            )[:len(self.recent_messages) - 1000]
            for user_id_to_remove, _ in oldest_users:
                del self.recent_messages[user_id_to_remove]

        is_spam = score >= 0.5
        return SpamResult(
            is_spam=is_spam,
            reason="; ".join(reasons) if reasons else None,
            score=score,
        )


# Singleton
spam_detector = SpamDetector()
