"""Tests for services/ai_moderation.py — memory leak fix."""

import time
from services.ai_moderation import _last_call_times, _prune_last_calls, _MAX_TRACKED_CHATS, _MAX_CALL_AGE


class TestPruneLastCalls:
    def setup_method(self):
        _last_call_times.clear()

    def test_max_call_age_5_minutes(self):
        assert _MAX_CALL_AGE == 300.0

    def test_removes_stale_entries(self):
        now = time.time()
        _last_call_times[1] = now - 400  # older than 5 min
        _last_call_times[2] = now - 100  # fresh
        _prune_last_calls(now)
        assert 1 not in _last_call_times
        assert 2 in _last_call_times

    def test_lru_eviction_at_capacity(self):
        now = time.time()
        # Fill to capacity + 1
        for i in range(_MAX_TRACKED_CHATS + 10):
            _last_call_times[i] = now - (i * 10)  # older = evicted first
        _prune_last_calls(now)
        assert len(_last_call_times) <= _MAX_TRACKED_CHATS
