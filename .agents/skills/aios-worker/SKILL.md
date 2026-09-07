---
# Format: UTF-8 without BOM, LF line endings
name: aios-worker
description: >
  Codex-only $aios-worker skill. Operates the AIOS worker protocol
  (RUN TASK-N, FIX TASK-N FINDING-ID, REPAIR RUN-N-NNN, STATUS TASK-N) through the exact pinned AIOS-renew
  kernel with executor identity codex.
  THIS SKILL IS THE CODEX $aios-worker SURFACE ONLY.
  It must never serve the Antigravity /aios-renew-worker surface.
---

# AIOS-renew Worker Operator Skill — Codex Surface

**Surface:** Codex `$aios-worker` skill invocation only.
**Executor identity:** `codex` — passed as `--executor codex` to the shared launcher.

> This skill is the **Codex-exclusive** operator surface.
> The active Antigravity surface is `/aios-renew-worker` (`.agents/workflows/aios-renew-worker.md`) — a physically separate file.
> The historical Antigravity `/aios-worker` namespace is permanently retired and fail-closed.
> Neither surface may infer, reroute, or substitute the other executor.

## Locked Identity Contract

```text
$aios-worker        -> Codex skill          -> executor codex       -> AIOS-renew
/aios-renew-worker  -> Antigravity workflow -> executor antigravity -> AIOS-renew
```

Cross-surface identity confusion is **forbidden**. This skill must never select
the Antigravity executor.

## Explicit Invocation

```text
$aios-worker RUN TASK-N
$aios-worker FIX TASK-N FINDING-ID
$aios-worker REPAIR RUN-N-NNN
$aios-worker STATUS TASK-N
```

Where `TASK-N` is the exact user-supplied task identifier (e.g. `TASK-048`),
`FINDING-ID` is the exact Human-supplied remediation finding identifier,
and `RUN-N-NNN` is the exact Human-supplied failed run identifier.

## Operator Role and Boundaries

The visible Codex session is only the operator UI. For RUN/FIX/REPAIR, the pinned
AIOS-renew kernel launches the one bounded Codex executor. The visible session
must not inspect the TASK as implementation context, inspect or reconstruct repair lineage,
edit product files, execute verification, synthesize evidence, or duplicate the implementation work.

### Strict Execution Constraints

When this skill is invoked:

1. Parse the exact Human command (`RUN TASK-N`, `FIX TASK-N FINDING-ID`,
   `REPAIR RUN-N-NNN`, or `STATUS TASK-N`). Missing FIX finding identifiers or missing/malformed
   REPAIR targets fail before kernel invocation.
2. Treat invocation of this Codex skill as explicit Human selection of executor `codex`.
3. Echo the requested task ID / run ID, action, and selected executor (`codex`).
4. Invoke the checked-in shared adapter script `.agents/skills/aios-worker/scripts/aios_worker.py`
   with **`--executor codex`** using the deterministic Python 3.11+ bootstrap-host
   resolution contract below. Invoke the launcher exactly once after probing.
   The launcher creates and proves its separate repository-local pinned runtime;
   the bootstrap host is never AIOS-renew runtime authority.
5. **DO NOT** select the Antigravity executor from this skill.
6. **DO NOT** edit implementation or test files in the parent Codex session.
7. **DO NOT** manually reconstruct TASK, RESULT, EVIDENCE, REVIEW, REMEDIATION, or REPAIR semantics/lineage.
8. **DO NOT** invoke raw `codex` or `codex exec` directly.
9. **DO NOT** perform automatic retries or executor rerouting upon failure.
10. **DO NOT** perform publication, push, or branch merge. Workers remain push-free and
    stop after Runtime PASS. Successful RUN/FIX/REPAIR exposes the candidate for ChatGPT
    semantic review and stops; ChatGPT remains the sole semantic Reviewer.
    Publication is an automatic repository event triggered only after ChatGPT emits a
    canonical PASS review-decision ref (`refs/heads/aios/review-decision/<RUN_ID>`), which
    triggers the repository-native publication workflow (`.github/workflows/aios-auto-publish.yml`)
    and delegates to the pinned AIOS-renew publication gate (`python -m aios_renew.publication`).
    The exact flow is: AIOS PASS -> ChatGPT semantic review -> canonical PASS review-decision ref -> repository-native workflow -> pinned AIOS publication gate -> exact source candidate fast-forward to main.
    There is no Human PUBLISH command in the normal path.
    A review verdict of CHANGES_REQUIRED does not publish and continues through narrow FIX lineage.
    Semantic PASS publishes only the exact reviewed source candidate and never review-decision, artifact, or remediation metadata commits.
11. **DO NOT** delegate or reroute to the Antigravity `/aios-renew-worker` workflow.
12. Reload or start a fresh Codex session after the migration commit so this
    repository-owned skill is not served from a stale cache.
13. On successful canonical AIOS PASS, instruct the Human:
    ```text
    Review TASK-N in ChatGPT
    ```

## Deterministic Bootstrap-Host Resolution

Resolve the repository root first. Probe candidate argv in this exact order;
probing is environment discovery and must never invoke AIOS-renew:

- Windows: repository-local `venv/Scripts/python.exe` when present, then
  `py -3.11`, then `python3`, then `python`.
- POSIX: repository-local `venv/bin/python` when present, then `python3`, then
  `python`.

For each candidate, execute only this version probe:

```text
<candidate argv> -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
```

Select the first candidate returning zero, append the launcher/action arguments,
and invoke the launcher exactly once. A missing command or nonzero probe advances
to the next documented candidate. If none qualifies, stop before dispatch and
report exactly `BOOTSTRAP_INTERPRETER_UNAVAILABLE`. Do not install AIOS-renew in
the selected bootstrap host; AIOS-renew runs only from the launcher's separate
`.git/aios/worker-runtime`.

