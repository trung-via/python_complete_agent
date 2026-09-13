# ChatGPT Project Contract — Python Agent / Product Intelligence

Status: Durable project governance  
Scope: ChatGPT Brain behavior for repository `trung-via/python_complete_agent`

## 1. Project Identity

Python Agent is the product.

Its long-term direction is Product Intelligence and the larger Commerce AI System.

AIOS-renew is the execution substrate used to implement this product.  
AIOS-renew does not own Python Agent domain architecture.

## 2. Governance Foundation and Operating Model

### Governance Foundation Precedence

The Governance Foundation has four distinct layers:

- **Manifesto = WHY:** the highest interpretive philosophy, expressing enduring values,
  refusals, and direction. It guides interpretation but is not an executable permission
  matrix.
- **Constitution = highest enforceable governance:** the authority, delegation, mutation,
  conflict, compliance, and amendment law governing Python Agent.
- **Product Contract = WHAT:** durable product and domain promises and architecture
  boundaries.
- **Project Contract = HOW** (ChatGPT Project Contract = HOW): the operating mechanics for
  the Brain, repository, execution, review, and publication system.

The ChatGPT Project Contract is subordinate to the Constitution and Product Contract and may
not silently override them. Phase and architecture documentation is subordinate to these
contracts, and TASK contracts are subordinate to every preceding enforceable layer.
Implementation and execution evidence cannot amend higher governance. Lower layers may refine
higher layers only without silently overriding them.

The Manifesto remains the highest interpretive philosophy and never becomes executable conflict
authority. Any deliberate constitutional departure from the Manifesto requires explicit Human
amendment intent and corresponding reconciliation rather than silently treating the Manifesto as
an executable precedence layer.

### Three Operating Dimensions

Rather than collapsing governance, intent, and repository state into a single mixed truth
list, Python Agent distinguishes three separate questions without allowing any one category
to silently override the others outside its authority:

1. **Human Mandate:**
   `HUMAN_PRINCIPAL` owns current mandate, priority, risk envelope, delegation, suspension,
   amendment initiation, and explicit supersession intent. Human intent operates
   prospectively; it does not silently rewrite canonical engineering or domain state, bypass
   an admitted governance or domain mutation path, or retroactively authorize prior actions.
   Canonical effects occur only through the relevant authorized path.

2. **Governance Precedence:**
   Governance conflicts follow higher enforceable governance in the canonical order:
   Constitution -> Product Contract -> ChatGPT Project Contract ->
   phase/architecture documentation -> TASK contracts. The Manifesto remains the highest
   interpretive philosophy and never becomes executable conflict authority. Any deliberate
   constitutional departure from the Manifesto requires explicit Human amendment intent and
   corresponding reconciliation rather than silently treating the Manifesto as an executable
   precedence layer. Lower layers may refine higher layers only without silently overriding
   them. Engineering evidence cannot amend higher governance.

3. **Engineering-State Truth:**
   Engineering-state truth is established by current canonical `python_complete_agent`
   repository state plus exact immutable TASK/RUN/RESULT/FAILURE/REVIEW/REMEDIATION/REPAIR
   and publication lineage.

Chat memory, project instructions, previous chats, and general model memory are advisory only.
They are never engineering-state truth, roadmap authority, or governance law.

### Constitutional Roles and Operating Actors

The seven constitutional roles map to current concrete operating actors without redefining
the roles or introducing new authority:

- `HUMAN_PRINCIPAL` -> Human.
- `ARCHITECT` -> ChatGPT Brain while framing architecture, roadmap, and TASK contracts
  within Human mandate.
- `DOMAIN_AUTHORITY` -> each existing canonical product/governance semantic owner for an
  explicitly assigned capability.
- `EXECUTION_RUNTIME` -> pinned AIOS Runtime for deterministic lifecycle, admission,
  verification, and evidence mechanics.
- `EXECUTOR` -> exactly one selected Codex or Antigravity executor for an admitted scope.
- `SEMANTIC_REVIEWER` -> ChatGPT while issuing the independent semantic verdict for an
  admitted review scope.
- `SOURCE_PUBLISHER` -> repository-owned source publisher for the exact admitted and reviewed
  source candidate only.

