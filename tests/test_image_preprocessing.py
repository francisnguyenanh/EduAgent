"""Unit tests for the deterministic image prep step -- pure PIL
transforms, no network/LLM involved."""

from __future__ import annotations

import io

from PIL import Image

from eduagent.skills.image_preprocessing import MAX_DIMENSION, preprocess_image_bytes


def _make_image_bytes(*, size: tuple[int, int], fmt: str = "PNG", exif: bytes | None = None) -> bytes:
    image = Image.new("RGB", size, color=(255, 0, 0))
    buffer = io.BytesIO()
    if exif is not None:
        image.save(buffer, format=fmt, exif=exif)
    else:
        image.save(buffer, format=fmt)
    return buffer.getvalue()


def test_downscales_oversized_image():
    original = _make_image_bytes(size=(4000, 3000))
    processed_bytes, mime_type = preprocess_image_bytes(original, "image/png")
    processed = Image.open(io.BytesIO(processed_bytes))
    assert max(processed.size) <= MAX_DIMENSION
    assert mime_type == "image/jpeg"


def test_leaves_small_image_dimensions_unchanged():
    original = _make_image_bytes(size=(800, 600))
    processed_bytes, _ = preprocess_image_bytes(original, "image/png")
    processed = Image.open(io.BytesIO(processed_bytes))
    assert processed.size == (800, 600)


def test_reduces_payload_size_for_large_image():
    original = _make_image_bytes(size=(4000, 3000))
    processed_bytes, _ = preprocess_image_bytes(original, "image/png")
    assert len(processed_bytes) < len(original)


def test_applies_exif_orientation_before_reencoding():
    # Orientation tag 6 = "rotate 90 CW to display correctly": a 100x200
    # (portrait) image stored with this tag should come out landscape
    # (200x100) once exif_transpose bakes the rotation into real pixels.
    exif = Image.Exif()
    exif[0x0112] = 6
    original = _make_image_bytes(size=(100, 200), fmt="JPEG", exif=exif.tobytes())
    processed_bytes, _ = preprocess_image_bytes(original, "image/jpeg")
    processed = Image.open(io.BytesIO(processed_bytes))
    assert processed.size == (200, 100)


def test_falls_back_to_original_bytes_on_corrupt_image():
    corrupt = b"not a real image"
    processed_bytes, mime_type = preprocess_image_bytes(corrupt, "image/jpeg")
    assert processed_bytes == corrupt
    assert mime_type == "image/jpeg"
