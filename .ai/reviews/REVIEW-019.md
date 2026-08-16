# REVIEW-019 — TASK-019 Canonical Project State

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `1`
- Reviewed branch: `ai/task-019`
- Reviewed branch head: `3d91bfe33147035b4818cc4748fa2afad14f1b98`
- Tested implementation SHA recorded by RESULT: `aab496eaa5d612406e1d1b365b040ca89042e5e5`
- Base main: `689c2c6dd8e41fe0f735b822118ba6530379b7dd`
- Branch relation: ahead `2`, behind `0`; merge-base is exact current main.
- Implementation-to-reviewed-head relation: one evidence-only RESULT commit; production code/tests at reviewed head equal tested implementation.

## Decision
TASK-019 is **not yet approved**. The overall namespace separation, immutable schema model, canonical serialization/fingerprint, explicit-observation freshness model, CLI scope, and test isolation are directionally correct, but several fail-closed requirements from ADR-011/TASK-019 are not enforced exactly.

## Required Changes

### 1. BLOCKER — 16 KiB cap is not enforced by parser/constructor
ADR-011/TASK-019 require parser/constructor validation to fail closed when canonical state exceeds `MAX_SERIALIZED_BYTES = 16384`.

Current behavior permits an oversized `ContinuityState` to be successfully created by `ContinuityState.from_dict(...)`; the size error occurs only later when `to_canonical_json()` is called. The focused test explicitly encodes that behavior by constructing the oversized state successfully first.

Required fix:
- make construction/parsing fail closed for oversized canonical state, including `from_dict(...)` and direct `ContinuityState(...)` construction;
- keep `from_json(...)` raw-input cap;
- avoid recursion by using a private unchecked canonical-byte helper if necessary;
- add regression tests proving oversized `from_dict(...)` and direct constructor fail before a usable state object is returned.

### 2. BLOCKER — artifact role paths are validated only by filename/stem, not canonical namespace
ADR-011 locks the active task artifact to `.ai/tasks/TASK-NNN.md`, result to `.ai/results/RESULT-NNN.md`, and review to `.ai/reviews/REVIEW-NNN.md`.

Current implementation checks only the task filename and result/review stem after the generic `.ai/` path check. Therefore values such as `.ai/context/TASK-019.md`, `.ai/context/RESULT-019.md`, or `.ai/context/REVIEW-019.md` can satisfy identity validation even though they are the wrong artifact roles.

Required fix:
- enforce exact role namespace + task identity for TASK/RESULT/REVIEW pointers;
- preserve plan/context behavior from ADR-011;
- add negative tests for correct filename in the wrong `.ai/...` directory.

### 3. BLOCKER — sensitive-path rejection can be bypassed by common document extensions and sensitive parent directories
The security contract forbids references to sensitive/secret-bearing paths, not only secret file extensions.

Current validator scans sensitive keywords only in the basename and explicitly allows keyword-bearing names when they end in `.md`, `.json`, `.yaml`, `.yml`, or `.sql`. It also does not reject sensitive parent components when the basename itself looks harmless. This can allow examples such as `.ai/context/token.json` or `.ai/secrets/plan.md`.

Required fix:
- fail closed on clearly sensitive path components/names regardless of common document extension;
- inspect relevant path components, not basename only;
- retain explicit `.env` / key-extension / SSH-key rejection;
- add regression tests for at least a keyword-bearing JSON/Markdown name and a sensitive parent directory.

### 4. REQUIRED HARDENING — Git ref validation is more permissive than a safe Git ref contract
`_BRANCH_REF_PATTERN` plus the current checks still permits malformed Git refs such as double-slash components or `.lock`/dot-style components that Git ref rules reject.

Required fix:
- tighten the conservative ref validator without invoking Git;
- at minimum reject empty/dot components, repeated `/`, `.lock` component endings, control/space-like unsafe syntax, and other forms outside the intended conservative branch/ref subset;
- add focused negative tests.

### 5. RESULT evidence diffstat is inaccurate
Current branch compare from base main to reviewed head is:
- 7 files changed;
- `RESULT-019.md`: 85 additions;
- total additions: 1706.

RESULT currently records `RESULT-019.md | 95` and `7 files changed, 1716 insertions(+).`

After implementing the fixes, regenerate RESULT evidence from the final tested implementation/head so changed-file and diffstat evidence is accurate.

## Evidence Accepted
The following evidence is accepted for round 1 but must be rerun after fixes:
- Focused Continuity suite: `22 passed`
- AIOS Bridge suite: `108 passed`
- Full repository suite: `582 passed`
- `BRIDGE_V0_4_BEHAVIOR_CHANGED: NO`
- `LIVE_EXTERNAL_CALLS: 0`
- `AUTHORITY_WIDENED: NO`
- `SECRETS_OR_REASONING_PERSISTED: NO`

The branch is a clean fast-forward candidate relative to current main, and the commit after tested implementation modifies only `.ai/results/RESULT-019.md`.

## FIX Scope
Keep the fix narrow to TASK-019 M1:
- `src/aios_bridge/continuity/`;
- focused Continuity tests;
- CLI only if needed for compatibility;
- RESULT evidence.

Do NOT modify `bridge.py` behavior, add Brain/Executor routing, add API calls, introduce automatic control-branch state publication, or widen RUN/FIX/MERGE authority.

## Required Retest
Run again after fixes:

```text
pytest tests/aios_bridge/continuity/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

Publish the corrected branch through the existing AIOS Bridge FIX flow for Review Round 2.
