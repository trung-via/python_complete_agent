# DIAGNOSIS — M3B Stable-Boundary Brain Failover Invariants

STATUS: DIAGNOSED

## CAUSE
A multi-agent continuity system requires cross-brain failover when a primary advisory Brain encounters a non-success boundary (e.g. rate-limit, timeout, or controlled handoff). Without content-addressed state anchoring and semantic request equality, replacement Brains could operate on stale context, drift in objectives, or create split-brain duplicate outputs.

## EVIDENCE
1. Canonical state fingerprint (`3ad86f80e693d4cc8fbab8dee502a0de1c60b581216c7ea2bbfa233b88cdb9db`) locks the repository main SHA, task definition blob, and governing ADR decision blobs before failover validation.
2. BrainRequest semantic equality guarantees that operation (DIAGNOSIS), objective, ordered context references, and output contract (`.ai/diagnosis/TASK-027-M3B-DIAGNOSIS.md`) remain byte-identical between source and replacement.
3. A source result with SUCCESS blocks duplicate competing failovers fail-closed; failover is permitted only at non-success boundaries.
4. Replacement Brain reconstructs its request and context without prior chat transcript, session cookies, prompt history, or hidden reasoning / chain-of-thought.
5. Capability gate validation confirms that the replacement Brain surface explicitly declares support for the requested DIAGNOSIS operation before execution.
6. Brain remains strictly advisory; human authority for RUN, FIX, and MERGE gates remains unchanged with zero execution authority granted to models.

## FIX
1. Validate source result status is non-SUCCESS to eliminate duplicate competing artifacts.
2. Verify exact equality of state fingerprint, task ID, operation, objective, context refs, and output contract between source and replacement requests.
3. Validate replacement Brain capability declarations against the requested operation.
4. Bind replacement SUCCESS result to the exact Git blob SHA of the persisted diagnosis artifact.

## TESTS
- `test_valid_replacement_request_construction_and_field_preservation`
- `test_same_brain_pseudo_failover_rejected`
- `test_context_refs_content_anchoring_to_state_snapshot`
- `test_semantic_drift_rejection_in_failover_validation`
- `test_replacement_capability_gate_is_mandatory`
- `test_source_result_and_duplicate_output_blocking`
- `test_diagnosis_semantic_anchors_validation`
- `test_m3b_attestation_validation`

## RISKS
- State drift if repository changes are unstaged or uncommitted during handoff.
- Loss of idempotency if a SUCCESS source result is allowed to fail over.
- Ambiguity if raw chat transcripts or hidden chain-of-thought are leaked into context packs instead of clean content-addressed references.
