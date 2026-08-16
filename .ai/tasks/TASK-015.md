# TASK-015 — AIOS Bridge v0.5-M2 Deterministic ContextBuilder + Token Budget

## Objective
Implement **v0.5-M2 Deterministic ContextBuilder + Token Budget** exactly as locked in:

`.ai/decisions/ADR-006-AIOS-BRIDGE-V0.5-M2-CONTEXT-BUDGET-CONTRACT-LOCK.md`

Canonical baseline when authored:
- `main`: `34b331c75d0577e403bb80b2ba0fe9818183b4f9`
- TASK-014 / External Brain M1 contracts are already present on `main`
- ADR-005: LOCKED
- ADR-006: LOCKED

M2 creates a deterministic, auditable selector that receives **explicit candidate `ContextItem`s** and returns a bounded context bundle. It MUST reduce model input without changing M1 contracts and without adding repository discovery or model execution.

```text
Antigravity / Bridge
      |
      | explicit bounded ContextItem candidates
      v
Context Safety + Integrity
      |
      v
Exact Dedupe
      |
      v
Mandatory Context
      |
      v
Deterministic Optional Ranking
      |
      v
Token Budget
      |
      v
ContextBuildResult
      |
      v
future M3 ModelGateway
```

## Core Invariants

1. **ContextBuilder selects from supplied candidates only.**
   It MUST NOT recursively crawl the repository, home directory, browser profile, Git tree, or arbitrary filesystem.

2. **No LLM/embedding/vector ranking.**
   M2 ranking is deterministic code only and therefore has zero model-token routing cost.

3. **M1 contracts stay backward compatible.**
   Do not weaken/redesign `ContextItem`, `ModelRequest`, `ModelResponse`, `ProviderAdapter`, `ModelTransport`, or output validation.

4. **TASK / CONTRACT correctness outranks utilization.**
   Mandatory context is never silently dropped or truncated just to fit budget.

5. **No live model/API/network call in M2.**

6. **No content truncation/slicing in M2.**
   Optional items are selected atomically or skipped atomically.

---

# M2.1 — TokenCounter Protocol

Add a provider-independent protocol, preferably in:

`src/aios_bridge/external_brain/budget.py`

Required semantic shape:

```python
class TokenCounter(Protocol):
    @property
    def counter_id(self) -> str: ...

    @property
    def is_exact(self) -> bool: ...

    def count(self, text: str) -> int: ...
```

Requirements:
- pure/deterministic;
- `count()` returns non-negative non-bool integer;
- stable non-empty `counter_id`;
- `is_exact` explicitly distinguishes exact provider count from estimation;
- no provider SDK/tokenizer dependency in M2.

Implement dependency-free default:

```text
Utf8ByteConservativeCounter
counter_id = "utf8-byte-conservative-v1"
is_exact = False
count(text) = len(text.encode("utf-8"))
```

Do NOT label this as provider token usage. It is a conservative deterministic budgeting unit.

---

# M2.2 — ContextBudget

Implement immutable contract equivalent to:

```python
@dataclass(frozen=True)
class ContextBudget:
    max_context_tokens: int
    protocol_reserve_tokens: int = 0
```

Validation:
- `max_context_tokens` > 0 and bool rejected;
- `protocol_reserve_tokens` >= 0 and bool rejected;
- `protocol_reserve_tokens < max_context_tokens`;
- expose deterministic available budget:

```text
available_context_tokens = max_context_tokens - protocol_reserve_tokens
```

M2 budgets only context. Do not merge output-token budgeting into this object.

---

# M2.3 — Canonical Context Rendering

Add one canonical helper:

```python
def render_context_item(item: ContextItem) -> str:
    ...
```

Canonical V1 framing must deterministically include:
- `kind`;
- `path` when present;
- exact unmodified `content`.

Conceptual format:

```text
<<<CONTEXT kind=SOURCE path=src/core/retry.py>>>
<exact content>
<<<END_CONTEXT>>>
```

Requirements:
- do not normalize/trim/modify source content;
- preserve supplied content and line endings;
- deterministic framing;
- token counting MUST count this rendered representation, not raw content alone;
- future M3 provider serialization can reuse this helper to avoid count/send drift.

---

# M2.4 — Errors / Failure Taxonomy

Add a small context-specific error taxonomy, preferably extending the existing External Brain base error where sensible.

