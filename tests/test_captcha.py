"""Tests for services/captcha.py — memory leak fix and captcha logic."""

import time
from unittest.mock import patch
from services.captcha import (
    generate_challenge,
    create_challenge,
    verify,
    has_pending,
    sweep_expired,
    _pending,
)


class TestGenerateChallenge:
    def test_length_4_to_6(self):
        for _ in range(100):
            result = generate_challenge()
            assert 4 <= len(result) <= 6

    def test_alphanumeric(self):
        result = generate_challenge()
        assert result.isalnum()

    def test_no_confusable_chars(self):
        for _ in range(100):
            result = generate_challenge()
            assert "O" not in result
            assert "I" not in result
            assert "0" not in result
            assert "1" not in result


class TestCreateChallenge:
    def setup_method(self):
        _pending.clear()

    def test_stores_challenge(self):
        answer, image = create_challenge(100, 200)
        assert (100, 200) in _pending
        assert _pending[(100, 200)]["answer"] == answer

    def test_max_pending_per_chat(self):
        """Creating more than 10 captchas for same chat should remove oldest."""
        for i in range(12):
            create_challenge(100, 200 + i)
        # Only 10 should remain for chat 100
        chat_pending = [k for k in _pending if k[0] == 100]
        assert len(chat_pending) <= 10


class TestSweepExpired:
    def setup_method(self):
        _pending.clear()

    def test_removes_expired(self):
        # Manually insert expired entry
        _pending[(100, 200)] = {
            "answer": "TEST",
            "attempts": 0,
            "sent_at": time.time() - 120,  # 2 minutes ago
        }
        removed = sweep_expired()
        assert removed == 1
        assert (100, 200) not in _pending

    def test_keeps_fresh(self):
        _pending[(100, 200)] = {
            "answer": "TEST",
            "attempts": 0,
            "sent_at": time.time(),
        }
        removed = sweep_expired()
        assert removed == 0
        assert (100, 200) in _pending


class TestVerify:
    def setup_method(self):
        _pending.clear()

    def test_correct_answer(self):
        _pending[(100, 200)] = {
            "answer": "ABC",
            "attempts": 0,
            "sent_at": time.time(),
        }
        result = verify(100, 200, "abc")
        assert result is True
        assert (100, 200) not in _pending

    def test_wrong_answer(self):
        _pending[(100, 200)] = {
            "answer": "ABC",
            "attempts": 0,
            "sent_at": time.time(),
        }
        result = verify(100, 200, "XYZ")
        assert result is False
        assert _pending[(100, 200)]["attempts"] == 1

    def test_no_pending(self):
        result = verify(100, 200, "ABC")
        assert result is None

    def test_expired_returns_none(self):
        _pending[(100, 200)] = {
            "answer": "ABC",
            "attempts": 0,
            "sent_at": time.time() - 120,
        }
        result = verify(100, 200, "ABC")
        assert result is None


class TestHasPending:
    def setup_method(self):
        _pending.clear()

    def test_fresh_pending(self):
        _pending[(100, 200)] = {
            "answer": "ABC",
            "attempts": 0,
            "sent_at": time.time(),
        }
        assert has_pending(100, 200) is True

    def test_no_pending(self):
        assert has_pending(100, 200) is False

    def test_expired_pending(self):
        _pending[(100, 200)] = {
            "answer": "ABC",
            "attempts": 0,
            "sent_at": time.time() - 120,
        }
        assert has_pending(100, 200) is False
        assert (100, 200) not in _pending
