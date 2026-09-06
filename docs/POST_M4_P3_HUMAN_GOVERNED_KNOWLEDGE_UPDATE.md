# Post-M4 P3 Human-Governed Knowledge Update Workflow

Status: **CLOSED**; P3.1 family review planning, P3.2 family decision plus
durable admission, and P3.3 sellable-variant review plus durable admission are
closed by TASK-139, TASK-140, and TASK-141 respectively.

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

### P3.3 — Sellable-variant review + durable admission — CLOSED

TASK-141 accepts one exact admitted canonical family and one explicit
caller-selected member tuple. It delegates proposal construction unchanged to
TASK-116 and retains that exact proposal in an immutable, factory-only Human
review value. Member selection remains explicit: TASK-141 never discovers,
ranks, repairs, or recommends a variant set. TASK-115 remains the sole evidence
and exactness-diagnostic authority, and TASK-116 remains the sole selection,
closure, singleton, proposal, and Human variant-decision authority.

Decision recording delegates the exact reviewed proposal and explicit Human
`APPROVE` or `REJECT`, actor, and timezone-aware decision time to TASK-116. A
separate durable-admission call proves exact proposal object lineage, then
delegates the exact decision and caller-supplied opaque `variant_id` to TASK-117
and the exact admitted variant and database path to TASK-120. TASK-117 remains
the sole canonical variant-admission and variant-ID validation authority;
TASK-118 remains the sole catalog-integrity authority; TASK-119 remains the sole
catalog codec/rehydration authority; and TASK-120 remains the sole SQLite
transaction and durability authority.

An explicit variant `REJECT` remains an exact in-memory TASK-116 decision record,
fails admission only through TASK-117, and creates no durable variant mutation.
TASK-141 adds no independent durable REJECT-history authority.

P3 is closed as an application-composition boundary, not a replacement semantic
layer. Family and variant ID allocation, identity evolution or membership
extension, conflict repair and singleton family admission, product-truth
reconciliation, durable REJECT history, and autonomous approval remain deferred
non-blocking future work. The next current post-M4 boundary is P4 Live
Grounded-QA Provider Certification.

## Staged authority map

| Stage | Input | Existing semantic owner | Output / side effect |
|---|---|---|---|
| P3.1 planning | Exact TASK-138 inventory | TASK-109 → TASK-111 → TASK-112 proposal construction | In-memory review plan only |
| P3.2 family decision | Exact planned family proposal + explicit Human fields | TASK-140 composition → TASK-112 | Human decision record only |
| P3.2 family admission | Exact planned decision + caller-supplied opaque `family_id` | TASK-140 composition → TASK-114 → TASK-118/TASK-119/TASK-120 | Canonical family and durable registration result |
| P3.3 variant review and decision | Exact admitted family + explicit member selection and Human fields | TASK-141 composition → TASK-115/TASK-116 | Exact proposal review and Human decision record only |
| P3.3 variant admission | Exact reviewed APPROVE + caller-supplied opaque `variant_id` | TASK-141 composition → TASK-117 | Canonical variant value |
| P3.3 durable registration | Exact admitted variant + exact database path | TASK-141 composition → TASK-118/TASK-119/TASK-120 | Validated catalog/SQLite mutation and unchanged registration status |
