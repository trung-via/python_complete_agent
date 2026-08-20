# TASK-059 — M11.3B Runtime Paid-API Proof Preflight + Canonical Provenance Lock

STATUS: READY
CLASS: L3 — SECURITY-CRITICAL PAID-API RUNTIME PREFLIGHT
MILESTONE: M11.3B
EXECUTOR_MODE: UNIFIED_AIOS_WORKER_DUAL_EXECUTOR

## Baseline

```text
MAIN_SHA: 0d7bddac2066ad508bf68fbb4d3bd8b69b18d1b3
TARGET_BRANCH: ai/task-059
```

## Purpose

Implement the no-spend runtime gate immediately before M11.3C.

TASK-059 must close the local-asset provenance gap, add a strict canonical MiniMax-M3 proof lock, harden the local input counter to require that lock, and add a Bridge `paid-proof-preflight` command that verifies real-proof readiness without dispatching, consuming a grant, or calling a provider.

## Authoritative Contracts

```text
ADR_036_PATH: .ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md
ADR_036_BLOB_SHA: cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc
REVIEW_058_PATH: .ai/reviews/REVIEW-058.md
REVIEW_058_BLOB_SHA: 04cd5b1199aeca3546e18d5052256cd6acd0eb33
BLUEPRINT_PATH: .ai/context/TASK-059-M11.3B-RUNTIME-PROOF-PREFLIGHT-AND-PROVENANCE-LOCK-BLUEPRINT.md
BLUEPRINT_BLOB_SHA: 53f0adce6cbb781b26c21cb29db02b0395d2ccb3
```

## Machine-Readable Executor Context

EXECUTOR_CONTEXT_REFS_JSON: [{"path":".ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md","blob_sha":"cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc"},{"path":".ai/context/TASK-059-M11.3B-RUNTIME-PROOF-PREFLIGHT-AND-PROVENANCE-LOCK-BLUEPRINT.md","blob_sha":"53f0adce6cbb781b26c21cb29db02b0395d2ccb3"},{"path":".ai/reviews/REVIEW-058.md","blob_sha":"04cd5b1199aeca3546e18d5052256cd6acd0eb33"}]

## Exact Writable Scope

EXECUTOR_ALLOWED_PATHS_JSON: ["bridge.py","src/aios_bridge/minimax_m3_proof_lock.py","src/aios_bridge/minimax_m3_input_counter.py","src/aios_bridge/paid_api_proof_preflight.py","tests/aios_bridge/test_minimax_m3_proof_lock.py","tests/aios_bridge/test_minimax_m3_input_counter.py","tests/aios_bridge/test_paid_api_proof_preflight.py","tests/test_bridge_paid_api_proof_preflight.py"]

Bridge-generated `.ai/results/RESULT-059.md` is publication output only.

## Executor Dispatch Policy

DISPATCH_EXECUTOR_POLICY_JSON: {"allow_paid_api":false,"candidates":[{"capacity_class":"SUBSCRIPTION","executor_id":"antigravity","preference_rank":0,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]},{"capacity_class":"SUBSCRIPTION","executor_id":"codex","preference_rank":1,"supported_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"],"supported_operations":["RUN"]}],"operation":"RUN","required_capabilities":["FILESYSTEM_WRITE","LOCAL_GIT","REPOSITORY_READ","SHELL","TEST_EXECUTION"]}

Human selects exactly one subscription Executor. No silent reroute, executor failover, paid Executor, or second executor.

## Core Requirement 1 — Canonical MiniMax-M3 Proof Lock

Create `src/aios_bridge/minimax_m3_proof_lock.py` exactly as locked in the blueprint.

Implement a frozen strict `MiniMaxM3ProofLock` with exact fields:

```text
schema_version = 1
provider_id = minimax
model_id = MiniMax-M3
endpoint_url
credential_env_name = MINIMAX_API_KEY
source_repository = MiniMaxAI/MiniMax-M3
source_revision = 3a41b311ffa5719cef48fed3974ccf2cc03733ea
chat_template_path = chat_template.jinja
chat_template_sha256
tokenizer_path = tokenizer.json
tokenizer_sha256
jinja2_version = 3.1.6
tokenizers_version = 0.23.1
requests_version = 2.32.3
```

