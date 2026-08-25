"""Unit tests for ĐỢT 7's Metacognitive Self-Correction Loop:
merge_reflection_into_profile pure logic, submit_reflection API function,
and the /api/debate/reflect FastAPI endpoint."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from eduagent.api import DebateReflectionRequest, submit_reflection
from eduagent.memory.student_profile import empty_profile, merge_reflection_into_profile
from eduagent.auth import create_access_token
from eduagent.server import app

client = TestClient(app)

# ĐỢT 12 NHÓM 2: /api/debate/reflect writes a growth bonus into a student
# profile, so it is now authenticated.
_STUDENT_ID = "c1_stu01"
_STUDENT_HEADERS = {"Authorization": f"Bearer {create_access_token(_STUDENT_ID, 'student', 'c1')}"}


def test_merge_reflection_into_profile_pure_function():
    base = empty_profile(name="Binh", class_id="c1")
    updated = merge_reflection_into_profile(
        base,
        reflection_text="While electric vehicles reduce direct emissions, total impact depends on grid power sources.",
        original_fallacy="hasty generalization",
        resolved=True,
        growth_bonus=0.5,
        timestamp="2026-08-24T12:00:00Z",
    )

    assert len(updated["reflections_history"]) == 1
    assert updated["total_growth_bonus"] == 0.5
    assert updated["breakthrough_count"] == 1
    assert updated["last_reflection"]["resolved"] is True
    assert updated["last_reflection"]["growth_bonus"] == 0.5


def test_merge_reflection_into_profile_accumulates_growth():
    base = empty_profile(name="Binh", class_id="c1")
    p1 = merge_reflection_into_profile(
        base,
        reflection_text="Revision 1",
        original_fallacy="fallacy 1",
        resolved=True,
        growth_bonus=0.5,
        timestamp="2026-08-24T12:00:00Z",
    )
    p2 = merge_reflection_into_profile(
        p1,
        reflection_text="Revision 2",
        original_fallacy="fallacy 2",
        resolved=True,
        growth_bonus=0.5,
        timestamp="2026-08-24T13:00:00Z",
    )

    assert len(p2["reflections_history"]) == 2
    assert p2["total_growth_bonus"] == 1.0
    assert p2["breakthrough_count"] == 2


def test_submit_reflection_evaluates_and_persists():
    fake_llm_result = {
        "resolved": True,
        "growth_bonus": 0.5,
        "feedback": "Excellent nuance added to qualify the environmental claim.",
    }
    with (
        patch("eduagent.llm.generate_json", return_value=fake_llm_result),
        patch("eduagent.memory.firestore_memory.apply_reflection_result") as mock_persist,
    ):
        result = submit_reflection(
            DebateReflectionRequest(
                student_id="s1",
                class_id="c1",
                original_fallacy="hasty generalization",
                original_claim="Electric cars produce zero emissions.",
                revised_claim="Electric cars produce zero tailpipe emissions, though manufacturing and charging impact varies.",
            )
        )

    assert result["resolved"] is True
    assert result["growth_bonus"] == 0.5
    assert "nuance" in result["feedback"]
    mock_persist.assert_called_once()


def test_submit_reflection_degrades_gracefully_on_llm_failure():
    from eduagent.llm import LLMGenerationError

    with (
        patch("eduagent.llm.generate_json", side_effect=LLMGenerationError("Model down")),
        patch("eduagent.memory.firestore_memory.apply_reflection_result") as mock_persist,
    ):
        result = submit_reflection(
            DebateReflectionRequest(
                student_id="s1",
                class_id="c1",
                revised_claim="Valid revised claim.",
            )
        )

    assert result["resolved"] is True
    assert result["growth_bonus"] == 0.5
    assert "recorded" in result["feedback"]
    mock_persist.assert_called_once()


def test_submit_reflection_rejects_oversized_claim():
    oversized = "X" * 4001
    with pytest.raises(ValueError, match="too long"):
        submit_reflection(
            DebateReflectionRequest(
                student_id="s1",
                revised_claim=oversized,
            )
        )


def test_api_debate_reflect_endpoint():
    fake_llm_result = {"resolved": True, "growth_bonus": 0.5, "feedback": "Great revision!"}
    with (
        patch("eduagent.llm.generate_json", return_value=fake_llm_result),
        patch("eduagent.memory.firestore_memory.apply_reflection_result"),
    ):
        response = client.post(
            "/api/debate/reflect",
            json={
                "student_id": _STUDENT_ID,
                "class_id": "c1",
                "original_fallacy": "hasty generalization",
                "original_claim": "Claim A",
                "revised_claim": "Revised Claim A with strong evidence.",
            },
            headers=_STUDENT_HEADERS,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["resolved"] is True
    assert body["growth_bonus"] == 0.5
    assert body["feedback"] == "Great revision!"


def test_api_debate_reflect_endpoint_rejects_oversized():
    oversized = "Z" * 4001
    response = client.post(
        "/api/debate/reflect",
        json={"student_id": _STUDENT_ID, "class_id": "c1", "revised_claim": oversized},
        headers=_STUDENT_HEADERS,
    )
    assert response.status_code == 400
