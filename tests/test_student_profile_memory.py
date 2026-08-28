"""Unit tests for the pure profile-merge logic (no Firestore, no network).

Locks in the "stuck persona streak" and "needs_attention" flagging rules
that Phase 3's Class Aggregator will depend on.
"""

from __future__ import annotations

from eduagent.memory.student_profile import (
    MAX_HISTORY_ENTRIES,
    empty_profile,
    merge_essay_into_profile,
    persona_history_from_profile,
    weakness_taxonomy_from_profile,
)


def _scores(avg: int) -> dict:
    return {"logical_coherence": avg, "evidence_quality": avg, "counterargument_handling": avg, "scope_awareness": avg}


def test_first_essay_starts_streak_at_zero():
    profile = empty_profile(name="An", class_id="c1")
    updated = merge_essay_into_profile(
        profile,
        essay_id="e1",
        timestamp="t1",
        persona_used="skeptic",
        scores=_scores(5),
        weakness_detected=["unsourced claim"],
    )
    assert updated["persona_streak"] == {"current_persona": "skeptic", "times_repeated_without_improvement": 0}
    assert updated["flags"]["needs_attention"] is False


def test_same_persona_no_improvement_increments_streak():
    profile = empty_profile(name="An", class_id="c1")
    profile = merge_essay_into_profile(profile, essay_id="e1", timestamp="t1", persona_used="skeptic", scores=_scores(5), weakness_detected=[])
    profile = merge_essay_into_profile(profile, essay_id="e2", timestamp="t2", persona_used="skeptic", scores=_scores(5), weakness_detected=[])
    profile = merge_essay_into_profile(profile, essay_id="e3", timestamp="t3", persona_used="skeptic", scores=_scores(4), weakness_detected=[])

    assert profile["persona_streak"]["times_repeated_without_improvement"] == 2
    assert profile["flags"]["needs_attention"] is False  # threshold is 3


def test_streak_hits_threshold_triggers_needs_attention():
    profile = empty_profile(name="An", class_id="c1")
    for i in range(4):
        profile = merge_essay_into_profile(
            profile, essay_id=f"e{i}", timestamp=f"t{i}", persona_used="skeptic", scores=_scores(5), weakness_detected=[]
        )
    assert profile["persona_streak"]["times_repeated_without_improvement"] == 3
    assert profile["flags"]["needs_attention"] is True
    assert "skeptic" in profile["flags"]["reason"]


def test_improvement_resets_streak():
    profile = empty_profile(name="An", class_id="c1")
    profile = merge_essay_into_profile(profile, essay_id="e1", timestamp="t1", persona_used="skeptic", scores=_scores(3), weakness_detected=[])
    profile = merge_essay_into_profile(profile, essay_id="e2", timestamp="t2", persona_used="skeptic", scores=_scores(3), weakness_detected=[])
    # Improved score -> streak resets even though persona is the same.
    profile = merge_essay_into_profile(profile, essay_id="e3", timestamp="t3", persona_used="skeptic", scores=_scores(8), weakness_detected=[])
    assert profile["persona_streak"]["times_repeated_without_improvement"] == 0


def test_persona_switch_resets_streak():
    profile = empty_profile(name="An", class_id="c1")
    profile = merge_essay_into_profile(profile, essay_id="e1", timestamp="t1", persona_used="skeptic", scores=_scores(5), weakness_detected=[])
    profile = merge_essay_into_profile(profile, essay_id="e2", timestamp="t2", persona_used="nitpicker", scores=_scores(4), weakness_detected=[])
    assert profile["persona_streak"] == {"current_persona": "nitpicker", "times_repeated_without_improvement": 0}


def test_persona_history_extraction():
    profile = empty_profile(name="An", class_id="c1")
    profile = merge_essay_into_profile(profile, essay_id="e1", timestamp="t1", persona_used="skeptic", scores=_scores(5), weakness_detected=[])
    profile = merge_essay_into_profile(profile, essay_id="e2", timestamp="t2", persona_used="expander", scores=_scores(6), weakness_detected=[])
    assert persona_history_from_profile(profile) == ["skeptic", "expander"]


