"""Canonical H4 Knowledge Registry + Explicit Lifecycle."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from src.aios_engineering.harness.contracts import (
    HarnessReceipt,
    _validate_hex_40,
    _validate_hex_64,
    _validate_posix_path,
)
from src.aios_engineering.harness.errors import (
    HarnessError,
    HarnessFingerprintError,
    HarnessValidationError,
)
from src.aios_engineering.harness.fingerprint import canonical_json_bytes, compute_sha256


H4_KNOWLEDGE_REGISTRY_POLICY_VERSION: str = "h4-knowledge-registry-v1"
H4_KNOWLEDGE_REGISTRY_SCHEMA_VERSION: str = "1"

# Bounded finite scales
MAX_KNOWLEDGE_ITEMS: int = 1024
MAX_KNOWLEDGE_PROVENANCE_REFS_PER_ITEM: int = 64
MAX_KNOWLEDGE_ID_LENGTH: int = 128
MAX_KNOWLEDGE_TITLE_LENGTH: int = 256
MAX_KNOWLEDGE_SUMMARY_LENGTH: int = 4096
MAX_KNOWLEDGE_METADATA_PAIRS: int = 32
MAX_KNOWLEDGE_METADATA_KEY_LENGTH: int = 64
MAX_KNOWLEDGE_METADATA_VALUE_LENGTH: int = 1024
MAX_KNOWLEDGE_METADATA_TOTAL_BYTES: int = 16384
MAX_KNOWLEDGE_REGISTRY_EVENTS: int = 4096
MAX_KNOWLEDGE_SERIALIZED_BYTES: int = 16 * 1024 * 1024
MAX_KNOWLEDGE_FINGERPRINT_PAYLOAD_BYTES: int = 64 * 1024 * 1024
MAX_KNOWLEDGE_SOURCE_PATH_LENGTH: int = 512


class RepositoryKnowledgeRegistryError(HarnessError):
    """Base error for canonical H4 knowledge registry operations."""


class RepositoryKnowledgeRegistryBoundError(RepositoryKnowledgeRegistryError):
    """Raised when an H4 knowledge registry hard bound is exceeded."""


class RepositoryKnowledgeRegistryStateError(RepositoryKnowledgeRegistryError):
    """Raised when an invalid state transition or stale fingerprint precondition occurs."""


class KnowledgeKind(str, Enum):
    """Exact knowledge kinds managed by H4."""

    INVARIANT = "INVARIANT"
    FINDING = "FINDING"
    LESSON = "LESSON"
    SKILL = "SKILL"


class KnowledgeValidationState(str, Enum):
    """Explicit validation state of a knowledge item."""

    UNVALIDATED = "UNVALIDATED"
    EVIDENCE_BACKED = "EVIDENCE_BACKED"
    HUMAN_APPROVED = "HUMAN_APPROVED"


class KnowledgeLifecycleState(str, Enum):
    """Explicit lifecycle state of a knowledge item."""

    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class KnowledgeAuthorityClass(str, Enum):
    """Authority class governing knowledge item precedence."""

    ADVISORY = "ADVISORY"
    CANONICAL_INVARIANT_REFERENCE = "CANONICAL_INVARIANT_REFERENCE"


class KnowledgeProvenanceKind(str, Enum):
    """Closed evidence/provenance kinds for H4 knowledge items."""

    TASK = "TASK"
    RESULT = "RESULT"
    REVIEW = "REVIEW"
    DECISION = "DECISION"
    LEARNING = "LEARNING"
    H2_GRAPH = "H2_GRAPH"
    H3_ROLE_TENDENCY = "H3_ROLE_TENDENCY"
    INVARIANT_AUTHORITY = "INVARIANT_AUTHORITY"
    OTHER_EXACT = "OTHER_EXACT"


class KnowledgeRegistryOperation(str, Enum):
    """Closed deterministic registry operations."""

    REGISTER = "REGISTER"
    SET_VALIDATION_STATE = "SET_VALIDATION_STATE"
    SET_LIFECYCLE_STATE = "SET_LIFECYCLE_STATE"
    AMEND_METADATA = "AMEND_METADATA"


VALID_VALIDATION_TRANSITIONS: frozenset[tuple[KnowledgeValidationState, KnowledgeValidationState]] = frozenset(
    {
        (KnowledgeValidationState.UNVALIDATED, KnowledgeValidationState.EVIDENCE_BACKED),
        (KnowledgeValidationState.UNVALIDATED, KnowledgeValidationState.HUMAN_APPROVED),
        (KnowledgeValidationState.EVIDENCE_BACKED, KnowledgeValidationState.HUMAN_APPROVED),
    }
)

VALID_LIFECYCLE_TRANSITIONS: frozenset[tuple[KnowledgeLifecycleState, KnowledgeLifecycleState]] = frozenset(
    {
        (KnowledgeLifecycleState.PROPOSED, KnowledgeLifecycleState.ACTIVE),
        (KnowledgeLifecycleState.PROPOSED, KnowledgeLifecycleState.RETIRED),
        (KnowledgeLifecycleState.ACTIVE, KnowledgeLifecycleState.RETIRED),
    }
)


def _validate_bounded_int(
    value: Any,
    field_name: str,
    *,
    min_val: int = 0,
    max_val: int | None = None,
) -> int:
    if type(value) is not int or isinstance(value, bool):
        raise HarnessValidationError(f"{field_name} must be an exact integer, not bool or other type")
    if value < min_val:
        raise HarnessValidationError(f"{field_name} must be >= {min_val}: got {value}")
    if max_val is not None and value > max_val:
        raise RepositoryKnowledgeRegistryBoundError(
            f"{field_name} ({value}) exceeds hard limit ({max_val})"
        )
    return value


def _bounded_fingerprint(payload: Any) -> str:
    encoded = canonical_json_bytes(payload)
    if len(encoded) > MAX_KNOWLEDGE_FINGERPRINT_PAYLOAD_BYTES:
        raise RepositoryKnowledgeRegistryBoundError(
            f"payload bytes ({len(encoded)}) exceeds hard limit ({MAX_KNOWLEDGE_FINGERPRINT_PAYLOAD_BYTES})"
        )
    return compute_sha256(encoded)


def _validate_knowledge_id(knowledge_id: str) -> None:
    if type(knowledge_id) is not str or not knowledge_id:
        raise HarnessValidationError("knowledge_id must be a non-empty string")
    if len(knowledge_id) > MAX_KNOWLEDGE_ID_LENGTH:
        raise RepositoryKnowledgeRegistryBoundError(
            f"knowledge_id length ({len(knowledge_id)}) exceeds hard limit ({MAX_KNOWLEDGE_ID_LENGTH})"
        )
    for c in knowledge_id:
        if not (c.isalnum() or c in ":-_./"):
            raise HarnessValidationError(
                f"knowledge_id contains disallowed character {c!r}: {knowledge_id!r}"
            )


def _validate_metadata_mapping(metadata: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(metadata, Mapping):
        raise HarnessValidationError("metadata must be a Mapping")
    if len(metadata) > MAX_KNOWLEDGE_METADATA_PAIRS:
        raise RepositoryKnowledgeRegistryBoundError(
            f"metadata pairs count ({len(metadata)}) exceeds hard limit ({MAX_KNOWLEDGE_METADATA_PAIRS})"
        )
    cleaned: dict[str, str] = {}
    for k, v in metadata.items():
        if type(k) is not str or not k:
            raise HarnessValidationError("metadata key must be a non-empty string")
        if len(k) > MAX_KNOWLEDGE_METADATA_KEY_LENGTH:
            raise RepositoryKnowledgeRegistryBoundError(
                f"metadata key length ({len(k)}) exceeds hard limit ({MAX_KNOWLEDGE_METADATA_KEY_LENGTH})"
            )
        if type(v) is not str:
            raise HarnessValidationError("metadata value must be a string")
        if len(v) > MAX_KNOWLEDGE_METADATA_VALUE_LENGTH:
            raise RepositoryKnowledgeRegistryBoundError(
                f"metadata value length ({len(v)}) exceeds hard limit ({MAX_KNOWLEDGE_METADATA_VALUE_LENGTH})"
            )
        cleaned[k] = v

    encoded = canonical_json_bytes(cleaned)
    if len(encoded) > MAX_KNOWLEDGE_METADATA_TOTAL_BYTES:
        raise RepositoryKnowledgeRegistryBoundError(
            f"total metadata bytes ({len(encoded)}) exceeds hard limit ({MAX_KNOWLEDGE_METADATA_TOTAL_BYTES})"
        )
    return {k: cleaned[k] for k in sorted(cleaned.keys())}


def _provenance_payload(
    *,
    source_path: str,
    source_blob_sha: str,
    provenance_kind: KnowledgeProvenanceKind,
    source_evidence_fingerprint: str,
    source_snapshot_sha: str | None,
) -> dict[str, Any]:
    return {
        "provenance_kind": provenance_kind.value,
        "source_blob_sha": source_blob_sha,
        "source_evidence_fingerprint": source_evidence_fingerprint,
        "source_path": source_path,
        "source_snapshot_sha": source_snapshot_sha,
    }


@dataclass(frozen=True)
class KnowledgeProvenanceRef:
    """Exact provenance link to evidence backing a knowledge item."""

    source_path: str
    source_blob_sha: str
    provenance_kind: KnowledgeProvenanceKind
    source_evidence_fingerprint: str
    source_snapshot_sha: str | None
    provenance_fingerprint: str

    def __post_init__(self) -> None:
        if type(self.provenance_kind) is not KnowledgeProvenanceKind:
            raise HarnessValidationError(
                f"provenance_kind must be an exact KnowledgeProvenanceKind: got {self.provenance_kind!r}"
            )
        _validate_posix_path(self.source_path)
        if len(self.source_path) > MAX_KNOWLEDGE_SOURCE_PATH_LENGTH:
            raise RepositoryKnowledgeRegistryBoundError(
                f"source_path length ({len(self.source_path)}) exceeds hard limit ({MAX_KNOWLEDGE_SOURCE_PATH_LENGTH})"
            )
        _validate_hex_40(self.source_blob_sha, "source_blob_sha")
        _validate_hex_64(self.source_evidence_fingerprint, "source_evidence_fingerprint")
        if self.source_snapshot_sha is not None:
            _validate_hex_40(self.source_snapshot_sha, "source_snapshot_sha")

        _validate_hex_64(self.provenance_fingerprint, "provenance_fingerprint")
        expected_fingerprint = _bounded_fingerprint(
            _provenance_payload(
                source_path=self.source_path,
                source_blob_sha=self.source_blob_sha,
                provenance_kind=self.provenance_kind,
                source_evidence_fingerprint=self.source_evidence_fingerprint,
                source_snapshot_sha=self.source_snapshot_sha,
            )
        )
        if self.provenance_fingerprint != expected_fingerprint:
            raise HarnessFingerprintError("KnowledgeProvenanceRef fingerprint mismatch")

    @classmethod
    def create(
        cls,
        *,
        source_path: str,
        source_blob_sha: str,
        provenance_kind: KnowledgeProvenanceKind,
        source_evidence_fingerprint: str,
        source_snapshot_sha: str | None = None,
    ) -> "KnowledgeProvenanceRef":
        _validate_posix_path(source_path)
        if len(source_path) > MAX_KNOWLEDGE_SOURCE_PATH_LENGTH:
            raise RepositoryKnowledgeRegistryBoundError(
                f"source_path length ({len(source_path)}) exceeds hard limit ({MAX_KNOWLEDGE_SOURCE_PATH_LENGTH})"
            )
        _validate_hex_40(source_blob_sha, "source_blob_sha")
        if type(provenance_kind) is not KnowledgeProvenanceKind:
            raise HarnessValidationError(
                f"provenance_kind must be an exact KnowledgeProvenanceKind: got {provenance_kind!r}"
            )
        _validate_hex_64(source_evidence_fingerprint, "source_evidence_fingerprint")
        if source_snapshot_sha is not None:
            _validate_hex_40(source_snapshot_sha, "source_snapshot_sha")

        fingerprint = _bounded_fingerprint(
            _provenance_payload(
                source_path=source_path,
                source_blob_sha=source_blob_sha,
                provenance_kind=provenance_kind,
                source_evidence_fingerprint=source_evidence_fingerprint,
                source_snapshot_sha=source_snapshot_sha,
            )
        )
        return cls(
            source_path=source_path,
            source_blob_sha=source_blob_sha,
            provenance_kind=provenance_kind,
            source_evidence_fingerprint=source_evidence_fingerprint,
            source_snapshot_sha=source_snapshot_sha,
            provenance_fingerprint=fingerprint,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance_fingerprint": self.provenance_fingerprint,
            "provenance_kind": self.provenance_kind.value,
            "source_blob_sha": self.source_blob_sha,
            "source_evidence_fingerprint": self.source_evidence_fingerprint,
            "source_path": self.source_path,
            "source_snapshot_sha": self.source_snapshot_sha,
        }


def _provenance_sort_key(p: KnowledgeProvenanceRef) -> tuple[str, str, str, str, str]:
    return (
        p.source_path,
        p.source_blob_sha,
        p.provenance_kind.value,
        p.source_evidence_fingerprint,
        p.source_snapshot_sha or "",
    )


def _item_payload(
    *,
    authority_class: KnowledgeAuthorityClass,
    kind: KnowledgeKind,
    knowledge_id: str,
    lifecycle_state: KnowledgeLifecycleState,
    metadata: Mapping[str, str],
    provenance_refs: Sequence[KnowledgeProvenanceRef],
    summary: str,
    title: str,
    validation_state: KnowledgeValidationState,
) -> dict[str, Any]:
    return {
        "authority_class": authority_class.value,
        "kind": kind.value,
        "knowledge_id": knowledge_id,
        "lifecycle_state": lifecycle_state.value,
        "metadata": {k: metadata[k] for k in sorted(metadata.keys())},
        "provenance_refs": [p.to_dict() for p in provenance_refs],
        "summary": summary,
        "title": title,
        "validation_state": validation_state.value,
    }


@dataclass(frozen=True)
class KnowledgeItem:
    """Canonical immutable technical memory item with explicit provenance and lifecycle."""

    knowledge_id: str
    kind: KnowledgeKind
    title: str
    summary: str
    provenance_refs: tuple[KnowledgeProvenanceRef, ...]
    validation_state: KnowledgeValidationState
    lifecycle_state: KnowledgeLifecycleState
    authority_class: KnowledgeAuthorityClass
    metadata: Mapping[str, str]
    item_fingerprint: str

    def __post_init__(self) -> None:
        _validate_knowledge_id(self.knowledge_id)
        if type(self.kind) is not KnowledgeKind:
            raise HarnessValidationError(f"kind must be an exact KnowledgeKind: got {self.kind!r}")
        if type(self.title) is not str or not self.title:
            raise HarnessValidationError("title must be a non-empty string")
        if len(self.title) > MAX_KNOWLEDGE_TITLE_LENGTH:
            raise RepositoryKnowledgeRegistryBoundError(
                f"title length ({len(self.title)}) exceeds hard limit ({MAX_KNOWLEDGE_TITLE_LENGTH})"
            )
        if type(self.summary) is not str or not self.summary:
            raise HarnessValidationError("summary must be a non-empty string")
        if len(self.summary) > MAX_KNOWLEDGE_SUMMARY_LENGTH:
            raise RepositoryKnowledgeRegistryBoundError(
                f"summary length ({len(self.summary)}) exceeds hard limit ({MAX_KNOWLEDGE_SUMMARY_LENGTH})"
            )

        if type(self.provenance_refs) is not tuple or len(self.provenance_refs) < 1:
            raise HarnessValidationError("provenance_refs must be a non-empty tuple")
        if len(self.provenance_refs) > MAX_KNOWLEDGE_PROVENANCE_REFS_PER_ITEM:
            raise RepositoryKnowledgeRegistryBoundError(
                f"provenance_refs count ({len(self.provenance_refs)}) exceeds hard limit "
                f"({MAX_KNOWLEDGE_PROVENANCE_REFS_PER_ITEM})"
            )

        seen_prov: set[str] = set()
        for idx, p in enumerate(self.provenance_refs):
            if type(p) is not KnowledgeProvenanceRef:
                raise HarnessValidationError(
                    f"provenance_refs must contain KnowledgeProvenanceRef: got {p!r}"
                )
            if p.provenance_fingerprint in seen_prov:
                raise HarnessValidationError(
                    f"duplicate provenance ref fingerprint: {p.provenance_fingerprint}"
                )
            seen_prov.add(p.provenance_fingerprint)
            if idx > 0 and _provenance_sort_key(p) < _provenance_sort_key(self.provenance_refs[idx - 1]):
                raise HarnessValidationError("provenance_refs must be sorted canonically")

        if type(self.validation_state) is not KnowledgeValidationState:
            raise HarnessValidationError(
                f"validation_state must be an exact KnowledgeValidationState: got {self.validation_state!r}"
            )
        if type(self.lifecycle_state) is not KnowledgeLifecycleState:
            raise HarnessValidationError(
                f"lifecycle_state must be an exact KnowledgeLifecycleState: got {self.lifecycle_state!r}"
            )
        if type(self.authority_class) is not KnowledgeAuthorityClass:
            raise HarnessValidationError(
                f"authority_class must be an exact KnowledgeAuthorityClass: got {self.authority_class!r}"
            )

        # Precedence boundaries
        if self.kind in (KnowledgeKind.FINDING, KnowledgeKind.LESSON, KnowledgeKind.SKILL):
            if self.authority_class is not KnowledgeAuthorityClass.ADVISORY:
                raise HarnessValidationError(
                    f"{self.kind.value} items must strictly have authority_class=ADVISORY: "
                    f"got {self.authority_class.value}"
                )

        if self.authority_class is KnowledgeAuthorityClass.CANONICAL_INVARIANT_REFERENCE:
            if self.kind is not KnowledgeKind.INVARIANT:
                raise HarnessValidationError(
                    "CANONICAL_INVARIANT_REFERENCE is only valid for INVARIANT knowledge items"
                )
            if self.validation_state is not KnowledgeValidationState.HUMAN_APPROVED:
                raise HarnessValidationError(
                    "CANONICAL_INVARIANT_REFERENCE requires validation_state=HUMAN_APPROVED"
                )
            has_authority_prov = any(
                p.provenance_kind in (KnowledgeProvenanceKind.INVARIANT_AUTHORITY, KnowledgeProvenanceKind.DECISION)
                for p in self.provenance_refs
            )
            if not has_authority_prov:
                raise HarnessValidationError(
                    "CANONICAL_INVARIANT_REFERENCE requires explicit INVARIANT_AUTHORITY or DECISION provenance"
                )

        cleaned_meta = _validate_metadata_mapping(self.metadata)
        frozen_meta = MappingProxyType(cleaned_meta)
        object.__setattr__(self, "metadata", frozen_meta)

        _validate_hex_64(self.item_fingerprint, "item_fingerprint")
        expected_fingerprint = _bounded_fingerprint(
            _item_payload(
                authority_class=self.authority_class,
                kind=self.kind,
                knowledge_id=self.knowledge_id,
                lifecycle_state=self.lifecycle_state,
                metadata=self.metadata,
                provenance_refs=self.provenance_refs,
                summary=self.summary,
                title=self.title,
                validation_state=self.validation_state,
            )
        )
        if self.item_fingerprint != expected_fingerprint:
            raise HarnessFingerprintError(f"KnowledgeItem fingerprint mismatch for {self.knowledge_id}")

    @classmethod
    def create(
        cls,
        *,
        knowledge_id: str,
        kind: KnowledgeKind,
        title: str,
        summary: str,
        provenance_refs: Sequence[KnowledgeProvenanceRef],
        validation_state: KnowledgeValidationState = KnowledgeValidationState.UNVALIDATED,
        lifecycle_state: KnowledgeLifecycleState = KnowledgeLifecycleState.PROPOSED,
        authority_class: KnowledgeAuthorityClass = KnowledgeAuthorityClass.ADVISORY,
        metadata: Mapping[str, str] | None = None,
    ) -> "KnowledgeItem":
        _validate_knowledge_id(knowledge_id)
        if type(kind) is not KnowledgeKind:
            raise HarnessValidationError(f"kind must be an exact KnowledgeKind: got {kind!r}")
        if type(validation_state) is not KnowledgeValidationState:
            raise HarnessValidationError(
                f"validation_state must be an exact KnowledgeValidationState: got {validation_state!r}"
            )
        if type(lifecycle_state) is not KnowledgeLifecycleState:
            raise HarnessValidationError(
                f"lifecycle_state must be an exact KnowledgeLifecycleState: got {lifecycle_state!r}"
            )
        if type(authority_class) is not KnowledgeAuthorityClass:
            raise HarnessValidationError(
                f"authority_class must be an exact KnowledgeAuthorityClass: got {authority_class!r}"
            )

        if not provenance_refs:
            raise HarnessValidationError("provenance_refs must not be empty")

        seen_prov: set[str] = set()
        for p in provenance_refs:
            if not isinstance(p, KnowledgeProvenanceRef):
                raise HarnessValidationError(
                    f"provenance_refs must contain KnowledgeProvenanceRef: got {p!r}"
                )
            if p.provenance_fingerprint in seen_prov:
                raise HarnessValidationError(
                    f"duplicate provenance ref fingerprint: {p.provenance_fingerprint}"
                )
            seen_prov.add(p.provenance_fingerprint)

        sorted_prov = tuple(sorted(provenance_refs, key=_provenance_sort_key))
        cleaned_meta = _validate_metadata_mapping(dict(metadata or {}))
        frozen_meta = MappingProxyType(cleaned_meta)

        fingerprint = _bounded_fingerprint(
            _item_payload(
                authority_class=authority_class,
                kind=kind,
                knowledge_id=knowledge_id,
                lifecycle_state=lifecycle_state,
                metadata=frozen_meta,
                provenance_refs=sorted_prov,
                summary=summary,
                title=title,
                validation_state=validation_state,
            )
        )
        return cls(
            knowledge_id=knowledge_id,
            kind=kind,
            title=title,
            summary=summary,
            provenance_refs=sorted_prov,
            validation_state=validation_state,
            lifecycle_state=lifecycle_state,
            authority_class=authority_class,
            metadata=frozen_meta,
            item_fingerprint=fingerprint,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "authority_class": self.authority_class.value,
            "item_fingerprint": self.item_fingerprint,
            "kind": self.kind.value,
            "knowledge_id": self.knowledge_id,
            "lifecycle_state": self.lifecycle_state.value,
            "metadata": dict(self.metadata),
            "provenance_refs": [p.to_dict() for p in self.provenance_refs],
            "summary": self.summary,
            "title": self.title,
            "validation_state": self.validation_state.value,
        }


def _event_payload(
    *,
    event_seq: int,
    knowledge_id: str,
    new_item_fingerprint: str | None,
    operation: KnowledgeRegistryOperation,
    prior_item_fingerprint: str | None,
    prior_registry_fingerprint: str,
    transition_evidence_fingerprint: str,
) -> dict[str, Any]:
    return {
        "event_seq": event_seq,
        "knowledge_id": knowledge_id,
        "new_item_fingerprint": new_item_fingerprint,
        "operation": operation.value,
        "prior_item_fingerprint": prior_item_fingerprint,
        "prior_registry_fingerprint": prior_registry_fingerprint,
        "transition_evidence_fingerprint": transition_evidence_fingerprint,
    }


@dataclass(frozen=True)
class KnowledgeRegistryEvent:
    """Deterministic audit record of an operation executed on the knowledge registry."""

    event_seq: int
    operation: KnowledgeRegistryOperation
    knowledge_id: str
    prior_registry_fingerprint: str
    prior_item_fingerprint: str | None
    new_item_fingerprint: str | None
    transition_evidence_fingerprint: str
    event_fingerprint: str

    def __post_init__(self) -> None:
        _validate_bounded_int(
            self.event_seq,
            "event_seq",
            min_val=0,
            max_val=MAX_KNOWLEDGE_REGISTRY_EVENTS,
        )
        if type(self.operation) is not KnowledgeRegistryOperation:
            raise HarnessValidationError(
                f"operation must be an exact KnowledgeRegistryOperation: got {self.operation!r}"
            )
        _validate_knowledge_id(self.knowledge_id)
        _validate_hex_64(self.prior_registry_fingerprint, "prior_registry_fingerprint")
        if self.prior_item_fingerprint is not None:
            _validate_hex_64(self.prior_item_fingerprint, "prior_item_fingerprint")
        if self.new_item_fingerprint is not None:
            _validate_hex_64(self.new_item_fingerprint, "new_item_fingerprint")
        _validate_hex_64(self.transition_evidence_fingerprint, "transition_evidence_fingerprint")

        _validate_hex_64(self.event_fingerprint, "event_fingerprint")
        expected_fingerprint = _bounded_fingerprint(
            _event_payload(
                event_seq=self.event_seq,
                knowledge_id=self.knowledge_id,
                new_item_fingerprint=self.new_item_fingerprint,
                operation=self.operation,
                prior_item_fingerprint=self.prior_item_fingerprint,
                prior_registry_fingerprint=self.prior_registry_fingerprint,
                transition_evidence_fingerprint=self.transition_evidence_fingerprint,
            )
        )
        if self.event_fingerprint != expected_fingerprint:
            raise HarnessFingerprintError(f"KnowledgeRegistryEvent fingerprint mismatch for seq {self.event_seq}")

    @classmethod
    def create(
        cls,
        *,
        event_seq: int,
        operation: KnowledgeRegistryOperation,
        knowledge_id: str,
        prior_registry_fingerprint: str,
        prior_item_fingerprint: str | None,
        new_item_fingerprint: str | None,
        transition_evidence_fingerprint: str,
    ) -> "KnowledgeRegistryEvent":
        if type(operation) is not KnowledgeRegistryOperation:
            raise HarnessValidationError(
                f"operation must be an exact KnowledgeRegistryOperation: got {operation!r}"
            )
        fingerprint = _bounded_fingerprint(
            _event_payload(
                event_seq=event_seq,
                knowledge_id=knowledge_id,
                new_item_fingerprint=new_item_fingerprint,
                operation=operation,
                prior_item_fingerprint=prior_item_fingerprint,
                prior_registry_fingerprint=prior_registry_fingerprint,
                transition_evidence_fingerprint=transition_evidence_fingerprint,
            )
        )
        return cls(
            event_seq=event_seq,
            operation=operation,
            knowledge_id=knowledge_id,
            prior_registry_fingerprint=prior_registry_fingerprint,
            prior_item_fingerprint=prior_item_fingerprint,
            new_item_fingerprint=new_item_fingerprint,
            transition_evidence_fingerprint=transition_evidence_fingerprint,
            event_fingerprint=fingerprint,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_fingerprint": self.event_fingerprint,
            "event_seq": self.event_seq,
            "knowledge_id": self.knowledge_id,
            "new_item_fingerprint": self.new_item_fingerprint,
            "operation": self.operation.value,
            "prior_item_fingerprint": self.prior_item_fingerprint,
            "prior_registry_fingerprint": self.prior_registry_fingerprint,
            "transition_evidence_fingerprint": self.transition_evidence_fingerprint,
        }


def _registry_payload(
    *,
    events: Sequence[KnowledgeRegistryEvent],
    items: Sequence[KnowledgeItem],
    policy_version: str,
    schema_version: str,
) -> dict[str, Any]:
    return {
        "events": [e.to_dict() for e in events],
        "items": [item.to_dict() for item in items],
        "policy_version": policy_version,
        "schema_version": schema_version,
    }


@dataclass(frozen=True)
class KnowledgeRegistryState:
    """Immutable, fingerprint-guarded registry state containing technical knowledge items and event audit."""

    schema_version: str
    policy_version: str
    items: tuple[KnowledgeItem, ...]
    events: tuple[KnowledgeRegistryEvent, ...]
    registry_fingerprint: str

    def __post_init__(self) -> None:
        if self.schema_version != H4_KNOWLEDGE_REGISTRY_SCHEMA_VERSION:
            raise HarnessValidationError("invalid H4 knowledge registry schema version")
        if self.policy_version != H4_KNOWLEDGE_REGISTRY_POLICY_VERSION:
            raise HarnessValidationError("invalid H4 knowledge registry policy version")

        if type(self.items) is not tuple:
            raise HarnessValidationError("items must be an exact tuple")
        if len(self.items) > MAX_KNOWLEDGE_ITEMS:
            raise RepositoryKnowledgeRegistryBoundError(
                f"items count ({len(self.items)}) exceeds hard limit ({MAX_KNOWLEDGE_ITEMS})"
            )

        seen_ids: set[str] = set()
        for idx, item in enumerate(self.items):
            if type(item) is not KnowledgeItem:
                raise HarnessValidationError(f"items must contain KnowledgeItem: got {item!r}")
            if item.knowledge_id in seen_ids:
                raise HarnessValidationError(f"duplicate knowledge_id in registry: {item.knowledge_id}")
            seen_ids.add(item.knowledge_id)
            if idx > 0 and item.knowledge_id < self.items[idx - 1].knowledge_id:
                raise HarnessValidationError("items must be sorted in canonical knowledge_id order")

        if type(self.events) is not tuple:
            raise HarnessValidationError("events must be an exact tuple")
        if len(self.events) > MAX_KNOWLEDGE_REGISTRY_EVENTS:
            raise RepositoryKnowledgeRegistryBoundError(
                f"events count ({len(self.events)}) exceeds hard limit ({MAX_KNOWLEDGE_REGISTRY_EVENTS})"
            )

        for idx, event in enumerate(self.events):
            if type(event) is not KnowledgeRegistryEvent:
                raise HarnessValidationError(f"events must contain KnowledgeRegistryEvent: got {event!r}")
            if event.event_seq != idx:
                raise HarnessValidationError(
                    f"event sequence mismatch: expected {idx}, got {event.event_seq}"
                )

        _validate_hex_64(self.registry_fingerprint, "registry_fingerprint")
        expected_fingerprint = _bounded_fingerprint(
            _registry_payload(
                events=self.events,
                items=self.items,
                policy_version=self.policy_version,
                schema_version=self.schema_version,
            )
        )
        if self.registry_fingerprint != expected_fingerprint:
            raise HarnessFingerprintError("KnowledgeRegistryState fingerprint mismatch")

    @classmethod
    def create(
        cls,
        *,
        items: Sequence[KnowledgeItem] = (),
        events: Sequence[KnowledgeRegistryEvent] = (),
    ) -> "KnowledgeRegistryState":
        seen_ids: set[str] = set()
        for it in items:
            if not isinstance(it, KnowledgeItem):
                raise HarnessValidationError(f"items must contain KnowledgeItem: got {it!r}")
            if it.knowledge_id in seen_ids:
                raise HarnessValidationError(f"duplicate knowledge_id: {it.knowledge_id}")
            seen_ids.add(it.knowledge_id)

        sorted_items = tuple(sorted(items, key=lambda it: it.knowledge_id))
        tuple_events = tuple(events)

        fingerprint = _bounded_fingerprint(
            _registry_payload(
                events=tuple_events,
                items=sorted_items,
                policy_version=H4_KNOWLEDGE_REGISTRY_POLICY_VERSION,
                schema_version=H4_KNOWLEDGE_REGISTRY_SCHEMA_VERSION,
            )
        )
        return cls(
            schema_version=H4_KNOWLEDGE_REGISTRY_SCHEMA_VERSION,
            policy_version=H4_KNOWLEDGE_REGISTRY_POLICY_VERSION,
            items=sorted_items,
            events=tuple_events,
            registry_fingerprint=fingerprint,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "events": [e.to_dict() for e in self.events],
            "items": [item.to_dict() for item in self.items],
            "policy_version": self.policy_version,
            "registry_fingerprint": self.registry_fingerprint,
            "schema_version": self.schema_version,
        }

    def get_item(self, knowledge_id: str) -> KnowledgeItem | None:
        for item in self.items:
            if item.knowledge_id == knowledge_id:
                return item
        return None


def create_empty_knowledge_registry() -> KnowledgeRegistryState:
    """Creates a new empty knowledge registry state."""
    return KnowledgeRegistryState.create(items=(), events=())


def register_knowledge_item(
    state: KnowledgeRegistryState,
    item: KnowledgeItem,
    transition_evidence_fingerprint: str,
) -> tuple[KnowledgeRegistryState, KnowledgeRegistryEvent]:
    """Registers a new knowledge item in the registry, appending an immutable event."""
    if type(state) is not KnowledgeRegistryState:
        raise HarnessValidationError("state must be exact KnowledgeRegistryState")
    if type(item) is not KnowledgeItem:
        raise HarnessValidationError("item must be exact KnowledgeItem")
    _validate_hex_64(transition_evidence_fingerprint, "transition_evidence_fingerprint")

    if state.get_item(item.knowledge_id) is not None:
        raise RepositoryKnowledgeRegistryStateError(
            f"knowledge_id already exists in registry: {item.knowledge_id}"
        )

    event = KnowledgeRegistryEvent.create(
        event_seq=len(state.events),
        operation=KnowledgeRegistryOperation.REGISTER,
        knowledge_id=item.knowledge_id,
        prior_registry_fingerprint=state.registry_fingerprint,
        prior_item_fingerprint=None,
        new_item_fingerprint=item.item_fingerprint,
        transition_evidence_fingerprint=transition_evidence_fingerprint,
    )

    new_items = sorted((*state.items, item), key=lambda it: it.knowledge_id)
    new_state = KnowledgeRegistryState.create(
        items=new_items,
        events=(*state.events, event),
    )
    return new_state, event


def set_knowledge_validation_state(
    state: KnowledgeRegistryState,
    knowledge_id: str,
    new_validation_state: KnowledgeValidationState,
    expected_item_fingerprint: str,
    expected_registry_fingerprint: str,
    transition_evidence_fingerprint: str,
) -> tuple[KnowledgeRegistryState, KnowledgeRegistryEvent]:
    """Executes a valid forward validation transition for a knowledge item."""
    if type(state) is not KnowledgeRegistryState:
        raise HarnessValidationError("state must be exact KnowledgeRegistryState")
    _validate_knowledge_id(knowledge_id)
    if type(new_validation_state) is not KnowledgeValidationState:
        raise HarnessValidationError("new_validation_state must be exact KnowledgeValidationState")
    _validate_hex_64(expected_item_fingerprint, "expected_item_fingerprint")
    _validate_hex_64(expected_registry_fingerprint, "expected_registry_fingerprint")
    _validate_hex_64(transition_evidence_fingerprint, "transition_evidence_fingerprint")

    if state.registry_fingerprint != expected_registry_fingerprint:
        raise RepositoryKnowledgeRegistryStateError(
            f"registry fingerprint mismatch: expected {expected_registry_fingerprint}, got {state.registry_fingerprint}"
        )

    current_item = state.get_item(knowledge_id)
    if current_item is None:
        raise RepositoryKnowledgeRegistryStateError(f"knowledge_id not found: {knowledge_id}")

    if current_item.item_fingerprint != expected_item_fingerprint:
        raise RepositoryKnowledgeRegistryStateError(
            f"item fingerprint mismatch: expected {expected_item_fingerprint}, got {current_item.item_fingerprint}"
        )

    if (current_item.validation_state, new_validation_state) not in VALID_VALIDATION_TRANSITIONS:
        raise RepositoryKnowledgeRegistryStateError(
            f"invalid validation transition from {current_item.validation_state.value} to {new_validation_state.value}"
        )

    updated_item = KnowledgeItem.create(
        knowledge_id=current_item.knowledge_id,
        kind=current_item.kind,
        title=current_item.title,
        summary=current_item.summary,
        provenance_refs=current_item.provenance_refs,
        validation_state=new_validation_state,
        lifecycle_state=current_item.lifecycle_state,
        authority_class=current_item.authority_class,
        metadata=current_item.metadata,
    )

    event = KnowledgeRegistryEvent.create(
        event_seq=len(state.events),
        operation=KnowledgeRegistryOperation.SET_VALIDATION_STATE,
        knowledge_id=knowledge_id,
        prior_registry_fingerprint=state.registry_fingerprint,
        prior_item_fingerprint=current_item.item_fingerprint,
        new_item_fingerprint=updated_item.item_fingerprint,
        transition_evidence_fingerprint=transition_evidence_fingerprint,
    )

    new_items = [it if it.knowledge_id != knowledge_id else updated_item for it in state.items]
    new_state = KnowledgeRegistryState.create(
        items=new_items,
        events=(*state.events, event),
    )
    return new_state, event


def set_knowledge_lifecycle_state(
    state: KnowledgeRegistryState,
    knowledge_id: str,
    new_lifecycle_state: KnowledgeLifecycleState,
    expected_item_fingerprint: str,
    expected_registry_fingerprint: str,
    transition_evidence_fingerprint: str,
) -> tuple[KnowledgeRegistryState, KnowledgeRegistryEvent]:
    """Executes a valid forward lifecycle transition for a knowledge item."""
    if type(state) is not KnowledgeRegistryState:
        raise HarnessValidationError("state must be exact KnowledgeRegistryState")
    _validate_knowledge_id(knowledge_id)
    if type(new_lifecycle_state) is not KnowledgeLifecycleState:
        raise HarnessValidationError("new_lifecycle_state must be exact KnowledgeLifecycleState")
    _validate_hex_64(expected_item_fingerprint, "expected_item_fingerprint")
    _validate_hex_64(expected_registry_fingerprint, "expected_registry_fingerprint")
    _validate_hex_64(transition_evidence_fingerprint, "transition_evidence_fingerprint")

    if state.registry_fingerprint != expected_registry_fingerprint:
        raise RepositoryKnowledgeRegistryStateError(
            f"registry fingerprint mismatch: expected {expected_registry_fingerprint}, got {state.registry_fingerprint}"
        )

    current_item = state.get_item(knowledge_id)
    if current_item is None:
        raise RepositoryKnowledgeRegistryStateError(f"knowledge_id not found: {knowledge_id}")

    if current_item.item_fingerprint != expected_item_fingerprint:
        raise RepositoryKnowledgeRegistryStateError(
            f"item fingerprint mismatch: expected {expected_item_fingerprint}, got {current_item.item_fingerprint}"
        )

    if (current_item.lifecycle_state, new_lifecycle_state) not in VALID_LIFECYCLE_TRANSITIONS:
        raise RepositoryKnowledgeRegistryStateError(
            f"invalid lifecycle transition from {current_item.lifecycle_state.value} to {new_lifecycle_state.value}"
        )

    updated_item = KnowledgeItem.create(
        knowledge_id=current_item.knowledge_id,
        kind=current_item.kind,
        title=current_item.title,
        summary=current_item.summary,
        provenance_refs=current_item.provenance_refs,
        validation_state=current_item.validation_state,
        lifecycle_state=new_lifecycle_state,
        authority_class=current_item.authority_class,
        metadata=current_item.metadata,
    )

    event = KnowledgeRegistryEvent.create(
        event_seq=len(state.events),
        operation=KnowledgeRegistryOperation.SET_LIFECYCLE_STATE,
        knowledge_id=knowledge_id,
        prior_registry_fingerprint=state.registry_fingerprint,
        prior_item_fingerprint=current_item.item_fingerprint,
        new_item_fingerprint=updated_item.item_fingerprint,
        transition_evidence_fingerprint=transition_evidence_fingerprint,
    )

    new_items = [it if it.knowledge_id != knowledge_id else updated_item for it in state.items]
    new_state = KnowledgeRegistryState.create(
        items=new_items,
        events=(*state.events, event),
    )
    return new_state, event


def amend_knowledge_metadata(
    state: KnowledgeRegistryState,
    knowledge_id: str,
    new_metadata: Mapping[str, str],
    expected_item_fingerprint: str,
    expected_registry_fingerprint: str,
    transition_evidence_fingerprint: str,
) -> tuple[KnowledgeRegistryState, KnowledgeRegistryEvent]:
    """Amends bounded advisory metadata on a knowledge item under exact fingerprint preconditions."""
    if type(state) is not KnowledgeRegistryState:
        raise HarnessValidationError("state must be exact KnowledgeRegistryState")
    _validate_knowledge_id(knowledge_id)
    _validate_hex_64(expected_item_fingerprint, "expected_item_fingerprint")
    _validate_hex_64(expected_registry_fingerprint, "expected_registry_fingerprint")
    _validate_hex_64(transition_evidence_fingerprint, "transition_evidence_fingerprint")
    cleaned_meta = _validate_metadata_mapping(dict(new_metadata))

    if state.registry_fingerprint != expected_registry_fingerprint:
        raise RepositoryKnowledgeRegistryStateError(
            f"registry fingerprint mismatch: expected {expected_registry_fingerprint}, got {state.registry_fingerprint}"
        )

    current_item = state.get_item(knowledge_id)
    if current_item is None:
        raise RepositoryKnowledgeRegistryStateError(f"knowledge_id not found: {knowledge_id}")

    if current_item.item_fingerprint != expected_item_fingerprint:
        raise RepositoryKnowledgeRegistryStateError(
            f"item fingerprint mismatch: expected {expected_item_fingerprint}, got {current_item.item_fingerprint}"
        )

    if dict(current_item.metadata) == cleaned_meta:
        raise RepositoryKnowledgeRegistryStateError("amend_knowledge_metadata requires modifying metadata")

    updated_item = KnowledgeItem.create(
        knowledge_id=current_item.knowledge_id,
        kind=current_item.kind,
        title=current_item.title,
        summary=current_item.summary,
        provenance_refs=current_item.provenance_refs,
        validation_state=current_item.validation_state,
        lifecycle_state=current_item.lifecycle_state,
        authority_class=current_item.authority_class,
        metadata=cleaned_meta,
    )

    event = KnowledgeRegistryEvent.create(
        event_seq=len(state.events),
        operation=KnowledgeRegistryOperation.AMEND_METADATA,
        knowledge_id=knowledge_id,
        prior_registry_fingerprint=state.registry_fingerprint,
        prior_item_fingerprint=current_item.item_fingerprint,
        new_item_fingerprint=updated_item.item_fingerprint,
        transition_evidence_fingerprint=transition_evidence_fingerprint,
    )

    new_items = [it if it.knowledge_id != knowledge_id else updated_item for it in state.items]
    new_state = KnowledgeRegistryState.create(
        items=new_items,
        events=(*state.events, event),
    )
    return new_state, event


def serialize_knowledge_registry(state: KnowledgeRegistryState) -> bytes:
    """Serializes KnowledgeRegistryState into deterministic canonical JSON bytes."""
    if type(state) is not KnowledgeRegistryState:
        raise HarnessValidationError("state must be exact KnowledgeRegistryState")
    encoded = canonical_json_bytes(state.to_dict())
    if len(encoded) > MAX_KNOWLEDGE_SERIALIZED_BYTES:
        raise RepositoryKnowledgeRegistryBoundError(
            f"serialized bytes ({len(encoded)}) exceeds hard limit ({MAX_KNOWLEDGE_SERIALIZED_BYTES})"
        )
    return encoded


def parse_knowledge_registry(data: bytes) -> KnowledgeRegistryState:
    """Strictly parses canonical JSON bytes into a fully validated KnowledgeRegistryState."""
    if not isinstance(data, (bytes, bytearray)):
        raise HarnessValidationError("data must be bytes")
    if len(data) > MAX_KNOWLEDGE_SERIALIZED_BYTES:
        raise RepositoryKnowledgeRegistryBoundError(
            f"input data bytes ({len(data)}) exceeds hard limit ({MAX_KNOWLEDGE_SERIALIZED_BYTES})"
        )

    try:
        raw_json = json.loads(data.decode("utf-8"))
    except Exception as exc:
        raise HarnessValidationError(f"malformed JSON in knowledge registry: {exc}") from exc

    if type(raw_json) is not dict:
        raise HarnessValidationError("knowledge registry root JSON must be a dict")

    # Strict canonical bytes check: parsed dict reserialized must equal input data
    canonical_bytes = canonical_json_bytes(raw_json)
    if canonical_bytes != bytes(data):
        raise HarnessValidationError("serialized bytes are non-canonical or malformed")

    expected_keys = {"events", "items", "policy_version", "registry_fingerprint", "schema_version"}
    if set(raw_json.keys()) != expected_keys:
        raise HarnessValidationError(f"unexpected keys in registry JSON: {set(raw_json.keys()) ^ expected_keys}")

    items_list: list[KnowledgeItem] = []
    for raw_item in raw_json["items"]:
        if type(raw_item) is not dict:
            raise HarnessValidationError("KnowledgeItem must be a dict")
        item_keys = {
            "authority_class",
            "item_fingerprint",
            "kind",
            "knowledge_id",
            "lifecycle_state",
            "metadata",
            "provenance_refs",
            "summary",
            "title",
            "validation_state",
        }
        if set(raw_item.keys()) != item_keys:
            raise HarnessValidationError("invalid keys in KnowledgeItem")

        try:
            kind_val = KnowledgeKind(raw_item["kind"])
            val_state = KnowledgeValidationState(raw_item["validation_state"])
            life_state = KnowledgeLifecycleState(raw_item["lifecycle_state"])
            auth_class = KnowledgeAuthorityClass(raw_item["authority_class"])
        except ValueError as exc:
            raise HarnessValidationError(f"unknown enum value in KnowledgeItem: {exc}") from exc

        prov_list: list[KnowledgeProvenanceRef] = []
        for raw_prov in raw_item["provenance_refs"]:
            if type(raw_prov) is not dict:
                raise HarnessValidationError("KnowledgeProvenanceRef must be a dict")
            prov_keys = {
                "provenance_fingerprint",
                "provenance_kind",
                "source_blob_sha",
                "source_evidence_fingerprint",
                "source_path",
                "source_snapshot_sha",
            }
            if set(raw_prov.keys()) != prov_keys:
                raise HarnessValidationError("invalid keys in KnowledgeProvenanceRef")
            try:
                p_kind = KnowledgeProvenanceKind(raw_prov["provenance_kind"])
            except ValueError as exc:
                raise HarnessValidationError(f"unknown provenance_kind: {exc}") from exc

            prov_obj = KnowledgeProvenanceRef(
                source_path=raw_prov["source_path"],
                source_blob_sha=raw_prov["source_blob_sha"],
                provenance_kind=p_kind,
                source_evidence_fingerprint=raw_prov["source_evidence_fingerprint"],
                source_snapshot_sha=raw_prov["source_snapshot_sha"],
                provenance_fingerprint=raw_prov["provenance_fingerprint"],
            )
            prov_list.append(prov_obj)

        item_obj = KnowledgeItem(
            knowledge_id=raw_item["knowledge_id"],
            kind=kind_val,
            title=raw_item["title"],
            summary=raw_item["summary"],
            provenance_refs=tuple(prov_list),
            validation_state=val_state,
            lifecycle_state=life_state,
            authority_class=auth_class,
            metadata=raw_item["metadata"],
            item_fingerprint=raw_item["item_fingerprint"],
        )
        items_list.append(item_obj)

    events_list: list[KnowledgeRegistryEvent] = []
    for raw_event in raw_json["events"]:
        if type(raw_event) is not dict:
            raise HarnessValidationError("KnowledgeRegistryEvent must be a dict")
        event_keys = {
            "event_fingerprint",
            "event_seq",
            "knowledge_id",
            "new_item_fingerprint",
            "operation",
            "prior_item_fingerprint",
            "prior_registry_fingerprint",
            "transition_evidence_fingerprint",
        }
        if set(raw_event.keys()) != event_keys:
            raise HarnessValidationError("invalid keys in KnowledgeRegistryEvent")

        try:
            op_val = KnowledgeRegistryOperation(raw_event["operation"])
        except ValueError as exc:
            raise HarnessValidationError(f"unknown operation: {exc}") from exc

        event_obj = KnowledgeRegistryEvent(
            event_seq=raw_event["event_seq"],
            operation=op_val,
            knowledge_id=raw_event["knowledge_id"],
            prior_registry_fingerprint=raw_event["prior_registry_fingerprint"],
            prior_item_fingerprint=raw_event["prior_item_fingerprint"],
            new_item_fingerprint=raw_event["new_item_fingerprint"],
            transition_evidence_fingerprint=raw_event["transition_evidence_fingerprint"],
            event_fingerprint=raw_event["event_fingerprint"],
        )
        events_list.append(event_obj)

    return KnowledgeRegistryState(
        schema_version=raw_json["schema_version"],
        policy_version=raw_json["policy_version"],
        items=tuple(items_list),
        events=tuple(events_list),
        registry_fingerprint=raw_json["registry_fingerprint"],
    )


__all__ = [
    "H4_KNOWLEDGE_REGISTRY_POLICY_VERSION",
    "H4_KNOWLEDGE_REGISTRY_SCHEMA_VERSION",
    "KnowledgeAuthorityClass",
    "KnowledgeItem",
    "KnowledgeKind",
    "KnowledgeLifecycleState",
    "KnowledgeProvenanceKind",
    "KnowledgeProvenanceRef",
    "KnowledgeRegistryEvent",
    "KnowledgeRegistryOperation",
    "KnowledgeRegistryState",
    "KnowledgeValidationState",
    "MAX_KNOWLEDGE_FINGERPRINT_PAYLOAD_BYTES",
    "MAX_KNOWLEDGE_ID_LENGTH",
    "MAX_KNOWLEDGE_ITEMS",
    "MAX_KNOWLEDGE_METADATA_KEY_LENGTH",
    "MAX_KNOWLEDGE_METADATA_PAIRS",
    "MAX_KNOWLEDGE_METADATA_TOTAL_BYTES",
    "MAX_KNOWLEDGE_METADATA_VALUE_LENGTH",
    "MAX_KNOWLEDGE_PROVENANCE_REFS_PER_ITEM",
    "MAX_KNOWLEDGE_REGISTRY_EVENTS",
    "MAX_KNOWLEDGE_SERIALIZED_BYTES",
    "MAX_KNOWLEDGE_SOURCE_PATH_LENGTH",
    "MAX_KNOWLEDGE_SUMMARY_LENGTH",
    "MAX_KNOWLEDGE_TITLE_LENGTH",
    "RepositoryKnowledgeRegistryBoundError",
    "RepositoryKnowledgeRegistryError",
    "RepositoryKnowledgeRegistryStateError",
    "VALID_LIFECYCLE_TRANSITIONS",
    "VALID_VALIDATION_TRANSITIONS",
    "amend_knowledge_metadata",
    "create_empty_knowledge_registry",
    "parse_knowledge_registry",
    "register_knowledge_item",
    "serialize_knowledge_registry",
    "set_knowledge_lifecycle_state",
    "set_knowledge_validation_state",
]
