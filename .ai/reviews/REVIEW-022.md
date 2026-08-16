# REVIEW-022 — TASK-022 M3A Brain Failover Contract & Proof Harness

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `4` — FULL RE-AUDIT after prior approval
- Reviewed branch: `ai/task-022`
- Reviewed branch head: `ef71a89f8a05823e12abd744150ab681aa58f312`
- Last tested implementation SHA reported by RESULT: `bae29799837229e30303e68f46f32a2b8cd62aa6`
- Production failover code SHA lineage remains from `92696e61782839a25aa8c0223e79904090590bfe`; `bae2979...` is test-only and `ef71a89...` is RESULT-only afterward.
- Base main: `4978e426f3445c086c017c07c844943ac841e4de`
- Branch relation at re-audit: ahead `6`, behind `0`; merge-base exact current main.
- Review mode: explicit full audit requested by human. Reloaded full TASK-022, full ADR-016, full `failover.py`, full `test_failover.py`, public exports, relevant M2 BrainRequest/BrainCapability/BrainResult contracts, shared state identity validators, RESULT, and branch compare. This review does not rely on the prior Round-3 approval.
- Test counts below are RESULT evidence from Antigravity; this re-audit did not independently execute the repository test suite.

## Previously Closed Findings

R1-1 mandatory canonical-state fingerprint argument, R1-2 mandatory replacement capability gate, and R1-3 source-result identity matrix remain substantively implemented. The new findings below were exposed only by reviewing the complete identity-validation stack rather than the prior tiny deltas.

## New Blocking Findings

### R4-1 — Same-Brain pseudo-failover can be bypassed with non-canonical whitespace-padded Brain IDs

ADR-016 requires the replacement `brain_id` to differ from the source Brain and requires same-Brain pseudo-failover to fail closed.

The shared `_validate_actor_id()` validator strips surrounding whitespace and returns the stripped value, but `BrainRequest` and `BrainCapability` validate without assigning that returned canonical value. Therefore objects such as `brain_id="brain-a "` can be constructed while retaining the padded raw value.

TASK-022's new failover boundary repeats the same issue:
- `build_replacement_brain_request()` calls `_validate_actor_id(replacement_brain_id, ...)` but ignores its returned canonical value;
- the same-Brain check compares the raw strings;
- `validate_brain_failover_eligibility()` also compares raw `source_request.brain_id`, `replacement_request.brain_id`, and capability identity.

Consequently the logical same Brain can be represented as:

```text
source:      "brain-a"
replacement: "brain-a "
```

and the raw equality check treats them as different identities. A padded replacement capability can match the padded replacement request as well. This violates the central fail-closed same-Brain invariant.

Required fix, scoped to TASK-022 failover boundary:
- require exact canonical actor IDs at all failover inputs and proof fields, or normalize then compare/store canonically;
- safest fail-closed behavior is to reject any source/replacement/capability/proof Brain ID whose raw value differs from the shared validator's canonical return;
- ensure source and replacement are compared by canonical identity, not raw padded text;
- do not widen this task into a broad M2 migration unless strictly necessary.

Required regression tests at minimum:
- source `brain-a`, replacement `brain-a ` => rejected as same/non-canonical Brain;
- source `brain-a `, replacement `brain-a` => rejected;
- padded replacement capability ID cannot make the failover eligible;
- normal `brain-a` -> `brain-b` remains valid.

### R4-2 — BrainFailoverProof parser accepts whitespace-wrapped fingerprints, violating exact SHA-256 proof schema

TASK-022 and ADR-016 require canonical state/request fingerprints to be exact lowercase 64-character SHA-256 hex values.

The new `_validate_hex_fingerprint()` currently performs `fp.strip()` before regex validation and returns the stripped string. `BrainFailoverProof.__post_init__()` calls that validator but does not assign the returned value back to the frozen field.

Therefore direct construction and `BrainFailoverProof.from_dict()/from_json()` can accept values such as:

```text
" <64-lowercase-hex> "
```

