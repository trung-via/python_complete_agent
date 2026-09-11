# AIOS Unified Worker Workflow

As of TASK-183 revision 1, the repository-owned Codex and Antigravity worker
surfaces delegate exclusively to the immutable AIOS-renew kernel at commit
`08e4a612377ac82be36061286a34138ea53ab0d1`. Legacy AIOS Bridge source remains
archived in this repository, but it is inactive and unreachable from these
CONTINUE/STATUS and explicit RUN/FIX/REPAIR surfaces.

---

## 1. Single Semantic Protocol

AIOS defines a single unified semantic protocol for Human operators across all supported AI environments:

```text
CONTINUE TASK-N
STATUS TASK-N
RUN TASK-N
FIX TASK-N FINDING-ID
REPAIR RUN-N-NNN
```

CONTINUE is the normal Human lifecycle command. STATUS is read-only Unified State
inspection. RUN, FIX, and REPAIR are retained as explicit compatibility/debug paths.

### UI Surface Parity

The protocol is invoked through physically separate, thin operator files:

| Environment | Explicit Invocation Command | Surface File | Selected Executor |
|:---|:---|:---|:---|
| **Antigravity** | `/aios-renew-worker CONTINUE TASK-N` | `.agents/workflows/aios-renew-worker.md` | `antigravity` |
| **Codex** | `$aios-worker CONTINUE TASK-N` | `.agents/skills/aios-worker/SKILL.md` | `codex` |

Both surfaces call the same `aios_worker.py` launcher. The selected executor is
the only semantic difference. TASK/RUN/RESULT/EVIDENCE, synchronization,
executor invocation, review validation, canonical remote remediation lineage
resolution, and remote REPAIR lookup all come from the same pinned AIOS-renew distribution.
Supplying the surface-selected identity makes that Human choice available to the
kernel; it does not force Executor work when the pinned Unified State action has
`executor_required: false`.

---

## 2. Locked Identity Contract

Each UI surface is permanently bound to a single executor identity. **No cross-surface reroute, inference, or substitution is allowed.**

```text
/aios-renew-worker -> .agents/workflows/aios-renew-worker.md -> executor antigravity -> AIOS-renew
$aios-worker  -> .agents/skills/aios-worker/SKILL.md -> executor codex       -> AIOS-renew
```

The two surface files are physically separate to prevent an operator tool from
selecting the wrong identity. Neither surface may retry with or reroute to the
other executor.

---

## 3. Dedicated Pinned Runtime and Shared State

The launcher does not depend on a global `aios` executable, a preinstalled
`aios_renew` import, a bare `python` command, or a machine-specific source
checkout. Before dispatch, each surface probes the same fixed Python 3.11+ host
order:

- Windows: repository `venv/Scripts/python.exe` when present, `py -3.11`,
  `python3`, `python`.
- POSIX: repository `venv/bin/python` when present, `python3`, `python`.

Each candidate receives only the fixed version probe. The first successful
candidate starts the launcher exactly once; if none qualifies, the surface
reports `BOOTSTRAP_INTERPRETER_UNAVAILABLE` before creating an AIOS RUN. A
repository product virtualenv is permitted only as this bootstrap host. Its
packages are irrelevant and AIOS-renew is never installed into or imported from
it.

On first use, the selected host creates a dedicated runtime below
`<git-dir>/aios/worker-runtime` and installs exactly the one immutable dependency in
`.agents/skills/aios-worker/requirements-aios-renew.txt`.

Every invocation validates installed PEP 610 direct-source metadata against the
authoritative repository and commit. A dedicated `worker-bootstrap.lock`
serializes concurrent first use and is separate from the kernel's
`operator.lock`. Valid runtimes are reused without reinstalling; incomplete,
stale, alternate-source, or unverifiable runtimes are rebuilt fail-closed before
an AIOS operator operation can exist.

AIOS-renew owns local RUN, handoff, RESULT, and operator-lock state below the
Git-dir AIOS area. Switching between Codex and Antigravity does not create a
second semantic state store.

---

## 4. Worker Operations

### CONTINUE TASK-N — normal Human lifecycle path

- **Codex**: Calls AIOS-renew `continue` once with the exact TASK ID, exact Python
  Agent repository root, and executor `codex`.
