from __future__ import annotations

import copy
from dataclasses import replace
import json
from pathlib import Path
import subprocess

import pytest

import src.aios_engineering.harness.knowledge_registry as kr_module
from src.aios_engineering.harness import (
    H4_KNOWLEDGE_REGISTRY_POLICY_VERSION,
    H4_KNOWLEDGE_REGISTRY_SCHEMA_VERSION,
    HarnessFingerprintError,
    HarnessValidationError,
    KnowledgeAuthorityClass,
    KnowledgeItem,
    KnowledgeKind,
    KnowledgeLifecycleState,
    KnowledgeProvenanceKind,
    KnowledgeProvenanceRef,
    KnowledgeRegistryEvent,
    KnowledgeRegistryOperation,
    KnowledgeRegistryState,
    KnowledgeValidationState,
    MAX_KNOWLEDGE_FINGERPRINT_PAYLOAD_BYTES,
    MAX_KNOWLEDGE_ID_LENGTH,
    MAX_KNOWLEDGE_ITEMS,
    MAX_KNOWLEDGE_METADATA_KEY_LENGTH,
    MAX_KNOWLEDGE_METADATA_PAIRS,
    MAX_KNOWLEDGE_METADATA_TOTAL_BYTES,
    MAX_KNOWLEDGE_METADATA_VALUE_LENGTH,
    MAX_KNOWLEDGE_PROVENANCE_REFS_PER_ITEM,
    MAX_KNOWLEDGE_REGISTRY_EVENTS,
    MAX_KNOWLEDGE_SERIALIZED_BYTES,
    MAX_KNOWLEDGE_SOURCE_PATH_LENGTH,
    MAX_KNOWLEDGE_SUMMARY_LENGTH,
    MAX_KNOWLEDGE_TITLE_LENGTH,
    RepositoryKnowledgeRegistryBoundError,
    RepositoryKnowledgeRegistryError,
    RepositoryKnowledgeRegistryStateError,
    VALID_LIFECYCLE_TRANSITIONS,
    VALID_VALIDATION_TRANSITIONS,
    amend_knowledge_metadata,
    create_empty_knowledge_registry,
    parse_knowledge_registry,
    register_knowledge_item,
    serialize_knowledge_registry,
    set_knowledge_lifecycle_state,
    set_knowledge_validation_state,
)


def _make_provenance(
    *,
    source_path: str = ".ai/tasks/TASK-082.md",
    source_blob_sha: str = "1" * 40,
    provenance_kind: KnowledgeProvenanceKind = KnowledgeProvenanceKind.TASK,
    source_evidence_fingerprint: str = "2" * 64,
    source_snapshot_sha: str | None = None,
) -> KnowledgeProvenanceRef:
    return KnowledgeProvenanceRef.create(
        source_path=source_path,
        source_blob_sha=source_blob_sha,
        provenance_kind=provenance_kind,
        source_evidence_fingerprint=source_evidence_fingerprint,
        source_snapshot_sha=source_snapshot_sha,
    )


def _make_item(
    *,
    knowledge_id: str = "finding:task-082:b1",
    kind: KnowledgeKind = KnowledgeKind.FINDING,
    title: str = "Finding title",
    summary: str = "Finding summary",
    provenance_refs: tuple[KnowledgeProvenanceRef, ...] | None = None,
    validation_state: KnowledgeValidationState = KnowledgeValidationState.UNVALIDATED,
    lifecycle_state: KnowledgeLifecycleState = KnowledgeLifecycleState.PROPOSED,
    authority_class: KnowledgeAuthorityClass = KnowledgeAuthorityClass.ADVISORY,
    metadata: dict[str, str] | None = None,
) -> KnowledgeItem:
    prov = provenance_refs if provenance_refs is not None else (_make_provenance(),)
    return KnowledgeItem.create(
        knowledge_id=knowledge_id,
        kind=kind,
        title=title,
        summary=summary,
        provenance_refs=prov,
        validation_state=validation_state,
        lifecycle_state=lifecycle_state,
        authority_class=authority_class,
        metadata=metadata or {},
    )


def test_h4_policy_schema_identity():
    assert H4_KNOWLEDGE_REGISTRY_POLICY_VERSION == "h4-knowledge-registry-v1"
    assert H4_KNOWLEDGE_REGISTRY_SCHEMA_VERSION == "1"

    empty_registry = create_empty_knowledge_registry()
    assert empty_registry.policy_version == H4_KNOWLEDGE_REGISTRY_POLICY_VERSION
    assert empty_registry.schema_version == H4_KNOWLEDGE_REGISTRY_SCHEMA_VERSION
    assert empty_registry.items == ()
    assert empty_registry.events == ()
    assert len(empty_registry.registry_fingerprint) == 64


