# TASK-031 — Open Multi-Agent Continuity OS M7 Third Executor Portability Proof

## Work Class

`L3 — CONTROL PLANE / MULTI-EXECUTOR / AUTHORITY-SAFETY`

This task follows the locked Uniform Assurance pipeline and ADR-021.

Primary Brain owns:
- contract;
- Architecture Implementation Plan;
- Adversarial Checklist;
- Full Semantic Review;
- controlled real-proof review gates;
- Final Independent Audit.

Active Executor owns:
- repository inspection;
- detailed implementation plan;
- code/tests within locked scope;
- self-audit;
- RESULT evidence.

Human remains sole RUN / FIX / MERGE authority and explicitly selects replacement Executor for cross-executor proof steps.

---

## Baseline

Canonical `main`:

```text
8a1550b40692798fe0c049aa2ad74d55c54618ee
```

M6 / TASK-030 is APPROVED and merged.

Authoritative architecture:

```text
ADR-010 — Open Multi-Agent Continuity OS Architecture Lock
ADR-021 — M7 Third Executor Portability Proof Contract Lock
```

Existing M4/M5/M6 canonical contracts are authoritative and MUST be reused rather than redesigned.

---

## Objective

Add **Claude Code** as the third real runtime Executor and prove that the existing vendor-neutral M4/M5/M6 architecture admits it without changing Continuity Core contracts or state-machine semantics.

The required architecture proof is:

```text
Antigravity -> Claude Code -> Antigravity
```

at stable RESULT/REVIEW boundaries under the same exact M5 lease and M6 `StableExecutorFailoverProof` semantics.

---

# Locked Contracts

## C1 — Runtime executor set

After M7 implementation, Bridge-supported runtime Executor IDs are exactly:

```text
antigravity
codex
claude-code
```

Exact case and spelling only.

Reject examples:

```text
Claude-Code
claude_code
 claude-code
claude-code 
claude
```

No arbitrary user-provided executor IDs.

---

## C2 — Continuity Core portability invariant

Adding Claude Code MUST NOT require semantic changes to:

```text
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/executor_failover.py
src/aios_bridge/continuity/state.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/continuity/brain.py
src/aios_bridge/continuity/failover.py
```

No Claude-specific branch/field/schema/state transition may be added to these modules.

If implementation discovers a genuine generic defect in these contracts, STOP and escalate rather than silently widen M7.

---

## C3 — Existing M5 single-active lease invariant remains exact

```text
MAX_ACTIVE_EXECUTORS_PER_TASK = 1
```

Claude Code uses the existing `ExecutorLease` and `AtomicExecutorLeaseStore` unchanged.

No second lock system, TTL, heartbeat, steal or parallel same-workspace mutation.

---

## C4 — Existing M6 stable-boundary failover contract is reused unchanged

Cross-executor FIX involving Claude Code requires the same preconditions already proven in M6:

```text
prior auth exists and is strict
prior auth status == CONSUMED
prior published_sha is exact
current branch == expected task branch
HEAD == source published_sha
remote task branch == source published_sha
source RESULT resolves at source published_sha
current authoritative REVIEW == CHANGES_REQUIRED
review commit/blob exact and immutable
no ACTIVE lease
Human explicitly selected replacement executor
```

Then the same existing path must:

```text
acquire replacement lease
build StableExecutorFailoverProof
validate source/replacement relation
persist ACTIVE authorization
publish only after exact lease/proof/review revalidation
push
release exact lease
auth -> CONSUMED + exact published_sha
```

No new M7 failover proof type.

---

## C5 — Human selection is mandatory for cross-executor transition

A transition such as:

```text
antigravity -> claude-code
claude-code -> antigravity
```

requires explicit Human selection via `--executor` or equivalent approved wrapper input.

Default executor behavior must never silently become an automatic failover decision.

---

## C6 — Same-executor Claude Code FIX remains ordinary FIX

If prior CONSUMED auth executor is `claude-code` and Human selects `claude-code`, then:

```text
EXECUTOR_FAILOVER: NO
```

No failover proof may be fabricated.

---

## C7 — Bridge context/state must expose Claude Code truthfully

When Claude Code owns the current lease/authorization, Bridge context and executor-aware state messages must expose:

```text
executor_id = claude-code
```

No hard-coded Antigravity/Codex wording may misrepresent the active executor.

Do not store Claude session transcripts, credentials or product-private runtime state.

---

## C8 — No automatic Claude Code launch required

TASK-031 does not require an AIOS transport adapter or automatic process launch.

After Bridge authorization, Human may invoke Claude Code using an official supported Claude Code client/CLI/surface in the same repository/workspace.

The Executor must obtain authority from Bridge context/authorization and publish through Bridge.

No browser automation, pseudo-API or paid API substitution is allowed for the M7 proof.

---

