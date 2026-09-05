# ChatGPT Project Contract — Python Agent / Product Intelligence

Status: Durable project governance  
Scope: ChatGPT Brain behavior for repository `trung-via/python_complete_agent`

## 1. Project Identity

Python Agent is the product.

Its long-term direction is Product Intelligence and the larger Commerce AI System.

AIOS-renew is the execution substrate used to implement this product.  
AIOS-renew does not own Python Agent domain architecture.

## 2. Authority Hierarchy

For current Python Agent truth use:

1. Explicit current Human intent.
2. Current canonical `python_complete_agent` repository state.
3. Exact current phase / architecture documentation.
4. Relevant TASK contracts and implementation authority.
5. Exact AIOS RUN / RESULT / FAILURE / REVIEW / REMEDIATION / REPAIR lineage.
6. This project contract.
7. Project Instructions.
8. Previous chats in this project.
9. General model memory.

Chat memory is advisory only.

## 3. AIOS Runtime Authority

Python Agent uses only the AIOS-renew version pinned by:

```text
.agents/skills/aios-worker/requirements-aios-renew.txt
```

The active runtime must never be inferred from current AIOS-renew main.

An AIOS-renew improvement does not exist for Python Agent until the Python Agent repository explicitly updates and certifies its pin.

## 4. Human-facing Worker Boundary

The unified semantic protocol is:

```text
RUN TASK-N
FIX TASK-N FINDING-ID
REPAIR RUN-N-NNN
STATUS TASK-N
```

Antigravity surface:

```text
/aios-renew-worker ...
```

Codex surface:

```text
$aios-worker ...
```

The visible surface selects one executor identity and may not reroute to the other.

Normal Human guidance must use these worker surfaces.

Internal commands such as:

```text
aios run
aios remediate
aios repair
raw codex
raw Antigravity executor invocation
manual local artifact courier
```

are implementation details and must not be exposed unless explicitly debugging the AIOS integration layer.

## 5. Product Architecture Authority

Every capability must have one explicit owner.

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

Product observations may conflict.

Evidence preservation is not product-truth reconciliation.

Retrieval relevance is not product ranking.

Business ranking is not entity identity.

RAG context is not answer truth.

Model-generated output must never silently become canonical product truth.

When designing future Product Intelligence layers, preserve these boundaries unless an explicit task introduces a new authority.

## 7. Task Design Audit

Before authoring TASK-N:

1. Read current main.
2. Identify current phase/milestone.
3. Identify the proposed new authority.
4. Search repository docs/tasks/modules for that exact authority.
5. Read direct predecessor TASK contracts.
6. Read current implementation boundary.
7. Check non-goals and deferred work.
8. Classify proposed work as:
   - new capability;
   - hardening;
   - regression;
   - integration;
   - or duplicate.
9. Only then author TASK-N.

Never generate the next task only from a remembered roadmap.

## 8. Execution Semantics

### PRIMARY

Use worker `RUN`.

### Semantic finding

Use worker `FIX` for the exact finding only.

### Failed admitted RUN

Author canonical REPAIR, then use worker `REPAIR`.

Do not substitute FIX for REPAIR.  
Do not substitute REPAIR for FIX.  
Do not restart PRIMARY after narrow correction.

### Brain REPAIR action preflight

Before authoring any REPAIR, the Brain must read the exact canonical FAILURE/candidate facts and classify the required continuation **before** invoking a worker. When action semantics have not already been reconciled in the current chat, the Brain must inspect the exact pinned AIOS-renew runtime rather than infer semantics from memory or current upstream main.

The classification is:

1. **CONTINUATION_ONLY**
   - No concrete repository defect requiring mutation has been established.
   - Typical evidence includes executor interruption, transport/control failure, or another non-product failure while the candidate remains clean, repairable, transportable, and within scope.
   - Verification may not yet have run, or there is otherwise no verification/review evidence proving a source/test/doc correction is required.
   - Author `NO_CHANGE` REPAIR with an empty modification scope when supported by the exact pinned runtime.
   - Preserve the exact failed candidate HEAD and use REPAIR to continue canonical verification/completion only.

2. **CODE_CORRECTION_REQUIRED**
   - A concrete defect requiring repository mutation is already established by canonical failure/verification evidence.
   - Author `CODE_FIX` REPAIR only with the minimum non-empty correction scope necessary for that defect.
   - The correction must produce a real committed delta descending from the exact failed head.

3. **RUNTIME_OR_LINEAGE_DEFECT**
   - The failure indicates AIOS/runtime/control-plane behavior, ambiguous lineage, an untransportable candidate, stale recovery assumptions, or another condition not safely correctable as product code.
   - Do not fabricate either a CODE_FIX or a product mutation.
   - Audit the recovery boundary and use Cross-project Escalation when the pinned AIOS runtime is the probable defect owner.

REPAIR action selection is fail-closed:

- Never choose `CODE_FIX` merely to keep open the possibility of editing later.
- Never pair `CODE_FIX` with instructions such as “do not edit if verification passes”, “verify unchanged candidate first”, or any other intended zero-delta continuation.
- The pinned Runtime may enforce the REPAIR mutation gate before Runtime-owned verification. Therefore a candidate that merely needs verification continuation must use `NO_CHANGE`; `CODE_FIX` cannot be used as a speculative verify-then-maybe-edit container.
- Never manufacture an empty/no-op/format-only commit solely to satisfy a `CODE_FIX` HEAD-advance gate.
- If a `NO_CHANGE` REPAIR reaches verification and verification then proves a concrete defect, preserve that failed RUN as canonical evidence and author the **next** REPAIR as `CODE_FIX` against that new failed RUN.
- Preserve the executor identity selected by the failed lineage unless explicit canonical Human intent requires a different boundary; never silently reroute during REPAIR.
- REPAIR instructions, action, and modification scope must agree with one another. If they are semantically contradictory, do not invoke a worker until the REPAIR contract is corrected.

## 9. Review Semantics

### PRIMARY review

Review TASK + candidate + evidence.

### DELTA review

Review only prior finding/repair delta plus directly introduced defect risk.

Do not re-review the entire task after every correction.

## 10. Publication

After semantic PASS, publish the reviewed source candidate only.

Never publish:

- review-decision commit;
- artifact branch;
- failure branch;
- remediation metadata branch.

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

Never automatically propagate AIOS main changes into Python Agent.

## 12. Brain Sync Protocol

For a new ChatGPT chat:

1. Read this contract.
2. Read current Python Agent main.
3. Read current AIOS dependency pin.
4. Read current phase document.
5. Determine last published implementation.
6. Determine next authored TASK, if any.
7. Inspect active RUN / FAILURE / REVIEW / FIX / REPAIR lineage only when relevant.
8. When a failed RUN needs REPAIR and REPAIR action semantics are not already reconciled in the current chat, inspect the exact pinned AIOS runtime before selecting `NO_CHANGE`, `CODE_FIX`, or any successor action vocabulary.
9. Produce SYNC CHECKPOINT.

Expected checkpoint:

```text
PROJECT: Python Agent
MAIN: <sha>
AIOS PIN: <sha>
PHASE: <phase>
LAST PUBLISHED: <task>
AUTHORED NEXT TASK: <task or none>
ACTIVE RUN: <run or none>
ACTIVE FINDING: <finding or none>
ACTIVE FAILURE: <run or none>
STATE: READY | BLOCKED
```

Never infer these values solely from chat memory.
