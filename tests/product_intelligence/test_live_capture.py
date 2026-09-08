from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import src.product_intelligence.live_capture as live_capture_module
from src.core.errors import AgentException
from src.core.types import ToolResult, ToolStatus
from src.product_intelligence.discovery import DiscoveryBlockedError
from src.product_intelligence.live_capture import (
    LiveCaptureError,
    LiveCapturePhase,
    LiveCaptureStatus,
    run_live_capture,
)


class _Manager:
    instances = []

    def __init__(self, cdp_endpoint):
        self.cdp_endpoint = cdp_endpoint
        self.close_count = 0
        type(self).instances.append(self)

    async def close_all(self):
        self.close_count += 1


class _Tool:
    instances = []
    block_at = None
    fail_at = None
    calls = []

    def __init__(self):
        type(self).instances.append(self)

    async def execute(self, call, context):
        type(self).calls.append((call.call_id, call.arguments["url"]))
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
    _Tool.instances = []
    _Tool.calls = []
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
    assert first.status is LiveCaptureStatus.CHALLENGE_REQUIRED
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
    assert first.status is LiveCaptureStatus.CHALLENGE_REQUIRED
    first_bytes = (root / "capture_checkpoint.json").read_bytes()
    second = asyncio.run(run_live_capture(
        job_root=root,
        cdp_endpoint="http://127.0.0.1:9222",
        resume=True,
        manager_factory=_Manager,
        tool_factory=_Tool,
        orchestration=_orchestration(seen, blocked_query="query"),
    ))
    assert second.status is LiveCaptureStatus.CHALLENGE_REQUIRED
    assert _Tool.calls == []
    assert seen == ["query", "query"]
    assert json.loads(first_bytes) == json.loads((root / "capture_checkpoint.json").read_bytes())


def test_endpoint_mismatch_is_terminal_before_browser_work(tmp_path):
    import asyncio
    root = tmp_path / "capture"
    asyncio.run(_run(root, ["query"], _orchestration([], blocked_query="query")))
    manager_count = len(_Manager.instances)
    with pytest.raises(LiveCaptureError):
        asyncio.run(run_live_capture(
            job_root=root,
            cdp_endpoint="http://127.0.0.1:9333",
            resume=True,
            manager_factory=_Manager,
            tool_factory=_Tool,
            orchestration=_orchestration([]),
        ))
    assert len(_Manager.instances) == manager_count
    assert json.loads((root / "capture_checkpoint.json").read_bytes())["status"] == "FAILED"


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
    assert checkpoint["status"] == "CHALLENGE_REQUIRED"


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