def test_knowledge_kind_exact_four():
    assert len(KnowledgeKind) == 4
    expected = {"INVARIANT", "FINDING", "LESSON", "SKILL"}
    assert {k.value for k in KnowledgeKind} == expected


def test_immutable_item_and_registry():
    item = _make_item()
    with pytest.raises((AttributeError, TypeError)):
        item.title = "new title"  # type: ignore[misc]

    reg = create_empty_knowledge_registry()
    with pytest.raises((AttributeError, TypeError)):
        reg.items = (item,)  # type: ignore[misc]


def test_exact_provenance_required_and_tamper_rejected():
    # 1. Empty provenance refs rejected
    with pytest.raises(HarnessValidationError, match="must not be empty"):
        KnowledgeItem.create(
            knowledge_id="test:1",
            kind=KnowledgeKind.FINDING,
            title="T",
            summary="S",
            provenance_refs=(),
        )

    # 2. Tampered provenance fingerprint rejected
    prov = _make_provenance()
    with pytest.raises(HarnessFingerprintError):
        KnowledgeProvenanceRef(
            source_path=prov.source_path,
            source_blob_sha=prov.source_blob_sha,
            provenance_kind=prov.provenance_kind,
            source_evidence_fingerprint=prov.source_evidence_fingerprint,
            source_snapshot_sha=prov.source_snapshot_sha,
            provenance_fingerprint="0" * 64,
        )


def test_duplicate_provenance_and_knowledge_id_rejected():
    prov = _make_provenance()

    # Factory rejects duplicate provenance
    with pytest.raises(HarnessValidationError, match="duplicate provenance ref"):
        KnowledgeItem.create(
            knowledge_id="test:dup_prov",
            kind=KnowledgeKind.FINDING,
            title="T",
            summary="S",
            provenance_refs=(prov, prov),
        )

    # Registry rejects duplicate knowledge_id in factory
    item1 = _make_item(knowledge_id="id:1")
    with pytest.raises(HarnessValidationError, match="duplicate knowledge_id"):
        KnowledgeRegistryState.create(items=(item1, item1))

    # Registry rejects duplicate registration via register_knowledge_item
    reg = create_empty_knowledge_registry()
    reg1, _ = register_knowledge_item(reg, item1, "0" * 64)
    with pytest.raises(RepositoryKnowledgeRegistryStateError, match="knowledge_id already exists"):
        register_knowledge_item(reg1, item1, "0" * 64)


def test_validation_state_closed_and_forward_transitions():
    assert len(KnowledgeValidationState) == 3
    assert {s.value for s in KnowledgeValidationState} == {"UNVALIDATED", "EVIDENCE_BACKED", "HUMAN_APPROVED"}

    reg = create_empty_knowledge_registry()
    item = _make_item(validation_state=KnowledgeValidationState.UNVALIDATED)
    reg, ev = register_knowledge_item(reg, item, "0" * 64)
    item_v1 = reg.get_item(item.knowledge_id)
    assert item_v1 is not None

    # Forward: UNVALIDATED -> EVIDENCE_BACKED
    reg2, ev2 = set_knowledge_validation_state(
        reg,
        item.knowledge_id,
        KnowledgeValidationState.EVIDENCE_BACKED,
        item_v1.item_fingerprint,
        reg.registry_fingerprint,
        "1" * 64,
    )
    item_v2 = reg2.get_item(item.knowledge_id)
    assert item_v2 is not None
    assert item_v2.validation_state is KnowledgeValidationState.EVIDENCE_BACKED

    # Forward: EVIDENCE_BACKED -> HUMAN_APPROVED
    reg3, ev3 = set_knowledge_validation_state(
        reg2,
        item.knowledge_id,
        KnowledgeValidationState.HUMAN_APPROVED,
        item_v2.item_fingerprint,
        reg2.registry_fingerprint,
        "2" * 64,
    )
    item_v3 = reg3.get_item(item.knowledge_id)
    assert item_v3 is not None
    assert item_v3.validation_state is KnowledgeValidationState.HUMAN_APPROVED


