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


# --- ADR-028: Gemma MaaS backpressure -------------------------------------


def _client_error(code: int):
    """A genai ClientError without going through its HTTP-response constructor."""
    from google.genai import errors as genai_errors

    exc = genai_errors.ClientError.__new__(genai_errors.ClientError)
    Exception.__init__(exc, f"{code} error")
    exc.code = code
    return exc


def test_maas_queue_full_recognises_429_only():
    """429 from a shared MaaS pool means 'come back in a second'. Every other
    4xx means the request itself is wrong and will fail identically forever --
    retrying those would just burn the budget, which is why the module-wide
    policy excludes ClientError. This predicate is the narrow exception."""
    from eduagent.llm import _is_maas_queue_full

    assert _is_maas_queue_full(_client_error(429)) is True
    assert _is_maas_queue_full(_client_error(400)) is False
    assert _is_maas_queue_full(_client_error(404)) is False
    assert _is_maas_queue_full(ValueError("not an API error")) is False


def test_generate_text_from_image_retries_429_then_succeeds():
    """Measured reality this exists for: 4 of 10 raw Gemma calls returned 429
    during Wave 24 integration testing, yet all 6 test images transcribed
    successfully once retried."""
    from unittest.mock import MagicMock, patch

    import eduagent.llm as llm

    fake = MagicMock()
    fake.models.generate_content.side_effect = [
        _client_error(429),
        _client_error(429),
        MagicMock(text="  transcribed at last  "),
    ]
    with patch.object(llm, "_gemma_client", return_value=fake), patch("time.sleep", return_value=None):
        out = llm.generate_text_from_image(model="gemma-x", prompt="p", image_bytes=b"i", image_mime_type="image/png")

    assert out == "transcribed at last"
    assert fake.models.generate_content.call_count == 3


def test_generate_text_from_image_gives_up_as_LLMGenerationError_not_raw_429():
    """The caller (ocr.py) falls back on LLMGenerationError. If a raw
    ClientError escaped instead, the fallback would never run and a busy
    shared queue would fail a student's submission."""
    from unittest.mock import MagicMock, patch

    import pytest

    import eduagent.llm as llm

    fake = MagicMock()
    fake.models.generate_content.side_effect = _client_error(429)
    with patch.object(llm, "_gemma_client", return_value=fake), patch("time.sleep", return_value=None):
        with pytest.raises(llm.LLMGenerationError):
            llm.generate_text_from_image(model="gemma-x", prompt="p", image_bytes=b"i", image_mime_type="image/png")
