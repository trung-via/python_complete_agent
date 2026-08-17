# ADR-021 — AIOS Continuity M7 Third Executor Portability Proof Contract Lock

STATUS: LOCKED

## Context

ADR-010 locks M7 as **Third Executor Portability Proof**: add Claude Code after Antigravity and Codex without changing Continuity Core contracts or the canonical state machine.

M4 established the vendor-neutral Executor contract. M5 established `MAX_ACTIVE_EXECUTORS_PER_TASK = 1`. M6 proved stable-boundary Executor failover in both directions between Antigravity and Codex using the same M5 lease, M6 `StableExecutorFailoverProof`, Bridge authorization and publish semantics.

M7 is therefore not a new failover design. It is an architecture portability test.

The key question is:

> Can a third real Executor be admitted at the Bridge/integration edge and participate in the already-locked M4/M5/M6 contracts without modifying Continuity Core simply because its product name is different?

If adding Claude Code requires vendor branches or schema/state-machine changes in Continuity Core, M7 fails its architectural objective.

Baseline `main`:

```text
8a1550b40692798fe0c049aa2ad74d55c54618ee
```

M6 / TASK-030 is APPROVED and merged at this baseline.

---

## Decision 1 — M7 adds exactly one third runtime Executor identity

The Bridge runtime executor set becomes exactly:

```text
antigravity
codex
claude-code
```

`claude-code` is an integration-edge identity only.

Continuity Core remains vendor-neutral and MUST NOT add product-name branching.

Unknown, padded or mixed-case executor IDs remain fail-closed.

---

## Decision 2 — No Continuity Core contract/state-machine changes

M7 MUST NOT change semantic behavior of:

```text
src/aios_bridge/continuity/executor.py
src/aios_bridge/continuity/lease.py
src/aios_bridge/continuity/executor_failover.py
src/aios_bridge/continuity/state.py
src/aios_bridge/runtime_lease.py
src/aios_bridge/continuity/brain.py
src/aios_bridge/continuity/failover.py
```

Nor may M7 add Claude-specific fields to:

```text
ExecutionRequest
PreparedExecution
ExecutionResult
ExecutorLease
StableExecutorFailoverProof
ContinuityState
```

The existing generic executor IDs and capability/lease/failover bindings are the entire portability surface.

A change to these contracts merely to accommodate Claude Code requires STOP and architecture escalation.

---

## Decision 3 — Reuse M5 lease semantics unchanged

`MAX_ACTIVE_EXECUTORS_PER_TASK = 1` remains unchanged.

Claude Code receives authority only through the same exact M5 active lease and ACTIVE authorization used by existing executors.

No:

```text
second lease type
Claude-specific lock
TTL
heartbeat
lease steal
PID ownership
parallel same-workspace execution
```

is authorized.

---

## Decision 4 — Reuse M6 stable-boundary failover unchanged

Cross-executor FIX involving Claude Code MUST use the existing M6 chain:

```text
prior authorization == CONSUMED
current branch == exact task branch
HEAD == prior published SHA
remote task branch == prior published SHA
source RESULT resolved at exact prior published SHA
current REVIEW == exact CHANGES_REQUIRED control artifact
no ACTIVE lease
human explicitly selects replacement executor
replacement lease acquired
StableExecutorFailoverProof built and validated
replacement ACTIVE authorization persisted
publish revalidates exact lease/proof/review before tests
push success
exact lease release
auth -> CONSUMED + published_sha
```

No M7-specific failover proof schema is permitted.

---

## Decision 5 — Human selection remains explicit for failover

Cross-executor FIX to or from Claude Code requires explicit Human executor selection.

Expected Bridge-level shape:

```text
/aios-worker FIX TASK-N --executor claude-code
/aios-worker FIX TASK-N --executor antigravity
```

Omitting `--executor` MUST NOT be interpreted as authorization to perform an automatic cross-executor transition.

No quota detector, availability detector, ranking, router or automatic replacement selection is part of M7.

---

## Decision 6 — Claude Code launch/transport is outside Continuity Core

M7 does not require AIOS to automate Claude Code startup.

A human may trigger Claude Code through an official supported client/CLI/surface after Bridge authorizes `executor_id=claude-code`.

Bridge/Continuity authority is determined by canonical authorization + lease + repository evidence, not by scraping a UI or storing a Claude session transcript.

M7 MUST NOT add browser automation of Claude, cookie/session reuse, unofficial pseudo-API transport or a paid API substitution merely to prove portability.

---

## Decision 7 — Same-executor Claude Code FIX must remain ordinary FIX

After Claude Code has published successfully, another Human-authorized FIX selecting `claude-code` is an ordinary same-executor FIX:

```text
EXECUTOR_FAILOVER: NO
```

It MUST NOT fabricate `StableExecutorFailoverProof` merely because Claude Code is the selected executor.

---

## Decision 8 — Real portability proof requires Claude Code as both replacement and source

M7 requires two controlled real repository transitions on TASK-031:

### Proof A

```text
Antigravity -> Claude Code
```

Claude Code must be the actual selected replacement executor and publish through Bridge.

### Proof B

```text
Claude Code -> Antigravity
```

Claude Code must therefore also be proven as a valid source executor whose prior CONSUMED authorization and canonical M5 lease snapshot can be reconstructed by the unchanged M6 contract.

This proves both ingress and egress portability for the third executor.

M6 Codex evidence remains valid and need not be repeated in M7.

---

## Decision 9 — Proof evidence is Bridge-generated and bounded

TASK-031 RESULT evidence must remain Bridge-generated.

M7 proof progress fields are:

```text
M7_REAL_PROOF_ANTIGRAVITY_TO_CLAUDE_CODE: PENDING|PASS
M7_REAL_PROOF_CLAUDE_CODE_TO_ANTIGRAVITY: PENDING|PASS
```

For a validated failover publish, existing M6 manifest fields remain authoritative:

```text
EXECUTOR_ID
EXECUTOR_FAILOVER
FAILOVER_FROM_EXECUTOR
FAILOVER_TO_EXECUTOR
FAILOVER_SOURCE_PUBLISHED_SHA
FAILOVER_PROOF_FINGERPRINT
FAILOVER_REVIEW_BLOB_SHA
```

Do not persist prompts, chat transcripts, Claude session IDs, credentials, raw runtime paths, tokens or command histories as canonical proof.

---

## Decision 10 — Proof progress must inherit only from exact Bridge-published predecessor evidence

M7 proof progress must use the same provenance rule hardened in M6:

- current validated failover may advance the current proof stage;
- already-proven stages may be inherited only from the exact prior Bridge-published SHA carried by authorization/failover evidence;
- arbitrary Git history scans, working-tree RESULT content or executor-authored unanchored commits are not proof authority.

Proof progress must be monotonic across later same-executor repair/evidence rounds.

---

## Decision 11 — M7 implementation boundary

Expected production change:

```text
MODIFY  bridge.py
```

Expected test change:

```text
MODIFY  tests/test_bridge.py
```

A small integration-edge helper file is allowed only if it clearly reduces duplication and remains outside Continuity Core.

No production change is expected in Continuity Core.

---

## Decision 12 — M8/M9/M10 leakage remains forbidden

M7 MUST NOT add:

```text
Brain+Executor end-to-end continuity proof
hot/dirty workspace handoff
checkpoint-based executor transfer
quota polling
availability polling
automatic executor selection
capability router/scoring/ranking
LLM routing
automatic API fallback
fourth executor
autonomous merge
```

Those belong to later milestones.

---

# Architecture Implementation Plan

## AIP-1 — Extend only the runtime executor allowlist

Update the integration-edge runtime executor set from:

```text
antigravity,codex
```

to:

```text
antigravity,codex,claude-code
```

Reuse the existing validator everywhere.

## AIP-2 — Reuse unchanged M6 classification and stable-boundary helpers

No Claude-specific branch should be added to failover classification, lease construction, proof construction or publish validation.

The same code path that handles Antigravity/Codex must handle Claude Code solely because `executor_id` is a valid canonical string admitted by the Bridge allowlist.

## AIP-3 — Extend TASK-031 proof-progress generation narrowly

Add bounded TASK-031 progress generation equivalent to M6 TASK-030 proof progress, but for:

```text
antigravity -> claude-code
claude-code -> antigravity
```

Use exact predecessor published SHA provenance only.

Do not generalize this into a router or arbitrary graph engine in M7.

## AIP-4 — Preserve M5/M6 publish and rollback behavior

No changes to release ordering, rollback authority or active-lease retention semantics are authorized merely because the selected executor is Claude Code.

## AIP-5 — Real proof remains stage-gated

Initial Antigravity RUN implements integration/test changes only and reports both M7 proof directions `PENDING`.

Primary Brain performs Full Semantic Review before any Claude Code proof run.

Only after semantic findings are closed may controlled proof A begin.

After proof A is reviewed, controlled proof B begins.

Final Independent Audit is mandatory after both proof directions pass and all findings are closed.

---

# Adversarial Checklist

- [ ] exact `claude-code` accepted;
- [ ] padded/mixed-case/unknown Claude aliases rejected;
- [ ] supported runtime set is exactly `antigravity,codex,claude-code`;
- [ ] Continuity Core files are semantically unchanged;
- [ ] no Claude-specific field added to canonical contracts;
- [ ] Antigravity -> Claude Code cross-executor FIX uses existing M6 proof;
- [ ] Claude Code -> Antigravity cross-executor FIX uses existing M6 proof;
- [ ] Claude Code -> Claude Code FIX is ordinary same-executor FIX;
- [ ] missing/malformed prior auth still fails closed;
- [ ] cross-executor selection still requires explicit `--executor`;
- [ ] wrong branch / HEAD drift / remote drift still blocks before lease acquisition;
- [ ] ACTIVE/corrupt lease still blocks replacement acquisition;
- [ ] partial/tampered failover metadata still blocks publish before tests;
- [ ] test/commit/push failure retains exact active lease;
- [ ] successful publish preserves M5 push -> release -> CONSUMED ordering;
- [ ] legacy approve path cannot bypass Claude Code failover rules;
- [ ] RESULT shows exact executor/failover identities;
- [ ] forged RESULT cannot advance M7 proof progress;
- [ ] proven M7 stage survives same-executor repair;
- [ ] no browser automation or pseudo-API launch for Claude Code;
- [ ] no router/quota detector/auto failover;
- [ ] Human RUN/FIX/MERGE authority unchanged;
- [ ] automated tests make zero live/paid external model calls.

---

# Acceptance

M7 is complete only when:

```text
third executor identity admitted at Bridge edge
+ Continuity Core/state machine unchanged
+ focused/full tests green
+ Antigravity -> Claude Code real proof PASS
+ Claude Code -> Antigravity real proof PASS
+ M5 single-active-executor invariant preserved
+ M6 stable-boundary contract reused unchanged
+ no router/hot-handoff/M8 leakage
+ Final Independent Audit PASS
+ REVIEW-031 APPROVED
```

Human MERGE remains a separate explicit authorization.
