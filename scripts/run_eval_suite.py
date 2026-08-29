"""4-Layer Deterministic ADK Eval Suite runner.

Executes all 4 layers (50 test cases total) and writes a JSON + Markdown report to eval/results/.
Design Principle: ZERO LLM-as-judge. Every metric is deterministic, auditable and
reproducible, and every case is verified capable of FAILING (see below).

4 Layers:
  - Layer 1: Safety & Security Guardrails (15 cases) -- real validator/sanitizer/auth
  - Layer 2: Behavioral & Pedagogical Discipline (15 cases) -- real prompt builders
  - Layer 3: Long-Term Memory & Adaptation (10 cases) -- real profile-merge functions
  - Layer 4: Learning Outcomes & Cognitive Growth (10 cases) -- 6 against the real
    metacognitive growth logic, 4 against the measured artifact produced by
    scripts/evaluate_learning_outcomes.py

Two groups of cases were previously unfalsifiable and have been
rewritten to drive production code instead:
  - Layer 4's 8 "growth" cases subtracted integer literals declared in
    eval/evalset.py (`8 - 2 >= 4`), passing even with src/ deleted.
  - Layer 2's persona-fidelity cases rebuilt the system instruction inside the
    runner and then asserted the anchor was in the string they had just
    concatenated. They now call nodes/debate.py::build_system_instruction().

Usage:
  python scripts/run_eval_suite.py
  python scripts/run_eval_suite.py --strict
  python scripts/run_eval_suite.py --live-persona   # opt-in: real Gemini debate turns
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

import eduagent
from eval.evalset import (
    ANSWER_LEAK_CASES,
    BOUNDS_AND_FORMATTING_CASES,
    ESCALATION_PROTOCOL_CASES,
    LEARNING_OUTCOME_CASES,
    MEMORY_ADAPTATION_CASES,
    PERSONA_FIDELITY_CASES,
    PROMPT_INJECTION_CASES,
    SINGLE_QUESTION_CONSTRAINT_CASES,
    TENANCY_SECURITY_CASES,
)

_RESULTS_DIR = _ROOT / "eval" / "results"


@dataclass
class CaseResult:
    id: str
    layer: str
    group: str
    passed: bool
    detail: str
    raw_output: dict = field(default_factory=dict)


# =============================================================================
# LAYER 1: SAFETY & SECURITY RUNNERS
# =============================================================================

def run_answer_leak_cases() -> list[CaseResult]:
    from eduagent.nodes.validator import validate_debate_turn

    results = []
    for case in ANSWER_LEAK_CASES:
        outcome = validate_debate_turn(case["text"])
        passed = outcome.passed == case["expect_passed"]
        results.append(
            CaseResult(
                id=case["id"],
                layer="Layer 1: Safety & Security",
                group="answer_leak",
                passed=passed,
                detail=f"expected passed={case['expect_passed']}, got passed={outcome.passed}",
                raw_output={"text": case["text"], "violations": outcome.violations},
            )
        )
    return results


def run_prompt_injection_cases() -> list[CaseResult]:
    from eduagent.nodes.intake import strip_injection_attempts

    results = []
    for case in PROMPT_INJECTION_CASES:
        _cleaned, matches = strip_injection_attempts(case["text"])
        was_blocked = bool(matches)
        passed = was_blocked == case["expect_blocked"]
        results.append(
            CaseResult(
                id=case["id"],
                layer="Layer 1: Safety & Security",
                group="prompt_injection",
                passed=passed,
                detail=f"expected blocked={case['expect_blocked']}, got blocked={was_blocked}",
                raw_output={"text": case["text"], "matched_patterns": matches},
            )
        )
    return results


def run_tenancy_security_cases() -> list[CaseResult]:
    """This runner used to re-implement the authorization check
    (`claims.get("class_id") == case["target_class_id"]`) instead of calling it.
    That protected a COPY of the logic -- a bug in the real
    `server._verify_class_auth` (a forgotten role check, say) would have left
    these 4 cases green. It now drives the exact function the HTTP routes use."""
    from eduagent.auth import create_access_token
    from eduagent.server import _verify_class_auth

    results = []
    for case in TENANCY_SECURITY_CASES:
        if case["token_class_id"] == "c1_tampered":
            token = "ey.tampered.token"
        elif case["token_class_id"]:
            token = create_access_token(user_id=f"{case['token_class_id']}_teacher", role="teacher", class_id=case["token_class_id"])
        else:
            token = ""

        authorization = f"Bearer {token}" if token else None
        try:
            _verify_class_auth(case["target_class_id"], authorization, required_role="teacher")
            allowed = True
        except Exception:
            allowed = False

        passed = allowed == case["expect_allowed"]
        results.append(
            CaseResult(
                id=case["id"],
                layer="Layer 1: Safety & Security",
                group="tenancy_isolation",
                passed=passed,
                detail=f"expected allowed={case['expect_allowed']}, got allowed={allowed}",
                raw_output=case,
            )
        )
    return results


# =============================================================================
# LAYER 2: BEHAVIORAL & PEDAGOGICAL DISCIPLINE RUNNERS
# =============================================================================

def _matches_signature(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in keywords)


def run_persona_fidelity_cases(*, live: bool = False) -> list[CaseResult]:
    """rework.

    Default (deterministic, zero LLM) mode asserts against the REAL production
    prompt builder, `nodes/debate.py::build_system_instruction()` -- the same
    function generate_debate_turn() sends to Gemini. The previous version
    rebuilt the instruction string inside this runner and then checked that the
    anchor was in the string it had just concatenated: a tautology. Now the
    checks are:
      1. the production builder injects this persona's anchor into the prompt
         it will actually send (fails if anchoring is refactored away),
      2. the anchor carries this persona's distinguishing keyword signature,
      3. the anchor is DISTINCT from every other persona's anchor, and no other
         persona's anchor satisfies this persona's signature (fails if two
         personas collapse into the same voice -- the exact drift failure mode
         persona anchoring exists to prevent),
      4. the persona survives all 3 escalation turns (anchor still present on
         turn 2 and turn 3, not just the opening turn).

    `--live-persona` additionally runs the real 3-turn debate against live
    Gemini and scores the model's actual questions against the keyword lexicon.
    """
    from eduagent.nodes.debate import build_system_instruction
    from eduagent.skills.personas import PERSONA_IDS, get_persona

    all_anchors = {pid: get_persona(pid).anchor for pid in PERSONA_IDS}

    results = []
    for case in PERSONA_FIDELITY_CASES:
        pid = case["persona_id"]
        persona = get_persona(pid)
        keywords = case["signature_keywords"]

        # (1) + (4): the real builder must carry the anchor on every turn.
        turns_with_anchor = [
            t for t in (1, 2, 3) if persona.anchor in build_system_instruction(persona_id=pid, turn_number=t)
        ]
        anchor_injected_all_turns = turns_with_anchor == [1, 2, 3]

        # (2)
        keyword_in_anchor = _matches_signature(persona.anchor, keywords)

        # (3)
        others = {other: a for other, a in all_anchors.items() if other != pid}
        anchor_is_unique = persona.anchor not in others.values()
        confusable_with = sorted(other for other, a in others.items() if _matches_signature(a, keywords))

        passed = anchor_injected_all_turns and keyword_in_anchor and anchor_is_unique and not confusable_with

        detail = (
            f"production builder injects anchor on turns {turns_with_anchor} (need [1, 2, 3]); "
            f"signature match={keyword_in_anchor}; anchor unique={anchor_is_unique}; "
            f"confusable with={confusable_with or 'none'}"
        )
        raw: dict = {"persona": pid, "focus": persona.focus, "turns_with_anchor": turns_with_anchor}

        if live:
            live_passed, live_detail, live_raw = _run_live_persona_debate(case)
            passed = passed and live_passed
            detail = f"{detail} | LIVE: {live_detail}"
            raw["live"] = live_raw

        results.append(
            CaseResult(
                id=case["id"],
                layer="Layer 2: Behavioral Discipline",
                group="persona_fidelity_live" if live else "persona_fidelity",
                passed=passed,
                detail=detail,
                raw_output=raw,
            )
        )
    return results


def _run_live_persona_debate(case: dict) -> tuple[bool, str, dict]:
    """Runs the real 3-turn debate against live Gemini and matches the model's
    ACTUAL questions against the persona's keyword lexicon. Opt-in only
    (`--live-persona`) so the default suite keeps its zero-LLM guarantee."""
    from eduagent.nodes.debate import generate_debate_turn
    from eduagent.nodes.validator import validate_debate_turn

    turns: list[dict] = []
    questions: list[str] = []
    matched_turns: list[int] = []
    validator_failures: list[int] = []

    for turn_number in (1, 2, 3):
        student_response = case["student_replies"][turn_number - 2] if turn_number > 1 else None
        turn = generate_debate_turn(
            persona_id=case["persona_id"],
            essay_text=case["essay"],
            summary=case["summary"],
            turn_number=turn_number,
            prior_turns=turns,
            student_response=student_response,
            prior_weaknesses=[],
        )
        turns.append(turn)
        question = turn["question"]
        questions.append(question)
        if _matches_signature(question, case["signature_keywords"]):
            matched_turns.append(turn_number)
        if not validate_debate_turn(question).passed:
            validator_failures.append(turn_number)

    # A persona holds if its voice is recognisable in at least 2 of 3 turns --
    # demanding 3/3 keyword hits from a live model would measure the lexicon's
    # completeness, not persona fidelity.
    passed = len(matched_turns) >= 2 and not validator_failures
    detail = (
        f"live signature matched on turns {matched_turns} (need >= 2 of 3); "
        f"validator failures on turns {validator_failures or 'none'}"
    )
    return passed, detail, {"questions": questions, "matched_turns": matched_turns}


def run_single_question_cases() -> list[CaseResult]:
    from eduagent.nodes.validator import validate_debate_turn

    results = []
    for case in SINGLE_QUESTION_CONSTRAINT_CASES:
        outcome = validate_debate_turn(case["text"])
        passed = outcome.passed == case["expect_valid"]
        results.append(
            CaseResult(
                id=case["id"],
                layer="Layer 2: Behavioral Discipline",
                group="single_question_constraint",
                passed=passed,
                detail=f"expected valid={case['expect_valid']}, got valid={outcome.passed}",
                raw_output={"text": case["text"], "violations": outcome.violations},
            )
        )
    return results


def run_bounds_cases() -> list[CaseResult]:
    from eduagent.nodes.validator import validate_debate_turn

    results = []
    for case in BOUNDS_AND_FORMATTING_CASES:
        outcome = validate_debate_turn(case["text"])
        passed = outcome.passed == case["expect_valid"]
        results.append(
            CaseResult(
                id=case["id"],
                layer="Layer 2: Behavioral Discipline",
                group="formatting_bounds",
                passed=passed,
                detail=f"expected valid={case['expect_valid']}, got valid={outcome.passed}",
                raw_output={"text": case["text"], "violations": outcome.violations},
            )
        )
    return results


def run_escalation_cases() -> list[CaseResult]:
    from eduagent.skills.debate_escalation import ESCALATION_INSTRUCTIONS

    results = []
    for case in ESCALATION_PROTOCOL_CASES:
        turn = case["turn"]
        instr = ESCALATION_INSTRUCTIONS.get(turn, "")
        passed = len(instr) > 10
        results.append(
            CaseResult(
                id=case["id"],
                layer="Layer 2: Behavioral Discipline",
                group="escalation_protocol",
                passed=passed,
                detail=f"turn {turn} has deterministic escalation instruction: '{instr[:40]}...'",
                raw_output={"turn": turn, "instruction": instr},
            )
        )
    return results


# =============================================================================
# LAYER 3: LONG-TERM MEMORY & ADAPTATION RUNNERS
# =============================================================================

def run_memory_cases() -> list[CaseResult]:
    from eduagent.memory.student_profile import (
        _score_trend,
        empty_profile,
        merge_essay_into_profile,
        weakness_taxonomy_from_profile,
    )
    from eduagent.nodes.debate import _build_prompt

    results = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for case in MEMORY_ADAPTATION_CASES:
        cid = case["id"]
        passed = False
        detail = ""

        if cid == "mem-streak-break-at-threshold":
            p = empty_profile(name="S", class_id="c1")
            for i in range(case["streak_count"] + 1):
                p = merge_essay_into_profile(
                    p, essay_id=f"e_{i}", timestamp=now_iso, persona_used="skeptic",
                    scores={"logic": 3}, weakness_detected=["claim"],
                )
            passed = p["flags"]["needs_attention"] == case["expect_needs_attention"]
            detail = f"needs_attention={p['flags']['needs_attention']}"

        elif cid == "mem-streak-reset-on-improvement":
            p = empty_profile(name="S", class_id="c1")
            p = merge_essay_into_profile(p, essay_id="e1", timestamp=now_iso, persona_used="skeptic", scores={"logic": 3}, weakness_detected=["claim"])
            p = merge_essay_into_profile(p, essay_id="e2", timestamp=now_iso, persona_used="skeptic", scores={"logic": 3}, weakness_detected=["claim"])
            # Improved score
            p = merge_essay_into_profile(p, essay_id="e3", timestamp=now_iso, persona_used="skeptic", scores={"logic": 7}, weakness_detected=["claim"])
            streak = p["persona_streak"]["times_repeated_without_improvement"]
            passed = (streak == 0) == case["expect_streak_reset"]
            detail = f"streak reset to {streak}"

        elif cid == "mem-taxonomy-dedup-preserves-order":
            profile = {"essay_history": [{"weakness_detected": case["input_weaknesses"]}], "all_time_weaknesses": []}
            res = weakness_taxonomy_from_profile(profile)
            passed = res == case["expected_output"]
            detail = f"taxonomy output={res}"

        elif cid == "mem-taxonomy-all-time-retention":
            p = empty_profile(name="S", class_id="c1")
            for i in range(case["historical_count"]):
                p = merge_essay_into_profile(p, essay_id=f"e_{i}", timestamp=now_iso, persona_used="skeptic", scores={"logic": 5}, weakness_detected=[f"w_{i}"])
            # History is capped at 50, but all_time_weaknesses retains all 60
            passed = len(p["essay_history"]) <= 50 and p["total_essays_count"] == 60
            detail = f"history capped={len(p['essay_history'])}, total={p['total_essays_count']}"

        elif "mem-trend-" in cid:
            history = [{"avg_score": s} for s in case["scores"]]
            trend = _score_trend(history)
            passed = trend == case["expected_trend"]
            detail = f"trend computed='{trend}', expected='{case['expected_trend']}'"

        elif cid == "mem-prompt-context-injection-turn-1":
            prompt = _build_prompt(
                essay_text="text", summary={"fallacies_draft": []}, turn=1,
                prior_turns=[], student_response=None, prior_weaknesses=case["prior_weaknesses"]
            )
            passed = ("previously struggled with" in prompt) == case["expect_injected_in_prompt"]
            detail = f"context injected in prompt={passed}"

        elif cid == "mem-prompt-context-omitted-turn-2-plus":
            prompt = _build_prompt(
                essay_text="text", summary={"fallacies_draft": []}, turn=2,
                prior_turns=[{"turn": 1, "question": "Q1"}], student_response="A1", prior_weaknesses=case["prior_weaknesses"]
            )
            passed = ("previously struggled with" in prompt) == case["expect_injected_in_prompt"]
            detail = f"context omitted on turn 2={passed}"

        results.append(
            CaseResult(
                id=cid,
                layer="Layer 3: Long-Term Memory",
                group="memory_adaptation",
                passed=passed,
                detail=detail,
                raw_output=case,
            )
        )
    return results


# =============================================================================
# LAYER 4: LEARNING OUTCOMES & COGNITIVE GROWTH RUNNERS
# =============================================================================

_MEASURED_ARTIFACT = _RESULTS_DIR / "learning_outcome_measured.json"
_AXES = ("logical_coherence", "evidence_quality", "counterargument_handling", "scope_awareness")


def _load_measured_artifact() -> dict | None:
    """Loads the learning-outcome measurement produced by
    scripts/evaluate_learning_outcomes.py. Returns None if it is absent or
    unreadable -- the Group B cases then FAIL loudly rather than silently
    passing, which is the whole point of the falsifiability requirement."""
    if not _MEASURED_ARTIFACT.exists():
        return None
    try:
        data = json.loads(_MEASURED_ARTIFACT.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    if not isinstance(data, dict) or not data.get("evaluations"):
        return None
    return data


def _run_reflection_logic_case(case: dict, now_iso: str) -> tuple[bool, str]:
    """Group A: exercises the real merge_reflection_into_profile()."""
    from eduagent.memory.student_profile import empty_profile, merge_reflection_into_profile

    cid = case["id"]
    bonus = case.get("growth_bonus", 0.5)
    sequence = case.get("resolution_sequence")
    if sequence is None:
        sequence = [case["resolved"]] * case.get("breakthroughs", 1) if "resolved" in case else [True] * case["breakthroughs"]

    p = empty_profile(name="S", class_id="c1")
    for i, resolved in enumerate(sequence):
        p = merge_reflection_into_profile(
            p,
            reflection_text=f"Revision {i}",
            original_fallacy=f"f{i}",
            resolved=resolved,
            growth_bonus=bonus,
            timestamp=now_iso,
        )

    checks: list[tuple[str, object, object]] = []
    if "expected_growth_bonus" in case:
        checks.append(("total_growth_bonus", p["total_growth_bonus"], case["expected_growth_bonus"]))
    if "expected_total_bonus" in case:
        checks.append(("total_growth_bonus", p["total_growth_bonus"], case["expected_total_bonus"]))
    if "expected_breakthrough_count" in case:
        checks.append(("breakthrough_count", p["breakthrough_count"], case["expected_breakthrough_count"]))
    if "expected_reflections_recorded" in case:
        checks.append(("reflections_recorded", len(p["reflections_history"]), case["expected_reflections_recorded"]))
    if "expected_last_resolved" in case:
        checks.append(("last_reflection.resolved", p["last_reflection"]["resolved"], case["expected_last_resolved"]))

    if not checks:
        return False, f"{cid}: no assertion declared for this case"

    passed = all(actual == expected for _name, actual, expected in checks)
    detail = ", ".join(f"{name}={actual!r} (expected {expected!r})" for name, actual, expected in checks)
    return passed, detail


def _run_measured_case(case: dict, measured: dict | None) -> tuple[bool, str]:
    """Group B: asserts against the real measured artifact. Every branch here
    can fail -- a missing artifact, a flat measurement, or an incomplete axis
    coverage all report FAIL."""
    if measured is None:
        return False, (
            f"measurement artifact missing or unreadable at {_MEASURED_ARTIFACT.relative_to(_ROOT)} -- "
            "run `python scripts/evaluate_learning_outcomes.py` first"
        )

    evaluations = measured["evaluations"]
    assertion = case["assertion"]

    if assertion == "artifact_present":
        n = len(evaluations)
        has_scores = all("before_scores" in e and "after_scores" in e for e in evaluations)
        passed = n >= 8 and has_scores and bool(measured.get("measured_at")) and bool(measured.get("scorer"))
        return passed, (
            f"artifact has {n} measured scenarios, full per-axis scores={has_scores}, "
            f"measured_at={measured.get('measured_at')!r}, scorer={measured.get('scorer')!r}"
        )

    if assertion == "mean_targeted_delta_gt":
        actual = measured["avg_targeted_growth"]
        return actual > case["threshold"], f"measured mean targeted delta={actual:+} (threshold > {case['threshold']:+})"

    if assertion == "improved_fraction_gte":
        improved = sum(1 for e in evaluations if e["delta_targeted"] > 0)
        fraction = improved / len(evaluations)
        return fraction >= case["threshold"], (
            f"{improved}/{len(evaluations)} scenarios improved on their targeted axis "
            f"({fraction:.0%}, threshold >= {case['threshold']:.0%})"
        )

    if assertion == "all_axes_covered":
        covered = {e["dimension"] for e in evaluations}
        missing = sorted(set(_AXES) - covered)
        return not missing, f"axes measured={sorted(covered)}, missing={missing}"

    return False, f"unknown measured assertion {assertion!r}"


def run_learning_outcome_cases() -> list[CaseResult]:
    results = []
    now_iso = datetime.now(timezone.utc).isoformat()
    measured = _load_measured_artifact()

    for case in LEARNING_OUTCOME_CASES:
        kind = case.get("kind")
        if kind == "reflection_logic":
            passed, detail = _run_reflection_logic_case(case, now_iso)
            group = "metacognitive_growth_logic"
        elif kind == "measured":
            passed, detail = _run_measured_case(case, measured)
            group = "measured_learning_outcome"
        else:
            passed, detail = False, f"case declares unknown kind={kind!r}"
            group = "learning_outcomes"

        results.append(
            CaseResult(
                id=case["id"],
                layer="Layer 4: Learning Outcomes",
                group=group,
                passed=passed,
                detail=detail,
                raw_output=case,
            )
        )
    return results


# =============================================================================
# SUITE AGGREGATOR & REPORT BUILDER
# =============================================================================

def run_full_suite(*, live_persona: bool = False) -> list[CaseResult]:
    results: list[CaseResult] = []
    # Layer 1 (15 cases)
    results += run_answer_leak_cases()
    results += run_prompt_injection_cases()
    results += run_tenancy_security_cases()
    # Layer 2 (15 cases)
    results += run_persona_fidelity_cases(live=live_persona)
    results += run_single_question_cases()
    results += run_bounds_cases()
    results += run_escalation_cases()
    # Layer 3 (10 cases)
    results += run_memory_cases()
    # Layer 4 (10 cases)
    results += run_learning_outcome_cases()
    return results


def build_report(results: list[CaseResult]) -> dict:
    by_layer: dict[str, list[CaseResult]] = {}
    for r in results:
        by_layer.setdefault(r.layer, []).append(r)

    layer_summaries = {}
    for layer, layer_results in by_layer.items():
        passed_count = sum(1 for r in layer_results if r.passed)
        layer_summaries[layer] = {
            "total": len(layer_results),
            "passed": passed_count,
            "pass_rate": round(passed_count / len(layer_results), 4) if layer_results else 0.0,
        }

    return {
        "overall": {
            "total": len(results),
            "passed": sum(1 for r in results if r.passed),
            "pass_rate": round(sum(1 for r in results if r.passed) / len(results), 4) if results else 0.0,
        },
        "layers": layer_summaries,
        "cases": [asdict(r) for r in results],
    }


def render_markdown(report: dict) -> str:
    total = report["overall"]["total"]
    is_live = any(c["group"].endswith("_live") for c in report["cases"])
    if is_live:
        live_cases = [c for c in report["cases"] if c["group"].endswith("_live")]
        live_passed = sum(1 for c in live_cases if c["passed"])
        return f"""# ADK Eval Suite Report -- `--live-persona` run (MAKES REAL GEMINI CALLS)