ChatGPT may occupy `ARCHITECT` and `SEMANTIC_REVIEWER` at different lifecycle stages, but
co-location does not merge their authorities. Co-location must never grant implementation,
execution, review-bypass, or publication power to ChatGPT. Every action must remain
attributable to the role whose authority permits it. Runtime or worker state must never
auto-advance the Brain's roadmap or adoption planning state.

### Bounded Delegation and Authority Boundaries

`CAPABILITY_IS_NOT_AUTHORITY` is operational law. Tool access, repository write capability,
model intelligence, successful execution, evidence possession, upstream AIOS feature
availability, or convenience never grants product truth, roadmap, semantic review, approval,
publication, domain ownership, or canonical mutation authority.

`ONE_CAPABILITY_ONE_AUTHORITY` is operational law: every proposed new semantic capability must
resolve exactly one existing or explicitly migrated canonical owner before canonical mutation
proceeds. Composition or introduction of a tool, model, interface, agent, runtime, or
automation layer does not create a second owner.

Bounded delegation requires that every delegated action remain strictly inside an explicit
mandate or envelope and applicable mutation authority. Absent, ambiguous, or conflicting
delegation fails closed for the affected canonical mutation. The Project Contract creates no
general Human bypass around admitted governance or domain mutation paths.

### Conflict Handling

The Constitution's three conflict classes have fail-closed operating handling without
inventing a second precedence system:

- `GOVERNANCE_CONFLICT`: disagreement among canonical governance layers follows higher
  enforceable governance (Constitution over Product Contract over Project Contract over
  phase docs over TASK contracts), while the Manifesto remains the highest interpretive
  philosophy and never becomes executable conflict authority.
- `AUTHORITY_CONFLICT`: exists when multiple actors or components claim the same semantic
  ownership, or a mutation has no resolvable owner. The affected canonical mutation fails
  closed until ownership is reconciled.
- `EVIDENCE_CONFLICT`: exists when sources or observations disagree. No recency, majority,
  model, or convenience rule chooses factual truth unless the owning domain authority acts.
  Evidence conflicts remain explicit evidence and are never converted into factual verdicts
  or governance shortcuts.

## 3. AIOS Runtime Authority

Python Agent uses only the AIOS-renew version pinned by:

```text
.agents/skills/aios-worker/requirements-aios-renew.txt
```

TASK-179 established the historical downstream authority
`883974be6ec5922ae57021b50a48c84a0014dbfa`. TASK-183 migrated the prior exact
authority to `08e4a612377ac82be36061286a34138ea53ab0d1`, TASK-184 migrated it to
`e72135cd5c5a1dec0d8374d9bb8994da5e458feb`, TASK-192 migrated it to
`2599202afedb0622e9e9bdc7b5a15f34da01cc27`, TASK-198 migrated it to
`a3b723b49cd65677f548c5694a52a6fc006a9e2a`, and TASK-201 migrates the sole active
authority to the reviewed, source-published commit
`f0237a3b98985ce6ebbaf41af1e06fa3eb4e998e`. Python Agent consumes established K0 and
post-K0 Runtime behavior plus TASK-086 Unified State, TASK-087 Unified Human Surface,
TASK-088 missing-local-TASK pre-resolution, TASK-089 `CONTINUE_IMPLEMENTATION`, TASK-090
safe-publication compatibility, TASK-091 revision 2, TASK-092 native instructions,
TASK-093 through TASK-100, TASK-102, published TASK-103 correction-frontier hardening,
TASK-101 revision 4 Performance Closure, recovered TASK-104/TASK-105 Brain Authoring
Ingress, and TASK-106 package-level Human-surface presentation hardening plus TASK-113
package compatibility only through that exact pin and its public
operator surfaces. For a syntactically valid requested TASK whose
canonical local TASK file is absent, pinned CONTINUE may use the bounded
TASK-062-governed pre-resolution synchronization before Unified State loads the TASK,
then derive state from fresh synchronized repository state. Existing local TASKs gain
no automatic synchronization path; `state` and STATUS remain read-only for product
state; unsafe repository states fail closed; and the downstream surfaces add no
synchronization implementation, retry, reroute, recursive continuation, or second
lifecycle operation. TASK-089 semantic selection, TASK-090 publication behavior, and
all Runtime validation remain inside the pinned distribution. Python Agent does not
copy AIOS-renew workflow files, create a second state machine, or automatically expose
every upstream operator command. In particular, availability of a third Executor backend
inside the kernel creates no new Python Agent Human-facing Executor surface.

