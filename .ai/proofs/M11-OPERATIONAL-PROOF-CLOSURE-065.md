# M11 Operational Proof Closure & Production Baseline Lock

```yaml
M11_STATUS: OPERATIONALLY_PROVEN
M11_CLOSED: YES
PRODUCTION_BASELINE_SHA: 5a714a410d4a4d5fc0b76cea62e7fd164f0cdd54
CLOSURE_RECORD_TASK: TASK-065
DATE_CLOSED: 2026-08-23
```

## 1. Closure Status

The M11 milestone (External Paid-Brain Escape Hatch Architecture & Runtime) is **OPERATIONALLY_PROVEN** and formally **CLOSED**.

The external paid-Brain escape hatch has executed a real one-shot MiniMax-M3 call under strict Human authorization, verified exact full input token counting (3155 == 3155), adhered to the bounded 120-second timeout and 8192-token completion envelope, created durable proposal and proof receipt artifacts, and preserved every core safety invariant with zero retry, zero second provider, and zero executor authority created.

## 2. Production Baseline

The production code and runtime baseline for M11 closure is locked at:

```text
BASELINE_MAIN_SHA: 5a714a410d4a4d5fc0b76cea62e7fd164f0cdd54
TASK_062_STATUS: PASS + MERGED (Real Operational Escape Harness)
TASK_063_STATUS: PASS + MERGED (Timeout Envelope Hardening: 60..180s)
TASK_064_STATUS: PASS + MERGED (Completion Envelope: 8192 tokens & Post-Consume Diagnostics)
FULL_SUITE_BASELINE: 1972 passed, 7 skipped, 0 failed
```

### Authoritative Architecture & Proof Lock References

```text
ADR_036_PATH: .ai/decisions/ADR-036-M11-EXTERNAL-API-ESCAPE-HATCH-ARCHITECTURE-LOCK.md
ADR_036_BLOB_SHA: cf71c571d8e3fd611ea07d21f15ad0bf90ef6ecc
PROOF_LOCK_PATH: .ai/context/TASK-062-PROOF-LOCK.json
PROOF_LOCK_BLOB_SHA: 9ff47f47c987f7e626f73b26ea9c783a59f6fd45
PROOF_LOCK_FINGERPRINT: a220f6747e78051a3bcb044cdc45ede9c650d4aeee7e5ea9e56487e4c2043da1
PROVIDER_ID: minimax
MODEL_ID: MiniMax-M3
ENDPOINT_URL: https://api.minimax.io/v1/chat/completions
CREDENTIAL_SOURCE: env:MINIMAX_API_KEY (Presence checked, value access deferred to post-gate factory)
```

## 3. Three Live Attempts Operational History

The M11 runtime was validated and hardened across three sequential live operational attempts:

### Attempt 1 ? Pre-TASK-063 (Initial Proof Execution)
- **Outcome**: `TIMEOUT` (at ~30.265 seconds).
- **Observed Latency**: 30,265 ms.
- **Root Cause**: Production `cmd_paid_proof_execute` hard-coded a 30.0s timeout in `MiniMaxOpenAIProvider` constructor.
- **Grant & State**: Grant transitioned to `CONSUMED` prior to call, zero retry, no proposal or proof published.
- **Remediation**: Developed and merged **TASK-063**, replacing the magic 30.0s timeout with a required explicit bounded CLI parameter `--provider-timeout-seconds` (range `60..180`, recommended `120`).

### Attempt 2 ? Post-TASK-063 / Pre-TASK-064 (Timeout Proven, Output Truncation)
- **Outcome**: `INVALID_RESPONSE / TRUNCATED_OUTPUT`.
- **Configured Timeout**: 120 seconds (Latency: 15,287 ms).
- **Input Token Accounting**: Exact correlation verified: local full provider input `3155` == provider-reported `prompt_tokens 3155` (context-only: 2758 tokens).
- **Output Token Accounting**: Provider generated exactly 2000 completion tokens and returned `finish_reason=length`. Provider adapter normalized this to `TRUNCATED_OUTPUT`.
- **Grant & State**: Grant remained `CONSUMED`, exactly 1 ledger record, zero retry, no proposal or proof published.
- **Remediation**: Developed and merged **TASK-064**, establishing canonical `M11_REAL_PROOF_MAX_OUTPUT_TOKENS = 8192` enforced pre-spend across preflight and execute paths, and adding bounded, allowlisted, secret-safe post-consume diagnostics.

### Attempt 3 ? Post-TASK-064 (Final Successful Proof Execution)
- **Outcome**: `SUCCESS / OPERATIONAL_PROOF_PASS`.
- **Configured Timeout**: 120 seconds (Latency: 82,645 ms).
- **Authorized Output Envelope**: 8,192 tokens.
- **Actual Generation**: 3,984 completion tokens (completed normally without truncation).
- **Input Tokens**: Exactly correlated: local count `3155` == provider `3155`.
- **Grant & State**: Grant transitioned to `CONSUMED`, exactly 1 provider call, 0 retries, durable `proposal.md` and `proof.json` artifacts generated.

## 4. Final Successful Proof Binding