def test_weakness_taxonomy_deduplicates_preserving_order():
    profile = empty_profile(name="An", class_id="c1")
    profile = merge_essay_into_profile(
        profile, essay_id="e1", timestamp="t1", persona_used="skeptic", scores=_scores(5),
        weakness_detected=["hasty generalization", "unsourced claim"],
    )
    profile = merge_essay_into_profile(
        profile, essay_id="e2", timestamp="t2", persona_used="skeptic", scores=_scores(5),
        weakness_detected=["unsourced claim", "ad hominem"],
    )
    assert weakness_taxonomy_from_profile(profile) == ["hasty generalization", "unsourced claim", "ad hominem"]


def test_score_trend_insufficient_data_on_first_essay():
    profile = empty_profile(name="An", class_id="c1")
    profile = merge_essay_into_profile(profile, essay_id="e1", timestamp="t1", persona_used="skeptic", scores=_scores(5), weakness_detected=[])
    assert profile["score_trend"] == "insufficient_data"


def test_score_trend_improving():
    profile = empty_profile(name="An", class_id="c1")
    profile = merge_essay_into_profile(profile, essay_id="e1", timestamp="t1", persona_used="skeptic", scores=_scores(3), weakness_detected=[])
    profile = merge_essay_into_profile(profile, essay_id="e2", timestamp="t2", persona_used="nitpicker", scores=_scores(6), weakness_detected=[])
    profile = merge_essay_into_profile(profile, essay_id="e3", timestamp="t3", persona_used="expander", scores=_scores(9), weakness_detected=[])
    assert profile["score_trend"] == "improving"


def test_score_trend_declining():
    profile = empty_profile(name="An", class_id="c1")
    profile = merge_essay_into_profile(profile, essay_id="e1", timestamp="t1", persona_used="skeptic", scores=_scores(9), weakness_detected=[])
    profile = merge_essay_into_profile(profile, essay_id="e2", timestamp="t2", persona_used="nitpicker", scores=_scores(6), weakness_detected=[])
    profile = merge_essay_into_profile(profile, essay_id="e3", timestamp="t3", persona_used="expander", scores=_scores(3), weakness_detected=[])
    assert profile["score_trend"] == "declining"


def test_score_trend_stagnant_within_flat_band():
    profile = empty_profile(name="An", class_id="c1")
    profile = merge_essay_into_profile(profile, essay_id="e1", timestamp="t1", persona_used="skeptic", scores=_scores(5), weakness_detected=[])
    profile = merge_essay_into_profile(profile, essay_id="e2", timestamp="t2", persona_used="nitpicker", scores=_scores(5), weakness_detected=[])
    assert profile["score_trend"] == "stagnant"


def test_score_trend_flags_a_mid_window_collapse_as_volatile():
    """Wave 15 #3 -- the audit's case: [10, 0, 10].

    The slope over that window is genuinely flat, so the old code called it
    "stagnant" and it contributed 0 to the teacher's ranking -- ranked exactly
    like a student holding a steady 5. A whole essay collapsing is not the same
    thing as a steady score, so it now reports "volatile": the slope keeps its
    honest meaning and the swing gets its own signal rather than being reported
    as a decline the student is not actually in.
    """
    profile = empty_profile(name="An", class_id="c1")
    for i, score in enumerate((10, 0, 10), start=1):
        profile = merge_essay_into_profile(
            profile, essay_id=f"e{i}", timestamp=f"t{i}", persona_used="skeptic", scores=_scores(score), weakness_detected=[]
        )
    assert profile["score_trend"] == "volatile"


def test_score_trend_volatile_outranks_stagnant_for_the_teacher():
    """The point of the classification: it has to change the ordering, or the
    teacher never sees the collapse. (Wave 15 #3)"""
    from datetime import datetime, timezone

    from eduagent.aggregator.priority_engine import compute_priority

    now = datetime.now(timezone.utc)
    ts = now.isoformat()

    def _profile(trend):
        return {"score_trend": trend, "essay_history": [{"timestamp": ts, "weakness_detected": []}], "persona_streak": {}}

    volatile = compute_priority(_profile("volatile"), now=now, common_fallacy_set=set())
    stagnant = compute_priority(_profile("stagnant"), now=now, common_fallacy_set=set())
    declining = compute_priority(_profile("declining"), now=now, common_fallacy_set=set())

    assert volatile["total"] > stagnant["total"]
    # ...but a sustained decline is still the stronger signal of the two.
    assert declining["total"] > volatile["total"]


