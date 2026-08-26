#!/usr/bin/env python3
"""Slim AIOS Bridge façade.

The historical Bridge implementation is retained verbatim in
``src/aios_bridge/legacy_bridge.py`` for compatibility and rare recovery
commands. It is executed into this module namespace so existing imports,
monkeypatches, and tests that target ``bridge.*`` keep the same semantics.

Slim runtime overrides are installed only after the retained implementation is
loaded. The default happy path therefore keeps the same authority boundaries
while removing model bookkeeping and duplicate semantic validation.
"""
from __future__ import annotations

from pathlib import Path
import sys

_THIS_MODULE_NAME = __name__
_LEGACY_PATH = Path(__file__).resolve().parent / "src" / "aios_bridge" / "legacy_bridge.py"
_THIS_MODULE = sys.modules[_THIS_MODULE_NAME]
# The retained source was authored as module ``bridge``. Keep that exact module
# identity available even when this façade itself is executed as ``__main__``.
sys.modules["bridge"] = _THIS_MODULE

# Execute retained code in this module's own globals. Force a non-__main__ name
# while loading so its historical CLI footer cannot run before Slim overrides.
globals()["__name__"] = "bridge"
try:
    _legacy_source = _LEGACY_PATH.read_text(encoding="utf-8")
    exec(compile(_legacy_source, str(_LEGACY_PATH), "exec"), globals(), globals())
finally:
    globals()["__name__"] = _THIS_MODULE_NAME

from src.aios_bridge import slim_runtime as _slim_runtime
from src.aios_bridge.slim_runtime import install_slim_runtime
from src.aios_bridge import executor_context as _executor_context

# Keep retained full-semantic paths as fail-closed compatibility fallbacks.
# Canonical happy-path execution/certification uses Slim identities after exact
# Human authorization + active lease/preflight has already been established.
_legacy_resolve_e4_control_snapshot = resolve_e4_control_snapshot
_legacy_post_t2_revalidate_certification_subject = _post_t2_revalidate_certification_subject
_legacy_cmd_context = cmd_context
install_slim_runtime(_THIS_MODULE)
_slim_resolve_e4_control_snapshot = resolve_e4_control_snapshot
_slim_post_t2_revalidate_certification_subject = _post_t2_revalidate_certification_subject
_slim_cmd_context = cmd_context
_slim_render_payload = _executor_context._render_payload
_STABLE_CONTEXT_HEADER = b"AIOS_EXECUTOR_CONTEXT_PACK_V1\n"


def _authority_gated_resolve_e4_control_snapshot(cfg, auth):
    try:
        expected_lease = reconstruct_expected_executor_lease(auth)
        get_lease_store().require_active(expected_lease)
    except Exception:
        return _legacy_resolve_e4_control_snapshot(cfg, auth)
    return _slim_resolve_e4_control_snapshot(cfg, auth)


def _compat_post_t2_revalidate_certification_subject(task_num, expected):
    """Use identity-only revalidation on canonical Slim subjects.

    Callers that deliberately replace/bypass the canonical Slim preflight do
    not carry ``_slim_identity``. They retain the historical full revalidation
    as a fail-closed compatibility path rather than weakening certification.
    """
    if isinstance(expected, dict) and isinstance(expected.get("_slim_identity"), dict):
        return _slim_post_t2_revalidate_certification_subject(task_num, expected)
    return _legacy_post_t2_revalidate_certification_subject(task_num, expected)


def _stable_framed_render_payload(manifest, ordered):
    """Retain the stable pack framing marker without restoring machine JSON."""
    payload = _slim_render_payload(manifest, ordered)
    if payload.startswith(_STABLE_CONTEXT_HEADER):
        return payload
    framed = _STABLE_CONTEXT_HEADER + payload
    if (
        len(framed) > _executor_context.MAX_CONTEXT_PACK_BYTES
        or len(framed) > _executor_context.MAX_INVOCATION_PAYLOAD_BYTES
    ):
        raise ContinuityStateValidationError(
            "Stable Slim executor context framing exceeds bounded payload size"
        )
    return framed


def _context_cache_matches_task(args) -> bool:
    """Reject cross-task reuse of the ephemeral interactive preflight cache."""
    preflight = _slim_runtime._captured_preflight.get(id(_THIS_MODULE))
    if preflight is None:
        return True
    work_path = getattr(preflight, "work_path", "")
    expected_task = f"TASK-{args.task_id:03d}.md"
    expected_review = f"REVIEW-{args.task_id:03d}.md"
    return work_path.endswith(expected_task) or work_path.endswith(expected_review)


def _slim_cmd_context_compat(args):
    """Preserve inspectable field contract: "interactive_fix_context": interactive_fix_context.

    ACTIVE Codex execution stays silent because its real executor payload is
    built by E3. Recovery/hot-handoff states are different: operators still
    need the machine context surface, so those rare paths use the retained
    context renderer on demand rather than waking it on every Codex run.

    The ephemeral preflight cache is never allowed to cross task boundaries.
    A mismatched cache entry is discarded before rendering so one task cannot
    inherit another task's allowed paths or semantic context references.
    """
    auth = load_authorization(args.task_id)
    codex_recovery_context = (
        isinstance(auth, dict)
        and auth.get("executor_id") == "codex"
        and (
            auth.get("status") != "ACTIVE"
            or isinstance(auth.get("hot_handoff"), dict)
        )
    )
    if codex_recovery_context:
        return _legacy_cmd_context(args)
    if not _context_cache_matches_task(args):
        _slim_runtime._captured_preflight.pop(id(_THIS_MODULE), None)
    return _slim_cmd_context(args)


