"""Phase 3 dev-mode Class Aggregator subscriber.

Synchronous pull loop against class-aggregator-sub -- good enough for local
testing and the demo video. Phase 7 replaces this with a Cloud Run push
subscriber (same process_event() call, different transport), so nothing in
aggregator/class_aggregator.py needs to change.

Usage: python scripts/run_class_aggregator_subscriber.py [--once]
  --once: process whatever's currently queued, then exit (used by the demo
          script and CI-style verification runs instead of running forever).
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

from google.cloud import pubsub_v1  # noqa: E402

from eduagent.aggregator.class_aggregator import process_event  # noqa: E402
from eduagent.config import PUBSUB  # noqa: E402


def _pull_and_process(subscriber: pubsub_v1.SubscriberClient, subscription_path: str, max_messages: int = 10) -> int:
    response = subscriber.pull(request={"subscription": subscription_path, "max_messages": max_messages})
    if not response.received_messages:
        return 0

    ack_ids = []
    for received in response.received_messages:
        event = json.loads(received.message.data.decode("utf-8"))
        print(f"Processing event: {event}")
        result = asyncio.run(process_event(event))
        print(f"  -> {result['status']}" + (f" (draft={result.get('gmail_draft_id')})" if result["status"] == "processed" else ""))
        ack_ids.append(received.ack_id)

    subscriber.acknowledge(request={"subscription": subscription_path, "ack_ids": ack_ids})
    return len(ack_ids)


def main() -> None:
    once = "--once" in sys.argv
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PUBSUB.project_id, PUBSUB.class_aggregator_subscription)

    total = 0
    while True:
        n = _pull_and_process(subscriber, subscription_path)
        total += n
        if once:
            print(f"\n--once: processed {total} message(s), exiting.")
            return
        if n == 0:
            import time

            time.sleep(2)


if __name__ == "__main__":
    main()
