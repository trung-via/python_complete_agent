# TASK-091 — FIX Proof Carry-Forward + Invalidation + Delta/Impact Review Integration

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L2 — AIOS BRIDGE LEAN EXECUTION / P1 LEAN REVIEW SLICE C
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: codex
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
IMPLEMENTATION_REFINEMENT_ADR: ADR-064
DECOMPOSITION_ADR: ADR-065
CUTOVER_SLICE: FIX_PROOF_REUSE_DELTA_IMPACT
TASK_090_PREREQUISITE: PASS_MERGED
TASK_087_REMAINS_RESERVED: YES
P1_FORMAL_COMPLETION: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
REVIEW_PIPELINE_MODE: REVIEW_FIRST_CERTIFICATION

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION","roadmap_version":"1.2","roadmap_blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c","roadmap_fingerprint":"89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"P1","capability_id":"P1_UNIFIED_VALIDATION_CAPABILITY_BATCH","requirement_bindings":["P1.R4","P1.R7","P1.R10"],"scope_in":["review-first FIX proof carry-forward based on deterministic subject and dependency fingerprints","known-impact invalidation of affected proofs only","unknown-impact conservative expansion of targeted test and semantic review scope","bounded machine-readable FIX Context Pack derived from authoritative CHANGES_REQUIRED review","deterministic impacted T1 selection at the common publication boundary","Delta plus Impact review evidence for the next semantic review round","accepted-surface protection when exact proof subject and dependencies remain unchanged","legacy tasks and review-first reviews without the Slice C opt-in remain fail-closed compatible","final exact-candidate T2 remains owned by certify-reviewed after semantic acceptance"],"scope_out":["compact RESULT redesign","single-source-of-truth RESULT cutover","persistent Finding Registry orchestration beyond bounded review markers","risk-adaptive live model routing","independent second-review orchestration","review or certification supersession cancellation integration","finding-to-guardrail promotion","stale background-job cancellation daemon","TASK-087 implementation","P1 capability batch integration lane","Python Agent fast-lane pilot","P2 persistent executor sessions","P3 adaptive executor selection","H5-H8 implementation","automatic retry","automatic reroute","paid API calls"]}

## Baseline

```text
MAIN_SHA: 5a609040030a140c0b10be58f4c351dc17cbfb23
TARGET_BRANCH: ai/task-091
TASK_089: PASS_MERGED
TASK_090: PASS_MERGED
REVIEW_FIRST_CERTIFICATION_ON_MAIN: YES
ROADMAP_V1_2: LOCKED_REGISTERED
ADR_065_SLICE_C_AUTHORITY: YES
TASK_087: RESERVED_NOT_EXECUTED
P1_FORMAL_COMPLETION: NO
P2_P3_STATUS: NOT_AUTHORIZED
H5_H8_STATUS: NOT_AUTHORIZED
```

TASK-091 is the first bounded implementation task that MUST itself use the review-first pipeline delivered by TASK-090.

Required TASK-091 delivery lifecycle:

```text
RUN executor
  -> executor T0 / targeted T1 / diff check
  -> publish candidate with AIOS-managed T2 count = 0
  -> ChatGPT semantic review
      -> CHANGES_REQUIRED: FIX candidate, still T2 = 0
      -> SEMANTICALLY_ACCEPTED_PENDING_T2: continue
  -> bridge.py certify-reviewed 91
      -> full canonical T2 exactly once for exact accepted candidate
  -> bridge.py merge-reviewed 91
```

No full canonical T2 is authorized during RUN/FIX candidate publication for TASK-091.

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.md","blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.completions.json","blob_sha":"6b5fb5f99ec17cacca632e3b7a1953131b82c9b7"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"09180853439a383bb459094cb96fa2bd705afdd4"},{"path":".ai/decisions/ADR-065-AIOS-LEAN-REVIEW-PIPELINE-ACTIVATION-BOUNDED-SLICES.md","blob_sha":"947b3ec5b63ddd628838a533822e37499a837a74"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/fix_review.py","src/aios_bridge/review_pipeline.py","src/aios_bridge/executor_context.py","src/aios_bridge/executor_automation.py","tests/aios_bridge/test_fix_review.py","tests/aios_bridge/test_review_pipeline.py","tests/aios_bridge/test_executor_context_pack.py","tests/aios_bridge/test_executor_automation.py","tests/aios_bridge/test_lean_review_integration.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Purpose

