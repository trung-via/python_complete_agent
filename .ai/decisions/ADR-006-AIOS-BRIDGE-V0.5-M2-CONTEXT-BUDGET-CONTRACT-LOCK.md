# ADR-006 — AIOS Bridge v0.5-M2 Deterministic ContextBuilder + Token Budget Contract Lock

## Status
LOCKED

## Date
2026-08-16

## Preconditions
- ADR-005 External Brain M1 contract is locked.
- TASK-014 is APPROVED at `34b331c75d0577e403bb80b2ba0fe9818183b4f9`.
- At ADR lock time, canonical `main` is still `540f4cb20b56cf72db333192d49ccf6eb295e9c4`; therefore TASK-015 MUST NOT be executed until TASK-014 is present on `main`.

## Objective
M2 adds a deterministic, auditable context-selection layer that reduces external-model input size without changing the M1 logical contracts or giving an external model any repository execution authority.

```text
Antigravity / Bridge
      |
      | bounded candidate ContextItems
      v
Context Safety + Integrity
      |
      v
Exact Dedupe
      |
      v
Deterministic Priority
      |
      v
Token Budget
      |
      v
selected ContextItems + audit report
      |
      v
ModelRequest (future M3 Gateway)
```

### Core invariant
**M2 selects from explicit candidates. It does not crawl the repository.**

Repository/file discovery remains outside External Brain. Antigravity/Bridge may later produce candidates from task-declared files, current diff, tests, and errors, but ContextBuilder itself MUST NOT recursively scan the repo, browser profile, home directory, or arbitrary filesystem.

---

# Decision 1 — Preserve M1 Contracts

M2 MUST NOT weaken or redesign:
- `ContextItem`
- `ModelRequest`
- `ModelResponse`
- `ProviderAdapter`
- `ModelTransport`
- output artifact contracts

Preferred additive files:

```text
src/aios_bridge/external_brain/context.py
src/aios_bridge/external_brain/budget.py
```

Tests:

```text
tests/aios_bridge/external_brain/test_context_builder.py
tests/aios_bridge/external_brain/test_context_budget.py
```

Small exports from `external_brain/__init__.py` are allowed.

---

# Decision 2 — Token Counting is Injectable and Auditable

M2 MUST NOT add a provider SDK or tokenizer dependency.

Required protocol:

```python
class TokenCounter(Protocol):
    @property
    def counter_id(self) -> str: ...

    @property
    def is_exact(self) -> bool: ...

    def count(self, text: str) -> int: ...
```

Requirements:
1. `count()` is pure and deterministic.
2. Result is a non-negative integer.
3. `counter_id` is stable and recorded in the build result.
4. `is_exact` MUST distinguish provider-exact counting from an estimate.
5. M2 MUST NOT claim approximate counts are exact provider token usage.

## Default M2 counter
Implement one dependency-free conservative estimator suitable for deterministic budgeting, for example:

```text
Utf8ByteConservativeCounter
counter_id = "utf8-byte-conservative-v1"
is_exact = False
count(text) = len(text.encode("utf-8"))
```

This intentionally under-fills context rather than pretending to know MiniMax/Kimi/DeepSeek tokenization. M3 may inject a provider-specific exact/closer counter without changing ContextBuilder.

A deterministic fake counter may be used in tests.

---

# Decision 3 — ContextBudget

Required semantic contract:

```python
@dataclass(frozen=True)
class ContextBudget:
    max_context_tokens: int
    protocol_reserve_tokens: int = 0
```

Rules:
- `max_context_tokens` must be a positive non-bool integer.
- `protocol_reserve_tokens` must be a non-negative non-bool integer.
- `protocol_reserve_tokens < max_context_tokens`.
- available context budget = `max_context_tokens - protocol_reserve_tokens`.
- M2 budgets only the context bundle. Output-token limits remain a separate `ModelRequest.max_output_tokens` concern.

The reserve exists because provider/message framing outside the context bundle may consume tokens in M3.

---

# Decision 4 — Canonical Context Framing

Token counting MUST use one deterministic context-item rendering helper, not raw content in one place and a different representation elsewhere.

Required semantic helper:

```python
def render_context_item(item: ContextItem) -> str:
    ...
```

Canonical V1 framing must include at least:
- kind
- path when present
- exact content

Example conceptual form:

```text
<<<CONTEXT kind=SOURCE path=src/core/retry.py>>>
<exact content>
<<<END_CONTEXT>>>
```

Rules:
- exact content is not normalized or modified;
- line endings/content bytes are treated as supplied;
- framing is deterministic;
- M3 provider adapters SHOULD reuse this helper when serializing selected context so budget accounting and sent context do not drift silently.

---

# Decision 5 — Integrity Verification

Before dedupe/selection, every candidate is integrity-checked.

