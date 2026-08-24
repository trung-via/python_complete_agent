# ADR-057 — AIOS Bridge Lean Execution v1.1 Canonical Roadmap Normalization

STATUS: ACCEPTED
DECISION_TYPE: IMPLEMENTATION_REFINEMENT
HUMAN_APPROVED: YES
SEMANTIC_CAPABILITY_CHANGE: NO
AUTHORITY_CHANGE: NO
SEQUENCING_CHANGE: NO

ROADMAP_ID: AIOS-BRIDGE-LEAN-EXECUTION
PRIOR_ROADMAP_VERSION: 1.0
CANONICAL_ROADMAP_VERSION: 1.1
CANONICAL_ROADMAP: .ai/roadmaps/AIOS-BRIDGE-LEAN-EXECUTION-v1.1.md
ROADMAP_BLOB_SHA: cae51de4db517dd452c260076a1daa521c1e3a4c
ROADMAP_FINGERPRINT: 4bcbb10e1e8e02169ccb5a516801abd1ce01b0b5edd348d90abcac7d0887404f
ROADMAP_FINGERPRINT_ALGORITHM_VERSION: roadmap-sha256-v1

## Context

The Human-approved Lean Execution roadmap v1.0 correctly defined the P0 -> P3 capability sequence, but its Markdown shape was not consumable by the existing canonical `parse_canonical_roadmap()` contract. The current parser requires exactly `AUTHORITY: CANONICAL`, milestone headings shaped as `### <MILESTONE> — <title>`, and requirement identities shaped as `- <MILESTONE>.R<n> — <text>`.

Because no Lean Execution task has yet been authorized or executed against v1.0, the correct controlled-evolution action is to preserve v1.0 as historical evidence and create v1.1 as the canonical machine-enforceable normalization rather than mutate v1.0 in place.

## Decision

Adopt v1.1 as the canonical executable roadmap for AIOS-BRIDGE-LEAN-EXECUTION.

The following remain unchanged from the approved v1.0 design:

```text
North Star: minimize Time-to-Trusted-Capability
P0 Validation Ownership + Delivery Telemetry
P1 Unified Validation Profiles + Capability Batch
Python Agent fast-lane pilot before optional P2
P2 Provider-Neutral Executor Session only if telemetry justifies it
P3 Executor Portability + Adaptive Selection
H5 remains closed
Bridge control-plane authority remains preserved
no automatic retry
no automatic reroute
Human authority over executor substitution remains preserved
```

## Bootstrap Constraint

Current `DEFAULT_ROADMAP_REGISTRY` and `task_requires_roadmap_governance()` were implemented for H-Series only. Therefore the first P0 executable slice must bootstrap generic registration/enforcement for the Lean Execution roadmap before later P0 tasks can rely on normal Bridge roadmap preflight.

TASK-083 is authorized to perform that narrow bootstrap together with the validation-ownership foundation. This bootstrap does not change Human/task/review/lease/merge authority; it extends existing roadmap enforcement to the newly approved roadmap family.

## Supersession

```text
AIOS-BRIDGE-LEAN-EXECUTION v1.0 = HISTORICAL / NOT EXECUTABLE
AIOS-BRIDGE-LEAN-EXECUTION v1.1 = CANONICAL / EXECUTABLE TARGET
```

No task may bind v1.0 after this decision.
