"""
单元测试 — message_processor 中的纯函数（无外部依赖）
覆盖：_normalize_profile_key, _normalize_profile_updates
"""
import pytest
from bot_app.message_processor import (
    _normalize_profile_key,
    _normalize_profile_updates,
)


# ── _normalize_profile_key ────────────────────────────────────────────────

class TestNormalizeProfileKey:
    def test_standard_key_passthrough(self):
        assert _normalize_profile_key("self_name") == "self_name"

    def test_spaces_converted(self):
        result = _normalize_profile_key("son name")
        assert result == "son_name"

    def test_uppercase_lowercased(self):
        assert _normalize_profile_key("SelfName") == "selfname"

    def test_non_string_returns_none(self):
        assert _normalize_profile_key(123) is None
        assert _normalize_profile_key(None) is None

    def test_empty_string_returns_none(self):
        assert _normalize_profile_key("") is None

    def test_starts_with_digit_invalid(self):
        assert _normalize_profile_key("1abc") is None


# ── _normalize_profile_updates ────────────────────────────────────────────

class TestNormalizeProfileUpdates:
    def test_standard_keys(self):
        result = _normalize_profile_updates({"self_name": "张三", "current_city": "上海"})
        assert result == {"self_name": "张三", "current_city": "上海"}

    def test_none_value_dropped(self):
        result = _normalize_profile_updates({"self_name": None})
        assert result == {}

    def test_empty_string_dropped(self):
        result = _normalize_profile_updates({"self_name": "   "})
        assert result == {}

    def test_invalid_key_dropped(self):
        result = _normalize_profile_updates({"1invalid": "value"})
        assert result == {}

    def test_empty_input(self):
        assert _normalize_profile_updates({}) == {}
