"""Learning Outcome & Cognitive Growth Measurement (Task 10.2).

MEASURES the learning-outcome delta (Before vs After) across the 4 cognitive
dimensions by running the REAL production scorer on both texts:

    initial_thesis  --summarize_essay()--> summary --score_essay()--> before
    revised_thesis  --summarize_essay()--> summary --score_essay()--> after

ĐỢT 12 NHÓM 1 fix (option A): this script previously carried `before_scores`
and `after_scores` as hand-typed literals and merely subtracted them, then the
report called the result "Giá Trị Đo Được" / "Chấm lại độc lập". Nothing was
measured and nothing was re-scored -- the headline number was the mean of 16
integers chosen by the author. Every number below now comes from a live
Gemini call through `nodes/scorer.py::score_essay()`, the exact same prompt,
schema and model the production `cognitive_scorer` graph node uses.

MEASUREMENT DESIGN (stated so the numbers can be read correctly):
  - Both texts are scored by the SAME production scorer with an EMPTY debate
    transcript, so the only variable between `before` and `after` is the text
    itself. The scorer is never told which text is the "revised" one, never
    shown the Socratic probe, and never shown the other text -- so it cannot
    infer that it is expected to award a higher score.
  - `summarize_essay()` runs on each text independently too (no hand-fed
    fallacy labels), so the scorer's input is produced the same way it is in
    production rather than being pre-annotated in this file.
  - n = 8 controlled thesis pairs written by the author (NOT 8 real students).
    This measures "does the production scorer register the cognitive
    improvement between a weak thesis and its Socratically-revised form",
    which is a real measurement of the scorer on controlled inputs -- it is
    NOT a longitudinal study of real classroom learning gains.
  - LLM scores are non-deterministic. `--runs N` scores each text N times and
    averages, which is why the report states the run count.

Output artifacts:
  - docs/learning_outcome_eval.md                    (human-readable report)
  - eval/results/learning_outcome_measured.json      (machine-readable; the
    ADK Eval Suite's Layer 4 asserts against THIS file rather than against
    literals, so Layer 4 can actually fail)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(_PROJECT_ROOT / ".env")

import eduagent  # noqa: F401 -- applies the GAPIC routing-header patch before any GCP SDK call

from eduagent.nodes.scorer import score_essay
from eduagent.nodes.summarizer import summarize_essay

_MEASURED_JSON = _PROJECT_ROOT / "eval" / "results" / "learning_outcome_measured.json"

_AXES = ("logical_coherence", "evidence_quality", "counterargument_handling", "scope_awareness")

# 8 controlled thesis pairs covering all 4 Socratic personas / cognitive axes.
# These are INPUTS to the measurement -- no scores are declared here.
BENCHMARK_SCENARIOS = [
    {
        "id": "scenario_01_evidence_skeptic",
        "topic": "Electric Vehicle Emissions",
        "dimension_targeted": "evidence_quality",
        "persona_used": "skeptic",
        "initial_thesis": "Electric cars are completely clean and produce zero pollution anywhere.",
        "diagnosed_fallacy": "unsupported claim / lack of evidence",
        "socratic_probe": "What empirical data accounts for battery manufacturing and electricity grid sources?",
        "revised_thesis": "While EVs produce zero tailpipe emissions, lifecycle studies show a 40-60% net reduction in carbon emissions depending on whether regional grid electricity comes from renewables.",
    },
    {
        "id": "scenario_02_counterarg_devils_advocate",
        "topic": "AI in High School Classrooms",
        "dimension_targeted": "counterargument_handling",
        "persona_used": "devils_advocate",
        "initial_thesis": "AI writing tools must be encouraged for all assignments because technology is the future.",
        "diagnosed_fallacy": "one-sided bias / ignoring drawbacks",
        "socratic_probe": "What would educators concerned with critical thinking decay argue, and how do you prevent overreliance?",
        "revised_thesis": "AI tools should be integrated as collaborative brainstorming aids rather than essay generators, paired with oral defenses to preserve critical reasoning.",
    },
    {
        "id": "scenario_03_logic_nitpicker",
        "topic": "Homework Policy Reform",
        "dimension_targeted": "logical_coherence",
        "persona_used": "nitpicker",
        "initial_thesis": "Students feel stressed on Mondays, so all homework across K-12 education should be abolished immediately.",
        "diagnosed_fallacy": "non sequitur / leaping assumption",
        "socratic_probe": "Where is the logical bridge between Monday stress and the complete elimination of skill practice across all subjects?",
        "revised_thesis": "Because excessive repetitive homework correlates with stress without improving retention in early grades, daily homework should be capped at 10 minutes per grade level and focused on conceptual practice.",
    },
    {
        "id": "scenario_04_scope_expander",
        "topic": "Social Media Age Restrictions",
        "dimension_targeted": "scope_awareness",
        "persona_used": "expander",
        "initial_thesis": "Social media destroys every teenager's mental health without exception.",
        "diagnosed_fallacy": "hasty generalization / universal overstatement",
        "socratic_probe": "Does this hold equally for creative and educational peer communities, or does harm depend on algorithmic design and screen time duration?",
        "revised_thesis": "High-frequency consumption of algorithmic feeds with engagement-maximizing loops significantly increases adolescent anxiety, while moderated interest-based communities show neutral to positive peer support effects.",
    },
    {
        "id": "scenario_05_evidence_popularity",
        "topic": "Renewable Energy Transition",
        "dimension_targeted": "evidence_quality",
        "persona_used": "skeptic",
        "initial_thesis": "Solar panels are obviously the best energy source because all my friends are getting them.",
        "diagnosed_fallacy": "appeal to popularity / anecdotal proof",
        "socratic_probe": "Beyond popularity, what levelized cost of energy (LCOE) metrics and storage requirements prove feasibility for baseload power?",
        "revised_thesis": "According to IRENA 2024 data, utility-scale solar PV has achieved an LCOE of $0.04/kWh, making it economically competitive when paired with grid-scale battery storage for intermittent demand.",
    },
    {
        "id": "scenario_06_counterarg_nuclear",
        "topic": "Nuclear Energy in Clean Grids",
        "dimension_targeted": "counterargument_handling",
        "persona_used": "devils_advocate",
        "initial_thesis": "Nuclear energy is completely unsafe and should be shut down everywhere.",
        "diagnosed_fallacy": "false dichotomy / fear appeal",
        "socratic_probe": "How do you reconcile this with modern Generation IV reactor safety records and IPCC findings on zero-carbon firm energy needs?",
        "revised_thesis": "While long-term waste management and high upfront capital remain critical challenges, modern passively safe reactors provide vital zero-emission firm power to complement intermittent renewables.",
    },
    {
        "id": "scenario_07_logic_correlation",
        "topic": "Video Games and Academic Performance",
        "dimension_targeted": "logical_coherence",
        "persona_used": "nitpicker",
        "initial_thesis": "Tim started playing video games and his math score dropped, so gaming causes academic failure.",
        "diagnosed_fallacy": "post hoc ergo propter hoc",
        "socratic_probe": "What confounding variables (sleep, study hours, curriculum difficulty) were ruled out before claiming direct causation?",
        "revised_thesis": "While unmoderated late-night screen time disrupts sleep and reduces study hours leading to grade declines, moderate gaming shows no statistically significant causal negative impact on cognitive skills.",
    },
    {
        "id": "scenario_08_scope_remote_work",
        "topic": "Universal Remote Work",
        "dimension_targeted": "scope_awareness",
        "persona_used": "expander",
        "initial_thesis": "All companies must switch 100% to remote work permanently because in-person offices are obsolete.",
        "diagnosed_fallacy": "sweeping generalization",
        "socratic_probe": "Does this model function effectively for hardware engineering, healthcare, and onboarding junior employees?",
        "revised_thesis": "While knowledge-work tasks benefit from remote autonomy and reduced commute friction, hybrid models remain optimal for sectors requiring physical collaboration, specialized equipment, and intensive junior mentorship.",
    },
]


class MeasurementError(RuntimeError):
    """Raised when the scorer degraded -- we refuse to emit a fabricated number."""


def _measure_text(text: str, *, label: str, runs: int) -> dict:
    """Runs the real production summarizer + scorer `runs` times and returns
    the per-axis mean. Raises rather than substituting a fake score if Gemini
    degrades -- the whole point of this rewrite is that no number in the
    output is invented."""
    per_run: list[dict] = []
    for i in range(runs):
        summary, summary_degraded = summarize_essay(text)
        if summary_degraded:
            raise MeasurementError(f"Summarizer degraded while measuring {label} (run {i + 1}/{runs}).")
        scores, _rationale, _feedback, degraded = score_essay(
            essay_text=text,
            summary=summary,
            debate_turns=[],  # deliberately empty -- see MEASUREMENT DESIGN
        )
        if degraded:
            raise MeasurementError(f"Scorer degraded while measuring {label} (run {i + 1}/{runs}).")
        per_run.append(scores)

    return {axis: round(sum(r[axis] for r in per_run) / len(per_run), 2) for axis in _AXES}


def evaluate_learning_outcomes(*, runs: int = 1, verbose: bool = True) -> dict:
    evaluated = []
    total_delta_targeted = 0.0
    total_delta_overall = 0.0

    for idx, s in enumerate(BENCHMARK_SCENARIOS, start=1):
        if verbose:
            print(f"  [{idx}/{len(BENCHMARK_SCENARIOS)}] scoring {s['id']} ...", flush=True)

        before_scores = _measure_text(s["initial_thesis"], label=f"{s['id']}:before", runs=runs)
        after_scores = _measure_text(s["revised_thesis"], label=f"{s['id']}:after", runs=runs)

        dim = s["dimension_targeted"]
        before_val = before_scores[dim]
        after_val = after_scores[dim]
        delta_targeted = round(after_val - before_val, 2)

        before_avg = round(sum(before_scores.values()) / len(before_scores), 2)
        after_avg = round(sum(after_scores.values()) / len(after_scores), 2)
        delta_avg = round(after_avg - before_avg, 2)

        # The only claim this measurement supports: the production scorer
        # registers improvement on the axis the Socratic probe targeted.
        # Deliberately NOT "after >= 7" -- an absolute-quality threshold on
        # an author-written revision measures the author, not the system.
        passed = delta_targeted > 0

        total_delta_targeted += delta_targeted
        total_delta_overall += delta_avg

        evaluated.append({
            "id": s["id"],
            "topic": s["topic"],
            "dimension": dim,
            "persona": s["persona_used"],
            "before_score": before_val,
            "after_score": after_val,
            "delta_targeted": delta_targeted,
            "before_scores": before_scores,
            "after_scores": after_scores,
            "before_avg": before_avg,
            "after_avg": after_avg,
            "delta_avg": delta_avg,
            "passed": passed,
            "initial_thesis": s["initial_thesis"],
            "revised_thesis": s["revised_thesis"],
        })
        if verbose:
            print(f"      {dim}: {before_val} -> {after_val}  (delta {delta_targeted:+})", flush=True)

    n = len(BENCHMARK_SCENARIOS)
    return {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "runs_per_text": runs,
        "scorer": "nodes/scorer.py::score_essay (production prompt/schema, Gemini via Vertex AI)",
        "all_passed": all(e["passed"] for e in evaluated),
        "total_scenarios": n,
        "pass_count": sum(1 for e in evaluated if e["passed"]),
        "avg_targeted_growth": round(total_delta_targeted / n, 2),
        "avg_overall_growth": round(total_delta_overall / n, 2),
        "evaluations": evaluated,
    }


def generate_markdown_report(results: dict) -> str:
    avg_targeted = results["avg_targeted_growth"]
    avg_overall = results["avg_overall_growth"]
    pass_cnt = results["pass_count"]
    total_cnt = results["total_scenarios"]
    runs = results["runs_per_text"]
    pass_pct = f"{pass_cnt / total_cnt:.0%}" if total_cnt else "0%"

    md = f"""# Learning-Outcome Measurement: Does the scorer register cognitive growth?

