# ADR-036 — M11 External API Escape Hatch Architecture Lock

STATUS: LOCKED
MILESTONE: M11 — EXTERNAL API ESCAPE HATCH
BASELINE_MAIN_SHA: 22a05d1f4880daf3a9f964e0564c658b051039cd

## Context

M10 already defines vendor-neutral deterministic dispatch with:

```text
CapacityClass.SUBSCRIPTION
CapacityClass.PAID_API
allow_paid_api: bool
```

A PAID_API candidate is incompatible when `allow_paid_api == false`. When paid API is allowed and multiple candidates are runnable, SUBSCRIPTION ranks before PAID_API.

The repository also already contains the External Brain API seam:

```text
ModelGateway
ProviderAdapter
MiniMaxOpenAIProvider
OpenAICompatibleTransport
UsageRecord / JsonlUsageLedger
```

The External Brain gateway performs one provider call and no retry.

By contrast, the merged Executor automation path is currently local-process oriented and E4 v1 invokes the local Codex transport. Creating a remote paid-API executor would require new remote execution / patch application / driver semantics.

## Decision

M11 v1 is a BRAIN-SIDE paid API escape hatch only.

It MUST NOT create a paid-API Executor transport.
It MUST NOT reinterpret a Brain API response as Executor worktree authority.
It MUST NOT apply model-generated patches automatically.
It MUST NOT activate H1-H5.

Paid API Executor support remains fail-closed and deferred until real workload evidence justifies the H-Series lifecycle/driver work.

## M11 Goal

M11 provides one explicit, bounded, Human-authorized way to permit a paid API Brain candidate only when subscription capacity is insufficient.

The intended control flow is:

```text
M10 recommendation policy may contain PAID_API Brain candidate
        ↓
DEFAULT: paid API forbidden
        ↓
Human explicitly grants one bounded paid-API Brain escape
        ↓
Runtime validates exact grant binding
        ↓
M10 BrainDispatchRequest.allow_paid_api = true
        ↓
M10 still prefers any runnable SUBSCRIPTION Brain
        ↓
Only if no runnable subscription candidate wins:
select explicitly granted PAID_API Brain
        ↓
Existing External Brain ModelGateway
        ↓
one provider call / no retry
        ↓
validated proposal artifact + usage telemetry
```

## Authority Invariants

```text
policy permits paid API != Human spend authorization
dispatch recommendation != authorization
paid API grant != executor authorization
Brain output != worktree authority
provider success != review PASS
usage telemetry != permission for another call
```

A TASK marker with `allow_paid_api: true` is never sufficient by itself to spend money.

Only a fresh Human runtime grant can unlock paid API dispatch.

## Default State

```text
PAID_API_DEFAULT: DENY
AUTO_ENABLE_FROM_TASK: FORBIDDEN
AUTO_ENABLE_FROM_DISPATCH: FORBIDDEN
AUTO_ENABLE_FROM_CAPACITY_EXHAUSTION: FORBIDDEN
AUTO_RETRY: FORBIDDEN
AUTO_FAILOVER_TO_SECOND_PAID_PROVIDER: FORBIDDEN
AUTO_EXECUTOR_API: FORBIDDEN
```

If the grant is missing, malformed, expired, consumed, mismatched, or cannot be durably verified, the effective `allow_paid_api` value is FALSE and the system fails closed.

## M11 Decomposition

### M11.1 — Paid API Grant Contract

Create a pure immutable contract that binds a one-shot Human grant to:

```text
grant_id
task_id
actor_kind = BRAIN
brain_id
provider_id
model_id
brain_operation
authorized_artifact_path
authorized_artifact_blob_sha
max_input_tokens
max_output_tokens
max_calls = 1
expires_at_epoch_seconds
workspace_id
grant_fingerprint
```

No secrets or API keys are stored in the grant.

M11.1 is pure contract/validation only. No network, no provider call, no filesystem mutation.

