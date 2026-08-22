from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.aios_bridge.continuity.dispatch import (
    CapacityState,
    DispatchActorKind,
)
from src.aios_bridge.continuity.state import ArtifactRef, BrainOperation
from src.aios_bridge.external_brain.contracts import (
    BrainOutputType,
    ModelRequest,
    ModelResponse,
    ModelResponseStatus,
)
from src.aios_bridge.external_brain.gateway import ModelGateway
from src.aios_bridge.external_brain.usage import JsonlUsageLedger
from src.aios_bridge import minimax_m3_input_counter as counter_module
from src.aios_bridge.minimax_m3_input_counter import (
    ASSET_MANIFEST_PATH,
    CHAT_TEMPLATE_PATH,
    MiniMaxM3LocalProviderInputCounter,
    SOURCE_REPOSITORY,
    SOURCE_REVISION,
    TOKENIZER_PATH,
)
from src.aios_bridge.minimax_m3_proof_lock import MiniMaxM3ProofLock
from src.aios_bridge.paid_api_grant import PaidApiGrant
from src.aios_bridge import paid_api_real_escape as real_escape_module
from src.aios_bridge.paid_api_real_escape import (
    PaidApiRealEscapeError,
    execute_paid_api_real_escape,
)
from src.aios_bridge.paid_api_proof_preflight import (
    build_paid_api_proof_preflight_receipt,
)
from src.aios_bridge.runtime_dispatch import RuntimeCapacityRecord
from src.aios_bridge.runtime_paid_api_grant import AtomicPaidApiGrantStore


TASK_ID = "TASK-062"
GRANT_ID = "grant-task-062-offline"
WORKSPACE_ID = "1" * 64
MAIN_SHA = "2" * 40
CONTROL_SHA = "3" * 40
PROOF_LOCK_PATH = ".ai/context/TASK-062-MINIMAX-PROOF-LOCK.json"
PROOF_LOCK_BLOB = "4" * 40
ARTIFACT_PATH = ".ai/tasks/TASK-062.md"
ARTIFACT_CONTENT = "# TASK-062\n\nBuild the bounded advisory proof harness.\n"
SUBSCRIPTION_BRAIN = "subscription-brain"
PAID_BRAIN = "minimax-paid-brain"
TOKEN_COUNT = 17

TEMPLATE = b"{{ messages[0].content }}|{{ messages[1].content }}"
TOKENIZER = b'{"synthetic":"offline-tokenizer"}'

SUCCESS_PROPOSAL = (
    "## SUMMARY\nBounded advisory plan.\n\n"
    "## STEPS\n1. Correlate the supplied evidence.\n\n"
    "## FILES\n- Advisory artifacts only.\n\n"
    "## TESTS\n- Verify the bounded proof.\n\n"
    "## RISKS\n- No execution authority.\n"
)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git_blob_sha(content: str) -> str:
    raw = content.encode("utf-8")
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


class FakeEncoding:
    ids = list(range(TOKEN_COUNT))


class FakeTokenizer:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.calls = 0

    def encode(self, _text: str, *, add_special_tokens: bool):
        assert add_special_tokens is False
        self.calls += 1
        self.events.append("context_count" if self.calls == 1 else "full_input_count")
        return FakeEncoding()


class FakeTemplate:
    def render(self, *, messages, tools, add_generation_prompt):
        assert tools is None
        assert add_generation_prompt is True
        return f"{messages[0]['content']}|{messages[1]['content']}"


