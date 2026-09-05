# Phase 6 M4.3 — Grounded Model Invocation Adapter

## 1. Purpose & Scope

TASK-132 establishes the model invocation and syntactic response parsing boundary for Phase 6 M4 Grounded Product Intelligence. It introduces a single bounded integration adapter connecting an exact `GroundedPromptPackage` (from TASK-131) to the generic `LLMProvider` interface (from `src/providers/base.py`).

The adapter performs exactly one tool-free provider call and validates the returned model output against the syntactic response schema into an immutable `GroundedModelPayload`. It operates strictly as a transport and syntax boundary: it does not use `AgentLoop`, does not retry or reroute, does not execute tools, and does not validate contextual citations or construct a `GroundedAnswer`.

The public API consists of exactly:
- `GroundedInvocationError`
- `GroundedModelPayload`
- `async invoke_grounded_model(package, provider)`

---

## 2. Authority Map

| Subsystem / Task | Sole Authority | Boundary & Exclusions |
| --- | --- | --- |
| **TASK-123 / TASK-124** | Bounded canonical grounded context construction and deterministic JSON rendering (`CanonicalRagContext`, `render_canonical_rag_context`). | Preserves evidence order, applies budgeting/truncation, and defines context-local citation addresses. |
| **TASK-129** | Final structural answer validation and immutable domain value (`GroundedAnswer`, `GroundedAnswerStatus`, `create_grounded_answer`). | Validates context-local citation resolution, leaf-citation minima, text length/non-blank bounds, and limitation bounds against an exact context. |
| **TASK-131** | Provider-neutral prompt packaging (`GroundedPromptPackage`, `build_grounded_prompt_package`). | Defines fixed system instructions, prompt framing, and compact response JSON Schema. |
| **TASK-132 (This Task)** | One-shot generic model transport and syntactic response parsing (`invoke_grounded_model`, `GroundedModelPayload`). | Translates package to two messages, calls `provider.generate` once with `tools=[]`, and parses response JSON into syntax-validated payload. Does not construct `GroundedAnswer`. |
| **Later Application Service** | End-to-end composition and workflow orchestration. | The only boundary authorized to pass `GroundedModelPayload` fields to `create_grounded_answer` alongside the original `CanonicalRagContext`. |

M2 remains the sole authority for product candidate scoring, ranking, and human approval. M3 remains the sole authority for entity resolution, canonical catalog state, variant profiles, and retrieval. Product-truth reconciliation (including preferred, latest, or majority evidence selection) remains deferred.

---

## 3. Invocation Contract

The invocation entry point is `async invoke_grounded_model(package, provider)`:

1. **Exact Package Verification**:
   - `package` must be an exact instance of `GroundedPromptPackage`. Subclasses and coercions fail closed with `GroundedInvocationError`.
2. **Provider Contract**:
   - `provider` is consumed exclusively via its existing `generate(messages, tools)` protocol method. No provider-specific protocols, wrappers, SDKs, or concrete class dependencies are introduced.
3. **Deterministic Message Mapping**:
   - Constructs exactly two `LLMMessage` objects in this exact order:
     1. `MessageRole.SYSTEM` with content equal to `package.system_instruction`.
     2. `MessageRole.USER` with content equal to `package.user_prompt`.
   - No assistant, tool, hidden instruction, metadata policy, rewritten question, provider-specific wrapper, or evidence interpolation is added.
4. **Single Tool-Free Invocation**:
   - Invokes `await provider.generate(messages, [])` exactly once with an empty tools list.
   - Zero routing through `AgentLoop` or `AgentController`.
   - No retries, fallbacks, rerouting, repair loops, token budgeting, continuation, or second calls.
   - Provider exceptions fail closed as `GroundedInvocationError` preserving the original exception via causal chaining (`raise ... from exc`).
   - `asyncio.CancelledError` is not caught or converted into retry behavior and propagates immediately.
5. **Tool Call Rejection**:
   - Any returned tool call in `response.tool_calls` causes immediate fail-closed rejection as `GroundedInvocationError`, even if content is otherwise valid. Tool execution is forbidden.
6. **Content Requirement**:
   - Missing, null, or non-string `response.content` fails closed as `GroundedInvocationError`.

---

## 4. Response Parsing & Syntactic Boundary

Parsing accepts only valid JSON matching the TASK-131 response schema:

1. **Single JSON Object Root**:
   - The content must parse as exactly one JSON object. Trailing data, multiple objects, primitives, arrays, or malformed JSON fail closed.
   - Duplicate JSON object keys fail closed.
2. **Exact Key Set**:
   - The root object must contain exactly four keys: `status`, `answer_text`, `citation_ids`, and `limitations`.
   - Missing keys or extra keys fail closed.
3. **Exact Syntactic Types**:
   - `status`: must be a string matching one of `GroundedAnswerStatus` enum values (`ANSWERED`, `INSUFFICIENT_EVIDENCE`, `CONFLICTING_EVIDENCE`). Unknown statuses fail closed.
   - `answer_text`: must be a string.
   - `citation_ids`: must be a JSON array of strings.
   - `limitations`: must be a JSON array of strings.
4. **Order and Value Preservation**:
   - Decoded strings are preserved byte-for-byte without stripping, normalization, deduplication, sorting, rewriting, or truncation.
   - `citation_ids` and `limitations` arrays are converted to immutable tuples preserving model-emitted order.
   - Status is mapped to the existing `GroundedAnswerStatus` enum.
5. **Strict Separation from TASK-129 Validation**:
   - TASK-132 syntax validation deliberately stops at the schema boundary.
   - Blank or oversized answer text, duplicate or non-resolving citations, hit-header citations alone under `ANSWERED`, empty limitations under non-answer statuses, or excessive limitation counts do **not** fail in TASK-132.
   - Such semantic and context-bound invariants are solely enforced downstream by TASK-129's `create_grounded_answer`.

---

## 5. Trust, Safety & Non-Entailment Boundary

- **Untrusted Model Output**:
  - `GroundedModelPayload` is unvalidated transport data from an untrusted model. It must never be treated as verified product knowledge or canonical product truth.
- **No Prompt Injection Immunity**:
  - TASK-132 provides no prompt-injection immunity. Instructions embedded in marketplace evidence remain untrusted.
- **No Semantic Entailment**:
  - Passing syntactic validation does **not** prove that `answer_text` is supported by cited evidence, factually accurate, free of hallucinations, or semantically entailed.
- **No Product-Truth Reconciliation**:
  - Model outputs cannot resolve conflicting marketplace observations or declare canonical values.
- **No GroundedAnswer Construction**:
  - TASK-132 does not instantiate `GroundedAnswer` and does not import or call `create_grounded_answer`.
