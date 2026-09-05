# Phase 6 M4 Completion — Persisted Knowledge to Grounded Answer

## Completion condition

Phase 6 M4 is complete only when both of these gates are PASS for the final
TASK-136 candidate:

1. canonical TASK-136 Runtime verification; and
2. semantic review of that Runtime-verified candidate and its immutable
   RESULT/EVIDENCE lineage.

This record does not independently declare M4 complete, predict either verdict,
or manufacture evidence. If either gate is missing, unresolved, or non-PASS,
the completion declaration is not effective. The canonical AIOS RESULT/EVIDENCE
lineage is the sole record of command results and subject identity after
execution.

TASK-136 is documentation and certification only. It adds no Product
Intelligence runtime behavior, source module, public API, test duplicate,
persistence format, retrieval behavior, provider behavior, prompt semantics,
answer semantics, or startup/composition semantics.

## Certified application boundary

The exact M4 vertical slice being certified is:

1. a persisted TASK-120 canonical SQLite catalog;
2. caller-supplied explicit Product Source Pack manifests, strictly typed and
   rehydrated under TASK-125 while the manifest codec remains owned by the
   existing Product Source Pack serialization authority;
3. a caller-supplied natural-language question and injected generic
   `LLMProvider`;
4. TASK-135 persistent composition and input-completeness validation;
5. TASK-121 reconstruction of the canonical variant-profile corpus;
6. TASK-134 deterministic `retrieval_query` planning;
7. TASK-123/TASK-124 canonical retrieval, grounded-context construction,
   packing, citation addressing, and rendering;
8. TASK-133 context-to-answer composition, using TASK-131 deterministic
   provider-neutral prompt packaging and TASK-132 exactly-one generic provider
   invocation plus syntactic response parsing; and
9. TASK-129 construction and structural validation of the resulting
   `GroundedAnswer`.

The certification subject is TASK-135's existing restart-style integration in
`tests/product_intelligence/test_persistent_grounded_qa.py`. It composes a
persisted catalog, explicit source manifests, and a deterministic fake provider
entirely offline. TASK-136 certifies that existing path; it does not add a
parallel implementation or duplicate vertical-slice test.

## Authority map

| Task | Sole or bounded authority preserved by M4 completion |
| --- | --- |
| TASK-120 | SQLite durability and loading of the canonical catalog. |
| TASK-121 | Evidence-preserving registered canonical variant-profile projection. |
| TASK-122 | Deterministic lexical normalization, matching, witnesses, and retrieval ordering. |
| TASK-123 | Canonical retrieval delegation and bounded grounded-context construction. |
| TASK-124 | Grounded-context packing integrity and fail-closed deterministic rendering. |
| TASK-125 | Strict typed V1 Product Source Pack rehydration and the M3 restart/closure boundary; it does not gain M4 runtime authority. |
| TASK-129 | `GroundedAnswer`, `GroundedAnswerStatus`, and final context-bound structural validation. |
| TASK-130 | Repository publication/control-plane support only, with zero Product Intelligence semantic authority. |
| TASK-131 | Deterministic provider-neutral prompt packaging and response-schema framing. |
| TASK-132 | Exactly one generic, tool-free provider invocation and syntactic response parsing. |
| TASK-133 | Context-to-answer composition across TASK-131, TASK-132, and TASK-129. |
| TASK-134 | Deterministic natural-question-to-`retrieval_query` planning. |
| TASK-135 | Persistent grounded-QA startup, manifest-set completeness validation, predecessor ordering, and complete runtime composition. |
| TASK-136 | One-time M4 certification and durable completion documentation only. |

All M2 and M3 authorities remain unchanged. In particular, M2 remains the sole
business scoring, ranking, recommendation, and Human approval authority. M3
retains canonical family/variant identity, catalog, persistence, profile,
lexical-retrieval, grounded-context, packing, and typed source-evidence
rehydration authority. M4 does not create a second authority for any of them.

## Original TASK-129 roadmap closure

TASK-129 deferred six M4 capabilities. Their durable ownership and closure map
is now exact:

| Originally deferred capability | Closing task |
| --- | --- |
| Deterministic prompt packaging | TASK-131 |
| Generic `LLMProvider` invocation | TASK-132 |
| Grounded QA service/composition | TASK-133 |
| Retrieval-query planning | TASK-134 |
| Restart-capable persistent application orchestration | TASK-135 |
| End-to-end vertical-slice certification | TASK-136, effective only after the Runtime and semantic-review gates above both PASS |

Once both TASK-136 gates PASS, this map closes the complete original TASK-129
M4 roadmap; end-to-end vertical-slice certification is no longer an open M4
item. No later task is required to transfer or recreate any authority in this
map.

## Certification limits

The certification is limited to deterministic offline fake-provider protocol
composition. It proves that the bounded application path composes against the
generic `LLMProvider` contract under the certified test conditions. It does not
certify a live provider, provider account, credentials, network availability,
specific model, model quality, or provider-specific behavior.

A structurally valid `GroundedAnswer` is not a guarantee of semantic
entailment, factual correctness, completeness, hallucination freedom,
prompt-injection immunity, canonical product truth, conflict reconciliation,
or recommendation/approval authority.

## Runtime-owned phase-transition verification

Runtime must execute the following gates on the final TASK-136 documentation
candidate and retain their immutable results in canonical AIOS RESULT/EVIDENCE
lineage:

1. Focused existing vertical-slice regression:

   `$env:PYTHONPATH = ".;src"; python -m pytest tests/product_intelligence/test_persistent_grounded_qa.py -q; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }`

2. Complete Product Intelligence subsystem suite, exactly once on the final
   candidate as the one-time M4 phase-transition health gate:

   `$env:PYTHONPATH = ".;src"; python -m pytest tests/product_intelligence -q; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }`

3. Documentation-delta and whitespace integrity, including confirmation that
   the committed TASK-136 execution delta contains only
   `docs/PHASE_6_M4_COMPLETION.md`,
   `docs/PHASE_6_M4_GROUNDED_ANSWER.md`, and
   `docs/PHASE_6_M4_PERSISTENT_GROUNDED_QA.md`:

   `git diff --check; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }`

The complete subsystem run is a one-time M4 transition gate. It does not impose
a new full-suite rule on future narrow FIX or REPAIR work. This document records
the required commands only; it intentionally records no prospective RUN ID,
RESULT ID, evidence ID, source-candidate SHA, test count, or command outcome.
Semantic review must inspect the actual Runtime artifacts.

## Post-M4 deferred work

The following are separate future capabilities, not unfinished M4 blockers:

- live-provider certification, network access, and credentials;
- automatic manifest, filesystem, or Drive discovery;
- HTTP, API, or CLI presentation and background serving;
- caches and registries;
- semantic/vector retrieval;
- product-truth reconciliation and preferred/latest/majority selection;
- semantic-entailment and factual-truth guarantees;
- autonomous recommendation or approval;
- identity evolution; and
- migrations.

TASK-136 grants none of these capabilities and names no future semantic owner.
The next Product Intelligence boundary is intentionally undecided until a fresh
post-M4 Brain audit establishes one owner and a new roadmap. This record does
not invent a Phase 6 M5 or any other post-M4 architecture.
