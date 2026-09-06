# Post-M4 P3 Human-Governed Knowledge Update Workflow

Status: **IN PROGRESS**; P3.1 family review planning and P3.2 family decision
plus durable admission are closed by TASK-139 and TASK-140 respectively.

## Boundary

P3 is a staged application-composition boundary over existing M3 authorities. It
does not create a new resolution, grouping, proposal, Human-decision, admission,
catalog, or persistence authority.

### P3.1 — Family review planning — CLOSED

TASK-139 accepts one exact TASK-138 `SourceEvidenceInventory` and composes the
existing authorities in their canonical order:

1. TASK-109 resolves the inventory's exact typed source-pack tuple.
2. TASK-111 groups that exact resolution graph and keeps every group visible,
   including `SINGLETON` and `CONFLICTED` groups.
3. TASK-112 creates an evidence-complete family merge proposal for every and only
   conflict-free `POSITIVE_CONNECTED` group, in TASK-111 group order.

The result is an immutable in-memory review plan retaining the exact inventory,
resolution graph, canonical group tuple, and exact actionable proposal objects.
It makes no Human decision, creates no canonical identity, and performs no
durable write.

### P3.2 — Family decision + durable admission — CLOSED

TASK-140 binds one explicit Human decision to the exact TASK-112 proposal object
retained exactly once by a TASK-139 review plan. Decision recording delegates to
TASK-112 unchanged. A separate durable-admission call delegates the exact decision
and caller-supplied opaque `family_id` to TASK-114, then forwards the exact admitted
family to TASK-120. TASK-118 remains the sole catalog-integrity authority, TASK-119
the sole catalog codec authority, and TASK-120 the sole SQLite transaction and
durability authority.

An explicit `REJECT` remains a valid in-memory TASK-112 decision record, but cannot
pass TASK-114 admission and has no durable catalog side effect. P3.2 introduces no
independent durable Human-decision history authority.

### Next P3 stage — not implemented by TASK-140

The immediate next stage is sellable-variant Human review and decision followed
by durable variant admission through TASK-115, TASK-116, TASK-117, TASK-118,
TASK-119, and TASK-120. TASK-117 continues to own admission under an explicit
caller-supplied opaque `variant_id`.

Family and variant ID allocation remains deferred. P3 does not infer Human intent,
automatically approve proposals, reconcile product truth, repair conflicts, admit
singletons, extend existing identities, or introduce another catalog or persistence
model.

## Staged authority map

| Stage | Input | Existing semantic owner | Output / side effect |
|---|---|---|---|
| P3.1 planning | Exact TASK-138 inventory | TASK-109 → TASK-111 → TASK-112 proposal construction | In-memory review plan only |
| P3.2 family decision | Exact planned family proposal + explicit Human fields | TASK-140 composition → TASK-112 | Human decision record only |
| P3.2 family admission | Exact planned decision + caller-supplied opaque `family_id` | TASK-140 composition → TASK-114 → TASK-118/TASK-119/TASK-120 | Canonical family and durable registration result |
| Variant review and decision | Admitted family + explicit member selection and Human fields | TASK-115/TASK-116 | Evidence, proposal, and Human decision |
| Variant admission | Approved decision + caller-supplied opaque `variant_id` | TASK-117 | Canonical variant value |
| Durable registration | Exact admitted values | TASK-118/TASK-119/TASK-120 | Validated catalog/SQLite mutation |
