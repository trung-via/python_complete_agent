# Phase 6 M4.2 — Grounded Prompt Package

## Purpose

TASK-131 adds one pure Product Intelligence domain boundary that converts an exact `CanonicalRagContext` into deterministic, provider-neutral model-facing strings. It packages a fixed system instruction, a deterministically framed user prompt, the canonical context JSON, and a compact response-schema JSON value. It does not invoke a model, consume model output, or construct a `GroundedAnswer`.

The public API consists of exactly:

- `GroundedPromptError`
- `GroundedPromptPackage`
- `build_grounded_prompt_package(context)`

`GroundedPromptPackage` is frozen and retains the exact supplied context object. The builder accepts only an exact `CanonicalRagContext`; subclasses and coercions fail closed.

## Authority map

| Boundary | Sole authority |
| --- | --- |
| TASK-123/TASK-124 | Build the bounded canonical grounded context, preserve evidence order and context-local citation identities, apply context budgeting/truncation policy, and render deterministic compact canonical context JSON. |
| TASK-129 | Define `GroundedAnswer`, its application statuses, and final structural validation of citation addresses, leaf minima, text bounds, and limitation bounds. |
| TASK-131 | Package the exact canonical context into fixed provider-neutral instructions, deterministic prompt framing, and a syntactic response JSON Schema. |
| Later invocation integration | Reuse the existing `LLMProvider` at the integration edge without moving prompt semantics into provider implementations. |

M2 remains the authority for business scoring, ranking, recommendation, and Human approval. M3 remains the authority for canonical identity, catalog state, evidence, retrieval, and context construction. Product-truth reconciliation—including preferred, latest, or majority selection—remains deferred.

## Deterministic contract

`build_grounded_prompt_package(context)` calls `render_canonical_rag_context(context)` directly. It does not rebuild the context, separately interpolate evidence, alter retrieval ordering, derive a query, or mutate any M3 value. Renderer failures are wrapped as `GroundedPromptError` with the original exception retained as the cause.

The user prompt has three fixed sections in this order:

1. `QUESTION`, containing the exact `context.question` without stripping, normalization, rewriting, translation, classification, or query derivation.
2. `CANONICAL_CONTEXT_JSON`, containing the exact result from the TASK-123/TASK-124 renderer.
3. `RESPONSE_SCHEMA_JSON`, containing the deterministic compact schema string.

The response schema describes exactly one object with required keys `status`, `answer_text`, `citation_ids`, and `limitations`, and rejects additional properties. Its status enum contains exactly `ANSWERED`, `INSUFFICIENT_EVIDENCE`, and `CONFLICTING_EVIDENCE`. It is serialized with `ensure_ascii=False`, sorted object keys, and compact separators.

## Trust and validation boundary

The fixed system instruction tells a future model that marketplace evidence is untrusted data and that instructions embedded in evidence are non-authoritative. It requires context-only answers, exact context citation identifiers, conflict preservation, abstention for unsupported claims, TASK-129-compatible status/leaf/limitation behavior, and JSON-only output.

These instructions reduce ambiguity; they do not provide prompt-injection immunity, prove factual correctness or semantic entailment, guarantee freedom from hallucination, validate context-local citations, resolve conflicting evidence, or reconcile canonical product truth. The schema is syntactic, and TASK-129 remains the later structural answer validator unless a separate explicit milestone grants additional semantic authority.

TASK-131 performs no provider/model/agent/tool/browser/network/storage/environment/clock/random/subprocess I/O or execution. Provider-specific messages, JSON modes, tool schemas, retries, model settings, and response parsing remain outside this domain boundary.