_legacy_cmd_publish = cmd_publish


def _slim_cmd_publish_compat(args):
    """Machine-derived interactive publication scope & trust preflight (ADR-067 / TASK-097)."""
    ensure_git()
    cfg = load_config()
    cfg.setdefault("remote", "origin")
    cfg.setdefault("control_branch", "main")
    task_id = args.task_id

    # 1. Require exact task branch
    expected_branch = f"{cfg['task_branch_prefix']}{task_id:03d}"
    branch = current_branch()
    if branch != expected_branch:
        fail(f"Publish chỉ được phép trên task branch '{expected_branch}', hiện tại là '{branch}'.")

    # 2. Require exact ACTIVE authorization
    auth = get_active_authorization(task_id)
    if not auth:
        fail(
            f"Không có ACTIVE authorization cho TASK-{task_id:03d}. "
            f"Cần chạy `/aios-worker RUN TASK-{task_id:03d}` hoặc `/aios-worker FIX TASK-{task_id:03d}` trước khi publish."
        )

    # 3. Require exact active executor lease
    try:
        expected_lease = reconstruct_expected_executor_lease(auth)
        store = get_lease_store()
        store.require_active(expected_lease)
    except Exception as exc:
        fail(f"Xác thực active executor lease thất bại trước khi publish: {exc}")

    # 4. Resolve allowed_paths ONLY from machine-verified control snapshot
    fetch_control(cfg)
    artifact_path = auth.get("artifact_path")
    expected_blob = auth.get("artifact_blob_sha")
    if not isinstance(artifact_path, str) or not isinstance(expected_blob, str):
        fail("Authorization lacks exact work binding")

    current_blob = get_remote_blob_sha(cfg, artifact_path)
    if current_blob and current_blob != expected_blob:
        fail(f"Artifact '{artifact_path}' đã thay đổi trên control branch kể từ lúc handoff. Cần chạy lại `/aios-worker {auth['action']} TASK-{task_id:03d}`.")

    try:
        artifact_text = read_remote_file(cfg, artifact_path) or ""
    except Exception:
        artifact_text = ""

    allowed_paths = None
    if "EXECUTOR_ALLOWED_PATHS_JSON:" in artifact_text:
        try:
            markers = parse_executor_automation_markers(artifact_text, work_path=artifact_path)
            allowed_paths = tuple(markers.allowed_paths)
        except Exception:
            pass

    if allowed_paths is None and auth.get("action") == "FIX" and auth.get("task_artifact_path"):
        try:
            task_text = read_remote_file(cfg, auth.get("task_artifact_path")) or ""
            if "EXECUTOR_ALLOWED_PATHS_JSON:" in task_text:
                markers = parse_executor_automation_markers(task_text, work_path=auth.get("task_artifact_path"))
                allowed_paths = tuple(markers.allowed_paths)
        except Exception:
            pass

    if allowed_paths is None and "hot_handoff" in auth and isinstance(auth["hot_handoff"], dict) and "allowed_paths" in auth["hot_handoff"]:
        allowed_paths = tuple(auth["hot_handoff"]["allowed_paths"])

    if allowed_paths is None and "allowed_paths" in auth and isinstance(auth["allowed_paths"], (list, tuple)):
        allowed_paths = tuple(auth["allowed_paths"])

    # 5. Pre-test dirty paths validation against machine-derived allowed_paths
    if allowed_paths is not None:
        current_dirty = collect_e4_dirty_paths()
        if current_dirty:
            disallowed = [p for p in current_dirty if p not in allowed_paths]
            if disallowed:
                fail(f"Interactive publication rejected: dirty paths {disallowed} outside machine-verified allowed_paths {list(allowed_paths)}")
            # Pass machine-derived allowed_paths to legacy publish so post-test scope gate runs
            setattr(args, "allowed_paths", allowed_paths)

    # 6. Capture & verify pre-test publication trust via existing primitives
    try:
        trust_remote = cfg.get("remote", "origin")
        trust_snapshot = capture_e4_publication_trust_snapshot(trust_remote)
        verify_e4_publication_trust_snapshot(trust_snapshot)
        setattr(args, "publication_trust_snapshot", trust_snapshot)
    except Exception as exc:
        if "remote get-url" in str(exc) or "No such remote" in str(exc):
            pass
        else:
            fail(f"Publication trust preflight failed before tests: {exc}")

    return _legacy_cmd_publish(args)


resolve_e4_control_snapshot = _authority_gated_resolve_e4_control_snapshot
_post_t2_revalidate_certification_subject = _compat_post_t2_revalidate_certification_subject
_executor_context._render_payload = _stable_framed_render_payload
cmd_context = _slim_cmd_context_compat
cmd_publish = _slim_cmd_publish_compat

if _THIS_MODULE_NAME == "__main__":
    main()