### M11.2 — Runtime Grant + Brain Escape Wiring

Add external runtime storage for ACTIVE/CONSUMED paid-API grants, analogous to existing external authorization/lease principles.

Human must explicitly create the grant through Bridge. Runtime wiring may set `BrainDispatchRequest.allow_paid_api = true` only after exact grant validation.

The selected paid Brain must exactly match the grant provider/model/operation/task/artifact/workspace binding.

Provider credentials remain environment/runtime secrets and never enter Git artifacts, grants, receipts, dispatch requests, fingerprints, RESULT files, or logs.

### M11.3 — Real Operational Escape Proof

Prove with fresh external capacity evidence:

```text
subscription Brain = QUOTA_EXHAUSTED or UNAVAILABLE
paid API Brain = AVAILABLE
valid unconsumed Human paid-API grant exists
```

Then prove:

```text
M10 selects PAID_API Brain
existing ModelGateway invoked exactly once
no retry
validated output artifact produced
usage telemetry produced
paid grant consumed exactly once
second attempt without new grant is rejected before provider call
no Executor authority created
```

A real paid provider call is permitted only after explicit Human authorization for the proof task.

## Budget Semantics

M11 v1 uses token/call bounds, not currency estimates.

Reason: currency pricing is provider/model/time dependent and must not be treated as a stable contract value.

Hard pre-call bounds:

```text
max_calls = 1
max_input_tokens > 0
max_output_tokens > 0
```

The request/context builder must prove it is within the grant bounds before provider invocation.

If exact pre-call input-token compliance cannot be proven under the active counter contract, fail closed.

Post-call provider token telemetry is recorded by the existing usage layer. Ledger failure must never authorize another call.

## Provider Scope

M11 does not add provider proliferation merely for architecture symmetry.

M11.3 may use the already-existing MiniMax adapter for real proof because it is the current concrete External Brain API provider.

Adding OpenAI/Anthropic/Gemini API providers is separate provider work and is not required for M11 PASS.

## Executor Boundary

The generic M10 dispatch contract may represent `CapacityClass.PAID_API` for Executor candidates, but M11 runtime MUST reject any attempt to exercise a paid-API Executor candidate.

```text
PAID_API_BRAIN: SUPPORTED BY M11
PAID_API_EXECUTOR: UNSUPPORTED / FAIL_CLOSED
```

This preserves E1-E5 and avoids prematurely implementing H4 Provider Lifecycle or H5 Driver Contract.

## Security / Secret Rules

Forbidden in all Git/control/runtime evidence artifacts except the provider process environment itself:

```text
api_key
Authorization header
Bearer token
cookie
raw provider request body containing secrets
raw provider response containing hidden reasoning
```

Fingerprints bind metadata and artifact identities, not credentials.

## Failure Semantics

Any of the following must fail before provider call:

```text
no grant
grant expired
grant consumed
grant fingerprint mismatch
wrong task
wrong workspace
wrong authorized artifact/blob
wrong operation
wrong brain/provider/model
requested input/output budget exceeds grant
paid API policy absent/false
selected candidate is Executor
```

After a provider call starts:
- no automatic retry;
- no automatic second provider;
- no grant refresh;
- no automatic executor invocation;
- preserve usage/evidence fail-closed.

## H-Series Boundary

H-Series remains exactly:

```text
H1 — Event Journal
H2 — Capability Seams
H3 — Execution Envelope
H4 — Provider Lifecycle
H5 — Driver Contract
STATUS: DEFERRED
TRIGGER: evidence from real Python Agent workloads
```

M11 MUST NOT activate these merely for architectural neatness.

## Completion

M11 is complete only when M11.1, M11.2, and M11.3 independently PASS and the operational proof demonstrates a one-shot Human-authorized paid API Brain escape with no Executor authority leakage.

Only Human authorizes any real paid API call and any merge.
