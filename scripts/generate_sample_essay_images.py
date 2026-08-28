"""PHASE 6: generates the 2 placeholder sample images referenced in
Phase 6's DoD ("chuan bi san 2 anh mau cho video: 1 anh 'dep vua
phai' + 1 anh that su lon xon").

IMPORTANT: these are SYNTHETIC placeholders (rendered typed text, not real
handwriting) -- good enough to exercise and demo the OCR node's code path
(routing, verbatim transcription incl. typos, confidence flagging) before a
real handwritten photo is available. Before recording the actual demo video,
replace assets/sample_essays/*.png with real photos of real handwritten
student essays, per the DoD's own requirement ("upload anh viet tay that").

Usage: python scripts/generate_sample_essay_images.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

_ASSETS_DIR = Path(__file__).parent.parent / "assets" / "sample_essays"

# Deliberately includes the student's own spelling/grammar mistakes -- this
# is what nodes/ocr.py's system_instruction is told to preserve VERBATIM,
# not clean up.
_CLEAN_ESSAY_TEXT = (
    "Homework shud be baned for all studnts because it takes\n"
    "away are free time. Every1 I no who does alot of homework\n"
    "is stressed all the time, so homework clearly causes stress\n"
    "for everyone. My freind stoped doing homework and now\n"
    "she is alot happyer."
)

_MESSY_ESSAY_TEXT = (
    "Scool uniforms shud be manditory in evry scool becuz they\n"
    "make studnts look profesional and stop bulling about close."
)


def _render(text: str, *, blur_radius: float = 0.0) -> Image.Image:
    img = Image.new("RGB", (900, 500), color="white")
    draw = ImageDraw.Draw(img)
    draw.multiline_text((30, 30), text, fill="black", spacing=14)
    if blur_radius:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    return img


def main() -> None:
    _ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    clean_path = _ASSETS_DIR / "sample_essay_clean.png"
    _render(_CLEAN_ESSAY_TEXT, blur_radius=0.0).save(clean_path)
    print(f"[OK] wrote {clean_path} ('reasonably clean' sample -- should OCR at confidence=high)")

    # A heavy blur simulates real messy-photo conditions (poor lighting,
    # camera shake, low resolution) well enough to exercise the
    # low-confidence / '[[unclear]]' path -- verified for real against
    # Vertex AI during development (see the ADR-007 / ADR-008 entries in README.md for the finding
    # that led to the anti-hallucination rule in nodes/ocr.py's prompt).
    messy_path = _ASSETS_DIR / "sample_essay_messy.png"
    _render(_MESSY_ESSAY_TEXT, blur_radius=6.0).save(messy_path)
    print(f"[OK] wrote {messy_path} ('truly messy' sample -- should OCR at confidence=low, transcribed_text='[[unclear]]')")

    print("\nReminder: replace these with real handwritten-essay photos before recording the actual demo video.")


if __name__ == "__main__":
    main()
