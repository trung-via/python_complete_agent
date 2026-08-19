# TASK-046 — E5 Zero-Copy/Paste Operational Proof #2 — Implementation Blueprint

STATUS: LOCKED BLUEPRINT
BASELINE_MAIN_SHA: 7b4e8bbe1322c0e26338071ca3be7bf08a3144ec
TARGET_BRANCH: ai/task-046
MILESTONE: E5
EXECUTOR: codex
EXECUTOR_MODE: E4_AUTOMATED_REAL_TRANSPORT

## Contract Anchor

```text
ADR_PATH: .ai/decisions/ADR-035-E5-SECOND-ZERO-COPY-OPERATIONAL-PROOF-CONTRACT-LOCK.md
ADR_BLOB_SHA: 3e2881b5710c4af85594a6fe9f2f963397dfbd83
```

## Baseline Transport Anchor

Merged E2.1 production transport:

```text
PATH: src/aios_bridge/executor_transports/codex_local.py
BLOB_SHA: b3a2c29fae7acab549bf26d0c621117923037375
EXPECTED_GLOBAL_FLAG_ORDER: codex --ask-for-approval never exec ...
```

## Blueprint Challenge

```text
BLUEPRINT_CHALLENGE: 17aab42d282621a9f2d1e89f93887da3
```

This value must reach Codex only through the E3-delivered context pack for TASK-046.

## Purpose

TASK-046 is a real operational proof of the already-merged E1/E2/E2.1/E3/E4 stack. It requests no runtime implementation.

Successful path:

```text
Human approve TASK-046 for codex
  -> bridge.py execute 46
  -> E4 freezes exact TASK + ADR + this blueprint
  -> E3 builds bounded payload
  -> E2.1 launches local Codex exactly once
  -> Codex creates exactly one proof file
  -> E4 verifies branch/HEAD/scope/publication trust
  -> E4 invokes existing publisher
  -> full repository suite
  -> RESULT-046 + commit + push
```

No manual executor prompt, `bridge.py context`, manual Codex command, or manual `bridge.py publish` belongs to the successful path.

## Exact Allowed Executor File

Create exactly:

```text
.ai/proofs/E5-ZERO-COPY-PASTE-OPERATIONAL-PROOF-046.md
```

Do not modify any other worktree path.
Do not modify Git administration or Git configuration.
Do not commit, push, switch branch, stash, reset, clean, merge, publish, retry, or invoke another model/executor.

## Exact File Content

Write exactly this UTF-8 semantic content:

```text
# E5 Zero-Copy/Paste Operational Proof #2

TASK_ID: TASK-046
PROOF_KIND: REAL_E4_CODEX_AUTOMATION_AFTER_E2_1
TASK_CHALLENGE: eaddcdd98c49d5c298f2b22dcf3244fe
ADR_CHALLENGE: ee4b936f9d1394f00af734bae19bc34f
BLUEPRINT_CHALLENGE: 17aab42d282621a9f2d1e89f93887da3
CHALLENGE_DIGEST_SHA256: 0c3e1100d0abf6c249e013fd774823d91ec8472dbb51b24356013e5f729cabbf
EXPECTED_DIRTY_PATH_COUNT: 1
```

A single final newline is allowed. Add nothing else.

## Work Method

Use only the minimum local filesystem operation needed to create the exact file.

No repository exploration is needed.
No production source needs to be read.
No tests should be run by Codex; E4 publication owns the full suite.

After the file is written, return normally so E2.1 can emit an EXITED_ZERO transport receipt.

## Fail-Closed Rules

If the TASK/ADR/blueprint payload does not contain all exact challenge values and the digest, do not guess.

If the proof file already exists unexpectedly, do not overwrite unknown content.

If completion requires any second worktree path, fail closed.

## Expected E4 Evidence

Do not fabricate these values. E4/Bridge must independently place them in RESULT-046:

```text
E4_AUTO_EXECUTION: YES
E4_CONTROL_COMMIT_SHA: <40-hex>
E4_CONTEXT_MANIFEST_FINGERPRINT: <64-hex>
E4_INVOCATION_FINGERPRINT: <64-hex>
E4_INVOCATION_RECEIPT_FINGERPRINT: <64-hex>
E4_TRANSPORT_STATUS: EXITED_ZERO
E4_ALLOWED_SCOPE_VERIFIED: PASS
E4_PUBLICATION_TRUST_VERIFIED: PASS
E4_DIRTY_PATH_COUNT: 1
```

## Forbidden Scope

No executor changes to:

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
.ai/proofs/E5-ZERO-COPY-PASTE-OPERATIONAL-PROOF.md
.git/**
```

The only writable path is `.ai/proofs/E5-ZERO-COPY-PASTE-OPERATIONAL-PROOF-046.md`.

Do not modify or retry TASK-044.
Do not implement M11 or H1-H5.

## Completion

After creating the exact proof file, STOP. Do not commit, push, publish, run tests, or invoke another executor.