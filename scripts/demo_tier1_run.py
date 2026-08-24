"""Manual demo run of the Tier 1 pipeline against real Vertex AI + Firestore.

Runs the SAME student through 3 different mock essays to prove the memory
loop actually works: the Persona Selector must read Firestore history before
choosing (Phase 2), so persona choice and weakness tracking should evolve
across calls instead of resetting each time. This is the direct evidence for
the track's "become more helpful over time" requirement -- not a unit test,
meant to be eyeballed.
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

from eduagent.graph.tier1_pipeline import build_tier1_workflow  # noqa: E402

MOCK_ESSAYS = [
    (
        "Homework should be banned in all schools. Everyone knows kids need free time "
        "to be happy, and my cousin never does homework and he is doing great in life. "
        "So clearly homework does not actually help anyone learn anything."
    ),
    (
        "Social media is destroying teenagers' attention spans. Every teenager I know "
        "spends hours a day on their phone, so it must be true for all teenagers "
        "everywhere in the world."
    ),
    (
        "School uniforms should be required because they make students look more "
        "professional and every student I've talked to at my school agrees they "
        "reduce bullying about clothes."
    ),
]


async def run_one_essay(app_name: str, student_id: str, essay_text: str) -> dict:
    workflow = build_tier1_workflow()
    runner = InMemoryRunner(node=workflow, app_name=app_name)
    session_id = f"demo-session-{uuid.uuid4().hex[:8]}"

    await runner.session_service.create_session(
        app_name=app_name,
        user_id=student_id,
        session_id=session_id,
        state={"student_id": student_id, "student_name": "Demo Student", "class_id": "demo_class"},
    )

    events = []
    async for event in runner.run_async(
        user_id=student_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=essay_text)]),
    ):
        events.append(event)

    return events[-1].output


async def main() -> None:
    student_id = f"demo_student_{uuid.uuid4().hex[:6]}"
    print(f"Running 3 essays for a fresh student: {student_id}\n")

    for i, essay in enumerate(MOCK_ESSAYS, start=1):
        output = await run_one_essay("eduagent-tier1-demo", student_id, essay)
        print(f"--- Essay {i} ---")
        print("persona chosen:", output["persona"])
        print("persona_history seen by selector (before this essay):", end=" ")
        print(output.get("profile_after_mutation", {}).get("persona_streak"))
        print("scores:", output["scores"])
        print()

    final_profile = output.get("profile_after_mutation")
    print("=== Final Firestore profile after 3 essays ===")
    print(json.dumps(final_profile, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
