---
# Format: UTF-8 without BOM, LF line endings
name: aios-renew-worker
description: >
  Antigravity-only /aios-renew-worker workflow. Operates the AIOS worker
  protocol (CONTINUE TASK-N, STATUS TASK-N, plus explicit RUN/FIX/REPAIR compatibility paths) through the exact pinned
  AIOS-renew kernel with executor identity antigravity.
---

# AIOS-renew Worker — Antigravity Workflow

**Surface:** Antigravity `/aios-renew-worker` slash command only.
**Executor identity:** `antigravity` — passed as `--executor antigravity` to the shared launcher.

This is the only active Antigravity execution surface. It must never serve the
Codex worker surface or infer, reroute, or substitute another executor.

## Explicit Invocation

```text
/aios-renew-worker CONTINUE TASK-N
/aios-renew-worker STATUS TASK-N
/aios-renew-worker RUN TASK-N
/aios-renew-worker FIX TASK-N FINDING-ID
/aios-renew-worker REPAIR RUN-N-NNN
```

`TASK-N` is the exact user-supplied task identifier. `FINDING-ID` is the exact
Human-supplied remediation finding identifier. `RUN-N-NNN` is the exact Human-supplied
failed run identifier.

## Operator Boundary

The visible Antigravity session is operator UI only. `CONTINUE TASK-N` is the normal
Human lifecycle command; the pinned kernel alone decides the next canonical action
and whether it requires a coding Executor. After dispatch the visible session must not
inspect TASK implementation context, inspect or reconstruct repair lineage,
edit product files, execute verification, synthesize evidence, review semantics,
retry, reroute, or continue coding.

## Strict Execution Contract

1. Parse the exact Human command (`CONTINUE TASK-N`, `STATUS TASK-N`, `RUN TASK-N`,
   `FIX TASK-N FINDING-ID`, or `REPAIR RUN-N-NNN`). CONTINUE and STATUS accept only one
   canonical TASK target. Missing FIX finding identifiers or missing/malformed REPAIR targets
   fail before kernel invocation.
2. Echo the requested task ID / run ID, action, and selected executor (`antigravity`).
3. Resolve the deterministic Python 3.11+ bootstrap host described below.
4. Invoke the checked-in shared launcher
   `.agents/skills/aios-worker/scripts/aios_worker.py` exactly once with the
   requested action, exact task ID or run ID, and `--executor antigravity`.
5. Do not invoke an executor directly, retry, reroute, or select another executor.
6. Do not reconstruct TASK, RESULT, EVIDENCE, REVIEW, REMEDIATION, or REPAIR semantics/lineage.
7. Do not perform publication, push, or branch merge. Workers remain push-free and
   stop after Runtime PASS. Successful RUN/FIX/REPAIR exposes the candidate for ChatGPT
   semantic review and stops; ChatGPT remains the sole semantic Reviewer.
   Publication is an automatic repository event triggered only after ChatGPT emits a
   canonical PASS review-decision ref (`refs/heads/aios/review-decision/<RUN_ID>`). The
   repository-native publication workflow (`.github/workflows/aios-auto-publish.yml`) accepts
   either the canonical ref push or the bounded `run_id` replay requested by successful
   SUBMIT_REVIEW ingress, then delegates to the pinned AIOS-renew publication gate
   (`python -m aios_renew.publication`). Manual dispatch of that same bounded `run_id`
   remains an emergency/debug fallback and grants no verdict override.
   The exact flow is: AIOS PASS -> ChatGPT semantic review -> canonical PASS review-decision ref -> repository-native workflow -> pinned AIOS publication gate -> exact source candidate fast-forward to main.
   There is no Human PUBLISH command in the normal path.
   A review verdict of CHANGES_REQUIRED does not publish and continues through narrow FIX lineage.
   Semantic PASS publishes only the exact reviewed source candidate and never review-decision, artifact, or remediation metadata commits.
8. After dispatch, stop. On successful canonical AIOS PASS, report:

   ```text
   Review TASK-N in ChatGPT
   ```

For CONTINUE and STATUS, pass through the pinned Human/Unified State surface output
and return code. Do not parse that output to select another action, call `state` before
CONTINUE, retry, or invoke the kernel a second time. The supplied `antigravity` identity
is Human selection available to the kernel; it must not force an Executor when pinned
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
report exactly `BOOTSTRAP_INTERPRETER_UNAVAILABLE`. The bootstrap host never
provides runtime authority; AIOS-renew runs only from the launcher's separate
`.git/aios/worker-runtime`.

## Command Details

### CONTINUE TASK-N — normal lifecycle command

