from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import src.product_intelligence.live_capture as live_capture_module
from src.core.errors import AgentException
from src.core.types import ToolResult, ToolStatus
from src.browser.errors import BrowserContextError, PageClosedError
from src.browser.models import BrowserState
from src.product_intelligence.discovery import DiscoveryBlockedError
from src.product_intelligence.live_capture import (
    LiveCaptureError,
    LiveCapturePhase,
    LiveCaptureStatus,
    run_live_capture,
)


class _Manager:
    instances = []
    binding_digest = "a" * 64
    binding_error = None
    evaluate_error = None
    session_state = BrowserState.READY

    def __init__(self, cdp_endpoint):
        self.cdp_endpoint = cdp_endpoint
        self.close_count = 0
        self.session = _Session(
            type(self).binding_digest,
            binding_error=type(self).binding_error,
            evaluate_error=type(self).evaluate_error,
            state=type(self).session_state,
        )
        type(self).instances.append(self)

    async def get_or_create_session(self, run_id):
        del run_id
        return self.session

    async def close_all(self):
        self.close_count += 1


class _Session:
    def __init__(self, binding_digest, *, binding_error=None, evaluate_error=None, state=None):
        self.state = state or BrowserState.READY
        self.binding_digest = binding_digest
        self.binding_error = binding_error
        self.evaluate_error = evaluate_error
        self.binding_calls = 0
        self.evaluate_calls = []
        self.navigated_urls = []

    async def browser_binding_digest(self):
        self.binding_calls += 1
        if self.binding_error:
            raise self.binding_error
        return self.binding_digest

    async def evaluate(self, script, arg=None):
        self.evaluate_calls.append(script)
        if self.evaluate_error:
            raise self.evaluate_error
        return True

    async def navigate(self, url):
        self.navigated_urls.append(url)
        return None


class _Tool:
    instances = []
    block_at = None
    fail_at = None
    calls = []
    contexts = []

    def __init__(self):
        type(self).instances.append(self)

    async def execute(self, call, context):
        type(self).calls.append((call.call_id, call.arguments["url"]))
        type(self).contexts.append(context)
        call_number = len(type(self).calls)
        if call_number == type(self).block_at:
            return ToolResult(
                call_id=call.call_id,
                run_id=call.run_id,
                tool_name="shopee_scrape",
                status=ToolStatus.FAILURE,
                error=AgentException("blocked", code="EXTRACTION_BLOCKED"),
            )
        if call_number == type(self).fail_at:
            return ToolResult(
                call_id=call.call_id,
                run_id=call.run_id,
                tool_name="shopee_scrape",
                status=ToolStatus.FAILURE,
                error=AgentException("empty", code="EXTRACTION_EMPTY"),
            )
        manifest = Path(context["output_dir"]) / "shopee" / f"pack-{call.call_id}" / "source_pack.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_bytes((f'{{"call_id":"{call.call_id}"}}\n').encode())
        return ToolResult(
            call_id=call.call_id,
            run_id=call.run_id,
            tool_name="shopee_scrape",
            status=ToolStatus.SUCCESS,
            data={"manifest_path": str(manifest)},
        )


@pytest.fixture(autouse=True)
def _reset_fakes():
    _Manager.instances = []
    _Manager.binding_digest = "a" * 64
    _Manager.binding_error = None
    _Manager.evaluate_error = None
    _Manager.session_state = BrowserState.READY
    _Tool.instances = []
    _Tool.calls = []
    _Tool.contexts = []
    _Tool.block_at = None
    _Tool.fail_at = None


def _orchestration(queries_seen, *, blocked_query=None):
    async def run(plans, **kwargs):
        del kwargs
        request = plans[0].request
        queries_seen.append(request.query)
        assert request.max_pages == 1
        assert request.max_candidates == 20
        if request.query == blocked_query:
            raise DiscoveryBlockedError("challenge")
        candidate = SimpleNamespace(
            candidate_id=f"candidate-{request.query}",
            url=f"https://shopee.test/{request.query}",
            title=f"title {request.query}",
        )
        return SimpleNamespace(shortlist=(SimpleNamespace(candidate=candidate),))

    return run