TASK-092 is adopted only through the exact pin. Its Codex and Antigravity adapters are
the native Executor instruction authority for `CONTINUE_IMPLEMENTATION`; the downstream
launcher contains no local action parser, native prompt implementation, repair dispatcher,
or second state machine. The admitted Executor resumes necessary bounded unfinished original
TASK work from the exact failed lineage, including bounded discovery/live capture when part
of that unfinished work, and must commit the permitted in-scope implementation state on
success. This grants no fresh PRIMARY, automatic retry, fallback, reroute, scope widening,
recursive continuation, semantic review, or Executor-owned canonical verification or
EVIDENCE authority. Brain retains semantic classification, and Runtime retains lifecycle,
completion, canonical verification, and EVIDENCE authority.

The TASK-198-era `a3b723b49cd65677f548c5694a52a6fc006a9e2a` installation,
the TASK-102-era `2599202afedb0622e9e9bdc7b5a15f34da01cc27` installation, and every
older installation are stale after this migration and must be atomically replaced under
the existing exact source-and-commit provenance boundary.

The active runtime must never be inferred from current AIOS-renew main.

An AIOS-renew improvement does not exist for Python Agent until the Python Agent repository explicitly updates and certifies its pin.

`.ai/aios-adoption-state.yaml` is the canonical Brain-readable adoption registry and
`.ai/roadmap-state.yaml` is the canonical Python Agent planning bookmark. They are
planning/governance state, not proof of Runtime PASS, source publication, or downstream
certification. TASK-083 roadmap sequencing is ported as repository governance. TASK-103 and
TASK-101 revision 4 are `ADOPTED_BY_PIN`; TASK-104/TASK-105 are one recovered Brain
Authoring Ingress capability with post-TASK-105 semantics authoritative for safe new
operations. TASK-106 and TASK-113 package compatibility are `ADOPTED_BY_PIN`.
Upstream planning checkpoint `e95d12122f35bf4e224dbbb28be1866c8250c069`
is separately recorded audit evidence and is never runtime authority. Mutable AIOS-renew
main is never downstream pin authority; future AIOS-renew main changes remain irrelevant
until another explicit reviewed downstream migration.

Brain authoring for this repository must use the checked-in
`.agents/skills/aios-worker/scripts/aios_brain_ingress.py` carrier with one caller-authored
canonical ingress-envelope file. The carrier proves the same pinned distribution used by the
workers and delegates only to `aios_renew.operator ingress` with the repository root resolved
from the carrier's checked-in location. It accepts no caller-selected repository or raw Git
destination and may not use an ambient executable, global/site package, mutable upstream
checkout, or current AIOS-renew main. The carrier is transport and provenance only: the pinned
post-TASK-105 ingress owns envelope validation, canonical destinations, and valid idempotency.
The carrier owns no TASK/REVIEW meaning, lifecycle selection, Executor invocation, semantic
review, remediation decision, publication, roadmap mutation, retry, reroute, or second state
machine. These authoring operations are not exposed through Human-facing worker surfaces.

Repository-native semantic review and source-only publication remain separate from
execution. `.github/workflows/aios-auto-publish.yml` continues to consume the same
checked-in requirements file and gains no review or publication authority from this
migration.

RUN-197-001, candidate `8992e64654b1342a70ad37c9c0aa693ce537a975`,
REVIEW-197-001, and malformed decision `f334312384543dd4726e83089601e375dd5da17b`
remain immutable incident lineage. The semantic PASS does not repair or authorize the
structurally malformed decision; it must not be rewritten, certified, or published, and
TASK-197 revision 1 must not resume through it.

TASK-179 does not establish a live stale-checkout CONTINUE proof or complete AIOS-renew
Downstream Adoption. That proof remains pending a fresh downstream task authored and run
after TASK-179 is published.

