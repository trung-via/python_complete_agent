# REVIEW-015 — TASK-015 (AIOS Bridge v0.5-M2 Deterministic ContextBuilder + Token Budget)

## Status
CHANGES_REQUIRED

## Reviewed Head
- Branch: `ai/task-015`
- Reviewed commit: `de078afe635629b619ec4c991d5295db7ab815ef`
- Canonical baseline: `34b331c75d0577e403bb80b2ba0fe9818183b4f9`
- Branch relation to main: ahead 1, behind 0; merge base exactly canonical baseline
- RESULT-015 status: `READY_FOR_REVIEW`

## Verification Recorded in RESULT-015
- Focused External Brain suite: **41 passed**
- Full repository suite: **515 passed**
- No live external-model request was made
- No protected Bridge/runtime-provider subsystem was changed

## Overall Review
The M2 implementation is structurally strong and remains within the locked scope:
- `TokenCounter` is injectable and the default UTF-8 byte counter is explicitly non-exact;
- `ContextBudget` is immutable and validates reserve/budget constraints;
- canonical framing is centralized in `render_context_item()`;
- SHA-256 integrity mismatches fail closed;
- high-confidence sensitive paths/private-key markers fail closed without echoing secret content;
- TASK is required and TASK/CONTRACT are mandatory;
- mandatory overflow fails closed with no truncation;
- exact duplicate identities are audited;
- optional selection is atomic greedy and later smaller candidates may fit after an oversized one is skipped;
- selected/excluded audit records and context fingerprint exist;
- no repository crawling, LLM ranking, embeddings, Gateway, provider, HTTP, router, fallback, quota logic, or usage ledger was introduced.

One deterministic-ranking contract defect remains.

---

## Blocker — Ranking uses raw path instead of the ADR-006 normalized-path tie-break

ADR-006 locks the optional ranking key as:

```text
1. higher ContextItem.priority first
2. higher kind precedence first
3. normalized path lexicographically
4. computed content SHA-256 lexicographically
```

It also locks mandatory TASK/CONTRACT ordering by:

```text
higher priority -> normalized path -> digest
```

The current implementation sorts mandatory and optional candidates with raw `item.path or ""`:

```python
task_items.sort(key=lambda t: (-t[0].priority, t[0].path or "", t[1]))
contract_items.sort(key=lambda t: (-t[0].priority, t[0].path or "", t[1]))

optional_items.sort(
    key=lambda t: (
        -t[0].priority,
        -_KIND_PRECEDENCE.get(t[0].kind, 0),
        t[0].path or "",
        t[1],
    )
)
```

This is observably different for Windows-style vs canonical forward-slash paths. For example, raw lexical ordering of:

```text
src\\b.py
src/a.py
```

is not the same as ordering after separator normalization:

```text
src/b.py
src/a.py
```

Since the repository runs on Windows and future candidate collectors may naturally supply backslash paths, this can make selection order/budget winners depend on path spelling rather than the locked deterministic policy.

### Required Fix
Add one small, pure, OS-independent path-normalization helper for **ranking only**, for example conceptually:

```python
def _normalized_sort_path(path: str | None) -> str:
    return (path or "").replace("\\", "/")
```

Use the same helper in:
- mandatory TASK ordering;
- mandatory CONTRACT ordering;
- optional ranking path tie-break.

Do **not** use platform-dependent filesystem resolution, `resolve()`, file I/O, repository crawling, or case-normalization that changes path semantics. The goal is only deterministic separator normalization for the locked lexical tie-break.

Do not change the canonical dedupe identity `(kind, path-or-empty, sha256)` unless ADR-006 is separately revised; this review concerns ranking/order, not identity equivalence.

### Required Regression Tests
Add focused tests proving:
1. equal-priority/equal-kind optional items with mixed `\\` and `/` separators sort according to normalized `/` path order;
2. mandatory TASK items with mixed separators use normalized path tie-break order;
3. mandatory CONTRACT items with mixed separators use normalized path tie-break order;
4. input permutation still produces identical selected order and fingerprint;
5. atomic budget selection follows that normalized ranking when only one of two equal-priority candidates can fit.

---

## Non-Blocking Reporting Note
`RESULT-015` lists all six changed implementation/test paths correctly, but its displayed `Diff Stat` only shows two modified files and omits the newly added `budget.py`, `context.py`, and their tests. This does not affect the code decision, but please regenerate/correct the diff stat when updating RESULT-015 after the fix so the review artifact is internally consistent.

---

## Scope Guard
The fix MUST remain inside M2 deterministic context/budget logic and tests. Do not add:
- repository/file discovery;
- AST/import graph traversal;
- content truncation/excerpting;
- embeddings/vector DB;
- LLM-based ranking;
- live model/API/network calls;
- ModelGateway;
- MiniMax/DeepSeek/Kimi provider implementation;
- router/fallback/retry/quota registry;
- usage ledger;
- filesystem/shell/browser/Git execution authority;
- semantic changes to `bridge.py` or `src.providers.LLMProvider`.

## Re-Verification Required
After the fix:
1. run focused `tests/aios_bridge/external_brain/`;
2. run existing bridge tests;
3. run the full repository suite;
4. update `RESULT-015` with exact counts and corrected diff stat;
5. publish the new branch head for re-review.

## Decision
CHANGES_REQUIRED.

The M2 design and implementation are otherwise acceptable. Only deterministic normalized-path ranking must be corrected before approval.

Human fix gate:

`/aios-worker FIX TASK-015`