- **Antigravity**: Calls the same operator once with executor `antigravity`.
- **Pass-through**: The launcher preserves the pinned kernel return code and bounded
  `AIOS_HUMAN_SURFACE` output. It does not parse prose or state to authorize another
  operation, synthesize failure/review state, retry, reroute, or call the kernel again.
- **Unified Authority**: TASK-086 Unified State and TASK-087 Next Action remain solely
  inside the pinned distribution. The downstream launcher does not call `state` first,
  inspect refs/files/RUNs, reconstruct the action taxonomy, or expose internal selectors.
- **Executor Semantics**: The selected surface identity is Human input available to the
  kernel. WAIT, Brain/Reviewer/Publisher handoff, DONE/BLOCKED, transport/recovery, and
  eligible verification-only NO_CHANGE paths do not acquire a coding Executor merely
  because an executor-specific surface supplied its identity. Exact `executor_required`
  and reuse decisions remain pinned AIOS-renew authority.

The explicit RUN, FIX, and REPAIR operations below remain bounded operational escape
hatches for compatibility and debugging; they are not the normal state-selection burden.

### RUN TASK-N

- **Codex**: Calls AIOS-renew `run` once with the exact TASK ID, explicit Python
  Agent repository root, and executor `codex`. AIOS-renew owns native mutation
  capability selection; the worker passes no sandbox or permission argument.
- **Antigravity**: Calls the same AIOS-renew `run` once with executor
  `antigravity`; the visible operator session does not implement the task.
- **Authority**: AIOS-renew retains PRIMARY synchronization, task parsing,
  execution, verification evidence, RESULT validation, and PASS authority.
- **Failure**: There is no automatic retry or executor reroute.

### FIX TASK-N FINDING-ID

- **Purpose**: Execute one canonical narrow remediation, never rerun the original
  TASK as an inferred fix.
- **Input**: Both surfaces require one explicit Human-supplied `FINDING-ID` and
  preserve that exact value together with the exact TASK and bound executor.
- **Failure**: Missing finding input fails before kernel invocation. Kernel
  remote-lineage failures are surfaced unchanged without retry, fallback,
  artifact reconstruction, or executor substitution.
- **Authority**: AIOS-renew resolves canonical remediation lineage remotely from
  TASK and finding with task/revision scoping (TASK-067). Unrelated historical finding ids
  cannot poison current FIX admission. Consuming TASK-067 occurs solely through the
  exact pinned AIOS distribution; the worker remains thin and contains no repository-wide
  remediation discovery or historical lineage filtering logic. The launcher does not inspect
  HEAD, infer a finding, resolve or materialize local REVIEW/REMEDIATION lineage, or pass
  prior-review, sandbox, scope, affected-verification, or reviewed-SHA authority.
- **TASK-078 Historical Subject**: A valid canonical remote finding may bind one exact
  historical TASK/revision, REVIEW, REMEDIATION, and `reviewed_sha`. When current control
  HEAD differs from that SHA, the pinned Runtime may create one isolated subject beginning
  exactly at `reviewed_sha` for one selected Executor. The current control checkout, branch,
  index, and worktree remain unchanged, and the exact bound historical TASK/revision is
  authoritative for the FIX. Current-head FIX behavior remains compatible.
- **Historical Failure Boundary**: An admitted historical FIX failure is persisted as canonical
  REMEDIATION failure and remains eligible for ordinary REPAIR continuity. A pre-admission
  historical TASK or subject defect fails closed without a synthetic RUN. The worker does not
  load historical TASK content, create subjects or worktrees, traverse reviewed lineage,
  recover current-versus-reviewed SHA state, persist admitted failures, or decide remediation
  policy.
- **Publication Boundary**: Historical FIX success does not authorize automatic merge, rebase,
  or cherry-pick onto current product main. Existing publication and integration authority
  remains separate and fail-closed when the reviewed historical lineage diverges from current
  main; the worker performs no publication integration.

### REPAIR RUN-N-NNN

- **Purpose**: Human-authorized thin delegation to the pinned AIOS-renew kernel
  for pre-PASS failed RUNs.
- **Input**: Both surfaces require one explicit Human-supplied `RUN-N-NNN` failed
  RUN identifier and validate canonical format before kernel invocation.
- **Safety**: The worker is explicitly forbidden from inspecting or reconstructing
  repair lineage, passing `--repair`, TASK ID, failed-head, scope, constraints,
  instructions, or verification authority.