TASK-183 historically adopted TASK-089/TASK-090 at the predecessor pin. TASK-184 migrates
only the execution substrate to reviewed TASK-092. It does not continue TASK-182 or claim
that TASK-182 has resumed, passed, been reviewed, or been published. RUN-182-003 remains
the canonical failed lineage under the predecessor adapter; only a later separately
authorized continuation may act on it.

## 4. Human-facing Worker Boundary

The unified semantic protocol is:

```text
CONTINUE TASK-N
STATUS TASK-N
RUN TASK-N
FIX TASK-N FINDING-ID
REPAIR RUN-N-NNN
```

`CONTINUE TASK-N` is the normal Human lifecycle command. It delegates next-action
selection solely to the exact pinned AIOS-renew Unified Human Surface. `STATUS TASK-N`
is the read-only, versioned Unified State inspection command. RUN, FIX, and REPAIR
remain explicit compatibility/debug escape hatches, not a normal requirement for the
Human to reconstruct low-level lifecycle state or selectors.

Antigravity surface:

```text
/aios-renew-worker ...
```

Codex surface:

```text
$aios-worker ...
```

The visible surface selects one executor identity and may not reroute to the other.
That identity is Human selection available to the pinned kernel; it does not force a
coding Executor for a canonical action whose `executor_required` value is false.

Normal Human guidance must use these worker surfaces.

Internal commands such as:

```text
aios run
aios continue
aios state
aios remediate
aios repair
raw codex
raw Antigravity executor invocation
manual local artifact courier
```

are implementation details and must not be exposed unless explicitly debugging the AIOS integration layer.
One CONTINUE surface invocation delegates at most one pinned canonical operation and
passes through bounded `AIOS_HUMAN_SURFACE` output. The downstream launcher must not
call state first, parse output to select another action, retry, reroute, poll, or
recursively continue.

## 5. Product Architecture Authority

The Product Contract (`docs/PYTHON_AGENT_PRODUCT_CONTRACT.md`) is the sole durable product
WHAT authority. Brain task design, review, and operating guidance must defer product and domain
meaning to the Product Contract plus the existing lower canonical owner for the exact
capability.

This Project Contract governs operating mechanics (HOW) and does not redefine algorithms,
schemas, truth, ranking, approval, identity, persistence, retrieval, evidence, intelligence,
decision/action, outcome/learning, or other product semantics.

Every capability must have one explicit owner (`ONE_CAPABILITY_ONE_AUTHORITY`).

Before creating a new module/API/task, identify which previous TASK already owns adjacent semantics.

Do not duplicate:

- canonical identity authority;
- catalog integrity;
- persistence authority;
- evidence projection;
- retrieval semantics;
- RAG context semantics;
- ranking/business scoring;
- Human approval/admission authority.

New tasks extend boundaries; they do not silently redefine earlier boundaries.

## 6. Evidence / Product Truth Separation

Epistemic and decision boundaries established by the Constitution and Product Contract must
be strictly preserved across all operating stages:

Product observations may conflict.

Evidence preservation is not product-truth reconciliation (`EVIDENCE_IS_NOT_PRODUCT_TRUTH`,
`EVIDENCE_CONFLICT`).

Retrieval relevance is not product ranking (`RETRIEVAL_IS_NOT_RANKING`).

Business ranking is not entity identity.

RAG context is not answer truth (`CONTEXT_IS_NOT_TRUTH`).

Model-generated output must never silently become canonical product truth.

When designing future Product Intelligence layers, preserve these boundaries unless an explicit
task introduces a new authority. Evidence conflicts remain explicit evidence and are never
converted into factual verdicts or governance shortcuts.

## 7. Task Design Audit

Before authoring or revising TASK-N:

1. Read current main.
2. Read the full applicable Governance Foundation (`docs/PYTHON_AGENT_MANIFESTO.md`,
   `docs/PYTHON_AGENT_CONSTITUTION.md`, `docs/PYTHON_AGENT_PRODUCT_CONTRACT.md`, and this contract).
3. Identify current phase/milestone from roadmap state and canonical lineage.
4. Identify the proposed new authority and exact current semantic owner (`ONE_CAPABILITY_ONE_AUTHORITY`).
5. Search repository docs/tasks/modules for duplicate or overlapping authority.
6. Read direct predecessor TASK contracts and non-goals/deferred work.
7. Read current implementation boundary.
8. Classify proposed work as:
   - new capability;
   - hardening;
   - regression;
   - integration;
   - or duplicate / authority-conflicting work.