while retaining the whitespace-padded value in the proof and its canonical JSON. This is not an exact 64-character fingerprint and breaks the strict/canonical proof-record contract.

The eligibility path happens to reject a padded `expected_state_fingerprint` later because it compares the raw value to `state.fingerprint()`, but the public proof parser/constructor remains permissive for `state_fingerprint`, `source_request_fingerprint`, and `replacement_request_fingerprint`.

Required fix:
- make fingerprint validation exact: surrounding whitespace must be rejected, not silently accepted;
- ensure all three proof fingerprint fields are stored exactly as validated canonical 64-char lowercase hex;
- preserve current malformed/uppercase/length failure behavior.

Required regression tests at minimum:
- whitespace-padded `state_fingerprint` rejected by direct/from_dict or from_json proof parsing;
- whitespace-padded `source_request_fingerprint` rejected;
- whitespace-padded `replacement_request_fingerprint` rejected;
- exact 64-char lowercase values still round-trip deterministically.

### R4-3 — Proof request identity fields inherit the same strip-without-canonicalization ambiguity

`BrainFailoverProof` validates `source_request_id` and `replacement_request_id` through `_validate_request_id()`, which also returns a stripped canonical ID while the proof object retains the raw input.

This does not create the same authority bypass as R4-1, but it violates the strict deterministic audit-record requirement and permits multiple textual representations of one logical request identity.

Required fix:
- at the TASK-022 proof boundary, require request IDs to be exactly canonical (or store the validator's canonical return);
- add focused padded-request-ID rejection/normalization tests consistent with the chosen fail-closed policy.

R4-3 may be implemented together with R4-1 using small local canonical-identity helpers in `failover.py`.

## Full-Audit Positive Evidence

The rest of M3A remains strong:
- replacement request derivation preserves task/schema/operation/objective/context-ref order/output contract;
- caller-supplied state fingerprint and capability are mandatory;
- state fingerprint equality is enforced on the eligibility path;
- source-result task/request/brain/operation identities are checked;
- source SUCCESS blocks duplicate same-operation failover;
- proof serialization is bounded to the Continuity 16 KiB limit and unknown proof fields fail closed;
- no raw transcript/reasoning/model output/secrets/authority fields are part of the proof schema;
- no provider calls, chat UI automation, router/fallback, Git mutation, Bridge mutation, executor authority, or vendor branching exist in `failover.py`;
- `M3_REAL_CROSS_BRAIN_PROOF_COMPLETE: NO` remains correctly stated;
- branch scope remains only RESULT + Continuity exports/failover/tests.

RESULT currently reports Continuity `60 passed`, Bridge `146 passed`, full repository `620 passed`, zero regressions, `LIVE_EXTERNAL_CALLS: 0`, `BRIDGE_V0_4_BEHAVIOR_CHANGED: NO`, and `AUTHORITY_WIDENED: NO`.

## Required Re-Test

After fixing R4-1/R4-2/R4-3, rerun at minimum:

```text
pytest tests/aios_bridge/continuity/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

No live external calls.

## FIX Scope Guidance

Expected fix should normally remain limited to:

```text
src/aios_bridge/continuity/failover.py
tests/aios_bridge/continuity/test_failover.py
.ai/results/RESULT-022.md
```

`src/aios_bridge/continuity/__init__.py` should not need change unless a public symbol genuinely changes.

Do NOT change Bridge lifecycle/authorization semantics, provider layers, routing/fallback, state lifecycle, Executor contracts, or RUN/FIX/MERGE authority.

## Next Review Budget

Although this was a full re-audit, the next review can return to delta-first and inspect only:
- this Round-4 REVIEW;
- new RESULT;
- fix delta for canonical Brain/request identity and exact proof fingerprints;
- new regression tests;
- SHA/branch relation.

## Decision

`CHANGES_REQUIRED`

The previous Round-3 APPROVED verdict is superseded by this human-requested full re-audit. TASK-022 must not be merged until the canonical identity bypass and exact proof-fingerprint parsing gaps are closed and the required suites are green.