def _run(root, queries, orchestration):
    return run_live_capture(
        job_root=root,
        cdp_endpoint="http://127.0.0.1:9222",
        queries=queries,
        manager_factory=_Manager,
        tool_factory=_Tool,
        orchestration=orchestration,
    )


def test_ordered_capture_preserves_manifest_bytes_and_creates_immutable_bundle(tmp_path):
    root = tmp_path / "capture"
    seen = []
    import asyncio
    outcome = asyncio.run(_run(root, [" query A ", "query B"], _orchestration(seen)))

    assert outcome.status is LiveCaptureStatus.READY
    assert outcome.phase is LiveCapturePhase.COMPLETE
    assert seen == [" query A ", "query B"]
    assert len(_Manager.instances) == len(_Tool.instances) == 1
    assert _Manager.instances[0].close_count == 1
    assert [item[0] for item in _Tool.calls] == [
        "live-capture-q0001-o0001", "live-capture-q0001-o0002",
        "live-capture-q0002-o0001", "live-capture-q0002-o0002",
    ]
    bundle_path = root / "capture_bundle.json"
    before = bundle_path.read_bytes()
    checkpoint_before = (root / "capture_checkpoint.json").read_bytes()
    checkpoint_document = json.loads(checkpoint_before)
    assert checkpoint_document["version"] == 2
    assert "cdp_endpoint" not in checkpoint_document
    assert checkpoint_document["endpoint_digest"] == hashlib.sha256(
        b"http://127.0.0.1:9222"
    ).hexdigest()
    assert checkpoint_document["browser_binding_digest"] == "a" * 64
    bundle = json.loads(before)
    assert bundle["schema"] == "product_intelligence_live_capture_bundle"
    assert [cohort["query"] for cohort in bundle["cohorts"]] == [" query A ", "query B"]
    for cohort in bundle["cohorts"]:
        assert len(cohort["observations"]) == 2
        for reference in cohort["observations"]:
            manifest = root / reference["manifest_path"]
            assert hashlib.sha256(manifest.read_bytes()).hexdigest() == reference["sha256"]
    with pytest.raises(LiveCaptureError):
        asyncio.run(run_live_capture(
            job_root=root,
            cdp_endpoint="http://127.0.0.1:9222",
            queries=None,
            resume=True,
            manager_factory=_Manager,
            tool_factory=_Tool,
            orchestration=_orchestration([]),
        ))
    assert bundle_path.read_bytes() == before
    assert (root / "capture_checkpoint.json").read_bytes() == checkpoint_before


def test_fresh_checkpoint_starts_new_then_session_ready_then_running(
    tmp_path, monkeypatch
):
    import asyncio

    statuses = []
    original = live_capture_module._atomic_checkpoint

    def trace(root, state):
        statuses.append(state["status"])
        original(root, state)

    monkeypatch.setattr(live_capture_module, "_atomic_checkpoint", trace)
    outcome = asyncio.run(_run(
        tmp_path / "capture", ["query"], _orchestration([])
    ))

    assert outcome.status is LiveCaptureStatus.READY
    assert statuses[:3] == ["NEW", "SESSION_READY", "RUNNING"]


@pytest.mark.parametrize("block_call,expected_phase,completed_calls", [
    (1, "ACQUIRE_1", 0),
    (2, "ACQUIRE_2", 1),
])
def test_acquisition_challenge_resume_continues_only_unfinished_phase(
    tmp_path, block_call, expected_phase, completed_calls
):
    import asyncio
    root = tmp_path / "capture"
    seen = []
    _Tool.block_at = block_call
    first = asyncio.run(_run(root, ["query"], _orchestration(seen)))
    checkpoint = json.loads((root / "capture_checkpoint.json").read_text(encoding="utf-8"))
    assert first.status is LiveCaptureStatus.HUMAN_ACTION_REQUIRED
    assert checkpoint["phase"] == expected_phase
    assert len(checkpoint["completed_observations"]) == completed_calls
    assert seen == ["query"]

    prior_calls = list(_Tool.calls)
    _Tool.block_at = None
    resumed = asyncio.run(run_live_capture(
        job_root=root,
        cdp_endpoint="http://127.0.0.1:9222",
        resume=True,
        manager_factory=_Manager,
        tool_factory=_Tool,
        orchestration=_orchestration(seen),
    ))
    assert resumed.status is LiveCaptureStatus.READY
    assert seen == ["query"]
    if expected_phase == "ACQUIRE_2":
        assert _Tool.calls.count(prior_calls[0]) == 1
    assert all(manager.close_count == 1 for manager in _Manager.instances)