9. Reject duplicate or authority-conflicting work (fails closed).
10. Only then author or revise TASK-N.

New Human intent is a new or revised TASK contract, not a FIX of unrelated lineage.
Never generate the next task only from a remembered roadmap, chat memory, or mutable upstream AIOS main alone.

## 8. Execution Semantics

### Normal lifecycle

Use worker `CONTINUE TASK-N`. Pinned TASK-086/TASK-087 Unified State and Next Action
own exact lifecycle selection, handoff/no-action, blocked/done, transport/recovery,
and `executor_required` semantics. Brain, Reviewer, and Publisher remain external
authorities when the bounded Human surface requests those handoffs. A successful
execution still stops for independent ChatGPT semantic review before source-only
publication. Runtime PASS is not semantic PASS.

Use worker `STATUS TASK-N` only to inspect bounded `AIOS_UNIFIED_STATE`. STATUS is
read-only and invokes no coding Executor or mutating lifecycle operation.

The explicit paths below are compatibility/debug escape hatches. They do not replace
CONTINUE as normal guidance and do not grant the downstream layer lifecycle-selection
authority.

### PRIMARY

Use worker `RUN`.

### Semantic finding

Use worker `FIX` for the exact finding only.

### Failed admitted RUN

Author canonical REPAIR, then use worker `REPAIR`.

Do not substitute FIX for REPAIR.  
Do not substitute REPAIR for FIX.  
Do not restart PRIMARY after narrow correction.

### Brain REPAIR action preflight for the explicit debug path

Before authoring any REPAIR, the Brain must read the exact canonical FAILURE/candidate facts and classify the required continuation **before** invoking a worker. When action semantics have not already been reconciled in the current chat, the Brain must inspect the exact pinned AIOS-renew runtime rather than infer semantics from memory or current upstream main.

The classification is:

1. **NO_CHANGE**
   - Use only for an eligible completed, unchanged candidate whose continuation requires zero repository mutation and only canonical verification/completion remains.
   - Author `NO_CHANGE` REPAIR with an empty modification scope and preserve the exact failed candidate HEAD.
   - Unfinished original implementation that still requires mutation is not `NO_CHANGE`, even when no defect has been established.

2. **CODE_FIX**
   - Use only when canonical failure, verification, or review evidence has established a concrete product/code defect requiring repository correction.
   - Author `CODE_FIX` REPAIR only with the minimum non-empty correction scope necessary for that established defect.
   - The correction must produce a real committed delta descending from the exact failed head.

3. **CONTINUE_IMPLEMENTATION**
   - Use only for an admitted, repairable, pre-verification failed RUN where the original implementation is unfinished, no product/code defect is asserted or established, and the remaining authorized work requires repository mutation.
   - Human/Brain must have a new reason to permit another attempt because an external/Human non-defect prerequisite changed. Brain records that reason and authors the semantic action; neither Runtime nor a worker may probe the prerequisite or infer the action from diagnostic prose.
   - Preserve the exact failed RUN, TASK revision, `failed_head_sha`, and root lineage. Author a non-empty explicit modification scope and select one explicit Executor.
   - The selected native Executor resumes necessary bounded unfinished original TASK work, including discovery/live capture when part of that unfinished work, and must commit the permitted in-scope implementation state on success.
   - This is one separately authorized continuation, never an automatic retry, fresh PRIMARY, fallback, reroute, or recursive lifecycle call.
   - It grants no scope widening, semantic review, or Executor-owned canonical verification or EVIDENCE authority.

4. **RUNTIME_OR_LINEAGE_DEFECT**
   - Use when the failure indicates AIOS/runtime/control-plane behavior, ambiguous lineage, an untransportable candidate, stale recovery assumptions, or when none of `NO_CHANGE`, `CODE_FIX`, or `CONTINUE_IMPLEMENTATION` is safe.
   - Do not fabricate a CODE_FIX, CONTINUE_IMPLEMENTATION, or product mutation.
   - Audit the recovery boundary and use Cross-project Escalation when the pinned AIOS runtime is the probable defect owner.

