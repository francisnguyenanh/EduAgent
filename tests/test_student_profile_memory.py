"""Unit tests for the pure profile-merge logic (no Firestore, no network).

Locks in the "stuck persona streak" and "needs_attention" flagging rules
that Phase 3's Class Aggregator will depend on.
"""

from __future__ import annotations

from eduagent.memory.student_profile import (
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
