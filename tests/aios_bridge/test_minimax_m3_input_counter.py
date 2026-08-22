"""Tests for MiniMaxM3LocalProviderInputCounter with ProofLock (TASK-059 / M11.3B)."""
from __future__ import annotations

import builtins
import hashlib
import json
from pathlib import Path

import pytest

from src.aios_bridge.external_brain.contracts import (
    BrainOperation,
    BrainOutputType,
    BrainRole,
    ModelRequest,
)
from src.aios_bridge import minimax_m3_input_counter as counter_module
from src.aios_bridge.minimax_m3_input_counter import (
    MiniMaxM3InputCounterError,
    MiniMaxM3LocalProviderInputCounter,
    PROVIDER_ID,
    MODEL_ID,
    SOURCE_REPOSITORY,
    SOURCE_REVISION,
    CHAT_TEMPLATE_PATH,
    TOKENIZER_PATH,
    ASSET_MANIFEST_PATH,
)
from src.aios_bridge.minimax_m3_proof_lock import MiniMaxM3ProofLock
from src.aios_bridge import provider_input_budget as budget_module
from src.aios_bridge.provider_input_budget import (
    ProviderInputBudgetError,
    fingerprint_model_request,
    require_trusted_local_provider_input_counter,
)


TEMPLATE = b"{{ messages[0].content }}|{{ messages[1].content }}"
TOKENIZER = b'{"synthetic":"tokenizer"}'


class FakeTemplate:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def render(self, **kwargs: object) -> str:
        self.calls.append(kwargs)
        messages = kwargs["messages"]
        assert isinstance(messages, list)
        return f"{messages[0]['content']}|{messages[1]['content']}"


class FakeEncoding:
    ids = [11, 12, 13, 14]


class FakeTokenizer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bool]] = []

    def encode(self, prompt: str, *, add_special_tokens: bool) -> FakeEncoding:
        self.calls.append((prompt, add_special_tokens))
        return FakeEncoding()


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _manifest(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "1",
        "source_repository": SOURCE_REPOSITORY,
        "source_revision": SOURCE_REVISION,
        "chat_template_path": CHAT_TEMPLATE_PATH,
        "chat_template_sha256": _sha(TEMPLATE),
        "tokenizer_path": TOKENIZER_PATH,
        "tokenizer_sha256": _sha(TOKENIZER),
    }
    value.update(overrides)
    return value


def _proof_lock(template_sha: str = _sha(TEMPLATE), tokenizer_sha: str = _sha(TOKENIZER), **overrides: object) -> MiniMaxM3ProofLock:
    data = {
        "schema_version": "1",
        "provider_id": PROVIDER_ID,
        "model_id": MODEL_ID,
        "endpoint_url": "https://api.minimax.io/v1/text/chatcompletion_v2",
        "credential_env_name": "MINIMAX_API_KEY",
        "source_repository": SOURCE_REPOSITORY,
        "source_revision": SOURCE_REVISION,
        "chat_template_path": CHAT_TEMPLATE_PATH,
        "chat_template_sha256": template_sha,
        "tokenizer_path": TOKENIZER_PATH,
        "tokenizer_sha256": tokenizer_sha,
        "jinja2_version": "3.1.6",
        "tokenizers_version": "0.23.1",
        "requests_version": "2.32.3",
    }
    data.update(overrides)
    return MiniMaxM3ProofLock.from_dict(data)


def _write_bundle(
    root: Path,
    *,
    template: bytes = TEMPLATE,
    tokenizer: bytes = TOKENIZER,
    manifest: dict[str, object] | None = None,
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / CHAT_TEMPLATE_PATH).write_bytes(template)
    (root / TOKENIZER_PATH).write_bytes(tokenizer)
    manifest_value = manifest if manifest is not None else _manifest(
        chat_template_sha256=_sha(template),
        tokenizer_sha256=_sha(tokenizer),
    )
    (root / ASSET_MANIFEST_PATH).write_text(
        json.dumps(manifest_value),
        encoding="utf-8",
    )


