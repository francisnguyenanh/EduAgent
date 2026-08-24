"""ĐỢT 3 GCP hygiene -- one CLI to sweep up 3 kinds of leftover cloud
resources this project can accumulate over repeated dev/demo/chaos-test
cycles:

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

SAFE BY DEFAULT: dry-run only, lists what it WOULD delete and why. Nothing
is actually deleted unless --apply is passed explicitly -- this project's own
discipline (README's "Executing actions with care") treats resource deletion
as the kind of hard-to-reverse action that needs an explicit, deliberate flag,
not a script someone runs on autopilot before a demo.

Usage:
    python scripts/cleanup_gcp_artifacts.py                # dry run (default)
    python scripts/cleanup_gcp_artifacts.py --apply         # actually delete
    python scripts/cleanup_gcp_artifacts.py --apply --keep-revisions 3 --keep-images 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

from eduagent.config import PUBSUB  # noqa: E402

CLOUD_RUN_SERVICE = "eduagent-class-aggregator"
CHAOS_TEST_SUBSCRIPTION_PREFIX = "chaos-test-"


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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ĐỢT 3 GCP hygiene sweep -- dry-run by default.")
    parser.add_argument("--apply", action="store_true", help="Actually delete what's listed (default: dry-run/list only).")
    parser.add_argument("--region", default="asia-southeast1", help="Cloud Run / Artifact Registry region (default: asia-southeast1).")
    parser.add_argument("--keep-revisions", type=int, default=5, help="Cloud Run revisions to keep per service (default: 5).")
    parser.add_argument("--keep-images", type=int, default=3, help="Untagged Artifact Registry image versions to keep per package (default: 3).")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    mode = "APPLY (deleting)" if args.apply else "DRY RUN (listing only, pass --apply to delete)"
    print(f"eduagent GCP hygiene sweep -- {mode}\n" + "=" * 60)

    print("\n[1/3] Stale chaos-test-* Pub/Sub subscriptions")
    stale_subs = find_stale_chaos_test_subscriptions()
    for s in stale_subs:
        print(f"  {'DELETE' if args.apply else 'WOULD DELETE'}: {s}")
    if not stale_subs:
        print("  none found.")
    elif args.apply:
        delete_subscriptions(stale_subs)

    print(f"\n[2/3] Cloud Run revisions of '{CLOUD_RUN_SERVICE}' beyond the {args.keep_revisions} most recent (never the serving one)")
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

    print(f"\n[3/3] Untagged Artifact Registry images beyond the {args.keep_images} most recent per package")
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

    print("\n" + "=" * 60)
    if not args.apply:
        print("Dry run complete -- re-run with --apply to actually delete the items listed above.")
    else:
        print("Cleanup applied.")


if __name__ == "__main__":
    main()
