"""Unit tests for Task 10.2: Learning-Outcome MEASUREMENT harness.

Wave 12 Group 1: the previous version of this file asserted that hand-typed
`before_scores`/`after_scores` literals differed by >= 4 -- i.e. it asserted
`8 - 2 >= 4`, which passes even if the entire `src/` tree is deleted. These
tests instead exercise the measurement machinery itself (with the LLM mocked,
so they stay deterministic and offline) plus one `e2e`-marked test that runs
the real scorer.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.evaluate_learning_outcomes import (  # noqa: E402
    BENCHMARK_SCENARIOS,
    MeasurementError,
    evaluate_learning_outcomes,
    generate_markdown_report,
)

_AXES = ("logical_coherence", "evidence_quality", "counterargument_handling", "scope_awareness")

# The revised thesis of every scenario is longer than its initial thesis, so
# "score by length" is a usable stand-in for a scorer that rewards the revision
# without needing a live model.
_REVISED_TEXTS = {s["revised_thesis"] for s in BENCHMARK_SCENARIOS}


def _fake_summarize(text, **_kwargs):
    return {"main_claim": text[:40], "claims": [], "evidence": [], "fallacies_draft": []}, False


def _fake_score(*, essay_text, summary, debate_turns, language="en", log_context=None):
    value = 8 if essay_text in _REVISED_TEXTS else 3
    return {axis: value for axis in _AXES}, {axis: "" for axis in _AXES}, "feedback", False


def _fake_score_degraded(**_kwargs):
    return {axis: 0 for axis in _AXES}, {axis: "" for axis in _AXES}, "", True


def test_no_scenario_declares_its_own_scores():
    """Regression guard for the Wave 12 finding: a scenario must only carry
    INPUT text. If `before_scores`/`after_scores` ever reappear as literals,
    the report stops being a measurement again."""
    for s in BENCHMARK_SCENARIOS:
        assert "before_scores" not in s, f"{s['id']} declares hand-typed before_scores"
        assert "after_scores" not in s, f"{s['id']} declares hand-typed after_scores"
        assert s["initial_thesis"].strip()
        assert s["revised_thesis"].strip()
        assert s["dimension_targeted"] in _AXES


def test_measurement_calls_the_real_scorer_for_every_text():
    """8 scenarios x 2 texts = 16 scorer calls; nothing may be short-circuited."""
    with patch("scripts.evaluate_learning_outcomes.summarize_essay", side_effect=_fake_summarize), patch(
        "scripts.evaluate_learning_outcomes.score_essay", side_effect=_fake_score
    ) as mock_score:
        results = evaluate_learning_outcomes(runs=1, verbose=False)

    assert mock_score.call_count == 2 * len(BENCHMARK_SCENARIOS) == 16
    # The scorer must never be handed the debate transcript for this measurement
    # (see MEASUREMENT DESIGN) -- that is what keeps before/after comparable.
    for call in mock_score.call_args_list:
        assert call.kwargs["debate_turns"] == []


def test_deltas_are_derived_from_scorer_output_not_literals():
    with patch("scripts.evaluate_learning_outcomes.summarize_essay", side_effect=_fake_summarize), patch(
        "scripts.evaluate_learning_outcomes.score_essay", side_effect=_fake_score
    ):
        results = evaluate_learning_outcomes(runs=1, verbose=False)

    assert results["total_scenarios"] == 8
    assert results["pass_count"] == 8
    # 3 -> 8 under the stand-in scorer, on every axis.
    assert results["avg_targeted_growth"] == 5.0
    assert results["avg_overall_growth"] == 5.0
    for e in results["evaluations"]:
        assert e["before_score"] == 3
        assert e["after_score"] == 8


def test_a_scorer_that_does_not_reward_the_revision_makes_the_suite_fail():
    """The measurement must be capable of FAILING -- this is the property the
    old literal-subtraction version did not have."""
    flat = lambda **_kw: ({axis: 5 for axis in _AXES}, {axis: "" for axis in _AXES}, "", False)  # noqa: E731
    with patch("scripts.evaluate_learning_outcomes.summarize_essay", side_effect=_fake_summarize), patch(
        "scripts.evaluate_learning_outcomes.score_essay", side_effect=flat
    ):
        results = evaluate_learning_outcomes(runs=1, verbose=False)

    assert results["all_passed"] is False
    assert results["pass_count"] == 0
    assert results["avg_targeted_growth"] == 0.0


def test_degraded_scorer_raises_instead_of_emitting_a_number():
    with patch("scripts.evaluate_learning_outcomes.summarize_essay", side_effect=_fake_summarize), patch(
        "scripts.evaluate_learning_outcomes.score_essay", side_effect=_fake_score_degraded
    ):
        with pytest.raises(MeasurementError):
            evaluate_learning_outcomes(runs=1, verbose=False)


def test_report_states_its_limitations():
    """The report must carry the n=8 / no-control-group caveats -- their absence
    is what turned this artifact into an over-claim in the first place."""
    with patch("scripts.evaluate_learning_outcomes.summarize_essay", side_effect=_fake_summarize), patch(
        "scripts.evaluate_learning_outcomes.score_essay", side_effect=_fake_score
    ):
        md = generate_markdown_report(evaluate_learning_outcomes(runs=1, verbose=False))

    assert "not 8 students" in md
    assert "No control group" in md
    assert "non-deterministic" in md
    # The old report claimed an "independent re-score ... Zero Leak | PASS" for a
    # behaviour that did not exist; make sure that exact over-claim is gone.
    assert "Zero Grade Inflation" not in md


@pytest.mark.e2e
def test_live_scorer_registers_improvement_on_one_scenario():
    """One real Vertex AI measurement, so the harness is proven against the
    actual model and not only against the stand-in above."""
    from scripts.evaluate_learning_outcomes import _measure_text

    scenario = BENCHMARK_SCENARIOS[0]
    dim = scenario["dimension_targeted"]
    before = _measure_text(scenario["initial_thesis"], label="e2e:before", runs=1)
    after = _measure_text(scenario["revised_thesis"], label="e2e:after", runs=1)
    assert after[dim] > before[dim], f"live scorer did not register improvement: {before[dim]} -> {after[dim]}"