def test_validation_stale_fingerprints_and_unsupported_transitions():
    reg = create_empty_knowledge_registry()
    item = _make_item(validation_state=KnowledgeValidationState.UNVALIDATED)
    reg, _ = register_knowledge_item(reg, item, "0" * 64)
    cur_item = reg.get_item(item.knowledge_id)
    assert cur_item is not None

    # Stale registry fingerprint
    with pytest.raises(RepositoryKnowledgeRegistryStateError, match="registry fingerprint mismatch"):
        set_knowledge_validation_state(
            reg,
            item.knowledge_id,
            KnowledgeValidationState.EVIDENCE_BACKED,
            cur_item.item_fingerprint,
            "f" * 64,
            "1" * 64,
        )

    # Stale item fingerprint
    with pytest.raises(RepositoryKnowledgeRegistryStateError, match="item fingerprint mismatch"):
        set_knowledge_validation_state(
            reg,
            item.knowledge_id,
            KnowledgeValidationState.EVIDENCE_BACKED,
            "f" * 64,
            reg.registry_fingerprint,
            "1" * 64,
        )

    # Unsupported same-state transition
    with pytest.raises(RepositoryKnowledgeRegistryStateError, match="invalid validation transition"):
        set_knowledge_validation_state(
            reg,
            item.knowledge_id,
            KnowledgeValidationState.UNVALIDATED,
            cur_item.item_fingerprint,
            reg.registry_fingerprint,
            "1" * 64,
        )

    # Unsupported downgrade transition
    reg_approved, _ = set_knowledge_validation_state(
        reg,
        item.knowledge_id,
        KnowledgeValidationState.HUMAN_APPROVED,
        cur_item.item_fingerprint,
        reg.registry_fingerprint,
        "1" * 64,
    )
    app_item = reg_approved.get_item(item.knowledge_id)
    assert app_item is not None
    with pytest.raises(RepositoryKnowledgeRegistryStateError, match="invalid validation transition"):
        set_knowledge_validation_state(
            reg_approved,
            item.knowledge_id,
            KnowledgeValidationState.EVIDENCE_BACKED,
            app_item.item_fingerprint,
            reg_approved.registry_fingerprint,
            "2" * 64,
        )


def test_lifecycle_state_closed_and_forward_transitions():
    assert len(KnowledgeLifecycleState) == 3
    assert {s.value for s in KnowledgeLifecycleState} == {"PROPOSED", "ACTIVE", "RETIRED"}

    reg = create_empty_knowledge_registry()
    item = _make_item(lifecycle_state=KnowledgeLifecycleState.PROPOSED)
    reg, _ = register_knowledge_item(reg, item, "0" * 64)
    item_v1 = reg.get_item(item.knowledge_id)
    assert item_v1 is not None

    # Forward: PROPOSED -> ACTIVE
    reg2, ev2 = set_knowledge_lifecycle_state(
        reg,
        item.knowledge_id,
        KnowledgeLifecycleState.ACTIVE,
        item_v1.item_fingerprint,
        reg.registry_fingerprint,
        "1" * 64,
    )
    item_v2 = reg2.get_item(item.knowledge_id)
    assert item_v2 is not None
    assert item_v2.lifecycle_state is KnowledgeLifecycleState.ACTIVE

    # Forward: ACTIVE -> RETIRED
    reg3, ev3 = set_knowledge_lifecycle_state(
        reg2,
        item.knowledge_id,
        KnowledgeLifecycleState.RETIRED,
        item_v2.item_fingerprint,
        reg2.registry_fingerprint,
        "2" * 64,
    )
    item_v3 = reg3.get_item(item.knowledge_id)
    assert item_v3 is not None
    assert item_v3.lifecycle_state is KnowledgeLifecycleState.RETIRED

    # Prove no physical deletion: item remains in registry as RETIRED
    assert item.knowledge_id in [it.knowledge_id for it in reg3.items]


