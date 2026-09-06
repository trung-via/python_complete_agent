# Post-M4 P4 Live Grounded-QA Provider Certification

Status: **P4.2 CERTIFICATION CANDIDATE — closure is conditional**  
Current stage: **P4.2 credentialed live grounded-QA certification — TASK-143**  
Next stage after both TASK-143 gates PASS: **P5 Human-Facing Product Intelligence Surface**

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

## P4.2 certification boundary

TASK-143 adds one certification-only integration harness. It constructs a minimal,
deterministic Product Source Pack fixture and non-empty canonical catalog entirely
under pytest's temporary directory, using the existing serialization, identity,
approval, canonical-construction, and TASK-120 SQLite registration authorities. It
does not use production data, browser state, Drive, live marketplace acquisition, or
network-fetched evidence.

The harness explicitly constructs `GeminiProvider(model_name="gemini-3.8-flash")`,
so `GEMINI_MODEL_NAME` on the caller machine cannot change the certification subject.
It does not read a credential itself: `GEMINI_API_KEY` enters only through the existing
provider environment boundary. No secret file, dotenv file, key store, or credential
API is consulted.

The harness makes exactly one application call through the existing chain:

`TASK-135 -> TASK-133 -> TASK-132 -> existing GeminiProvider`

The call starts at `answer_persisted_grounded_question(...)`; the harness never invokes
`provider.generate`, TASK-132, or the Google SDK directly. It has no retry, fallback,
reroute, output repair, dynamic model selection, or second request. A successful call
must return an exact TASK-129 `GroundedAnswer` with non-empty canonical context. The
test asserts only existing TASK-129 structure, not model wording, citation choice, or
one particular answer status.

## Evidence hygiene and fail-closed reporting

The live response body, prompt, rendered context, usage metadata, response ID, and
credential are neither printed nor persisted. Normal success evidence is therefore
only pytest's PASS summary.

Failure reporting retains three decision-relevant categories while suppressing raw
provider diagnostics:

- a TASK-132 `GroundedInvocationError` whose causal chain contains the existing
  `AgentException(code="LLM_PROVIDER_ERROR")` is reported only as **Gemini provider
  unavailable**; this covers missing, placeholder, invalid, or unauthorized credentials
  and account, quota, network, service, or selected-model unavailability;
- other `GroundedInvocationError` values remain **grounded invocation or response
  structure invalid**, preserving TASK-132 authority; and
- `GroundedAnswerError` remains **grounded answer structure invalid**, preserving
  TASK-129 authority.

None of these failures is skipped, xfailed, converted to PASS, repaired, or retried.
The test-only categorization creates no production exception taxonomy. Sanitized
canonical failure output contains no raw SDK exception, authorization material,
account/project identifier, request header, or provider payload.

## Conditional P4 closure

P4 is not declared closed by this source change alone. Closure becomes effective only
when canonical TASK-143 Runtime verification and ChatGPT semantic review both PASS on
the same source candidate. At that point P4 is CLOSED and P5 Human-Facing Product
Intelligence Surface becomes CURRENT; TASK-143 itself implements no P5 surface.

This certification establishes only one credentialed structural interoperability
result under the certified conditions. It does not guarantee provider reliability or
an SLA, factual correctness, semantic entailment, completeness, hallucination freedom,
prompt-injection immunity, canonical product truth, conflict reconciliation, ranking,
recommendation, or autonomous approval.
