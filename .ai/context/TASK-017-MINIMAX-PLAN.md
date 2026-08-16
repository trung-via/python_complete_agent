# TASK-017 — MiniMax-M3 Advisory PLAN

STATUS: VALIDATED
PLAN_ADOPTION_RECOMMENDATION: ACCEPTED_WITH_LOCAL_ADJUSTMENTS
CHATGPT_REPLAN_REQUIRED: NO

## Control Metadata
- Task: `TASK-017`
- Contract: `ADR-008`
- Current main at validation: `54303dc7d56ddce4ae9b22ef05c7dd310e731737`
- Provider: `minimax`
- Model: `MiniMax-M3`
- Request ID: `m31-real-plan-task017-005`
- Task ID: `TASK-017`
- Normalized status: `SUCCESS`
- Provider input tokens: `7921`
- Provider output tokens: `4232`
- Latency ms: `84525`
- Provider request ID: `06d0aabe8c45cb9f5a72e66d715be01d`
- Context counted tokens: `33354`
- Context counter: `utf8-byte-conservative-v1`
- Context count exact: `False`
- Context fingerprint: `a2c1611f56260a687849ab8871c6c3ba25d64118ba36abc51464af038803dc4f`
- Ledger persisted: `True`
- Separated reasoning persisted: `NO`
- Credentials persisted: `NO`

## Selected M2 Context
- `TASK` — `.ai/tasks/TASK-017.md`
- `CONTRACT` — `.ai/decisions/ADR-008-AIOS-BRIDGE-V0.5-M3.1-REAL-TASK-PROOF-CONTRACT-LOCK.md`
- `ARCHITECTURE` — generated existing API-surface signatures only
- `SOURCE` — `src/aios_bridge/external_brain/gateway.py`
- `TEST` — `tests/aios_bridge/external_brain/test_provider_contract.py`

No candidate was excluded by M2.

## Reviewer Adoption Notes
The MiniMax PLAN is sufficiently concrete for Antigravity to implement TASK-017 without ChatGPT replacement planning. TASK/ADR remain authoritative.

Apply these local adjustments while implementing:
1. Do **not** add `--print-plan-artifact` or another model-output write path in TASK-017. The runner should print the validated PLAN; the control-plane advisory artifact is managed separately.
2. Use finite defaults informed by the successful live proof. Prefer `max_output_tokens=8192` and `timeout_seconds=180.0` unless existing local conventions justify another finite value. Do not restore the failed 2048/30 combination as the primary real-task default.
3. A helper module under `src/aios_bridge/external_brain/` is allowed for testability, but re-exporting helpers from `__init__.py` is optional and should be avoided unless genuinely required.
4. Test placement/injection may be adjusted to fit existing repository conventions. Do not introduce a special production backdoor merely to inject a fake provider into subprocess tests.
5. The runner does not author `RESULT-017`; RESULT remains worker/publish evidence after implementation and tests.
6. Preserve all ADR-008 authority boundaries: no repo discovery, retry, fallback, router, patch application, shell/browser/Git/tool authority, or changes to `bridge.py` / Python Agent runtime providers.

These are local scope/parameter corrections, not an architectural re-plan.

## MiniMax PLAN

### SUMMARY
- Implement a thin manual External Brain PLAN runner (`scripts/aios_external_brain_plan.py`) plus a small testable helper module under `src/aios_bridge/external_brain/`, reusing existing M1/M2/M3 primitives (`ContextBuilder`, `ContextBudget`, `ContextItem`, `ModelRequest`, `ModelGateway`, `MiniMaxOpenAIProvider`, `JsonlUsageLedger`) — no new framework, no provider reimplementation.
- CLI accepts explicit `--task-file` and repeatable `--context KIND:PATH` (valid `ContextKind`s only: TASK, CONTRACT, SOURCE, TEST, DIFF, ERROR, ARCHITECTURE), reads credential only from `AIOS_MINIMAX_API_KEY`, performs no repo crawl/glob/discovery, fails closed before any network call on invalid inputs, and invokes the provider exactly once with `role=ARCHITECT`, `operation=PLAN`, `provider=minimax`, `model=MiniMax-M3`.
- On SUCCESS prints safe telemetry (status, provider/model, request_id, input/output tokens, latency, context fingerprint/count/counter id, ledger persistence) plus the validated PLAN; on failure prints bounded normalized status/error_code and exits non-zero; never prints/persists the API key, raw HTTP, or separated reasoning; the runner does NOT write `RESULT-017`.

