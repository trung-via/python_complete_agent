# Phase 5.5 — Agent Reliability & Recovery Control Plane
## Implementation Guide & Status Report

**Baseline**: `main @ c95b88df`  
**Branch**: `p0-agent-reliability`  
**Timeline**: ~7 hours of focused work

---

## 🎯 Executive Summary

Your proposal for Phase 5.5 is **excellent and well-aligned with what's already built**.

**Good news**: Phase 5.4's **core reliability architecture is 90% complete**:
- ✅ Terminal state contract enforced
- ✅ Checkpoint integrity validation
- ✅ Session replay engine
- ✅ Integrity verification framework
- ✅ Multi-process safety

**What remains** (Phase 5.5 real work):
- **M2** — Recovery diagnostics classification layer
- **M3** — Integrity verification test hardening
- **M4** — E2E reliability test suite

---

## 📋 Milestone Status

### ✅ M1 — Run Lifecycle & Terminal-State Contract (DONE)

**Implementation**: `src/core/checkpoint_contract.py`

```python
def validate_state_transition(current_state: RunState, event: CheckpointEvent) -> RunState:
    # Terminal states (COMPLETED, FAILED, HALTED) are immutable
    # Cannot transition out of terminal state
    # Fail-closed on invalid transitions
    if current_state == RunState.COMPLETED:
        if evt_type in (RUN_COMPLETED, LLM_FINAL_RESPONSE, TASK_END):
            return RunState.COMPLETED  # Idempotent
        raise CheckpointStateError(...)  # Blocked
```

**Acceptance Criteria**: ✅ ALL MET
- ✅ One terminal state only (immutable)
- ✅ Fail-closed validation
- ✅ Clear failure domain distinction (USER_APP, LLM_PROVIDER, TOOL_EXECUTION, etc.)
- ✅ RunSummary dataclass with metadata
- ✅ Enforced in CheckpointManager.log_event()

---

### 🎯 M2 — Recovery Diagnostics & Failure Classification (PRIMARY FOCUS)

**Implementation location**: 
- `src/core/recovery_diagnostics.py` (NEW)
- `src/agent/loop.py` (enhance resume())

**Current state**: ❌ INCOMPLETE

**What's missing**:
- Resume doesn't classify failures explicitly
- No recovery state machine documentation
- No diagnostics on recovery potential

**To implement** (2-3 hours):

#### Step 1: Create RecoveryAnalyzer
```python
# src/core/recovery_diagnostics.py
@dataclass
class RecoveryDiagnostics:
    run_id: str
    current_state: RunState
    recovery_potential: Literal["RECOVERABLE", "NON_RECOVERABLE", "CORRUPT", "COMPLETED"]
    failure_domain: Optional[FailureDomain]
    error_message: str
    pending_tool_calls: int
    completed_tool_calls: int
    
    def can_retry(self) -> bool:
        return self.recovery_potential == "RECOVERABLE"

class RecoveryAnalyzer:
    @staticmethod
    def analyze(run_id: str, db_path: str) -> RecoveryDiagnostics:
        """Determine recovery potential without mutating state."""
        # Read checkpoint
        # Reconstruct session
        # Classify: RECOVERABLE | NON_RECOVERABLE | CORRUPT | COMPLETED
```

#### Step 2: Enhance AgentLoop.resume()
```python
async def resume(self, run_id: str) -> Optional[str]:
    """Resume with explicit failure classification."""
    # Use RecoveryAnalyzer to classify state
    # If COMPLETED → return answer (deterministic)
    # If RECOVERABLE → continue execution
    # If NON_RECOVERABLE or CORRUPT → raise specific error
    # Never silent recovery
```

#### Step 3: Document recovery state machine
- Create `docs/RECOVERY_STATE_MACHINE.md`
- Map: current_state × event → (recovery_potential, action)