class FakeProvider:
    provider_id = "minimax"
    model_name = "MiniMax-M3"

    def __init__(
        self,
        *,
        store: AtomicPaidApiGrantStore,
        grant: PaidApiGrant,
        events: list[str],
        status: ModelResponseStatus = ModelResponseStatus.SUCCESS,
        raises: Exception | None = None,
        content: str = SUCCESS_PROPOSAL,
    ) -> None:
        self.store = store
        self.grant = grant
        self.events = events
        self.status = status
        self.raises = raises
        self.content = content
        self.calls = 0
        self.api_key = "DUMMY_REAL_ESCAPE_SECRET_MUST_NOT_LEAK"

    async def invoke(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        self.events.append("provider_invoke")
        assert self.store.load_active(self.grant.task_id, self.grant.grant_id) is None
        assert self.store.load_consumed(self.grant.task_id, self.grant.grant_id) == self.grant
        if self.raises is not None:
            raise self.raises
        success = self.status is ModelResponseStatus.SUCCESS
        return ModelResponse(
            schema_version="1",
            request_id=request.request_id,
            task_id=request.task_id,
            provider=self.provider_id,
            model=self.model_name,
            status=self.status,
            output_type=BrainOutputType.PLAN if success else None,
            content=self.content if success else None,
            input_tokens=TOKEN_COUNT,
            output_tokens=8 if success else 0,
            latency_ms=1,
            provider_request_id="offline-minimax-request-062",
            error_code=None if success else "OFFLINE_PROVIDER_FAILURE",
            error_message=None if success else "offline failure",
        )


class FailingLedger:
    def append(self, _record) -> None:
        raise OSError("offline ledger failure")


def _proof_lock() -> MiniMaxM3ProofLock:
    return MiniMaxM3ProofLock(
        schema_version="1",
        provider_id="minimax",
        model_id="MiniMax-M3",
        endpoint_url="https://api.minimax.io/v1/chat/completions",
        credential_env_name="MINIMAX_API_KEY",
        source_repository=SOURCE_REPOSITORY,
        source_revision=SOURCE_REVISION,
        chat_template_path=CHAT_TEMPLATE_PATH,
        chat_template_sha256=_sha256(TEMPLATE),
        tokenizer_path=TOKENIZER_PATH,
        tokenizer_sha256=_sha256(TOKENIZER),
        jinja2_version="3.1.6",
        tokenizers_version="0.23.1",
        requests_version="2.32.3",
    )


def _counter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    events: list[str],
) -> MiniMaxM3LocalProviderInputCounter:
    bundle = tmp_path / "assets"
    bundle.mkdir()
    (bundle / CHAT_TEMPLATE_PATH).write_bytes(TEMPLATE)
    (bundle / TOKENIZER_PATH).write_bytes(TOKENIZER)
    (bundle / ASSET_MANIFEST_PATH).write_text(
        json.dumps(
            {
                "schema_version": "1",
                "source_repository": SOURCE_REPOSITORY,
                "source_revision": SOURCE_REVISION,
                "chat_template_path": CHAT_TEMPLATE_PATH,
                "chat_template_sha256": _sha256(TEMPLATE),
                "tokenizer_path": TOKENIZER_PATH,
                "tokenizer_sha256": _sha256(TOKENIZER),
            }
        ),
        encoding="utf-8",
    )
    tokenizer = FakeTokenizer(events)
    monkeypatch.setattr(counter_module, "_load_jinja_template", lambda _value: FakeTemplate())
    monkeypatch.setattr(counter_module, "_load_tokenizer", lambda _value: tokenizer)
    return MiniMaxM3LocalProviderInputCounter(bundle, _proof_lock())


def _grant() -> PaidApiGrant:
    return PaidApiGrant(
        schema_version="1",
        grant_id=GRANT_ID,
        task_id=TASK_ID,
        actor_kind=DispatchActorKind.BRAIN,
        brain_id=PAID_BRAIN,
        provider_id="minimax",
        model_id="MiniMax-M3",
        brain_operation=BrainOperation.PLAN,
        authorized_artifact_path=ARTIFACT_PATH,
        authorized_artifact_blob_sha=_git_blob_sha(ARTIFACT_CONTENT),
        max_input_tokens=256,
        max_output_tokens=64,
        max_calls=1,
        expires_at_epoch_seconds=1_000,
        workspace_id=WORKSPACE_ID,
    )