Rules:
1. Compute SHA-256 over the exact UTF-8 `ContextItem.content`.
2. If `content_sha256` is present, it MUST equal the computed digest (case-insensitive hex comparison is acceptable).
3. A mismatch is a hard failure (`ContextIntegrityError` or equivalent), not a warning.
4. If `content_sha256` is absent, the builder may use the computed digest internally; it MUST NOT mutate the frozen `ContextItem`.

This prevents stale path/hash metadata from corrupting dedupe, caching, or audit records.

---

# Decision 6 — Secret / Sensitive Context Safety Gate

ADR-005 forbids secrets in model context. M2 is the first enforcement layer and MUST fail closed on high-confidence sensitive material.

## Minimum path-based blocklist
Case-insensitive basename/path checks must reject at least:
- `.env`
- `.env.*`
- `*.pem`
- `*.key`
- `id_rsa`
- `id_rsa.*`
- `id_ed25519`
- `id_ed25519.*`
- browser credential stores with exact sensitive basenames such as `Cookies`, `Login Data`, `Web Data`

## Minimum high-confidence content block
Reject private-key material markers such as:
- `-----BEGIN PRIVATE KEY-----`
- `-----BEGIN RSA PRIVATE KEY-----`
- `-----BEGIN OPENSSH PRIVATE KEY-----`

Rules:
- fail closed with `SensitiveContextError` (or equivalent);
- do not redact and continue silently in M2;
- error/audit messages MUST identify kind/path/reason but MUST NOT echo the secret-bearing content;
- do not implement a broad speculative API-key regex in M2; high false-positive secret scanning is explicitly out of scope.

`.env.example` is intentionally treated as sensitive path input for External Brain V1. If sanitized configuration context is needed, the caller should construct a sanitized `ContextItem` instead of sending the file wholesale.

---

# Decision 7 — Exact Dedupe

Dedupe is deterministic and content-aware.

Canonical candidate identity:

```text
(kind, path-or-empty, sha256(exact UTF-8 content))
```

Rules:
- only exact identity duplicates are removed;
- same content under a different semantic kind/path is not automatically collapsed;
- first/selected representative is determined by deterministic ranking, not caller iteration accident;
- duplicates appear in the audit report with reason `DUPLICATE`;
- no fuzzy similarity or embedding dedupe in M2.

---

# Decision 8 — Mandatory Context

A build requires at least one `ContextKind.TASK` candidate after validation/dedupe.

Mandatory kinds in V1:
- `TASK`
- `CONTRACT` (when supplied)

Rules:
1. All mandatory candidates are selected before optional candidates.
2. If mandatory candidates alone exceed available budget, fail with `MandatoryContextBudgetError` (or equivalent).
3. M2 MUST NOT silently truncate mandatory content.
4. M2 MUST NOT silently drop a TASK/CONTRACT to make the budget pass.

This preserves task/contract correctness over token utilization.

---

# Decision 9 — Deterministic Optional Ranking

Optional candidates are ranked with a stable key.

Default V1 kind tie-break precedence:

```text
ERROR        80
DIFF         80
TEST         70
SOURCE       60
ARCHITECTURE 50
```

`TASK` and `CONTRACT` are mandatory and are not governed by optional ranking.

For optional items, rank by:

```text
1. higher ContextItem.priority first
2. higher kind precedence first
3. normalized path lexicographically
4. computed content SHA-256 lexicographically
```

Rules:
- caller input order MUST NOT affect the selected set/result ordering for semantically identical candidate sets;
- ties are resolved deterministically;
- no LLM is used for ranking;
- no embeddings/vector DB in M2.

---

# Decision 10 — Atomic Greedy Budget Selection

M2 uses deterministic atomic selection.

Algorithm:
1. validate safety/integrity;
2. dedupe;
3. select/count mandatory items;
4. sort optional items by locked ranking;
5. for each optional item:
   - if the entire rendered item fits remaining budget -> select;
   - otherwise -> exclude with reason `BUDGET` and continue to later candidates;
6. never exceed available budget.

Rules:
- no silent content truncation/slicing in M2;
- an oversized optional file may be skipped while smaller lower-ranked items can still fit;
- excerpt/symbol-aware slicing is a future enhancement, not M2.

---

# Decision 11 — ContextBuildResult / Auditability

Required semantic result:

```python
@dataclass(frozen=True)
class ContextBuildResult:
    selected: tuple[ContextItem, ...]
    excluded: tuple[ContextExclusion, ...]
    counted_tokens: int
    max_context_tokens: int
    protocol_reserve_tokens: int
    counter_id: str
    token_count_is_exact: bool
    context_fingerprint: str
```

`ContextExclusion` should contain metadata only, for example:

```python
@dataclass(frozen=True)
class ContextExclusion:
    kind: ContextKind
    path: str | None
    content_sha256: str
    counted_tokens: int
    reason: ContextExclusionReason
```

