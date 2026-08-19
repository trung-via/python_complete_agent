# ADR-031 — E3 Bounded Executor Context Pack Contract Lock

STATUS: LOCKED

## Context

E1 / ADR-029 established the vendor-neutral `ExecutorInvocation` payload identity contract.
E2 / ADR-030 established the concrete local Codex transport that delivers exact payload bytes through stdin.

E3 defines how AIOS deterministically composes those payload bytes from already-bound execution/control artifacts.

```text
E1 — Executor Invocation Contract                  COMPLETE
E2 — Codex Local Transport                         COMPLETE
E3 — Bounded Context Pack Delivery                 THIS ADR
E4 — Result Collection + Auto Publication
E5 — Zero-Copy/Paste Operational Proof
```

E3 does NOT invoke Codex and does NOT integrate with `bridge.py`.
E3 does NOT grant Human authorization.
E3 does NOT implement the deferred H3 Execution Envelope.

---

## Decision 1 — Reuse Existing Canonical Primitives

E3 SHALL reuse, without modifying:

- M4 `ExecutionRequest` and `PreparedExecution`;
- M4 `ArtifactRef` through `ExecutionRequest.work_ref/context_refs`;
- M5 `ExecutorLease`;
- E1 `ExecutorInvocation`, `validate_executor_invocation`, and `validate_invocation_payload`.

E3 MUST NOT create a parallel generic execution-envelope framework or a second artifact-pointer model.

---

## Decision 2 — One Pure Composer Outside Continuity Core

E3 SHALL add:

```text
src/aios_bridge/executor_context.py
```

This module is an E-Series payload composer. It is not a new Continuity Core contract and is not H3.

The module SHALL perform no filesystem, Git, subprocess, network, Bridge-runtime, provider, or model I/O.

All control-artifact bytes are supplied explicitly by the caller.

---

## Decision 3 — Minimal Authorization Evidence Binding, Not Authority

E3 SHALL define an immutable `ExecutorAuthorizationBinding` carrying only the minimal non-secret fields required to bind a context pack to the already-existing Human-approved runtime boundary:

```text
schema_version
task_id
operation
executor_id
target_branch
artifact_path
artifact_blob_sha
lease_id
lease_fingerprint
workspace_id
execution_fingerprint
status = ACTIVE
```

The binding is evidence only.

`ExecutorAuthorizationBinding` MUST NOT:
- create approval;
- infer approval;
- approve RUN/FIX/MERGE;
- select an executor;
- acquire/release a lease;
- contain approval tokens, secrets, cookies, API keys, timestamps, model/session IDs, or merge permission.

A future E4 caller is solely responsible for constructing this binding from the exact active Bridge authorization record after independently verifying Human authority.

The pack itself SHALL state that it does not grant or extend authority.

---

## Decision 4 — Exact Relational Binding

Before rendering any payload, E3 SHALL mechanically validate:

1. `PreparedExecution` matches `ExecutionRequest`.
2. authorization binding `task_id`, `operation`, `executor_id`, `target_branch` match the request.
3. authorization `artifact_path/blob_sha` match `ExecutionRequest.work_ref.path/blob_sha` exactly.
4. authorization `lease_id`, `lease_fingerprint`, `workspace_id`, `execution_fingerprint` match the exact `ExecutorLease`.
5. lease task/executor/operation binding matches the request/binding.
6. no authority field is inferred from recommendation, transport, or artifact content.

Any mismatch fails closed before payload construction.

---

## Decision 5 — Artifact Set Is Exactly the Request Artifact Set

The exact E3 artifact sequence is:

```text
1. ExecutionRequest.work_ref
2. ExecutionRequest.context_refs in their existing request order
```

The caller supplies:

```python
artifact_payloads: Mapping[str, bytes]
```

The key set MUST equal the exact artifact paths above.

No missing artifact.
No extra artifact.
No duplicate path.
No directory scan.
No nearest-match lookup.
No fallback to a similarly named TASK/REVIEW/ADR/blueprint.

For RUN, `work_ref` remains the exact TASK artifact required by M4.
For FIX, `work_ref` remains the exact REVIEW artifact required by M4.

---

## Decision 6 — Exact Git Blob Verification

Each supplied artifact payload SHALL be exact non-empty `bytes`.

E3 SHALL recompute the canonical Git blob SHA-1:

```text
SHA1(b"blob " + decimal_byte_length + b"\0" + exact_content_bytes)
```

