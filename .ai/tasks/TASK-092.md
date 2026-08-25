# TASK-092 — Lean Review Slice D: Compact Evidence, Supersession, Guardrail Learning & Blocked Recovery

STATUS: READY
PUBLISHER_PROFILE: CANONICAL_E4
CLASS: L2 — AIOS BRIDGE LEAN EXECUTION / P1 LEAN REVIEW SLICE D
MILESTONE: P1
CAPABILITY_ID: P1_UNIFIED_VALIDATION_CAPABILITY_BATCH
EXECUTOR_MODE: DUAL_EXECUTOR_ALLOWED
RECOMMENDED_EXECUTOR: codex
PAID_API_CALL_ALLOWED: NO
AUTO_RETRY_ALLOWED: NO
AUTO_REROUTE_ALLOWED: NO
IMPLEMENTATION_REFINEMENT_ADR: ADR-064
DECOMPOSITION_ADR: ADR-065
CUTOVER_SLICE: EVIDENCE_LEARNING_OPTIMIZATION
TASK_091_PREREQUISITE: PASS_MERGED
TASK_087_REMAINS_RESERVED: YES
P1_FORMAL_COMPLETION: NO
P2_P3_AUTHORIZED: NO
H5_H8_AUTHORIZED: NO
REVIEW_PIPELINE_MODE: REVIEW_FIRST_CERTIFICATION

ROADMAP_BINDING_JSON: {"roadmap_id":"AIOS-BRIDGE-LEAN-EXECUTION","roadmap_version":"1.2","roadmap_blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c","roadmap_fingerprint":"89c9372c074ecb43778705f07c6fded67e4af7833c0feb72a92a9ae2e737c612","roadmap_fingerprint_algorithm_version":"roadmap-sha256-v1","milestone":"P1","capability_id":"P1_UNIFIED_VALIDATION_CAPABILITY_BATCH","requirement_bindings":["P1.R8","P1.R9","P1.R10"],"scope_in":["compact single-source-of-truth review-first RESULT evidence","machine-readable finding lifecycle integration and deterministic bounded review-risk evidence","evidence-driven bounded finding-to-guardrail promotion recommendation","review and certification supersession bound to exact candidate identity","stale candidate cancellation or ignore semantics where the current synchronous infrastructure safely permits","structured clean-no-op executor blocker evidence without raw model reasoning","explicit-Human safe replacement executor after a proven clean no-op blocked execution with zero worktree delta","deterministic review and pre-invocation validation before lease/executor start where possible","deterministic rollback of a newly acquired lease when post-acquire pre-start validation fails and executor provably never started","preservation of review-first certification, proof-reuse FIX, roadmap, lease, scope and merge authority"],"scope_out":["automatic executor retry","automatic executor reroute","automatic guardrail code generation or automatic policy mutation","raw model reasoning persistence","background certification daemon","cancelling an already-running external process without a proven safe cancellation primitive","persistent executor sessions","adaptive executor selection","TASK-087 implementation","P1 capability-batch integration lane","Python Agent fast-lane pilot","P2","P3","H5-H8","paid API calls","canonical roadmap mutation"]}

## Baseline

```text
MAIN_SHA: 5570e64bec7522caf6b4ebda3b2f34ec45a11ebf
TARGET_BRANCH: ai/task-092
TASK_089: PASS_MERGED
TASK_090: PASS_MERGED
TASK_091: PASS_CERTIFIED_MERGED
REVIEW_FIRST_CERTIFICATION_ON_MAIN: YES
FIX_PROOF_REUSE_DELTA_IMPACT_ON_MAIN: YES
ROADMAP_V1_2: LOCKED_REGISTERED
ADR_065_SLICE_D_AUTHORITY: YES
TASK_087: RESERVED_NOT_EXECUTED
P1_FORMAL_COMPLETION: NO
P2_P3_STATUS: NOT_AUTHORIZED
H5_H8_STATUS: NOT_AUTHORIZED
```

TASK-092 is the final bounded Lean Review implementation slice authorized by ADR-065. It MUST itself use the review-first pipeline delivered by TASK-090 and the Slice-C FIX path delivered by TASK-091 for any CHANGES_REQUIRED round.

Required delivery lifecycle:

```text
RUN executor
  -> T0 / bounded targeted T1 / diff check
  -> publish candidate with AIOS-managed T2 count = 0
  -> ChatGPT semantic review
      -> CHANGES_REQUIRED: use FIX_REVIEW_MODE=PROOF_REUSE_DELTA_IMPACT + bounded FIX_CONTEXT_PACK_JSON; publish next candidate with T2=0
      -> SEMANTICALLY_ACCEPTED_PENDING_T2: continue
  -> bridge.py certify-reviewed 92
      -> full canonical T2 exactly once for exact accepted candidate
  -> bridge.py merge-reviewed 92
```

No full canonical T2 is authorized during RUN/FIX candidate publication for TASK-092.

## Machine-Readable E4 Inputs

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.md","blob_sha":"41bf467f3dd4fc8aea165ac65c37e0e2a5a3ef5c"},{"path":".ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.2.completions.json","blob_sha":"6b5fb5f99ec17cacca632e3b7a1953131b82c9b7"},{"path":".ai/roadmaps/CANONICAL-ROADMAP-REGISTRY-v1.json","blob_sha":"09180853439a383bb459094cb96fa2bd705afdd4"},{"path":".ai/decisions/ADR-065-AIOS-LEAN-REVIEW-PIPELINE-ACTIVATION-BOUNDED-SLICES.md","blob_sha":"947b3ec5b63ddd628838a533822e37499a837a74"}]
EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/result_evidence.py","src/aios_bridge/review_learning.py","src/aios_bridge/blocked_recovery.py","src/aios_bridge/review_pipeline.py","src/aios_bridge/certification_job.py","src/aios_bridge/executor_automation.py","tests/aios_bridge/test_result_evidence.py","tests/aios_bridge/test_review_learning.py","tests/aios_bridge/test_blocked_recovery.py","tests/aios_bridge/test_review_pipeline.py","tests/aios_bridge/test_certification_job.py","tests/aios_bridge/test_lean_review_integration.py","tests/test_bridge_executor_automation.py","tests/test_bridge.py"]
DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

## Purpose

Finish the Lean Review activation with one compact deterministic evidence model, exact-candidate supersession semantics, bounded review learning, and safe recovery from the clean-no-op executor dead-end observed during TASK-089/TASK-091 without weakening explicit Human authority.

The optimization rule is:

```text
ONE CANDIDATE
  -> ONE MACHINE EVIDENCE SOURCE
  -> ONE CURRENT REVIEW AUTHORITY
  -> ONE EXACT CERTIFICATION SUBJECT

STALE SUBJECT
  -> SUPERSEDED / IGNORED
  -> ZERO MERGE AUTHORITY

RECURRING EVIDENCE-BACKED FINDING
  -> BOUNDED GUARDRAIL PROMOTION CANDIDATE
  -> HUMAN/REVIEW AUTHORITY STILL REQUIRED

CLEAN EXECUTOR NO-OP
  -> STRUCTURED BLOCKED EVIDENCE
  -> NO AUTO RETRY/REROUTE
  -> EXPLICIT HUMAN MAY SELECT SAFE REPLACEMENT EXECUTOR
  -> ONLY IF ZERO-MUTATION BOUNDARY IS REPROVEN
```

## 1. Compact RESULT — One Machine-Readable Source Of Truth

Introduce a strict bounded review-first RESULT evidence contract, preferably isolated in `src/aios_bridge/result_evidence.py`.

For review-first candidates emit exactly one authoritative top-level machine block:

```text
RESULT_EVIDENCE_JSON: <canonical compact JSON object>
```

Minimum evidence must cover the facts currently duplicated across Review Manifest / Validation Evidence / Risks-Notes where applicable:

```text
schema_version
task_id
action
executor_id
pipeline_mode
candidate_head_sha
base_main_sha or explicit UNKNOWN when unavailable by contract
validation_profile
full_canonical_owner
candidate_stage_aios_managed_t2_execution_count
certification_deferred
semantic_review_required
targeted_test_status
publication_trust_status
transport_status
actual_changed_paths
slice_c_impact_evidence when present
review_risk_evidence when available
blocked_execution_evidence when applicable
```

Requirements:

```text
strict exact field set or versioned closed variant
bounded strings/lists only
canonical JSON serialization
stable fingerprint over canonical machine evidence
no raw pytest stdout
no raw model/executor reasoning
no duplicate machine-authoritative representations of the same fact
human-readable markdown summary may remain, but MUST be explicitly non-authoritative and derived from the machine object
legacy non-review-first RESULT format remains compatible unless explicitly migrated by this task
```

