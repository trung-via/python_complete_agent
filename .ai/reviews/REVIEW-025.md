# REVIEW-025 — TASK-025 Canonical Project State Identity & Freshness Hardening

STATUS: CHANGES_REQUIRED

## Review Scope
- Review round: `2` — ADR-017 Delta Fix Review + Final Independent Audit
- Reviewed branch: `ai/task-025`
- Reviewed branch head: `dba49b410675a0af35241939f41605f91a0db739`
- Tested implementation SHA reported by RESULT: `4bee2904495244d5ee90311da121cd7cf944b8a9`
- Previous reviewed branch head: `13c916a01c988325f693ec106e8060d43cd3c875`
- Base main: `47dbde428169bb003d010b9ded79c9528bb40fba`
- Branch relation: ahead `4`, behind `0`; merge-base exact current main.
- `13c916a... -> 4bee290...` changes only `src/aios_bridge/continuity/state.py`, `tests/aios_bridge/continuity/test_state.py`, and `tests/aios_bridge/continuity/test_failover.py`.
- `4bee290... -> dba49b4...` changes only `.ai/results/RESULT-025.md`; production code/tests at reviewed head equal the tested implementation.
- Review mode: first ADR-013 delta verification for R1-1/R1-2, then a fresh ADR-017 Final Independent Audit reconstructed from TASK-025, ADR-011/ADR-016, final Canonical State implementation, state/freshness tests, failover coupling, RESULT evidence, and branch/base relation.
- Test counts below are RESULT evidence from Antigravity; this review did not independently execute the repository test suite.

## ADR-017 Stage Result

```text
FULL_SEMANTIC_REVIEW: PASS after R1 remediation
KNOWN_FINDINGS: OPEN
DELTA_FIX_REVIEW: PASS
FINAL_INDEPENDENT_AUDIT: FAIL
APPROVED: NO
```

## R1 Finding Closure

### R1-1 — POSIX `.` segment aliases
RESOLVED.

`_validate_artifact_path()` now rejects every path component exactly equal to `.` fail-closed without normalization. Regression checks cover `.ai/./...`, `.ai/context/./...`, `.ai/decisions/./...`, embedded dot segments, and retain existing `..`/empty-segment rejection.

### R1-2 — TASK-022 failover collision defense direct proof
RESOLVED.

The failover tests now retain the new Canonical State constructor collision gate **and** directly exercise the independent `_validate_context_refs_content_anchored()` collision defense using test-only malformed `ContinuityState`/`ContinuityArtifacts` objects. Different-blob task-vs-contract and same-blob task-vs-plan collisions both reach `validate_brain_failover_eligibility()` and fail with the failover-layer `Ambiguous state artifact path collision in canonical state` error.

No production change to `failover.py` was introduced.

## Final Independent Audit Findings

The Final Independent Audit deliberately did not limit its search space to R1-1/R1-2. It found two additional Canonical State contract defects.

### R2-1 — `contracts` accepts unordered/one-shot iterables, weakening deterministic state/fingerprint semantics
Severity: HIGH

ADR-011 defines `artifacts.contracts` as a deterministic ordered tuple/list. TASK-025 C6 preserves deterministic canonical JSON/fingerprint semantics.

Current `ContinuityArtifacts.__post_init__()` does:

```python
if not isinstance(self.contracts, tuple):
    object.__setattr__(self, "contracts", tuple(self.contracts))
```

This accepts arbitrary iterables, including `set` / `frozenset` and generators. A set of frozen `ArtifactRef` objects can therefore be accepted and converted into a tuple using an iteration order that is not a stable contract representation across Python processes/hash seeds. A one-shot or externally stateful iterable is likewise outside the locked ordered tuple/list contract.

Consequences:
- accepted constructor input can produce process-dependent contract ordering;
- canonical JSON and the state fingerprint can vary for the same logical unordered contract set;
- freshness issue ordering and downstream state anchoring inherit that nondeterminism;
- invalid unordered input is silently widened into a supposedly canonical state instead of failing closed.

Required fix:
- accept only an already-ordered `tuple` or `list` for direct `ContinuityArtifacts.contracts` construction;
- convert `list` to tuple deterministically;
- reject `set`, `frozenset`, generators, mappings, strings and other arbitrary iterables with `ContinuityStateValidationError`;
- keep `from_dict()` JSON list behavior unchanged;
- do not sort contracts silently because ADR-011 defines an ordered collection and changing caller order would alter semantics;
- add tests for tuple pass, list pass + tuple storage, set/frozenset/generator rejection, and canonical fingerprint stability for valid ordered inputs.