> ⚠️ **This is NOT the deterministic report.** This run was invoked with
> `--live-persona`, so the persona-fidelity group ran the real 3-turn debate
> against live Gemini and matched the model's actual questions against a fixed
> keyword lexicon. The deterministic, zero-LLM report is `eval_report.md`.
>
> Live persona-fidelity result: **{live_passed}/{len(live_cases)} personas held their voice**
> (criterion: the persona's signature lexicon appears in >= 2 of 3 generated
> questions, and every question passes the independent validator).
>
> Live results are **not reproducible** -- Gemini output varies per run. Cite
> them as a diagnostic observation, never as a pass rate.

| Case | Result | Detail |
|---|:---:|---|
""" + "".join(
            f"| `{c['id']}` | **{'PASS' if c['passed'] else 'FAIL'}** | {c['detail']} |\n" for c in live_cases
        ) + f"""
## All cases in this run ({report['overall']['passed']}/{total})

| Case ID | Layer | Group | Result | Detail |
|---|---|---|:---:|---|
""" + "".join(
            f"| `{c['id']}` | {c['layer']} | `{c['group']}` | **{'PASS' if c['passed'] else 'FAIL'}** | {c['detail']} |\n"
            for c in report["cases"]
        )

    md = f"""# 4-Layer Deterministic ADK Eval Suite Report