and require it to equal `ArtifactRef.blob_sha` exactly.

This proves the bytes embedded into the context pack are the bytes named by the canonical artifact ref.

E3 SHALL additionally compute SHA-256 and byte size for the pack manifest.

No newline conversion, trimming, BOM removal, Unicode normalization, content rewriting, or Markdown cleanup is allowed.

---

## Decision 7 — Text Safety Without Mutation

Every artifact must be valid UTF-8 and MUST NOT contain NUL bytes.

Validation decodes only to prove UTF-8 validity; rendering SHALL preserve the original exact bytes.

Invalid UTF-8 or NUL-containing artifacts fail closed.

E3 does not sanitize or repair trusted control artifacts.

---

## Decision 8 — Low-Token Hard Bounds

E3 SHALL be materially tighter than the E1 1 MiB transport ceiling.

Locked bounds:

```text
MAX_CONTEXT_ARTIFACTS = 8
MAX_CONTEXT_ARTIFACT_BYTES = 131072          # 128 KiB each
MAX_CONTEXT_RAW_ARTIFACT_BYTES = 196608      # 192 KiB aggregate
MAX_CONTEXT_PACK_BYTES = 262144              # 256 KiB final payload
```

The final payload MUST also remain within E1 `MAX_INVOCATION_PAYLOAD_BYTES`.

E3 MUST NOT truncate, summarize, omit, compress, or silently reduce an oversized artifact set.
It fails closed so the Primary Brain/Human can deliberately reduce the control context.

These limits are operational/context-budget controls, not a claim about model token count.

---

## Decision 9 — Deterministic Manifest

E3 SHALL define immutable manifest models with deterministic canonical JSON.

Each artifact manifest entry contains exactly:

```text
role              # WORK or CONTEXT
ordinal
path
ref
blob_sha
content_sha256
size_bytes
```

The context-pack manifest contains exactly the non-secret execution/binding identity required to reproduce the pack:

```text
schema_version
format_version = aios-executor-context-v1
instruction_profile = thin-executor-v1
task_id
operation
request_id
executor_id
transport_id
target_branch
workspace_id
execution_id
request_fingerprint
prepared_execution_fingerprint
lease_id
lease_fingerprint
execution_fingerprint
authorization_binding_fingerprint
expected_task_head_sha
expected_result_path
required_capabilities
artifacts
```

Manifest canonical JSON uses:

```python
json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False)
```

`manifest_fingerprint = SHA256(canonical_manifest_json UTF-8)`.

No timestamps, random values, host paths, usernames, environment data, session IDs, model prose, or dynamic system state are permitted in the manifest.

---

## Decision 10 — Deterministic Human/Model-Readable Payload Format

E3 SHALL render one deterministic UTF-8 payload in this conceptual order:

```text
AIOS_EXECUTOR_CONTEXT_PACK_V1
<fixed authority/scope notice>
<fixed thin-executor operating instructions>
MANIFEST_SHA256: <manifest fingerprint>
MANIFEST_JSON: <canonical JSON on one line>

ARTIFACT 0 BEGIN
ROLE: WORK
PATH: ...
REF: ...
BLOB_SHA: ...
CONTENT_SHA256: ...
SIZE_BYTES: ...
CONTENT_BEGIN
<exact artifact bytes>
CONTENT_END
ARTIFACT 0 END

... context artifacts in exact request order ...

AIOS_EXECUTOR_CONTEXT_PACK_END
```

The fixed instruction block SHALL tell the executor:
- this pack itself does not grant or extend authority;
- obey the exact WORK artifact and bounded CONTEXT artifacts;
- do not redesign beyond them;
- do not self-select an executor;
- do not commit, push, publish, merge, or mutate Bridge/authorization/lease state;
- run only executor-side targeted tests authorized by the control artifacts;
- stop after bounded implementation/testing and report to the caller.

The renderer MUST NOT interpolate arbitrary caller prose.
There is no `extra_prompt`, `system_prompt`, or free-form instruction override in E3 v1.

---

## Decision 11 — Content-Addressed E1 Invocation Output

E3 SHALL accept explicit canonical:

```text
invocation_id
transport_id
```

and produce an `ExecutorInvocation` whose:

```text
payload_sha256 = SHA256(exact rendered payload bytes)
payload_size_bytes = len(exact rendered payload bytes)
```

All remaining invocation identity SHALL be copied mechanically from the exact request/prepared/lease objects.