Integrate the Slice A proof contracts into the live review-first FIX path so accepted proof is reused until deterministic evidence invalidates it, FIX execution receives only bounded relevant review context, impacted tests are selected from machine-readable impact evidence, and the next semantic review can perform Delta + Impact rather than re-reviewing all previously accepted surfaces.

The optimization rule is:

```text
NO CHANGE
  -> NO RE-PROOF

CHANGE WITH KNOWN IMPACT
  -> INVALIDATE ONLY AFFECTED PROOFS
  -> RUN ONLY REQUIRED IMPACTED T1
  -> RE-REVIEW DELTA + IMPACT ENVELOPE

UNKNOWN IMPACT
  -> FAIL CONSERVATIVE
  -> EXPAND T1 + SEMANTIC REVIEW SCOPE

FINAL CANDIDATE
  -> SEMANTIC ACCEPTANCE
  -> T2 FULL CANONICAL EXACTLY ONCE
```

Tests are never deleted merely because a previous proof passed.

## 1. Closed Slice-C FIX Opt-In

Add a strict top-level marker for future `CHANGES_REQUIRED` reviews:

```text
FIX_REVIEW_MODE: PROOF_REUSE_DELTA_IMPACT
```

Required semantics:

```text
legacy task/review -> existing behavior unchanged
review-first review with marker missing -> existing review-first FIX compatibility behavior
exact single Slice-C marker -> activate proof-reuse FIX path
multiple marker occurrences -> FAIL_CLOSED
unknown mode -> FAIL_CLOSED
marker inside fenced prose/example -> MUST_NOT_ACTIVATE
```

TASK-091 does not need to self-bootstrap Slice C if its own first semantic review requires a FIX. The existing TASK-090 review-first FIX path remains valid until TASK-091 merges. Slice C becomes mandatory for later Lean Review FIX reviews after TASK-091 is merged.

## 2. Machine-Readable FIX Context Pack

For a Slice-C opt-in `CHANGES_REQUIRED` review, require one exact top-level marker:

```text
FIX_CONTEXT_PACK_JSON: <strict bounded JSON object>
```

Implement the pure schema in `src/aios_bridge/fix_review.py` and reuse existing `ProofRecord`, `ProofStatus`, `ImpactConfidence`, and proof carry-forward decisions from `review_pipeline.py` rather than creating parallel permissive enums.

Minimum closed fields:

```text
schema_version
previous_reviewed_head_sha
impact_confidence
open_finding_ids
affected_paths
protected_accepted_paths
required_test_paths
unknown_impact_fallback_test_paths
proof_bindings
```

Each `proof_bindings` item must contain at minimum:

```text
proof_id
subject_paths
dependency_paths
subject_fingerprint
dependency_fingerprint
test_paths
```

All lists are bounded, exact, duplicate-free, canonical repository-relative paths. Test paths must live under `tests/`. Git/admin/runtime namespaces must not be grantable through this pack.

The pack MUST be bound to the exact review header `REVIEWED_TASK_HEAD_SHA`; mismatch fails before lease/executor invocation.

## 3. Deterministic Proof Fingerprints

Add one canonical fingerprint algorithm for a proof's subject and dependencies.

Fingerprint input must be deterministic exact path/blob evidence, conceptually:

```text
sorted canonical path -> exact Git blob identity
```

Requirements:

```text
same path/blob set -> same SHA-256 fingerprint
changed blob -> different fingerprint
added/removed declared path -> different fingerprint
missing/unresolvable declared path -> UNKNOWN impact, never silently VALID
prose/model wording -> MUST NOT participate in fingerprint
```

At FIX handoff, Bridge validates that the review-supplied previous subject/dependency fingerprints match the exact previous reviewed candidate head before Slice-C optimization authority is accepted.

Do not trust reviewer-provided fingerprints without recomputing them from exact Git evidence.

## 4. Proof Carry-Forward / Invalidation Decision

For every proof binding, compare the previous reviewed candidate evidence against the current FIX evidence using the canonical fingerprints.

Required closed decisions:

```text
subject unchanged + dependencies unchanged + previous proof VALID
    -> CARRY_FORWARD_ALLOWED

subject changed OR dependency changed
    -> INVALIDATE

proof NEW/INVALIDATED already
    -> CARRY_FORWARD_FORBIDDEN

missing path / unreadable evidence / ambiguous impact
    -> UNKNOWN IMPACT
    -> conservative expansion
```

A carried proof MUST retain its source review round/evidence identity. Do not synthesize a new proof merely to avoid testing.

## 5. FIX Context Delivery

For Slice-C FIX, augment the existing thin executor context with a dedicated deterministic `FIX CONTEXT PACK` section derived only from the validated machine-readable pack.

It must emphasize exactly:

```text
previous reviewed head
open findings
affected paths
protected accepted paths
proof IDs and current carry-forward/invalidation state
required impacted test paths
impact confidence
fallback test paths when confidence is UNKNOWN
roadmap/task authority remains external and unchanged
```

The canonical REVIEW remains the WORK artifact and the canonical TASK remains exact context authority. The derived pack is guidance/evidence only and MUST NOT create new RUN/FIX/MERGE authority.

Do not re-add unrelated ADR/history artifacts into the FIX executor context merely for prose convenience.

Provider neutrality is mandatory: Codex and Antigravity receive the same semantic FIX pack contract.

## 6. Invalidation-Based T1 Selection

For Slice-C review-first FIX publication, select deterministic impacted T1 from the validated pack.

Known impact:

```text
base required_test_paths
+ test_paths for INVALIDATED / non-carry-forward proofs
-> dedupe canonical test paths
-> run one bounded pytest T1 command at the common executor/publication boundary
```

If every relevant proof carries forward and the pack declares no new required test path, do not re-run unrelated accepted proof tests solely because this is a new FIX round.

Unknown impact:

```text
impact confidence UNKNOWN
OR proof/path evidence cannot be resolved
OR actual changed paths escape the declared affected envelope
-> select unknown_impact_fallback_test_paths
-> mark impact scope EXPANDED
-> next semantic review must expand its impact envelope
```

The unknown-impact fallback must remain T0/T1/impact validation. It MUST NOT invoke the final full canonical T2 before semantic acceptance.

All selected tests must finish successfully before candidate publication. Failure blocks publication without automatic retry/reroute.

## 7. Actual Delta vs Declared Impact Envelope

After executor mutation and before candidate publication, compare actual dirty/changed paths with the validated FIX pack.

Required semantics:

```text
actual change inside affected_paths -> expected impact
actual change touches proof subject/dependency -> corresponding proof invalidated
actual change touches protected accepted path but is not covered by declared affected proof/envelope -> UNKNOWN impact / expand
actual change outside existing EXECUTOR_ALLOWED_PATHS_JSON -> existing scope gate still blocks
```

Slice C must not weaken the existing allowed-path authority. Impact evidence refines review/testing scope; it never expands executable file scope.

## 8. Delta + Impact Evidence For Semantic Review

Without redesigning RESULT format, add one bounded machine-readable Slice-C evidence block to the existing candidate result for opt-in FIX rounds.

Minimum evidence:

```text
previous_reviewed_head_sha
impact_confidence_observed
impact_scope_expanded
actual_changed_paths
carried_forward_proof_ids
invalidated_proof_ids
forbidden_or_unknown_proof_ids
selected_test_paths
selected_test_status
protected_accepted_paths_unchanged
```

Do not persist raw model reasoning, raw executor reasoning, or large test logs in this new block.

The next ChatGPT review uses this evidence for `Delta + Impact Review`:

```text
carried proof + protected subject/dependencies unchanged
    -> do not reopen solely because review round changed

invalidated proof / changed affected surface
    -> re-review that impact envelope

UNKNOWN / expanded impact
    -> broaden semantic review conservatively
```

The final semantic reviewer retains authority to find new blockers in the impacted semantic area; proof reuse is not a prohibition against detecting adjacent regressions.

## 9. Existing Review-First Certification Must Remain Unchanged

TASK-090 invariants are protected:

```text
candidate RUN/FIX publication -> AIOS-managed T2 count 0
semantic acceptance -> non-authoritative
certify-reviewed -> one exact blocking machine T2
model polls during T2 -> 0
executor polls during T2 -> 0
post-T2 trust revalidation -> required
exact terminal digest verification -> required
final merge authority -> existing merge gate
```

Slice C MUST NOT move T2 back into FIX publication.

## 10. Required Tests

Add focused deterministic tests. The targeted suite must not run a real five-minute canonical repository suite.

Required proof matrix includes at minimum:

```text
FIX_MODE_MISSING_COMPATIBLE: PASS
FIX_MODE_EXACT_OPT_IN: PASS
FIX_MODE_DUPLICATE_OR_UNKNOWN_FAILS_CLOSED: PASS
FENCED_FIX_MODE_EXAMPLE_DOES_NOT_ACTIVATE: PASS
FIX_PACK_STRICT_BOUNDED_SCHEMA: PASS
FIX_PACK_PREVIOUS_HEAD_MUST_MATCH_REVIEW_HEADER: PASS
PROOF_FINGERPRINT_DETERMINISTIC: PASS
PROOF_FINGERPRINT_CHANGES_ON_BLOB_CHANGE: PASS
UNRESOLVABLE_PROOF_PATH_BECOMES_UNKNOWN: PASS
UNCHANGED_VALID_PROOF_CARRIES_FORWARD: PASS
SUBJECT_CHANGE_INVALIDATES_PROOF: PASS
DEPENDENCY_CHANGE_INVALIDATES_PROOF: PASS
KNOWN_IMPACT_SELECTS_ONLY_REQUIRED_T1: PASS
UNKNOWN_IMPACT_SELECTS_FALLBACK_T1: PASS
ACTUAL_DELTA_ESCAPE_EXPANDS_IMPACT: PASS
ALLOWED_PATH_SCOPE_REMAINS_FAIL_CLOSED: PASS
FIX_CONTEXT_PACK_IS_BOUNDED_AND_PROVIDER_NEUTRAL: PASS
CARRIED_ACCEPTED_SURFACE_NOT_REOPENED_BY_MACHINE_STATE: PASS
INVALIDATED_SURFACE_MARKED_FOR_DELTA_IMPACT_REVIEW: PASS
SLICE_C_FIX_PUBLICATION_T2_COUNT_ZERO: PASS
FINAL_CERTIFICATION_STILL_OWNED_BY_CERTIFY_REVIEWED: PASS
NO_AUTO_RETRY_OR_REROUTE: PASS
TASK_087_NOT_IMPLEMENTED: PASS
```

At minimum run:

```text
venv\Scripts\python.exe -m pytest tests/aios_bridge/test_fix_review.py tests/aios_bridge/test_review_pipeline.py tests/aios_bridge/test_executor_context_pack.py tests/aios_bridge/test_executor_automation.py tests/aios_bridge/test_lean_review_integration.py -q
```

Run additional bounded impacted tests if implementation touches an existing shared helper.

DO NOT run `pytest tests/ -q` during executor RUN/FIX for TASK-091. Final full canonical belongs only to `certify-reviewed` after semantic acceptance.

## 11. Forbidden Scope

Do not implement in TASK-091:

```text
compact RESULT redesign
single-source-of-truth evidence migration
review/certification cancellation or supersession workflow beyond existing exact-head fail-closed behavior
persistent Finding Registry service
risk-adaptive live reviewer/model routing
independent second-review orchestration
finding-to-guardrail promotion
background daemon/service
TASK-087
P1 capability integration lane
Python Agent pilot
P2
P3
H5-H8
automatic retry
automatic reroute
paid API calls
```

## 12. Completion Boundary

TASK-091 semantic acceptance is NOT PASS and does not authorize merge.

TASK-091 completes only when:

```text
candidate semantic review -> SEMANTICALLY_ACCEPTED_PENDING_T2
exact candidate certify-reviewed -> CERTIFICATION_PASS
merge-reviewed -> exact reviewed/certified head fast-forwarded to main
```

TASK-091 completion means Slice C is implemented. It does NOT mean ADR-064 or P1 is complete.

After TASK-091 merge, the next exact-baseline task is Slice D — compact evidence + supersession + bounded finding-to-guardrail promotion. TASK-087 remains reserved until Slice D also PASS/merges.