def test_discovery_challenge_repeats_stably_without_wait_or_acquisition(tmp_path):
    import asyncio
    root = tmp_path / "capture"
    seen = []
    first = asyncio.run(_run(root, ["query"], _orchestration(seen, blocked_query="query")))
    assert first.status is LiveCaptureStatus.HUMAN_ACTION_REQUIRED
    first_bytes = (root / "capture_checkpoint.json").read_bytes()
    second = asyncio.run(run_live_capture(
        job_root=root,
        cdp_endpoint="http://127.0.0.1:9222",
        resume=True,
        manager_factory=_Manager,
        tool_factory=_Tool,
        orchestration=_orchestration(seen, blocked_query="query"),
    ))
    assert second.status is LiveCaptureStatus.HUMAN_ACTION_REQUIRED
    assert _Tool.calls == []
    assert seen == ["query", "query"]
    assert json.loads(first_bytes) == json.loads((root / "capture_checkpoint.json").read_bytes())


def test_endpoint_mismatch_becomes_session_lost_before_browser_work(tmp_path):
    import asyncio
    root = tmp_path / "capture"
    asyncio.run(_run(root, ["query"], _orchestration([], blocked_query="query")))
    manager_count = len(_Manager.instances)
    outcome = asyncio.run(run_live_capture(
        job_root=root,
        cdp_endpoint="http://127.0.0.1:9333",
        resume=True,
        manager_factory=_Manager,
        tool_factory=_Tool,
        orchestration=_orchestration([]),
    ))
    assert outcome.status is LiveCaptureStatus.SESSION_LOST
    assert len(_Manager.instances) == manager_count
    checkpoint = json.loads((root / "capture_checkpoint.json").read_bytes())
    assert checkpoint["status"] == "SESSION_LOST"
    assert "cdp_endpoint" not in checkpoint


def test_binding_mismatch_stops_before_unfinished_operation_and_explicit_rebind_continues(
    tmp_path,
):
    import asyncio

    root = tmp_path / "capture"
    seen = []
    first = asyncio.run(_run(root, ["query"], _orchestration(seen, blocked_query="query")))
    assert first.status is LiveCaptureStatus.HUMAN_ACTION_REQUIRED
    _Manager.binding_digest = "b" * 64

    lost = asyncio.run(run_live_capture(
        job_root=root,
        cdp_endpoint="http://127.0.0.1:9222",
        resume=True,
        manager_factory=_Manager,
        tool_factory=_Tool,
        orchestration=_orchestration(seen),
    ))
    assert lost.status is LiveCaptureStatus.SESSION_LOST
    assert seen == ["query"]
    assert _Tool.calls == []

    resumed = asyncio.run(run_live_capture(
        job_root=root,
        cdp_endpoint="http://127.0.0.1:9333",
        resume=True,
        rebind_session=True,
        manager_factory=_Manager,
        tool_factory=_Tool,
        orchestration=_orchestration(seen),
    ))
    assert resumed.status is LiveCaptureStatus.READY
    assert seen == ["query", "query"]
    checkpoint = json.loads((root / "capture_checkpoint.json").read_bytes())
    assert "cdp_endpoint" not in checkpoint
    assert checkpoint["endpoint_digest"] == hashlib.sha256(
        b"http://127.0.0.1:9333"
    ).hexdigest()
    assert checkpoint["browser_binding_digest"] == "b" * 64