def test_lifecycle_unsupported_transitions_and_stale_fingerprint():
    reg = create_empty_knowledge_registry()
    item = _make_item(lifecycle_state=KnowledgeLifecycleState.PROPOSED)
    reg, _ = register_knowledge_item(reg, item, "0" * 64)
    cur_item = reg.get_item(item.knowledge_id)
    assert cur_item is not None

    # Stale registry fingerprint
    with pytest.raises(RepositoryKnowledgeRegistryStateError, match="registry fingerprint mismatch"):
        set_knowledge_lifecycle_state(
            reg,
            item.knowledge_id,
            KnowledgeLifecycleState.ACTIVE,
            cur_item.item_fingerprint,
            "f" * 64,
            "1" * 64,
        )

    # Same-state transition
    with pytest.raises(RepositoryKnowledgeRegistryStateError, match="invalid lifecycle transition"):
        set_knowledge_lifecycle_state(
            reg,
            item.knowledge_id,
            KnowledgeLifecycleState.PROPOSED,
            cur_item.item_fingerprint,
            reg.registry_fingerprint,
            "1" * 64,
        )

    # Retire item
    reg_ret, _ = set_knowledge_lifecycle_state(
        reg,
        item.knowledge_id,
        KnowledgeLifecycleState.RETIRED,
        cur_item.item_fingerprint,
        reg.registry_fingerprint,
        "1" * 64,
    )
    ret_item = reg_ret.get_item(item.knowledge_id)
    assert ret_item is not None

    # Resurrection / backwards: RETIRED -> ACTIVE fails closed
    with pytest.raises(RepositoryKnowledgeRegistryStateError, match="invalid lifecycle transition"):
        set_knowledge_lifecycle_state(
            reg_ret,
            item.knowledge_id,
            KnowledgeLifecycleState.ACTIVE,
            ret_item.item_fingerprint,
            reg_ret.registry_fingerprint,
            "2" * 64,
        )


def test_finding_lesson_skill_advisory_only():
    prov = _make_provenance()
    for non_invariant_kind in (KnowledgeKind.FINDING, KnowledgeKind.LESSON, KnowledgeKind.SKILL):
        # ADVISORY passes
        item = _make_item(kind=non_invariant_kind, authority_class=KnowledgeAuthorityClass.ADVISORY)
        assert item.authority_class is KnowledgeAuthorityClass.ADVISORY

        # CANONICAL_INVARIANT_REFERENCE fails closed
        with pytest.raises(HarnessValidationError, match="must strictly have authority_class=ADVISORY"):
            KnowledgeItem.create(
                knowledge_id=f"{non_invariant_kind.value.lower()}:1",
                kind=non_invariant_kind,
                title="T",
                summary="S",
                provenance_refs=(prov,),
                authority_class=KnowledgeAuthorityClass.CANONICAL_INVARIANT_REFERENCE,
                validation_state=KnowledgeValidationState.HUMAN_APPROVED,
            )


def test_invariant_reference_requires_explicit_authority_provenance_and_human_approval():
    auth_prov = _make_provenance(provenance_kind=KnowledgeProvenanceKind.INVARIANT_AUTHORITY)
    task_prov = _make_provenance(provenance_kind=KnowledgeProvenanceKind.TASK)

    # 1. Valid CANONICAL_INVARIANT_REFERENCE with INVARIANT_AUTHORITY provenance & HUMAN_APPROVED
    inv_item = KnowledgeItem.create(
        knowledge_id="invariant:1",
        kind=KnowledgeKind.INVARIANT,
        title="Authoritative invariant",
        summary="Summary of invariant",
        provenance_refs=(auth_prov,),
        authority_class=KnowledgeAuthorityClass.CANONICAL_INVARIANT_REFERENCE,
        validation_state=KnowledgeValidationState.HUMAN_APPROVED,
    )
    assert inv_item.authority_class is KnowledgeAuthorityClass.CANONICAL_INVARIANT_REFERENCE

    # 2. Rejection if validation_state is not HUMAN_APPROVED
    with pytest.raises(HarnessValidationError, match="requires validation_state=HUMAN_APPROVED"):
        KnowledgeItem.create(
            knowledge_id="invariant:2",
            kind=KnowledgeKind.INVARIANT,
            title="Invariant",
            summary="Summary",
            provenance_refs=(auth_prov,),
            authority_class=KnowledgeAuthorityClass.CANONICAL_INVARIANT_REFERENCE,
            validation_state=KnowledgeValidationState.UNVALIDATED,
        )

    # 3. Rejection if missing authoritative provenance
    with pytest.raises(HarnessValidationError, match="requires explicit INVARIANT_AUTHORITY or DECISION"):
        KnowledgeItem.create(
            knowledge_id="invariant:3",
            kind=KnowledgeKind.INVARIANT,
            title="Invariant",
            summary="Summary",
            provenance_refs=(task_prov,),
            authority_class=KnowledgeAuthorityClass.CANONICAL_INVARIANT_REFERENCE,
            validation_state=KnowledgeValidationState.HUMAN_APPROVED,
        )


