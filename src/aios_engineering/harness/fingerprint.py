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
    """Compute order-independent SHA-256 fingerprint for the union of candidate evidence identities.
    
    Extracts the underlying RepositoryEvidenceRef identity from selected evidence and exclusions,
    serializes each evidence identity to canonical JSON, sorts them lexicographically, and hashes.
    """
    serialized_evidence_identities: list[str] = []
    
    for item in selected_evidence:
        d = item.to_dict() if hasattr(item, "to_dict") else dict(item)
        serialized_evidence_identities.append(canonical_json_bytes(d).decode("utf-8"))
        
    for ex in excluded_evidence:
        # For HarnessEvidenceExclusion, extract the underlying evidence reference
        if hasattr(ex, "evidence"):
            ev = ex.evidence
            d = ev.to_dict() if hasattr(ev, "to_dict") else dict(ev)
        elif isinstance(ex, dict) and "evidence" in ex:
            d = ex["evidence"]
        else:
            d = ex.to_dict() if hasattr(ex, "to_dict") else dict(ex)
        serialized_evidence_identities.append(canonical_json_bytes(d).decode("utf-8"))
    
    # Sort lexicographically for order-independence
    serialized_evidence_identities.sort()
    payload_bytes = canonical_json_bytes(serialized_evidence_identities)
    return compute_sha256(payload_bytes)


def compute_plan_fingerprint(
    task_id: str,
    snapshot: Any,
    selected_evidence: Sequence[Any],
    excluded_evidence: Sequence[Any],
    candidate_set_fingerprint: str,
    schema_version: str = "1",
) -> str:
    """Compute plan fingerprint binding snapshot, ranked selected evidence, deterministic exclusions, and candidate set.
    
    Selected evidence rank order is preserved as semantically meaningful.
    Exclusions are ordered canonically by deterministic serialization so incidental exclusion order has no semantic effect.
    """
    snapshot_dict = snapshot.to_dict() if hasattr(snapshot, "to_dict") else dict(snapshot)
    selected_dicts = [
        item.to_dict() if hasattr(item, "to_dict") else dict(item)
        for item in selected_evidence
    ]
    excluded_dicts = [
        ex.to_dict() if hasattr(ex, "to_dict") else dict(ex)
        for ex in excluded_evidence
    ]
    # Sort excluded dicts deterministically by canonical JSON bytes
    excluded_dicts.sort(key=lambda d: canonical_json_bytes(d))
    
    payload = {
        "candidate_set_fingerprint": candidate_set_fingerprint,
        "excluded_evidence": excluded_dicts,
        "schema_version": str(schema_version),
        "selected_evidence": selected_dicts,
        "snapshot": snapshot_dict,
        "task_id": str(task_id),
    }
    return compute_sha256(canonical_json_bytes(payload))