**Tests to add**:
```python
# tests/core/test_recovery_diagnostics.py
def test_analyze_completed_run()
def test_analyze_recoverable_state()
def test_analyze_non_recoverable_state()
def test_analyze_corrupt_checkpoint()
def test_recovery_is_deterministic()
```

---

### 📊 M3 — Health / Integrity Verification (MOSTLY DONE)

**Implementation location**: `src/agent/integrity_verifier.py`

**Current state**: ✅ MOSTLY COMPLETE

**What exists**:
- ✅ RunIntegrityReport dataclass
- ✅ 6 audit checks (JSON syntax, sequence continuity, timestamps, state transitions, pending/completed tools, idempotency cross-check)
- ✅ Read-only verification (never mutates)
- ✅ Deterministic (idempotent)

**What's missing**:
- Recovery potential classification (can add 2-3 checks)
- Limited test coverage
- Failure domain detection

**To implement** (2 hours):

#### Step 1: Extend RunIntegrityReport
```python
@dataclass
class RunIntegrityReport:
    # ... existing fields ...
    recovery_potential: str = "UNKNOWN"  # ← NEW
    failure_domain: Optional[str] = None  # ← NEW
    last_event_time: Optional[float] = None  # ← NEW
    state_transitions: List[tuple[RunState, float]] = field(default_factory=list)  # ← NEW
```

#### Step 2: Add 3 new audit checks
```python
class RunIntegrityVerifier:
    @staticmethod
    def verify(...) -> RunIntegrityReport:
        # ... existing 6 checks ...
        
        # NEW 7: Classify recovery potential
        report.recovery_potential = classify_recovery_potential(
            state=report.state,
            pending_count=report.pending_tool_calls,
            issues=report.issues
        )
        
        # NEW 8: Detect failure domain
        if report.state == RunState.FAILED:
            report.failure_domain = detect_failure_domain(events)
        
        # NEW 9: Extract state transition timeline
        report.state_transitions = extract_state_timeline(events)
```

**Tests to add**:
```python
# tests/integration/test_phase55_integrity_verification.py
def test_verify_completed_run()
def test_verify_failed_run_with_domain()
def test_verify_corrupt_checkpoint()
def test_verify_partial_run_recovery_potential()
def test_verify_concurrent_interleaved_runs()
def test_verify_with_idempotency_store()
def test_verify_recovery_classification()
```

---

### 🧪 M4 — Operational Hardening & E2E Reliability (NEW)

**Implementation location**: `tests/integration/test_phase55_e2e_hardening.py` (NEW)

**Current tests**: 5 tests in `test_phase55_reliability_suite.py`

**Missing**: 10+ scenario tests per proposal

**To implement** (3 hours):

#### Test scenarios (10+ required):
```python
# Scenario 1: Multi-crash cascade
async def test_multi_crash_cascade_with_tool_recovery()
    # LLM crash → Resume → Tool crash → Resume → Complete

# Scenario 2: Process crash during checkpoint
async def test_process_crash_during_checkpoint_flush()

# Scenario 3: Tool done, checkpoint fails
async def test_tool_complete_checkpoint_write_fails()

# Scenario 4: Corrupted checkpoint
async def test_corrupted_checkpoint_fail_closed()

# Scenario 5: Resume after terminal (idempotent)
async def test_resume_completed_run_idempotent()

# Scenario 6: 4 concurrent processes
async def test_multiprocess_4_concurrent_runs()

# Scenario 7: Store compact/prune mid-recovery
async def test_recovery_with_concurrent_store_maintenance()

# Scenario 8: Tool retry exhaustion
async def test_tool_max_retries_halts_run()

# Scenario 9: LLM rate limit
async def test_llm_rate_limit_triggers_halt()

# Scenario 10: Full lifecycle
async def test_complete_lifecycle_with_integrity_checks()
```

#### Regression verification:
```python
def test_regression_164_plus_tests_all_pass():
    """pytest tests/ -q"""
    # Expected: ≥ 164 tests PASS
```