def test_amend_knowledge_metadata_audit():
    reg = create_empty_knowledge_registry()
    item = _make_item(metadata={"domain": "harness"})
    reg, _ = register_knowledge_item(reg, item, "0" * 64)
    cur_item = reg.get_item(item.knowledge_id)
    assert cur_item is not None

    # Amend metadata
    new_meta = {"domain": "harness", "layer": "h4"}
    reg2, ev = amend_knowledge_metadata(
        reg,
        item.knowledge_id,
        new_meta,
        cur_item.item_fingerprint,
        reg.registry_fingerprint,
        "1" * 64,
    )
    assert ev.operation is KnowledgeRegistryOperation.AMEND_METADATA
    updated_item = reg2.get_item(item.knowledge_id)
    assert updated_item is not None
    assert updated_item.metadata == {"domain": "harness", "layer": "h4"}

    # Core identity and state must not be modified by amend metadata
    assert updated_item.knowledge_id == cur_item.knowledge_id
    assert updated_item.kind == cur_item.kind
    assert updated_item.validation_state == cur_item.validation_state
    assert updated_item.lifecycle_state == cur_item.lifecycle_state
    assert updated_item.authority_class == cur_item.authority_class

    # Same-metadata update fails closed
    with pytest.raises(RepositoryKnowledgeRegistryStateError, match="amend_knowledge_metadata requires modifying"):
        amend_knowledge_metadata(
            reg2,
            item.knowledge_id,
            new_meta,
            updated_item.item_fingerprint,
            reg2.registry_fingerprint,
            "2" * 64,
        )


def test_no_kind_promotion_no_auto_gardening():
    # Verify module has no promotion operations or gardening functions
    assert not hasattr(kr_module, "promote_kind")
    assert not hasattr(kr_module, "finding_to_lesson")
    assert not hasattr(kr_module, "lesson_to_skill")
    assert not hasattr(kr_module, "auto_promote")
    assert not hasattr(kr_module, "garden_knowledge")
    assert not hasattr(kr_module, "merge_knowledge")
    assert not hasattr(kr_module, "infer_confidence")


def test_canonical_ordering_and_order_independence():
    prov1 = _make_provenance(source_path="src/b.py")
    prov2 = _make_provenance(source_path="src/a.py")

    # Provenance list permutation produces identical canonical item
    item_p1 = KnowledgeItem.create(
        knowledge_id="item:1",
        kind=KnowledgeKind.FINDING,
        title="T",
        summary="S",
        provenance_refs=(prov1, prov2),
    )
    item_p2 = KnowledgeItem.create(
        knowledge_id="item:1",
        kind=KnowledgeKind.FINDING,
        title="T",
        summary="S",
        provenance_refs=(prov2, prov1),
    )
    assert item_p1.provenance_refs == item_p2.provenance_refs
    assert item_p1.item_fingerprint == item_p2.item_fingerprint

    # Item list permutation in registry produces identical canonical state
    item_a = _make_item(knowledge_id="a:1")
    item_b = _make_item(knowledge_id="b:1")
    reg_ab = KnowledgeRegistryState.create(items=(item_a, item_b))
    reg_ba = KnowledgeRegistryState.create(items=(item_b, item_a))
    assert reg_ab.items == reg_ba.items
    assert reg_ab.registry_fingerprint == reg_ba.registry_fingerprint


def test_canonical_serialize_and_parse_roundtrip():
    reg = create_empty_knowledge_registry()
    item1 = _make_item(knowledge_id="item:1", metadata={"tag": "alpha"})
    item2 = _make_item(knowledge_id="item:2", kind=KnowledgeKind.LESSON)
    reg, _ = register_knowledge_item(reg, item1, "0" * 64)
    reg, _ = register_knowledge_item(reg, item2, "1" * 64)
    reg, _ = set_knowledge_validation_state(
        reg,
        "item:1",
        KnowledgeValidationState.EVIDENCE_BACKED,
        reg.get_item("item:1").item_fingerprint,  # type: ignore[union-attr]
        reg.registry_fingerprint,
        "2" * 64,
    )

    serialized = serialize_knowledge_registry(reg)
    assert isinstance(serialized, bytes)

    parsed = parse_knowledge_registry(serialized)
    assert parsed.registry_fingerprint == reg.registry_fingerprint
    assert len(parsed.items) == len(reg.items)
    assert len(parsed.events) == len(reg.events)
    assert parsed.items == reg.items
    assert parsed.events == reg.events

    # Reserializing parsed state yields identical bytes
    assert serialize_knowledge_registry(parsed) == serialized


