"""
Deterministic M8 Real Multi-Agent Continuity Proof Runner & Verifier (TASK-032 / ADR-022).
Composes M3/M3B Brain continuity and M5/M6/M7 Executor continuity to prove cross-domain
failover across both Brain and Executor boundaries without transcript transfer.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

REPO_DIR = Path(__file__).resolve().parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from src.aios_bridge.continuity.brain import (
    BrainCapability,
    BrainOperation,
    BrainOutputType,
    BrainRequest,
    BrainResult,
    BrainResultStatus,
    ContextRef,
    OutputContract,
)
from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.failover import (
    BrainFailoverProof,
    build_replacement_brain_request,
    validate_brain_failover_eligibility,
)
from src.aios_bridge.continuity.state import (
    MAX_SERIALIZED_BYTES,
    SCHEMA_VERSION,
    ArtifactRef,
    BranchState,
    BrainState,
    ContinuityArtifacts,
    ContinuityPhase,
    ContinuityState,
    ExecutorState,
    NextOperation,
)

FORBIDDEN_ATTESTATION_KEYS = {
    "transcript",
    "transcripts",
    "raw_prompt",
    "raw_prompts",
    "raw_response",
    "raw_responses",
    "cookie",
    "cookies",
    "token",
    "tokens",
    "session",
    "sessions",
    "auth",
    "cot",
    "reasoning",
    "history",
}

_TOKEN_USAGE_PATTERN = re.compile(r"^(UNKNOWN|REPORTED\([a-zA-Z0-9_\-:, .]+\))$")

REQUIRED_DIAGNOSIS_SECTIONS = ("CAUSE", "EVIDENCE", "FIX", "TESTS", "RISKS")


def normalize_line_endings(text: str | bytes) -> bytes:
    """
    Deterministic newline-only normalization (LF only, single trailing LF).
    """
    if isinstance(text, (bytes, bytearray)):
        decoded = bytes(text).decode("utf-8")
    else:
        decoded = str(text)

    normalized = decoded.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    return normalized.encode("utf-8")


def compute_git_blob_sha(content_bytes: bytes) -> str:
    """
    Computes git blob SHA-1: sha1("blob " + len + "\\0" + content).
    """
    header = f"blob {len(content_bytes)}\0".encode("utf-8")
    return hashlib.sha1(header + content_bytes).hexdigest()


def compute_sha256(content_bytes: bytes) -> str:
    """
    Computes standard SHA-256 hex digest.
    """
    return hashlib.sha256(content_bytes).hexdigest()


def validate_m8_controlled_source_result(source_result: BrainResult) -> None:
    """
    Enforces TASK-032 C4 / AIP-4 controlled source mode:
    status == INCOMPLETE
    error_code == 'M8-CONTROLLED-BRAIN-HANDOFF'
    artifact_ref is None
    evidence_ref is None
    """
    if source_result.status != BrainResultStatus.INCOMPLETE:
        raise ContinuityStateValidationError(
            f"TASK-032 requires source result status INCOMPLETE, got: {source_result.status.value}"
        )
    if source_result.error_code != "M8-CONTROLLED-BRAIN-HANDOFF":
        raise ContinuityStateValidationError(
            f"TASK-032 requires error_code 'M8-CONTROLLED-BRAIN-HANDOFF', got: {source_result.error_code!r}"
        )
    if source_result.artifact_ref is not None:
        raise ContinuityStateValidationError("TASK-032 controlled source result must not contain artifact_ref")
    if source_result.evidence_ref is not None:
        raise ContinuityStateValidationError("TASK-032 controlled source result must not contain evidence_ref")


def validate_m8_diagnosis_artifact(content_text: str) -> None:
    """
    Enforces compact structured diagnosis sections (TASK-032 C2).
    """
    for section in REQUIRED_DIAGNOSIS_SECTIONS:
        pattern = rf"(^|\n)##?\s*{section}\b"
        if not re.search(pattern, content_text, re.IGNORECASE):
            raise ContinuityStateValidationError(
                f"TASK-032 diagnosis artifact missing required section: '{section}'"
            )


def validate_m8_attestation(attestation_data: dict[str, Any]) -> None:
    """
    Validates that the live Brain proof attestation contains zero forbidden keys (C5)
    and strictly compliant token format.
    """
    for key in attestation_data:
        if key.lower() in FORBIDDEN_ATTESTATION_KEYS:
            raise ContinuityStateValidationError(
                f"TASK-032 attestation contains forbidden key: '{key}'"
            )

    token_usage = attestation_data.get("token_usage")
    if token_usage is not None:
        if not isinstance(token_usage, str) or not _TOKEN_USAGE_PATTERN.match(token_usage):
            raise ContinuityStateValidationError(
                f"TASK-032 attestation token_usage format invalid: {token_usage!r}"
            )


TASK_032_PATH = ".ai/tasks/TASK-032.md"
ADR_022_PATH = ".ai/decisions/ADR-022-M8-MULTI-AGENT-CONTINUITY-PROOF-CONTRACT-LOCK.md"
RESULT_032_PATH = ".ai/results/RESULT-032.md"


def prepare_brain_pack(
    repo_dir: Path,
    output_dir: Path,
    task_id: str = "TASK-032",
    base_main_sha: str = "08508e48f6ffda70d1891dad461f6fd1b893b24b",
    source_published_sha: str | None = None,
    source_brain_id: str = "chatgpt-chat",
    replacement_brain_id: str = "claude-chat",
) -> dict[str, Any]:
    """
    Prepares the exact S0-bound canonical Brain proof bundle (AIP-3 / C1 / C3 / C4 / C5 / R1-2).
    """
    if source_brain_id == replacement_brain_id:
        raise ContinuityStateValidationError(
            f"TASK-032 requires distinct source and replacement Brains: {source_brain_id} vs {replacement_brain_id}"
        )

    # Determine and validate S0
    if not source_published_sha:
        p_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=False, capture_output=True, text=True)
        if p_head.returncode != 0 or not p_head.stdout.strip():
            raise ContinuityStateValidationError("Failed to resolve git HEAD for source_published_sha")
        source_published_sha = p_head.stdout.strip()

    if not re.match(r"^[0-9a-f]{40}$", source_published_sha):
        raise ContinuityStateValidationError(
            f"source_published_sha must be a 40-hex lowercase string, got: {source_published_sha!r}"
        )

    # Check commit existence in git object database
    p_check_commit = subprocess.run(["git", "cat-file", "-e", f"{source_published_sha}^{{commit}}"], cwd=repo_dir, check=False, capture_output=True)
    if p_check_commit.returncode != 0:
        raise ContinuityStateValidationError(
            f"source_published_sha '{source_published_sha}' does not exist as a commit in git object store"
        )

    # Resolve authoritative control commit strictly (R1-2 Round 2)
    control_ref = "origin/ai-control"
    p_ctrl = subprocess.run(["git", "rev-parse", control_ref], cwd=repo_dir, check=False, capture_output=True, text=True)
    if p_ctrl.returncode != 0 or not p_ctrl.stdout.strip():
        # Fallback to local tracking branch if remote not configured in test environments
        p_ctrl = subprocess.run(["git", "rev-parse", "ai-control"], cwd=repo_dir, check=False, capture_output=True, text=True)
        if p_ctrl.returncode != 0 or not p_ctrl.stdout.strip():
            raise ContinuityStateValidationError("Failed to resolve authoritative control commit (tried origin/ai-control and ai-control)")
    control_commit_sha = p_ctrl.stdout.strip()
    if not re.match(r"^[0-9a-f]{40}$", control_commit_sha):
        raise ContinuityStateValidationError(f"Invalid control commit SHA: {control_commit_sha!r}")

    # Resolve exact artifact blobs strictly from their designated provenance domains (R1-2)
    # RESULT-032 strictly from S0
    p_res = subprocess.run(["git", "rev-parse", f"{source_published_sha}:{RESULT_032_PATH}"], cwd=repo_dir, check=False, capture_output=True, text=True)
    if p_res.returncode != 0 or not p_res.stdout.strip():
        err = p_res.stderr.strip() if p_res.stderr else p_res.stdout.strip()
        raise ContinuityStateValidationError(
            f"Failed to resolve exact source RESULT-032 at S0 commit {source_published_sha[:10]}: {err}"
        )
    result_blob = p_res.stdout.strip()
    if not re.match(r"^[0-9a-f]{40}$", result_blob) or result_blob == "0" * 40:
        raise ContinuityStateValidationError(f"Resolved invalid blob SHA for RESULT-032 at S0: {result_blob!r}")

    # TASK-032 and ADR-022 strictly from authoritative control commit
    p_task = subprocess.run(["git", "rev-parse", f"{control_commit_sha}:{TASK_032_PATH}"], cwd=repo_dir, check=False, capture_output=True, text=True)
    if p_task.returncode != 0 or not p_task.stdout.strip():
        err = p_task.stderr.strip() if p_task.stderr else p_task.stdout.strip()
        raise ContinuityStateValidationError(
            f"Failed to resolve exact TASK-032 at control commit {control_commit_sha[:10]}: {err}"
        )
    task_blob = p_task.stdout.strip()
    if not re.match(r"^[0-9a-f]{40}$", task_blob) or task_blob == "0" * 40:
        raise ContinuityStateValidationError(f"Resolved invalid blob SHA for TASK-032 at control commit: {task_blob!r}")

    p_adr = subprocess.run(["git", "rev-parse", f"{control_commit_sha}:{ADR_022_PATH}"], cwd=repo_dir, check=False, capture_output=True, text=True)
    if p_adr.returncode != 0 or not p_adr.stdout.strip():
        err = p_adr.stderr.strip() if p_adr.stderr else p_adr.stdout.strip()
        raise ContinuityStateValidationError(
            f"Failed to resolve exact ADR-022 at control commit {control_commit_sha[:10]}: {err}"
        )
    adr_blob = p_adr.stdout.strip()
    if not re.match(r"^[0-9a-f]{40}$", adr_blob) or adr_blob == "0" * 40:
        raise ContinuityStateValidationError(f"Resolved invalid blob SHA for ADR-022 at control commit: {adr_blob!r}")

    # Build Canonical State with explicit provenance
    task_ref = ArtifactRef(path=TASK_032_PATH, ref=control_commit_sha, blob_sha=task_blob)
    adr_ref = ArtifactRef(path=ADR_022_PATH, ref=control_commit_sha, blob_sha=adr_blob)
    result_ref = ArtifactRef(path=RESULT_032_PATH, ref=source_published_sha, blob_sha=result_blob)

    state = ContinuityState(
        schema_version=SCHEMA_VERSION,
        task_id=task_id,
        phase=ContinuityPhase.READY_FOR_REVIEW,
        next_operation=NextOperation.REVIEW,
        main=BranchState(branch="main", sha=base_main_sha),
        task_branch=BranchState(branch="ai/task-032", sha=source_published_sha),
        artifacts=ContinuityArtifacts(
            task=task_ref,
            contracts=(adr_ref,),
            result=result_ref,
        ),
        brain=BrainState(last_id=source_brain_id, last_operation=BrainOperation.DIAGNOSIS),
        executor=ExecutorState(last_id="antigravity"),
    )
    state_fingerprint = state.fingerprint()

    # Build Context Refs
    context_refs = (
        ContextRef(
            path=TASK_032_PATH,
            blob_sha=task_blob,
            description="Task contract",
        ),
        ContextRef(
            path=ADR_022_PATH,
            blob_sha=adr_blob,
            description="ADR-022 contract",
        ),
        ContextRef(
            path=RESULT_032_PATH,
            blob_sha=result_blob,
            description="Prior result",
        ),
    )

    output_contract = OutputContract(
        expected_output_type=BrainOutputType.DIAGNOSIS_ARTIFACT,
        target_artifact_path=".ai/context/proofs/TASK-032-M8/brain/BRAIN-DIAGNOSIS.md",
    )

    source_request = BrainRequest(
        schema_version="1",
        task_id=task_id,
        request_id="req-task-032-diag-001",
        brain_id=source_brain_id,
        operation=BrainOperation.DIAGNOSIS,
        objective="Independently diagnose whether S0 is safe and contract-complete for cross-executor M8 continuation",
        output_contract=output_contract,
        context_refs=context_refs,
    )

    replacement_request = build_replacement_brain_request(
        source_request,
        replacement_brain_id=replacement_brain_id,
        replacement_request_id="req-task-032-diag-002",
    )

    replacement_capability = BrainCapability(
        brain_id=replacement_brain_id,
        supported_operations=(BrainOperation.DIAGNOSIS, BrainOperation.PLAN),
    )

    # Save to output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "canonical-state.json").write_text(state.to_canonical_json(), encoding="utf-8")
    (output_dir / "source-request.json").write_text(source_request.to_canonical_json(), encoding="utf-8")
    (output_dir / "replacement-request.json").write_text(replacement_request.to_canonical_json(), encoding="utf-8")
    (output_dir / "replacement-capability.json").write_text(json.dumps(replacement_capability.to_dict(), indent=2), encoding="utf-8")

    prompt_md = f"""# TASK-032 M8 Brain Diagnosis Prompt