REPAIR action selection is fail-closed:

- Never choose `CODE_FIX` merely to keep open the possibility of editing later.
- Never use `NO_CHANGE` for unfinished implementation or `CONTINUE_IMPLEMENTATION` for an established product/code defect.
- Never pair `CODE_FIX` with instructions such as “do not edit if verification passes”, “verify unchanged candidate first”, or any other intended zero-delta continuation.
- The pinned Runtime may enforce the REPAIR mutation gate before Runtime-owned verification. Therefore a candidate that merely needs verification continuation must use `NO_CHANGE`; `CODE_FIX` cannot be used as a speculative verify-then-maybe-edit container.
- Never manufacture an empty/no-op/format-only commit solely to satisfy a `CODE_FIX` HEAD-advance gate.
- If a `NO_CHANGE` REPAIR reaches verification and verification then proves a concrete defect, preserve that failed RUN as canonical evidence and author the **next** REPAIR as `CODE_FIX` against that new failed RUN.
- Runtime validates the selected REPAIR structure and owns execution and verification; it does not select `CONTINUE_IMPLEMENTATION` semantically or probe an external/Human prerequisite.
- Preserve the executor identity selected by the failed lineage unless explicit canonical Human intent requires a different boundary; never silently reroute during REPAIR.
- REPAIR instructions, action, and modification scope must agree with one another. If they are semantically contradictory, do not invoke a worker until the REPAIR contract is corrected.

### Mutable live-evidence authoring boundary

When mutable marketplace evidence can be staged through a repository-owned operational surface,
engineering TASK implementation and Runtime verification consume reviewed, frozen evidence instead
of requiring an Executor to acquire live marketplace evidence. Human access/session work belongs to
that operational plane; deterministic implementation and verification belong to the engineering
plane. `CONTINUE_IMPLEMENTATION` remains an exceptional recovery safety net, not the normal Human
access/session workflow. Any exception requires explicit current Human intent and TASK-specific
architecture justification.

## 9. Review Semantics

Reviewer issues an independent semantic verdict for the admitted review scope. Runtime PASS is
not semantic PASS. Reviewer verdict grants no source-mutation or publication authority.

### PRIMARY review

Review TASK + candidate + evidence.

### DELTA review

Review only prior finding/repair delta plus directly introduced defect risk.

Do not re-review the entire task after every correction.

### REPAIR after failed FIX

A REPAIR that continues a failed FIX remains a **DELTA semantic review** of the preserved finding/correction continuity; it does not become a new PRIMARY review merely because the Runtime operation is REPAIR.

Before materializing the review-decision for this lineage, the Brain must reconcile the review metadata with the **exact pinned AIOS publication validator** when the lineage shape differs from an ordinary successful FIX.

For the current pinned Runtime:

- Preserve the finding lineage through the canonical prior REVIEW, REMEDIATION, failed FIX RUN/FAILURE, REPAIR authorization, and successful REPAIR RUN artifacts.
- Do not add `prior_finding_id` to the final REPAIR review-decision unless the exact publication validator can resolve a canonical `prior_review` for that source run.
- If the validator cannot resolve such a `prior_review`, keep `mode: DELTA`, record only the acceptance criterion actually re-reviewed, omit `prior_finding_id`, and rely on the canonical lineage artifacts for finding continuity.
- Never change the source candidate or rerun verification merely to make review-decision metadata publishable.
- A publication-schema mismatch is control-plane metadata work, not a new product finding.

### Review/remediation authoring preflight

Before invoking FIX or publishing a DELTA decision, fail closed on structural metadata:

- every finding `basis` must be an exact acceptance ID supported by the relevant review contract;
- remediation `constraints` must be empty or an exact allowed subset of the TASK hard constraints under the pinned Runtime contract; do not paraphrase new Human intent into remediation constraints;
- nonstandard lineage such as REPAIR-after-FIX must be checked against the exact pinned publication semantics before materializing the final review-decision.

## 10. Publication

After semantic PASS, publish the reviewed source candidate only.

Never publish:

- review-decision commit;
- artifact branch;
- failure branch;
- remediation metadata branch.

Review-decision, artifact, failure, or remediation metadata must never be published as implementation.
Do not rerun verification solely before publication if reviewed evidence remains valid.

