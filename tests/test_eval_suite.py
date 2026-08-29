"""Unit tests for the eval suite's deterministic groups (answer_leak,
prompt_injection) -- fast, zero LLM. persona_fidelity hits real Vertex AI
(scripts/run_eval_suite.py itself, not covered here -- see eval_report.md
for its real, committed results) so it's exercised by running the script
directly, not by the fast test suite.
"""

from __future__ import annotations

from eval.evalset import ANSWER_LEAK_CASES, PROMPT_INJECTION_CASES
from scripts.run_eval_suite import run_answer_leak_cases, run_prompt_injection_cases


def test_answer_leak_cases_all_pass_against_real_validator():
    results = run_answer_leak_cases()
    assert len(results) == len(ANSWER_LEAK_CASES)
    failed = [r for r in results if not r.passed]
    assert not failed, f"eval regressions in answer_leak group: {failed}"


def test_prompt_injection_cases_all_pass_against_real_sanitizer():
    results = run_prompt_injection_cases()
    assert len(results) == len(PROMPT_INJECTION_CASES)
    failed = [r for r in results if not r.passed]
    assert not failed, f"eval regressions in prompt_injection group: {failed}"
