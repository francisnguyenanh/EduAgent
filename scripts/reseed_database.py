#!/usr/bin/env python3
import os
import sys
from google.cloud import firestore

# Ensure we import config correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from eduagent.config import FIRESTORE
from eduagent.memory.student_profile import empty_profile

def reseed():
    project_id = FIRESTORE.project_id or "project-4fc36103-f4ca-49f6-883"
    db = firestore.Client(project=project_id)
    print(f"Reseeding database for project: {project_id}")


    # 1. Clear student_profiles
    profiles_col = db.collection(FIRESTORE.student_profiles_collection)
    docs = profiles_col.stream()
    count = 0
    for doc in docs:
        print(f"Deleting profile: {doc.id}")
        doc.reference.delete()
        count += 1
    print(f"Deleted {count} student profiles.")

    # 2. Clear class_analytics digests
    analytics_col = db.collection(FIRESTORE.class_analytics_collection)
    # Since class_analytics is a collection of classes, which contain subcollections "digests",
    # let's delete subcollections or the documents
    classes = analytics_col.stream()
    digest_count = 0
    class_count = 0
    for cls in classes:
        digests = cls.reference.collection("digests").stream()
        for d in digests:
            print(f"Deleting digest: {d.id} for class {cls.id}")
            d.reference.delete()
            digest_count += 1
        cls.reference.delete()
        class_count += 1
    print(f"Deleted {digest_count} digests and {class_count} class documents.")

    # 3. Clear processed_events
    events_col = db.collection(FIRESTORE.processed_events_collection)
    docs = events_col.stream()
    event_count = 0
    for doc in docs:
        doc.reference.delete()
        event_count += 1
    print(f"Deleted {event_count} processed events.")

    # 4. Clear pending_essays
    pending_col = db.collection(FIRESTORE.pending_essays_collection)
    docs = pending_col.stream()
    pending_count = 0
    for doc in docs:
        doc.reference.delete()
        pending_count += 1
    print(f"Deleted {pending_count} pending essays.")

    # 5. Insert 2 fresh student profiles for class "c1"
    students = [
        {"id": "c1_stu01", "name": "Alice"},
        {"id": "c1_stu02", "name": "Bob"}
    ]
    for s in students:
        p = empty_profile(name=s["name"], class_id="c1")
        # Ensure last_updated is set to None or current time
        profiles_col.document(s["id"]).set(p)
        print(f"Created fresh profile for student: {s['name']} ({s['id']})")

    print("Database reseed completed successfully!")

if __name__ == "__main__":
    reseed()
