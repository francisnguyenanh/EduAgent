"""Unit tests for deterministic language detection -- ZERO LLM (skills/language.py)."""

from __future__ import annotations

from eduagent.skills.language import detect_language, language_instruction


def test_detects_vietnamese_from_diacritics():
    text = "Học sinh không nên có bài tập về nhà vì nó chiếm mất thời gian rảnh."
    assert detect_language(text) == "vi"


def test_detects_english_plain_text():
    text = "Students should not have homework because it takes away free time."
    assert detect_language(text) == "en"


def test_single_stray_accent_does_not_flip_to_vietnamese():
    # One borrowed/foreign name shouldn't misclassify an otherwise-English essay.
    text = "My friend Nguyễn moved here last year and loves reading."
    assert detect_language(text) == "en"


def test_empty_text_defaults_to_english():
    assert detect_language("") == "en"


def test_language_instruction_names_the_language():
    assert "Vietnamese" in language_instruction("vi")
    assert "English" in language_instruction("en")
