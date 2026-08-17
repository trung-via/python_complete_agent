# REVIEW-032 — TASK-032 M8 Real Multi-Agent Continuity Proof

STATUS: CHANGES_REQUIRED

## Review Scope
- Round: 4 — Review Protocol v2 / Semantic Closure & Live Brain-Proof Gate
- Baseline main: `08508e48f6ffda70d1891dad461f6fd1b893b24b`
- Prior reviewed head: `e7191b6d7d28b970cf1088e3a9ae6258b9ecb948`
- Current reviewed head: `38356f100563da420c488ee6362917fd4f81b48b`
- Prior REVIEW blob: `0ccfda08c45772d62081dff318b748e8d13e1caa`

```text
FULL_SEMANTIC_REVIEW: PASS
R1-1: CLOSED
R1-2: CLOSED
R1-3: CLOSED
R1-4: CLOSED
SEMANTIC_FINDINGS: NONE
M8_BRAIN_PROOF_REQUIRED: YES
M8_BRAIN_PROOF: PENDING
M8_EXECUTOR_PROOF_REQUIRED: BLOCKED_UNTIL_BRAIN_PASS
M8_COMPOSITE_CHAIN: PENDING
FINAL_INDEPENDENT_AUDIT: NOT_RUN
APPROVED: NO
```

Repository evidence at the accepted Executor-A publication:

```text
EXECUTOR_A: antigravity
M8_EFFECTIVE_S0: 38356f100563da420c488ee6362917fd4f81b48b
BRIDGE_TESTS: 58/58 pass
CONTINUITY_TESTS: 174/174 pass
FULL_REPO_TESTS: 779/779 pass
REGRESSIONS: 0
```

From this review gate onward, `38356f100563da420c488ee6362917fd4f81b48b` is the frozen Executor-A stable boundary used by the live M8 Brain proof and later Executor failover. No further task-branch commit is permitted before the cross-executor Stage-B FIX is explicitly authorized.

---

# FINDING R1-1 — CLOSED

Round-4 repair changed `_evaluate_task_032_proof_progress(...)` so a syntactically valid/exact C7 REVIEW can no longer promote `M8_BRAIN_PROOF` to PASS. Brain state remains `PENDING` until Primary Brain independently validates the real Brain proof bundle. Exact REVIEW blob binding remains enforced; Executor proof may reflect the exact validated stable failover/review relationship, while `M8_COMPOSITE_CHAIN` remains PENDING until explicit composite verification.

Close conditions satisfied:

```text
[x] no code path promotes Brain PASS from C7 syntax alone
[x] fake-but-well-formed proof/artifact/state values do not create Brain PASS
[x] exact REVIEW blob binding remains enforced
[x] composite PASS is not emitted by publish metadata inference
[x] full repository remains green
```

---

# FINDING R1-2 — CLOSED

`prepare-brain` now accepts an explicit immutable `--control-commit-sha`, otherwise resolves only authoritative `origin/ai-control`. If that remote ref is unavailable it fails closed; there is no production fallback to local `ai-control`.

Proof provenance is now separated exactly:

```text
RESULT-032 -> exact M8_EFFECTIVE_S0
TASK-032   -> exact control_commit_sha
ADR-022    -> exact control_commit_sha
```

Close conditions satisfied:

```text
[x] no origin/ai-control -> local ai-control fallback
[x] exact control commit can be supplied explicitly
[x] stale local control branch cannot substitute
[x] TASK/ADR refs bind to exact immutable control commit
[x] RESULT remains exact S0-only
```

---

# FINDING R1-3 — CLOSED

Persisted `BrainFailoverProof` remains canonically bound to the proof derived from validated source/replacement requests, state and source result.

---

# FINDING R1-4 — CLOSED

Replacement BrainResult remains fully bound to task/request/brain/operation/output/path/blob plus approved control storage ref/domain.

---

# LIVE M8 BRAIN-PROOF GATE

Semantic repair is complete. The next operation is Stage A only.

## Frozen boundary

```text
M8_EFFECTIVE_S0: 38356f100563da420c488ee6362917fd4f81b48b
SOURCE_EXECUTOR_ID: antigravity
```

The task branch MUST remain exactly at S0 during Stage A. Brain proof artifacts MUST be persisted off the task branch, preferably:

```text
ai-control:.ai/context/proofs/TASK-032-M8/brain/
```

## Required real Brain pair

Human must explicitly choose two distinct real interactive Brain surfaces. Recommended for this proof:

```text
SOURCE_BRAIN_ID: chatgpt-chat
REPLACEMENT_BRAIN_ID: claude-chat
```

No chat UI automation and no transcript transfer.

## Required prepare command

Resolve the exact authoritative `ai-control` commit after this REVIEW is published, then run the proof-local prepare tool with explicit immutable refs:

```text
python scripts/aios_m8_multi_agent_continuity_proof.py prepare-brain \
  --source-published-sha 38356f100563da420c488ee6362917fd4f81b48b \
  --control-commit-sha <EXACT_CURRENT_AI_CONTROL_COMMIT_SHA> \
  --source-brain-id chatgpt-chat \
  --replacement-brain-id claude-chat \
  --output-dir <OFF_TASK_BRANCH_PROOF_DIR>
```

The resulting bounded pack may contain canonical state/request/capability/prompt artifacts only. No hidden reasoning, transcript, session data or secrets.

## Stage-A acceptance contract

Primary Brain will mark `M8_BRAIN_PROOF: PASS` only after exact verification proves:

```text
source controlled INCOMPLETE / M8-CONTROLLED-BRAIN-HANDOFF
source and replacement Brain IDs are distinct
same exact S0-bound canonical state fingerprint
source/replacement request equivalence under M3 failover semantics
valid canonical BrainFailoverProof
Brain B SUCCESS result exactly matches replacement request/output contract
BRAIN-DIAGNOSIS.md exact path/blob is verified
attestation contains no forbidden transcript/secrets
all persisted proof artifacts are on approved control storage, not task branch
```

After these conditions pass, Primary Brain will replace this review with the exact C7 provenance block and unlock Stage B Executor failover.

## Forbidden next actions

Do NOT yet run:

```text
/aios-worker FIX TASK-032 --executor claude-code
```

Do NOT create another commit on `ai/task-032` during Brain proof preparation/execution.

## Decision

`SEMANTIC PASS — ALL R1 FINDINGS CLOSED — LIVE BRAIN A -> B PROOF AUTHORIZED — EXECUTOR B STILL BLOCKED`