### STEPS
1. Add `src/aios_bridge/external_brain/runner.py` with testable helpers for parsing context specs, loading explicit `ContextItem`s, building the PLAN `ModelRequest`, and rendering bounded safe success output.
2. Create `scripts/aios_external_brain_plan.py` with `argparse`: required `--task-file`; repeatable `--context KIND:PATH`; finite context/output/timeout controls; optional request ID and usage-ledger path. Keep the interface minimal and operator-controlled.
3. Implement preflight fail-closed checks before network use: credential present, task/context files readable, kinds valid, and local configuration valid. Print only bounded normalized local errors.
4. Parse TASK as `ContextKind.TASK`, parse explicitly supplied context using caller-supplied valid kinds, and run all candidates through the existing `ContextBuilder` + finite `ContextBudget`. Propagate M2 safety/integrity/budget failure without provider invocation.
5. Build `ModelRequest` from exactly `context_build.selected`; instantiate the existing `MiniMaxOpenAIProvider` and `ModelGateway`, optional `JsonlUsageLedger`, and call `gateway.invoke(request, context_build=...)` exactly once. No retry/fallback/second call.
6. On SUCCESS print normalized provider/model/request telemetry, provider usage, M2 fingerprint/count/counter metadata, ledger state, and final validated PLAN. On non-SUCCESS print bounded normalized status/error code and return non-zero. Never print key, raw HTTP, or separated reasoning.
7. Run focused tests, `tests/aios_bridge/`, and full `tests/`; worker/publish flow records the locked RESULT-017 evidence and PLAN adoption/deviations.

### FILES
1. `scripts/aios_external_brain_plan.py` — thin CLI entry point.
2. `src/aios_bridge/external_brain/runner.py` — optional small testable helper module where useful.
3. `tests/aios_bridge/external_brain/test_runner.py` — focused helper/gateway behavior tests using fakes/mocks only.
4. A CLI-focused test file may be added if needed by repository conventions; automated tests must remain local-only.
5. `.ai/context/TASK-017-MINIMAX-PLAN.md` — this read-only advisory control artifact; not authored by the runner.
6. Existing gateway/provider/context/usage modules are reused, not redesigned.

### TESTS
1. Missing `AIOS_MINIMAX_API_KEY` fails before provider/network invocation.
2. Missing/unreadable task file fails before provider/network invocation.
3. Invalid context kind/spec fails before provider/network invocation.
4. Explicit context only: no repo crawl, glob, semantic search, or automatic dependency discovery.
5. Valid explicit TASK/context passes through M2; `ModelRequest.context == context_build.selected`; gateway invoked exactly once.
6. Sensitive-context and context-budget failures fail closed without provider invocation.
7. Normalized provider failure returns non-zero with no retry/second call.
8. SUCCESS renders safe telemetry + final PLAN without API key, raw HTTP body, or reasoning content/markers.

Also satisfy every minimum test/acceptance item explicitly listed in TASK-017 even if not repeated above.

### RISKS
1. Credential leakage through errors/repr/output — keep credential env-only and render bounded normalized errors/telemetry.
2. Accidental repo discovery — accept/read only explicit task/context paths and test that boundary.
3. Accidental execution-authority widening — no patch, shell, browser, Git, tool, retry, fallback, registry, classifier, or router paths.
4. M2 safety/budget bypass — always route candidates through the existing unmodified ContextBuilder/ContextBudget.
5. Token/time overrun — finite context/output/timeout settings and exactly one provider call.

## Authority
This artifact is advisory context only. It does not authorize execution and cannot override TASK-017, ADR-008, safety/integrity invariants, or human `/aios-worker RUN TASK-017` approval.