## C9 — TASK-031 proof progress is Bridge-generated

Bridge must generate bounded fields:

```text
M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PENDING|PASS
M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PENDING|PASS
```

Initial implementation RESULT must be:

```text
PENDING
PENDING
```

Proof A RESULT must be:

```text
PASS
PENDING
```

Proof B RESULT must be:

```text
PASS
PASS
```

Executor-authored working-tree text is never sufficient to advance proof state.

---

## C10 — M7 proof provenance uses exact predecessor evidence only

Proof progress may advance from:

1. the current validated failover publication; or
2. the exact predecessor Bridge-published RESULT anchored by `source_published_sha` / `prior_published_sha`.

Do not scan arbitrary Git history.
Do not trust unanchored commits.
Do not trust current working-tree RESULT content.

A forged committed RESULT before Bridge publish must not advance M7 proof progress.

---

## C11 — Existing M6 manifest remains authoritative for transitions

Validated cross-executor RESULT must continue to report:

```text
EXECUTOR_ID
EXECUTOR_FAILOVER: YES
FAILOVER_FROM_EXECUTOR
FAILOVER_TO_EXECUTOR
FAILOVER_SOURCE_PUBLISHED_SHA
FAILOVER_PROOF_FINGERPRINT
FAILOVER_REVIEW_BLOB_SHA
```

M7 adds only proof-progress fields for TASK-031.

---

## C12 — No M8/M9/M10 scope leakage

Do not implement:

```text
Brain+Executor end-to-end continuity proof
hot/dirty-workspace handoff
checkpoint handoff
quota/availability polling
router/scoring/ranking
automatic executor selection
automatic failover
LLM dispatch
automatic API fallback
fourth executor
autonomous merge
```

---

# Primary Brain Architecture Implementation Plan

## AIP-1 — Minimal integration-edge change

Expected production delta:

```text
MODIFY bridge.py
```

Primary functional change:

```text
SUPPORTED_RUNTIME_EXECUTORS:
antigravity,codex
-> antigravity,codex,claude-code
```

Do not add vendor branches to lease/failover logic.

## AIP-2 — Extend proof-progress generation for TASK-031

Add a narrow TASK-031 progress evaluator following the exact provenance rules already hardened for TASK-030.

Required transitions:

```text
Stage A: antigravity -> claude-code
Stage B: claude-code -> antigravity
```

Do not refactor into a generic routing engine in M7.

## AIP-3 — Extend Bridge tests, not Continuity Core

Expected test delta:

```text
MODIFY tests/test_bridge.py
```

Continuity Core tests may be rerun but should not need semantic edits for the new vendor identity.

## AIP-4 — Preserve all M5/M6 failure semantics

Claude Code participation must not alter:

```text
fail-closed prior-auth classification
stable branch checks
no-active-lease gate
post-acquire rollback
publish-before-test validation
failure lease retention
push -> release -> CONSUMED ordering
human recovery semantics
```

## AIP-5 — Stage-gate real proof

Initial RUN is performed by Antigravity and implements code/tests only.

Do not invoke Claude Code before Primary Brain Full Semantic Review passes.

---

# Required Automated Tests

At minimum add/extend tests for:

1. `validate_runtime_executor_id("claude-code")` succeeds;
2. padded/mixed-case/alias Claude IDs fail closed;
3. runtime executor set contains exactly three IDs;
4. initial RUN may persist `executor_id=claude-code` if Human explicitly selects it;
5. Antigravity -> Claude Code FIX is classified as failover and uses existing M6 proof path;
6. Claude Code -> Antigravity FIX is classified as failover from strict prior CONSUMED auth;
7. Claude Code -> Claude Code FIX is ordinary same-executor FIX with no failover metadata;
8. legacy `cmd_approve()` applies identical rules;
9. publish under Claude Code ACTIVE auth requires exact active lease before tests;
10. tampered/partial failover metadata still fails closed before tests;
11. wrong branch / HEAD / remote branch still blocks before acquire;
12. active/corrupt lease still blocks replacement acquisition;
13. TASK-031 initial proof progress is `PENDING/PENDING`;
14. validated Antigravity -> Claude Code publish yields `PASS/PENDING`;
15. validated Claude Code -> Antigravity publish yields `PASS/PASS`;
16. same-executor repair preserves already-proven M7 progress;
17. forged working-tree or committed RESULT cannot advance M7 proof progress without exact Bridge predecessor anchor;
18. existing TASK-030 M6 proof-progress tests remain green;
19. full Bridge suite green;
20. full Continuity suite green;
21. full repository suite green;
22. automated tests make zero live/paid external model calls.

---

# Expected Implementation Boundary

Expected production change:

```text
MODIFY bridge.py
```

Expected tests:

```text
MODIFY tests/test_bridge.py
```

Expected RESULT:

