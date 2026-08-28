"""Wave 3 GCP hygiene -- one CLI to sweep up leftover cloud resources this
project accumulates over repeated dev/demo/chaos-test cycles:

  1. Stale Pub/Sub subscriptions matching `chaos-test-*` -- scripts/
     chaos_test_pubsub.py creates one temporarily and deletes it in a
     `finally` block, but a hard crash/Ctrl-C mid-run can still leave one
     behind (real risk: it silently keeps pulling from the DLQ topic,
     which is otherwise meant to sit untouched for teacher/judge review).
  2. Cloud Run revisions of eduagent-class-aggregator older than the N most
     recent -- Cloud Run keeps every revision by default; NEVER deletes the
     revision currently serving traffic.
  3. Untagged Artifact Registry images in the Cloud Run source-deploy
     repository, keeping only the K most recent per package.
  4. Firestore documents left behind by demo/test scripts -- matched ONLY
     against known test/demo identifiers (see TEST_* constants below), never
     a blind "everything in this collection" wipe:
       - student_profiles: seed script's fixed ids (stu_improving, stu_stuck,
         ...) or a demo script's `demo_student_*`/`ocr_demo_*` prefix, or
         `class_id` in a known test class.
       - pending_essays: same student_id/class_id matching.
       - class_analytics/{class_id} (+ its digests subcollection): known
         test class_ids only.
       - processed_events: ONLY the specific essay_ids collected while
         matching the categories above (never a scan of the whole
         collection -- there's no class_id/student_id on these docs to
         match against safely).
  5. Gmail drafts whose subject matches "Class digest for {test class_id}:"
     -- reuses gmail_mcp.py's own credential loading, same discipline as
     scripts/cleanup_gmail_test_artifacts.py (Phase 0).

DELIBERATELY NOT HANDLED: Sheets audit rows. sheets_mcp.py's own docstring
states the design principle directly -- "append-only by convention... an
audit trail you can edit isn't an audit trail." Adding row deletion here
would contradict that. If test runs pollute your production audit sheet,
either point EDUAGENT_AUDIT_SPREADSHEET_ID at a separate throwaway
spreadsheet while testing, or clear test rows by hand in Sheets UI.

SAFE BY DEFAULT: dry-run only, lists what it WOULD delete and why. Nothing
is actually deleted unless --apply is passed explicitly -- this project's own
discipline (README's "Executing actions with care") treats resource deletion
as the kind of hard-to-reverse action that needs an explicit, deliberate flag,
not a script someone runs on autopilot before a demo.

Usage:
    python scripts/cleanup_gcp_artifacts.py                # dry run (default)
    python scripts/cleanup_gcp_artifacts.py --apply         # actually delete
    python scripts/cleanup_gcp_artifacts.py --apply --keep-revisions 3 --keep-images 3
    python scripts/cleanup_gcp_artifacts.py --apply --extra-class-id my_test_class
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

from eduagent.config import FIRESTORE, PUBSUB  # noqa: E402

CLOUD_RUN_SERVICE = "eduagent-class-aggregator"
CHAOS_TEST_SUBSCRIPTION_PREFIX = "chaos-test-"

# Known test/demo identifiers -- see scripts/seed_student_profiles.py and
# scripts/demo_tier1_run.py / demo_ocr_run.py for where each of these comes
# from. Extend via --extra-class-id/--extra-student-id rather than editing
# these if you use different identifiers in your own test runs.
TEST_STUDENT_IDS = {"stu_improving", "stu_stuck", "stu_declining", "stu_inactive", "stu_common_fallacy"}
TEST_STUDENT_ID_PREFIXES = ("demo_student_", "ocr_demo_")
TEST_CLASS_IDS = {"c1", "demo_class", "ocr_demo_class"}


def _is_test_student_id(student_id: str, extra_student_ids: set[str]) -> bool:
    if not student_id:
        return False
    if student_id in TEST_STUDENT_IDS or student_id in extra_student_ids:
        return True
    return any(student_id.startswith(prefix) for prefix in TEST_STUDENT_ID_PREFIXES)


def find_stale_chaos_test_subscriptions() -> list[str]:
    from google.cloud import pubsub_v1

    subscriber = pubsub_v1.SubscriberClient()
    project_path = f"projects/{PUBSUB.project_id}"
    return [
        sub.name
        for sub in subscriber.list_subscriptions(request={"project": project_path})
        if sub.name.rsplit("/", 1)[-1].startswith(CHAOS_TEST_SUBSCRIPTION_PREFIX)
    ]


def delete_subscriptions(subscription_paths: list[str]) -> None:
    from google.cloud import pubsub_v1

    subscriber = pubsub_v1.SubscriberClient()
    for path in subscription_paths:
        subscriber.delete_subscription(request={"subscription": path})


def find_old_cloud_run_revisions(*, region: str, keep: int) -> list[str]:
    """Returns revision names to delete: every revision NOT in the `keep`
    most-recently-created, and never one currently receiving traffic."""
    from google.cloud import run_v2

    client = run_v2.RevisionsClient()
    parent = f"projects/{PUBSUB.project_id}/locations/{region}/services/{CLOUD_RUN_SERVICE}"
    revisions = list(client.list_revisions(request={"parent": parent}))
    revisions.sort(key=lambda r: r.create_time, reverse=True)

    serving = {r.name for r in revisions if getattr(r, "percent_traffic", 0) or getattr(r, "in_progress_percent_traffic", 0)}
    return [r.name for r in revisions[keep:] if r.name not in serving]


def delete_cloud_run_revisions(revision_names: list[str]) -> None:
    from google.cloud import run_v2

    client = run_v2.RevisionsClient()
    for name in revision_names:
        client.delete_revision(request={"name": name})


def find_untagged_old_images(*, region: str, keep: int) -> list[str]:
    """Cloud Run's `--source .` deploy writes to a default 'cloud-run-source-deploy'
    Artifact Registry repo. Returns package version names beyond the `keep`
    most recent, per package, that carry no tag (a tagged image is assumed
    deliberately kept, e.g. `:latest`)."""
    from google.cloud import artifactregistry_v1

    client = artifactregistry_v1.ArtifactRegistryClient()
    parent = f"projects/{PUBSUB.project_id}/locations/{region}/repositories/cloud-run-source-deploy"

    to_delete: list[str] = []
    packages = client.list_packages(request={"parent": parent})
    for package in packages:
        versions = list(client.list_versions(request={"parent": package.name}))
        versions.sort(key=lambda v: v.create_time, reverse=True)
        for version in versions[keep:]:
            if not version.related_tags:
                to_delete.append(version.name)
    return to_delete


def delete_image_versions(version_names: list[str]) -> None:
    from google.cloud import artifactregistry_v1

    client = artifactregistry_v1.ArtifactRegistryClient()
    for name in version_names:
        client.delete_version(request={"name": name})


def find_test_firestore_docs(*, extra_class_ids: set[str] | None = None, extra_student_ids: set[str] | None = None) -> dict[str, list]:
    """Returns {category: [DocumentReference, ...]} for every Firestore doc
    matched against the known test identifiers -- see module docstring for
    exactly which fields are matched per collection. Never touches a doc
    that doesn't match one of these identifiers."""
    from google.cloud import firestore

    class_ids = TEST_CLASS_IDS | (extra_class_ids or set())
    extra_student_ids = extra_student_ids or set()

    db = firestore.Client()
    matched: dict[str, list] = {"student_profiles": [], "pending_essays": [], "class_analytics": [], "processed_events": []}
    essay_ids: set[str] = set()

    for doc in db.collection(FIRESTORE.student_profiles_collection).stream():
        data = doc.to_dict() or {}
        if _is_test_student_id(doc.id, extra_student_ids) or data.get("class_id") in class_ids:
            matched["student_profiles"].append(doc.reference)
            for essay in data.get("essay_history", []):
                if essay.get("essay_id"):
                    essay_ids.add(essay["essay_id"])

    for doc in db.collection(FIRESTORE.pending_essays_collection).stream():
        data = doc.to_dict() or {}
        if data.get("class_id") in class_ids or _is_test_student_id(data.get("student_id", ""), extra_student_ids):
            matched["pending_essays"].append(doc.reference)
            essay_ids.add(doc.id)  # pending_essays doc id IS the essay_id (nodes/mutator.py::_park_pending_essay)

    for class_id in class_ids:
        class_ref = db.collection(FIRESTORE.class_analytics_collection).document(class_id)
        digest_docs = list(class_ref.collection("digests").stream())
        matched["class_analytics"].extend(d.reference for d in digest_docs)
        if class_ref.get().exists:
            matched["class_analytics"].append(class_ref)

    for essay_id in essay_ids:
        ref = db.collection(FIRESTORE.processed_events_collection).document(essay_id)
        if ref.get().exists:
            matched["processed_events"].append(ref)

    return matched