## Command Details

### RUN TASK-N

Delegates one primary execution to AIOS-renew and leaves HEAD local for semantic review:

```powershell
<resolved bootstrap-host argv> .agents/skills/aios-worker/scripts/aios_worker.py RUN TASK-N --executor codex
```

### FIX TASK-N FINDING-ID

Delegates the exact task and Human-supplied finding identifier once to AIOS-renew,
which owns canonical remote remediation lineage resolution. Consuming TASK-067 occurs
solely through the exact pinned AIOS distribution: AIOS-renew resolves canonical
remediation lineage with task/revision scoping, so unrelated historical finding ids
cannot poison current FIX admission or require a Python Agent workaround or branch cleanup.
Worker FIX remains thin and contains no repository-wide remediation discovery or historical
lineage filtering logic. The worker does not inspect HEAD or local REVIEW/REMEDIATION
artifacts, infer a finding, or pass local lineage, sandbox, scope, or verification authority.
Missing finding identifiers fail before kernel invocation. Leaves HEAD local for semantic review:

```powershell
<resolved bootstrap-host argv> .agents/skills/aios-worker/scripts/aios_worker.py FIX TASK-N FINDING-ID --executor codex
```

### REPAIR RUN-N-NNN

Delegates the exact failed run identifier once to AIOS-renew, which owns remote
REPAIR lookup and all failure/repair semantics. Worker REPAIR remains thin and does
not implement TASK-064 fast-path or TASK-075 authority-ordering decisions. Eligible
NO_CHANGE verification-only continuation may invoke zero Executors only when the
pinned Runtime proves all canonical reuse preconditions. Malformed or mismatched
reusable state fails closed when an eligible NO_CHANGE request actually relies on
reuse. CODE_FIX does not consult reuse-only sidecar or package validation and proceeds
through normal exactly-one selected Executor REPAIR dispatch; canonical FAILURE, TASK,
`failed_head_sha`, REPAIR, lineage, and completion gates remain intact. All reuse
eligibility, sidecar decoding, candidate changed-files comparison, and historical
failed-head reconstruction remain solely inside the pinned Runtime.
The worker is explicitly forbidden from inspecting or reconstructing repair lineage,
passing `--repair`, TASK ID, failed-head, scope, constraints, instructions, or verification
authority. Missing or malformed failed run identifiers fail before kernel invocation.
Leaves candidate HEAD local for semantic review:

```powershell
<resolved bootstrap-host argv> .agents/skills/aios-worker/scripts/aios_worker.py REPAIR RUN-N-NNN --executor codex
```

Historical recovery is Runtime-owned under the pinned kernel: AIOS-renew admits
historical repair execution when the current control checkout differs from an immutable
`failed_head_sha`, preserving the current checkout unchanged, isolating the exact
historical failed subject, and executing without bootstrapping from the historical tree's
old worker pin. Candidate ancestry is preserved from the exact failed head; a recovered
candidate is not silently rebased or merged onto an already-advanced main, and any required
publication reconciliation is a separate canonical downstream task rather than worker behavior.

### STATUS TASK-N

Delegates to AIOS-renew task description semantics. STATUS is read-only for the
product worktree, branch, TASK/RUN state, publication, and executor authority.

```powershell
<resolved bootstrap-host argv> .agents/skills/aios-worker/scripts/aios_worker.py STATUS TASK-N --executor codex
```

STATUS may initialize the dedicated untracked worker runtime but must not invoke
an executor or become a second status/review authority.

## Adopted Upstream Capabilities and Boundaries

Under the pinned commit `d036324f3f9ab74ca3f217ed22e416313da71695`, Python Agent adopts:
- **TASK-064**: Eligible NO_CHANGE verification-only continuation may invoke zero Executors
  only when the pinned Runtime proves all canonical reuse preconditions. The worker remains
  thin and makes no fast-path decisions.
- **TASK-065**: Same-invocation native Executor operational telemetry (`token_usage`). Worker
  code adds no token parsing or telemetry authority; `token_usage` is optional same-native-invocation
  telemetry and may remain null when the native response does not expose a complete trusted
  counter group. Telemetry is never treated as RESULT, EVIDENCE, review, routing, or acceptance authority.
- **TASK-067**: Task/revision-scoped remediation lineage resolution prevents unrelated historical
  finding ids from poisoning current FIX admission. Consumed solely through the pinned kernel;
  the worker performs no repository-wide discovery or branch filtering.
- **TASK-075**: Reuse-only state is authoritative only for an eligible verification-only
  NO_CHANGE continuation. Such reuse remains fail-closed and may elide the Executor only
  under existing Runtime preconditions. CODE_FIX bypasses reuse-only validation and follows
  the ordinary exactly-one selected Executor REPAIR path with canonical lineage and completion
  gates preserved. The worker contains none of this decision logic.

Capabilities present in upstream history but **not** exposed by this downstream worker:
- **TASK-066 / TASK-068..TASK-074**: Although the exact package contains this intervening
  Runtime history, no AIOS-renew workflow files, upstream remote approval/status workflow,
  wakeup workflow, dispatch-reconciliation or publication implementation are copied. No
  self-hosted `wakeup`, `recover-primary`, or other worker command is exposed, and Python
  Agent's existing publication/automation authority remains unchanged. The Human-facing
  worker surface remains strictly RUN, FIX, REPAIR, and STATUS.

## Immutable Kernel Pin

The only authoritative AIOS-renew kernel is commit
`d036324f3f9ab74ca3f217ed22e416313da71695`. The launcher validates both the
checked-in dependency pin and installed PEP 610 source+commit provenance and
atomically replaces stale or unverifiable worker runtimes.