```text
TASK_ID: TASK-062
RUNTIME_MAIN_SHA: 5a714a410d4a4d5fc0b76cea62e7fd164f0cdd54
CONTROL_COMMIT_SHA: 8daee57bc4e6b0ba470081247cd95a64b5e84fb5
SUBSCRIPTION_CAPACITY_FINGERPRINT: d23b13f989b480d6c9a2db396cc6ff6220f1cea8b52e5c77829e990901b241f9
PAID_CAPACITY_FINGERPRINT: d587f0911752a5443e2a07dd239247f63ad63ac774df2ef745d9075cea7d5d83
PREFLIGHT_FINGERPRINT: ca95ba98272e90cf27cb8b1d3fdf1b93f9fdd0d7f15b2627d5ee047dc49cb2c9
OPERATIONAL_PROOF_FINGERPRINT: a33718c201e171d8145b3cd98ea246073ba146ab29e8a0f404b306a178151c96
FINAL_GRANT_SHA256_NAMESPACE: b44af77179540f9efaf99496b83011367b853393d3b035cb436df51b8d3376e4
FINAL_GRANT_FINGERPRINT: 47a9c27b1d0c3ad48b380a48d23816f467b8a6e9855bd79ce3125c57da87d564
PROPOSAL_LOGICAL_PATH: paid_api_proofs/TASK-062/b44af77179540f9efaf99496b83011367b853393d3b035cb436df51b8d3376e4/proposal.md
PROPOSAL_SHA256: 5f5bfc8fddcdba00bbd72590793479490b34193bad9963432dba873d65c4c251
PROOF_LOGICAL_PATH: paid_api_proofs/TASK-062/b44af77179540f9efaf99496b83011367b853393d3b035cb436df51b8d3376e4/proof.json
FINAL_GRANT_STATE: CONSUMED
PROVIDER_CALL_COUNT: 1
RETRY_COUNT: 0
EXECUTOR_AUTHORITY_CREATED: NO
```

## 5. Durable Runtime Evidence Verification

Read-only verification of local runtime state confirms:

1. **Proof Artifacts**:
   - `paid_api_proofs/TASK-062/b44af77179540f9efaf99496b83011367b853393d3b035cb436df51b8d3376e4/proposal.md` exists with SHA-256 `5f5bfc8fddcdba00bbd72590793479490b34193bad9963432dba873d65c4c251`.
   - `paid_api_proofs/TASK-062/b44af77179540f9efaf99496b83011367b853393d3b035cb436df51b8d3376e4/proof.json` exists with matching operational proof fingerprint `a33718c201e171d8145b3cd98ea246073ba146ab29e8a0f404b306a178151c96`.
2. **Usage Ledger**:
   - `paid_api_usage/TASK-062/b44af77179540f9efaf99496b83011367b853393d3b035cb436df51b8d3376e4.jsonl` contains exactly 1 usage record (`status: SUCCESS`, `provider_input_tokens: 3155`, `provider_output_tokens: 3984`, `latency_ms: 82645`).
3. **Grant Store**:
   - Grant `b44af77179540f9efaf99496b83011367b853393d3b035cb436df51b8d3376e4.json` is located in `consumed/` directory with `max_output_tokens: 8192` and fingerprint `47a9c27b1d0c3ad48b380a48d23816f467b8a6e9855bd79ce3125c57da87d564`.
   - 0 active grants remain for TASK-062.
4. **Prior Attempt Grants**:
   - Prior attempt grants remain permanently non-active/consumed; no replay or reuse is possible.

## 6. Locked Safety Invariants

The following invariants remain strictly locked and enforced across the entire AIOS runtime:

```text
MAX_CALLS: 1
AUTO_RETRY: 0
SECOND_PAID_PROVIDER: 0
PAID_EXECUTOR: FORBIDDEN
GRANT_REUSE: FORBIDDEN
GRANT_REACTIVATION: FORBIDDEN
CONSUME_BEFORE_CALL: REQUIRED
MODEL_GATEWAY_INVOCATIONS: EXACTLY_ONE
EXECUTOR_AUTHORITY_CREATED: FALSE
BRAIN_OUTPUT_WORKTREE_AUTHORITY: FORBIDDEN
SECRET_VALUE_READ_BEFORE_POST_GATE_FACTORY: FORBIDDEN
PROVIDER_TIMEOUT_CONTRACT_SECONDS: 60..180
REAL_PROOF_MAX_OUTPUT_TOKENS: 8192
EXACT_INPUT_TOKEN_MATCH_REQUIRED: YES
R9_OPERATIONAL_PROOF_STRICTNESS: PRESERVED
```

## 7. Deferred / Non-Blocking Items

- **Reasoning-Token Telemetry**: `provider_reasoning_tokens` field is preserved in `UsageRecord` but omitted from `ModelResponse` to prevent cross-cutting contract migrations during proof closure. This remains deferred to a future milestone if needed.
- **Future Tasks**: No further M11 tasks (e.g. TASK-066) are authorized. M11 is complete.

## 8. Reopen Conditions

M11 may only be reopened under explicit Human direction if new, verifiable production evidence falsifies one of the locked invariants above or if the upstream provider interface changes fundamentally.