Exact JSON field set, duplicate-key rejection, strict UTF-8, bounded values, canonical JSON, deterministic SHA-256 fingerprint.

Endpoint must be canonical HTTPS on exact host `api.minimax.io`, with no query/fragment/userinfo and only an explicitly audited MiniMax chat endpoint allowlist. Runtime CLI must never override it.

No secret value is stored in the lock.

## Core Requirement 2 — Counter Provenance Hardening

Modify `MiniMaxM3LocalProviderInputCounter` so constructor requires exact `MiniMaxM3ProofLock`.

```text
MANIFEST_ONLY_AUTHORITY: FORBIDDEN
DEFAULT_PROOF_LOCK: FORBIDDEN
CALLER_MAPPING_AS_LOCK: FORBIDDEN
EXACT_LOCK_TYPE: REQUIRED
```

Before Jinja/tokenizer engine construction, require manifest metadata/digests and actual file SHA-256 values to exactly equal the Git-bound proof lock.

Keep all existing symlink/path escape/size/UTF-8/sandbox/tokenizer security behavior and exact trusted-counter registry semantics.

## Core Requirement 3 — Offline Runtime Preflight Receipt

Create `src/aios_bridge/paid_api_proof_preflight.py` with strict frozen `PaidApiProofPreflightReceipt` and bounded pure receipt builder.

Receipt must bind all readiness evidence listed in the blueprint, including:

```text
task/grant/workspace/brain/provider/model
runtime main SHA
canonical control commit SHA
authorized artifact path/blob
proof lock path/blob/fingerprint
endpoint URL
credential source name + presence boolean only
source revision + asset digests
counter ID
exact package versions
logical external ledger target + readiness
grant_active = true
grant_consumed = false
paid_dispatch_enabled = false
provider_call_started = false
```

No secret, prompt, context, model output, raw provider body, absolute machine path, or timestamp in receipt.

## Core Requirement 4 — Bridge `paid-proof-preflight`

Add parser and command:

```text
python bridge.py paid-proof-preflight <task_id>
  --grant-id <grant-id>
  --proof-lock-path <canonical .ai/ path>
  --proof-lock-blob-sha <exact 40-hex blob>
```

No endpoint/provider/model/asset/ledger/workspace/credential-value override flags.

Implement the exact P0→P7 order in the blueprint:

```text
P0 clean local main == origin/main
P1 canonical control proof-lock exact blob
P2 existing exact ACTIVE Human grant + authorized artifact blob
P3 exact installed Jinja2/tokenizers/requests versions
P4 deterministic external asset directory + exact counter construction
P5 fixed MINIMAX_API_KEY presence-only check
P6 deterministic external JsonlUsageLedger target readiness via separate fsync probe
P7 bounded deterministic PASS receipt/output
```

Critical ordering requirement:

```text
proof-lock blob mismatch / invalid lock / grant mismatch / dependency mismatch /
asset failure MUST occur before reading credential presence whenever the prior
check can determine failure.
```

The preflight command MUST NOT call `count_request()`, dispatch Brain, consume grant, instantiate/invoke a real provider, append a fake UsageRecord, or perform network access.

Grant must remain ACTIVE after successful preflight.

## Runtime Paths

Add deterministic external paths through existing Bridge runtime root, at minimum logical equivalents of:

```text
paid_api_assets/minimax/MiniMax-M3/<source_revision>/
paid_api_usage/TASK-N/<sha256(grant_id)>.jsonl
```

No CLI overrides. Paths must remain outside the Git worktree.

Only a logical runtime-relative ledger path may enter the receipt/output; never print/persist the absolute user-specific runtime path as proof metadata.

## Credential Rules

Production preflight may check only presence of exact env name `MINIMAX_API_KEY` when the Human later invokes the command.

During TASK-059 E4 execution/tests, no real credential may be read.

Forbidden forever in receipt/output:

```text
secret value
secret hash
secret length
secret prefix/suffix
Authorization header
cookie
.env contents
```

No automatic dotenv loading.

## No-Spend Boundary

TASK-059 implementation/test execution must satisfy:

```text
REAL_MINIMAX_CALL: NO
REAL_PAID_API_CALL: NO
REAL_API_KEY_READ: NO
NETWORK: NO
ASSET_DOWNLOAD: NO
PACKAGE_INSTALL: NO
TOKEN_COUNT_ENDPOINT: NO
REAL_GRANT_CREATE: NO
REAL_GRANT_CONSUME: NO
PAID_DISPATCH: NO
M11.3C: NOT_STARTED
```

## Required Tests

Implement the complete blueprint matrix. At minimum prove:

```text
proof-lock exact parsing/constants/endpoint/credential/dependency/digest/fingerprint
counter exact lock required and manifest-only provenance rejected
manifest + actual template/tokenizer digests bound to lock
preflight clean-main and canonical control blob requirements
preflight existing ACTIVE exact Human grant only
expired/consumed/mismatched grant rejected
exact installed dependency versions required
external deterministic asset path only
counter constructs but count_request is never called
credential read occurs only after earlier security gates and never leaks secret
missing credential rejects
external deterministic ledger target readiness probe
probe never appends real UsageRecord
receipt contains no secret or absolute runtime path
successful preflight leaves grant ACTIVE
no provider/gateway/dispatch/network/mutation surface
parser exposes no security override flags
full repository tests pass
```

## Locked Source Anchors

```text
bridge.py                                      1870351fb18bb9224e5a91524b72d612205617f2
src/aios_bridge/minimax_m3_input_counter.py    304011b037a7eec38f5d19cd4854e83cc725ed4d
src/aios_bridge/paid_api_grant.py              7f1e1fe666154a9b17013a2cb084db9ce36f134f
src/aios_bridge/runtime_paid_api_grant.py      a3c7a446ff0f8195e68640493900776334a9e551
src/aios_bridge/paid_api_operational_proof.py  8425c49a571cbfa8959fb8c9d39b39100d3e4466
src/aios_bridge/external_brain/providers/minimax.py f907deeccf5d24ec80d4de58f7769330126f3624
src/aios_bridge/external_brain/transports/openai_compatible.py cd49451317f3e67479952b96fe3c9424fe8688c1
requirements.txt                               fa6c2618417bbd962f5927c305798a0a08917910
```

## Targeted Tests

```powershell
.\venv\Scripts\python.exe -m pytest `
  tests/aios_bridge/test_minimax_m3_proof_lock.py `
  tests/aios_bridge/test_minimax_m3_input_counter.py `
  tests/aios_bridge/test_paid_api_proof_preflight.py `
  tests/test_bridge_paid_api_proof_preflight.py -q
```

Executor runs targeted tests. Bridge publication owns full repository tests.

## Child Executor Role Lock

The Bridge E4-spawned process is the bounded implementation child, NOT the visible aios-worker operator UI.

```text
visible aios-worker UI = operator
Bridge E4 child        = implementation Executor
```

Child MUST implement now, modify only authorized paths, run targeted tests, leave authorized dirty delta, and exit normally.

Child MUST NOT invoke the worker adapter again, commit, push, publish, merge, install/download dependencies, access credentials, call providers/network, create/consume a real paid grant, or begin M11.3C.

## Explicit Out of Scope

```text
REAL PROOF LOCK ARTIFACT WITH PRODUCTION DIGESTS: NOT CREATED YET
REAL ASSET PROVISIONING: NOT YET
REAL MINIMAX API KEY SETUP: NOT YET
M11.3C REAL CALL: NOT YET
PAID SPEND: NOT AUTHORIZED
RETRY: FORBIDDEN
SECOND PAID PROVIDER: FORBIDDEN
EXECUTOR API: FORBIDDEN
H-SERIES: DEFERRED
```

## Completion Boundary

After implementation + Bridge publication:

```text
STOP
NEXT: Review TASK-059
```

Do not provision real assets, create the M11.3C Human grant, or call MiniMax automatically.