## Task Context
- Task ID: `{task_id}`
- Base Main SHA: `{base_main_sha}`
- Shared Boundary SHA (S0): `{source_published_sha}`
- Canonical State Fingerprint: `{state_fingerprint}`
- Control Commit SHA: `{control_commit_sha}`

## Objective
Independently diagnose whether S0 is safe and contract-complete for a cross-executor M8 continuation,
and identify any invariant that would block the continuation.

## Required Output Format (Markdown)
Please provide the diagnosis strictly containing the following sections:
## CAUSE
## EVIDENCE
## FIX
## TESTS
## RISKS
"""
    (output_dir / "BRAIN_PROMPT.md").write_text(prompt_md, encoding="utf-8")

    return {
        "task_id": task_id,
        "source_published_sha": source_published_sha,
        "control_commit_sha": control_commit_sha,
        "state_fingerprint": state_fingerprint,
        "source_request_id": source_request.request_id,
        "replacement_request_id": replacement_request.request_id,
        "output_dir": str(output_dir),
    }


def verify_brain_proof(proof_dir: Path) -> dict[str, Any]:
    """
    Verifies the Brain proof bundle (AIP-4 / C4 / C5 / C6 / R1-3 / R1-4).
    """
    req_files = [
        "canonical-state.json",
        "source-request.json",
        "replacement-request.json",
        "replacement-capability.json",
        "source-result.json",
        "replacement-result.json",
        "brain-failover-proof.json",
        "BRAIN-DIAGNOSIS.md",
        "brain-proof-attestation.json",
    ]
    for rf in req_files:
        p = proof_dir / rf
        if not p.exists():
            raise ContinuityStateValidationError(f"Missing required Brain proof file: {rf}")

    state = ContinuityState.from_json((proof_dir / "canonical-state.json").read_text(encoding="utf-8"))
    source_req = BrainRequest.from_json((proof_dir / "source-request.json").read_text(encoding="utf-8"))
    repl_req = BrainRequest.from_json((proof_dir / "replacement-request.json").read_text(encoding="utf-8"))
    repl_cap = BrainCapability.from_dict(json.loads((proof_dir / "replacement-capability.json").read_text(encoding="utf-8")))
    source_res = BrainResult.from_json((proof_dir / "source-result.json").read_text(encoding="utf-8"))
    repl_res = BrainResult.from_json((proof_dir / "replacement-result.json").read_text(encoding="utf-8"))
    proof = BrainFailoverProof.from_json((proof_dir / "brain-failover-proof.json").read_text(encoding="utf-8"))
    diag_raw = (proof_dir / "BRAIN-DIAGNOSIS.md").read_bytes()
    attestation = json.loads((proof_dir / "brain-proof-attestation.json").read_text(encoding="utf-8"))

    # 1. State validation (validated during ContinuityState.from_json)

    # 2. Source Result validation (controlled non-success)
    validate_m8_controlled_source_result(source_res)
    if source_res.task_id != source_req.task_id:
        raise ContinuityStateValidationError(f"Source result task_id mismatch: '{source_res.task_id}' vs '{source_req.task_id}'")
    if source_res.request_id != source_req.request_id:
        raise ContinuityStateValidationError(f"Source result request_id mismatch: '{source_res.request_id}' vs '{source_req.request_id}'")
    if source_res.brain_id != source_req.brain_id:
        raise ContinuityStateValidationError(f"Source result brain_id mismatch: '{source_res.brain_id}' vs '{source_req.brain_id}'")
    if source_res.operation != source_req.operation:
        raise ContinuityStateValidationError(f"Source result operation mismatch: '{source_res.operation.value}' vs '{source_req.operation.value}'")

    # 3. Diagnosis artifact validation
    diag_norm = normalize_line_endings(diag_raw)
    validate_m8_diagnosis_artifact(diag_norm.decode("utf-8"))
    diag_blob_sha = compute_git_blob_sha(diag_norm)

    # 4. Replacement Result validation (R1-4: full identity, output contract, and storage domain binding)
    if repl_res.status != BrainResultStatus.SUCCESS:
        raise ContinuityStateValidationError(f"Replacement result status must be SUCCESS, got: {repl_res.status.value}")
    if repl_res.task_id != repl_req.task_id:
        raise ContinuityStateValidationError(f"Replacement result task_id mismatch: '{repl_res.task_id}' vs '{repl_req.task_id}'")
    if repl_res.request_id != repl_req.request_id:
        raise ContinuityStateValidationError(f"Replacement result request_id mismatch: '{repl_res.request_id}' vs '{repl_req.request_id}'")
    if repl_res.brain_id != repl_req.brain_id:
        raise ContinuityStateValidationError(f"Replacement result brain_id mismatch: '{repl_res.brain_id}' vs '{repl_req.brain_id}'")
    if repl_res.brain_id == source_req.brain_id:
        raise ContinuityStateValidationError("Replacement brain_id must differ from source brain_id")
    if repl_res.operation != repl_req.operation:
        raise ContinuityStateValidationError(f"Replacement result operation mismatch: '{repl_res.operation.value}' vs '{repl_req.operation.value}'")
    if repl_res.output_type != repl_req.output_contract.expected_output_type:
        raise ContinuityStateValidationError(
            f"Replacement result output_type mismatch: '{repl_res.output_type.value}' vs '{repl_req.output_contract.expected_output_type.value}'"
        )
    if not repl_res.artifact_ref:
        raise ContinuityStateValidationError("Replacement result missing artifact_ref")
    if repl_res.artifact_ref.path != repl_req.output_contract.target_artifact_path:
        raise ContinuityStateValidationError(
            f"Replacement result artifact path mismatch: '{repl_res.artifact_ref.path}' vs '{repl_req.output_contract.target_artifact_path}'"
        )
    if repl_res.artifact_ref.blob_sha != diag_blob_sha:
        raise ContinuityStateValidationError(
            f"Replacement result artifact blob mismatch: '{repl_res.artifact_ref.blob_sha}' vs '{diag_blob_sha}'"
        )
    approved_control_domain_pattern = re.compile(r"^(ai-control|refs/remotes/[a-zA-Z0-9_\-]+/ai-control|origin/ai-control|[0-9a-f]{40})$")
    if not repl_res.artifact_ref.ref or not approved_control_domain_pattern.match(repl_res.artifact_ref.ref):
        raise ContinuityStateValidationError(
            f"Replacement result artifact ref '{repl_res.artifact_ref.ref}' is not in approved control storage domain"
        )
    if repl_res.artifact_ref.ref in ("ai/task-032", "main", state.task_branch.branch, state.main.branch):
        raise ContinuityStateValidationError(
            f"Replacement result artifact ref must not point to task/main branch: '{repl_res.artifact_ref.ref}'"
        )

    # 5. Failover Proof validation & exact input binding (R1-3)
    expected_proof = validate_brain_failover_eligibility(
        source_request=source_req,
        replacement_request=repl_req,
        state=state,
        expected_state_fingerprint=state.fingerprint(),
        replacement_capability=repl_cap,
        source_result=source_res,
    )

    if proof.to_canonical_json() != expected_proof.to_canonical_json():
        if proof.state_fingerprint != expected_proof.state_fingerprint:
            raise ContinuityStateValidationError(
                f"BrainFailoverProof state_fingerprint mismatch: '{proof.state_fingerprint}' vs '{expected_proof.state_fingerprint}'"
            )
        if proof.source_request_fingerprint != expected_proof.source_request_fingerprint:
            raise ContinuityStateValidationError(
                f"BrainFailoverProof source_request_fingerprint mismatch: '{proof.source_request_fingerprint}' vs '{expected_proof.source_request_fingerprint}'"
            )
        if proof.replacement_request_fingerprint != expected_proof.replacement_request_fingerprint:
            raise ContinuityStateValidationError(
                f"BrainFailoverProof replacement_request_fingerprint mismatch: '{proof.replacement_request_fingerprint}' vs '{expected_proof.replacement_request_fingerprint}'"
            )
        if proof.source_brain_id != expected_proof.source_brain_id:
            raise ContinuityStateValidationError(
                f"BrainFailoverProof source_brain_id mismatch: '{proof.source_brain_id}' vs '{expected_proof.source_brain_id}'"
            )
        if proof.replacement_brain_id != expected_proof.replacement_brain_id:
            raise ContinuityStateValidationError(
                f"BrainFailoverProof replacement_brain_id mismatch: '{proof.replacement_brain_id}' vs '{expected_proof.replacement_brain_id}'"
            )
        if proof.task_id != expected_proof.task_id:
            raise ContinuityStateValidationError(
                f"BrainFailoverProof task_id mismatch: '{proof.task_id}' vs '{expected_proof.task_id}'"
            )
        if proof.operation != expected_proof.operation:
            raise ContinuityStateValidationError(
                f"BrainFailoverProof operation mismatch: '{proof.operation.value}' vs '{expected_proof.operation.value}'"
            )
        raise ContinuityStateValidationError("BrainFailoverProof content differs from derived canonical proof")

    # 6. Attestation validation (no transcripts/secrets)
    validate_m8_attestation(attestation)

    return {
        "status": "PASS",
        "state_fingerprint": state.fingerprint(),
        "brain_source_id": source_req.brain_id,
        "brain_replacement_id": repl_req.brain_id,
        "failover_proof_fingerprint": expected_proof.fingerprint(),
        "diagnosis_artifact_path": str(proof_dir / "BRAIN-DIAGNOSIS.md"),
        "diagnosis_artifact_blob_sha": diag_blob_sha,
    }


def verify_composite_chain(
    s0_sha: str,
    review_content: str,
    proof_dir: Path,
    s1_sha: str | None = None,
    s1_result_content: str | None = None,
) -> dict[str, Any]:
    """
    Verifies the complete composite causal chain (AIP-7 / C7 / C8 / C9 / C10):
    Brain proof -> exact REVIEW-032 blob -> Executor failover -> S1.
    """
    # 1. Verify Brain Proof
    brain_summary = verify_brain_proof(proof_dir)

    # 2. Verify REVIEW-032 C7 Provenance Block
    required_review_keys = [
        ("M8_SOURCE_EXECUTOR_PUBLISHED_SHA", s0_sha),
        ("M8_BRAIN_SOURCE_ID", brain_summary["brain_source_id"]),
        ("M8_BRAIN_REPLACEMENT_ID", brain_summary["brain_replacement_id"]),
        ("M8_BRAIN_FAILOVER_PROOF_FINGERPRINT", brain_summary["failover_proof_fingerprint"]),
        ("M8_BRAIN_SUCCESS_ARTIFACT_BLOB_SHA", brain_summary["diagnosis_artifact_blob_sha"]),
        ("M8_CANONICAL_STATE_FINGERPRINT", brain_summary["state_fingerprint"]),
    ]

    for key, expected_val in required_review_keys:
        m = re.search(rf"{key}:\s*([^\s\n]+)", review_content)
        if not m:
            raise ContinuityStateValidationError(f"REVIEW-032 missing required C7 provenance key: '{key}'")
        actual_val = m.group(1).strip()
        if actual_val != expected_val:
            raise ContinuityStateValidationError(
                f"REVIEW-032 provenance mismatch for '{key}': expected '{expected_val}', got '{actual_val}'"
            )

    review_blob_sha = compute_git_blob_sha(normalize_line_endings(review_content))

    # 3. If S1 is provided, verify Executor Failover link
    if s1_sha and s1_result_content:
        req_result_checks = [
            ("EXECUTOR_FAILOVER", "YES"),
            ("FAILOVER_SOURCE_PUBLISHED_SHA", s0_sha),
            ("FAILOVER_REVIEW_BLOB_SHA", review_blob_sha),
            ("M8_BRAIN_PROOF", "PASS"),
            ("M8_EXECUTOR_PROOF", "PASS"),
            ("M8_COMPOSITE_CHAIN", "PASS"),
        ]
        for rk, exp_rv in req_result_checks:
            m = re.search(rf"{rk}:\s*([^\s\n]+)", s1_result_content)
            if not m:
                raise ContinuityStateValidationError(f"S1 RESULT-032 missing required key: '{rk}'")
            act_rv = m.group(1).strip()
            if act_rv != exp_rv:
                raise ContinuityStateValidationError(
                    f"S1 RESULT-032 mismatch for '{rk}': expected '{exp_rv}', got '{act_rv}'"
                )

    return {
        "status": "PASS",
        "s0_sha": s0_sha,
        "s1_sha": s1_sha,
        "review_blob_sha": review_blob_sha,
        "brain_proof_fingerprint": brain_summary["failover_proof_fingerprint"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="M8 Real Multi-Agent Continuity Proof Runner & Verifier")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # prepare-brain
    p_prep = subparsers.add_parser("prepare-brain", help="Prepares S0-bound Brain proof bundle")
    p_prep.add_argument("--task-id", default="TASK-032")
    p_prep.add_argument("--base-main-sha", default="08508e48f6ffda70d1891dad461f6fd1b893b24b")
    p_prep.add_argument("--source-published-sha", default=None)
    p_prep.add_argument("--source-brain-id", default="chatgpt-chat")
    p_prep.add_argument("--replacement-brain-id", default="claude-chat")
    p_prep.add_argument("--output-dir", required=True)

    # verify-brain
    p_vbrain = subparsers.add_parser("verify-brain", help="Verifies Brain failover proof bundle")
    p_vbrain.add_argument("--proof-dir", required=True)

    # verify-composite
    p_vcomp = subparsers.add_parser("verify-composite", help="Verifies composite causal chain")
    p_vcomp.add_argument("--s0", required=True)
    p_vcomp.add_argument("--review-file", required=True)
    p_vcomp.add_argument("--proof-dir", required=True)
    p_vcomp.add_argument("--s1", default=None)
    p_vcomp.add_argument("--s1-result-file", default=None)

    args = parser.parse_args()

    try:
        if args.command == "prepare-brain":
            res = prepare_brain_pack(
                repo_dir=REPO_DIR,
                output_dir=Path(args.output_dir),
                task_id=args.task_id,
                base_main_sha=args.base_main_sha,
                source_published_sha=args.source_published_sha,
                source_brain_id=args.source_brain_id,
                replacement_brain_id=args.replacement_brain_id,
            )
            print(json.dumps(res, indent=2))
            return 0

        elif args.command == "verify-brain":
            res = verify_brain_proof(Path(args.proof_dir))
            print(json.dumps(res, indent=2))
            return 0

        elif args.command == "verify-composite":
            rev_text = Path(args.review_file).read_text(encoding="utf-8")
            s1_res_text = Path(args.s1_result_file).read_text(encoding="utf-8") if args.s1_result_file else None
            res = verify_composite_chain(
                s0_sha=args.s0,
                review_content=rev_text,
                proof_dir=Path(args.proof_dir),
                s1_sha=args.s1,
                s1_result_content=s1_res_text,
            )
            print(json.dumps(res, indent=2))
            return 0

    except Exception as e:
        print(f"[ERROR] M8 Proof validation failed: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
