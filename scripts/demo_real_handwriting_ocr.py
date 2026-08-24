"""PHASE 6 DoD proof with REAL handwritten photos (not synthetic placeholders).

Runs nodes/ocr.py's multimodal_ocr() (the exact production node -- including
the self-consistency cross-check) against every image in eval/test_images/
and prints transcribed_text/confidence/uncertain_segments for each. This is
the OCR step in isolation (cheap: 2 Vision calls per image) -- use
demo_ocr_run.py for a couple of these run through the FULL Tier 1 pipeline.

Usage: python scripts/demo_real_handwriting_ocr.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

from eduagent.nodes.ocr import multimodal_ocr  # noqa: E402

_TEST_IMAGES_DIR = Path(__file__).parent.parent / "eval" / "test_images"
_MIME_BY_SUFFIX = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def _safe_print(*args) -> None:
    text = " ".join(str(a) for a in args)
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


async def run_one(path: Path) -> dict:
    ctx = MagicMock()
    ctx.state = {
        "ocr_image_bytes": path.read_bytes(),
        "ocr_image_mime_type": _MIME_BY_SUFFIX.get(path.suffix.lower(), "image/jpeg"),
        "essay_id": path.stem,
    }
    return await multimodal_ocr(ctx)


async def main() -> None:
    images = sorted(_TEST_IMAGES_DIR.glob("*"))
    images = [p for p in images if p.suffix.lower() in _MIME_BY_SUFFIX]
    if not images:
        _safe_print(f"No images found in {_TEST_IMAGES_DIR}")
        return

    results = []
    for path in images:
        _safe_print(f"\n=== {path.name} ===")
        result = await run_one(path)
        results.append((path.name, result))
        _safe_print("confidence:", result["confidence"])
        _safe_print("uncertain_segments:", result["uncertain_segments"])
        _safe_print("transcribed_text:")
        _safe_print(result["transcribed_text"])

    _safe_print("\n=== Summary ===")
    for name, result in results:
        _safe_print(f"{name}: confidence={result['confidence']}, chars={len(result['transcribed_text'])}")


if __name__ == "__main__":
    asyncio.run(main())
