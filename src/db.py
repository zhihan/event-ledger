"""Shared Firestore client factory."""

from __future__ import annotations

import os


def get_client():
    """Return a Firestore client (lazy import to avoid import-time errors).

    Respects ``LIVING_MEMORY_FIRESTORE_DATABASE`` to select a non-default
    database and ``GOOGLE_CLOUD_PROJECT`` for the project ID.
    """
    from google.cloud import firestore

    kwargs: dict[str, str] = {}
    database = os.environ.get("LIVING_MEMORY_FIRESTORE_DATABASE")
    if database:
        kwargs["database"] = database
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project:
        kwargs["project"] = project
    return firestore.Client(**kwargs)