A parser/validator must reject duplicate `RESULT_EVIDENCE_JSON`, malformed JSON, unknown schema fields, contradictory T2/deferred facts, invalid SHA/fingerprint/path values, and authority-bearing facts inconsistent with review-first lifecycle.

TASK-092's own successful candidate publication SHOULD use the new compact review-first evidence if the implementation is active at publication time.

## 2. Finding Registry Integration + Risk Evidence

Use the existing `FindingRecord`, `FindingStatus`, review-risk enums/contracts from `review_pipeline.py`; do not create permissive parallel lifecycle vocabularies.

Add a bounded machine-readable review finding registry contract suitable for semantic review artifacts/evidence:

```text
finding_records
review_round
candidate_head_sha
review_effort
risk_evidence
```

Required semantics:

```text
finding lifecycle remains NEW -> OPEN -> FIX_SUBMITTED -> VERIFYING -> CLOSED
verification failure -> OPEN
CLOSED -> REOPENED only with evidence-backed regression
CLOSED retains fixed_by_sha + closure_review_round
registry entries duplicate-free by finding_id
candidate/head and review-round binding exact
risk router output is deterministic from bounded evidence
CRITICAL_SECOND_REVIEW may be emitted as required review effort evidence, but this task does NOT orchestrate a second model automatically
```

The registry is review evidence, not merge authority by itself.

## 3. Bounded Finding -> Guardrail Promotion

Prefer a pure contract in `src/aios_bridge/review_learning.py`.

Closed promotion targets may include only bounded categories such as:

```text
NONE
REGRESSION_TEST
STATIC_RULE
ARCHITECTURE_INVARIANT
TASK_TEMPLATE_RULE
ADR_CANDIDATE
```

Promotion MUST be evidence-driven and deterministic. At minimum consider:

```text
same normalized finding class/guardrail key recurs
finding is CLOSED or evidence-backed REOPENED as appropriate
severity / recurrence threshold is bounded
promotion target is explicitly allowed for that finding class
```

Required safety:

```text
one isolated style/nit finding -> NONE
raw prose similarity alone -> insufficient
promotion decision -> recommendation/evidence only
no automatic file edits, test generation, lint configuration mutation, ADR creation, roadmap mutation or authority expansion
Human/reviewer remains authority for actually adopting the guardrail
```

Persist only compact promotion evidence, never model reasoning.

## 4. Review + Certification Supersession

Integrate the existing `SUPERSEDED` lifecycle semantics into the live review-first path.

Required behavior:

```text
new candidate head for same task -> prior review/certification evidence for older head is stale
old review semantic acceptance -> cannot certify new head
old certification PASS -> cannot authorize merge of new head
pending certification for different candidate -> mark/archive/ignore as SUPERSEDED before creating a new current job when safe
stale terminal evidence -> retained only as provenance/history; never current authority
current candidate fingerprint must bind task/head/base/task blob/roadmap/profile/cert command as already defined
```

Where current synchronous infrastructure cannot safely cancel an already-running T2 process, do NOT invent cancellation. Let deterministic work finish, then fail closed / ignore stale output through exact post-T2 subject revalidation. Record stale/superseded semantics without model polling.

A repeated `certify-reviewed` for the exact current PASS candidate remains idempotent and MUST NOT run T2 twice.

## 5. Structured CLEAN_NO_WORKTREE_DELTA Blocker Evidence

The current clean-no-op path releases the lease and changes authorization to `EXECUTION_BLOCKED`, but retains only a coarse status and human diagnostic string. Replace/augment that with bounded structured fields such as:

```text
blocked_reason_code = CLEAN_NO_WORKTREE_DELTA
blocked_executor_id
blocked_operation
blocked_head_sha
blocked_at
executor_outcome
final_agent_message_observed
diagnostic_code
zero_worktree_delta = true
```

Exact names may differ, but the schema must be closed, bounded and machine-readable.

Do not persist raw final-agent prose or hidden reasoning.

## 6. Explicit-Human Safe Blocked Executor Replacement

Close the observed state-machine dead-end:

```text
Codex clean no-op
-> lease released
-> authorization EXECUTION_BLOCKED
-> Human explicitly selects Antigravity
-> old stable failover path currently rejects because source auth is not CONSUMED
```