```text
.ai/results/RESULT-031.md
```

No expected semantic changes to Continuity Core modules listed in C2.

If those files change, RESULT must stop and explain why before claiming completion.

---

# Initial RESULT-031 Required Manifest

Initial RUN RESULT must report at minimum:

```text
TASK_ID: TASK-031
ACTION: RUN
BASE_SHA: 8a1550b40692798fe0c049aa2ad74d55c54618ee
M7_THIRD_EXECUTOR_PORTABILITY: IMPLEMENTED
SUPPORTED_RUNTIME_EXECUTORS: antigravity,codex,claude-code
CONTINUITY_CORE_CHANGED: NO
M5_LEASE_SEMANTICS_CHANGED: NO
M6_FAILOVER_CONTRACT_CHANGED: NO
AUTOMATIC_EXECUTOR_ROUTING: NO
HOT_HANDOFF_ADDED: NO
FOURTH_EXECUTOR_ADDED: NO
PAID_EXTERNAL_API_CALLS: 0
LIVE_EXTERNAL_CALLS_AUTOMATED_TESTS: 0
M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PENDING
M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PENDING
BRIDGE_TESTS: <count/pass>
CONTINUITY_TESTS: <count/pass>
FULL_REPO_TESTS: <count/pass>
REGRESSIONS: 0
EXECUTOR_ID: antigravity
```

Do not claim M7 complete in initial RESULT.

---

# Controlled Real Proof Protocol

## Stage 0 — Implementation

Human authorizes:

```text
/aios-worker RUN TASK-031
```

Antigravity implements only the M7 integration/test delta and publishes RESULT-031.

Primary Brain performs Full Semantic Review.

If semantic blockers exist, they take precedence.

If semantic review is clean but Proof A is absent, Primary Brain issues controlled:

```text
STATUS: CHANGES_REQUIRED
SEMANTIC_FINDINGS: NONE
M7_PROOF_REQUIRED: ANTIGRAVITY_TO_CLAUDE_CODE
```

---

## Stage A — Antigravity -> Claude Code

Human must explicitly authorize:

```text
/aios-worker FIX TASK-031 --executor claude-code
```

Then Human triggers Claude Code through an official supported Claude Code surface in the same repository/workspace.

Claude Code must reconstruct from canonical repo/TASK/ADR/REVIEW/Bridge context, run required proof tests and publish through Bridge.

A RESULT-only evidence commit is acceptable if no semantic fix is required.

Stage-A RESULT must contain:

```text
EXECUTOR_ID: claude-code
EXECUTOR_FAILOVER: YES
FAILOVER_FROM_EXECUTOR: antigravity
FAILOVER_TO_EXECUTOR: claude-code
M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PASS
M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PENDING
```

Primary Brain reviews Proof A.

If valid and semantic blockers are absent, Primary Brain issues controlled:

```text
STATUS: CHANGES_REQUIRED
SEMANTIC_FINDINGS: NONE
M7_PROOF_REQUIRED: CLAUDE_CODE_TO_ANTIGRAVITY
```

---

## Stage B — Claude Code -> Antigravity

Human explicitly authorizes:

```text
/aios-worker FIX TASK-031 --executor antigravity
```

Antigravity executes the proof-required FIX and publishes through Bridge.

Stage-B RESULT must contain:

```text
EXECUTOR_ID: antigravity
EXECUTOR_FAILOVER: YES
FAILOVER_FROM_EXECUTOR: claude-code
FAILOVER_TO_EXECUTOR: antigravity
M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PASS
M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PASS
```

Primary Brain then performs:

```text
proof-B validation
-> Full Semantic Review / delta confirmation
-> Final Independent Audit
-> APPROVED only if all findings/evidence are closed
```

Human MERGE remains a separate explicit action.

---

# Stop Conditions

STOP and escalate instead of widening scope if M7 appears to require:

- modification of M5 lease atomicity or compare-and-release semantics;
- modification of `StableExecutorFailoverProof` merely for Claude Code;
- modification of canonical state machine merely for Claude Code;
- dirty-workspace transfer;
- automatic process killing;
- quota/availability routing;
- browser automation of Claude;
- paid API key/token as normal M7 path;
- fourth executor;
- concurrency >1 active Executor;
- autonomous merge.

---

# Definition of Done

TASK-031 is done only when:

```text
claude-code admitted as third Bridge runtime executor
+ Continuity Core contracts/state machine unchanged
+ focused/full tests green
+ real Antigravity -> Claude Code proof PASS
+ real Claude Code -> Antigravity proof PASS
+ M5 single-active lease invariant preserved
+ M6 stable-boundary failover reused unchanged
+ no M8/M9/M10 leakage
+ Final Independent Audit PASS
+ REVIEW-031 APPROVED
```

Do not merge before explicit Human MERGE authorization.
