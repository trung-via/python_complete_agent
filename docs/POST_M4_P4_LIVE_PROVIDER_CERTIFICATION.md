# Post-M4 P4 Live Grounded-QA Provider Certification

Status: **P4 IN PROGRESS**  
Current stage: **P4.1 production-provider foundation — TASK-142**  
Next stage: **P4.2 separate credentialed live grounded-QA certification**

## P4.1 boundary

TASK-142 establishes only the production transport foundation for the repository's
existing `GeminiProvider`. It replaces the legacy Gemini SDK with the pinned
`google-genai==2.22.0` client, fixes `gemini-3.8-flash` as this adapter's default,
and proves the generic message, manual-function-declaration, and response mappings
offline.

`LLMProvider`, `LLMResponse`, and `ProviderToolCall` remain the sole generic provider
transport contract. `GeminiProvider` remains the single concrete default Gemini
adapter used by `AgentController`. P4.1 adds no second protocol, grounded-only
provider, model registry, router, retry, fallback, or provider-selection policy.
The adapter transports provider text and manual function calls only. It does not
execute tools or interpret Product Intelligence response meaning.

P4.1 does not certify a provider account, credential, quota, network path, selected
model availability, live response quality, or a live `GroundedAnswer`. Its tests use
an isolated offline Google transport.

## Preserved M4 authority chain

TASK-142 changes none of the following authorities:

1. TASK-120 loads the canonical SQLite catalog.
2. TASK-125 rehydrates caller-supplied persisted Product Source Pack evidence, and
   `SourceObservationIdentity` supplies the exact source-identity projection.
3. TASK-121 builds canonical variant profiles.
4. TASK-134 plans the `retrieval_query`.
5. TASK-123 performs canonical retrieval and builds the grounded context.
6. TASK-131 owns grounded prompt and response-schema framing.
7. TASK-132 owns exactly one generic, tool-free provider invocation and syntactic
   parsing of the provider response.
8. TASK-129 remains the sole `GroundedAnswer` structural-validation authority.
9. TASK-133 composes prompt, provider invocation, and validated answer from an exact
   context.
10. TASK-135 owns only persistent startup and the predecessor call order.

TASK-142 supplies the provider-specific transport beneath TASK-132. It does not parse
the TASK-131 JSON contract, construct an answer, validate citations, infer status or
limitations, reconcile product truth, or modify the TASK-129/131/132/133/134/135
semantics.

## Failure-boundary distinction

Provider availability and grounded structural validation are separate failure
classes:

- missing or placeholder credentials fail locally as `LLM_PROVIDER_ERROR` before a
  Google client request;
- provider account, authentication, quota, network, service, or model-availability
  failures arise at the Google transport boundary and are preserved under
  `LLM_PROVIDER_ERROR` with their cause;
- malformed provider JSON or a response that violates TASK-132's exact syntactic
  payload contract is a `GroundedInvocationError` owned by TASK-132;
- context-local citation, leaf-minimum, answer-text, limitation-bound, and final
  grounded-answer structural failures remain TASK-129 `GroundedAnswerError`
  authority.

A successful provider request proves availability only. It does not by itself prove
grounded structural validity, factual correctness, product truth, or end-to-end live
certification. Conversely, a provider availability failure supplies no conclusion
about the offline-grounded structural validators.

## P4.2 next stage

P4 remains IN PROGRESS. P4.2 must separately prove one credentialed live call through
the existing application chain:

`TASK-135 -> TASK-133 -> TASK-132 -> existing GeminiProvider`

That certification must use the existing TASK-142 adapter and must separately report
provider availability and the downstream grounded structural result. Credentials and
account identifiers must not enter repository artifacts, logs, fixtures, or evidence.
P4.2 is not authority to add retries, fallback, provider rerouting, dynamic model
selection, provider-managed tool execution, or a new Product Intelligence parser.
Any such policy would require a separate explicit task.
