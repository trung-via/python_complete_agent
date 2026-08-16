"""Tests for External Brain ContextBudget and TokenCounter contracts."""
from __future__ import annotations

import pytest

from src.aios_bridge.external_brain import (
    ContextBudget,
    ContractValidationError,
    TokenCounter,
    Utf8ByteConservativeCounter,
)


class FakeExactCounter:
    """Fake exact token counter for testing protocol implementation."""

    @property
    def counter_id(self) -> str:
        return "fake-exact-counter-v1"

    @property
    def is_exact(self) -> bool:
        return True

    def count(self, text: str) -> int:
        return len(text.split())


def test_utf8_conservative_counter_properties_and_determinism():
    """Default counter has stable ID, is_exact=False, and deterministic UTF-8 byte counting."""
    counter = Utf8ByteConservativeCounter()
    assert counter.counter_id == "utf8-byte-conservative-v1"
    assert counter.is_exact is False

    # ASCII
    assert counter.count("hello world") == 11

    # Multibyte Unicode (Vietnamese, Chinese, emoji)
    vn_text = "Xin chào Việt Nam 🇻🇳"
    assert counter.count(vn_text) == len(vn_text.encode("utf-8"))
    assert counter.count(vn_text) == counter.count(vn_text)  # Deterministic

    chinese_text = "你好世界"
    assert counter.count(chinese_text) == len(chinese_text.encode("utf-8"))


def test_token_counter_protocol_conformance():
    """Custom TokenCounter conforms to protocol and exposes exactness."""
    counter: TokenCounter = FakeExactCounter()
    assert counter.counter_id == "fake-exact-counter-v1"
    assert counter.is_exact is True
    assert counter.count("three word text") == 3


def test_context_budget_validation():
    """ContextBudget validates positive max tokens, non-negative reserve, and reserve < max."""
    # Valid
    budget = ContextBudget(max_context_tokens=8000, protocol_reserve_tokens=500)
    assert budget.max_context_tokens == 8000
    assert budget.protocol_reserve_tokens == 500
    assert budget.available_context_tokens == 7500

    # Default reserve is 0
    b_default = ContextBudget(max_context_tokens=4000)
    assert b_default.protocol_reserve_tokens == 0
    assert b_default.available_context_tokens == 4000

    # Non-positive max
    with pytest.raises(ContractValidationError, match="max_context_tokens must be a positive integer"):
        ContextBudget(max_context_tokens=0)

    with pytest.raises(ContractValidationError, match="max_context_tokens must be a positive integer"):
        ContextBudget(max_context_tokens=-100)

    # Boolean max rejected
    with pytest.raises(ContractValidationError, match="max_context_tokens must be a positive integer"):
        ContextBudget(max_context_tokens=True)

    # Negative reserve
    with pytest.raises(ContractValidationError, match="protocol_reserve_tokens must be a non-negative integer"):
        ContextBudget(max_context_tokens=1000, protocol_reserve_tokens=-1)

    # Boolean reserve rejected
    with pytest.raises(ContractValidationError, match="protocol_reserve_tokens must be a non-negative integer"):
        ContextBudget(max_context_tokens=1000, protocol_reserve_tokens=False)

    # Reserve >= max rejected
    with pytest.raises(ContractValidationError, match="must be strictly less than"):
        ContextBudget(max_context_tokens=1000, protocol_reserve_tokens=1000)

    with pytest.raises(ContractValidationError, match="must be strictly less than"):
        ContextBudget(max_context_tokens=1000, protocol_reserve_tokens=1500)


def test_context_budget_to_dict():
    """ContextBudget serializes to a clean dictionary."""
    budget = ContextBudget(max_context_tokens=16000, protocol_reserve_tokens=1000)
    d = budget.to_dict()
    assert d == {
        "max_context_tokens": 16000,
        "protocol_reserve_tokens": 1000,
        "available_context_tokens": 15000,
    }
