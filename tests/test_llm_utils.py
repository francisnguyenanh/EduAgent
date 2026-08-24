"""Unit tests for eduagent.llm helpers -- no network calls."""

from __future__ import annotations

from eduagent.llm import _config_with_thinking_budget, _strip_markdown_fence


def test_strip_markdown_fence_removes_json_fence():
    text = '```json\n{"a": 1}\n```'
    assert _strip_markdown_fence(text) == '{"a": 1}'


def test_strip_markdown_fence_removes_bare_fence():
    text = '```\n{"a": 1}\n```'
    assert _strip_markdown_fence(text) == '{"a": 1}'


def test_strip_markdown_fence_leaves_bare_json_untouched():
    text = '{"a": 1}'
    assert _strip_markdown_fence(text) == '{"a": 1}'


def test_config_with_thinking_budget_none_leaves_config_unchanged():
    config = {"system_instruction": "x"}
    assert _config_with_thinking_budget(config, None) == {"system_instruction": "x"}


def test_config_with_thinking_budget_zero_adds_thinking_config():
    config = {"system_instruction": "x"}
    result = _config_with_thinking_budget(config, 0)
    assert result == {"system_instruction": "x", "thinking_config": {"thinking_budget": 0}}
    assert config == {"system_instruction": "x"}  # original not mutated