def test_score_trend_small_swing_is_still_stagnant():
    """The volatility band must not fire on ordinary essay-to-essay noise."""
    profile = empty_profile(name="An", class_id="c1")
    for i, score in enumerate((5, 6, 5), start=1):
        profile = merge_essay_into_profile(
            profile, essay_id=f"e{i}", timestamp=f"t{i}", persona_used="skeptic", scores=_scores(score), weakness_detected=[]
        )
    assert profile["score_trend"] == "stagnant"


def test_trend_slope_is_a_real_regression_over_a_wider_window():
    """Wave 15 #3: the old `sum(diffs)/len(diffs)` telescoped to
    (last - first) / (n - 1), so every essay between the ends cancelled out.
    At TREND_WINDOW == 3 the two agree; this pins the difference that appears
    the moment the window widens, so the bug cannot come back by config change.
    """
    from eduagent.memory.student_profile import _trend_slope

    # Same endpoints, different shape in between -- the telescoping version read
    # 1.0 for both, because everything but the endpoints cancelled out.
    assert _trend_slope([0.0, 0.0, 0.0, 0.0, 4.0]) == 0.8
    assert _trend_slope([0.0, 1.0, 2.0, 3.0, 4.0]) == 1.0
    # A pure straight line must still read exactly as its slope.
    assert _trend_slope([1.0, 2.0, 3.0, 4.0]) == 1.0


def test_student_feedback_is_stored_per_essay():
    profile = empty_profile(name="An", class_id="c1")
    profile = merge_essay_into_profile(
        profile, essay_id="e1", timestamp="t1", persona_used="skeptic", scores=_scores(5),
        weakness_detected=[], student_feedback="Great use of evidence -- next time, address counterarguments too.",
    )
    assert profile["essay_history"][-1]["student_feedback"] == "Great use of evidence -- next time, address counterarguments too."


def test_student_feedback_defaults_to_empty_string():
    profile = empty_profile(name="An", class_id="c1")
    profile = merge_essay_into_profile(profile, essay_id="e1", timestamp="t1", persona_used="skeptic", scores=_scores(5), weakness_detected=[])
    assert profile["essay_history"][-1]["student_feedback"] == ""


def test_essay_history_capped_at_max_entries():
    profile = empty_profile(name="An", class_id="c1")
    for i in range(MAX_HISTORY_ENTRIES + 10):
        profile = merge_essay_into_profile(
            profile, essay_id=f"e{i}", timestamp=f"t{i}", persona_used="skeptic", scores=_scores(5), weakness_detected=[],
        )
    assert len(profile["essay_history"]) == MAX_HISTORY_ENTRIES
    assert profile["essay_history"][-1]["essay_id"] == f"e{MAX_HISTORY_ENTRIES + 9}"
    assert profile["essay_history"][0]["essay_id"] == "e10"


def test_total_essays_count_tracks_beyond_cap():
    profile = empty_profile(name="An", class_id="c1")
    for i in range(MAX_HISTORY_ENTRIES + 10):
        profile = merge_essay_into_profile(
            profile, essay_id=f"e{i}", timestamp=f"t{i}", persona_used="skeptic", scores=_scores(5), weakness_detected=[],
        )
    assert profile["total_essays_count"] == MAX_HISTORY_ENTRIES + 10


def test_all_time_weaknesses_survive_history_trim():
    profile = empty_profile(name="An", class_id="c1")
    profile = merge_essay_into_profile(
        profile, essay_id="e0", timestamp="t0", persona_used="skeptic", scores=_scores(5),
        weakness_detected=["hasty generalization"],
    )
    for i in range(1, MAX_HISTORY_ENTRIES + 10):
        profile = merge_essay_into_profile(
            profile, essay_id=f"e{i}", timestamp=f"t{i}", persona_used="skeptic", scores=_scores(5), weakness_detected=[],
        )
    # e0's weakness has long since been trimmed off essay_history...
    assert not any(e["essay_id"] == "e0" for e in profile["essay_history"])
    # ...but the cumulative taxonomy still remembers it.
    assert "hasty generalization" in weakness_taxonomy_from_profile(profile)


def test_weakness_taxonomy_falls_back_when_all_time_field_missing():
    profile = empty_profile(name="An", class_id="c1")
    profile = merge_essay_into_profile(
        profile, essay_id="e1", timestamp="t1", persona_used="skeptic", scores=_scores(5),
        weakness_detected=["anecdotal evidence"],
    )
    del profile["all_time_weaknesses"]
    assert weakness_taxonomy_from_profile(profile) == ["anecdotal evidence"]