def test_resume_verifies_once_before_exact_unfinished_phase(tmp_path, monkeypatch):
    import asyncio

    root = tmp_path / "capture"
    _Tool.block_at = 2
    asyncio.run(_run(root, ["query"], _orchestration([])))
    prior_calls = list(_Tool.calls)
    _Tool.block_at = None
    statuses = []
    original = live_capture_module._atomic_checkpoint

    def trace(checkpoint_root, state):
        statuses.append(state["status"])
        original(checkpoint_root, state)

    monkeypatch.setattr(live_capture_module, "_atomic_checkpoint", trace)
    outcome = asyncio.run(run_live_capture(
        job_root=root,
        cdp_endpoint="http://127.0.0.1:9222",
        resume=True,
        manager_factory=_Manager,
        tool_factory=_Tool,
        orchestration=_orchestration([]),
    ))

    assert outcome.status is LiveCaptureStatus.READY
    resume_session = _Manager.instances[-1].session
    assert resume_session.evaluate_calls == ["() => true"]
    assert statuses[:3] == ["VERIFY_SESSION", "SESSION_READY", "RUNNING"]
    assert _Tool.calls.count(prior_calls[0]) == 1


def test_resource_loss_is_resumable_but_ordinary_probe_failure_is_terminal(tmp_path):
    import asyncio

    lost_root = tmp_path / "lost"
    asyncio.run(_run(lost_root, ["query"], _orchestration([], blocked_query="query")))
    _Manager.evaluate_error = PageClosedError()
    _Manager.session_state = BrowserState.CRASHED
    lost = asyncio.run(run_live_capture(
        job_root=lost_root,
        cdp_endpoint="http://127.0.0.1:9222",
        resume=True,
        manager_factory=_Manager,
        tool_factory=_Tool,
        orchestration=_orchestration([]),
    ))
    assert lost.status is LiveCaptureStatus.SESSION_LOST

    failed_root = tmp_path / "failed"
    _Manager.evaluate_error = None
    _Manager.session_state = BrowserState.READY
    asyncio.run(_run(failed_root, ["query"], _orchestration([], blocked_query="query")))
    _Manager.evaluate_error = BrowserContextError("ordinary probe failure")
    with pytest.raises(LiveCaptureError, match="Live capture failed"):
        asyncio.run(run_live_capture(
            job_root=failed_root,
            cdp_endpoint="http://127.0.0.1:9222",
            resume=True,
            manager_factory=_Manager,
            tool_factory=_Tool,
            orchestration=_orchestration([]),
        ))
    assert json.loads((failed_root / "capture_checkpoint.json").read_bytes())["status"] == "FAILED"


def test_valid_v1_challenge_upgrade_removes_raw_endpoint(tmp_path):
    import asyncio

    root = tmp_path / "capture"
    endpoint = "http://127.0.0.1:9222/private"
    asyncio.run(run_live_capture(
        job_root=root,
        cdp_endpoint=endpoint,
        queries=["query"],
        manager_factory=_Manager,
        tool_factory=_Tool,
        orchestration=_orchestration([], blocked_query="query"),
    ))
    checkpoint_path = root / "capture_checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_bytes())
    checkpoint["version"] = 1
    checkpoint["status"] = "CHALLENGE_REQUIRED"
    checkpoint["cdp_endpoint"] = endpoint
    del checkpoint["endpoint_digest"]
    del checkpoint["browser_binding_digest"]
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")

    outcome = asyncio.run(run_live_capture(
        job_root=root,
        cdp_endpoint=endpoint,
        resume=True,
        manager_factory=_Manager,
        tool_factory=_Tool,
        orchestration=_orchestration([]),
    ))
    assert outcome.status is LiveCaptureStatus.READY
    upgraded = json.loads(checkpoint_path.read_bytes())
    assert upgraded["version"] == 2
    assert "cdp_endpoint" not in upgraded
    assert endpoint not in checkpoint_path.read_text(encoding="utf-8")


