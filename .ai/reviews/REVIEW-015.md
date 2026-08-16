# REVIEW-015 — TASK-015 (AIOS Bridge v0.5-M2 Deterministic ContextBuilder + Token Budget)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-015`
- Reviewed commit: `25f4dde8912040e5edfe1134f25e876a232b3811`
- Previous reviewed head: `de078afe635629b619ec4c991d5295db7ab815ef`
- Canonical baseline: `34b331c75d0577e403bb80b2ba0fe9818183b4f9`
- RESULT-015 status: `READY_FOR_REVIEW`

## Verification Recorded in Updated RESULT-015
- Focused External Brain suite: **43 passed**
- Full repository suite: **517 passed**
- No live external-model request was made
- Fix delta remains limited to ContextBuilder ranking/tests plus RESULT metadata

## Previous Blocker — RESOLVED
The normalized separator tie-break requested in the prior review is now present through `_normalized_sort_path(path)`, and is applied to mandatory TASK ordering, mandatory CONTRACT ordering, optional ranking, dedupe pre-sort, and exclusion ordering.

Regression coverage now verifies ordinary mixed-separator ordering and atomic budget winner behavior for distinct normalized paths such as `src/a.py` vs `src\\b.py`.

The prior RESULT diff-stat inconsistency is also corrected in the updated result artifact.

---

## Final Blocker — normalized-path collisions still fall back to caller input order

The current sort keys use normalized path and digest, for example:

```python
task_items.sort(key=lambda t: (-t[0].priority, _normalized_sort_path(t[0].path), t[1]))

optional_items.sort(
    key=lambda t: (
        -t[0].priority,
        -_KIND_PRECEDENCE.get(t[0].kind, 0),
        _normalized_sort_path(t[0].path),
        t[1],
    )
)
```

This fixes the original separator-ordering defect, but leaves one deterministic collision case.

Consider two distinct candidates with identical kind, priority, and content SHA:

```text
path A = src\\a.py
path B = src/a.py
```

ADR-006 intentionally keeps dedupe identity based on the **raw path**, so these remain two distinct candidates:

```text
(kind, raw-path, sha256)
```

However, `_normalized_sort_path()` maps both paths to the same ranking value:

```text
src/a.py
```

If their content is also identical, the current complete sort keys are equal. Python sorting is stable, so the final order then inherits caller input order. Because the selected bundle and fingerprint retain the original raw `item.path`, reversing candidate input order can reverse selected order and therefore change `context_fingerprint`.

That violates ADR-006's stronger invariant that equivalent candidate sets produce deterministic selected ordering/fingerprint regardless of caller iteration order.

### Required Fix
Preserve normalized path as the locked semantic path tie-break, but add a deterministic raw-path fallback only when all locked semantic keys collide.

Conceptually:

```python
normalized = _normalized_sort_path(item.path)
raw = item.path or ""

# mandatory
(-priority, normalized, digest, raw)

# optional
(-priority, -kind_precedence, normalized, digest, raw)
```

Equivalent placement of the raw-path fallback is acceptable as long as:
- normalized path remains the primary path tie-break;
- digest remains in the locked ordering;
- raw path is used only as a final deterministic discriminator for otherwise-equal distinct identities;
- no filesystem resolution/case folding is introduced;
- dedupe identity remains unchanged.

Apply the same deterministic fallback anywhere a collection of distinct raw-path identities can otherwise receive equal sort keys and leak caller order, including the pre-dedupe deterministic sort and exclusion ordering where applicable.

### Required Regression Tests
Add a compact collision test using two distinct items whose paths normalize identically, e.g.:

```text
src\\a.py
src/a.py
```

with identical kind, priority, and content.

Prove that:
1. both remain distinct because raw-path dedupe identity is unchanged;
2. reversing input candidate order yields identical `selected` order;
3. reversing input order yields identical `context_fingerprint`;
4. if budget fits only one optional collision candidate, the same raw-path winner is selected regardless of caller input order;
5. existing normalized-path tests and all M2 tests remain green.

---

## Scope Guard
This is a final deterministic tie-break correction only. Do not change:
- dedupe identity semantics;
- `ContextItem` / M1 contracts;
- context rendering;
- token counter/budget semantics;
- secret/integrity gates;
- repository discovery behavior.

Do not add Gateway, provider, networking, router/fallback, embeddings, LLM ranking, truncation, filesystem crawling, or execution authority.

## Re-Verification Required
After the fix:
1. run focused `tests/aios_bridge/external_brain/`;
2. run full repository tests;
3. update RESULT-015 with exact counts and small fix delta;
4. publish the new branch head for re-review.

## Decision
CHANGES_REQUIRED.

The original normalized-path blocker is resolved. Only the normalized-path collision fallback above remains before M2 approval.

Human fix gate:

`/aios-worker FIX TASK-015`
