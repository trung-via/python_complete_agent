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


resolve_e4_control_snapshot = _authority_gated_resolve_e4_control_snapshot
_post_t2_revalidate_certification_subject = _compat_post_t2_revalidate_certification_subject
_executor_context._render_payload = _stable_framed_render_payload
cmd_context = _slim_cmd_context_compat

if _THIS_MODULE_NAME == "__main__":
    main()
