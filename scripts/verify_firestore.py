"""One-off verification: write + read a real document in each Firestore
collection declared in eduagent.config.FirestoreConfig, then clean up.

Not part of the app — just proof the GCP project/credentials/collections work
end-to-end before building real logic on top.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

from google.cloud import firestore  # noqa: E402

from eduagent.config import FIRESTORE  # noqa: E402


def main() -> None:
    project_id = os.environ["GCP_PROJECT_ID"]
    db = firestore.Client(project=project_id)

    collections = [
        FIRESTORE.student_profiles_collection,
        FIRESTORE.class_analytics_collection,
        FIRESTORE.audit_log_collection,
        FIRESTORE.processed_events_collection,
    ]

    doc_id = "phase0_verify"
    for coll in collections:
        ref = db.collection(coll).document(doc_id)
        ref.set({"phase": "0", "note": "skeleton verification, safe to delete"})
        snapshot = ref.get()
        assert snapshot.exists, f"write/read failed for {coll}"
        print(f"[OK] {coll}/{doc_id} -> {snapshot.to_dict()}")
        ref.delete()
        print(f"[OK] {coll}/{doc_id} cleaned up")

    print("\nFirestore verification PASSED for project:", project_id)


if __name__ == "__main__":
    main()
