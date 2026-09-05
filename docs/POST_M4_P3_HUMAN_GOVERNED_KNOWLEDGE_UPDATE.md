# Post-M4 P3 Human-Governed Knowledge Update Workflow

Status: **IN PROGRESS**; P3.1 family review planning is closed by TASK-139.

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

### Later P3 stages — not implemented by TASK-139

The next P3 boundary is explicit Human family decision followed by durable family
admission through the existing TASK-112, TASK-114, TASK-118, TASK-119, and TASK-120
authorities. TASK-114 continues to require an explicit caller-supplied opaque
`family_id`.

A separate later stage may compose sellable-variant evidence, explicit Human
review and decision, and durable variant admission through TASK-115, TASK-116,
TASK-117, TASK-118, TASK-119, and TASK-120. TASK-117 continues to require an
explicit caller-supplied opaque `variant_id`.

Family and variant ID allocation remains deferred. P3 does not infer Human intent,
automatically approve proposals, reconcile product truth, repair conflicts, admit
singletons, extend existing identities, or introduce another catalog or persistence
model.

## Staged authority map

| Stage | Input | Existing semantic owner | Output / side effect |
|---|---|---|---|
| P3.1 planning | Exact TASK-138 inventory | TASK-109 → TASK-111 → TASK-112 proposal construction | In-memory review plan only |
| Family decision | Exact family proposal + explicit Human fields | TASK-112 | Human decision record only |
| Family admission | Approved decision + caller-supplied opaque `family_id` | TASK-114 | Canonical family value |
| Variant review and decision | Admitted family + explicit member selection and Human fields | TASK-115/TASK-116 | Evidence, proposal, and Human decision |
| Variant admission | Approved decision + caller-supplied opaque `variant_id` | TASK-117 | Canonical variant value |
| Durable registration | Exact admitted values | TASK-118/TASK-119/TASK-120 | Validated catalog/SQLite mutation |
