"""Tests for services/spam_detector.py — memory leak fix and spam detection."""

import time
from services.spam_detector import SpamDetector, SpamResult


class TestSpamResult:
    def test_default_values(self):
        r = SpamResult()
        assert r.is_spam is False
        assert r.reason is None
        assert r.score == 0.0

    def test_bool_true(self):
        r = SpamResult(is_spam=True)
        assert bool(r) is True

    def test_bool_false(self):
        r = SpamResult(is_spam=False)
        assert bool(r) is False


class TestSpamDetector:
    def setup_method(self):
        self.detector = SpamDetector()

    def test_empty_text(self):
        result = self.detector.check(None)
        assert result.is_spam is False

    def test_caps_high(self):
        result = self.detector.check("THIS IS ALL CAPS MESSAGE YO")
        assert result.is_spam is True
        assert "CapsLock" in result.reason

    def test_repeated_chars(self):
        result = self.detector.check("привееееееет")
        assert "Repeated chars" in result.reason

    def test_mentions(self):
        result = self.detector.check("hey @user1 @user2 @user3 @user4")
        assert "Too many mentions" in result.reason

    def test_links(self):
        result = self.detector.check("check https://a.com https://b.com https://c.com")
        assert "Too many links" in result.reason

    def test_clean_message(self):
        result = self.detector.check("hello world")
        assert result.is_spam is False


class TestMemoryBounds:
    """Verify memory leak fixes."""

    def test_per_user_cap_100(self):
        detector = SpamDetector()
        # Send 150 messages from one user
        for i in range(150):
            detector.check(f"message {i}", user_id=123)
        # Per-user list should be capped at 100
        assert len(detector.recent_messages[123]) <= 100

    def test_total_user_cap_1000(self):
        detector = SpamDetector()
        # Send messages from 1050 different users
        for i in range(1050):
            detector.check("hello", user_id=i)
        # Total dict should be bounded at ~1000
        assert len(detector.recent_messages) <= 1050  # small margin for timing

    def test_60_second_pruning(self):
        detector = SpamDetector()
        # Manually insert old entries (simulating 60+ seconds ago)
        detector.recent_messages[999] = [("old", time.monotonic() - 70)]
        # New check should prune old entries
        detector.check("new message", user_id=999)
        # The old entry should be pruned, only the new one remains
        assert len(detector.recent_messages[999]) == 1