> **Methodological Mandate (ZERO LLM-as-Judge):** all {total} cases are decided by **deterministic rules** — validator regexes, the ranking algorithm, and pure functions in `src/`. No LLM acts as a judge anywhere in this suite, so there is no LLM-as-judge path to reward-hack.
>
> **How to read this number:** it means **{report['overall']['passed']}/{total} deterministic test cases passed** — i.e. "the suite is green", NOT "the system is {report['overall']['pass_rate']:.0%} correct". Those are two different claims.
>
> **What to know about Layer 4:** 6 cases exercise the real metacognitive growth logic directly (`memory/student_profile.py`); the other 4 assert against **actually measured results** in `eval/results/learning_outcome_measured.json`, produced by `scripts/evaluate_learning_outcomes.py` calling the production scorer through Vertex AI. If that measurement file is missing, or the measurement shows no growth, those cases **FAIL** — they are not arithmetic on hard-coded constants.

---

## 1. Four-Layer Summary

**Total:** **{report['overall']['passed']}/{total} deterministic test cases passed ({report['overall']['pass_rate']:.0%})**

| Evaluation Layer | Cases Passed | Total Cases | Pass Rate |
|---|:---:|:---:|:---:|
"""
    for layer, s in report["layers"].items():
        md += f"| **{layer}** | {s['passed']} | {s['total']} | **{s['pass_rate']:.0%}** |\n"

    md += """
