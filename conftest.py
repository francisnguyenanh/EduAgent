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