def _capacity(actor_id: str, state: CapacityState) -> RuntimeCapacityRecord:
    return RuntimeCapacityRecord(
        actor_kind=DispatchActorKind.BRAIN,
        actor_id=actor_id,
        capacity_state=state,
        observed_at_epoch_seconds=90,
        ttl_seconds=100,
    )


def _setup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    provider_status: ModelResponseStatus = ModelResponseStatus.SUCCESS,
    provider_raises: Exception | None = None,
    provider_content: str = SUCCESS_PROPOSAL,
    ledger=None,
    subscription_state: CapacityState = CapacityState.QUOTA_EXHAUSTED,
):
    events: list[str] = []
    proof_lock = _proof_lock()
    counter = _counter(tmp_path, monkeypatch, events)
    grant = _grant()
    store = AtomicPaidApiGrantStore(tmp_path / "grants", WORKSPACE_ID)
    store.activate(grant, now_epoch_seconds=10)
    subscription = _capacity(SUBSCRIPTION_BRAIN, subscription_state)
    paid = _capacity(PAID_BRAIN, CapacityState.AVAILABLE)
    grant_hash = hashlib.sha256(GRANT_ID.encode("utf-8")).hexdigest()
    preflight = build_paid_api_proof_preflight_receipt(
        task_id=TASK_ID,
        grant=grant,
        runtime_main_sha=MAIN_SHA,
        control_commit_sha=CONTROL_SHA,
        proof_lock_path=PROOF_LOCK_PATH,
        proof_lock_blob_sha=PROOF_LOCK_BLOB,
        proof_lock=proof_lock,
        counter_id=counter.counter_id,
        ledger_logical_path=f"paid_api_usage/{TASK_ID}/{grant_hash}.jsonl",
        ledger_ready=True,
        credential_present=True,
    )
    actual_ledger = ledger or JsonlUsageLedger(tmp_path / "usage" / "proof.jsonl")
    provider = FakeProvider(
        store=store,
        grant=grant,
        events=events,
        status=provider_status,
        raises=provider_raises,
        content=provider_content,
    )
    factory_calls = {"count": 0}

    def provider_factory():
        factory_calls["count"] += 1
        events.append("provider_factory")
        assert store.load_consumed(TASK_ID, GRANT_ID) == grant
        return provider

    arguments = {
        "task_id": TASK_ID,
        "runtime_main_sha": MAIN_SHA,
        "control_commit_sha": CONTROL_SHA,
        "proof_lock_path": PROOF_LOCK_PATH,
        "proof_lock_blob_sha": PROOF_LOCK_BLOB,
        "proof_lock": proof_lock,
        "preflight_receipt": preflight,
        "grant": grant,
        "grant_store": store,
        "authorized_artifact": ArtifactRef(
            path=ARTIFACT_PATH,
            ref=CONTROL_SHA,
            blob_sha=grant.authorized_artifact_blob_sha,
        ),
        "authorized_artifact_content": ARTIFACT_CONTENT,
        "provider_input_counter": counter,
        "subscription_brain_id": SUBSCRIPTION_BRAIN,
        "subscription_capacity_record": subscription,
        "paid_capacity_record": paid,
        "subscription_capacity_fingerprint": subscription.record_fingerprint,
        "paid_capacity_fingerprint": paid.record_fingerprint,
        "now_epoch_seconds": 100,
        "runtime_root": tmp_path / "runtime",
        "provider_factory": provider_factory,
        "ledger": actual_ledger,
    }
    return arguments, provider, factory_calls, events, store, grant


def _run(arguments):
    return asyncio.run(execute_paid_api_real_escape(**arguments))