def test_parse_rejects_malformed_noncanonical_or_tampered_bytes():
    reg = create_empty_knowledge_registry()
    item = _make_item(knowledge_id="item:1")
    reg, _ = register_knowledge_item(reg, item, "0" * 64)
    valid_bytes = serialize_knowledge_registry(reg)

    # 1. Non-canonical JSON (e.g. added whitespace or different indentation)
    raw_dict = json.loads(valid_bytes.decode("utf-8"))
    non_canonical_bytes = json.dumps(raw_dict, indent=2).encode("utf-8")
    with pytest.raises(HarnessValidationError, match="non-canonical or malformed"):
        parse_knowledge_registry(non_canonical_bytes)

    # 2. Unknown keys in root dict
    bad_dict = copy.deepcopy(raw_dict)
    bad_dict["unknown_key"] = "bad"
    with pytest.raises(HarnessValidationError, match="unexpected keys"):
        parse_knowledge_registry(json.dumps(bad_dict, separators=(",", ":"), sort_keys=True).encode("utf-8"))

    # 3. Tampered item fingerprint
    bad_item_dict = copy.deepcopy(raw_dict)
    bad_item_dict["items"][0]["item_fingerprint"] = "0" * 64
    with pytest.raises(HarnessFingerprintError, match="KnowledgeItem fingerprint mismatch"):
        parse_knowledge_registry(json.dumps(bad_item_dict, separators=(",", ":"), sort_keys=True).encode("utf-8"))

    # 4. Tampered registry fingerprint
    bad_reg_dict = copy.deepcopy(raw_dict)
    bad_reg_dict["registry_fingerprint"] = "0" * 64
    with pytest.raises(HarnessFingerprintError, match="KnowledgeRegistryState fingerprint mismatch"):
        parse_knowledge_registry(json.dumps(bad_reg_dict, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def test_all_hard_bounds_and_bool_as_int_rejection(monkeypatch: pytest.MonkeyPatch):
    prov = _make_provenance()
    item = _make_item()
    reg = create_empty_knowledge_registry()
    reg, ev = register_knowledge_item(reg, item, "0" * 64)

    # --- 1. Bool as int rejection on bounded integers ---
    with pytest.raises(HarnessValidationError, match="event_seq must be an exact integer, not bool"):
        replace(ev, event_seq=True)  # type: ignore[arg-type]

    # --- 2. String length bounds ---
    # Knowledge ID length
    with pytest.raises(RepositoryKnowledgeRegistryBoundError, match="knowledge_id length .* exceeds hard limit"):
        _make_item(knowledge_id="a" * (MAX_KNOWLEDGE_ID_LENGTH + 1))

    # Title length
    with pytest.raises(RepositoryKnowledgeRegistryBoundError, match="title length .* exceeds hard limit"):
        _make_item(title="t" * (MAX_KNOWLEDGE_TITLE_LENGTH + 1))

    # Summary length
    with pytest.raises(RepositoryKnowledgeRegistryBoundError, match="summary length .* exceeds hard limit"):
        _make_item(summary="s" * (MAX_KNOWLEDGE_SUMMARY_LENGTH + 1))

    # Source path length
    with pytest.raises(RepositoryKnowledgeRegistryBoundError, match="source_path length .* exceeds hard limit"):
        _make_provenance(source_path="a/" * 260 + "a.py")

    # --- 3. Metadata bounds ---
    # Metadata key length
    with pytest.raises(RepositoryKnowledgeRegistryBoundError, match="metadata key length .* exceeds hard limit"):
        _make_item(metadata={"k" * (MAX_KNOWLEDGE_METADATA_KEY_LENGTH + 1): "v"})

    # Metadata value length
    with pytest.raises(RepositoryKnowledgeRegistryBoundError, match="metadata value length .* exceeds hard limit"):
        _make_item(metadata={"k": "v" * (MAX_KNOWLEDGE_METADATA_VALUE_LENGTH + 1)})

    # Metadata pairs count
    big_meta = {f"k{i}": "v" for i in range(MAX_KNOWLEDGE_METADATA_PAIRS + 1)}
    with pytest.raises(RepositoryKnowledgeRegistryBoundError, match="metadata pairs count .* exceeds hard limit"):
        _make_item(metadata=big_meta)

    # --- 4. Isolated bound tests using monkeypatch.context() ---
    # A. MAX_KNOWLEDGE_ITEMS
    with monkeypatch.context() as m:
        m.setattr(kr_module, "MAX_KNOWLEDGE_ITEMS", 1)
        item2 = _make_item(knowledge_id="id:2")
        with pytest.raises(RepositoryKnowledgeRegistryBoundError, match="items count .* exceeds hard limit"):
            replace(reg, items=(item, item2))

    # B. MAX_KNOWLEDGE_PROVENANCE_REFS_PER_ITEM
    with monkeypatch.context() as m:
        m.setattr(kr_module, "MAX_KNOWLEDGE_PROVENANCE_REFS_PER_ITEM", 1)
        prov2 = _make_provenance(source_path="src/other.py")
        with pytest.raises(RepositoryKnowledgeRegistryBoundError, match="provenance_refs count .* exceeds hard limit"):
            KnowledgeItem.create(
                knowledge_id="item:bound_prov",
                kind=KnowledgeKind.FINDING,
                title="T",
                summary="S",
                provenance_refs=(prov, prov2),
            )

    # C. MAX_KNOWLEDGE_REGISTRY_EVENTS
    with monkeypatch.context() as m:
        m.setattr(kr_module, "MAX_KNOWLEDGE_REGISTRY_EVENTS", 1)
        ev2 = KnowledgeRegistryEvent.create(
            event_seq=1,
            operation=KnowledgeRegistryOperation.REGISTER,
            knowledge_id="item:2",
            prior_registry_fingerprint=reg.registry_fingerprint,
            prior_item_fingerprint=None,
            new_item_fingerprint="1" * 64,
            transition_evidence_fingerprint="0" * 64,
        )
        with pytest.raises(RepositoryKnowledgeRegistryBoundError, match="events count .* exceeds hard limit"):
            replace(reg, events=(ev, ev2))

    # D. MAX_KNOWLEDGE_SERIALIZED_BYTES
    with monkeypatch.context() as m:
        m.setattr(kr_module, "MAX_KNOWLEDGE_SERIALIZED_BYTES", 10)
        with pytest.raises(RepositoryKnowledgeRegistryBoundError, match="serialized bytes .* exceeds hard limit"):
            serialize_knowledge_registry(reg)

    # E. MAX_KNOWLEDGE_FINGERPRINT_PAYLOAD_BYTES
    with monkeypatch.context() as m:
        m.setattr(kr_module, "MAX_KNOWLEDGE_FINGERPRINT_PAYLOAD_BYTES", 10)
        with pytest.raises(RepositoryKnowledgeRegistryBoundError, match="payload bytes .* exceeds hard limit"):
            kr_module._bounded_fingerprint({"key": "a_long_value_that_exceeds_10_bytes"})


def test_pure_composition_zero_authority_and_no_subprocesses(monkeypatch: pytest.MonkeyPatch):
    # Monkeypatch subprocess.Popen and subprocess.run to forbid calls
    def forbidden(*args: object, **kwargs: object):
        raise AssertionError("No subprocesses allowed in pure H4 operations")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)

    reg = create_empty_knowledge_registry()
    item = _make_item()
    reg, ev = register_knowledge_item(reg, item, "0" * 64)
    assert reg.registry_fingerprint is not None

    # Inspect source code for forbidden concepts
    source = Path(kr_module.__file__).read_text(encoding="utf-8")
    assert "import ast" not in source
    assert "urllib" not in source and "requests" not in source and "http" not in source
    assert "bridge.py" not in source
    assert "promote_kind" not in source
    assert "auto_gardening" not in source


# --- B1 METADATA DEEP IMMUTABILITY REGRESSIONS ---


def test_metadata_direct_mutation_raises_type_error():
    item = KnowledgeItem.create(
        knowledge_id="INVARIANT:001",
        kind=KnowledgeKind.INVARIANT,
        title="Sample Invariant",
        summary="Summary of invariant",
        provenance_refs=[_make_provenance(provenance_kind=KnowledgeProvenanceKind.INVARIANT_AUTHORITY)],
        validation_state=KnowledgeValidationState.HUMAN_APPROVED,
        authority_class=KnowledgeAuthorityClass.CANONICAL_INVARIANT_REFERENCE,
        metadata={"domain": "harness", "owner": "core"},
    )
    assert item.metadata["domain"] == "harness"
    assert item.metadata.get("owner") == "core"

    with pytest.raises(TypeError):
        item.metadata["domain"] = "tampered"

    with pytest.raises(TypeError):
        del item.metadata["owner"]

    with pytest.raises(AttributeError):
        item.metadata.clear()

    with pytest.raises(AttributeError):
        item.metadata.pop("domain")

    with pytest.raises(AttributeError):
        item.metadata.update({"domain": "tampered"})


def test_registry_state_contained_item_metadata_immutable():
    item = KnowledgeItem.create(
        knowledge_id="INVARIANT:001",
        kind=KnowledgeKind.INVARIANT,
        title="Sample Invariant",
        summary="Summary of invariant",
        provenance_refs=[_make_provenance(provenance_kind=KnowledgeProvenanceKind.INVARIANT_AUTHORITY)],
        validation_state=KnowledgeValidationState.HUMAN_APPROVED,
        authority_class=KnowledgeAuthorityClass.CANONICAL_INVARIANT_REFERENCE,
        metadata={"domain": "harness"},
    )
    state, _ = register_knowledge_item(create_empty_knowledge_registry(), item, "a" * 64)

    fetched = state.get_item("INVARIANT:001")
    assert fetched is not None
    with pytest.raises(TypeError):
        fetched.metadata["domain"] = "tampered"

    with pytest.raises(TypeError):
        state.items[0].metadata["domain"] = "tampered"


def test_caller_input_dict_mutation_after_construction():
    input_meta = {"domain": "harness", "layer": "h4"}
    item = KnowledgeItem.create(
        knowledge_id="INVARIANT:001",
        kind=KnowledgeKind.INVARIANT,
        title="Sample Invariant",
        summary="Summary of invariant",
        provenance_refs=[_make_provenance(provenance_kind=KnowledgeProvenanceKind.INVARIANT_AUTHORITY)],
        validation_state=KnowledgeValidationState.HUMAN_APPROVED,
        authority_class=KnowledgeAuthorityClass.CANONICAL_INVARIANT_REFERENCE,
        metadata=input_meta,
    )
    # Mutate caller input dictionary
    input_meta["domain"] = "tampered_caller_dict"
    input_meta["new_key"] = "added_later"

    assert item.metadata["domain"] == "harness"
    assert "new_key" not in item.metadata
    assert item.to_dict()["metadata"]["domain"] == "harness"


def test_failed_mutation_preserves_fingerprints_and_serialization():
    item = KnowledgeItem.create(
        knowledge_id="INVARIANT:001",
        kind=KnowledgeKind.INVARIANT,
        title="Sample Invariant",
        summary="Summary of invariant",
        provenance_refs=[_make_provenance(provenance_kind=KnowledgeProvenanceKind.INVARIANT_AUTHORITY)],
        validation_state=KnowledgeValidationState.HUMAN_APPROVED,
        authority_class=KnowledgeAuthorityClass.CANONICAL_INVARIANT_REFERENCE,
        metadata={"domain": "harness"},
    )
    old_item_fp = item.item_fingerprint

    state, _ = register_knowledge_item(create_empty_knowledge_registry(), item, "a" * 64)
    old_reg_fp = state.registry_fingerprint
    old_serialized = serialize_knowledge_registry(state)

    try:
        item.metadata["domain"] = "tampered"
    except TypeError:
        pass

    assert item.item_fingerprint == old_item_fp
    assert state.registry_fingerprint == old_reg_fp
    assert serialize_knowledge_registry(state) == old_serialized


def test_amend_metadata_remains_only_valid_mutation_path():
    item = KnowledgeItem.create(
        knowledge_id="INVARIANT:001",
        kind=KnowledgeKind.INVARIANT,
        title="Sample Invariant",
        summary="Summary of invariant",
        provenance_refs=[_make_provenance(provenance_kind=KnowledgeProvenanceKind.INVARIANT_AUTHORITY)],
        validation_state=KnowledgeValidationState.HUMAN_APPROVED,
        authority_class=KnowledgeAuthorityClass.CANONICAL_INVARIANT_REFERENCE,
        metadata={"domain": "harness"},
    )
    old_item_fp = item.item_fingerprint
    state, _ = register_knowledge_item(create_empty_knowledge_registry(), item, "a" * 64)
    old_reg_fp = state.registry_fingerprint

    amended_state, event = amend_knowledge_metadata(
        state,
        "INVARIANT:001",
        {"domain": "updated_harness"},
        old_item_fp,
        old_reg_fp,
        "b" * 64,
    )

    assert amended_state.registry_fingerprint != old_reg_fp
    amended_item = amended_state.get_item("INVARIANT:001")
    assert amended_item is not None
    assert amended_item.item_fingerprint != old_item_fp
    assert amended_item.metadata["domain"] == "updated_harness"

    # Original state and item remain completely unchanged
    assert state.registry_fingerprint == old_reg_fp
    assert state.get_item("INVARIANT:001").metadata["domain"] == "harness"
