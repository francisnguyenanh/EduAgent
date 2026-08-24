"""Unit tests for eduagent.llm helpers -- no network calls."""

from __future__ import annotations

from eduagent.llm import _strip_markdown_fence


def test_strip_markdown_fence_removes_json_fence():
    text = '```json\n{"a": 1}\n```'
    assert _strip_markdown_fence(text) == '{"a": 1}'


def test_strip_markdown_fence_removes_bare_fence():
    text = '```\n{"a": 1}\n```'
    assert _strip_markdown_fence(text) == '{"a": 1}'


def test_strip_markdown_fence_leaves_bare_json_untouched():
    text = '{"a": 1}'
    assert _strip_markdown_fence(text) == '{"a": 1}'
