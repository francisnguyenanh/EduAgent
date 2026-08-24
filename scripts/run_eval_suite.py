"""PHASE 5 -- ADK Eval Suite runner.

Runs eval/evalset.py's 3 groups and writes a JSON + Markdown report to
eval/results/. Deliberately does NOT use an LLM-as-judge for any of these
groups (see eval/evalset.py module docstring for why -- reward-hacking risk):

  - answer_leak / prompt_injection: call the EXACT deterministic production
    functions (nodes/validator.py, nodes/intake.py) the real pipeline runs --
    zero LLM cost, zero flakiness, and a genuine regression test (if someone
    weakens a regex later, this suite catches it).
  - persona_fidelity: calls the EXACT production turn-generation function
    (nodes/debate.generate_debate_turn) against real Vertex AI for all 3
    turns per persona, then scores the REAL text against a fixed keyword
    signature per persona -- a deterministic metric applied to a real model
    call, not a self-graded LLM judge.

Usage: python scripts/run_eval_suite.py
       python scripts/run_eval_suite.py --category leak
       python scripts/run_eval_suite.py --category injection --strict

--category [leak|injection|persona|all] (default: all) -- ĐỢT 3 #6: restrict
    the run to one group. `leak`/`injection` are the two zero-LLM-quota,
    zero-flakiness deterministic groups (see module docstring above) -- pick
    either for a fast pre-commit/CI check without touching Vertex AI at all.
    `persona` is the one group that calls real Vertex AI and costs quota.
--strict -- exit code 1 if any case in the run failed. Off by default so a
    partial `--category` run during local iteration doesn't fail a shell
    pipeline; pass it explicitly to gate a deploy/CI step on 100% pass, per
    TODO.md PHASE 5's "eval pipeline chay truoc moi lan deploy" framing.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env")

from eval.evalset import (  # noqa: E402
    ANSWER_LEAK_CASES,
    PERSONA_FIDELITY_CASES,
    PROMPT_INJECTION_CASES,
)

_RESULTS_DIR = _ROOT / "eval" / "results"


@dataclass
class CaseResult:
    id: str
    group: str
    passed: bool
    detail: str
    raw_output: dict = field(default_factory=dict)


def run_answer_leak_cases() -> list[CaseResult]:
    from eduagent.nodes.validator import validate_debate_turn

    results = []
    for case in ANSWER_LEAK_CASES:
        outcome = validate_debate_turn(case["text"])
        passed = outcome.passed == case["expect_passed"]
        results.append(
            CaseResult(
                id=case["id"],
                group="answer_leak",
                passed=passed,
                detail=(
                    f"expected passed={case['expect_passed']}, got passed={outcome.passed}"
                    + (f", violations={outcome.violations}" if outcome.violations else "")
                ),
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
                group="prompt_injection",
                passed=passed,
                detail=f"expected blocked={case['expect_blocked']}, got blocked={was_blocked}",
                raw_output={"text": case["text"], "matched_patterns": matches},
            )
        )
    return results


def _matches_signature(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in keywords)


def run_persona_fidelity_cases() -> list[CaseResult]:
    from eduagent.nodes.debate import generate_debate_turn
    from eduagent.nodes.validator import validate_debate_turn

    results = []
    for case in PERSONA_FIDELITY_CASES:
        turns: list[dict] = []
        turn_signature_hits = []
        turn_validator_passed = []

        for turn_number in range(1, 4):
            student_response = case["student_replies"][turn_number - 2] if turn_number > 1 else None
            turn = generate_debate_turn(
                persona_id=case["persona_id"],
                essay_text=case["essay"],
                summary=case["summary"],
                turn_number=turn_number,
                prior_turns=turns,
                student_response=student_response,
                prior_weaknesses=[],
                language="en",
            )
            turns.append(turn)
            turn_signature_hits.append(_matches_signature(turn["question"], case["signature_keywords"]))
            turn_validator_passed.append(validate_debate_turn(turn["question"]).passed)

        # Fidelity bar: the persona's signature must show up in AT LEAST 2 of
        # the 3 turns (not necessarily every single one -- turn 3's "defend or
        # concede" framing per debate_escalation.py can legitimately drop the
        # persona's usual vocabulary while still being in-character) --
        # dropping it in every turn is the real drift failure mode.
        signature_ok = sum(turn_signature_hits) >= 2
        validator_ok = all(turn_validator_passed)
        passed = signature_ok and validator_ok

        results.append(
            CaseResult(
                id=case["id"],
                group="persona_fidelity",
                passed=passed,
                detail=(
                    f"signature hit {sum(turn_signature_hits)}/3 turns (need >=2), "
                    f"validator passed {sum(turn_validator_passed)}/3 turns (need 3/3)"
                ),
                raw_output={"turns": turns, "signature_hits_per_turn": turn_signature_hits},
            )
        )
    return results


def build_report(results: list[CaseResult]) -> dict:
    by_group: dict[str, list[CaseResult]] = {}
    for r in results:
        by_group.setdefault(r.group, []).append(r)

    group_summaries = {}
    for group, group_results in by_group.items():
        passed_count = sum(1 for r in group_results if r.passed)
        group_summaries[group] = {
            "total": len(group_results),
            "passed": passed_count,
            "pass_rate": round(passed_count / len(group_results), 4) if group_results else 0.0,
        }

    return {
        "groups": group_summaries,
        "overall": {
            "total": len(results),
            "passed": sum(1 for r in results if r.passed),
            "pass_rate": round(sum(1 for r in results if r.passed) / len(results), 4) if results else 0.0,
        },
        "cases": [asdict(r) for r in results],
    }


def render_markdown(report: dict) -> str:
    lines = ["# ADK Eval Suite Report", ""]
    lines.append(f"**Overall: {report['overall']['passed']}/{report['overall']['total']} passed ({report['overall']['pass_rate']:.0%})**")
    lines.append("")
    lines.append("| Group | Passed | Total | Pass rate |")
    lines.append("|---|---|---|---|")
    for group, summary in report["groups"].items():
        lines.append(f"| {group} | {summary['passed']} | {summary['total']} | {summary['pass_rate']:.0%} |")
    lines.append("")
    lines.append("## Case detail")
    lines.append("")
    lines.append("| Case | Group | Result | Detail |")
    lines.append("|---|---|---|---|")
    for case in report["cases"]:
        status = "PASS" if case["passed"] else "FAIL"
        lines.append(f"| {case['id']} | {case['group']} | {status} | {case['detail']} |")
    return "\n".join(lines) + "\n"


_CATEGORY_RUNNERS = {
    "leak": ("answer_leak", run_answer_leak_cases),
    "injection": ("prompt_injection", run_prompt_injection_cases),
    "persona": ("persona_fidelity", run_persona_fidelity_cases),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PHASE 5 ADK Eval Suite runner")
    parser.add_argument(
        "--category",
        choices=["leak", "injection", "persona", "all"],
        default="all",
        help="Restrict the run to one case group (default: all). 'leak'/'injection' cost zero Vertex AI quota.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit code 1 if any case in this run failed (use to gate CI/deploy).",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    categories = list(_CATEGORY_RUNNERS) if args.category == "all" else [args.category]

    print(f"Running PHASE 5 ADK Eval Suite (category={args.category})...\n")
    results: list[CaseResult] = []
    for category in categories:
        label, runner = _CATEGORY_RUNNERS[category]
        if label == "persona_fidelity":
            print("  running persona_fidelity (real Vertex AI calls, ~3 turns x 4 personas)...")
        results += runner()
        print(f"  + {label}: {len(results)} cases total so far")

    report = build_report(results)

    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (_RESULTS_DIR / "eval_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (_RESULTS_DIR / "eval_report.md").write_text(render_markdown(report), encoding="utf-8")

    # Windows terminals often default to a non-UTF-8 codepage (cp932/cp1252)
    # that can't encode Vietnamese answer-leak text embedded in the detail
    # column -- degrade to ASCII-safe printing rather than crashing AFTER the
    # report is already safely written to disk.
    try:
        print("\n" + render_markdown(report))
    except UnicodeEncodeError:
        print("\n" + render_markdown(report).encode("ascii", errors="replace").decode("ascii"))
    print(f"Report written to {_RESULTS_DIR / 'eval_report.json'} and eval_report.md")

    if args.strict and report["overall"]["passed"] != report["overall"]["total"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
