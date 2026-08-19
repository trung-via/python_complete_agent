# ADR-035 — E5 Second Zero-Copy/Paste Operational Proof Contract Lock

STATUS: LOCKED
MILESTONE: E5 — ZERO-COPY/PASTE OPERATIONAL PROOF #2
BASELINE_MAIN_SHA: 7b4e8bbe1322c0e26338071ca3be7bf08a3144ec
TARGET_TASK: TASK-046
TARGET_BRANCH: ai/task-046

## Context

TASK-044 was the first real E5 attempt. It reached the real E2 Codex transport but failed before any worktree mutation because Codex CLI 0.147.0 rejected the placement of the global `--ask-for-approval` flag after the `exec` subcommand.

TASK-045 / E2.1 corrected only that parser-boundary defect and was independently reviewed PASS and merged to main at the baseline SHA above.

TASK-044 remains failed evidence and MUST NOT be reused, retried, manually published, or retroactively converted into E5 PASS.

## Decision

E5 attempt #2 is proof-only. It introduces no runtime architecture and changes no E1/E2/E2.1/E3/E4/M1/M4/M5/M10 contract.

The only valid successful path is:

```text
Human approve TASK-046 for codex
  -> ACTIVE authorization + ACTIVE lease
  -> bridge.py execute 46
  -> one frozen TASK/ADR/blueprint control snapshot
  -> E3 bounded context pack
  -> real merged E2.1 CodexLocalTransport
  -> exactly one executor-created proof file
  -> E4 Git/scope/publication-trust gates
  -> existing cmd_publish full repository suite
  -> RESULT-046 + commit + push
  -> independent ChatGPT review
```

The successful path MUST NOT include manual `bridge.py context 46`, a manually pasted Codex prompt, manual `codex exec`, or manual `bridge.py publish 46`.

Human RUN authorization and Human merge authorization remain mandatory and separate.

## Fresh Proof Challenges

These challenge values are new and unrelated to TASK-044:

```text
TASK_CHALLENGE: eaddcdd98c49d5c298f2b22dcf3244fe
ADR_CHALLENGE: ee4b936f9d1394f00af734bae19bc34f
BLUEPRINT_CHALLENGE: 17aab42d282621a9f2d1e89f93887da3
```

Exact digest:

```text
CHALLENGE_DIGEST_SHA256: 0c3e1100d0abf6c249e013fd774823d91ec8472dbb51b24356013e5f729cabbf
```

The digest is SHA-256 over the exact UTF-8 bytes:

```text
eaddcdd98c49d5c298f2b22dcf3244fe|ee4b936f9d1394f00af734bae19bc34f|17aab42d282621a9f2d1e89f93887da3
```

The challenge mechanism is evidence that Codex received the exact active TASK plus both ordered context artifacts through E3. It does not create or imply authorization.

## Exact Executor Mutation

Codex may create exactly one worktree path:

```text
.ai/proofs/E5-ZERO-COPY-PASTE-OPERATIONAL-PROOF-046.md
```

No other executor mutation is authorized. `RESULT-046.md` remains Bridge-generated only.

## Exact Proof Artifact

The executor-created file must contain exactly this semantic payload:

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

A single final newline is allowed. No timestamp, random value, model prose, local absolute path, stdout/stderr, token, secret, chain-of-thought, guessed Git SHA, lease ID, invocation ID, or fingerprint may be added.

## Real Transport Requirement

Acceptance requires the production `CodexLocalTransport` from merged main, including the E2.1 argv correction:

```text
codex --ask-for-approval never exec ...
```

No fake/mocked transport, manual Codex UI/session, manual `codex exec`, or alternate subprocess is valid proof.

Codex must not commit, push, publish, merge, switch branch, alter HEAD, modify Git administration, invoke another executor/model, or retry itself.

## E4 Publication Evidence

Bridge-generated RESULT-046 must mechanically contain at least:

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

E4 must run the existing fixed full repository suite and obtain exit code 0.

Relative to baseline main, the task branch may contain exactly:

```text
.ai/proofs/E5-ZERO-COPY-PASTE-OPERATIONAL-PROOF-046.md
.ai/results/RESULT-046.md
```

## Authority Invariants

```text
recommendation != authorization
authorization != lease
lease != invocation
invocation != receipt
receipt != task success
publication != review PASS
review PASS != merge authorization
```

Only the Human authorizes RUN/MERGE and selects `codex`.

## Failure Semantics

Any failure follows existing E4 fail-closed behavior. No retry, fallback, cleanup, repair, force push, manual proof substitution, alternate publication path, or auto merge may be added.

If `bridge.py execute 46` fails, TASK-046 remains NOT PROVEN and must not be manually completed to manufacture E5 evidence.

## Forbidden Scope

E5 attempt #2 must not:
- modify `bridge.py` or any runtime/test module;
- modify E1/E2/E2.1/E3/E4/M1/M4/M5/M10 contracts;
- modify TASK-044 failed evidence;
- implement M11;
- activate H1/H2/H3/H4/H5;
- add automatic approval, automatic executor selection, retry/fallback, or auto merge.

## Acceptance

E5 passes only after independent review proves:

```text
BASELINE_INCLUDES_E2_1_FIX: PASS
REAL_CODEX_E2_1_INVOCATION_PATH: PASS
E3_WORK_REF_CHALLENGE_DELIVERED: PASS
E3_ADR_CONTEXT_CHALLENGE_DELIVERED: PASS
E3_BLUEPRINT_CONTEXT_CHALLENGE_DELIVERED: PASS
CHALLENGE_DIGEST: PASS
ONLY_ONE_EXECUTOR_DIRTY_PATH: PASS
E4_AUTO_EXECUTION_RESULT_EVIDENCE: PASS
E4_TRANSPORT_EXITED_ZERO: PASS
E4_SCOPE_GATE: PASS
E4_PUBLICATION_TRUST_GATE: PASS
FULL_REPO_TESTS: PASS
RESULT_COMMIT_PUSH: PASS
MANUAL_CONTEXT_COMMAND_REQUIRED: NO
MANUAL_EXECUTOR_PROMPT_COPY_PASTE_REQUIRED: NO
MANUAL_CODEX_INVOCATION_REQUIRED: NO
MANUAL_PUBLISH_REQUIRED: NO
HUMAN_RUN_AUTHORIZATION_REQUIRED: YES
HUMAN_MERGE_AUTHORIZATION_REQUIRED: YES
FINAL_INDEPENDENT_AUDIT: PASS
E5: PASS
```

E5 PASS does not merge automatically.