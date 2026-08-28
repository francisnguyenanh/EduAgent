"""Deterministic image prep before a photo ever reaches Gemini Vision.

Wave 3 #1: a phone-camera photo of a handwritten essay can weigh 5-15MB and
carry an EXIF rotation flag that most viewers auto-apply but the raw bytes
never do -- sent as-is, that risks a sideways transcription and adds network
latency/timeout risk (PHASE 6 real finding: a 2.6MB test photo, `stu_stuck_
messy.png`, hit a 504 DEADLINE_EXCEEDED at the multimodal call's 60s budget).

Pure, zero-LLM, Function Node-style transformation (ADK2 deterministic-first
principle) -- only touches pixels, never the transcription content that gets
judged/scored downstream.
"""

from __future__ import annotations

import io
import logging

from PIL import Image, ImageOps

_logger = logging.getLogger(__name__)

MAX_DIMENSION = 2048  # long edge, px -- ample for legible handwriting OCR, well under typical phone-camera resolution
JPEG_QUALITY = 85


def preprocess_image_bytes(image_bytes: bytes, mime_type: str) -> tuple[bytes, str]:
    """Normalize orientation and downscale/re-encode a photo before OCR.

    Returns (possibly re-encoded) bytes and the (possibly changed) mime type.
    On any decode failure (corrupt bytes, unsupported format), falls back to
    the original bytes/mime type unchanged -- preprocessing must never be why
    a legible photo fails to reach Vision at all.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        # Bakes the EXIF orientation tag into actual pixel data (a raw byte
        # stream has no "this is rotated 90deg" concept otherwise), then the
        # re-encode below drops the tag entirely -- no downstream consumer
        # needs to re-apply it.
        image = ImageOps.exif_transpose(image)

        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        if max(image.size) > MAX_DIMENSION:
            image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return buffer.getvalue(), "image/jpeg"
    except Exception:
        _logger.exception("Image preprocessing failed -- falling back to original bytes/mime_type unchanged")
        return image_bytes, mime_type