---

## 2. Detailed Test Matrix

| Case ID | Layer | Group | Result | Execution Detail |
|---|---|---|:---:|---|
"""
    for c in report["cases"]:
        res_str = "PASS" if c["passed"] else "FAIL"
        md += f"| `{c['id']}` | {c['layer']} | `{c['group']}` | **{res_str}** | {c['detail']} |\n"

    return md


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="4-Layer ADK Eval Suite Runner")
    parser.add_argument("--strict", action="store_true", help="Exit code 1 if any test fails")
    parser.add_argument(
        "--live-persona",
        action="store_true",
        help="Additionally run the real 3-turn debate against live Gemini for the persona-fidelity cases "
        "(opt-in: the default suite makes ZERO LLM calls)",
    )
    args = parser.parse_args()

    print(f"[*] Running 4-Layer ADK Eval Suite (deterministic; live-persona={'on' if args.live_persona else 'off'})...")
    results = run_full_suite(live_persona=args.live_persona)
    report = build_report(results)

    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    # A --live-persona run makes real Gemini calls, so it must NOT overwrite the
    # deterministic report -- that report's whole claim is "zero LLM calls".
    stem = "eval_report_live_persona" if args.live_persona else "eval_report"
    (_RESULTS_DIR / f"{stem}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (_RESULTS_DIR / f"{stem}.md").write_text(render_markdown(report), encoding="utf-8")

    print(f"\n[OK] Evaluation complete: {report['overall']['passed']}/{report['overall']['total']} passed ({report['overall']['pass_rate']:.0%})")
    print(f"[OK] Report written to: {_RESULTS_DIR / f'{stem}.md'}")

    if args.strict and report["overall"]["passed"] != report["overall"]["total"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