Required semantic concepts:
- `ContextBuildError`
- `ContextIntegrityError`
- `SensitiveContextError`
- `MissingMandatoryContextError`
- `MandatoryContextBudgetError`
- invalid token-counter result error may use contract/build error rather than adding a large hierarchy

Keep exceptions small and focused.

Error messages involving sensitive context MUST NOT echo the candidate content.

---

# M2.5 — Integrity Verification

Before dedupe/ranking/budget selection, compute SHA-256 over exact UTF-8 `ContextItem.content`.

Rules:
- if `content_sha256` exists, compare to computed digest;
- hex comparison may be case-insensitive;
- mismatch -> hard `ContextIntegrityError`;
- absence of hash is allowed; use computed digest internally without mutating the frozen `ContextItem`;
- integrity failure occurs before a normal `ContextBuildResult` is produced.

---

# M2.6 — Sensitive Context Safety Gate

M2 is the first enforcement layer for ADR-005's rule that secrets do not enter External Brain context.

## Minimum path-based rejection
Case-insensitive path/basename handling MUST reject at least:
- `.env`
- `.env.*`
- `*.pem`
- `*.key`
- `id_rsa`
- `id_rsa.*`
- `id_ed25519`
- `id_ed25519.*`
- exact sensitive browser-store basenames: `Cookies`, `Login Data`, `Web Data`

`.env.example` is intentionally rejected in V1.

## Minimum content-based rejection
Reject candidates containing private-key markers including:
- `-----BEGIN PRIVATE KEY-----`
- `-----BEGIN RSA PRIVATE KEY-----`
- `-----BEGIN OPENSSH PRIVATE KEY-----`

Rules:
- hard fail with `SensitiveContextError`;
- error may identify `kind`, `path`, and reason only;
- MUST NOT echo secret-bearing content;
- do not add broad speculative API-key regex scanning in M2;
- do not redact-and-continue silently.

---

# M2.7 — Exact Dedupe

Canonical exact identity:

```text
(kind, path-or-empty, sha256(exact UTF-8 content))
```

Rules:
- only exact identity duplicates are collapsed;
- same bytes at different path or semantic `kind` are NOT automatically duplicates;
- deterministic representative selection, not caller-order accident;
- duplicate candidates appear in audit result with reason `DUPLICATE`;
- no fuzzy/semantic/embedding dedupe.

---

# M2.8 — Mandatory Context

V1 mandatory rules:
- at least one `ContextKind.TASK` candidate MUST remain after validation/dedupe;
- all TASK items are mandatory;
- CONTRACT items, when supplied, are mandatory.

Selection order:
1. TASK
2. CONTRACT
3. optional ranked candidates

Within TASK and CONTRACT groups, stable order:
1. higher explicit `priority` first;
2. normalized path lexicographically;
3. computed content digest lexicographically.

If mandatory rendered context exceeds available budget:
- raise `MandatoryContextBudgetError`;
- do not truncate;
- do not drop any mandatory candidate.

If no TASK remains:
- raise `MissingMandatoryContextError`.

---

# M2.9 — Deterministic Optional Ranking

Locked V1 kind precedence:

```text
ERROR        80
DIFF         80
TEST         70
SOURCE       60
ARCHITECTURE 50
```

Optional ranking key:
1. higher `ContextItem.priority` first;
2. higher kind precedence first;
3. normalized path lexicographically;
4. computed SHA-256 lexicographically.

Requirements:
- caller input order MUST NOT change selected set/output ordering for semantically identical candidate sets;
- ties deterministic;
- no LLM/embedding/vector database.

---

# M2.10 — Atomic Greedy Budget Selection

Locked algorithm:

```text
validate safety/integrity
    -> dedupe
    -> mandatory selection/count
    -> sort optional candidates
    -> iterate optional candidates
         if entire rendered item fits:
             select
         else:
             exclude reason=BUDGET
             continue
```

Requirements:
- count `render_context_item(item)`;
- never exceed `ContextBudget.available_context_tokens` according to injected counter;
- oversized optional item is skipped atomically;
- builder continues to later lower-ranked items which may fit;
- never truncate/slice optional content.

---

# M2.11 — Audit Contracts

Implement immutable audit contracts equivalent to:

```python
class ContextExclusionReason(str, Enum):
    DUPLICATE = "DUPLICATE"
    BUDGET = "BUDGET"

@dataclass(frozen=True)
class ContextExclusion:
    kind: ContextKind
    path: str | None
    content_sha256: str
    counted_tokens: int
    reason: ContextExclusionReason

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

Validation/semantics:
- result/exclusions immutable;
- token counts non-negative non-bool integers;
- no content copied into `ContextExclusion`;
- selected items remain original `ContextItem` values (no hidden truncation);
- excluded duplicate/budget metadata uses computed digest and canonical rendered token count.

---

# M2.12 — Context Fingerprint

`context_fingerprint` MUST be SHA-256 of a deterministic canonical representation of:
- final selected bundle/order/content identity;
- relevant context budget values;
- token counter identity/exactness.

Requirements:
- stable for equivalent candidates/policy regardless of caller input ordering;
- changes when selected content/order changes;
- changes when relevant budget/counter identity changes;
- no sensitive content can reach result generation because safety gate runs first;
- use standard SHA-256 hex string.

Do not use Python's process-randomized `hash()`.

---

# M2.13 — ContextBuilder API

Implement a compact deterministic builder, preferably in:

`src/aios_bridge/external_brain/context.py`

Suggested semantic shape:

```python
class ContextBuilder:
    def __init__(self, token_counter: TokenCounter | None = None): ...

    def build(
        self,
        candidates: Sequence[ContextItem],
        budget: ContextBudget,
    ) -> ContextBuildResult:
        ...
```

Requirements:
- pure with respect to repository/workspace state;
- no filesystem/network/Git/browser/model side effects;
- does not mutate caller sequence or `ContextItem`s;
- default counter = `Utf8ByteConservativeCounter`;
- deterministic for equivalent candidate sets.

---

# Required Tests

Add focused tests under:

```text
tests/aios_bridge/external_brain/test_context_builder.py
tests/aios_bridge/external_brain/test_context_budget.py
```

Cover at minimum:

1. default counter ID is exactly `utf8-byte-conservative-v1`;
2. default counter `is_exact is False`;
3. UTF-8 byte count deterministic for ASCII and multibyte Unicode;
4. counter returning negative/non-int/bool is rejected by builder boundary;
5. ContextBudget validates positive max;
6. ContextBudget rejects bool max/reserve;
7. reserve must be less than max;
8. available budget is correct;
9. canonical rendering includes kind/path/content and preserves exact content;
10. supplied correct SHA-256 accepted;
11. hash mismatch hard-fails;
12. `.env` rejected without echoing its content;
13. `.env.example` rejected;
14. `.pem` / `.key` rejected;
15. SSH private key paths rejected;
16. `Cookies`, `Login Data`, `Web Data` path basenames rejected;
17. private-key marker in otherwise ordinary path rejected;
18. secret error text does not contain secret-bearing content;
19. at least one TASK required;
20. CONTRACT is mandatory when supplied;
21. mandatory context that exceeds budget hard-fails;
22. mandatory content is never truncated/dropped;
23. exact duplicate collapses and creates `DUPLICATE` audit exclusion;
24. same content at different path does not dedupe;
25. same content/path under different kind does not dedupe;
26. input candidate permutation yields identical selected order/fingerprint;
27. explicit priority outranks kind precedence for optional candidates;
28. kind precedence resolves equal priority;
29. path resolves equal priority/kind;
30. digest resolves final tie deterministically;
31. optional item fitting budget is selected;
32. oversized optional item receives `BUDGET` exclusion;
33. oversized higher-ranked optional item does not prevent later smaller item fitting;
34. builder never exceeds available budget;
35. no partial/truncated item appears in selected output;
36. selected order = TASK -> CONTRACT -> optional ranking;
37. excluded audit has no content field;
38. fingerprint stable for same semantic input;
39. fingerprint changes when selected content changes;
40. fingerprint changes when counter ID or relevant budget policy changes;
41. custom exact fake counter records `token_count_is_exact=True`;
42. default result records `token_count_is_exact=False`;
43. ContextBuilder does not read files/repository implicitly (test through API shape / monkeypatch if useful, but do not make brittle implementation-internals assertions);
44. M1 External Brain tests remain green;
45. existing bridge tests remain green;
46. full repository suite remains green.

Add more focused tests if necessary, but avoid unnecessary framework/abstraction growth.

---

# Files Expected to Change

Preferred implementation scope:

```text
src/aios_bridge/external_brain/context.py
src/aios_bridge/external_brain/budget.py
src/aios_bridge/external_brain/errors.py          # small additive error types only
src/aios_bridge/external_brain/__init__.py        # exports only