- **TASK-064/TASK-075/TASK-076 Reuse Boundary**: Worker REPAIR remains thin and does not
  implement fast-path eligibility, authority ordering, or changed-files reconciliation.
  For an eligible NO_CHANGE verification-only continuation, the pinned Runtime compares
  like-for-like canonical changed-files authority. Root-relative reusable
  `Result.changed_files` and correction-relative `FAILURE candidate.changed_files` remain
  distinct truths, so a valid reusable package is not rejected solely because the latter
  is narrower than the full TASK delta. Genuine malformed or conflicting reuse state still
  fails closed without Executor fallback. CODE_FIX does not consult reuse-only sidecar or
  package validation and proceeds through normal exactly-one selected Executor REPAIR
  dispatch. Canonical FAILURE, TASK, `failed_head_sha`, REPAIR, lineage, and completion
  gates remain intact.
- **TASK-089 Continuation Boundary**: `CONTINUE_IMPLEMENTATION` is available only through
  the pinned Runtime for an admitted repairable pre-verification failed RUN whose original
  implementation is unfinished, no product/code defect is asserted, remaining authorized
  work requires mutation, and a new external/Human reason permits one separately authorized
  continuation. It preserves the exact RUN, TASK revision, `failed_head_sha`/root lineage,
  non-empty explicit modification scope, and one explicit Executor. Brain selects the
  semantic action; Runtime validates and executes it without probing the prerequisite.
  The worker adds no parser, dispatcher, state machine, automatic retry, fresh PRIMARY,
  fallback, or reroute. The Human continues to use normal `CONTINUE TASK-N`, with explicit
  REPAIR retained only as a compatibility/debug path.
- **Thin-Worker Boundary**: Reusable-sidecar decoding, changed-files authority comparison,
  NO_CHANGE eligibility, historical failed-head reconstruction, repair-action policy, and
  the TASK-075/TASK-076 behaviors are consumed solely through the exact pinned distribution.
  TASK-077 snapshot acquisition, Git transport classification, historical lineage traversal,
  duplicate-continuation policy, and recovery decisions are likewise absent from the repository
  launcher. TASK-078 historical TASK loading, reviewed-lineage resolution, isolated-subject
  creation, admitted-failure persistence, and remediation/publication decisions are also
  exclusively Runtime-owned and are not a second REPAIR path.
- **Historical Recovery**: Historical recovery is Runtime-owned under the pinned
  kernel: AIOS-renew admits historical repair execution when the current control
  checkout differs from an immutable `failed_head_sha`, preserving the current
  checkout unchanged, isolating the exact historical failed subject, and executing
  without bootstrapping from the historical tree's old worker pin. Candidate
  ancestry is preserved from the exact failed head; a recovered candidate is not
  silently rebased or merged onto an already-advanced main, and any required
  publication reconciliation is a separate canonical downstream task rather than
  worker behavior.
- **TASK-077 Remote Snapshot**: One historical REPAIR admission acquires one immutable
  task-scoped remote ref snapshot inside the pinned Runtime. That single snapshot supplies
  terminal and candidate identity, duplicate-continuation checks, and lineage reconstruction.
  A nonzero acquisition fails closed with bounded operational provenance; after a successful
  acquisition, missing required refs remain a semantic lineage failure. The worker does not
  acquire or refresh snapshots, classify Git transport failures, traverse historical lineage,
  choose repair action, retry, fall back, or reroute.
- **Failure**: Nonzero return, bootstrap failure, lineage failure, Executor failure,
  verification failure, or completion-gate failure fails closed without retry, reroute,
  fallback, or second kernel invocation.
- **Authority**: The AIOS-renew kernel owns remote REPAIR lookup, failure validation,
  repair contract validation, one-Executor execution, verification, and ResultPackage persistence.

### STATUS TASK-N

- **Behavior**: Calls AIOS-renew `state` exactly once for the exact TASK and passes
  through its bounded, versioned `AIOS_UNIFIED_STATE` observation. STATUS is Unified
  State inspection, not task description.
- **Safety**: STATUS may validate/bootstrap the untracked worker runtime, but is
  read-only for the product worktree, branch/ref, TASK, RUN/RESULT state,
  publication, and executor authority. It does not fetch, synchronize, review,
  execute, or push product state.

