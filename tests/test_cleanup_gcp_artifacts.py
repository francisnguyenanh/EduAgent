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


def _fake_doc(doc_id: str, data: dict) -> MagicMock:
    doc = MagicMock()
    doc.id = doc_id
    doc.to_dict.return_value = data
    doc.reference = MagicMock()
    doc.reference.id = doc_id
    doc.reference.path = f"fake/{doc_id}"
    return doc


def _fake_firestore_client(*, profiles=(), pending=(), class_docs=None, existing_event_ids=()):
    """profiles/pending: iterables of (doc_id, data) tuples.
    class_docs: {class_id: {"exists": bool, "digest_ids": [id, ...]}}."""
    class_docs = class_docs or {}
    profile_docs = [_fake_doc(doc_id, data) for doc_id, data in profiles]
    pending_docs = [_fake_doc(doc_id, data) for doc_id, data in pending]

    def class_analytics_document(class_id):
        info = class_docs.get(class_id, {"exists": False, "digest_ids": []})
        class_ref = MagicMock()
        class_ref.id = class_id
        class_ref.get.return_value = MagicMock(exists=info["exists"])
        digests_collection = MagicMock()
        digests_collection.stream.return_value = iter([_fake_doc(did, {}) for did in info["digest_ids"]])
        class_ref.collection.return_value = digests_collection
        return class_ref

    def processed_events_document(essay_id):
        ref = MagicMock()
        ref.id = essay_id
        ref.get.return_value = MagicMock(exists=essay_id in existing_event_ids)
        return ref

    def collection_side_effect(name):
        col = MagicMock()
        if name == "student_profiles":
            col.stream.return_value = iter(profile_docs)
        elif name == "pending_essays":
            col.stream.return_value = iter(pending_docs)
        elif name == "class_analytics":
            col.document.side_effect = class_analytics_document
        elif name == "processed_events":
            col.document.side_effect = processed_events_document
        return col

    client = MagicMock()
    client.collection.side_effect = collection_side_effect
    return client


def test_find_test_firestore_docs_matches_seed_student_ids():
    client = _fake_firestore_client(profiles=[("stu_stuck", {"class_id": "some_other_class", "essay_history": []})])
    with patch("google.cloud.firestore.Client", return_value=client):
        matched = cleanup.find_test_firestore_docs()
    assert [ref.id for ref in matched["student_profiles"]] == ["stu_stuck"]


def test_find_test_firestore_docs_matches_demo_prefix():
    client = _fake_firestore_client(profiles=[("demo_student_abc123", {"class_id": "some_other_class", "essay_history": []})])
    with patch("google.cloud.firestore.Client", return_value=client):
        matched = cleanup.find_test_firestore_docs()
    assert [ref.id for ref in matched["student_profiles"]] == ["demo_student_abc123"]


def test_find_test_firestore_docs_matches_by_class_id_even_with_unrelated_student_id():
    client = _fake_firestore_client(profiles=[("some_real_student", {"class_id": "c1", "essay_history": []})])
    with patch("google.cloud.firestore.Client", return_value=client):
        matched = cleanup.find_test_firestore_docs()
    assert [ref.id for ref in matched["student_profiles"]] == ["some_real_student"]


def test_find_test_firestore_docs_ignores_non_test_profile():
    client = _fake_firestore_client(profiles=[("a_real_student", {"class_id": "real_production_class", "essay_history": []})])
    with patch("google.cloud.firestore.Client", return_value=client):
        matched = cleanup.find_test_firestore_docs()
    assert matched["student_profiles"] == []


def test_find_test_firestore_docs_cross_references_processed_events_by_essay_id():
    client = _fake_firestore_client(
        profiles=[("stu_stuck", {"class_id": "c1", "essay_history": [{"essay_id": "e1"}, {"essay_id": "e2"}]})],
        existing_event_ids={"e1"},  # e2 was never actually published/claimed
    )
    with patch("google.cloud.firestore.Client", return_value=client):
        matched = cleanup.find_test_firestore_docs()
    assert [ref.id for ref in matched["processed_events"]] == ["e1"]


def test_find_test_firestore_docs_matches_pending_essays_by_class_id():
    client = _fake_firestore_client(pending=[("essay-uuid-1", {"class_id": "demo_class", "student_id": "whatever"})])
    with patch("google.cloud.firestore.Client", return_value=client):
        matched = cleanup.find_test_firestore_docs()
    assert [ref.id for ref in matched["pending_essays"]] == ["essay-uuid-1"]


def test_find_test_firestore_docs_extra_class_id_extends_matching():
    client = _fake_firestore_client(profiles=[("real_student", {"class_id": "my_custom_test_class", "essay_history": []})])
    with patch("google.cloud.firestore.Client", return_value=client):
        matched = cleanup.find_test_firestore_docs(extra_class_ids={"my_custom_test_class"})
    assert [ref.id for ref in matched["student_profiles"]] == ["real_student"]


def test_find_test_firestore_docs_includes_class_analytics_parent_and_digests():
    client = _fake_firestore_client(class_docs={"c1": {"exists": True, "digest_ids": ["e1", "e2"]}})
    with patch("google.cloud.firestore.Client", return_value=client):
        matched = cleanup.find_test_firestore_docs()
    matched_ids = {ref.id for ref in matched["class_analytics"]}
    assert matched_ids == {"c1", "e1", "e2"}


def test_delete_firestore_docs_calls_delete_on_every_ref():
    client = _fake_firestore_client(profiles=[("stu_stuck", {"class_id": "c1", "essay_history": []})])
    with patch("google.cloud.firestore.Client", return_value=client):
        matched = cleanup.find_test_firestore_docs()
    cleanup.delete_firestore_docs(matched)
    for refs in matched.values():
        for ref in refs:
            ref.delete.assert_called_once()


def test_find_test_gmail_drafts_queries_each_test_class_id():
    mock_service = MagicMock()
    mock_service.users().drafts().list().execute.return_value = {"drafts": [{"id": "d1"}]}
    with patch("eduagent.integrations.gmail_mcp._service", return_value=mock_service):
        drafts = cleanup.find_test_gmail_drafts()
    assert len(drafts) == len(cleanup.TEST_CLASS_IDS)  # one query per known test class_id, each returning d1


def test_delete_gmail_drafts_calls_delete_for_each():
    mock_service = MagicMock()
    with patch("eduagent.integrations.gmail_mcp._service", return_value=mock_service):
        cleanup.delete_gmail_drafts([{"id": "d1"}, {"id": "d2"}])
    calls = mock_service.users().drafts().delete.call_args_list
    assert {c.kwargs["id"] for c in calls} == {"d1", "d2"}
