"""Phase 0 DoD check: Tier 1 skeleton graph runs end-to-end with mock data.

Not a unit test of real logic (there is none yet, by design) — this only
proves the ADK2 Graph Workflow wiring (edges, FunctionNode stubs, Context
state threading) actually executes without error.
"""

from __future__ import annotations

import asyncio

from google.adk.runners import InMemoryRunner

from eduagent.graph.tier1_pipeline import build_tier1_workflow

MOCK_ESSAY = (
    "Students should not have homework because it takes away free time "
    "and everyone knows free time is important for kids."
)


async def _run() -> dict:
    workflow = build_tier1_workflow()
    runner = InMemoryRunner(node=workflow, app_name="eduagent-tier1-skeleton")
    events = await runner.run_debug(MOCK_ESSAY, quiet=True)
    assert events, "workflow produced no events"
    final_output = events[-1].output
    assert final_output is not None, "final node returned no output"
    assert final_output.get("stage") == "profile_mutator"
    return final_output


def test_tier1_skeleton_end_to_end() -> None:
    result = asyncio.run(_run())
    print("Tier 1 skeleton final state:", result)


if __name__ == "__main__":
    test_tier1_skeleton_end_to_end()