### Operational Telemetry and Upstream Scope Boundaries

- **TASK-086 Unified State**: Python Agent adopts the deterministic read-only lifecycle
  reducer solely through the pinned public `state` operator surface. It does not copy,
  cache, approximate, or independently interpret Unified State or Next Action.
- **TASK-087 Unified Human Surface**: Python Agent adopts the bounded continuation front
  door solely through the pinned public `continue` operator surface. One downstream
  invocation delegates at most one pinned canonical operation; the launcher adds no
  recommendation, ranking, memory, fallback, cross-surface substitution, polling, or
  recursive continuation.
- **TASK-088 Missing-local-TASK Pre-resolution**: For a syntactically valid requested
  TASK whose canonical local TASK file is absent, pinned CONTINUE may perform the bounded
  TASK-062-governed pre-resolution synchronization before Unified State loads the TASK,
  then derive state from fresh synchronized repository state. Existing local TASKs gain
  no automatic synchronization path; `state` and STATUS remain read-only for product
  state; unsafe repository states fail closed; and the launcher adds no synchronization
  implementation, retry, reroute, recursive continuation, or second lifecycle operation.

- **TASK-065 Operational Telemetry**: Under the pinned kernel, same-invocation native Executor
  operational telemetry (`token_usage`) may be recorded by the pinned Runtime's native adapters.
  Worker code adds no token parsing or telemetry authority; `token_usage` is optional same-native-invocation
  telemetry and may remain null when the native response does not expose a complete trusted counter
  group. Telemetry is never treated as RESULT, EVIDENCE, review, routing, or acceptance authority.
- **TASK-075 Authority Ordering**: Reuse-only state is authoritative only for an eligible
  verification-only NO_CHANGE continuation. Such reuse remains fail-closed and may elide
  the Executor only under existing Runtime preconditions. CODE_FIX bypasses reuse-only
  validation and follows the ordinary exactly-one selected Executor REPAIR path with all
  canonical lineage and completion gates preserved.
- **TASK-076 Changed-Files Authority**: Valid eligible NO_CHANGE reuse compares like-for-like
  canonical changed-files authority. The reusable package preserves root-relative full TASK
  `Result.changed_files`, while FAILURE preserves correction-relative
  `candidate.changed_files`; their truthful difference alone does not invalidate reuse.
  Genuine malformed or conflicting reuse state remains fail-closed without Executor fallback.
  Zero-Executor reuse and every reconciliation decision remain solely Runtime-owned.
- **TASK-077 Historical-Repair Snapshot**: Historical REPAIR remote discovery is consolidated
  into one immutable task-scoped snapshot per admission. Nonzero snapshot acquisition remains
  fail-closed with bounded operational provenance, while a successful but incomplete snapshot
  remains a semantic lineage failure. The Runtime owns snapshot use and all repair decisions;
  there is no automatic retry, fallback, reroute, or worker-side transport policy.
- **TASK-078 Historical-Remediation Subject**: Canonical remote FIX lineage may bind an exact
  historical TASK/revision and `reviewed_sha`, then execute in a Runtime-owned isolated subject
  while leaving the current control checkout unchanged. Admitted failures remain canonical and
  REPAIR-continuable; pre-admission historical subject defects fail closed without a synthetic
  RUN. Current-head FIX remains compatible, and historical success grants no automatic
  publication integration. The worker owns none of the lineage, isolation, persistence, or
  policy decisions.
- **TASK-079 Native REMEDIATION Structure**: The native remediation-specific schema requires
  empty root evidence, claims, and unresolved, structurally rejecting the RUN-156-007 class of
  non-empty remediation claims. The worker does not inspect, generate, strip, normalize,
  synthesize, or validate these ResultPackage arrays. Runtime remains authoritative for
  fail-closed completion, semantic acceptance coverage, changed_files, verification, EVIDENCE,
  lineage, and publication. PRIMARY semantics are unchanged.
- **TASK-080 Native REPAIR Structure**: The native repair-specific schema requires at least one
  structurally valid claim and empty unresolved, root evidence, and per-claim evidence,
  structurally rejecting the RUN-079-002 class of empty claims. The worker does not enumerate
  TASK acceptance IDs, generate per-TASK schemas, synthesize claims, repair structural output,
  or decide reusable-candidate or historical-recovery policy. Runtime remains authoritative for
  dynamic complete original TASK acceptance coverage, canonical changed_files, verification,
  EVIDENCE, lineage, and publication. PRIMARY semantics are unchanged.