After construction E3 MUST call:

```python
validate_executor_invocation(...)
validate_invocation_payload(invocation, payload)
```

The returned pack/bundle SHALL therefore be directly consumable by any matching E1 `ExecutionTransport`, including E2 `CodexLocalTransport`, without payload rewriting.

E3 itself MUST NOT call `transport.invoke()`.

---

## Decision 12 — Determinism Requirement

For identical:
- execution request;
- prepared execution;
- executor lease;
- authorization binding;
- invocation ID;
- transport ID;
- exact artifact bytes;

E3 MUST return byte-identical payload, identical manifest fingerprint, identical payload SHA-256, and identical E1 invocation fingerprint across repeated calls.

Mapping insertion order MUST NOT affect output.
Locale, OS, current time, working directory, environment, and Python hash randomization MUST NOT affect output.

---

## Decision 13 — Security / Scope Boundaries

E3 MUST NOT:
- read `.env` or environment variables;
- include API keys/tokens/cookies;
- include arbitrary repo files not named by `ExecutionRequest`;
- follow symlinks or paths;
- run Git;
- call Codex;
- call model/provider SDKs;
- use browser/network/HTTP;
- inspect session/history;
- commit/push/publish/merge;
- change Human authorization;
- acquire/release lease;
- modify dispatcher/failover/hot-handoff;
- implement M11;
- implement H1-H5.

---

## Decision 14 — Required Tests

Required positive coverage:
- valid RUN pack;
- valid FIX pack;
- exact artifact ordering;
- exact Git blob verification;
- exact raw artifact byte preservation;
- deterministic manifest JSON/fingerprint;
- deterministic final payload bytes;
- mapping insertion order independence;
- exact E1 invocation payload SHA/size binding;
- E1 `validate_executor_invocation` and `validate_invocation_payload` pass;
- authority binding/lease/request relational validation;
- exact fixed thin-executor instruction block.

Required adversarial coverage:
- missing artifact;
- extra artifact;
- wrong Git blob bytes;
- empty bytes;
- bytearray/non-bytes;
- invalid UTF-8;
- NUL byte;
- >8 artifacts;
- per-artifact limit exceeded;
- aggregate raw limit exceeded;
- final pack limit exceeded;
- authorization artifact mismatch;
- authorization task/action/executor/branch mismatch;
- authorization non-ACTIVE status;
- authorization lease ID/fingerprint/workspace/execution mismatch;
- prepared/request mismatch;
- malformed invocation/transport IDs;
- no payload truncation;
- no free-form caller prompt field;
- no filesystem/Git/subprocess/network/provider/Bridge runtime imports or calls.

Full repository suite remains Bridge publication gate.

---

## Decision 15 — Expected Implementation Boundary

Allowed production file:

```text
src/aios_bridge/executor_context.py
```

Expected tests:

```text
tests/aios_bridge/test_executor_context_pack.py
```

Bridge publication may generate:

```text
.ai/results/RESULT-042.md
```

No E1/E2/M4/M5/Bridge file modification is expected.

---

## E3 Acceptance

```text
REUSES_M4_ARTIFACT_REFS: PASS
REUSES_E1_INVOCATION: PASS
AUTHORIZATION_BINDING_IS_EVIDENCE_ONLY: PASS
REQUEST_PREPARED_LEASE_AUTH_BINDING: PASS
EXACT_ARTIFACT_SET: PASS
GIT_BLOB_BYTE_IDENTITY: PASS
UTF8_NO_MUTATION: PASS
LOW_TOKEN_BOUNDS: PASS
NO_TRUNCATION_OR_SUMMARIZATION: PASS
DETERMINISTIC_MANIFEST: PASS
DETERMINISTIC_PAYLOAD: PASS
PAYLOAD_CONTENT_ADDRESSED: PASS
E1_INVOCATION_VALIDATED: PASS
NO_REAL_TRANSPORT_INVOCATION: PASS
NO_BRIDGE_INTEGRATION: PASS
H_SERIES_REMAINS_DEFERRED: PASS
FULL_REPO_TESTS: PASS
REGRESSIONS: 0
FINAL_INDEPENDENT_AUDIT: PASS
E3: PASS
```

E3 PASS does NOT mean zero-copy/paste workflow is operational yet.
E4 may then wire exact runtime authorization + local artifact loading + E3 composition + E2 invocation + bounded result collection/publication under unchanged Human authority.
