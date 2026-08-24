"""Unit tests for scripts/cleanup_gcp_artifacts.py's selection logic (which
revisions/images/subscriptions to flag). Mocks the GCP clients -- must never
touch real Cloud Run/Artifact Registry/Pub/Sub."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import cleanup_gcp_artifacts as cleanup  # noqa: E402


def _revision(name: str, create_time: int, *, serving: bool = False) -> SimpleNamespace:
    return SimpleNamespace(name=name, create_time=create_time, percent_traffic=100 if serving else 0, in_progress_percent_traffic=0)


def test_find_old_cloud_run_revisions_keeps_n_most_recent():
    revisions = [_revision(f"rev-{i}", create_time=i) for i in range(7)]  # rev-6 is newest (create_time=6)
    mock_client = MagicMock()
    mock_client.list_revisions.return_value = revisions

    with patch("google.cloud.run_v2.RevisionsClient", return_value=mock_client):
        to_delete = cleanup.find_old_cloud_run_revisions(region="asia-southeast1", keep=5)

    # 7 revisions, keep 5 most recent (create_time 2..6) -> delete create_time 0,1
    assert set(to_delete) == {"rev-0", "rev-1"}


def test_find_old_cloud_run_revisions_never_deletes_the_serving_one_even_if_old():
    revisions = [_revision(f"rev-{i}", create_time=i, serving=(i == 0)) for i in range(7)]
    mock_client = MagicMock()
    mock_client.list_revisions.return_value = revisions

    with patch("google.cloud.run_v2.RevisionsClient", return_value=mock_client):
        to_delete = cleanup.find_old_cloud_run_revisions(region="asia-southeast1", keep=5)

    assert "rev-0" not in to_delete  # rev-0 is oldest AND serving -- must survive


def _version(name: str, create_time: int, *, tags: list | None = None) -> SimpleNamespace:
    return SimpleNamespace(name=name, create_time=create_time, related_tags=tags or [])


def test_find_untagged_old_images_keeps_recent_and_tagged():
    package = SimpleNamespace(name="pkg-1")
    versions = [_version(f"v{i}", create_time=i) for i in range(5)]  # v0..v4, v4 newest
    versions[0] = _version("v0", create_time=0, tags=["latest"])  # oldest but tagged -- must survive

    mock_client = MagicMock()
    mock_client.list_packages.return_value = [package]
    mock_client.list_versions.return_value = versions

    with patch("google.cloud.artifactregistry_v1.ArtifactRegistryClient", return_value=mock_client):
        to_delete = cleanup.find_untagged_old_images(region="asia-southeast1", keep=3)

    # keep=3 most recent (v2,v3,v4) survive by recency; v0 survives because tagged;
    # only v1 (old AND untagged) should be flagged.
    assert to_delete == ["v1"]


def test_find_stale_chaos_test_subscriptions_filters_by_prefix():
    subs = [
        SimpleNamespace(name="projects/p/subscriptions/class-aggregator-sub"),
        SimpleNamespace(name="projects/p/subscriptions/chaos-test-dlq-inspector"),
    ]
    mock_client = MagicMock()
    mock_client.list_subscriptions.return_value = subs

    with patch("google.cloud.pubsub_v1.SubscriberClient", return_value=mock_client):
        stale = cleanup.find_stale_chaos_test_subscriptions()

    assert stale == ["projects/p/subscriptions/chaos-test-dlq-inspector"]