> **What this measures:** each of 8 controlled thesis pairs (a weak thesis and
> its Socratically-revised form) is put through the **real production path** --
> `summarize_essay()` then `score_essay()` (`src/eduagent/nodes/scorer.py`,
> Gemini via Vertex AI) -- and the per-axis delta is recorded.
>
> **What this does NOT measure:** real classroom learning gains. n = 8 author-written
> thesis pairs, not 8 students. See "Measurement design & limitations" below before
> quoting any number from this file.

*Measured at {results["measured_at"]} · {runs} scoring run(s) per text · scorer: `{results["scorer"]}`*

---

## 1. Measured Summary

| Metric | Measured value | Threshold | Result |
|---|:---:|:---:|:---:|
| Scenarios where the targeted axis improved | **{pass_cnt}/{total_cnt} ({pass_pct})** | > 0 delta | **{"PASS" if results["all_passed"] else "PARTIAL"}** |
| Mean delta on the targeted axis | **{avg_targeted:+} / 10** | > +1.0 | **{"PASS" if avg_targeted > 1.0 else "FAIL"}** |
| Mean delta across all 4 axes | **{avg_overall:+} / 10** | > +0.5 | **{"PASS" if avg_overall > 0.5 else "FAIL"}** |
| Independent re-scoring (no debate transcript, no cross-text context) | **Yes -- both texts scored by the same production scorer** | — | **VERIFIED** |