tests/aios_bridge/external_brain/test_context_builder.py
tests/aios_bridge/external_brain/test_context_budget.py
.ai/results/RESULT-015.md
```

Small test-only helpers are acceptable.

---

# Protected From Semantic Change

TASK-015 MUST NOT semantically modify:
- `bridge.py` v0.4 handoff/sync/authorization/publish/branch behavior;
- `src/providers/base.py` / `GeminiProvider` runtime abstraction;
- M1 `ModelRequest` / `ModelResponse` / `ProviderAdapter` / `ModelTransport` semantics;
- AgentLoop/retry/checkpoint/idempotency;
- browser execution stack;
- Product Source Pack.

Any unavoidable M1 change must be additive/backward-compatible and explicitly justified in RESULT-015; otherwise stop rather than redesign M1.

---

# Explicit Non-Goals

TASK-015 MUST NOT implement:
- recursive repo/file discovery;
- import graph/AST/symbol retrieval;
- automatic Git diff collection;
- automatic failing-test/error collection;
- embeddings/vector retrieval;
- LLM-based relevance/ranking;
- MiniMax/Kimi/DeepSeek provider calls;
- provider SDK tokenizer;
- ModelGateway;
- HTTP transport implementation;
- ProviderRegistry;
- model router;
- fallback/retry/quota policy;
- usage ledger;
- MCP server;
- external filesystem/shell/browser/Git execution authority;
- model patch application;
- auto commit/push/merge;
- context truncation/excerpt generation.

---

# Acceptance Criteria

TASK-015 is ready for review only when all are true:

1. `ContextBuilder` accepts explicit candidate `ContextItem`s and does not discover files itself.
2. injectable `TokenCounter` exists with stable identity/exactness metadata.
3. dependency-free conservative default counter exists and does not pretend to be exact provider usage.
4. `ContextBudget` validates max/reserve and exposes available budget.
5. canonical rendering is deterministic and used for counting.
6. integrity SHA mismatch fails closed.
7. high-confidence sensitive paths/private-key content fail closed without secret echo.
8. at least one TASK is required.
9. TASK/CONTRACT mandatory context cannot be dropped or truncated.
10. mandatory overflow fails closed.
11. exact duplicates are deterministically removed and audited.
12. optional ordering exactly follows ADR-006 priority/kind/path/digest ranking.
13. equivalent input permutations produce equivalent selected order/result fingerprint.
14. atomic greedy selector never exceeds available budget.
15. oversized optional candidate is skipped; later smaller candidate may still fit.
16. no content truncation/slicing occurs.
17. `ContextBuildResult` contains selected/excluded audit metadata, budget, counter identity/exactness, token count, and SHA-256 fingerprint.
18. no repository crawl, external model/API/network call, router, fallback, or Gateway is introduced.
19. no semantic regression to M1 or v0.4 Bridge.
20. focused M2 tests pass.
21. all M1 External Brain tests pass.
22. existing bridge tests pass.
23. full repository suite passes with zero regressions.
24. RESULT-015 explicitly reports changed files, focused/full test counts, counter semantics, and confirms no external-model request or implicit repository scan occurred.

---

# Review Focus

Reviewer should pay special attention to:
- accidental repository/filesystem crawling;
- token estimate being mislabeled as exact;
- counting raw content instead of canonical rendered context;
- caller-order dependence;
- unstable Python `hash()` / set ordering;
- secrets appearing in exceptions/audit records;
- `.env.example` slipping through path checks;
- SHA metadata not actually being verified;
- mandatory TASK/CONTRACT silently dropped/truncated;
- oversized optional item terminating selection instead of allowing later smaller item;
- mutable collections inside frozen result/audit contracts;
- content copied into exclusions/logs;
- provider-specific logic leaking into M2;
- changes to M1 contracts or `bridge.py`.

---

## Human Gate

Do not execute automatically.

After Bridge sync detects TASK-015, execution requires explicit approval:

`/aios-worker RUN TASK-015`