@pytest.fixture
def fake_engines(monkeypatch: pytest.MonkeyPatch) -> tuple[FakeTemplate, FakeTokenizer, None]:
    template = FakeTemplate()
    tokenizer = FakeTokenizer()
    monkeypatch.setattr(counter_module, "_load_jinja_template", lambda _source: template)
    monkeypatch.setattr(counter_module, "_load_tokenizer", lambda _source: tokenizer)
    return template, tokenizer, None


@pytest.fixture
def model_request() -> ModelRequest:
    return ModelRequest(
        schema_version="1",
        request_id="request-059",
        task_id="TASK-059",
        role=BrainRole.ARCHITECT,
        operation=BrainOperation.PLAN,
        instruction="instruction text",
        context=(),
        output_format=BrainOutputType.PLAN,
        provider="minimax",
        model="MiniMax-M3",
    )


class TestMiniMaxM3InputCounterProvenance:
    def test_construction_with_valid_lock(self, tmp_path: Path, fake_engines):
        bundle = tmp_path / "bundle"
        _write_bundle(bundle)
        lock = _proof_lock()
        counter = MiniMaxM3LocalProviderInputCounter(bundle, lock)
        assert counter.provider_id == PROVIDER_ID
        assert counter.model_id == MODEL_ID
        assert counter.is_exact is True
        assert counter.counter_id == f"minimax-m3-local:{SOURCE_REVISION}:{_sha(TEMPLATE)}:{_sha(TOKENIZER)}"
        assert counter.proof_lock == lock

    def test_construction_requires_exact_proof_lock_type(self, tmp_path: Path, fake_engines):
        bundle = tmp_path / "bundle"
        _write_bundle(bundle)
        with pytest.raises(MiniMaxM3InputCounterError, match="exact MiniMaxM3ProofLock"):
            MiniMaxM3LocalProviderInputCounter(bundle, None)  # type: ignore
        with pytest.raises(MiniMaxM3InputCounterError, match="exact MiniMaxM3ProofLock"):
            MiniMaxM3LocalProviderInputCounter(bundle, {"some": "dict"})  # type: ignore

        class SubclassProofLock(MiniMaxM3ProofLock):
            pass

        subclass_instance = SubclassProofLock(**_proof_lock().to_dict())
        with pytest.raises(MiniMaxM3InputCounterError, match="exact MiniMaxM3ProofLock"):
            MiniMaxM3LocalProviderInputCounter(bundle, subclass_instance)

    def test_rejects_manifest_digest_mismatch_with_proof_lock(self, tmp_path: Path, fake_engines):
        bundle = tmp_path / "bundle"
        _write_bundle(bundle)
        bad_lock = _proof_lock(template_sha="0" * 64)
        with pytest.raises(MiniMaxM3InputCounterError, match="does not match proof lock"):
            MiniMaxM3LocalProviderInputCounter(bundle, bad_lock)

        bad_lock2 = _proof_lock(tokenizer_sha="0" * 64)
        with pytest.raises(MiniMaxM3InputCounterError, match="does not match proof lock"):
            MiniMaxM3LocalProviderInputCounter(bundle, bad_lock2)

    def test_rejects_file_digest_mismatch_with_proof_lock(self, tmp_path: Path, fake_engines):
        bundle = tmp_path / "bundle"
        _write_bundle(bundle)
        (bundle / CHAT_TEMPLATE_PATH).write_bytes(b"modified")
        lock = _proof_lock()
        with pytest.raises(MiniMaxM3InputCounterError, match="digest does not match"):
            MiniMaxM3LocalProviderInputCounter(bundle, lock)

    def test_missing_asset_file_fails_closed(self, tmp_path: Path, fake_engines):
        bundle = tmp_path / "bundle"
        _write_bundle(bundle)
        (bundle / TOKENIZER_PATH).unlink()
        lock = _proof_lock()
        with pytest.raises(MiniMaxM3InputCounterError, match="required bundle files"):
            MiniMaxM3LocalProviderInputCounter(bundle, lock)

    def test_unexpected_file_fails_closed(self, tmp_path: Path, fake_engines):
        bundle = tmp_path / "bundle"
        _write_bundle(bundle)
        (bundle / "unexpected").write_text("x", encoding="utf-8")
        lock = _proof_lock()
        with pytest.raises(MiniMaxM3InputCounterError, match="exact"):
            MiniMaxM3LocalProviderInputCounter(bundle, lock)

    def test_oversize_is_rejected_before_engine_parse(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        bundle = tmp_path / "bundle"
        _write_bundle(bundle)
        monkeypatch.setattr(counter_module, "MAX_CHAT_TEMPLATE_BYTES", len(TEMPLATE) - 1)
        calls: list[str] = []
        monkeypatch.setattr(counter_module, "_load_jinja_template", lambda _source: calls.append("jinja"))
        monkeypatch.setattr(counter_module, "_load_tokenizer", lambda _source: calls.append("tokenizer"))
        lock = _proof_lock()
        with pytest.raises(MiniMaxM3InputCounterError, match="size limit"):
            MiniMaxM3LocalProviderInputCounter(bundle, lock)
        assert calls == []

    def test_count_uses_exact_render_chain_and_returns_bound_evidence(
        self,
        tmp_path: Path,
        fake_engines,
        monkeypatch: pytest.MonkeyPatch,
        model_request: ModelRequest,
    ):
        bundle = tmp_path / "bundle"
        _write_bundle(bundle)
        template, tokenizer, _ = fake_engines
        rendered_messages = [
            {"role": "system", "content": "system text"},
            {"role": "user", "content": "user text"},
        ]
        render_calls: list[ModelRequest] = []

        def render_messages(value):
            render_calls.append(value)
            return rendered_messages

        monkeypatch.setattr(counter_module.external_brain_prompt, "render_messages", render_messages)
        lock = _proof_lock()
        counter = MiniMaxM3LocalProviderInputCounter(bundle, lock)

        evidence = counter.count_request(model_request)

        assert render_calls == [model_request]
        assert template.calls == [
            {
                "messages": rendered_messages,
                "tools": None,
                "add_generation_prompt": True,
            }
        ]
        assert tokenizer.calls == [("system text|user text", False)]
        assert evidence.counted_input_tokens == len(FakeEncoding.ids)
        assert evidence.model_request_fingerprint == fingerprint_model_request(model_request)
        assert evidence.provider_id == "minimax"
        assert evidence.model_id == "MiniMax-M3"
        assert evidence.counter_id == counter.counter_id
        assert evidence.token_count_is_exact is True

    def test_production_registry_accepts_only_exact_class(self, tmp_path: Path, fake_engines):
        bundle = tmp_path / "bundle"
        _write_bundle(bundle)
        lock = _proof_lock()
        counter = MiniMaxM3LocalProviderInputCounter(bundle, lock)

        assert budget_module._TRUSTED_LOCAL_COUNTER_TYPES == (
            MiniMaxM3LocalProviderInputCounter,
        )
        assert require_trusted_local_provider_input_counter(counter) is counter

        class CounterSubclass(MiniMaxM3LocalProviderInputCounter):
            pass

        subclass = object.__new__(CounterSubclass)
        with pytest.raises(ProviderInputBudgetError):
            require_trusted_local_provider_input_counter(subclass)

    def test_production_module_has_no_network_provider_or_credential_surface(self):
        source = Path(counter_module.__file__).read_text(encoding="utf-8")
        forbidden = (
            "import requests",
            "import httpx",
            "import aiohttp",
            "import socket",
            "import subprocess",
            "huggingface_hub",
            "Authorization",
            "api_key",
            "os.environ",
        )
        assert all(fragment not in source for fragment in forbidden)
