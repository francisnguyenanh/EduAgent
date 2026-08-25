"""Allows `pytest` to find the src/ layout without an editable install, and
loads .env so tests that call Vertex AI have credentials/project configured."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

import pytest


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """ĐỢT 12 NHÓM 2: the token-bucket limiters (rate_limit.py) are module-level
    singletons, so without this the buckets drain across the whole test session
    and later tests fail with 429 for reasons that have nothing to do with what
    they assert. Resetting per test keeps the limiter itself exercised (the
    routes really do call it) while making each test independent."""
    from eduagent.rate_limit import debate_limiter, login_limiter

    debate_limiter.reset()
    login_limiter.reset()
    yield


@pytest.fixture
def student_token():
    """Bearer token for the default demo student, for the debate endpoints that
    became authenticated in ĐỢT 12 NHÓM 2."""
    from eduagent.auth import create_access_token

    def _make(student_id="c1_stu01", role="student", class_id=None):
        return create_access_token(
            user_id=student_id,
            role=role,
            class_id=class_id or student_id.split("_", 1)[0],
        )

    return _make


@pytest.fixture
def student_headers(student_token):
    """`headers=` value carrying a valid student Bearer token."""

    def _make(student_id="c1_stu01", role="student", class_id=None):
        return {"Authorization": f"Bearer {student_token(student_id, role, class_id)}"}

    return _make
