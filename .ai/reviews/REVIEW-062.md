# REVIEW-062 — M11.3C Real Operational Escape Harness

STATUS: CHANGES_REQUIRED
APPROVED: NO
READY_FOR_HUMAN_MERGE: NO
MERGE_AUTHORIZED: NO
MERGED_TO_MAIN: NO

## Fresh Independent Review Binding

```text
TASK_ID: TASK-062
BASELINE_MAIN_SHA: d6f51f14188ffc56fd06bc887b68d9cad550c9e0
PRIOR_REVIEWED_HEAD_SHA: 82f461f5373f70d03f3035b021ae0fe1fc7c03d0
TARGET_BRANCH: ai/task-062
TASK_BLOB_SHA: 550add135a201c627aaac98b8fce26b1c9c93ace
BLUEPRINT_BLOB_SHA: 5b9a6a366a390a2f9f0735ebeff022cf62c9b551
RESULT_BLOB_SHA: a1f39d9edb32f73a0d0a4b97d237ff9c0b2a2728
BRIDGE_BLOB_SHA: bcfbc6a2f3fe1c2b73acf0f62647dd266ab8450e
INPUT_COUNTER_BLOB_SHA: 28928665d71e0bb818a8e4ff41281dd39d29105a
REAL_ESCAPE_BLOB_SHA: cd7ff36e64b3952b6db25b452b1da76c555b3265
INPUT_COUNTER_TEST_BLOB_SHA: a293817b9a9e8a40fad5a1f354b52fc5f6da8021
REAL_ESCAPE_TEST_BLOB_SHA: 11fa3de7133c6a062a15c0b724c6e9c235d8d309
BRIDGE_REAL_ESCAPE_TEST_BLOB_SHA: 802d433147ccdeb86952509e7dd1bb9c0926bf58
```

GitHub comparison proves at this review snapshot:

```text
main -> ai/task-062: ahead 2 / behind 0
merge-base: d6f51f14188ffc56fd06bc887b68d9cad550c9e0
82f461f... -> ai/task-062: ahead 1 / behind 0
scope: exact six authorized implementation/test paths + RESULT-062 publication output
```

The connector comparison surface does not expose the current symbolic branch head SHA directly. This review is therefore immutably snapshot-bound by the exact prior reviewed parent, the exactly-one-commit relation, and the exact current blob SHAs above. A future merge gate MUST resolve the exact current task head and re-check these blobs before moving `main`.

## Current Verdict

TASK-062 remains CHANGES_REQUIRED, but only one production code blocker remains.

```text
B1 credential-value boundary: UNRESOLVED
B2 symlink/junction containment: RESOLVED
B3 POSIX absolute-path sanitizer: RESOLVED
B4 publication/test evidence: RESOLVED
```

## B1 — CRITICAL — `name in os.environ` still reads the credential value on real CPython

The FIX replaced the early R4 value read with:

```python
if proof_lock.credential_env_name not in os.environ:
    ...
```

This looks like a key-presence-only check, but on real CPython `os.environ` is an `os._Environ` MutableMapping that does not provide a dedicated value-free `__contains__`. Mapping membership therefore falls back through mapping lookup semantics and reaches `__getitem__`, retrieving/decoding the environment value.

Therefore the production R4 code can still read the real `MINIMAX_API_KEY` value before R5 capacity validation, R6 dispatch proof, R7 full-input budget proof, and durable consume-before-call.

That still violates the locked blueprint boundary:

```text
Real credential value may exist only in provider process memory/environment after R0-R7 pass.
```

### Why the new regression test does not prove production behavior

The test replaces `os.environ` with a custom `GuardedEnviron(dict)` that explicitly overrides:

```python
def __contains__(self, key):
    return key in original_environ
```

That custom behavior is safer than the real `os._Environ` membership behavior and therefore masks the production issue. The test can truthfully report zero value reads only for the fake mapping, not for the actual runtime object.

### Required final fix

Use an explicit value-free key-presence helper before R7 that only iterates environment keys, for example a bounded semantic equivalent of:

```python
any(key == credential_env_name for key in os.environ)
```