### R2-2 — PLAN task identity still silently normalizes non-canonical TASK-token forms
Severity: MEDIUM

ADR-011 locks canonical task IDs as case-sensitive `^TASK-\d+$` and forbids lowercase/mixed-case normalization. TASK-025 C6 explicitly preserves plan task-identity behavior **unless a correctness defect is demonstrated**.

Current PLAN identity check uppercases the path and matches:

```python
plan_path_upper = self.artifacts.plan.path.upper()
found_task_tokens = re.findall(r"TASK[-_](\d+)", plan_path_upper)
```

It therefore treats forms such as:

```text
task-025
TaSk-025
TASK_025
```

as equivalent declarations of canonical `TASK-025`. It also scans the entire path rather than the filename, although ADR-011 specifies the filename declaration rule.

This is silent identity normalization at the Canonical State boundary and is inconsistent with the exact-canonical policy now applied elsewhere.

Required fix:
- evaluate the PLAN **filename** rather than parent directories;
- use delimiter-aware task-like token detection;
- if the filename contains a task-like `TASK[-_]digits` token in any case/form, require that token to be exactly the active canonical `task_id` (`TASK-<exact digits>`, case-sensitive, hyphen only);
- reject lowercase/mixed-case, underscore, leading-zero aliases, shortened aliases and wrong-task canonical tokens fail-closed;
- filenames with no task-like token remain allowed under the ADR-011 optional-declaration rule;
- add tests for canonical active token pass; wrong task, lowercase/mixed-case, underscore, `TASK-25` vs `TASK-025`, `TASK-0025`, and parent-directory-only task-like text behavior.

Do not widen this FIX into PLAN content parsing or filesystem/Git discovery.

## Positive Final-Audit Evidence

The audit reconfirms:
- BranchState branch, ArtifactRef path/ref and Brain/Executor actor IDs now reject whitespace padding;
- artifact paths reject absolute paths, backslashes, empty segments, `..`, and now `.` aliases;
- authoritative artifact paths are unique across task/contracts/plan/result/review for accepted canonical paths;
- omitted artifact observations construct successfully and produce `INCOMPLETE` when required facts are absent;
- observation mappings are defensively copied and immutable through `MappingProxyType`;
- invalid Brain operation parsing remains inside `ContinuityStateValidationError`;
- schema version remains `1`; `MAX_SERIALIZED_BYTES` remains `16384`;
- phase/next-operation, task-branch SHA, exact TASK/RESULT/REVIEW role paths, sensitive-path checks, 16 KiB gates and STALE > INCOMPLETE > FRESH precedence remain intact;
- production scope remains limited to `state.py`; `brain.py`, `usage.py`, `failover.py`, Bridge, providers and executor production code are unchanged;
- TASK-022 failover content anchoring, fingerprint anchoring and duplicate-path defense remain present;
- no RUN/FIX/MERGE authority, routing, provider or execution behavior was widened.

RESULT reports against tested implementation `4bee2904495244d5ee90311da121cd7cf944b8a9`:

```text
Continuity: 76 passed
AIOS Bridge: 162 passed
Full repository: 636 passed
Regressions: 0
LIVE_EXTERNAL_CALLS: 0
BRIDGE_V0_4_BEHAVIOR_CHANGED: NO
AUTHORITY_WIDENED: NO
EXECUTOR_RUNS: 1
EXECUTOR_FIX_RUNS: 1
CANONICAL_STATE_COMPATIBLE: YES
TASK_022_FAILOVER_REGRESSION: PASS
```

The FIX RESULT correctly records `PREVIOUS_REVIEW_SHA: 524679e130986aba6363e6b7d4290d20cbd832b4`, the exact Round-1 REVIEW blob.

## Required FIX Scope

Expected next delta is bounded to:

```text
src/aios_bridge/continuity/state.py
tests/aios_bridge/continuity/test_state.py
.ai/results/RESULT-025.md
```

`tests/aios_bridge/continuity/test_failover.py` should not need another semantic change unless a regression test must be adjusted solely because of stricter state construction.

Do not change `brain.py`, `usage.py`, `failover.py` production, Bridge, providers, executor, schema version, state publication or authority semantics.

## Required Re-Test

```text
pytest tests/aios_bridge/continuity/test_state.py -q
pytest tests/aios_bridge/continuity/ -q
pytest tests/aios_bridge/ -q
pytest tests/ -q -W ignore
```

No live external calls.

## Decision

`CHANGES_REQUIRED`

After R2-1 and R2-2 are fixed, perform ADR-013 delta verification and then another fresh ADR-017 Final Independent Audit before emitting `APPROVED`.