---

## 2. Per-scenario measurement (all values produced by live scorer calls)

| Scenario & topic | Targeted axis | Persona | Before | After | Delta | Status |
|---|---|---|:---:|:---:|:---:|:---:|
"""
    for e in results["evaluations"]:
        md += (
            f"| **{e['topic']}** | `{e['dimension']}` | `{e['persona']}` | {e['before_score']}/10 | "
            f"{e['after_score']}/10 | **{e['delta_targeted']:+}** | {'PASS' if e['passed'] else 'FAIL'} |\n"
        )

    md += """
### Full 4-axis breakdown

| Scenario | Axis | Before | After | Delta |
|---|---|:---:|:---:|:---:|
"""
    for e in results["evaluations"]:
        for axis in _AXES:
            b = e["before_scores"][axis]
            a = e["after_scores"][axis]
            marker = " ⟵ targeted" if axis == e["dimension"] else ""
            md += f"| `{e['id']}` | `{axis}`{marker} | {b} | {a} | {round(a - b, 2):+} |\n"

    md += """
---

## 3. Case studies (thesis text is the input; scores are the measurement)

"""
    icons = {"evidence_quality": "🔬", "counterargument_handling": "😈", "logical_coherence": "🔍", "scope_awareness": "🌌"}
    seen_axes: set[str] = set()
    for e in results["evaluations"]:
        if e["dimension"] in seen_axes:
            continue
        seen_axes.add(e["dimension"])
        md += (
            f"### {icons.get(e['dimension'], '•')} {e['dimension']} (`{e['persona']}`)\n"
            f"* **Before:** *\"{e['initial_thesis']}\"* — measured **{e['before_score']}/10**\n"
            f"* **After Socratic revision:** *\"{e['revised_thesis']}\"* — measured **{e['after_score']}/10**\n"
            f"* **Measured delta:** **{e['delta_targeted']:+} points**\n\n"
        )

    md += f"""---

