"""Deterministic canonical fingerprinting for AIOS Engineering Harness."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Sequence


def canonical_json_bytes(obj: Any) -> bytes:
    """Serialize an object to canonical UTF-8 JSON bytes with sorted keys and tight separators."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_sha256(data: bytes | str) -> str:
    """Compute lowercase 64-hex SHA-256 hash of UTF-8 bytes or string."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest().lower()


def compute_candidate_set_fingerprint(
    selected_evidence: Iterable[Any],
    excluded_evidence: Iterable[Any] = (),
) -> str:
    """Compute order-independent SHA-256 fingerprint for the union of candidate evidence items.
    
    Each item is converted to its canonical dict, serialized to canonical JSON bytes,
    sorted lexicographically, and hashed.
    """
    serialized_items: list[str] = []
    for item in selected_evidence:
        d = item.to_dict() if hasattr(item, "to_dict") else dict(item)
        serialized_items.append(canonical_json_bytes({"type": "SELECTED", "evidence": d}).decode("utf-8"))
    for ex in excluded_evidence:
        d = ex.to_dict() if hasattr(ex, "to_dict") else dict(ex)
        serialized_items.append(canonical_json_bytes({"type": "EXCLUDED", "exclusion": d}).decode("utf-8"))
    
    # Sort lexicographically for order-independence
    serialized_items.sort()
    payload_bytes = canonical_json_bytes(serialized_items)
    return compute_sha256(payload_bytes)


def compute_plan_fingerprint(
    task_id: str,
    snapshot: Any,
    selected_evidence: Sequence[Any],
    excluded_evidence: Sequence[Any],
    candidate_set_fingerprint: str,
    schema_version: str = "1",
) -> str:
    """Compute order-sensitive plan fingerprint binding snapshot, ranked selected evidence, and exclusions."""
    snapshot_dict = snapshot.to_dict() if hasattr(snapshot, "to_dict") else dict(snapshot)
    selected_dicts = [
        item.to_dict() if hasattr(item, "to_dict") else dict(item)
        for item in selected_evidence
    ]
    excluded_dicts = [
        ex.to_dict() if hasattr(ex, "to_dict") else dict(ex)
        for ex in excluded_evidence
    ]
    
    payload = {
        "candidate_set_fingerprint": candidate_set_fingerprint,
        "excluded_evidence": excluded_dicts,
        "schema_version": str(schema_version),
        "selected_evidence": selected_dicts,
        "snapshot": snapshot_dict,
        "task_id": str(task_id),
    }
    return compute_sha256(canonical_json_bytes(payload))
