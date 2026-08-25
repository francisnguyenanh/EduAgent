"""Unit tests for Task 10.2: Learning-Outcome Evaluation Suite."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root and src to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.evaluate_learning_outcomes import BENCHMARK_SCENARIOS, evaluate_learning_outcomes


def test_learning_outcomes_benchmark_scenarios_pass_100_percent():
    results = evaluate_learning_outcomes()
    assert results["all_passed"] is True
    assert results["pass_count"] == results["total_scenarios"] == 8
    assert results["avg_targeted_growth"] >= 4.0
    assert results["avg_overall_growth"] >= 2.5


def test_every_scenario_improves_targeted_dimension():
    for s in BENCHMARK_SCENARIOS:
        dim = s["dimension_targeted"]
        before = s["before_scores"][dim]
        after = s["after_scores"][dim]
        delta = after - before
        assert delta >= 4, f"Scenario {s['id']} expected delta >= 4 for {dim}, got {delta}"
        assert after >= 7, f"Scenario {s['id']} expected post-revision score >= 7, got {after}"
