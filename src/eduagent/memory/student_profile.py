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

# ĐỢT 15 #3: how far the window may swing peak-to-trough before a flat slope is
# reported as "volatile" rather than "stagnant". 2.0 points on the 0-10 avg_score
# scale is roughly a whole grade band collapsing and recovering -- large enough
# not to fire on ordinary essay-to-essay noise, small enough to catch the [10, 0,
# 10] case the audit raised.
TREND_VOLATILITY_BAND = 2.0

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


def _trend_slope(recent: list[float]) -> float:
    """Least-squares slope (avg_score points gained per essay) over `recent`.

    ĐỢT 15 #3 replaced `sum(diffs) / len(diffs)` here. That expression telescopes
    -- (x1-x0) + (x2-x1) collapses to x2-x0 -- so it was only ever reading the
    first and last essay in the window and every essay between them cancelled
    out. For TREND_WINDOW == 3 an OLS fit happens to give the identical number
    ((y2-y0)/2), so this is not by itself a behaviour change; what it fixes is
    that the code now MEANS the slope it computes, and stays correct if anyone
    widens TREND_WINDOW. The audit's real complaint -- that a mid-window
    collapse is invisible -- is a property of a slope, not of this arithmetic,
    and is answered by the volatility branch in _score_trend() below.
    """
    n = len(recent)
    mean_x = (n - 1) / 2.0
    mean_y = sum(recent) / n
    numerator = sum((i - mean_x) * (y - mean_y) for i, y in enumerate(recent))
    denominator = sum((i - mean_x) ** 2 for i in range(n))
    return numerator / denominator if denominator else 0.0


def _score_trend(essay_history: list[dict]) -> str:
    """'improving' / 'declining' / 'volatile' / 'stagnant' / 'insufficient_data'
    over the last TREND_WINDOW essays' avg_score. Feeds directly into the
    Intervention Priority Index's score_decline / score_volatility weights.

    'volatile' (ĐỢT 15 #3) exists because a slope alone cannot see a dip that
    recovered: a student scoring [10, 0, 10] has a genuinely flat trend, and the
    old code called that "stagnant" -- indistinguishable from [5, 5, 5], with the
    same zero contribution to the teacher's ranking. But the flat one deserves
    no attention and the one who collapsed for a whole essay clearly does. So
    the slope keeps its honest meaning and the swing is reported as its own
    signal rather than being smuggled into "declining", which would tell the
    teacher something untrue about the direction the student is heading.
    """
    recent = [e["avg_score"] for e in essay_history[-TREND_WINDOW:]]
    if len(recent) < 2:
        return "insufficient_data"
    slope = _trend_slope(recent)
    if slope > TREND_FLAT_BAND:
        return "improving"
    if slope < -TREND_FLAT_BAND:
        return "declining"
    if max(recent) - min(recent) >= TREND_VOLATILITY_BAND:
        return "volatile"
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
    if profile.get("all_time_weaknesses"):
        return list(profile["all_time_weaknesses"])
    seen: dict[str, None] = {}
    for essay in profile.get("essay_history", []):
        for w in essay.get("weakness_detected", []):
            seen.setdefault(w, None)
    return list(seen.keys())


def merge_reflection_into_profile(
    profile: dict,
    *,
    reflection_text: str,
    original_fallacy: str,
    resolved: bool,
    growth_bonus: float,
    timestamp: str,
) -> dict:
    """Pure function: old profile + student's post-debate self-correction -> new profile.

    Appends to reflections_history and sets metacognitive_growth metrics.
    Preserves all existing profile fields without breaking backward compatibility.
    """
    reflections = list(profile.get("reflections_history", []))
    reflections.append(
        {
            "timestamp": timestamp,
            "reflection_text": reflection_text,
            "original_fallacy": original_fallacy,
            "resolved": resolved,
            "growth_bonus": growth_bonus,
        }
    )
    if len(reflections) > MAX_HISTORY_ENTRIES:
        reflections = reflections[-MAX_HISTORY_ENTRIES:]

    total_growth = profile.get("total_growth_bonus", 0.0) + (growth_bonus if resolved else 0.0)
    breakthrough_count = profile.get("breakthrough_count", 0) + (1 if resolved else 0)

    return {
        **profile,
        "reflections_history": reflections,
        "total_growth_bonus": round(total_growth, 2),
        "breakthrough_count": breakthrough_count,
        "last_reflection": {
            "timestamp": timestamp,
            "resolved": resolved,
            "original_fallacy": original_fallacy,
            "growth_bonus": growth_bonus,
        },
    }