def test_non_challenge_tool_failure_is_terminal_and_not_resumable(tmp_path):
    import asyncio
    root = tmp_path / "capture"
    _Tool.fail_at = 1
    with pytest.raises(LiveCaptureError):
        asyncio.run(_run(root, ["query"], _orchestration([])))
    assert json.loads((root / "capture_checkpoint.json").read_bytes())["status"] == "FAILED"
    with pytest.raises(LiveCaptureError):
        asyncio.run(run_live_capture(
            job_root=root,
            cdp_endpoint="http://127.0.0.1:9222",
            resume=True,
            manager_factory=_Manager,
            tool_factory=_Tool,
            orchestration=_orchestration([]),
        ))


def test_repository_local_root_rejected_before_browser_work():
    import asyncio
    repository_root = Path(__file__).resolve().parents[2]
    with pytest.raises(LiveCaptureError):
        asyncio.run(_run(repository_root / "forbidden-capture", ["query"], _orchestration([])))
    assert _Manager.instances == []


def test_initial_checkpoint_replace_failure_is_bounded_and_cleans_staging(
    tmp_path, monkeypatch
):
    import asyncio

    root = tmp_path / "capture-secret-root"
    leaked = f"permission denied: {root.resolve()}"

    def fail_replace(source, destination):
        del source, destination
        raise PermissionError(leaked)

    monkeypatch.setattr(live_capture_module.os, "replace", fail_replace)
    with pytest.raises(LiveCaptureError) as exc_info:
        asyncio.run(_run(root, ["query"], _orchestration([])))

    assert str(exc_info.value) == "Capture checkpoint could not be updated"
    assert str(root.resolve()) not in str(exc_info.value)
    assert not (root / ".capture_checkpoint.json.tmp").exists()
    assert not (root / "capture_checkpoint.json").exists()
    assert _Manager.instances == []


def test_initial_checkpoint_open_failure_is_bounded_without_path_leak(
    tmp_path, monkeypatch
):
    import asyncio

    root = tmp_path / "open-secret-root"

    def fail_open(path, flags, mode):
        del flags, mode
        raise PermissionError(f"cannot open {Path(path).resolve()}")

    monkeypatch.setattr(live_capture_module.os, "open", fail_open)
    with pytest.raises(LiveCaptureError) as exc_info:
        asyncio.run(_run(root, ["query"], _orchestration([])))

    assert str(exc_info.value) == "Capture checkpoint could not be updated"
    assert str(root.resolve()) not in str(exc_info.value)
    assert not (root / ".capture_checkpoint.json.tmp").exists()
    assert not (root / "capture_checkpoint.json").exists()
    assert _Manager.instances == []


def test_resume_checkpoint_read_failure_is_bounded_without_path_leak(
    tmp_path, monkeypatch
):
    import asyncio

    root = tmp_path / "resume-secret-root"
    asyncio.run(_run(root, ["query"], _orchestration([], blocked_query="query")))
    checkpoint = root / "capture_checkpoint.json"
    original_read_bytes = Path.read_bytes

    def fail_checkpoint_read(path):
        if path == checkpoint:
            raise PermissionError(f"cannot read {checkpoint.resolve()}")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", fail_checkpoint_read)
    with pytest.raises(LiveCaptureError) as exc_info:
        asyncio.run(run_live_capture(
            job_root=root,
            cdp_endpoint="http://127.0.0.1:9222",
            resume=True,
            manager_factory=_Manager,
            tool_factory=_Tool,
            orchestration=_orchestration([]),
        ))

    assert str(exc_info.value) == "Capture checkpoint is corrupt"
    assert str(root.resolve()) not in str(exc_info.value)


