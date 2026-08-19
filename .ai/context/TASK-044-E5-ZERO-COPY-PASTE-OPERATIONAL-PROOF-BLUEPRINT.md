# TASK-044 — E5 Zero-Copy/Paste Operational Proof — Implementation Blueprint

STATUS: LOCKED BLUEPRINT
BASELINE_MAIN_SHA: a01b5f4b028ccdc416004b3d25608d23fb922c51
TARGET_BRANCH: ai/task-044
MILESTONE: E5
EXECUTOR: codex
EXECUTOR_MODE: E4_AUTOMATED_REAL_TRANSPORT

## Contract Anchor

```text
ADR_PATH: .ai/decisions/ADR-033-E5-ZERO-COPY-PASTE-OPERATIONAL-PROOF-CONTRACT-LOCK.md
ADR_BLOB_SHA: b9f98dfd59d4785682ea5917052ca11be91274cd
```

## Blueprint Challenge

```text
BLUEPRINT_CHALLENGE: b60d55bc08ce25adab0658c10e4348a8
```

This value must appear exactly in the executor-created proof artifact. It must not be supplied to Codex outside the E3-delivered context pack.

## Purpose

TASK-044 is not an implementation task. It is one real operational proof of the already-merged E1-E4 stack.

The successful path is:

```text
Human approves TASK-044 for codex
  -> bridge.py execute 44
  -> E4 freezes exact TASK + ADR + this blueprint
  -> E3 builds bounded payload
  -> E2 invokes local Codex exactly once
  -> Codex creates exactly one proof file
  -> E4 verifies scope/trust
  -> E4 reuses existing publisher
  -> full repository suite
  -> RESULT-044 + commit + push
```

No manual executor prompt, `bridge.py context`, manual Codex command, or manual `bridge.py publish` belongs to the successful E5 path.

## Exact Allowed Executor File

Create exactly:

```text
.ai/proofs/E5-ZERO-COPY-PASTE-OPERATIONAL-PROOF.md
```

Do not modify any other worktree path.
Do not modify `.git/**` or Git configuration.
Do not commit, push, switch branch, stash, reset, clean, merge, or invoke another model/executor.
Do not run `bridge.py publish`.
Do not run `bridge.py approve`.
Do not invoke `codex` recursively.

## Exact File Content

Write this exact UTF-8 content, preserving the field values exactly:

```text
# E5 Zero-Copy/Paste Operational Proof

TASK_ID: TASK-044
PROOF_KIND: REAL_E4_CODEX_AUTOMATION
TASK_CHALLENGE: 723736ac142eb3afc6593e8328c584e5
ADR_CHALLENGE: a9eb3fa7b39555d964f0d03dfd74dcd6
BLUEPRINT_CHALLENGE: b60d55bc08ce25adab0658c10e4348a8
CHALLENGE_DIGEST_SHA256: 8661ac8bf8c0b8382a5161b746facb0d70fe6146ea6b20b06bf702d88dc16073
EXPECTED_DIRTY_PATH_COUNT: 1
```

A single final newline is allowed. Do not add explanation, timestamp, path, model name, runtime identity, fingerprint, stdout/stderr, secret, or chain-of-thought.

## Work Method

The executor may use only the minimum local filesystem action needed to create the exact file.

No repository exploration is required.
No production source needs to be read.
No tests need to be run by the executor; E4 publication owns the full repository suite.

After the file is created, STOP and return normally so E2 can emit an EXITED_ZERO transport receipt.

## Fail-Closed Rules

If the TASK/ADR/blueprint content received through the executor payload does not contain the exact three challenge values or the digest, do not guess. Exit nonzero or leave no worktree mutation.

If the target proof file already exists unexpectedly, do not overwrite unknown content; fail closed.

If any other worktree path must be modified to complete the task, fail closed.

## Acceptance Evidence Expected From E4

The executor does not fabricate these values. E4/Bridge must generate them independently in RESULT-044:

```text
E4_AUTO_EXECUTION: YES
E4_CONTEXT_MANIFEST_FINGERPRINT: <64-hex>
E4_INVOCATION_FINGERPRINT: <64-hex>
E4_INVOCATION_RECEIPT_FINGERPRINT: <64-hex>
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
E4_DIRTY_PATH_COUNT: 1
```

## Forbidden Scope

No changes to:

```text
bridge.py
src/**
tests/**
docs/**
.ai/tasks/**
.ai/reviews/**
.ai/decisions/**
.ai/context/**
.ai/results/**
.git/**
```

The only Executor-writable path is the exact `.ai/proofs/...` file above.

## E-Series Boundary

```text
E1 — Executor Invocation Contract          COMPLETE
E2 — Codex Local Transport                 COMPLETE
E3 — Bounded Context Pack Delivery         COMPLETE
E4 — Result Collection + Auto Publication  COMPLETE
E5 — Zero-Copy/Paste Operational Proof     ← THIS TASK
```

H-Series remains DEFERRED. M11 remains separate and is not part of TASK-044.