Locked exclusion reasons:
- `DUPLICATE`
- `BUDGET`

Safety/integrity/mandatory-budget failures are hard errors and therefore are not ordinary exclusions.

## Fingerprint
`context_fingerprint` is SHA-256 of a deterministic canonical representation of the final selected bundle and relevant budget/counter metadata.

It MUST:
- be stable for identical inputs/policy;
- change if selected content/order/budget-counter identity changes;
- never include secrets because sensitive candidates fail before result creation.

This fingerprint is intended for future M3 usage ledger/cache correlation.

---

# Decision 12 — Output Ordering

Final `selected` ordering is deterministic:
1. mandatory `TASK` items;
2. mandatory `CONTRACT` items;
3. optional selected items in locked ranking order.

Within mandatory groups, order by:
- higher explicit priority;
- normalized path;
- computed digest.

This means equivalent candidate sets produce byte-for-byte equivalent rendered context order regardless of input list order.

---

# Decision 13 — No Repository Discovery in M2

Explicit non-goals:
- recursive repo scan;
- import graph traversal;
- AST/symbol relevance selection;
- grep/search by LLM;
- embeddings/vector retrieval;
- automatic Git diff collection;
- automatic failing-test collection;
- browser/session/cookie reading.

Future integration may construct candidates from:

```text
TASK declared paths
current git diff
failing tests/errors
explicit relevant source files
architecture/contract artifacts
```

but those collectors remain outside this M2 selector.

---

# M2 Acceptance Criteria

M2 implementation is accepted only when all are true:

1. No semantic regression to M1 contracts or v0.4 Bridge.
2. TokenCounter is injectable and records whether counts are exact.
3. Dependency-free conservative default counter exists; no provider tokenizer SDK is added.
4. ContextBudget validates limits/reserve correctly.
5. Canonical context rendering is deterministic.
6. Supplied SHA-256 mismatch fails closed.
7. High-confidence sensitive paths/private-key material fail closed without echoing content.
8. At least one TASK is required.
9. TASK/CONTRACT are mandatory and cannot be silently dropped/truncated.
10. Mandatory context exceeding budget fails closed.
11. Exact duplicates are removed and audited.
12. Optional selection is deterministic and independent of caller input ordering.
13. Builder never exceeds available context budget according to the injected counter.
14. Oversized optional items are skipped atomically; later smaller candidates may still fit.
15. No content truncation in M2.
16. Result contains selected/excluded metadata, counter identity/exactness, counts, and deterministic fingerprint.
17. No repository crawling/file discovery is introduced.
18. No external model call, HTTP transport, provider adapter, router, fallback, retry, quota registry, or usage ledger is introduced.
19. Existing `bridge.py` and Python Agent `src.providers.LLMProvider` semantics remain untouched.
20. Focused M2 tests and full repository suite pass with zero regression.

---

# Required Test Matrix

Cover at minimum:

### Token counter / budget
1. default counter deterministic for ASCII/Unicode;
2. default counter reports `is_exact=False`;
3. invalid counter output (<0 / bool if relevant) rejected at builder boundary;
4. invalid max budget/reserve rejected;
5. reserve reduces available budget exactly.

### Integrity / safety
6. matching supplied SHA accepted;
7. mismatched supplied SHA rejected;
8. `.env`, `.pem`, `.key`, private-key content rejected;
9. error text does not contain candidate content/secret;
10. normal source/test/task content accepted.

### Dedupe / deterministic selection
11. exact duplicate excluded as `DUPLICATE`;
12. same content with different path/kind remains distinct;
13. shuffled equivalent inputs produce same selected order, exclusions, counts, and fingerprint;
14. explicit priority beats kind tie-break;
15. kind precedence resolves equal-priority optional items.

### Budget behavior
16. missing TASK rejected;
17. mandatory TASK/CONTRACT selected first;
18. mandatory-only overflow fails closed;
19. optional item that fits is selected;
20. oversized optional item excluded as `BUDGET`;
21. smaller later optional item can still be selected after oversized skip;
22. no selected result exceeds available budget;
23. content remains byte/text exact; no truncation.

### Compatibility
24. M1 contract tests remain green;
25. bridge tests remain green;
26. full repository suite remains green.

---

# Forward Path

```text
v0.5-M1  External Brain contracts                 APPROVED
    |
v0.5-M2  ContextBuilder + deterministic budget    <-- this ADR
    |
v0.5-M3  ModelGateway + generic OpenAI-compatible transport + MiniMax POC
    |
v0.5-M3b DeepSeek compatibility proof
    |
v0.6     Kimi + ProviderRegistry
    |
v0.7     rule router + quota awareness + explicit fallback
```

Before TASK-015 is published/executed, TASK-014 approved head must be present on canonical `main` so M2 branches from the locked M1 implementation rather than the pre-M1 baseline.
