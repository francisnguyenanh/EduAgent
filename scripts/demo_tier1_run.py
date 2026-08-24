"""Manual demo run of the Tier 1 pipeline with a real (mock) essay, printing
the full final state -- useful for eyeballing LLM output quality, not a test."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

from google.adk.runners import InMemoryRunner  # noqa: E402

from eduagent.graph.tier1_pipeline import build_tier1_workflow  # noqa: E402

MOCK_ESSAY = (
    "Homework should be banned in all schools. Everyone knows kids need free time "
    "to be happy, and my cousin never does homework and he is doing great in life. "
    "So clearly homework does not actually help anyone learn anything."
)


async def main() -> None:
    workflow = build_tier1_workflow()
    runner = InMemoryRunner(node=workflow, app_name="eduagent-tier1-demo")
    events = await runner.run_debug(MOCK_ESSAY, quiet=True)
    print(json.dumps(events[-1].output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
