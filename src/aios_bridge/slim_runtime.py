"""Slim AIOS R0 compatibility overrides.

No new authority, store, registry, graph, or state machine is introduced here.
The retained Bridge remains the authority implementation. These overrides only
remove duplicated semantic work and machine bookkeeping from the default path.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from src.aios_bridge.continuity.errors import ContinuityStateValidationError
from src.aios_bridge.continuity.executor import ExecutionOperation
from src.aios_bridge.continuity.state import ArtifactRef

_MACHINE_ONLY_PREFIXES = (".ai/roadmaps/",)
_installed: set[int] = set()
_captured_preflight: dict[int, Any] = {}


def _is_machine_only(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _MACHINE_ONLY_PREFIXES)


def _render_semantic_payload(ec: Any, manifest: Any, ordered: Any) -> bytes:
    """Keep machine provenance in the manifest, out of model-visible bytes."""
    parts: list[bytes] = [
        ec._FIXED_INSTRUCTION_BLOCK.encode("utf-8"),
        (
            "\n\nSLIM AIOS SEMANTIC CONTEXT\n"
            f"TASK_ID: {manifest.task_id}\n"
            f"ACTION: {manifest.operation.value}\n"
            f"TARGET_BRANCH: {manifest.target_branch}\n"
            "PROVENANCE: MACHINE_VERIFIED_OUT_OF_BAND\n\n"
        ).encode("utf-8"),
    ]
    for entry, content in ordered:
        if entry.role.value != "WORK" and _is_machine_only(entry.path):
            parts.append(
                f"MACHINE_CONTEXT_OMITTED_FROM_MODEL: {entry.path}\n".encode("utf-8")
            )
            continue
        parts.extend(
            [
                (
                    f"ARTIFACT {entry.ordinal} BEGIN\n"
                    f"ROLE: {entry.role.value}\n"
                    f"PATH: {entry.path}\n"
                    "CONTENT_BEGIN\n"
                ).encode("utf-8"),
                content,
                f"\nCONTENT_END\nARTIFACT {entry.ordinal} END\n\n".encode("utf-8"),
            ]
        )
    parts.append(b"AIOS_EXECUTOR_CONTEXT_PACK_END\n")
    payload = b"".join(parts)
    payload.decode("utf-8")
    if not payload or len(payload) > ec.MAX_CONTEXT_PACK_BYTES:
        raise ContinuityStateValidationError("Slim executor context exceeds E3 bounds")
    from src.aios_bridge.continuity.executor_transport import MAX_INVOCATION_PAYLOAD_BYTES
    if len(payload) > MAX_INVOCATION_PAYLOAD_BYTES:
        raise ContinuityStateValidationError("Slim executor context exceeds transport bounds")
    return payload


def _identity_snapshot(
    bridge: Any, cfg: dict[str, Any], auth: dict[str, Any]
) -> dict[str, Any]:
    """Revalidate authority identities without rerunning full semantic preflight.

    Handoff remains the single semantic authoring/roadmap/milestone preflight.
    Execute reparses only small machine markers from the exact authorized Git
    artifact so local runtime state can never widen scope or executor policy.
    """
    bridge.fetch_control(cfg)
    control_sha = bridge.resolve_control_commit_sha(cfg)

    work_path = auth.get("artifact_path")
    expected_work_blob = auth.get("artifact_blob_sha")
    if not isinstance(work_path, str) or not isinstance(expected_work_blob, str):
        raise ContinuityStateValidationError("Authorization lacks exact work binding")
    work_blob = bridge.resolve_git_blob_sha(control_sha, work_path)
    if work_blob != expected_work_blob:
        raise ContinuityStateValidationError("Authorized work artifact drifted")
    work_bytes = bridge.read_git_blob_bytes(control_sha, work_path)
    try:
        work_text = work_bytes.decode("utf-8")
        operation = ExecutionOperation(auth.get("action"))
    except (UnicodeDecodeError, TypeError, ValueError) as exc:
        raise ContinuityStateValidationError(
            "Authorized work artifact/action is not canonical"
        ) from exc

    # Cheap machine marker parse only: no publisher prose scan, no milestone
    # completion logic, no full canonical roadmap parse.
    markers = bridge.parse_executor_automation_markers(
        work_text, work_path=work_path
    )
    policy = bridge.parse_executor_dispatch_policy_marker(work_text)
    if policy.operation is not operation:
        raise ContinuityStateValidationError("Dispatch policy operation drifted")
    matches = [
        item for item in policy.candidates if item.executor_id == auth.get("executor_id")
    ]
    if len(matches) != 1:
        raise ContinuityStateValidationError(
            "Human-selected executor is no longer an exact policy candidate"
        )
    candidate = matches[0]
    if operation not in candidate.supported_operations:
        raise ContinuityStateValidationError(
            "Human-selected executor no longer supports authorized operation"
        )
    missing = [
        cap for cap in policy.required_capabilities
        if cap not in candidate.supported_capabilities
    ]
    if missing:
        raise ContinuityStateValidationError(
            "Human-selected executor no longer satisfies required capabilities"
        )

    refs: list[ArtifactRef] = []
    payloads: dict[str, bytes] = {work_path: work_bytes}
    for spec in markers.context_refs:
        observed = bridge.resolve_git_blob_sha(control_sha, spec.path)
        if observed != spec.blob_sha:
            raise ContinuityStateValidationError(
                f"Executor context drifted: {spec.path}"
            )
        refs.append(ArtifactRef(path=spec.path, ref=control_sha, blob_sha=observed))
        payloads[spec.path] = bridge.read_git_blob_bytes(control_sha, spec.path)

    # Roadmap identity stays machine-enforced, but its prose/milestones are not
    # interpreted a second time. For FIX, governance belongs to the canonical
    # TASK rather than the REVIEW authority artifact.
    governance_text = work_text
    if operation is ExecutionOperation.FIX:
        import re

        match = re.fullmatch(r"\.ai/reviews/REVIEW-([0-9]+)\.md", work_path)
        if match is None:
            raise ContinuityStateValidationError(
                "FIX review path cannot resolve canonical TASK identity"
            )
        task_path = f".ai/tasks/TASK-{int(match.group(1)):03d}.md"
        task_bytes = bridge.read_git_blob_bytes(control_sha, task_path)
        try:
            governance_text = task_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ContinuityStateValidationError(
                "Canonical TASK must be strict UTF-8"
            ) from exc
        if any(ref.path == task_path for ref in refs):
            payloads[task_path] = task_bytes

    governed = (
        bridge.task_requires_roadmap_governance(governance_text)
        or "ROADMAP_BINDING_JSON:" in governance_text
    )
    if governed:
        binding = bridge.parse_roadmap_task_binding(governance_text)
        registry = bridge.resolve_canonical_roadmap_registry(control_sha)
        registration = registry.get((binding.roadmap_id, binding.roadmap_version))
        if registration is None:
            raise ContinuityStateValidationError(
                "Task-bound canonical roadmap is no longer registered"
            )
        if registration.roadmap_blob_sha != binding.roadmap_blob_sha:
            raise ContinuityStateValidationError(
                "Task-bound canonical roadmap blob drifted"
            )
        exact = bridge.resolve_exact_roadmap_bytes(
            control_sha, registration.artifact_path, registration.roadmap_blob_sha
        )
        if hashlib.sha256(exact).hexdigest() != binding.roadmap_fingerprint:
            raise ContinuityStateValidationError(
                "Task-bound canonical roadmap fingerprint drifted"
            )
        roadmap_refs = [
            ref for ref in refs
            if ref.path == registration.artifact_path
            and ref.blob_sha == registration.roadmap_blob_sha
        ]
        if len(roadmap_refs) != 1:
            raise ContinuityStateValidationError(
                "Canonical roadmap context identity is missing or duplicated"
            )

    return {
        "control_commit_sha": control_sha,
        "work_ref": ArtifactRef(path=work_path, ref=control_sha, blob_sha=work_blob),
        "context_refs": tuple(refs),
        "allowed_paths": markers.allowed_paths,
        "policy": policy,
        "candidate": candidate,
        "artifact_payloads": payloads,
    }


def _interactive_context(bridge: Any, args: Any) -> None:
    """Small semantic-only interactive context for authorized sessions."""
    auth = bridge.load_authorization(args.task_id)

    preflight = _captured_preflight.get(id(bridge))
    allowed = list(preflight.markers.allowed_paths) if preflight is not None else []
    semantic_refs = (
        [
            ref.path
            for ref in preflight.markers.context_refs
            if not _is_machine_only(ref.path)
        ]
        if preflight is not None
        else []
    )
    action = auth.get("action") if isinstance(auth, dict) else None
    n = args.task_id
    print(
        json.dumps(
            {
                "task_id": f"TASK-{n:03d}",
                "action": action,
                "executor_id": auth.get("executor_id") if isinstance(auth, dict) else None,
                "current_branch": bridge.current_branch(),
                "expected_branch": auth.get("branch") if isinstance(auth, dict) else None,
                "task_file": str(bridge.get_artifact_path(f".ai/tasks/TASK-{n:03d}.md")),
                "review_file": (
                    str(bridge.get_artifact_path(f".ai/reviews/REVIEW-{n:03d}.md"))
                    if action == "FIX"
                    else None
                ),
                "allowed_paths": allowed,
                "semantic_context_files": semantic_refs,
                "interactive_fix_context": (
                    bridge._interactive_fix_context_for_auth(auth)
                    if hasattr(bridge, "_interactive_fix_context_for_auth")
                    else None
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _cert_identity(bridge: Any, task_num: int, context: dict[str, Any]) -> dict[str, Any]:
    """Capture identities after the one full pre-T2 semantic preflight."""
    cfg = bridge.load_config()
    remote = str(cfg.get("remote", "origin") or "origin")
    base = str(cfg.get("base_branch", "main") or "main")
    prefix = str(cfg.get("task_branch_prefix", "ai/task-") or "ai/task-")
    control_sha = bridge.resolve_control_commit_sha(cfg)
    task_path = f".ai/tasks/TASK-{task_num:03d}.md"
    review_path = f".ai/reviews/REVIEW-{task_num:03d}.md"
    task_text = bridge.read_git_blob_bytes(control_sha, task_path).decode("utf-8")
    binding = bridge.parse_roadmap_task_binding(task_text)
    registry = bridge.resolve_canonical_roadmap_registry(control_sha)
    registration = registry[(binding.roadmap_id, binding.roadmap_version)]
    task_branch = f"{prefix}{task_num:03d}"
    return {
        "remote": remote,
        "base": base,
        "task_branch": task_branch,
        "task_path": task_path,
        "review_path": review_path,
        "task_blob": bridge.resolve_git_blob_sha(control_sha, task_path),
        "review_blob": bridge.resolve_git_blob_sha(control_sha, review_path),
        "main_sha": bridge.git(
            "rev-parse", f"refs/remotes/{remote}/{base}", check=False
        ).stdout.strip().lower(),
        "task_sha": bridge.git(
            "rev-parse", f"refs/remotes/{remote}/{task_branch}", check=False
        ).stdout.strip().lower(),
        "roadmap_id": binding.roadmap_id,
        "roadmap_version": binding.roadmap_version,
        "roadmap_path": registration.artifact_path,
        "roadmap_blob": registration.roadmap_blob_sha,
        "roadmap_fingerprint": binding.roadmap_fingerprint,
        "command_identity": context["command_identity"],
    }


def _post_t2_identity_only(bridge: Any, task_num: int, expected: dict[str, Any]) -> None:
    """Replace the second full semantic preflight with exact identity checks."""
    identity = expected.get("_slim_identity")
    if not isinstance(identity, dict):
        raise ContinuityStateValidationError("Missing Slim T2 identity evidence")

    cfg = bridge.load_config()
    remote, base, task_branch = identity["remote"], identity["base"], identity["task_branch"]
    control_branch = str(cfg.get("control_branch", "ai-control") or "ai-control")
    fetched = bridge.git(
        "fetch", remote, control_branch, base, task_branch, check=False
    )
    if fetched.returncode != 0:
        raise ContinuityStateValidationError(
            "Unable to refresh certification identities after T2"
        )
    control_sha = bridge.resolve_control_commit_sha(cfg)
    if bridge.resolve_git_blob_sha(control_sha, identity["task_path"]) != identity["task_blob"]:
        raise ContinuityStateValidationError("Task changed while T2 was running")
    if bridge.resolve_git_blob_sha(control_sha, identity["review_path"]) != identity["review_blob"]:
        raise ContinuityStateValidationError("Review changed while T2 was running")

    main_sha = bridge.git(
        "rev-parse", f"refs/remotes/{remote}/{base}", check=False
    ).stdout.strip().lower()
    task_sha = bridge.git(
        "rev-parse", f"refs/remotes/{remote}/{task_branch}", check=False
    ).stdout.strip().lower()
    if main_sha != identity["main_sha"] or task_sha != identity["task_sha"]:
        raise ContinuityStateValidationError("Certification Git subject drifted")
    if (
        bridge.current_branch() != task_branch
        or bridge.observe_e4_head() != task_sha
        or not bridge.is_worktree_clean()
    ):
        raise ContinuityStateValidationError("Certification local subject drifted")

    registry = bridge.resolve_canonical_roadmap_registry(control_sha)
    registration = registry.get((identity["roadmap_id"], identity["roadmap_version"]))
    if (
        registration is None
        or registration.artifact_path != identity["roadmap_path"]
        or registration.roadmap_blob_sha != identity["roadmap_blob"]
    ):
        raise ContinuityStateValidationError("Certification roadmap registration drifted")
    exact = bridge.resolve_exact_roadmap_bytes(
        control_sha, identity["roadmap_path"], identity["roadmap_blob"]
    )
    if hashlib.sha256(exact).hexdigest() != identity["roadmap_fingerprint"]:
        raise ContinuityStateValidationError("Certification roadmap fingerprint drifted")
    if (
        bridge.build_certification_command_identity(expected["command"])
        != identity["command_identity"]
    ):
        raise ContinuityStateValidationError("Certification command identity drifted")


def install_slim_runtime(bridge: Any) -> None:
    """Install subtractive overrides once into the canonical bridge namespace."""
    key = id(bridge)
    if key in _installed:
        return
    _installed.add(key)

    import src.aios_bridge.executor_context as ec

    original_handoff = bridge.cmd_handoff
    original_execute = bridge.cmd_execute
    original_preflight = bridge.preflight_executable_artifact
    original_cert_preflight = bridge._preflight_certify_reviewed

    def capture_preflight(*args: Any, **kwargs: Any) -> Any:
        result = original_preflight(*args, **kwargs)
        _captured_preflight[key] = result
        return result

    def slim_handoff(args: Any) -> None:
        _captured_preflight.pop(key, None)
        original_handoff(args)

    def cert_preflight_once(task_num: int) -> dict[str, Any]:
        context = dict(original_cert_preflight(task_num))
        context["_slim_identity"] = _cert_identity(bridge, task_num, context)
        return context

    bridge.preflight_executable_artifact = capture_preflight
    bridge.cmd_handoff = slim_handoff
    bridge.cmd_context = lambda args: _interactive_context(bridge, args)
    bridge.resolve_e4_control_snapshot = lambda cfg, auth: _identity_snapshot(
        bridge, cfg, auth
    )
    bridge.cmd_execute = original_execute
    bridge._preflight_certify_reviewed = cert_preflight_once
    bridge._post_t2_revalidate_certification_subject = (
        lambda task_num, expected: _post_t2_identity_only(bridge, task_num, expected)
    )
    ec._render_payload = lambda manifest, ordered: _render_semantic_payload(
        ec, manifest, ordered
    )


__all__ = ["install_slim_runtime"]