Add a separate fail-closed `BLOCKED_EXECUTOR_REPLACEMENT` path; do not fake `EXECUTION_BLOCKED` as `CONSUMED` and do not manufacture a source RESULT.

Minimum preconditions:

```text
prior auth status == EXECUTION_BLOCKED
blocked_reason_code == CLEAN_NO_WORKTREE_DELTA
zero_worktree_delta == true
no active lease
replacement executor explicitly selected by Human
replacement executor != blocked executor
current task/review artifact passes normal preflight
current local branch is exact task branch
worktree clean before replacement authorization
current local HEAD == structured blocked_head_sha
remote task HEAD, when branch already exists remotely, == blocked_head_sha
for FIX, current REVIEWED_TASK_HEAD_SHA == blocked_head_sha
no automatic retry/reroute path calls this transition
```

For a RUN clean-no-op with no published source RESULT, replacement may still be allowed only from the exact proven zero-mutation head/task authority. For FIX, preserve previous published/result provenance separately if it exists; do not attribute it to the blocked executor attempt.

Replacement creates a fresh lease/execution fingerprint under explicit Human authority. Existing allowed paths, roadmap binding and publication trust remain unchanged.

If any precondition is uncertain -> FAIL CLOSED.

## 7. Deterministic Review / Pre-Invocation Preflight + Lease Rollback

Close the artifact/lease failures observed during earlier Lean Review rollout.

Before executor start, deterministically validate every fact that does not require a live executor:

```text
review machine header parses from exact top header region
required authority keys present exactly once
FIX_EXECUTION_MODE unambiguous
Slice-C marker/context pack unambiguous when used
all executor context refs resolve from the correct authoritative control commit
context blob SHAs match
TASK appears exactly once where governed FIX requires it
allowed paths are bounded and within TASK authority
executor policy supports exact operation/capabilities
launch/context pack can be built deterministically
```

Ordering invariant:

```text
VALIDATE_WHAT_CAN_BE_VALIDATED
-> THEN ACQUIRE/ACTIVATE LEASE
-> THEN START EXECUTOR
```

If a validation necessarily occurs after lease acquisition but before executor process/session start:

```text
PRE_START_FAILURE + EXECUTOR_PROVABLY_NOT_STARTED
-> release the newly acquired lease
-> restore prior authorization/state deterministically
-> no stale lease
```

If executor-start state is uncertain, do not auto-release; use `RECOVERY_REQUIRED`.

This mechanism must not create automatic retry/reroute.

## 8. Review-First / Slice-C Invariants Must Remain Intact

Protect all prior Lean Review behavior:

```text
candidate RUN/FIX publication -> AIOS-managed T2 count 0
semantic acceptance -> non-authoritative
Slice-C FIX -> proof carry-forward + invalidation + delta/impact + bounded T1
certify-reviewed -> exactly one final T2 for exact semantic-accepted candidate
machine waits for machine; model/executor polling count zero
post-T2 trust revalidation required
terminal result digest verification required
review/cert exact-head binding required
roadmap v1.2 binding required
merge-reviewed remains the only final fast-forward authority
TASK PASS != P1 COMPLETE
```

## 9. Required Tests

Add focused deterministic tests. Do not run the real full canonical suite during executor RUN/FIX.

At minimum cover:

```text
COMPACT_RESULT_CANONICAL_ROUND_TRIP: PASS
COMPACT_RESULT_DUPLICATE_OR_UNKNOWN_FIELD_FAILS_CLOSED: PASS
COMPACT_RESULT_CONTRADICTORY_T2_FACTS_FAILS_CLOSED: PASS
COMPACT_RESULT_NO_RAW_LOG_OR_REASONING: PASS
REVIEW_FIRST_RESULT_HAS_SINGLE_MACHINE_SOURCE: PASS
FINDING_REGISTRY_EXACT_HEAD_AND_ROUND_BOUND: PASS
FINDING_REGISTRY_INVALID_TRANSITION_FAILS_CLOSED: PASS
RISK_EVIDENCE_DETERMINISTIC: PASS
LOW_VALUE_SINGLE_FINDING_NOT_PROMOTED: PASS
RECURRING_EVIDENCE_FINDING_CAN_PRODUCE_BOUNDED_PROMOTION_CANDIDATE: PASS
PROMOTION_NEVER_MUTATES_REPO_OR_AUTHORITY: PASS
OLD_REVIEW_HEAD_CANNOT_CERTIFY_NEW_CANDIDATE: PASS
OLD_CERT_PASS_CANNOT_MERGE_NEW_CANDIDATE: PASS
STALE_PENDING_CERT_BECOMES_SUPERSEDED_OR_IGNORED_WITHOUT_T2_DUPLICATION: PASS
EXACT_CURRENT_CERT_PASS_REMAINS_IDEMPOTENT: PASS
CLEAN_NOOP_PERSISTS_STRUCTURED_BLOCKER: PASS
CLEAN_NOOP_PERSISTS_NO_RAW_AGENT_REASONING: PASS
BLOCKED_REPLACEMENT_REQUIRES_EXPLICIT_HUMAN_EXECUTOR_SELECTION: PASS
BLOCKED_REPLACEMENT_REQUIRES_ZERO_DELTA_AND_EXACT_HEAD: PASS
BLOCKED_REPLACEMENT_REQUIRES_NO_ACTIVE_LEASE: PASS
BLOCKED_REPLACEMENT_FIX_REVIEW_HEAD_MUST_MATCH_BLOCKED_HEAD: PASS
BLOCKED_REPLACEMENT_CREATES_FRESH_LEASE_WITHOUT_FAKE_CONSUMED_SOURCE: PASS
NO_AUTO_REROUTE_TO_BLOCKED_REPLACEMENT: PASS
PRE_INVOCATION_INVALID_REVIEW_FAILS_BEFORE_EXECUTOR_START: PASS
POST_ACQUIRE_PRE_START_FAILURE_ROLLS_BACK_LEASE_WHEN_NOT_STARTED_PROVEN: PASS
UNCERTAIN_EXECUTOR_START_STATE_REQUIRES_RECOVERY: PASS
SLICE_D_CANDIDATE_PUBLICATION_T2_COUNT_ZERO: PASS
SLICE_C_FIX_REMAINS_ACTIVE_FOR_TASK_092_REVIEW_ROUNDS: PASS
FINAL_CERTIFICATION_EXACTLY_ONCE: PASS
TASK_087_NOT_IMPLEMENTED: PASS
P2_P3_H5_H8_REMAIN_CLOSED: PASS
```

At minimum run bounded tests for the touched surfaces, for example:

```text
venv\Scripts\python.exe -m pytest tests/aios_bridge/test_result_evidence.py tests/aios_bridge/test_review_learning.py tests/aios_bridge/test_blocked_recovery.py tests/aios_bridge/test_review_pipeline.py tests/aios_bridge/test_certification_job.py tests/aios_bridge/test_lean_review_integration.py tests/test_bridge_executor_automation.py tests/test_bridge.py -q
```

If new test files are not created because an existing bounded test file is the clearer owner, keep all execution inside the authorized paths above.

DO NOT run `pytest tests/ -q` during executor RUN/FIX for TASK-092. Final full canonical belongs only to `certify-reviewed` after semantic acceptance.

## 10. Forbidden Scope

Do not implement in TASK-092:

```text
TASK-087
P1 formal completion declaration
capability integration lane
Python Agent pilot
P2 persistent executor sessions
P3 adaptive executor selection
Claude Code integration work
H5-H8
background polling/daemon
automatic retry
automatic reroute
automatic failover after blocked execution
automatic second-review model invocation
automatic guardrail/test/lint/ADR generation
raw chain-of-thought or raw final-agent reasoning persistence
paid API calls
roadmap v1.2 mutation
merge gate replacement or weakening
```

## 11. Completion Boundary

TASK-092 semantic acceptance is NOT PASS and does not authorize merge.

TASK-092 completes only when:

```text
candidate semantic review -> SEMANTICALLY_ACCEPTED_PENDING_T2
exact candidate certify-reviewed -> CERTIFICATION_PASS with AIOS-managed T2 count exactly 1
merge-reviewed -> exact reviewed/certified head fast-forwarded to main
```

After TASK-092 PASS + merge:

```text
ADR-065 Lean Review implementation slices A-D = implemented
TASK-087 may be evaluated for exact-baseline rebind
P1 is still NOT automatically complete
TASK-087 is still NOT automatically executable until the rebind/preflight step is performed
```
