"""Phase 2 seed data: 5 student profiles with varied history, per
the Phase 2 spec, so Phase 3's Class Aggregator has something real to
rank against during development and the demo video.

Profiles (all in class 'c1'):
  stu_improving   - steadily improving scores, persona rotates normally
  stu_stuck       - stuck on 'skeptic' for 4 essays with no improvement
                    (should trip needs_attention)
  stu_declining   - average score trending down across recent essays
  stu_inactive    - only 1 essay, a while ago (long-inactivity case)
  stu_common_fallacy - shares a fallacy ("hasty generalization") with
                    stu_stuck, for Systemic Fallacy Clustering in Phase 3

Writes real documents to the Firestore project configured in .env. Safe to
rerun -- each profile is fully overwritten (not appended) via empty_profile
+ replay, so this script is idempotent.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

from google.cloud import firestore  # noqa: E402

from eduagent.config import FIRESTORE  # noqa: E402
from eduagent.memory.student_profile import empty_profile, merge_essay_into_profile  # noqa: E402

NOW = datetime(2026, 8, 24, tzinfo=timezone.utc)


def _ts(days_ago: int) -> str:
    return (NOW - timedelta(days=days_ago)).isoformat()


def _scores(avg: int) -> dict:
    return {
        "logical_coherence": avg,
        "evidence_quality": avg,
        "counterargument_handling": avg,
        "scope_awareness": avg,
    }


def _replay(name: str, class_id: str, essays: list[dict]) -> dict:
    profile = empty_profile(name=name, class_id=class_id)
    for i, e in enumerate(essays):
        profile = merge_essay_into_profile(
            profile,
            essay_id=f"seed_{name}_{i}",
            timestamp=e["timestamp"],
            persona_used=e["persona_used"],
            scores=e["scores"],
            weakness_detected=e["weakness_detected"],
        )
    return profile


SEED_PROFILES: dict[str, dict] = {
    "stu_improving": _replay(
        "Mia",
        "c1",
        [
            {"timestamp": _ts(20), "persona_used": "skeptic", "scores": _scores(4), "weakness_detected": ["unsourced claim"]},
            {"timestamp": _ts(13), "persona_used": "nitpicker", "scores": _scores(6), "weakness_detected": ["non sequitur"]},
            {"timestamp": _ts(6), "persona_used": "expander", "scores": _scores(8), "weakness_detected": []},
        ],
    ),
    "stu_stuck": _replay(
        "Tom",
        "c1",
        [
            {"timestamp": _ts(28), "persona_used": "skeptic", "scores": _scores(5), "weakness_detected": ["hasty generalization"]},
            {"timestamp": _ts(21), "persona_used": "skeptic", "scores": _scores(5), "weakness_detected": ["hasty generalization"]},
            {"timestamp": _ts(14), "persona_used": "skeptic", "scores": _scores(4), "weakness_detected": ["hasty generalization"]},
            {"timestamp": _ts(7), "persona_used": "skeptic", "scores": _scores(4), "weakness_detected": ["hasty generalization"]},
        ],
    ),
    "stu_declining": _replay(
        "Jerry",
        "c1",
        [
            {"timestamp": _ts(18), "persona_used": "devils_advocate", "scores": _scores(8), "weakness_detected": []},
            {"timestamp": _ts(11), "persona_used": "nitpicker", "scores": _scores(6), "weakness_detected": ["non sequitur"]},
            {"timestamp": _ts(4), "persona_used": "expander", "scores": _scores(3), "weakness_detected": ["scope too narrow"]},
        ],
    ),
    "stu_inactive": _replay(
        "David",
        "c1",
        [
            {"timestamp": _ts(45), "persona_used": "skeptic", "scores": _scores(5), "weakness_detected": ["unsourced claim"]},
        ],
    ),
    "stu_common_fallacy": _replay(
        "Emma",
        "c1",
        [
            {"timestamp": _ts(15), "persona_used": "skeptic", "scores": _scores(5), "weakness_detected": ["hasty generalization"]},
            {"timestamp": _ts(8), "persona_used": "devils_advocate", "scores": _scores(6), "weakness_detected": ["hasty generalization"]},
        ],
    ),
    "c1_stu01": _replay(
        "Alice",
        "c1",
        [
            {"timestamp": _ts(10), "persona_used": "skeptic", "scores": _scores(7), "weakness_detected": ["unsourced claim"]},
            {"timestamp": _ts(2), "persona_used": "expander", "scores": _scores(8), "weakness_detected": []},
        ],
    ),
    "c1_stu02": _replay(
        "Bob",
        "c1",
        [
            {"timestamp": _ts(12), "persona_used": "devils_advocate", "scores": _scores(6), "weakness_detected": ["hasty generalization"]},
            {"timestamp": _ts(5), "persona_used": "skeptic", "scores": _scores(5), "weakness_detected": ["hasty generalization"]},
        ],
    ),
}


def main() -> None:
    db = firestore.Client()
    coll = db.collection(FIRESTORE.student_profiles_collection)
    for student_id, profile in SEED_PROFILES.items():
        coll.document(student_id).set(profile)
        streak = profile["persona_streak"]
        print(f"[OK] seeded {student_id} ({profile['name']}): {len(profile['essay_history'])} essays, "
              f"streak={streak}, needs_attention={profile['flags']['needs_attention']}")

    print(f"\nSeeded {len(SEED_PROFILES)} student profiles into "
          f"'{FIRESTORE.student_profiles_collection}' (project from .env).")


if __name__ == "__main__":
    main()
