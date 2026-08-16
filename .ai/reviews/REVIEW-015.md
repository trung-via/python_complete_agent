# REVIEW-015 — TASK-015 (AIOS Bridge v0.5-M2 Deterministic ContextBuilder + Token Budget)

## Status
APPROVED

## Reviewed Head
- Branch: `ai/task-015`
- Reviewed commit: `4f5fafc4f9c4f16413d3e4e2d13adc856509bde9`
- Previous reviewed head: `25f4dde8912040e5edfe1134f25e876a232b3811`
- Canonical baseline: `34b331c75d0577e403bb80b2ba0fe9818183b4f9`
- Branch relation to main: ahead 3, behind 0; merge base exactly canonical baseline
- RESULT-015 status: `READY_FOR_REVIEW`

## Verification Recorded in RESULT-015
- Focused External Brain suite: **44 passed**
- Full repository suite: **518 passed**
- No live external-model request was made
- No protected Bridge/runtime-provider subsystem was changed

## Final Blocker Resolution — Normalized-Path Collision Determinism
RESOLVED.

The reviewed head preserves normalized path as the semantic lexical tie-break and adds raw path only as the final deterministic discriminator when normalized path + digest + prior ranking keys collide.

The fallback is applied consistently to:
- pre-dedupe deterministic ordering;
- mandatory TASK ordering;
- mandatory CONTRACT ordering;
- optional ranking;
- exclusion ordering.

The raw-path dedupe identity remains unchanged, so `src/a.py` and `src\\a.py` remain distinct candidates as required by ADR-006.

Regression coverage explicitly verifies the collision case with identical kind, priority, content, and normalized path. Reversing caller input order yields:
- identical selected ordering;
- identical context fingerprint;
- identical atomic-budget winner;
- unchanged distinct raw-path identities.

## M2 Contract Review Summary
The implementation now satisfies ADR-006 and TASK-015 boundaries:

1. ContextBuilder selects only from explicitly supplied `ContextItem` candidates and does not crawl the repository/filesystem.
2. Ranking/budgeting is deterministic code only; no LLM/embedding/vector selection is used.
3. M1 contracts remain backward compatible.
4. TokenCounter is injectable; `counter_id` and `is_exact` are preserved in the result.
5. Default `utf8-byte-conservative-v1` counter is dependency-free and explicitly non-exact.
6. ContextBudget validates total/reserve semantics and budgets the context bundle only.
7. Canonical context framing is centralized and used for token counting.
8. SHA-256 integrity mismatch fails closed.
9. High-confidence sensitive paths/private-key material fail closed without echoing secret content.
10. At least one TASK is required; TASK/CONTRACT are mandatory when supplied.
11. Mandatory context cannot be silently truncated/dropped and overflow fails closed.
12. Exact duplicate identity `(kind, raw-path-or-empty, sha256)` is preserved and audited.
13. Optional ranking follows priority -> kind precedence -> normalized path -> digest with deterministic raw-path collision fallback.
14. Atomic greedy selection never exceeds available budget and may skip oversized optional items while later smaller items fit.
15. No content truncation/slicing is introduced.
16. Selected/excluded audit metadata and stable context fingerprint are present.
17. Equivalent candidate sets are permutation-invariant, including normalized-path collision cases.
18. No external model call, HTTP transport implementation, ModelGateway, provider adapter implementation, router, fallback, retry/quota registry, or usage ledger was introduced.
19. `bridge.py` and existing Python Agent `src.providers.LLMProvider` semantics remain untouched.
20. Focused and full repository suites pass with zero regression.

## Decision
APPROVED.

TASK-015 / AIOS Bridge v0.5-M2 Deterministic ContextBuilder + Token Budget is accepted at exact reviewed head:

`4f5fafc4f9c4f16413d3e4e2d13adc856509bde9`

The next milestone may proceed to **v0.5-M3 — ModelGateway + generic OpenAI-compatible transport + first external provider (MiniMax M3) + usage ledger**, while preserving all M1/M2 contracts and v0.4 Zero-Touch Handoff semantics.

Do not merge automatically unless the existing human merge gate is explicitly invoked.