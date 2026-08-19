# ADR-033 — E5 Zero-Copy/Paste Operational Proof Contract Lock

STATUS: LOCKED
MILESTONE: E5 — ZERO-COPY/PASTE OPERATIONAL PROOF
BASELINE_MAIN_SHA: a01b5f4b028ccdc416004b3d25608d23fb922c51
TARGET_TASK: TASK-044
TARGET_BRANCH: ai/task-044

## Decision

E5 is a proof-only milestone. It introduces no new runtime architecture and changes no E1/E2/E3/E4/M1/M4/M5/M10 contract.

E5 must prove one real Human-authorized Codex execution through the merged E4 path:

```text
Human approve
  -> existing ACTIVE authorization + ACTIVE lease
  -> bridge.py execute 44
  -> exact frozen TASK/ADR/blueprint bytes
  -> E3 bounded context pack
  -> E2 real local Codex transport
  -> one allowed proof-file mutation
  -> E4 Git/scope/publication-trust gates
  -> existing cmd_publish full repository suite
  -> RESULT-044 + commit + push
  -> independent ChatGPT review
```

The Human must not manually copy/paste an executor prompt, manually run `bridge.py context 44`, manually invoke Codex, or manually run `bridge.py publish 44` on the successful E5 happy path.

Human authorization remains mandatory. `approve` and later merge authorization are not automated.

## Proof Challenges

E5 uses independent challenge values embedded in three exact Human-approved control artifacts.

```text
TASK_CHALLENGE: 723736ac142eb3afc6593e8328c584e5
ADR_CHALLENGE: a9eb3fa7b39555d964f0d03dfd74dcd6
BLUEPRINT_CHALLENGE: b60d55bc08ce25adab0658c10e4348a8
```

The proof artifact must contain all three exact challenge values and this exact digest:

```text
CHALLENGE_DIGEST_SHA256: 8661ac8bf8c0b8382a5161b746facb0d70fe6146ea6b20b06bf702d88dc16073
```

The digest is SHA-256 over the exact UTF-8 bytes of:

```text
723736ac142eb3afc6593e8328c584e5|a9eb3fa7b39555d964f0d03dfd74dcd6|b60d55bc08ce25adab0658c10e4348a8
```

The challenge mechanism is evidence that the executor received the active TASK work artifact plus both ordered context artifacts through the E3 payload. It does not create authorization.

## Exact Executor Mutation

Codex may create exactly one worktree path:

```text
.ai/proofs/E5-ZERO-COPY-PASTE-OPERATIONAL-PROOF.md
```

No production code, test code, configuration, Git administration, other documentation, task, review, decision, context, or result file may be modified by Codex.

`RESULT-044.md` remains Bridge-generated only.

## Exact Proof Artifact

The executor-created file must be UTF-8 text with exactly this semantic payload and no fabricated runtime identities:

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

No timestamp, random value, model prose, token, secret, local absolute path, stdout/stderr, chain-of-thought, or guessed Git/lease/invocation fingerprint is allowed in the proof artifact.

## Real Transport Requirement

E5 acceptance requires the normal production `CodexLocalTransport` invoked by `bridge.py execute 44`.

No fake/mocked transport, manual Codex UI/session, manual `codex exec`, or direct subprocess substitute is valid E5 proof.

The executor must not commit, push, publish, merge, switch branch, alter HEAD, modify `.git/**`, or retry itself.

## Publication Evidence

The Bridge-generated RESULT-044 must mechanically include E4 automatic execution evidence produced by the merged E4 code path, including at minimum:

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

The full repository suite must be executed by E4's existing publisher and pass with zero failures.

The task branch must remain a fast-forward descendant of baseline main and contain only:

```text
.ai/proofs/E5-ZERO-COPY-PASTE-OPERATIONAL-PROOF.md
.ai/results/RESULT-044.md
```

relative to baseline main.

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

Only the Human authorizes RUN and MERGE and chooses `codex` as executor.

## Failure Semantics

Any failure before or after real invocation follows existing E4 fail-closed behavior. E5 must not add retry, fallback, cleanup, repair, force push, auto merge, or alternate publication logic.

If `bridge.py execute 44` fails, E5 remains NOT PROVEN. Human recovery must follow the existing E4 state/evidence without inventing proof from partial execution.

## Forbidden Scope

E5 must not:
- modify `bridge.py` or any runtime module;
- modify E1/E2/E3/E4/M1/M4/M5/M10 contracts;
- add another transport/provider/driver/envelope/event journal;
- implement M11;
- activate H1/H2/H3/H4/H5;
- add automatic approval, executor selection, retry, publication implementation, or merge;
- infer zero-copy proof from prose alone.

## Acceptance

E5 passes only after independent ChatGPT review mechanically proves:

```text
REAL_CODEX_E2_INVOCATION_PATH: PASS
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
E5: PASS
```

E5 PASS does not merge automatically. Human merge authorization remains required.