def delete_firestore_docs(matched: dict[str, list]) -> None:
    for refs in matched.values():
        for ref in refs:
            ref.delete()


def find_test_gmail_drafts(*, extra_class_ids: set[str] | None = None) -> list[dict]:
    """Reuses gmail_mcp.py's own credential loading (same OAuth token this
    project already manages) -- searches by the exact subject prefix
    class_aggregator.py's create_digest_draft() call always uses:
    '[eduagent] Class digest for {class_id}: ...'."""
    from eduagent.integrations.gmail_mcp import _service

    class_ids = TEST_CLASS_IDS | (extra_class_ids or set())
    service = _service()
    drafts: list[dict] = []
    for class_id in class_ids:
        response = service.users().drafts().list(userId="me", q=f'subject:"Class digest for {class_id}:"').execute()
        drafts.extend(response.get("drafts", []))
    return drafts


def delete_gmail_drafts(drafts: list[dict]) -> None:
    from eduagent.integrations.gmail_mcp import _service

    service = _service()
    for draft in drafts:
        service.users().drafts().delete(userId="me", id=draft["id"]).execute()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wave 3 GCP hygiene sweep -- dry-run by default.")
    parser.add_argument("--apply", action="store_true", help="Actually delete what's listed (default: dry-run/list only).")
    parser.add_argument("--region", default="asia-southeast1", help="Cloud Run / Artifact Registry region (default: asia-southeast1).")
    parser.add_argument("--keep-revisions", type=int, default=5, help="Cloud Run revisions to keep per service (default: 5).")
    parser.add_argument("--keep-images", type=int, default=3, help="Untagged Artifact Registry image versions to keep per package (default: 3).")
    parser.add_argument(
        "--extra-class-id", action="append", default=[], dest="extra_class_ids",
        help="Additional class_id to treat as test data (repeatable). Extends TEST_CLASS_IDS for this run only.",
    )
    parser.add_argument(
        "--extra-student-id", action="append", default=[], dest="extra_student_ids",
        help="Additional exact student_id to treat as test data (repeatable). Extends TEST_STUDENT_IDS for this run only.",
    )
    parser.add_argument("--skip-firestore", action="store_true", help="Skip the Firestore test-data sweep (e.g. no ADC configured).")
    parser.add_argument("--skip-gmail", action="store_true", help="Skip the Gmail test-draft sweep (e.g. no OAuth token yet).")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    mode = "APPLY (deleting)" if args.apply else "DRY RUN (listing only, pass --apply to delete)"
    print(f"eduagent GCP hygiene sweep -- {mode}\n" + "=" * 60)

    print("\n[1/5] Stale chaos-test-* Pub/Sub subscriptions")
    stale_subs = find_stale_chaos_test_subscriptions()
    for s in stale_subs:
        print(f"  {'DELETE' if args.apply else 'WOULD DELETE'}: {s}")
    if not stale_subs:
        print("  none found.")
    elif args.apply:
        delete_subscriptions(stale_subs)

    print(f"\n[2/5] Cloud Run revisions of '{CLOUD_RUN_SERVICE}' beyond the {args.keep_revisions} most recent (never the serving one)")
    try:
        old_revisions = find_old_cloud_run_revisions(region=args.region, keep=args.keep_revisions)
    except Exception as exc:  # noqa: BLE001 -- one section's failure must not block the others
        print(f"  SKIPPED: {type(exc).__name__}: {exc}")
        old_revisions = []
    for r in old_revisions:
        print(f"  {'DELETE' if args.apply else 'WOULD DELETE'}: {r}")
    if not old_revisions:
        print("  none found (or service/region not reachable).")
    elif args.apply:
        delete_cloud_run_revisions(old_revisions)

    print(f"\n[3/5] Untagged Artifact Registry images beyond the {args.keep_images} most recent per package")
    try:
        old_images = find_untagged_old_images(region=args.region, keep=args.keep_images)
    except Exception as exc:  # noqa: BLE001
        print(f"  SKIPPED: {type(exc).__name__}: {exc}")
        old_images = []
    for v in old_images:
        print(f"  {'DELETE' if args.apply else 'WOULD DELETE'}: {v}")
    if not old_images:
        print("  none found (or repository not reachable).")
    elif args.apply:
        delete_image_versions(old_images)

    extra_class_ids = set(args.extra_class_ids)
    extra_student_ids = set(args.extra_student_ids)

    if args.skip_firestore:
        print("\n[4/5] Firestore test data -- SKIPPED (--skip-firestore)")
    else:
        print("\n[4/5] Firestore test data (student_profiles/pending_essays/class_analytics/processed_events)")
        try:
            matched = find_test_firestore_docs(extra_class_ids=extra_class_ids, extra_student_ids=extra_student_ids)
        except Exception as exc:  # noqa: BLE001
            print(f"  SKIPPED: {type(exc).__name__}: {exc}")
            matched = {}
        total = sum(len(refs) for refs in matched.values())
        for category, refs in matched.items():
            for ref in refs:
                print(f"  {'DELETE' if args.apply else 'WOULD DELETE'}: [{category}] {ref.path}")
        if not total:
            print("  none found (or Firestore not reachable).")
        elif args.apply:
            delete_firestore_docs(matched)

    if args.skip_gmail:
        print("\n[5/5] Gmail test drafts -- SKIPPED (--skip-gmail)")
    else:
        print("\n[5/5] Gmail drafts matching a known test class_id's digest subject")
        try:
            test_drafts = find_test_gmail_drafts(extra_class_ids=extra_class_ids)
        except Exception as exc:  # noqa: BLE001
            print(f"  SKIPPED: {type(exc).__name__}: {exc}")
            test_drafts = []
        for d in test_drafts:
            print(f"  {'DELETE' if args.apply else 'WOULD DELETE'}: draft {d['id']}")
        if not test_drafts:
            print("  none found (or Gmail token not configured).")
        elif args.apply:
            delete_gmail_drafts(test_drafts)

    print("\nNOTE: Sheets audit rows are deliberately NOT covered -- sheets_mcp.py's own")
    print("design principle is append-only ('an audit trail you can edit isn't an audit")
    print("trail'). Use a separate test spreadsheet, or clear test rows by hand.")

    print("\n" + "=" * 60)
    if not args.apply:
        print("Dry run complete -- re-run with --apply to actually delete the items listed above.")
    else:
        print("Cleanup applied.")


if __name__ == "__main__":
    main()
