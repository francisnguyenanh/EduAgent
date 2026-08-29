"""Unit tests for the Class Aggregator orchestration -- mocks every external
call (Firestore, Gmail, Sheets, LLM) so this suite runs fast and offline.
Real end-to-end wiring is verified separately via scripts/demo_tier2_run.py
against live GCP services.
"""

from __future__ import annotations

import asyncio
import logging
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
    """This HTML is no longer Gmail-only -- it is also injected into
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
        patch("eduagent.integrations.gmail_mcp.create_digest_draft", return_value={"draft_id": "draft123", "message_id": "1a04055b6640d946"}) as mock_gmail,
        patch("eduagent.integrations.sheets_mcp.append_audit_row") as mock_sheets_append,
        patch("eduagent.aggregator.class_aggregator.persist_digest") as mock_persist_digest,
        patch("eduagent.aggregator.class_aggregator.get_last_digest_timestamp", return_value=None),
        patch("eduagent.aggregator.class_aggregator.get_class_settings", return_value={}),
    ):
        mock_teacher.email = "teacher@example.com"
        mock_sheets.audit_spreadsheet_id = "sheet123"

        result = asyncio.run(process_event({"event_id": "e3", "student_id": "stu_stuck", "class_id": "c1", "essay_id": "e1"}))

    assert result["status"] == "processed"
    assert result["gmail_draft_id"] == "draft123"
    # The hex message id is carried separately -- Gmail's web UI
    # addresses drafts by that, not by the API draft id, so collapsing the two
    # gives the teacher a link that opens an empty compose window.
    assert result["gmail_draft_message_id"] == "1a04055b6640d946"
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
        patch("eduagent.aggregator.class_aggregator.get_class_settings", return_value={}),
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


# --- ADR-031: WHY the Gmail draft is missing, not just THAT it is ---
# Judging runs for a month and a Gmail refresh token can expire inside that
# window. Before this, both causes rendered the same dashboard badge ("no
# recipient configured"), so a teacher with an address in their Settings box was
# shown a message their own screen contradicted.


def _run_with_gmail(gmail_patch, teacher_email="teacher@example.com", class_settings=None):
    with (
        patch("eduagent.aggregator.class_aggregator.claim_event", return_value=True),
        patch("eduagent.aggregator.class_aggregator.load_class_profiles", return_value=_FAKE_PROFILES),
        patch("eduagent.aggregator.class_aggregator.synthesize_digest", new_callable=AsyncMock, return_value=_FAKE_DIGEST),
        patch("eduagent.aggregator.class_aggregator.TEACHER") as mock_teacher,
        patch("eduagent.aggregator.class_aggregator.SHEETS") as mock_sheets,
        patch("eduagent.aggregator.class_aggregator.persist_digest") as mock_persist,
        patch("eduagent.aggregator.class_aggregator.get_last_digest_timestamp", return_value=None),
        patch("eduagent.aggregator.class_aggregator.get_class_settings", return_value=class_settings or {}),
        gmail_patch,
    ):
        mock_teacher.email = teacher_email
        mock_sheets.audit_spreadsheet_id = ""
        result = asyncio.run(process_event({"event_id": "e_status", "student_id": "stu_stuck", "class_id": "c1", "essay_id": "e1"}))
    return result, mock_persist


def test_gmail_draft_status_is_created_on_success():
    gmail = patch("eduagent.integrations.gmail_mcp.create_digest_draft", return_value={"draft_id": "d1", "message_id": "1a04055b6640d946"})
    result, mock_persist = _run_with_gmail(gmail)

    assert result["gmail_draft_status"] == "created"
    assert mock_persist.call_args.kwargs["gmail_draft_status"] == "created"


def test_gmail_draft_status_is_failed_when_the_token_is_dead():
    """An expired/revoked OAuth refresh token is the realistic month-two
    failure. The digest must still be composed and stored, and the status must
    say `failed` -- NOT `no_recipient`, which would blame a recipient that is
    plainly configured."""
    gmail = patch(
        "eduagent.integrations.gmail_mcp.create_digest_draft",
        side_effect=Exception("invalid_grant: Token has been expired or revoked."),
    )
    result, mock_persist = _run_with_gmail(gmail)

    assert result["status"] == "processed"  # the digest itself survives
    assert result["digest"]["headline"]  # and still carries its analysis
    assert result["gmail_draft_id"] is None
    assert result["gmail_draft_status"] == "failed"
    assert result["gmail_draft_status"] != "no_recipient"
    assert mock_persist.call_args.kwargs["gmail_draft_status"] == "failed"


def test_gmail_draft_status_is_no_recipient_when_no_address_is_configured():
    gmail = patch("eduagent.integrations.gmail_mcp.create_digest_draft")
    result, mock_persist = _run_with_gmail(gmail, teacher_email="")

    assert result["gmail_draft_status"] == "no_recipient"
    assert mock_persist.call_args.kwargs["gmail_draft_status"] == "no_recipient"


# ---------------------------------------------------------------------------
# The Teacher Settings tab actually reaching the digest path.
#
# `class_aggregator.py` CALLED get_class_settings() without importing it, so
# every call raised NameError into a bare `except: pass`. The teacher's saved
# `digest_notify_email` / `audit_spreadsheet_id` were therefore dead on the
# only path that consumes them, while the Settings UI showed them saved and
# `POST /api/classes/{id}/test-sheets` (which imports correctly, via api.py)
# reported the Sheet as reachable. Nothing failed loudly; drafts simply always
# went to the deployment-wide TEACHER.email.
#
# These tests bind the fix to behaviour rather than to the import line: they
# assert the *override wins over the deployment default*, which is false for
# both the NameError version and any future refactor that drops the read.
# ---------------------------------------------------------------------------


def _run_and_capture_recipient(*, teacher_email, class_settings):
    """Runs a full process_event and hands back the address the Gmail draft was
    actually addressed to -- the one observable that separates a working
    Settings read from the NameError version."""
    with (
        patch("eduagent.aggregator.class_aggregator.claim_event", return_value=True),
        patch("eduagent.aggregator.class_aggregator.load_class_profiles", return_value=_FAKE_PROFILES),
        patch("eduagent.aggregator.class_aggregator.synthesize_digest", new_callable=AsyncMock, return_value=_FAKE_DIGEST),
        patch("eduagent.aggregator.class_aggregator.TEACHER") as mock_teacher,
        patch("eduagent.aggregator.class_aggregator.SHEETS") as mock_sheets,
        patch("eduagent.aggregator.class_aggregator.persist_digest"),
        patch("eduagent.aggregator.class_aggregator.get_last_digest_timestamp", return_value=None),
        patch("eduagent.aggregator.class_aggregator.get_class_settings", return_value=class_settings),
        patch(
            "eduagent.integrations.gmail_mcp.create_digest_draft",
            return_value={"draft_id": "d1", "message_id": "1a04055b6640d946"},
        ) as mock_gmail,
    ):
        mock_teacher.email = teacher_email
        mock_sheets.audit_spreadsheet_id = ""
        result = asyncio.run(process_event({"event_id": "e_recipient", "student_id": "stu_stuck", "class_id": "c1", "essay_id": "e1"}))
    return result, mock_gmail


def test_class_settings_digest_email_overrides_the_deployment_wide_default():
    """The address a teacher typed into Settings must win over TEACHER.email."""
    result, mock_gmail = _run_and_capture_recipient(
        teacher_email="deployment-default@example.com",
        class_settings={"digest_notify_email": "teacher-typed-this@example.com"},
    )

    assert result["gmail_draft_status"] == "created"
    assert mock_gmail.call_args.kwargs["to_address"] == "teacher-typed-this@example.com"


def test_class_settings_absent_falls_back_to_the_deployment_wide_default():
    """The fallback is deliberate, not accidental -- a class with no Settings
    saved still gets its digest delivered."""
    result, mock_gmail = _run_and_capture_recipient(
        teacher_email="deployment-default@example.com",
        class_settings={"digest_notify_email": ""},
    )

    assert result["gmail_draft_status"] == "created"
    assert mock_gmail.call_args.kwargs["to_address"] == "deployment-default@example.com"


def test_class_settings_audit_spreadsheet_overrides_the_deployment_wide_sheet():
    """Same defect, second field: the per-class audit Sheet was equally dead."""
    with (
        patch("eduagent.aggregator.class_aggregator.claim_event", return_value=True),
        patch("eduagent.aggregator.class_aggregator.load_class_profiles", return_value=_FAKE_PROFILES),
        patch("eduagent.aggregator.class_aggregator.synthesize_digest", new_callable=AsyncMock, return_value=_FAKE_DIGEST),
        patch("eduagent.aggregator.class_aggregator.TEACHER") as mock_teacher,
        patch("eduagent.aggregator.class_aggregator.SHEETS") as mock_sheets,
        patch("eduagent.aggregator.class_aggregator.persist_digest"),
        patch("eduagent.aggregator.class_aggregator.get_last_digest_timestamp", return_value=None),
        patch(
            "eduagent.aggregator.class_aggregator.get_class_settings",
            return_value={"audit_spreadsheet_id": "sheet_from_settings"},
        ),
        patch("eduagent.integrations.gmail_mcp.create_digest_draft", return_value={"draft_id": "d1", "message_id": "abc"}),
        patch("eduagent.integrations.sheets_mcp.append_audit_row") as mock_append,
    ):
        mock_teacher.email = "teacher@example.com"
        mock_sheets.audit_spreadsheet_id = "sheet_from_deployment"
        result = asyncio.run(process_event({"event_id": "e_sheet", "student_id": "stu_stuck", "class_id": "c1", "essay_id": "e1"}))

    assert result["status"] == "processed"
    mock_append.assert_called_once()
    assert mock_append.call_args.kwargs["spreadsheet_id"] == "sheet_from_settings"


def test_class_settings_failure_is_logged_not_swallowed_silently(caplog):
    """The NameError survived because nothing ever reported it. A Firestore
    outage on this read must degrade to the deployment default AND say so."""
    with (
        caplog.at_level(logging.ERROR, logger="eduagent.aggregator.class_aggregator"),
        patch("eduagent.aggregator.class_aggregator.claim_event", return_value=True),
        patch("eduagent.aggregator.class_aggregator.load_class_profiles", return_value=_FAKE_PROFILES),
        patch("eduagent.aggregator.class_aggregator.synthesize_digest", new_callable=AsyncMock, return_value=_FAKE_DIGEST),
        patch("eduagent.aggregator.class_aggregator.TEACHER") as mock_teacher,
        patch("eduagent.aggregator.class_aggregator.SHEETS") as mock_sheets,
        patch("eduagent.aggregator.class_aggregator.persist_digest"),
        patch("eduagent.aggregator.class_aggregator.get_last_digest_timestamp", return_value=None),
        patch(
            "eduagent.aggregator.class_aggregator.get_class_settings",
            side_effect=RuntimeError("Firestore unavailable"),
        ),
        patch(
            "eduagent.integrations.gmail_mcp.create_digest_draft",
            return_value={"draft_id": "d1", "message_id": "1a04055b6640d946"},
        ) as mock_gmail,
    ):
        mock_teacher.email = "deployment-default@example.com"
        mock_sheets.audit_spreadsheet_id = ""
        result = asyncio.run(process_event({"event_id": "e_settings_down", "student_id": "stu_stuck", "class_id": "c1", "essay_id": "e1"}))

    assert result["status"] == "processed"
    assert mock_gmail.call_args.kwargs["to_address"] == "deployment-default@example.com"
    assert any("get_class_settings failed" in r.message for r in caplog.records)
