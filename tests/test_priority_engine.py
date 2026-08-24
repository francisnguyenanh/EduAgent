"""Unit tests for the deterministic Class Cluster & Pattern Engine.

No Firestore, no LLM -- builds profiles with the same pure merge function
used elsewhere so the fixtures stay realistic without a live connection.
"""

from __future__ import annotations

from datetime import datetime, timezone

from eduagent.aggregator.priority_engine import (
    cluster_fallacies,
    common_fallacies,
    compute_priority,
    rank_students,
)
from eduagent.memory.student_profile import empty_profile, merge_essay_into_profile

NOW = datetime(2026, 8, 24, tzinfo=timezone.utc)


def _scores(avg: int) -> dict:
    return {"logical_coherence": avg, "evidence_quality": avg, "counterargument_handling": avg, "scope_awareness": avg}


def _essay(profile, i, ts, persona, avg, weaknesses):
    return merge_essay_into_profile(
        profile, essay_id=f"e{i}", timestamp=ts, persona_used=persona, scores=_scores(avg), weakness_detected=weaknesses
    )


def test_cluster_fallacies_counts_students_not_essays():
    stuck = empty_profile(name="Binh", class_id="c1")
    stuck = _essay(stuck, 0, "2026-08-01T00:00:00+00:00", "skeptic", 5, ["hasty generalization"])
    stuck = _essay(stuck, 1, "2026-08-08T00:00:00+00:00", "skeptic", 5, ["hasty generalization"])

    common = empty_profile(name="Em", class_id="c1")
    common = _essay(common, 0, "2026-08-10T00:00:00+00:00", "devils_advocate", 6, ["hasty generalization"])

    clusters = cluster_fallacies({"stu_stuck": stuck, "stu_common": common})
    # Both students share it -> counted once per student, not twice for stuck's 2 essays.
    assert clusters["hasty generalization"] == ["stu_common", "stu_stuck"]


def test_common_fallacies_requires_minimum_students():
    clusters = {"hasty generalization": ["a", "b"], "ad hominem": ["a"]}
    assert common_fallacies(clusters) == ["hasty generalization"]


def test_compute_priority_stuck_streak_dominates():
    stuck_profile = empty_profile(name="Binh", class_id="c1")
    for i in range(4):
        stuck_profile = _essay(stuck_profile, i, f"2026-08-{i+1:02d}T00:00:00+00:00", "skeptic", 5, [])

    fine_profile = empty_profile(name="Mai", class_id="c1")
    fine_profile = _essay(fine_profile, 0, "2026-08-20T00:00:00+00:00", "expander", 8, [])

    stuck_result = compute_priority(stuck_profile, now=NOW, common_fallacy_set=set())
    fine_result = compute_priority(fine_profile, now=NOW, common_fallacy_set=set())
    assert stuck_result["total"] > fine_result["total"]
    assert stuck_result["reason"]["stuck_streak_count"] == 3


def test_compute_priority_inactivity_component_present():
    inactive_profile = empty_profile(name="Duc", class_id="c1")
    inactive_profile = _essay(inactive_profile, 0, "2026-07-01T00:00:00+00:00", "skeptic", 5, [])

    result = compute_priority(inactive_profile, now=NOW, common_fallacy_set=set())
    assert result["reason"]["inactivity_days"] > 0
    assert result["breakdown"]["inactivity"] > 0


def test_compute_priority_declining_trend_adds_component():
    declining = empty_profile(name="Chi", class_id="c1")
    declining = _essay(declining, 0, "2026-08-01T00:00:00+00:00", "devils_advocate", 8, [])
    declining = _essay(declining, 1, "2026-08-08T00:00:00+00:00", "nitpicker", 6, [])
    declining = _essay(declining, 2, "2026-08-15T00:00:00+00:00", "expander", 3, [])

    result = compute_priority(declining, now=NOW, common_fallacy_set=set())
    assert result["reason"]["score_trend"] == "declining"
    assert result["breakdown"]["score_decline"] > 0


def test_rank_students_sorted_highest_priority_first():
    stuck = empty_profile(name="Binh", class_id="c1")
    for i in range(4):
        stuck = _essay(stuck, i, f"2026-08-{i+1:02d}T00:00:00+00:00", "skeptic", 5, ["hasty generalization"])

    thriving = empty_profile(name="Mai", class_id="c1")
    thriving = _essay(thriving, 0, "2026-08-22T00:00:00+00:00", "expander", 9, [])

    ranked = rank_students({"stu_stuck": stuck, "stu_thriving": thriving}, now=NOW)
    assert [r["student_id"] for r in ranked] == ["stu_stuck", "stu_thriving"]
    assert ranked[0]["priority"] > ranked[1]["priority"]


def test_rank_students_ties_broken_deterministically():
    a = empty_profile(name="A", class_id="c1")
    b = empty_profile(name="B", class_id="c1")
    # Identical empty profiles -> identical priority (0) -> tie broken by student_id.
    ranked = rank_students({"stu_b": b, "stu_a": a}, now=NOW)
    assert [r["student_id"] for r in ranked] == ["stu_a", "stu_b"]