Do not call `os.environ.get`, `os.getenv`, `os.environ[...]`, or membership semantics that can invoke value lookup before R7.

The actual secret value must remain retrieved only inside the deferred provider factory after the existing R7 gate and durable grant consumption permit the single provider call.

Add regression tests that mirror production mapping semantics rather than overriding `__contains__` with a safer implementation. At minimum prove:

```text
R0-R7 valid path: zero credential-value reads
R0-R7 validation failure: zero credential-value reads
same-grant replay rejection: zero credential-value reads
provider factory after consume: exactly one credential-value read is permitted
```

## B2 — PASS — external runtime containment hardened

The FIX now rejects symlink/junction/reparse-point components for runtime/proofs/task/final namespaces, resolves and verifies containment for `paid_api_proofs`, TASK directory, staging directory, and final directory, and keeps bounded error messages.

Regression coverage includes:

```text
paid_api_proofs symlink/junction -> outside: reject
task directory symlink/junction -> outside: reject
normal directory path: persist successfully
```

B2 is resolved.

## B3 — PASS — POSIX single-component absolute paths rejected

The sanitizer now rejects single-component and multi-component absolute POSIX paths. Regression tests cover `/tmp`, `/etc`, `/Users`, `/var`, `/etc/passwd`, and proposal text containing `/tmp` or `/etc/hosts`.

B3 is resolved.

## B4 — PASS — fresh evidence is sufficient

Fresh RESULT-062 clearly records the FIX delta and independent cumulative task scope remains verifiable from GitHub comparison.

Targeted suite:

```text
venv/Scripts/python.exe -m pytest tests/aios_bridge/test_minimax_m3_input_counter.py tests/aios_bridge/test_paid_api_real_escape.py tests/test_bridge_paid_api_real_escape.py -v
42 passed / 0 skipped / 0 failed
exit code 0
```

Full repository suite:

```text
venv/Scripts/python.exe -m pytest tests/ -q
1923 passed / 7 skipped / 0 failed
exit code 0
```

RESULT also records explicit no-spend boundaries:

```text
REAL_PAID_API_CALL_DURING_TASK: NO
REAL_API_KEY_USE_DURING_TASK: NO
REAL_GRANT_CONSUME_DURING_TASK: NO
```

B4 is resolved. The RESULT marker `CREDENTIAL_VALUE_READS_BEFORE_R7: ZERO` is not accepted as production proof until B1 above is corrected.

## Executor Continuity Note

Fresh RESULT records an explicit Bridge failover:

```text
ACTION: FIX
EXECUTOR_ID: antigravity
EXECUTOR_FAILOVER: YES
FAILOVER_FROM_EXECUTOR: codex
FAILOVER_TO_EXECUTOR: antigravity
FAILOVER_SOURCE_PUBLISHED_SHA: 82f461f5373f70d03f3035b021ae0fe1fc7c03d0
HOT_HANDOFF: NO
```

This is not treated as a silent reroute because RESULT carries explicit failover evidence and there was no hot handoff. However the prior review requested no second executor for the FIX. To avoid further continuity churn, the final B1-only FIX should remain on the current Antigravity lane unless the Human explicitly authorizes another executor switch.

## Required Final FIX

Preserve all B2-B4 fixes and all previously passing M11.3C semantics. Change only the credential presence probe and its regression coverage within the existing writable scope.

Do not redesign dispatch, grants, M11.2C consume-before-call, ModelGateway, MiniMax provider, proof-lock, or executor transport.

After FIX run:

```text
1. targeted TASK-062 suite
2. canonical full repository suite: venv/Scripts/python.exe -m pytest tests/ -q
3. truthful RESULT publication
```

## Verdict

```text
TASK-062: CHANGES_REQUIRED
MERGE: FORBIDDEN
LIVE_MINIMAX_PROOF: FORBIDDEN
NEXT: Human may authorize final FIX TASK-062 for B1 only.
```

No real paid MiniMax call may occur until TASK-062 reaches PASS, is Human-merged, and a separate fresh Human paid-spend/live-proof authorization is issued.