def test_resume_checkpoint_replace_failure_preserves_original_bounded_error(
    tmp_path, monkeypatch
):
    import asyncio

    root = tmp_path / "resume-update-secret-root"
    asyncio.run(_run(root, ["query"], _orchestration([], blocked_query="query")))
    replace_calls = 0

    def fail_replace(source, destination):
        nonlocal replace_calls
        del source, destination
        replace_calls += 1
        raise PermissionError(f"cannot replace {root.resolve()}")

    monkeypatch.setattr(live_capture_module.os, "replace", fail_replace)
    with pytest.raises(LiveCaptureError) as exc_info:
        asyncio.run(run_live_capture(
            job_root=root,
            cdp_endpoint="http://127.0.0.1:9222",
            resume=True,
            manager_factory=_Manager,
            tool_factory=_Tool,
            orchestration=_orchestration([]),
        ))

    assert str(exc_info.value) == "Capture checkpoint could not be updated"
    assert str(root.resolve()) not in str(exc_info.value)
    assert replace_calls == 2
    assert not (root / ".capture_checkpoint.json.tmp").exists()
    checkpoint = json.loads(
        (root / "capture_checkpoint.json").read_text(encoding="utf-8")
    )
    assert checkpoint["status"] == "HUMAN_ACTION_REQUIRED"


def test_resume_manifest_read_failure_is_bounded_without_path_leak(
    tmp_path, monkeypatch
):
    import asyncio

    root = tmp_path / "manifest-secret-root"
    _Tool.block_at = 2
    asyncio.run(_run(root, ["query"], _orchestration([])))
    original_read_bytes = Path.read_bytes

    def fail_manifest_read(path):
        if path.name == "source_pack.json":
            raise PermissionError(f"cannot read {path.resolve()}")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", fail_manifest_read)
    with pytest.raises(LiveCaptureError) as exc_info:
        asyncio.run(run_live_capture(
            job_root=root,
            cdp_endpoint="http://127.0.0.1:9222",
            resume=True,
            manager_factory=_Manager,
            tool_factory=_Tool,
            orchestration=_orchestration([]),
        ))

    assert str(exc_info.value) == "Checkpoint manifest could not be read"
    assert str(root.resolve()) not in str(exc_info.value)


def test_capture_artifact_read_failure_is_terminal_and_bounded(tmp_path, monkeypatch):
    import asyncio

    root = tmp_path / "artifact-secret-root"
    original_read_bytes = Path.read_bytes

    def fail_manifest_read(path):
        if path.name == "source_pack.json":
            raise PermissionError(
                f"cannot read {path.resolve()} https://shopee.test/query"
            )
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", fail_manifest_read)
    with pytest.raises(LiveCaptureError) as exc_info:
        asyncio.run(_run(root, ["query"], _orchestration([])))

    assert str(exc_info.value) == "Live capture failed"
    assert str(root.resolve()) not in str(exc_info.value)
    checkpoint = json.loads(
        (root / "capture_checkpoint.json").read_text(encoding="utf-8")
    )
    assert checkpoint["status"] == "FAILED"


def test_bundle_creation_failure_cleans_staging_and_fails_closed(
    tmp_path, monkeypatch
):
    import asyncio

    root = tmp_path / "bundle-secret-root"

    def fail_link(source, destination):
        del source, destination
        raise PermissionError(f"cannot create {root.resolve()}\\capture_bundle.json")

    monkeypatch.setattr(live_capture_module.os, "link", fail_link)
    with pytest.raises(LiveCaptureError) as exc_info:
        asyncio.run(_run(root, ["query"], _orchestration([])))

    assert str(exc_info.value) == "Capture bundle could not be created"
    assert str(root.resolve()) not in str(exc_info.value)
    assert not (root / ".capture_bundle.json.tmp").exists()
    assert not (root / "capture_bundle.json").exists()
    checkpoint = json.loads(
        (root / "capture_checkpoint.json").read_text(encoding="utf-8")
    )
    assert checkpoint["status"] == "FAILED"


def test_existing_bundle_is_not_overwritten_when_resumable_state_fails_closed(
    tmp_path,
):
    import asyncio

    root = tmp_path / "capture"
    asyncio.run(_run(root, ["query"], _orchestration([], blocked_query="query")))
    bundle = root / "capture_bundle.json"
    sentinel = b"existing-bundle-must-not-change\n"
    bundle.write_bytes(sentinel)

    with pytest.raises(LiveCaptureError, match="Capture bundle already exists"):
        asyncio.run(run_live_capture(
            job_root=root,
            cdp_endpoint="http://127.0.0.1:9222",
            resume=True,
            manager_factory=_Manager,
            tool_factory=_Tool,
            orchestration=_orchestration([]),
        ))

    assert bundle.read_bytes() == sentinel
    checkpoint = json.loads(
        (root / "capture_checkpoint.json").read_text(encoding="utf-8")
    )
    assert checkpoint["status"] == "FAILED"
    assert checkpoint["category"] == "TERMINAL_FAILURE"