def test_success_runs_r0_r10_flow_once_and_persists_bounded_external_proof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    arguments, provider, factory_calls, events, store, grant = _setup(
        tmp_path, monkeypatch
    )
    gateway_calls = {"count": 0}

    def gateway_factory(deferred_provider, ledger):
        gateway_calls["count"] += 1
        return ModelGateway(deferred_provider, ledger=ledger)

    arguments["gateway_factory"] = gateway_factory

    result = _run(arguments)

    assert events == [
        "context_count",
        "full_input_count",
        "provider_factory",
        "provider_invoke",
    ]
    assert factory_calls["count"] == 1
    assert gateway_calls["count"] == 1
    assert provider.calls == 1
    assert store.load_active(TASK_ID, GRANT_ID) is None
    assert store.load_consumed(TASK_ID, GRANT_ID) == grant
    receipt = result.proof_receipt
    assert receipt.provider_call_count == 1
    assert receipt.retry_count == 0
    assert receipt.grant_consumed is True
    assert receipt.executor_authority_created is False
    proposal = tmp_path / "runtime" / receipt.proposal_logical_path
    proof = tmp_path / "runtime" / receipt.proof_logical_path
    assert proposal.read_text(encoding="utf-8") == SUCCESS_PROPOSAL
    proof_data = json.loads(proof.read_text(encoding="utf-8"))
    assert proof_data == receipt.to_dict()
    combined = proposal.read_text(encoding="utf-8") + proof.read_text(encoding="utf-8")
    assert "DUMMY_REAL_ESCAPE_SECRET_MUST_NOT_LEAK" not in combined
    assert str(tmp_path) not in combined
    assert "Authorization" not in combined
    assert "executor_authority_created" in combined

    before_events = list(events)
    with pytest.raises(PaidApiRealEscapeError, match="GRANT_NOT_ACTIVE"):
        _run(arguments)
    assert events == before_events
    assert factory_calls["count"] == 1
    assert provider.calls == 1


@pytest.mark.parametrize(
    "state",
    [
        CapacityState.AVAILABLE,
        CapacityState.LIMITED,
        CapacityState.UNKNOWN,
    ],
)
def test_invalid_subscription_capacity_fails_before_construction_or_consumption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state: CapacityState,
):
    arguments, provider, factory_calls, _events, store, grant = _setup(
        tmp_path,
        monkeypatch,
        subscription_state=state,
    )

    with pytest.raises(PaidApiRealEscapeError, match="capacity state"):
        _run(arguments)
    assert factory_calls["count"] == 0
    assert provider.calls == 0
    assert store.load_active(TASK_ID, GRANT_ID) == grant
    assert store.load_consumed(TASK_ID, GRANT_ID) is None


def test_capacity_fingerprint_and_freshness_are_exact_pre_call_gates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    arguments, provider, factory_calls, _events, store, grant = _setup(
        tmp_path, monkeypatch
    )
    arguments["paid_capacity_fingerprint"] = "f" * 64
    with pytest.raises(PaidApiRealEscapeError, match="fingerprint"):
        _run(arguments)
    assert factory_calls["count"] == provider.calls == 0
    assert store.load_active(TASK_ID, GRANT_ID) == grant

    arguments["paid_capacity_fingerprint"] = arguments[
        "paid_capacity_record"
    ].record_fingerprint
    arguments["now_epoch_seconds"] = 500
    with pytest.raises(PaidApiRealEscapeError, match="not FRESH"):
        _run(arguments)
    assert factory_calls["count"] == provider.calls == 0
    assert store.load_active(TASK_ID, GRANT_ID) == grant


def test_full_provider_input_budget_fails_before_factory_call_or_consumption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    arguments, provider, factory_calls, _events, store, grant = _setup(
        tmp_path, monkeypatch
    )

    class SequenceTokenizer:
        def __init__(self):
            self.calls = 0

        def encode(self, _text, *, add_special_tokens):
            assert add_special_tokens is False
            self.calls += 1
            count = 10 if self.calls == 1 else grant.max_input_tokens + 1
            return SimpleNamespace(ids=list(range(count)))

    arguments["provider_input_counter"]._tokenizer = SequenceTokenizer()
    with pytest.raises(PaidApiRealEscapeError, match="PRE_CALL_VALIDATION"):
        _run(arguments)
    assert factory_calls["count"] == 0
    assert provider.calls == 0
    assert store.load_active(TASK_ID, GRANT_ID) == grant
    assert store.load_consumed(TASK_ID, GRANT_ID) is None


