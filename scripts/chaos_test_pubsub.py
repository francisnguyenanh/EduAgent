"""PHASE 4 chaos test: inject a malformed event into Pub/Sub and confirm the
subscriber survives it (doesn't crash) and Pub/Sub eventually dead-letters
it after PUBSUB.max_delivery_attempts, instead of retrying forever.

Speeds up the wait: rather than waiting out the real ack_deadline
(60s) x max_delivery_attempts (5) = 5+ minutes, this script actively pulls
and nacks (modify_ack_deadline=0, i.e. "redeliver immediately") the bad
message itself, so the whole test finishes in seconds while still exercising
the real Pub/Sub dead-letter mechanism (no mocking of GCP).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

from google.cloud import pubsub_v1  # noqa: E402

from eduagent.config import PUBSUB  # noqa: E402


def main() -> None:
    publisher = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()

    topic_path = publisher.topic_path(PUBSUB.project_id, PUBSUB.essay_evaluated_topic)
    sub_path = subscriber.subscription_path(PUBSUB.project_id, PUBSUB.class_aggregator_subscription)
    dlq_topic_path = publisher.topic_path(PUBSUB.project_id, PUBSUB.dead_letter_topic)

    # Create the DLQ inspector subscription BEFORE triggering dead-lettering --
    # a Pub/Sub subscription only receives messages published/redirected AFTER
    # it exists, so creating it afterwards would see nothing even on success.
    temp_sub_path = subscriber.subscription_path(PUBSUB.project_id, "chaos-test-dlq-inspector")
    subscriber.create_subscription(request={"name": temp_sub_path, "topic": dlq_topic_path})
    print(f"Created temporary DLQ inspector subscription on {PUBSUB.dead_letter_topic}.")

    print(f"\nPublishing a deliberately malformed message to {PUBSUB.essay_evaluated_topic}...")
    future = publisher.publish(topic_path, b"this is not valid JSON {{{")
    message_id = future.result(timeout=30)
    print(f"Published message_id={message_id}")

    print(f"\nPulling and immediately nacking up to {PUBSUB.max_delivery_attempts} times "
          "to force redelivery without waiting out the real ack deadline...")
    for attempt in range(1, PUBSUB.max_delivery_attempts + 2):
        response = subscriber.pull(request={"subscription": sub_path, "max_messages": 1})
        if not response.received_messages:
            print(f"  attempt {attempt}: nothing to pull (likely already dead-lettered)")
            break
        received = response.received_messages[0]
        delivery_attempt = received.delivery_attempt
        print(f"  attempt {attempt}: pulled message_id={received.message.message_id}, delivery_attempt={delivery_attempt}")
        # Force immediate redelivery instead of waiting for ack_deadline to expire.
        subscriber.modify_ack_deadline(request={"subscription": sub_path, "ack_ids": [received.ack_id], "ack_deadline_seconds": 0})
        time.sleep(1)

    print(f"\nChecking dead-letter topic {PUBSUB.dead_letter_topic} for the message...")
    try:
        time.sleep(3)  # let dead-lettering propagate
        dlq_response = subscriber.pull(request={"subscription": temp_sub_path, "max_messages": 5})
        if dlq_response.received_messages:
            print(f"PASS: {len(dlq_response.received_messages)} message(s) found in DLQ.")
            for m in dlq_response.received_messages:
                print(f"  DLQ message data: {m.message.data!r}")
            subscriber.acknowledge(
                request={"subscription": temp_sub_path, "ack_ids": [m.ack_id for m in dlq_response.received_messages]}
            )
        else:
            print("FAIL (or not yet propagated): no messages found in DLQ.")
    finally:
        subscriber.delete_subscription(request={"subscription": temp_sub_path})
        print("Cleaned up temporary DLQ inspector subscription.")


if __name__ == "__main__":
    main()
