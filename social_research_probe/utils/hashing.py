"""
Stable, deterministic hashing utilities for JSON-serialisable objects.

Why this exists: many parts of the pipeline need a reproducible cache key or
deduplication fingerprint for arbitrary structured data (dicts, lists, scalars).
`stable_hash` provides a single, consistent answer across Python sessions.

Called by: FilesystemCache (cache.py) and any code that needs content-addressed
storage (pipeline deduplication, state hashing, etc.).
"""

from __future__ import annotations

import hashlib
import json


def stable_hash(obj: object) -> str:
    """Return a deterministic SHA-256 hex digest for any JSON-serialisable object.

    The object is first serialised with ``json.dumps(sort_keys=True)`` so that
    dicts with the same keys in different insertion orders produce the same hash.
    The resulting UTF-8 bytes are then fed to SHA-256.

    Args:
        obj: Any JSON-serialisable value — dict, list, str, int, float, or None.

    Returns:
        A 64-character lowercase hexadecimal string (SHA-256 digest).

    Raises:
        TypeError: Propagated directly from ``json.dumps`` when ``obj`` contains
            a value that cannot be serialised to JSON (e.g. a custom class
            instance, a ``set``, a ``bytes`` object).

    Why this exists:
        Python dict ordering is insertion-order-dependent (CPython 3.7+), so
        naively calling ``str(obj)`` or ``hash(obj)`` on two semantically
        identical dicts with different key-insertion histories would yield
        different results.  Sorting keys before serialisation eliminates this
        ambiguity without requiring callers to pre-sort their data.
    """
    # sort_keys=True ensures dict {b:1, a:2} and {a:2, b:1} produce identical JSON.
    serialised = json.dumps(obj, sort_keys=True)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()