def test_provider_error_leaves_consumed_and_never_retries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    arguments, provider, factory_calls, _events, store, grant = _setup(
        tmp_path,
        monkeypatch,
        provider_raises=TimeoutError("offline timeout"),
    )

    with pytest.raises(PaidApiRealEscapeError, match="AFTER_CONSUME"):
        _run(arguments)
    assert factory_calls["count"] == 1
    assert provider.calls == 1
    assert store.load_active(TASK_ID, GRANT_ID) is None
    assert store.load_consumed(TASK_ID, GRANT_ID) == grant


def test_failed_response_and_ledger_failure_both_leave_consumed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    failed_dir = tmp_path / "failed"
    failed_dir.mkdir()
    arguments, provider, factory_calls, _events, store, grant = _setup(
        failed_dir,
        monkeypatch,
        provider_status=ModelResponseStatus.FAILED,
    )
    with pytest.raises(PaidApiRealEscapeError, match="OPERATIONAL_PROOF"):
        _run(arguments)
    assert factory_calls["count"] == provider.calls == 1
    assert store.load_consumed(TASK_ID, GRANT_ID) == grant

    ledger_dir = tmp_path / "ledger"
    ledger_dir.mkdir()
    arguments, provider, factory_calls, _events, store, grant = _setup(
        ledger_dir,
        monkeypatch,
        ledger=FailingLedger(),
    )
    with pytest.raises(PaidApiRealEscapeError, match="OPERATIONAL_PROOF"):
        _run(arguments)
    assert factory_calls["count"] == provider.calls == 1
    assert store.load_consumed(TASK_ID, GRANT_ID) == grant


def test_proof_write_failure_leaves_consumed_without_second_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    arguments, provider, factory_calls, _events, store, grant = _setup(
        tmp_path, monkeypatch
    )

    def fail_write(**_kwargs):
        raise OSError("offline proof write failure")

    monkeypatch.setattr(
        real_escape_module,
        "persist_paid_api_real_escape_artifacts",
        fail_write,
    )
    with pytest.raises(PaidApiRealEscapeError, match="PROOF_WRITE"):
        _run(arguments)
    assert factory_calls["count"] == provider.calls == 1
    assert store.load_consumed(TASK_ID, GRANT_ID) == grant


@pytest.mark.parametrize(
    "unsafe_content",
    [
        SUCCESS_PROPOSAL + "\nAuthorization: Bearer not-safe\n",
        SUCCESS_PROPOSAL + "\nC:\\Users\\secret\\credential.txt\n",
        SUCCESS_PROPOSAL + "\n/home/user/private/credential.txt\n",
        SUCCESS_PROPOSAL + "\n<think>hidden reasoning</think>\n",
    ],
)
def test_unsafe_proposal_is_rejected_after_consume_and_never_persisted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unsafe_content: str,
):
    arguments, provider, factory_calls, _events, store, grant = _setup(
        tmp_path,
        monkeypatch,
        provider_content=unsafe_content,
    )

    with pytest.raises(PaidApiRealEscapeError):
        _run(arguments)
    assert factory_calls["count"] == provider.calls == 1
    assert store.load_consumed(TASK_ID, GRANT_ID) == grant
    assert not (tmp_path / "runtime" / "paid_api_proofs").exists()


def test_orchestrator_has_no_network_repository_or_executor_authority_surface():
    source = Path(real_escape_module.__file__).read_text(encoding="utf-8")
    forbidden = (
        "import requests",
        "import socket",
        "import subprocess",
        "git fetch",
        "git clone",
        "ExecutorDispatch",
        "fetch_control",
        "paid-grant-create",
    )
    assert all(fragment not in source for fragment in forbidden)
