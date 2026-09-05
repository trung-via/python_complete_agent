# Phase 6 M4.4 — Grounded QA Application Composition

## Purpose and public API

TASK-133 adds the single application entry point `async answer_grounded_context(context, provider) -> GroundedAnswer`. It begins with an already-constructed, exact `CanonicalRagContext` and returns the `GroundedAnswer` produced by the existing TASK-129 constructor.

TASK-133 is composition authority only. It introduces no service or result wrapper, error or status type, policy, configuration, persistence, cache, retrieval behavior, prompt semantics, provider behavior, parsing behavior, or answer validation.

## Authority boundaries

| Authority | Ownership |
| --- | --- |
| TASK-123 / TASK-124 | Construct and render `CanonicalRagContext`, including retrieval delegation, evidence order, citation addressing, byte budgets, and truncation. |
| TASK-129 | Define `GroundedAnswer` and `GroundedAnswerStatus`; perform final structural validation through `create_grounded_answer`, including citation resolution, leaf minima, text bounds, and limitation bounds. |
| TASK-131 | Build the deterministic provider-neutral `GroundedPromptPackage` and own all prompt and response-schema semantics. |
| TASK-132 | Map the package to the generic provider boundary, perform the single tool-free provider call, reject tool calls, and parse syntactically valid output into `GroundedModelPayload`. |
| TASK-133 | Call those three predecessor entry points once each, in canonical order, and return the validated TASK-129 answer. |

M2 remains the authority for scoring, ranking, recommendation, and Human approval. M3 remains the authority for canonical product entities, catalogs, profiles, and retrieval.

## Canonical composition

The service performs exactly this sequence:

1. `build_grounded_prompt_package(context)` with the exact caller context.
2. `await invoke_grounded_model(package, provider)` with the exact returned package and injected provider.
3. `create_grounded_answer(context, status=payload.status, answer_text=payload.answer_text, citation_ids=payload.citation_ids, limitations=payload.limitations)` with the original context and exact payload fields.
4. Return that exact `GroundedAnswer`.

No context or payload value is copied, normalized, stripped, sorted, deduplicated, truncated, repaired, or reclassified. In particular, the final constructor receives the original caller context rather than treating `package.context` as a new source of authority.

Predecessor exceptions and `asyncio` cancellation propagate unchanged. Failure short-circuits later stages. TASK-133 has no retry, fallback, reroute, repair, timeout, second provider call, direct message construction, tool path, or direct provider invocation.

A payload may satisfy TASK-132 syntax rules yet violate TASK-129 structural grounding. TASK-133 passes it unchanged to `create_grounded_answer`, where it fails under the existing `GroundedAnswerError`; the service does not convert that failure into an answer.

## Deferred and non-authoritative behavior

The caller must supply an already-built `CanonicalRagContext`. Question-to-retrieval-query planning and persisted-knowledge application startup remain later milestones. TASK-133 performs no retrieval, context construction, prompt reconstruction, JSON parsing, provider-specific behavior, storage, or product-truth reconciliation.

A structurally valid `GroundedAnswer` is an application answer, not canonical product truth and not an M2 recommendation or approval decision. TASK-133 does not establish semantic entailment, factual correctness, hallucination freedom, conflict resolution, prompt-injection immunity, completeness, or product-truth reconciliation.

Focused tests use deterministic fakes and monkeypatching only. They require no live provider, network, credentials, persisted catalog, or external service.