Delegates exactly once to the pinned Unified Human Surface with the exact repository
root and Human-selected Antigravity identity. AIOS-renew TASK-086/TASK-087 exclusively
owns Unified State, next-action selection, `executor_required`, NO_CHANGE reuse,
handoff, recovery, and bounded `AIOS_HUMAN_SURFACE` output. This workflow does not
inspect state, reconstruct an action, automatically continue, or synthesize a verdict.

```powershell
<resolved bootstrap-host argv> .agents/skills/aios-worker/scripts/aios_worker.py CONTINUE TASK-N --executor antigravity
```

RUN, FIX, and REPAIR below remain explicit compatibility/debug paths; they are not
the normal Human state-selection burden. Brain, Reviewer, and Publisher handoffs remain
external authorities. Raw `aios ...` and `python -m aios_renew.operator ...` commands
are internal integration details, not normal downstream Human guidance.

### RUN TASK-N

Delegates one primary execution to AIOS-renew and leaves HEAD local for semantic review:

```powershell
<resolved bootstrap-host argv> .agents/skills/aios-worker/scripts/aios_worker.py RUN TASK-N --executor antigravity
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
<resolved bootstrap-host argv> .agents/skills/aios-worker/scripts/aios_worker.py FIX TASK-N FINDING-ID --executor antigravity
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
permits one continuation. The workflow does not parse, select, infer, or implement that
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
<resolved bootstrap-host argv> .agents/skills/aios-worker/scripts/aios_worker.py REPAIR RUN-N-NNN --executor antigravity
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
state, publication, and executor authority:

```powershell
<resolved bootstrap-host argv> .agents/skills/aios-worker/scripts/aios_worker.py STATUS TASK-N --executor antigravity
```

STATUS may initialize the dedicated untracked worker runtime but must not invoke
an executor or become a second status or review authority.

## Adopted Upstream Capabilities and Boundaries

Under the pinned commit `49ad4d7a1e57a4c25ba44e60589d8320cb0f57b2`, Python Agent adopts:
- **TASK-086**: Deterministic, read-only Unified State and Next Action through the
  public `state` operator surface. The workflow neither copies nor caches the reducer.
- **TASK-087**: One bounded Human continuation front door through the public `continue`
  operator surface. The pinned kernel alone selects the lifecycle operation and exact
  `executor_required` behavior; supplying `antigravity` does not force coding work.
- **TASK-088**: For a syntactically valid requested TASK whose canonical local TASK file
  is absent, pinned CONTINUE may perform the bounded TASK-062-governed pre-resolution
  synchronization before Unified State loads the TASK, then derive state from the fresh
  synchronized repository state. Existing local TASKs gain no automatic synchronization
  path; `state` and STATUS remain read-only for product state; unsafe repository states
  fail closed; and the workflow adds no synchronization implementation, retry, reroute,
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
  fallback, or reroute, and no parser, dispatcher, or state machine is added to this workflow.
- **TASK-090**: Safe publication recognizes valid `CONTINUE_IMPLEMENTATION` lineage while
  preserving review-before-publication and exact source-candidate publication. The capability
  is consumed solely through the pinned distribution; Python Agent copies no Runtime or
  publication implementation and its repository-native publication boundary remains unchanged.
- **TASK-092**: The exact pinned Antigravity adapter is the native Executor instruction authority
  for `CONTINUE_IMPLEMENTATION`. An admitted native Executor resumes the necessary bounded
  unfinished original TASK work from the exact failed lineage, including bounded discovery/live
  capture when that is part of the unfinished work, and must commit the permitted in-scope
  implementation state on success. This grants no fresh PRIMARY, automatic retry, fallback,
  reroute, scope widening, recursive continuation, semantic review, or Executor-owned canonical
  verification or EVIDENCE authority. Brain still selects the semantic action, and Runtime still
  owns lifecycle validation, completion, canonical verification, and EVIDENCE. The launcher
  contains no local instruction parser, prompt implementation, repair dispatcher, or second state
  machine.
- **TASK-091 revision 2 / TASK-093..TASK-100 / TASK-102**: The published post-pin
  runtime and control-plane capability families are available solely through the exact pinned
  kernel. TASK-102 pre-observation synchronization remains Runtime-owned. This workflow adds
  no synchronization engine, correction frontier, performance collector, lifecycle parser, and
  no new Human-facing Executor selection.
- **TASK-103 / TASK-101 revision 4**: Published correction-frontier hardening and
  Performance Closure are consumed solely through the exact pin. The workflow adds no
  correction frontier or performance collector.
- **TASK-104 / TASK-105**: Recovered Brain Authoring Ingress is available only through
  the separate repository-owned `aios_brain_ingress.py` carrier under post-TASK-105
  semantics. This Human-facing workflow never exposes authoring ingress operations.
- **TASK-106**: Package-level Human-surface presentation hardening is consumed
  through the pinned kernel.
- **TASK-113**: Package compatibility is consumed through the pinned kernel and the
  downstream [AIOS TERMINAL ATTENTION] Issue carrier remains the active Phase-1 binding.
- **TASK-115**: Truthful zero-delta intermediate `CONTINUE_IMPLEMENTATION` publication
  hardening is consumed solely through the pinned distribution. The repository-owned
  source-only auto-publish workflow gains only bounded `run_id` replay transport and no
  local review or publication semantics.
- **TASK-114 / TASK-116**: Downstream portability-versus-activation reconciliation is
  recorded as upstream governance-policy provenance. It does not activate any Python
  Agent repository binding, workflow, product authority, or lifecycle authority.
- **TASK-117**: Package carrier portability hardening across PRIMARY wakeup, REMEDIATION
  intent, REPAIR wakeup, and terminal-attention admission is consumed solely through the
  pinned distribution. Existing Phase-1 and Phase-2 repository bindings remain active and
  delegate through the exact pinned package without repository-specific policy changes.
- **TASK-118**: Terminal-attention package portability hardening for source-repository and
  exact-pin downstream layouts is consumed solely through the pinned distribution. Existing
  terminal truth, Phase-1 and Phase-2 bindings, and Runtime/Reviewer/Publisher authority remain
  unchanged; the workflow adds no repository-specific fallback or lifecycle behavior.
- **TASK-119**: Unified Human Surface preserves no-Executor repair semantics even when a
  Human-facing downstream carrier supplies an executor identity to `continue`. Consumed solely
  through the pinned distribution.
- **TASK-120**: Runtime-owned canonical verification hardening for native Windows verification
  executions receiving an isolated temporary environment.
- **TASK-121 / TASK-128**: Deterministic read-only canonical rehydration snapshot and durable Brain
  Sync contract integration.
- **TASK-122**: Bounded `FINALIZE_CANDIDATE` REPAIR action closing native terminal-response loss
  gaps for clean unmutated candidates.
- **TASK-123 / TASK-124 / TASK-125**: Bounded, immutable REPAIR-authorization supersession contract,
  repeatable across multiple generations for the same failed RUN, with publication repair lineage
  validation.
- **TASK-126**: Native Antigravity zero-mutation execution structural ResultPackage return for
  read-only completion work.
- **TASK-127**: Post-canonicalization AUTHOR_REPAIR handoff and bounded wakeup carrier.
- **TASK-129**: Generic REPAIR-after-failed-REMEDIATION resolving embedded RUN identity.
- **TASK-145 revision 2**: Generic Unified State local/canonical REPAIR semantic-identity
  reconciliation fix, validated against the reviewed TASK-146 verification baseline
  (commit `89ac1880fed41c7237146422e2e985d98c0eeda8`). Pinned Unified State reconciles local
  pending runs with canonical remote correction lineage without leaving review_id or finding_id
  unset. Consumed solely through the pinned kernel; Python Agent adds no downstream workaround
  or second lifecycle authority.

Capabilities present in upstream history but **not** exposed by this downstream worker:
- **TASK-066 / TASK-068..TASK-074**: Although the exact package contains this intervening
  Runtime history, no upstream workflow or Runtime/publication implementation is copied.
  Repository-owned Phase-1/Phase-2 bindings delegate to pinned public operator boundaries,
  while no self-hosted `wakeup`, `recover-primary`, or correction command is exposed on this
  Human-facing worker. Python Agent's publication/automation semantic authority remains unchanged. The Human-facing
  worker surface exposes normal CONTINUE/STATUS plus explicit RUN/FIX/REPAIR
  compatibility/debug paths only.
- **TASK-107, TASK-108, TASK-110, TASK-111, TASK-112, TASK-113**: These repository-specific
  GitHub Issue/wakeup/publication continuation/repair/remediation-intent/terminal-attention
  bindings are active repository workflows, but are deliberately not exposed as commands of
  this Human-facing worker surface.

## Immutable Kernel Pin

The only authoritative AIOS-renew kernel is commit
`49ad4d7a1e57a4c25ba44e60589d8320cb0f57b2`. Installed provenance for the TASK-216/TASK-217-era
`c96eb8b52acd865b9453409e6598e08a8bd4e48e` pin, the TASK-209-era
`91a177d5b96b2197a4d8223dbb727dda6201cb64` pin, the TASK-208-era
`26097405343150dc1b55015b94720528afad50ed` pin, the TASK-204-era
`652b00b103dd50e2a550dd0ec0fe4063e69631b7` pin, the TASK-201-era
`f0237a3b98985ce6ebbaf41af1e06fa3eb4e998e` pin, the TASK-198-era
`a3b723b49cd65677f548c5694a52a6fc006a9e2a` pin, the TASK-102-era
`2599202afedb0622e9e9bdc7b5a15f34da01cc27` pin, the immediate-predecessor
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

TASK-192 historically advanced the execution substrate and recorded downstream governance.
TASK-198 adopts published TASK-103 hardening, TASK-101 revision 4, and the recovered
TASK-104/TASK-105 Brain Authoring Ingress lineage through the exact pin.
TASK-201 historically migrated the then-sole active downstream runtime authority to exact reviewed, source-published
commit `f0237a3b98985ce6ebbaf41af1e06fa3eb4e998e` as historical migration provenance.
TASK-204 historically superseded that active pin with exact reviewed, source-published
commit `652b00b103dd50e2a550dd0ec0fe4063e69631b7`, consuming TASK-115 publication hardening
and recording TASK-114/TASK-116 policy provenance without activating repository bindings.
TASK-205 completes FULL_AIOS_CONTROL_PLANE_ADOPTION_PHASE_1 by activating repository-owned
downstream bindings for Brain Issue authoring (`.github/workflows/aios-brain-ingress.yml`),
PRIMARY wakeup (`.github/workflows/aios-brain-wakeup.yml` and `.github/workflows/aios-self-hosted-wakeup.yml`),
and terminal attention (`.github/workflows/aios-terminal-attention.yml`). GitHub Issue
authoring/PRIMARY/attention represent the normal Phase-1 repository bindings after publication,
while the local `aios_brain_ingress.py` file/stdin carrier and this Human-facing `/aios-renew-worker`
surface remain bounded emergency/debug/fallback paths. TASK-206 completes
FULL_AIOS_CONTROL_PLANE_ADOPTION_PHASE_2 by activating the bounded TASK-110 publication
continuation, TASK-112 remediation intent over separate A3/A6 authorities, and the dedicated
TASK-111 REPAIR wakeup. Their thin bootstraps reuse the exact-pin runtime and do not add worker,
Runtime, Reviewer, or Publisher authority.
TASK-208 supersedes that active pin with exact reviewed, source-published commit
`26097405343150dc1b55015b94720528afad50ed`, consuming TASK-117 / REVIEW-117-001 carrier
portability hardening across PRIMARY wakeup, REMEDIATION intent, REPAIR wakeup, and
terminal-attention admission while preserving all Phase-1 and Phase-2 repository bindings unchanged.
TASK-209 supersedes that active pin with exact reviewed, source-published commit
`91a177d5b96b2197a4d8223dbb727dda6201cb64`, consuming TASK-118 / REVIEW-118-001
terminal-attention portability hardening while preserving those bindings and authority boundaries.
TASK-216 supersedes that active pin with exact reviewed, source-published commit
`c96eb8b52acd865b9453409e6598e08a8bd4e48e`, consuming cumulative reviewed TASK-119..129 /
REVIEW-129-001 capabilities and porting bounded TASK-127 post-canonicalization REPAIR handoff
and non-target repair receipt suppression while preserving authority boundaries.
TASK-218 supersedes that active pin with exact reviewed, source-published commit
`49ad4d7a1e57a4c25ba44e60589d8320cb0f57b2`, consuming upstream TASK-145 revision 2 /
RUN-145-002 / REVIEW-145-001 local/canonical REPAIR semantic-identity reconciliation fix
validated against reviewed baseline 89ac1880fed41c7237146422e2e985d98c0eeda8 (TASK-146 /
REVIEW-146-001) while preserving all Phase-1/Phase-2 repository bindings and authority boundaries.
Prior TASK-207 revision-4 conformance remains historical evidence tied to
`c96eb8b52acd865b9453409e6598e08a8bd4e48e`; fresh full downstream conformance certification
under `49ad4d7a1e57a4c25ba44e60589d8320cb0f57b2` remains pending through the existing TASK-207
semantic authority.
TASK-207 revision 2 and RUN-207-001/RUN-207-002/REPAIR-207-001 remain immutable old-pin
history; conformance resumes only through a fresh Brain revision bound to the new pin.
Future AIOS-renew main changes remain irrelevant until another explicit reviewed downstream migration.

## Live Self-Hosted Operational Prerequisites

Live PRIMARY and Phase-2 REMEDIATION/REPAIR execution require one-time Human operational setup before live use:
1. Register a dedicated Windows x64 self-hosted runner for repository `trung-via/python_complete_agent` with custom label `python-complete-agent`.
2. Run the runner under an account able to use the already-working local Python/Codex/Antigravity/Git environment.
3. Configure repository variable `AIOS_REPO_ROOT` to the persistent Python Agent checkout.
4. Keep existing non-interactive Git transport available.
Source publication of this task does not claim those external prerequisites are live-proven.