---

## 📁 File Changes Map

### New Files (3)
- `src/core/recovery_diagnostics.py` — RecoveryAnalyzer + RecoveryDiagnostics
- `docs/RECOVERY_STATE_MACHINE.md` — Documentation
- `tests/integration/test_phase55_e2e_hardening.py` — 10+ scenario tests

### Modified Files (3)
- `src/agent/loop.py` — enhance resume() with diagnostics
- `src/agent/integrity_verifier.py` — add recovery_potential, failure_domain, state_transitions
- `tests/integration/test_phase55_integrity_verification.py` — add 7+ tests

### Unchanged (protected)
- `src/core/checkpoint_contract.py` — no changes needed
- `src/core/checkpoint.py` — no changes needed
- `src/core/idempotency_store_v2.py` — no changes needed
- `src/agent/replay_engine.py` — no changes needed

---

## 🔄 Implementation Sequence

```
┌─────────────────────────────────────────────────────────┐
│ M1: Terminal State Contract                  ✅ DONE    │
│ (validate_state_transition, CheckpointStateError)       │
└─────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────┐
│ M2: Recovery Diagnostics (2-3 hours)        🎯 START    │
│ 1. RecoveryAnalyzer class                               │
│ 2. Enhance resume() classification                      │
│ 3. Document recovery state machine                      │
│ 4. Add 5 unit tests                                     │
└─────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────┐
│ M3: Integrity Hardening (2 hours)           ⏭️ NEXT    │
│ 1. Extend RunIntegrityReport                            │
│ 2. Add 3 audit checks                                   │
│ 3. Add 7+ integration tests                             │
└─────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────┐
│ M4: E2E Reliability Tests (3 hours)         🔚 FINAL   │
│ 1. Implement 10 scenario tests                          │
│ 2. Regression verification (164+ tests)                 │
│ 3. Final cleanup                                        │
└─────────────────────────────────────────────────────────┘
                              ↓
                    ✅ MERGE to main
```

---

## 🎯 Definition of Done

### Non-Breaking
- [x] No API breaking changes
- [x] No refactoring of existing systems
- [x] ReplayEngine stays read-only
- [x] Checkpoint logging unchanged

### Terminal State Contract
- [x] States immutable (COMPLETED, FAILED, HALTED)
- [x] CheckpointStateError on illegal transition
- [x] Validation fail-closed

### Recovery Diagnostics
- [ ] Resume distinguishes: RECOVERABLE | NON_RECOVERABLE | CORRUPT | COMPLETED
- [ ] No silent recovery (all paths explicit)
- [ ] Recovery deterministic (same input → same output)
- [ ] 5+ recovery path tests

### Integrity Verification
- [ ] RunIntegrityReport includes recovery_potential, failure_domain, state_transitions
- [ ] Verification never mutates filesystem
- [ ] Deterministic (idempotent)
- [ ] 9 audit checks implemented
- [ ] 7+ integration tests

### E2E Reliability
- [ ] 10 scenario tests implemented and passing
- [ ] Multi-process stress test passes
- [ ] Regression suite: ≥ 164 tests PASS
- [ ] Working tree clean

### Final
- [ ] Branch synced with main
- [ ] Code review ready
- [ ] Documentation complete

---

## 🚀 Ready to Start?

**Recommended next step**:
1. Create branch `p0-agent-reliability`
2. Start with **M2: Recovery Diagnostics** (highest value)
3. Implement RecoveryAnalyzer class
4. Enhance AgentLoop.resume()
5. Add unit tests

Would you like me to:
- [ ] Create the branch and start M2 implementation?
- [ ] Review current implementation in detail?
- [ ] Add more context on any milestone?

---

## 📞 Questions?

All infrastructure for Phase 5.5 is already in place. We're just adding the **diagnostics and verification layers** on top of the solid foundation that 5.3 + 5.4 built.