def test_resume_rejects_lexical_manifest_escape(tmp_path):
    import asyncio

    root = tmp_path / "capture"
    _Tool.block_at = 2
    asyncio.run(_run(root, ["query"], _orchestration([])))
    checkpoint_path = root / "capture_checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["completed_observations"][0]["manifest_path"] = (
        "../outside/source_pack.json"
    )
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")

    with pytest.raises(LiveCaptureError, match="observation path is invalid"):
        asyncio.run(run_live_capture(
            job_root=root,
            cdp_endpoint="http://127.0.0.1:9222",
            resume=True,
            manager_factory=_Manager,
            tool_factory=_Tool,
            orchestration=_orchestration([]),
        ))


def test_resume_rejects_resolved_manifest_escape_without_browser_work(
    tmp_path, monkeypatch
):
    import asyncio

    root = tmp_path / "capture"
    _Tool.block_at = 2
    asyncio.run(_run(root, ["query"], _orchestration([])))
    checkpoint_path = root / "capture_checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    manifest = root / checkpoint["completed_observations"][0]["manifest_path"]
    outside = tmp_path / "outside-secret" / "source_pack.json"
    original_resolve = Path.resolve

    def resolve_manifest_outside(path, strict=False):
        if path == manifest:
            return outside
        return original_resolve(path, strict=strict)

    _Manager.instances = []
    _Tool.instances = []
    _Tool.calls = []
    monkeypatch.setattr(Path, "resolve", resolve_manifest_outside)

    with pytest.raises(LiveCaptureError, match="escapes the job root") as exc_info:
        asyncio.run(run_live_capture(
            job_root=root,
            cdp_endpoint="http://127.0.0.1:9222",
            resume=True,
            manager_factory=_Manager,
            tool_factory=_Tool,
            orchestration=_orchestration([]),
        ))

    assert str(root) not in str(exc_info.value)
    assert str(outside) not in str(exc_info.value)
    assert _Manager.instances == []
    assert _Tool.instances == []
    assert _Tool.calls == []


def test_fresh_capture_reuses_bound_session_and_rejects_silent_switch(tmp_path):
    """AC5 regression: bound session must govern discovery and acquisition without silent switch."""
    import asyncio
    root = tmp_path / "capture"

    class StrictSwitchingManager:
        instances = []

        def __init__(self, cdp_endpoint):
            self.cdp_endpoint = cdp_endpoint
            self.close_count = 0
            self.bound_session = _Session("a" * 64)
            self.requested_run_ids = []
            type(self).instances.append(self)

        async def get_or_create_session(self, run_id):
            self.requested_run_ids.append(run_id)
            if run_id == live_capture_module._BINDING_RUN_ID:
                return self.bound_session
            raise AssertionError(
                f"Downstream operation requested independent session with run_id={run_id!r}"
            )

        async def close_all(self):
            self.close_count += 1

    seen_adapter_browsers = []

    async def recording_orchestration(plans, **kwargs):
        del kwargs
        plan = plans[0]
        seen_adapter_browsers.append(plan.adapter._browser)
        candidate = SimpleNamespace(
            candidate_id="cand-1",
            url="https://shopee.test/item-1",
            title="Item 1",
        )
        return SimpleNamespace(shortlist=(SimpleNamespace(candidate=candidate),))

    outcome = asyncio.run(run_live_capture(
        job_root=root,
        cdp_endpoint="http://127.0.0.1:9222",
        queries=["test query"],
        manager_factory=StrictSwitchingManager,
        tool_factory=_Tool,
        orchestration=recording_orchestration,
    ))

    assert outcome.status is LiveCaptureStatus.READY
    mgr = StrictSwitchingManager.instances[0]
    assert mgr.requested_run_ids == [live_capture_module._BINDING_RUN_ID]
    assert seen_adapter_browsers == [mgr.bound_session]
    assert len(_Tool.contexts) == 2
    for ctx in _Tool.contexts:
        assert ctx["browser"] is mgr.bound_session
        assert ctx["browser_manager"] is mgr
    assert mgr.close_count == 1


