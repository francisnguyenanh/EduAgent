"""Dev-mode Class Aggregator subscriber.

Synchronous pull loop against class-aggregator-sub -- good enough for local
testing and demos. server.py replaces this with a Cloud Run push
subscriber (same process_event() call, different transport), so nothing in
aggregator/class_aggregator.py needs to change.

Usage: python scripts/run_class_aggregator_subscriber.py [--once]
  --once: process whatever's currently queued, then exit (used by the demo
          script and CI-style verification runs instead of running forever).
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

from google.cloud import pubsub_v1  # noqa: E402

from eduagent.aggregator.class_aggregator import process_event  # noqa: E402
from eduagent.config import PUBSUB  # noqa: E402
from eduagent.logging_config import configure_json_logging  # noqa: E402

_logger = logging.getLogger(__name__)


def _pull_and_process(subscriber: pubsub_v1.SubscriberClient, subscription_path: str, max_messages: int = 10) -> int:
    """Chaos-test fix: each message is handled independently -- a
    malformed payload or a process_event() exception for ONE message must
    never prevent acking the OTHER messages in the same batch, and must
    never crash the subscriber process itself. A failed message is simply
    left un-acked; Pub/Sub redelivers it (and eventually dead-letters it
    after PUBSUB.max_delivery_attempts) without any special-casing here.
    """
    response = subscriber.pull(request={"subscription": subscription_path, "max_messages": max_messages})
    if not response.received_messages:
        return 0

    ack_ids = []
    for received in response.received_messages:
        try:
            event = json.loads(received.message.data.decode("utf-8"))
            print(f"Processing event: {event}")
            result = asyncio.run(process_event(event))
            print(f"  -> {result['status']}" + (f" (draft={result.get('gmail_draft_id')})" if result["status"] == "processed" else ""))
            ack_ids.append(received.ack_id)
        except Exception:
            _logger.exception(
                "Failed to process a message -- leaving it un-acked for redelivery/DLQ",
                extra={"message_id": received.message.message_id, "raw_data": received.message.data[:500]},
            )
            print(f"  -> FAILED (message_id={received.message.message_id}), leaving un-acked for redelivery")

    if ack_ids:
        subscriber.acknowledge(request={"subscription": subscription_path, "ack_ids": ack_ids})
    return len(ack_ids)


def main() -> None:
    configure_json_logging()
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