## 11. Cross-project Escalation

If a Python Agent RUN exposes a probable AIOS-renew kernel defect:

1. Preserve the Python Agent RUN/FAILURE evidence.
2. Do not modify AIOS kernel from the Python Agent project.
3. Open the AIOS-renew ChatGPT Project.
4. `SYNC PROJECT` there.
5. Audit/design the kernel correction against AIOS current main.
6. Publish the AIOS correction.
7. Return to Python Agent.
8. Create a separate Python Agent migration/update task if the pinned kernel should advance.

Preserve cross-project isolation: a probable AIOS kernel defect discovered from Python Agent
must retain downstream evidence, be corrected under AIOS-renew authority, and require a
separate explicit Python Agent migration before any new upstream source becomes downstream
runtime authority. Never automatically propagate AIOS main changes into Python Agent.

## 12. Brain Sync Protocol

For a new ChatGPT chat, before roadmap, TASK, review, repair, publication, or architecture decisions:

1. Read the full Governance Foundation:
   - `docs/PYTHON_AGENT_MANIFESTO.md`
   - `docs/PYTHON_AGENT_CONSTITUTION.md`
   - `docs/PYTHON_AGENT_PRODUCT_CONTRACT.md`
   - `docs/CHATGPT_PROJECT_CONTRACT.md` (this contract)
2. Read current Python Agent main.
3. Read current AIOS dependency pin (`.agents/skills/aios-worker/requirements-aios-renew.txt`).
4. Read `.ai/roadmap-state.yaml`.
5. Read `.ai/aios-adoption-state.yaml`.
6. Read the current Product Intelligence and phase roadmaps,
   `docs/POST_M4_PRODUCT_INTELLIGENCE_ROADMAP.md` and
   `docs/POST_P5_P6_QUALITY_SCALE_ROADMAP.md`, including the current product/phase
   document selected by those roadmaps.
7. Reconcile the unique roadmap `next` pointer and every relevant adoption classification
   with current main, the exact pin, and relevant immutable TASK/RUN/RESULT/FAILURE/REVIEW/
   REMEDIATION/REPAIR and publication lineage.
8. Determine the last published implementation and the unique next authored TASK, if any.
9. Use the repository-owned `STATUS TASK-N` surface for read-only Unified State
   inspection and `CONTINUE TASK-N` for the normal lifecycle step.
10. When the explicit debug path requires REPAIR and action semantics are not already reconciled in the current chat, inspect the exact pinned AIOS runtime before selecting `NO_CHANGE`, `CODE_FIX`, or any successor action vocabulary.
11. When review/publication follows a nonstandard lineage such as REPAIR-after-FIX, inspect the exact pinned publication semantics before materializing review-decision fields that depend on prior-review resolution.
12. Produce SYNC CHECKPOINT.

Brain Sync requires the full Governance Foundation, current main, the exact pin, and relevant
canonical lineage before making semantic decisions. It must keep Human mandate, governance
precedence, engineering-state truth, roadmap planning state, and adoption planning state
distinct; conflicts fail closed rather than being guessed from chat memory or mutable upstream
main.

Generic Human intent such as "continue roadmap" resolves only from the reconciled single
`next` pointer. It must never be inferred from the numerically latest TASK, Human memory,
previous-chat context, or current AIOS-renew main. If either governance file is missing,
malformed, ambiguous, or conflicts with engineering lineage, stop before roadmap selection
or TASK authoring and report exactly `ROADMAP/ADOPTION SYNC BLOCKED`; do not guess.

Expected checkpoint:

```text
PROJECT: Python Agent
MAIN: <sha>
AIOS PIN: <sha>
ROADMAP NEXT: <task or none>
RETURN TO: <milestone or none>
ADOPTION AUDIT: <checkpoint>
PHASE: <phase>
LAST PUBLISHED: <task>
AUTHORED NEXT TASK: <task or none>
ACTIVE RUN: <run or none>
ACTIVE FINDING: <finding or none>
ACTIVE FAILURE: <run or none>
STATE: READY | ROADMAP/ADOPTION SYNC BLOCKED | BLOCKED
```

Never infer these values solely from chat memory, the latest TASK, or Runtime/worker state.