def test_resume_reuses_bound_session_and_rejects_silent_switch(tmp_path):
    """AC5 regression: resumed operations must reuse bound session without creating new ones."""
    import asyncio
    root = tmp_path / "resume_capture"

    class StrictSwitchingManager:
        instances = []

        def __init__(self, cdp_endpoint):
            self.cdp_endpoint = cdp_endpoint
            self.close_count = 0
            self.bound_session = _Session("a" * 64)
            self.requested_run_ids = []
            type(self).instances.append(self)

        async def get_or_create_session(self, run_id):
            self.requested_run_ids.append(run_id)
            if run_id == live_capture_module._BINDING_RUN_ID:
                return self.bound_session
            raise AssertionError(
                f"Downstream operation requested independent session with run_id={run_id!r}"
            )

        async def close_all(self):
            self.close_count += 1

    _Tool.block_at = 1
    first = asyncio.run(_run(root, ["query"], _orchestration([])))
    assert first.status is LiveCaptureStatus.HUMAN_ACTION_REQUIRED
    _Tool.block_at = None

    resumed = asyncio.run(run_live_capture(
        job_root=root,
        cdp_endpoint="http://127.0.0.1:9222",
        resume=True,
        manager_factory=StrictSwitchingManager,
        tool_factory=_Tool,
        orchestration=_orchestration([]),
    ))

    assert resumed.status is LiveCaptureStatus.READY
    mgr = StrictSwitchingManager.instances[-1]
    assert mgr.requested_run_ids == [live_capture_module._BINDING_RUN_ID]
    for ctx in _Tool.contexts[1:]:
        assert ctx["browser"] is mgr.bound_session
        assert ctx["browser_manager"] is mgr
    assert mgr.close_count == 1


def test_downstream_components_would_fail_if_given_manager_instead_of_bound_session():
    """AC5 regression: proves ShopeeDiscoveryAdapter and ShopeeSourceExtractor acquire bound session."""
    import asyncio
    from src.product_intelligence.adapters.shopee import ShopeeDiscoveryAdapter
    from src.product_source.platforms.shopee import ShopeeSourceExtractor

    class StrictSwitchingManager:
        def __init__(self):
            self.bound_session = _Session("a" * 64)

        async def get_or_create_session(self, run_id):
            if run_id == live_capture_module._BINDING_RUN_ID:
                return self.bound_session
            raise AssertionError(
                f"Downstream operation requested independent session with run_id={run_id!r}"
            )

    mgr = StrictSwitchingManager()

    # 1. Given manager directly, ShopeeDiscoveryAdapter attempts to create independent session
    adapter_with_mgr = ShopeeDiscoveryAdapter(browser=mgr)
    with pytest.raises(AssertionError, match="discovery_run"):
        asyncio.run(adapter_with_mgr._acquire_page())

    # Given bound session, ShopeeDiscoveryAdapter reuses it cleanly
    adapter_with_session = ShopeeDiscoveryAdapter(browser=mgr.bound_session)
    page, cleanup = asyncio.run(adapter_with_session._acquire_page())
    assert page is mgr.bound_session
    assert cleanup is None

    # 2. Given manager directly, ShopeeSourceExtractor attempts to create independent session
    extractor_with_mgr = ShopeeSourceExtractor(browser=mgr)
    with pytest.raises(AssertionError, match="test-run"):
        asyncio.run(extractor_with_mgr._acquire_page("https://shopee.vn/product/123/456", "test-run"))

    # Given bound session, ShopeeSourceExtractor reuses it cleanly
    extractor_with_session = ShopeeSourceExtractor(browser=mgr.bound_session)
    extractor_page = asyncio.run(extractor_with_session._acquire_page("https://shopee.vn/product/123/456", "test-run"))
    assert extractor_page is mgr.bound_session
