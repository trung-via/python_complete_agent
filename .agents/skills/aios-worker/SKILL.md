---
# Format: UTF-8 without BOM, LF line endings
name: aios-worker
description: >
  Codex-only $aios-worker skill. Operates the AIOS worker protocol
  (CONTINUE TASK-N, STATUS TASK-N, plus explicit RUN/FIX/REPAIR compatibility paths) through the exact pinned AIOS-renew
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
$aios-worker CONTINUE TASK-N
$aios-worker STATUS TASK-N
$aios-worker RUN TASK-N
$aios-worker FIX TASK-N FINDING-ID
$aios-worker REPAIR RUN-N-NNN
```

Where `TASK-N` is the exact user-supplied task identifier (e.g. `TASK-048`),
`FINDING-ID` is the exact Human-supplied remediation finding identifier,
and `RUN-N-NNN` is the exact Human-supplied failed run identifier.

## Operator Role and Boundaries

The visible Codex session is only the operator UI. `CONTINUE TASK-N` is the normal
Human lifecycle command; the pinned kernel alone decides the next canonical action
and whether that action requires a coding Executor. For RUN/FIX/REPAIR, the pinned
AIOS-renew kernel launches the one bounded Codex executor. The visible session
must not inspect the TASK as implementation context, inspect or reconstruct repair lineage,
edit product files, execute verification, synthesize evidence, or duplicate the implementation work.

### Strict Execution Constraints

When this skill is invoked:

1. Parse the exact Human command (`CONTINUE TASK-N`, `STATUS TASK-N`, `RUN TASK-N`,
   `FIX TASK-N FINDING-ID`, or `REPAIR RUN-N-NNN`). CONTINUE and STATUS accept only one
   canonical TASK target. Missing FIX finding identifiers or missing/malformed REPAIR targets
   fail before kernel invocation.
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

For CONTINUE and STATUS, pass through the pinned Human/Unified State surface output
and return code. Do not parse that output to select another action, call `state` before
CONTINUE, retry, or invoke the kernel a second time. The supplied `codex` identity is
Human selection available to the kernel; it must not force an Executor when pinned
`executor_required` semantics select WAIT, handoff, DONE/BLOCKED, transport/recovery,
or an eligible verification-only NO_CHANGE path.

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

### CONTINUE TASK-N — normal lifecycle command

Delegates exactly once to the pinned Unified Human Surface with the exact repository
root and Human-selected Codex identity. AIOS-renew TASK-086/TASK-087 exclusively owns
Unified State, next-action selection, `executor_required`, NO_CHANGE reuse, handoff,
recovery, and bounded `AIOS_HUMAN_SURFACE` output. This worker does not inspect state,
reconstruct an action, automatically continue, or synthesize a lifecycle verdict.

```powershell
<resolved bootstrap-host argv> .agents/skills/aios-worker/scripts/aios_worker.py CONTINUE TASK-N --executor codex
```

RUN, FIX, and REPAIR below remain explicit compatibility/debug paths; they are not
the normal Human state-selection burden. Brain, Reviewer, and Publisher handoffs remain
external authorities. Raw `aios ...` and `python -m aios_renew.operator ...` commands
are internal integration details, not normal downstream Human guidance.

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

TASK-078 historical remediation is also solely Runtime-owned. A valid canonical remote finding
binds one exact historical TASK/revision, REVIEW, REMEDIATION, and `reviewed_sha`.
When the current control HEAD differs, the Runtime may execute one selected Executor in an
isolated subject beginning exactly at `reviewed_sha`, while preserving the current control
checkout, branch, index, and worktree unchanged. The bound historical TASK/revision remains
authoritative for that FIX. An admitted execution failure is persisted as canonical
REMEDIATION failure and remains eligible for ordinary REPAIR continuity; a pre-admission
historical TASK or subject defect fails closed without a synthetic RUN. Current-head FIX
behavior remains compatible.

The worker does not load historical TASK content, create worktrees or subjects, traverse
reviewed lineage, recover current-versus-reviewed SHA state, persist admitted failures,
decide remediation policy, or integrate publication lineage. Successful historical FIX does
not authorize automatic merge, rebase, or cherry-pick onto current product main; existing
publication and integration authority remains separate and fail-closed when lineages diverge.

### REPAIR RUN-N-NNN

Delegates the exact failed run identifier once to AIOS-renew, which owns remote
REPAIR lookup and all failure/repair semantics. Worker REPAIR remains thin and does
not implement TASK-064 fast-path, TASK-075 authority-ordering, or TASK-076
changed-files reconciliation decisions. For an eligible NO_CHANGE verification-only
continuation, the pinned Runtime compares like-for-like canonical changed-files
authority. Root-relative reusable `Result.changed_files` and correction-relative
`FAILURE candidate.changed_files` remain distinct truths, so a valid reusable package
is not rejected solely because the latter is narrower than the full TASK delta.
Malformed or conflicting genuine reuse state still fails closed without Executor
fallback. CODE_FIX does not consult reuse-only sidecar or package validation and
proceeds through normal exactly-one selected Executor REPAIR dispatch; canonical
FAILURE, TASK, `failed_head_sha`, REPAIR, lineage, and completion gates remain intact.
For an admitted repairable pre-verification failure where original implementation is
unfinished and authorized work still requires mutation, the pinned Runtime may consume
a Brain-authored `CONTINUE_IMPLEMENTATION` REPAIR after a new external/Human reason
permits one continuation. The worker does not parse, select, infer, or implement that
action and does not probe the changed prerequisite; the Human still invokes ordinary
`CONTINUE TASK-N` or the explicit `REPAIR RUN-N-NNN` compatibility path.
All reuse eligibility, sidecar decoding, changed-files authority comparison, repair
action policy, and historical failed-head reconstruction remain solely inside the
pinned Runtime.
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

TASK-077 remote discovery is also solely Runtime-owned. One historical REPAIR admission
acquires one immutable task-scoped remote ref snapshot and uses that single snapshot for
terminal and candidate identity, duplicate-continuation checks, and lineage reconstruction.
A nonzero snapshot acquisition fails closed with bounded operational provenance. A successful
snapshot that lacks required refs remains a semantic lineage failure. The worker does not
acquire or refresh the snapshot, classify Git transport failures, traverse historical lineage,
choose repair action, retry, fall back, or reroute.

### STATUS TASK-N

Delegates exactly once to the pinned TASK-086 Unified State read-only boundary and
passes through its versioned `AIOS_UNIFIED_STATE` output. STATUS does not use task
description semantics and is read-only for the product worktree, branch, TASK/RUN
state, publication, and executor authority.

```powershell
<resolved bootstrap-host argv> .agents/skills/aios-worker/scripts/aios_worker.py STATUS TASK-N --executor codex
```

STATUS may initialize the dedicated untracked worker runtime but must not invoke
an executor or become a second status/review authority.

## Adopted Upstream Capabilities and Boundaries

Under the pinned commit `2599202afedb0622e9e9bdc7b5a15f34da01cc27`, Python Agent adopts:
- **TASK-086**: Deterministic, read-only Unified State and Next Action through the
  public `state` operator surface. The worker neither copies nor caches the reducer.
- **TASK-087**: One bounded Human continuation front door through the public `continue`
  operator surface. The pinned kernel alone selects the lifecycle operation and exact
  `executor_required` behavior; supplying `codex` does not force coding work.
- **TASK-088**: For a syntactically valid requested TASK whose canonical local TASK file
  is absent, pinned CONTINUE may perform the bounded TASK-062-governed pre-resolution
  synchronization before Unified State loads the TASK, then derive state from the fresh
  synchronized repository state. Existing local TASKs gain no automatic synchronization
  path; `state` and STATUS remain read-only for product state; unsafe repository states
  fail closed; and the worker adds no synchronization implementation, retry, reroute,
  recursive continuation, or second lifecycle operation.
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
- **TASK-076**: Valid eligible NO_CHANGE reuse compares like-for-like canonical changed-files
  authority. The reusable package preserves root-relative full TASK `Result.changed_files`,
  while FAILURE preserves correction-relative `candidate.changed_files`; their truthful
  difference alone does not invalidate reuse. Genuine malformed or conflicting reuse state
  remains fail-closed without Executor fallback. Zero-Executor reuse and every reconciliation
  decision remain Runtime-owned and are not implemented by this worker.
- **TASK-077**: Historical REPAIR remote ref discovery is consolidated into one immutable
  task-scoped snapshot per admission. The Runtime uses it consistently for terminal and
  candidate identity, duplicate-continuation checks, and lineage reconstruction. Nonzero
  acquisition fails closed with bounded operational provenance; a successful but incomplete
  snapshot remains a semantic lineage failure. There is no automatic retry, fallback, or
  reroute, and the worker owns none of these decisions.
- **TASK-078**: A canonical remote FIX finding may bind an exact historical TASK/revision and
  execute in a Runtime-owned isolated subject beginning at the exact `reviewed_sha` while the
  current control checkout remains unchanged. Admitted failures remain canonical and
  REPAIR-continuable; pre-admission historical subject defects fail closed without a synthetic
  RUN. Current-head FIX remains compatible, and historical success grants no automatic
  publication integration. All lineage, isolation, persistence, and policy remain Runtime-owned.
- **TASK-079**: Native REMEDIATION uses a remediation-specific structural schema that requires
  empty root evidence, claims, and unresolved. It therefore rejects the RUN-156-007 class of
  non-empty remediation claims before they can be structurally valid. The worker does not inspect,
  generate, strip, normalize, synthesize, or validate these ResultPackage arrays.
  Runtime remains authoritative for fail-closed completion, semantic acceptance coverage, changed_files,
  verification, EVIDENCE, lineage, and publication. PRIMARY semantics are unchanged.
- **TASK-080**: Native REPAIR uses a repair-specific structural schema that requires at least one
  structurally valid claim plus empty unresolved, root evidence, and per-claim evidence. It
  therefore rejects the RUN-079-002 class of empty claims before they can be structurally valid.
  The worker does not enumerate TASK acceptance IDs, generate per-TASK schemas, synthesize claims,
  repair output, or decide reusable-candidate or historical-recovery policy.
  Runtime remains authoritative for dynamic complete original TASK acceptance coverage, canonical changed_files,
  verification, EVIDENCE, lineage, and publication. PRIMARY semantics are unchanged.
- **TASK-089**: REPAIR may use the bounded `CONTINUE_IMPLEMENTATION` action only for an
  admitted repairable pre-verification failed RUN whose original implementation is unfinished,
  no product/code defect is asserted, remaining authorized work requires mutation, and a new
  external/Human reason permits one separately authorized continuation. Exact failed RUN,
  TASK revision, `failed_head_sha`/root lineage, non-empty explicit modification scope, and one
  explicit Executor are preserved. Brain owns the semantic choice; Runtime validates and
  executes it without probing the prerequisite. It is not automatic retry, fresh PRIMARY,
  fallback, or reroute, and no parser, dispatcher, or state machine is added to this worker.
- **TASK-090**: Safe publication recognizes valid `CONTINUE_IMPLEMENTATION` lineage while
  preserving review-before-publication and exact source-candidate publication. The capability
  is consumed solely through the pinned distribution; Python Agent copies no Runtime or
  publication implementation and its repository-native publication boundary remains unchanged.
- **TASK-092**: The exact pinned Codex adapter is the native Executor instruction authority for
  `CONTINUE_IMPLEMENTATION`. An admitted native Executor resumes the necessary bounded unfinished
  original TASK work from the exact failed lineage, including bounded discovery/live capture when
  that is part of the unfinished work, and must commit the permitted in-scope implementation state
  on success. This grants no fresh PRIMARY, automatic retry, fallback, reroute, scope widening,
  recursive continuation, semantic review, or Executor-owned canonical verification or EVIDENCE
  authority. Brain still selects the semantic action, and Runtime still owns lifecycle validation,
  completion, canonical verification, and EVIDENCE. The launcher contains no local instruction
  parser, prompt implementation, repair dispatcher, or second state machine.
- **TASK-091 revision 2 / TASK-093..TASK-100 / TASK-102**: The published post-pin
  runtime and control-plane capability families are available solely through the exact pinned
  kernel. In particular, TASK-102 pre-observation synchronization remains Runtime-owned.
  This worker adds no synchronization engine, correction frontier, performance collector,
  lifecycle parser, or new Human-facing Executor selection.

Capabilities present in upstream history but **not** exposed by this downstream worker:
- **TASK-066 / TASK-068..TASK-074**: Although the exact package contains this intervening
  Runtime history, no AIOS-renew workflow files, upstream remote approval/status workflow,
  wakeup workflow, dispatch-reconciliation or publication implementation are copied. No
  self-hosted `wakeup`, `recover-primary`, or other worker command is exposed, and Python
  Agent's existing publication/automation authority remains unchanged. The Human-facing
  worker surface exposes normal CONTINUE/STATUS plus explicit RUN/FIX/REPAIR
  compatibility/debug paths only.

## Immutable Kernel Pin

The only authoritative AIOS-renew kernel is commit
`2599202afedb0622e9e9bdc7b5a15f34da01cc27`. Installed provenance for the immediate-predecessor
`e72135cd5c5a1dec0d8374d9bb8994da5e458feb` pin, and every older pin including
`08e4a612377ac82be36061286a34138ea53ab0d1`,
`883974be6ec5922ae57021b50a48c84a0014dbfa` and
`32ace104c5cfaa1b7affbaa40157872b1f85147f`, is stale. The launcher validates both the
checked-in dependency pin and installed PEP 610 source+commit provenance and
atomically replaces stale or unverifiable worker runtimes.

This pin migration does not prove a live stale-checkout CONTINUE or complete AIOS-renew
Downstream Adoption. That proof remains pending a fresh downstream task authored and run
after TASK-179 is published.

TASK-183 historically adopted TASK-089/TASK-090 at the predecessor pin. TASK-184 migrates
only the execution substrate to reviewed TASK-092. It does not continue TASK-182 or claim
that TASK-182 has resumed, passed, been reviewed, or been published. RUN-182-003 remains
the canonical failed lineage under the predecessor adapter; only a later separately
authorized continuation may act on it.

TASK-192 advances only the exact execution substrate and records downstream governance.
TASK-101 and TASK-103 remain blocked pending exact reviewed source publication; current
AIOS-renew main and unpublished candidates are not admissible runtime authority.
