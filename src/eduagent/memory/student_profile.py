"""Student profile merge logic -- kept as PURE FUNCTIONS separate from the
Firestore client (PROJECT_WIKI.md 7.5.6: this is the ADK "Memory" layer,
distinct from per-session state -- it must survive across many essays/weeks).

Schema (PROJECT_WIKI.md 8.2), one document per student:
    student_profiles/{student_id}
      name, class_id
      essay_history: [{essay_id, timestamp, persona_used, scores, avg_score,
                        weakness_detected}]
      persona_streak: {current_persona, times_repeated_without_improvement}
      flags: {needs_attention, reason, last_updated}

The pure `merge_essay_into_profile` function is what makes "does the agent
mutate data, not just store it" auditable and unit-testable without a live
Firestore connection.
"""

from __future__ import annotations

STUCK_STREAK_THRESHOLD = 3  # matches PRIORITY_WEIGHTS.stuck_streak semantics (Phase 3)
TREND_WINDOW = 3  # how many recent essays feed score_trend
TREND_FLAT_BAND = 0.3  # avg-score-per-essay change smaller than this counts as "stagnant", not noise

# ĐỢT 3 #3: cap essay_history so the Firestore document (1MB hard limit) stays
# bounded across hundreds of essays. Everything score_trend/persona_streak
# need only ever looks at the tail (TREND_WINDOW / the single previous
# essay), so trimming the head is safe -- the two cumulative counters below
# preserve what would otherwise be lost from the trimmed-off entries.
MAX_HISTORY_ENTRIES = 50


def empty_profile(*, name: str, class_id: str) -> dict:
    return {
        "name": name,
        "class_id": class_id,
        "essay_history": [],
        "persona_streak": {"current_persona": None, "times_repeated_without_improvement": 0},
        "flags": {"needs_attention": False, "reason": "", "last_updated": None},
        "score_trend": "insufficient_data",
        "total_essays_count": 0,
        "all_time_weaknesses": [],
    }


def _avg(scores: dict) -> float:
    return sum(scores.values()) / len(scores) if scores else 0.0


def _score_trend(essay_history: list[dict]) -> str:
    """'improving' / 'declining' / 'stagnant' / 'insufficient_data', from the
    average slope of the last TREND_WINDOW essays' avg_score. Feeds directly
    into the Intervention Priority Index's score_decline weight in Phase 3."""
    recent = [e["avg_score"] for e in essay_history[-TREND_WINDOW:]]
    if len(recent) < 2:
        return "insufficient_data"
    diffs = [recent[i + 1] - recent[i] for i in range(len(recent) - 1)]
    avg_diff = sum(diffs) / len(diffs)
    if avg_diff > TREND_FLAT_BAND:
        return "improving"
    if avg_diff < -TREND_FLAT_BAND:
        return "declining"
    return "stagnant"


def merge_essay_into_profile(
    profile: dict,
    *,
    essay_id: str,
    timestamp: str,
    persona_used: str,
    scores: dict,
    weakness_detected: list[str],
    student_feedback: str = "",
) -> dict:
    """Pure function: old profile + one essay's results -> new profile.

    No Firestore, no network -- this is what nodes/persona_selector.py and
    nodes/mutator.py actually reason over; the Firestore wrapper below only
    handles the read-then-write plumbing around it.
    """
    avg_score = _avg(scores)
    essay_history = list(profile.get("essay_history", []))
    essay_history.append(
        {
            "essay_id": essay_id,
            "timestamp": timestamp,
            "persona_used": persona_used,
            "scores": scores,
            "avg_score": avg_score,
            "weakness_detected": weakness_detected,
            "student_feedback": student_feedback,
        }
    )

    prior_streak = profile.get("persona_streak") or {"current_persona": None, "times_repeated_without_improvement": 0}
    prior_avg = essay_history[-2]["avg_score"] if len(essay_history) >= 2 else None

    same_persona_no_improvement = (
        prior_streak.get("current_persona") == persona_used
        and prior_avg is not None
        and avg_score <= prior_avg
    )
    times_repeated = (prior_streak.get("times_repeated_without_improvement", 0) + 1) if same_persona_no_improvement else 0

    persona_streak = {"current_persona": persona_used, "times_repeated_without_improvement": times_repeated}

    needs_attention = times_repeated >= STUCK_STREAK_THRESHOLD
    flags = {
        "needs_attention": needs_attention,
        "reason": (
            f"stuck on persona '{persona_used}' for {times_repeated + 1} consecutive "
            "essays without score improvement"
            if needs_attention
            else ""
        ),
        "last_updated": timestamp,
    }

    score_trend = _score_trend(essay_history)
    total_essays_count = profile.get("total_essays_count", len(profile.get("essay_history", []))) + 1

    all_time_weaknesses = list(profile.get("all_time_weaknesses", []))
    seen_weaknesses = set(all_time_weaknesses)
    for w in weakness_detected:
        if w not in seen_weaknesses:
            seen_weaknesses.add(w)
            all_time_weaknesses.append(w)

    # Trim AFTER computing streak/trend (both only ever look at the tail) so
    # a document that has accumulated hundreds of essays doesn't grow
    # unbounded -- see MAX_HISTORY_ENTRIES.
    if len(essay_history) > MAX_HISTORY_ENTRIES:
        essay_history = essay_history[-MAX_HISTORY_ENTRIES:]

    return {
        **profile,
        "essay_history": essay_history,
        "persona_streak": persona_streak,
        "flags": flags,
        "score_trend": score_trend,
        "total_essays_count": total_essays_count,
        "all_time_weaknesses": all_time_weaknesses,
    }


def persona_history_from_profile(profile: dict) -> list[str]:
    return [e["persona_used"] for e in profile.get("essay_history", [])]


def weakness_taxonomy_from_profile(profile: dict) -> list[str]:
    """Flattened, de-duplicated (order-preserving) weaknesses across all
    essays -- including ones trimmed off `essay_history` by MAX_HISTORY_ENTRIES,
    since `all_time_weaknesses` is the cumulative counter for exactly that
    case. Falls back to scanning essay_history for profiles written before
    that field existed."""
    if "all_time_weaknesses" in profile:
        return list(profile["all_time_weaknesses"])
    seen: dict[str, None] = {}
    for essay in profile.get("essay_history", []):
        for w in essay.get("weakness_detected", []):
            seen.setdefault(w, None)
    return list(seen.keys())
