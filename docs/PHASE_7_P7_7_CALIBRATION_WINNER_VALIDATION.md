# P7.7 Calibration & Winner Validation

Status: TASK-225 revision 1, publication-gated DONE. This source becomes effective only when canonical Runtime verification and independent semantic review pass and the safe Publisher publishes the exact reviewed TASK-225 source candidate.

Authority identifier: `COMMERCE_OPPORTUNITY_INTELLIGENCE_P7_7`

Canonical owner: `src/commerce_opportunity_intelligence/calibration_and_winner_validation.py`

## Purpose and composition

P7.7 supplies one bounded immutable post-test interpretation value, `WinnerValidationAssessment`, and one pure construction surface, `create_winner_validation_assessment`. The construction surface composes the exact P7.3 `DecisionContext` and `OpportunityHypothesis` with a non-empty ordered set of exact P7.6 `MarketTestEvidenceProfile` values. It preserves the caller's profile order, assessment evidence-reference order, and unresolved-uncertainty order.

The assessment records a stable caller-supplied identity, exact context and hypothesis identities, explicit timezone-aware `as_of`, the bound profile identities, caller-authored rationales, supporting evidence references, counter evidence references, and unresolved uncertainties. It does not copy, rewrite, synthesize, persist, or dereference the underlying evidence. Every assessment evidence reference must already occur in one of the four P7.6 evidence dimensions on a bound profile.

## Bounded judgment vocabularies

`HYPOTHESIS_CALIBRATION_DISPOSITIONS` is exactly, in order:

1. `ALIGNED`
2. `MIXED`
3. `MISALIGNED`
4. `INCONCLUSIVE`

These are ex-post semantic judgments about how caller-interpreted outcomes relate to the original hypothesis expectations and disconfirming conditions. Calibration judgment != probability calibration. No disposition is a certainty level, score, lifecycle state, or automatic truth.

`WINNER_VALIDATION_DISPOSITIONS` is exactly, in order:

1. `SUPPORTED`
2. `CONTRADICTED`
3. `INCONCLUSIVE`

These are contextual judgments about whether the supplied post-test evidence supports the hypothesis in the exact tested decision context. Validation disposition != lifecycle state. `SUPPORTED` != universal winner truth. It is not approval, recommendation, a commerce decision, or a persisted `VALIDATED_WINNER` or `SCALABLE_WINNER` state.

## Binding and minimum coherence

Pure construction verifies all of the following without external I/O:

- the hypothesis belongs to the exact supplied decision context;
- every profile belongs to that exact context and exact hypothesis;
- the ordered profile set is non-empty and its profile identities are unique;
- assessment `as_of` is not earlier than any bound profile `as_of`;
- every supporting or counter reference is anchored to at least one exposure, funnel, economic, or quality evidence dimension of a bound profile; and
- ordered values are nonblank, bounded, duplicate-free within each collection, single-line, deterministic, and safe for public projection.

Only local minimum-inspectability rules apply:

- `ALIGNED` requires supporting evidence;
- `MISALIGNED` requires counter evidence;
- `MIXED` requires both supporting and counter evidence;
- inconclusive calibration requires unresolved uncertainty;
- `SUPPORTED` requires supporting evidence and collective representation across all four P7.6 dimensions;
- `CONTRADICTED` requires counter evidence; and
- inconclusive winner validation requires unresolved uncertainty.

Represented != sufficient. Dimension representation says only that a caller supplied at least one opaque reference in that dimension. It does not establish relevance, quality, reliability, weight, or sufficiency. Supporting and counter evidence may coexist under any disposition whose local rule is met, and mixed/counter evidence remains visible. There is no universal score, threshold, formula, fixed cross-context weighting, or automatic winner rule.

## Epistemic and authority boundaries

- confidence != probability of winning. Existing Product Intelligence confidence measures data completeness, freshness, source reliability, and evidence coverage. P7.7 does not import it, copy it, reinterpret it as win probability, or statistically calibrate it.
- outcome != attribution. A test design reference, authorization reference, action reference, exposure evidence, and observed outcomes do not establish randomization, a valid control, counterfactual identification, incrementality, treatment effect, uplift, or causality.
- outcome != retroactive proof. A favorable outcome does not prove that an earlier hypothesis, recommendation, score, rank, or decision process was correct.
- one favorable test != scalable winner. Repeated support != automatic scalability. Scalability requires separate contextual judgment and is not a P7.7 output.
- validation != approval/decision. P7.7 neither authorizes nor selects an action, budget, traffic change, campaign, promotion, or roadmap item.
- learning != self-authorization. Assessment results do not automatically rewrite hypotheses, knowledge, policy, mandate, delegation, or future work.
- P7.7 does not mutate Product Intelligence policy. Scoring, ranking, category weights, confidence formulas, thresholds, and recommendation policy remain owned outside this package and require separately authorized change.

The P7.2 names `DISCOVERED_CANDIDATE`, `OPPORTUNITY_HYPOTHESIS`, `TEST_READY`, `VALIDATED_WINNER`, and `SCALABLE_WINNER` remain conceptual reasoning stages only. P7.7 adds no enum, field, state machine, transition, promotion, or automatic lifecycle state for them.

The mandatory boundary shorthand is preserved verbatim:

- calibration judgment != probability calibration
- confidence != probability of winning
- validation disposition != lifecycle state
- SUPPORTED != universal winner truth
- outcome != attribution
- outcome != retroactive proof
- represented != sufficient
- mixed/counter evidence remains visible
- one favorable test != scalable winner
- repeated support != automatic scalability
- validation != approval/decision
- learning != self-authorization
- P7.7 does not mutate Product Intelligence policy

## Deterministic public projection

`WinnerValidationAssessment.to_dict()` returns only JSON-serializable primitives, serializes `as_of` with ISO-8601, and preserves every ordered value. Construction and projection fail closed for blank, multiline, unbounded, object-representation, memory-address, obvious secret, cookie/session, model-prompt, execution-metadata, or raw-HTML payloads. No object representation or memory address is emitted.

## Lineage and roadmap closure

- TASK-191 / P7.1 remains CLOSED / PUBLISHED at `40da098b3b0dcf3d1994fc510dd55717b81a2f67`.
- TASK-214 / P7.2 remains CLOSED / PUBLISHED at `123bbb71d44ad15a25e07b07f21f6cb2dd00d20b`.
- TASK-215 / P7.3 remains CLOSED / PUBLISHED at `dc4c4c8e6f3f4d6eb3441ff4873632e5f51655f9`.
- TASK-222 / P7.4 remains CLOSED / PUBLISHED at `ca6da00e9e58f66e25f2f6edcb416677bed70b6d`.
- TASK-223 / P7.5 remains CLOSED / PUBLISHED at `3c67a828857f74466883463abf35a17ecdcc6775`.
- TASK-224 / P7.6 is CLOSED / PUBLISHED at `d361361958fbcbe791c04aefbeba3d186c5f9608`.
- TASK-225 / P7.7 is publication-gated DONE and is the current/final milestone of the Human-approved P7.2-P7.7 sequence.

The P7.2-P7.7 sequence becomes complete only after publication of the exact reviewed TASK-225 source candidate. There is no P7.8 and no pending or automatic P7 NEXT. Subsequent product sequencing requires fresh Brain/Human interpretation; Runtime, workers, evidence, outcomes, scores, and assessment dispositions cannot select it.

The exact AIOS-renew pin remains `edd7d8d92d54900c56442bbfcddb8648ec4d2e09`, with TASK-207 revision-8 downstream conformance unchanged. This document adds no AIOS, review, publication, or roadmap authority.