## 4. Measurement design & limitations (read this before quoting a number)

**How it was measured.** For each scenario, both the initial thesis and the revised
thesis are pushed through the production summarizer and then the production scorer
with an **empty debate transcript**. The scorer sees one text at a time, is never
told which one is the revision, and never sees the Socratic probe -- so it cannot
infer that a higher score is expected. Every number in this document is the output
of a live Gemini call; none is written by hand.

**What the numbers support.** That the deterministic-first pipeline's scorer
*detects* the specific cognitive improvement each persona targets, at a mean of
{avg_targeted:+} points on the targeted axis across {total_cnt} scenarios.

**What the numbers do NOT support.**
1. **n = {total_cnt} controlled thesis pairs, not {total_cnt} students.** The revised theses were
   written by the project author as exemplars of a successful Socratic outcome. This
   is a measurement of the *scorer*, on controlled inputs -- not evidence that real
   students improve by this much.
2. **No control group and no longitudinal data.** A classroom study would need real
   student revisions, a control condition, and repeated measurement over time.
3. **LLM scoring is non-deterministic.** This run used {runs} scoring run(s) per text;
   re-running will move the numbers. That is why the run count and timestamp are
   stamped at the top of this file rather than the numbers being treated as fixed.

**Related, and stronger, evidence.** `scripts/experiment_memory_ab.py` A/B-tests the
real `choose_persona()` and `compute_priority()` production logic, and the ADK Eval
Suite's Layers 1-3 assert against real production functions. Those are deterministic
and reproducible; this document is a live-model measurement and should be cited as one.
"""
    return md


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Measure learning-outcome deltas with the real production scorer")
    parser.add_argument("--output", default="docs/learning_outcome_eval.md", help="Path to output report")
    parser.add_argument("--runs", type=int, default=1, help="Scoring runs per text (averaged); >1 reduces LLM variance")
    args = parser.parse_args()

    print(f"[*] Measuring learning outcomes via live scorer ({len(BENCHMARK_SCENARIOS)} scenarios x 2 texts x {args.runs} run(s))...")
    try:
        results = evaluate_learning_outcomes(runs=args.runs)
    except MeasurementError as exc:
        print(f"[FAIL] {exc}")
        print("[FAIL] Refusing to write a report containing numbers the scorer did not actually produce.")
        sys.exit(1)

    report_md = generate_markdown_report(results)

    output_path = _PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_md, encoding="utf-8")

    _MEASURED_JSON.parent.mkdir(parents=True, exist_ok=True)
    _MEASURED_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    pct = f"{results['pass_count'] / results['total_scenarios']:.0%}"
    print(f"\n[OK] Measured: targeted axis improved in {results['pass_count']}/{results['total_scenarios']} scenarios ({pct})")
    print(f"[OK] Mean measured delta on targeted axis: {results['avg_targeted_growth']:+} / 10")
    print(f"[OK] Mean measured delta across all axes:  {results['avg_overall_growth']:+} / 10")
    print(f"[OK] Report saved to:   {output_path}")
    print(f"[OK] Measured data:     {_MEASURED_JSON}  (consumed by eval suite Layer 4)")


if __name__ == "__main__":
    main()