- **TASK-090 Safe-Publication Compatibility**: The pinned distribution recognizes valid
  `CONTINUE_IMPLEMENTATION` lineage at the publication boundary while preserving independent
  semantic review and exact source-candidate publication. Python Agent adopts that compatibility
  solely through the immutable dependency; no Runtime, publication, or semantic-selection
  implementation moves into the launcher or worker surfaces.
- **TASK-066 / TASK-068..TASK-074 Upstream Boundary**: Although the exact pinned package
  contains this intervening Runtime history, Python Agent does not adopt AIOS-renew workflow
  files, upstream remote approval/status workflow, wakeup workflow, dispatch-reconciliation,
  or publication implementation. It exposes no self-hosted `wakeup`, `recover-primary`, or
  internal operator selector. Python Agent's existing publication/automation authority remains
  unchanged. The Human-facing worker surface exposes normal CONTINUE/STATUS plus explicit
  RUN/FIX/REPAIR compatibility/debug paths only.

---

## 5. Review-Before-Publication and Automatic Publication Boundaries

Successful RUN/FIX/REPAIR executions remain push-free implementation operations.
After Runtime PASS, they leave the candidate commit local at `HEAD` (or expose it via
transport) for independent semantic review and stop.
The launcher reports `REVIEW_CANDIDATE_HEAD` and directs the operator to ChatGPT.

### Independent Review Loop

After canonical AIOS PASS, the operator prompts ChatGPT:

```text
Review TASK-N
```

ChatGPT remains the sole semantic Reviewer. It performs an independent semantic audit
and emits a canonical REVIEW artifact with verdict `PASS` or `CHANGES_REQUIRED`.

Runtime PASS proves only internal task verification; it is distinct from semantic REVIEW PASS,
which evaluates architectural alignment and task fulfillment.
A review verdict of CHANGES_REQUIRED does not publish and continues through narrow FIX lineage.

### Automatic Publication Gate

- **Automatic Publication Flow**:
  `AIOS PASS -> ChatGPT semantic review -> canonical PASS review-decision ref -> repository-native workflow -> pinned AIOS publication gate -> exact source candidate fast-forward to main`
- **No Human Publication Command**: There is no Human PUBLISH command in the normal path.
  Automatic publication is a repository event occurring only after ChatGPT materializes a canonical PASS
  review-decision ref at `refs/heads/aios/review-decision/<RUN_ID>`.
- **Repository-Native Workflow**: Pushing the review-decision ref triggers `.github/workflows/aios-auto-publish.yml`,
  which provisions Python 3.11+, installs AIOS-renew from `.agents/skills/aios-worker/requirements-aios-renew.txt`,
  and delegates to `python -m aios_renew.publication`.
- **Candidate Purity**: Semantic PASS publishes only the exact reviewed source candidate fast-forwarded to `main`,
  and never review-decision, artifact, or remediation metadata commits.
- **Merge Boundary**: `MERGE` is never a worker command:
  - Worker executors **NEVER** merge code into `main` or claim publication authority.
  - Worker surfaces stop immediately after canonical PASS and instruct the Human
    operator to review the task in ChatGPT (`Review TASK-N in ChatGPT`).

---

## 6. Normal Human Operator Flow

- **Antigravity**: The Human enters `/aios-renew-worker CONTINUE TASK-N`.
- **Codex**: The Human enters `$aios-worker CONTINUE TASK-N`.
- **Inspection**: The Human uses the corresponding `STATUS TASK-N` surface to inspect
  versioned Unified State without mutation or Executor dispatch.
- **Sequence**: `AIOS PASS -> ChatGPT semantic review -> canonical PASS review-decision ref -> repository-native workflow -> pinned AIOS publication gate -> exact source candidate fast-forward to main`.

---

## 7. Surface File Format Standards

To ensure unambiguous discovery and reliable tool parsing across all AI environments:

- **Encoding**: UTF-8 strictly without BOM (`\xef\xbb\xbf`).
- **Frontmatter Delimiter**: Frontmatter must begin at byte 0 with `b"---\n"` (LF).
- **Physical Separation**:
  - Active Antigravity workflow: `.agents/workflows/aios-renew-worker.md`
  - Retired Antigravity stub: `.agents/workflows/aios-worker.md`
  - Codex skill: `.agents/skills/aios-worker/SKILL.md`
- **Scope Isolation**: Surface files are dedicated to operator protocol translation and must never duplicate implementation logic.

## 8. Migration Certification Boundary

Repository-owned skill/workflow files may be cached by an already-open operator
session. After changes are present on `main`, start a fresh or
explicitly reloaded Codex/Antigravity session before exercising the migrated
surface.

This is a hard namespace cutover. Antigravity uses `/aios-renew-worker` from now
on; `/aios-worker` is permanently retired and fail-closed. Stale Antigravity
branches or caches that do not expose `/aios-renew-worker` fail closed instead of
falling back to legacy `/aios-worker` semantics.

Both active worker surfaces use exactly AIOS-renew commit
`08e4a612377ac82be36061286a34138ea53ab0d1`. Installed provenance for the immediate-predecessor
`883974be6ec5922ae57021b50a48c84a0014dbfa` pin, and every older pin including
`32ace104c5cfaa1b7affbaa40157872b1f85147f`, is stale and is atomically replaced.

This is an exact-pin adoption boundary: Python Agent consumes reviewed TASK-086/TASK-087/TASK-088,
TASK-089, and TASK-090
only through their public operator surfaces. It copies no AIOS-renew workflow files,
creates no second lifecycle state machine, and does not automatically expose every
upstream operator command. ChatGPT semantic review, source-only publication, and the
existing repository-native publication workflow remain separate repository-owned
authorities; raw `aios ...` commands are internal integration details in normal guidance.

TASK-179 does not establish a live stale-checkout CONTINUE proof or complete AIOS-renew
Downstream Adoption. That operational proof remains pending a fresh downstream task
authored and run after TASK-179 is published.

TASK-183 migrates only the execution substrate. It does not continue TASK-182 or claim
that TASK-182 has resumed, passed, been reviewed, or been published.

## 9. Stale-Checkout CONTINUE Certification Protocol

This certification applies only with the downstream AIOS-renew pin
`08e4a612377ac82be36061286a34138ea53ab0d1` already present. Before the first
invocation, record that the fresh proof TASK exists on the canonical remote while
`.ai/tasks/TASK-N.yaml` is absent from the local checkout. The record must bind the
exact TASK ID, the canonical remote ref/commit containing it, the local HEAD, and
the local-missing path observation. This remote-only TASK / local-missing TASK
precondition must exist before CONTINUE; creating it through a preliminary local
sync is not a certification.

The Human then invokes exactly one repository-owned normal lifecycle surface for
that TASK: `$aios-worker CONTINUE TASK-N` for Codex or
`/aios-renew-worker CONTINUE TASK-N` for Antigravity. The Human must not manually
pull, fetch-reset, or otherwise synchronize the checkout, invoke a raw operator
command, retry CONTINUE, switch executors, or use any fallback, reroute, or recursive
CONTINUE to manufacture a successful proof. If this first invocation does not pass
the missing-TASK boundary, preserve its output and repository observations as
failure evidence to inspect. It remains fail-closed and grants no permission for an
automatic retry or reroute.

A valid control-plane proof combines the pre-invocation record above with canonical
AIOS lifecycle evidence from that same CONTINUE invocation. The lifecycle evidence
must show both the pinned pre-resolution synchronization passage for the missing
TASK and progress beyond missing-TASK resolution into the derived canonical
lifecycle action. Executor-authored prose, this documentation, a documentation
test, or a later manual pull or repository synchronization is insufficient evidence.

TASK-088 boundaries remain unchanged: only pinned Runtime rules may synchronize in
the missing-local-TASK CONTINUE pre-resolution path; existing local TASKs gain no
generic auto-sync; STATUS and `state` remain read-only for product state; unsafe
repository states fail closed; downstream code owns no Git synchronization; and
one CONTINUE invocation delegates at most one canonical lifecycle operation. This
protocol defines the certification procedure and evidence types; it does not declare
TASK-180 PASS or AIOS-renew Downstream Adoption complete. Canonical Runtime and
review artifacts remain the authority for those outcomes.
