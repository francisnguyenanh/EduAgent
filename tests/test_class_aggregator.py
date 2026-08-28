"""Unit tests for the Class Aggregator orchestration -- mocks every external
call (Firestore, Gmail, Sheets, LLM) so this suite runs fast and offline.
Real end-to-end wiring is verified separately via scripts/demo_tier2_run.py
against live GCP services.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from eduagent.aggregator.class_aggregator import format_digest_email, format_digest_email_html, process_event, should_coalesce_digest

_FAKE_DIGEST = {
    "headline": "Binh needs attention.",
    "priority_students": [{"student_id": "stu_stuck", "why": "stuck streak"}],
    "class_wide_pattern": "hasty generalization is common.",
    "mini_lesson_suggestion": "Do a 15-minute exercise.",
}

_FAKE_PROFILES = {
    "stu_stuck": {
        "name": "Binh",
        "class_id": "c1",
        "essay_history": [
            {"essay_id": "e1", "timestamp": "2026-08-01T00:00:00+00:00", "persona_used": "skeptic", "scores": {"logical_coherence": 5, "evidence_quality": 5, "counterargument_handling": 5, "scope_awareness": 5}, "avg_score": 5, "weakness_detected": ["hasty generalization"]}
        ],
        "persona_streak": {"current_persona": "skeptic", "times_repeated_without_improvement": 3},
        "flags": {"needs_attention": True, "reason": "stuck", "last_updated": "2026-08-01T00:00:00+00:00"},
        "score_trend": "stagnant",
    }
}


def test_format_digest_email_includes_all_sections():
    text = format_digest_email(_FAKE_DIGEST)
    assert "Binh needs attention." in text
    assert "stu_stuck" in text
    assert "hasty generalization is common." in text
    assert "15-minute exercise" in text


def test_format_digest_email_resolves_human_friendly_name():
    text = format_digest_email(_FAKE_DIGEST, name_by_id={"stu_stuck": "Binh"})
    assert "Binh (stu_stuck)" in text


def test_format_digest_email_html_includes_table_and_mini_lesson():
    ranked = [{"student_id": "stu_stuck", "name": "Binh", "priority": 9.0, "breakdown": {}, "reason": {"stuck_streak_count": 3, "score_trend": "stagnant", "inactivity_days": 0, "shared_fallacies": []}}]
    html = format_digest_email_html(_FAKE_DIGEST, ranked, name_by_id={"stu_stuck": "Binh"})
    assert "<table" in html
    assert "Binh (stu_stuck)" in html
    assert "stuck streak" in html
    assert "15-minute exercise" in html


def test_format_digest_email_html_escapes_model_generated_text():
    """ĐỢT 26 #1.3: this HTML is no longer Gmail-only -- it is also injected into
    the Teacher Dashboard preview. Gmail sanitizes; our own origin does not, so
    markup arriving in an LLM-written field must come out inert.

    Sabotage check: drop `_h(...)` from the `why` cell and this goes red."""
    digest = {
        "headline": "<b>headline</b>",
        "priority_students": [{"student_id": "s1", "why": "<script>alert(1)</script>"}],
        "class_wide_pattern": "cause & effect",
        "mini_lesson_suggestion": "compare <a> and <b>",
    }
    html = format_digest_email_html(digest, [{"student_id": "s1", "priority": 9.0, "reason": {}}])

    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<b>headline</b>" not in html
    assert "cause &amp; effect" in html
    # The chrome the function itself writes must survive escaping.
    assert "<table" in html


def test_process_event_skips_duplicate_delivery():
    with patch("eduagent.aggregator.class_aggregator.claim_event", return_value=False):
        result = asyncio.run(process_event({"event_id": "e1", "student_id": "s1", "class_id": "c1", "essay_id": "e1"}))
    assert result == {"status": "skipped_duplicate", "event_id": "e1"}


def test_process_event_handles_empty_class():
    with (
        patch("eduagent.aggregator.class_aggregator.claim_event", return_value=True),
        patch("eduagent.aggregator.class_aggregator.load_class_profiles", return_value={}),
    ):
        result = asyncio.run(process_event({"event_id": "e2", "student_id": "s1", "class_id": "c1", "essay_id": "e1"}))
    assert result["status"] == "no_profiles"


def test_process_event_full_happy_path_calls_gmail_and_sheets():
    with (
        patch("eduagent.aggregator.class_aggregator.claim_event", return_value=True),
        patch("eduagent.aggregator.class_aggregator.load_class_profiles", return_value=_FAKE_PROFILES),
        patch("eduagent.aggregator.class_aggregator.synthesize_digest", new_callable=AsyncMock, return_value=_FAKE_DIGEST),
        patch("eduagent.aggregator.class_aggregator.TEACHER") as mock_teacher,
        patch("eduagent.aggregator.class_aggregator.SHEETS") as mock_sheets,
        patch("eduagent.integrations.gmail_mcp.create_digest_draft", return_value="draft123") as mock_gmail,
        patch("eduagent.integrations.sheets_mcp.append_audit_row") as mock_sheets_append,
        patch("eduagent.aggregator.class_aggregator.persist_digest") as mock_persist_digest,
        patch("eduagent.aggregator.class_aggregator.get_last_digest_timestamp", return_value=None),
    ):
        mock_teacher.email = "teacher@example.com"
        mock_sheets.audit_spreadsheet_id = "sheet123"

        result = asyncio.run(process_event({"event_id": "e3", "student_id": "stu_stuck", "class_id": "c1", "essay_id": "e1"}))

    assert result["status"] == "processed"
    assert result["gmail_draft_id"] == "draft123"
    assert result["ranked_students"][0]["student_id"] == "stu_stuck"
    mock_gmail.assert_called_once()
    mock_sheets_append.assert_called_once()
    mock_persist_digest.assert_called_once()
    assert mock_persist_digest.call_args.kwargs["class_id"] == "c1"
    assert mock_persist_digest.call_args.kwargs["digest_id"] == "e3"
    # Sheets audit row should use the human-friendly name, not the raw id.
    sheets_row = mock_sheets_append.call_args.kwargs["row"]
    assert "Binh (stu_stuck)" in sheets_row[4]
    # Gmail draft should carry both a plain-text and an HTML body.
    gmail_kwargs = mock_gmail.call_args.kwargs
    assert "Binh (stu_stuck)" in gmail_kwargs["body_text"]
    assert "<table" in gmail_kwargs["body_html"]


def test_process_event_skips_gmail_and_sheets_when_unconfigured():
    with (
        patch("eduagent.aggregator.class_aggregator.claim_event", return_value=True),
        patch("eduagent.aggregator.class_aggregator.load_class_profiles", return_value=_FAKE_PROFILES),
        patch("eduagent.aggregator.class_aggregator.synthesize_digest", new_callable=AsyncMock, return_value=_FAKE_DIGEST),
        patch("eduagent.aggregator.class_aggregator.TEACHER") as mock_teacher,
        patch("eduagent.aggregator.class_aggregator.SHEETS") as mock_sheets,
        patch("eduagent.aggregator.class_aggregator.persist_digest"),
        patch("eduagent.aggregator.class_aggregator.get_last_digest_timestamp", return_value=None),
    ):
        mock_teacher.email = ""
        mock_sheets.audit_spreadsheet_id = ""

        result = asyncio.run(process_event({"event_id": "e4", "student_id": "stu_stuck", "class_id": "c1", "essay_id": "e1"}))

    assert result["status"] == "processed"
    assert result["gmail_draft_id"] is None


def test_should_coalesce_digest_within_window():
    from datetime import datetime, timedelta, timezone

    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    last_digest_at = now - timedelta(seconds=30)
    assert should_coalesce_digest(last_digest_at=last_digest_at, now=now, window_seconds=120) is True


def test_should_coalesce_digest_outside_window():
    from datetime import datetime, timedelta, timezone

    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    last_digest_at = now - timedelta(seconds=300)
    assert should_coalesce_digest(last_digest_at=last_digest_at, now=now, window_seconds=120) is False


def test_should_coalesce_digest_no_prior_digest():
    from datetime import datetime, timezone

    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert should_coalesce_digest(last_digest_at=None, now=now, window_seconds=120) is False


def test_process_event_coalesces_digest_within_debounce_window():
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    recent_digest_at = now - timedelta(seconds=10)

    with (
        patch("eduagent.aggregator.class_aggregator.claim_event", return_value=True),
        patch("eduagent.aggregator.class_aggregator.load_class_profiles", return_value=_FAKE_PROFILES),
        patch("eduagent.aggregator.class_aggregator.get_last_digest_timestamp", return_value=recent_digest_at),
        patch("eduagent.aggregator.class_aggregator.synthesize_digest", new_callable=AsyncMock) as mock_synthesize,
    ):
        result = asyncio.run(process_event({"event_id": "e5", "student_id": "stu_stuck", "class_id": "c1", "essay_id": "e1"}))

    assert result["status"] == "coalesced_skip_digest"
    mock_synthesize.assert_not_awaited()  # never even got to the expensive LLM digest call
