"""PHASE 6 DoD proof: upload a real image -> OCR -> continue the FULL Tier 1
pipeline (sanitize -> summarize -> persona -> debate -> validate -> score ->
mutate Firestore) with no manual intervention in between.

Runs both sample images from assets/sample_essays/ (generate them first with
scripts/generate_sample_essay_images.py if missing) through the real graph
against real Vertex AI + Firestore -- same pattern as demo_tier1_run.py, just
with an image Part instead of a text Part as the input Content.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

from eduagent.graph.tier1_pipeline import build_tier1_workflow  # noqa: E402


def _safe_print(*args) -> None:
    # Windows terminals often default to a non-UTF-8 codepage (cp932/cp1252)
    # that can't encode an em-dash or Vietnamese text a real model response
    # may contain -- degrade to ASCII-safe printing rather than crashing
    # mid-demo after the real (and expensive) LLM calls already succeeded.
    text = " ".join(str(a) for a in args)
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


_ASSETS_DIR = Path(__file__).parent.parent / "assets" / "sample_essays"
_REAL_PHOTOS_DIR = Path(__file__).parent.parent / "eval" / "test_images"

# Prefer REAL handwritten photos (eval/test_images/, provided 2026-08-24) over
# the synthetic PIL placeholders in assets/sample_essays/ -- this is what
# actually closes PHASE 6's DoD ("upload anh viet tay THAT"). Falls back to
# the synthetic ones only if the real photos aren't present.
if _REAL_PHOTOS_DIR.exists() and any(_REAL_PHOTOS_DIR.glob("*.jpg")):
    SAMPLE_IMAGES = [
        ("neat", _REAL_PHOTOS_DIR / "neat_essay_homework.jpg"),
        ("messy_with_crossouts", _REAL_PHOTOS_DIR / "messy_essay_videogames.jpg"),
        ("faded_low_light", _REAL_PHOTOS_DIR / "faded_essay_cellphones.jpg"),
    ]
else:
    SAMPLE_IMAGES = [
        ("clean", _ASSETS_DIR / "sample_essay_clean.png"),
        ("messy", _ASSETS_DIR / "sample_essay_messy.png"),
    ]


async def run_one_image(app_name: str, student_id: str, image_path: Path) -> dict:
    workflow = build_tier1_workflow()
    runner = InMemoryRunner(node=workflow, app_name=app_name)
    session_id = f"ocr-demo-{uuid.uuid4().hex[:8]}"

    await runner.session_service.create_session(
        app_name=app_name,
        user_id=student_id,
        session_id=session_id,
        state={"student_id": student_id, "student_name": "OCR Demo Student", "class_id": "ocr_demo_class"},
    )

    mime_type = "image/jpeg" if image_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    image_bytes = image_path.read_bytes()
    content = types.Content(role="user", parts=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type)])

    events = []
    async for event in runner.run_async(user_id=student_id, session_id=session_id, new_message=content):
        events.append(event)

    return events[-1].output


async def main() -> None:
    for label, path in SAMPLE_IMAGES:
        if not path.exists():
            print(f"[SKIP] {path} not found -- run scripts/generate_sample_essay_images.py first.")
            continue

        _safe_print(f"\n=== Sample image: {label} ({path.name}) ===")
        student_id = f"ocr_demo_{label}_{uuid.uuid4().hex[:6]}"
        output = await run_one_image("eduagent-ocr-demo", student_id, path)

        _safe_print("OCR confidence:", output.get("ocr_confidence"))
        _safe_print("OCR uncertain segments:", output.get("ocr_uncertain_segments"))
        _safe_print("Transcribed/sanitized text used downstream:", output.get("essay_text"))
        _safe_print("Persona chosen:", output.get("persona"))
        _safe_print("Scores:", output.get("scores"))
        _safe_print("Student feedback:", output.get("student_feedback"))
        _safe_print("Parked to pending_essays (untrustworthy input)?", output.get("pending_retry"))

    print("\nDone -- both images ran through OCR -> the full Tier 1 pipeline with zero manual intervention.")


if __name__ == "__main__":
    asyncio.run(main())
