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
)
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
        "source_repository": "MiniMaxAI/MiniMax-M3",
        "source_revision": "3a41b311ffa5719cef48fed3974ccf2cc03733ea",
        "chat_template_path": "chat_template.jinja",
        "chat_template_sha256": _sha(TEMPLATE),
        "tokenizer_path": "tokenizer.json",
        "tokenizer_sha256": _sha(TOKENIZER),
    }
    value.update(overrides)
    return value


def _write_bundle(
    root: Path,
    *,
    template: bytes = TEMPLATE,
    tokenizer: bytes = TOKENIZER,
    manifest: dict[str, object] | None = None,
) -> None:
    root.mkdir()
    (root / "chat_template.jinja").write_bytes(template)
    (root / "tokenizer.json").write_bytes(tokenizer)
    manifest_value = manifest if manifest is not None else _manifest(
        chat_template_sha256=_sha(template),
        tokenizer_sha256=_sha(tokenizer),
    )
    (root / "asset-manifest.json").write_text(
        json.dumps(manifest_value),
        encoding="utf-8",
    )


@pytest.fixture
def model_request() -> ModelRequest:
    return ModelRequest(
        schema_version="1",
        request_id="request-057",
        task_id="TASK-057",
        role=BrainRole.CODER,
        operation=BrainOperation.GENERATE_PATCH,
        instruction="Implement the bounded task.",
        context=(),
        output_format=BrainOutputType.PATCH_PROPOSAL,
        provider="minimax",
        model="MiniMax-M3",
        max_input_tokens=1000,
        max_output_tokens=100,
    )


@pytest.fixture
def fake_engines(monkeypatch):
    template = FakeTemplate()
    tokenizer = FakeTokenizer()
    observed: dict[str, object] = {}

    def load_template(source: str) -> FakeTemplate:
        observed["template_source"] = source
        return template

    def load_tokenizer(source: bytes) -> FakeTokenizer:
        observed["tokenizer_bytes"] = source
        return tokenizer

    monkeypatch.setattr(counter_module, "_load_jinja_template", load_template)
    monkeypatch.setattr(counter_module, "_load_tokenizer", load_tokenizer)
    return template, tokenizer, observed


def test_exact_identity_counter_id_and_asset_loading(tmp_path, fake_engines):
    bundle = tmp_path / "bundle"
    _write_bundle(bundle)
    template, tokenizer, observed = fake_engines

    counter = MiniMaxM3LocalProviderInputCounter(bundle)

    assert counter.provider_id == "minimax"
    assert counter.model_id == "MiniMax-M3"
    assert counter.is_exact is True
    assert counter_module.SOURCE_REVISION in counter.counter_id
    assert _sha(TEMPLATE) in counter.counter_id
    assert _sha(TOKENIZER) in counter.counter_id
    assert observed == {
        "template_source": TEMPLATE.decode("utf-8"),
        "tokenizer_bytes": TOKENIZER,
    }
    assert template.calls == []
    assert tokenizer.calls == []


@pytest.mark.parametrize(
    "mutation",
    [
        {"extra": "field"},
        {"schema_version": 1},
        {"source_repository": "other/repository"},
        {"source_revision": "main"},
        {"chat_template_path": "../chat_template.jinja"},
        {"tokenizer_path": "../tokenizer.json"},
        {"chat_template_sha256": "A" * 64},
        {"tokenizer_sha256": "0" * 63},
    ],
)
def test_manifest_requires_exact_fields_values_and_digests(
    tmp_path,
    fake_engines,
    mutation,
):
    manifest = _manifest()
    manifest.update(mutation)
    if "extra" not in mutation:
        pass
    bundle = tmp_path / "bundle"
    _write_bundle(bundle, manifest=manifest)

    with pytest.raises(MiniMaxM3InputCounterError):
        MiniMaxM3LocalProviderInputCounter(bundle)


def test_manifest_missing_field_is_rejected(tmp_path, fake_engines):
    manifest = _manifest()
    del manifest["source_revision"]
    bundle = tmp_path / "bundle"
    _write_bundle(bundle, manifest=manifest)

    with pytest.raises(MiniMaxM3InputCounterError):
        MiniMaxM3LocalProviderInputCounter(bundle)


@pytest.mark.parametrize("missing", ["asset-manifest.json", "chat_template.jinja", "tokenizer.json"])
def test_missing_required_file_is_rejected(tmp_path, fake_engines, missing):
    bundle = tmp_path / "bundle"
    _write_bundle(bundle)
    (bundle / missing).unlink()

    with pytest.raises(MiniMaxM3InputCounterError):
        MiniMaxM3LocalProviderInputCounter(bundle)


def test_extra_bundle_file_is_rejected(tmp_path, fake_engines):
    bundle = tmp_path / "bundle"
    _write_bundle(bundle)
    (bundle / "unexpected").write_text("x", encoding="utf-8")

    with pytest.raises(MiniMaxM3InputCounterError):
        MiniMaxM3LocalProviderInputCounter(bundle)


@pytest.mark.parametrize("filename", ["asset-manifest.json", "chat_template.jinja", "tokenizer.json"])
def test_asset_symlinks_are_rejected(tmp_path, fake_engines, monkeypatch, filename):
    bundle = tmp_path / "bundle"
    _write_bundle(bundle)
    symlink_path = bundle / filename
    original_is_symlink = Path.is_symlink

    def is_symlink(path: Path) -> bool:
        return path == symlink_path or original_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", is_symlink)

    with pytest.raises(MiniMaxM3InputCounterError):
        MiniMaxM3LocalProviderInputCounter(bundle)


def test_oversize_is_rejected_before_engine_parse(tmp_path, monkeypatch):
    bundle = tmp_path / "bundle"
    _write_bundle(bundle)
    monkeypatch.setattr(counter_module, "MAX_CHAT_TEMPLATE_BYTES", len(TEMPLATE) - 1)
    calls: list[str] = []
    monkeypatch.setattr(counter_module, "_load_jinja_template", lambda _source: calls.append("jinja"))
    monkeypatch.setattr(counter_module, "_load_tokenizer", lambda _source: calls.append("tokenizer"))

    with pytest.raises(MiniMaxM3InputCounterError, match="size limit"):
        MiniMaxM3LocalProviderInputCounter(bundle)
    assert calls == []


@pytest.mark.parametrize(
    ("template", "tokenizer"),
    [(TEMPLATE + b"x", TOKENIZER), (TEMPLATE, TOKENIZER + b"x")],
)
def test_digest_mismatch_is_rejected_before_engine_parse(
    tmp_path,
    monkeypatch,
    template,
    tokenizer,
):
    bundle = tmp_path / "bundle"
    _write_bundle(bundle, template=template, tokenizer=tokenizer, manifest=_manifest())
    calls: list[str] = []
    monkeypatch.setattr(counter_module, "_load_jinja_template", lambda _source: calls.append("jinja"))
    monkeypatch.setattr(counter_module, "_load_tokenizer", lambda _source: calls.append("tokenizer"))

    with pytest.raises(MiniMaxM3InputCounterError, match="digest"):
        MiniMaxM3LocalProviderInputCounter(bundle)
    assert calls == []


def test_invalid_template_utf8_is_rejected_before_engine_parse(tmp_path, monkeypatch):
    bundle = tmp_path / "bundle"
    _write_bundle(bundle, template=b"\xff")
    calls: list[str] = []
    monkeypatch.setattr(counter_module, "_load_jinja_template", lambda _source: calls.append("jinja"))
    monkeypatch.setattr(counter_module, "_load_tokenizer", lambda _source: calls.append("tokenizer"))

    with pytest.raises(MiniMaxM3InputCounterError, match="UTF-8"):
        MiniMaxM3LocalProviderInputCounter(bundle)
    assert calls == []


def test_missing_runtime_dependencies_fail_closed(monkeypatch):
    real_import = builtins.__import__

    def missing_jinja(name, *args, **kwargs):
        if name == "jinja2" or name.startswith("jinja2."):
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing_jinja)
    with pytest.raises(MiniMaxM3InputCounterError, match="Jinja2==3.1.6"):
        counter_module._load_jinja_template("synthetic")

    def missing_tokenizers(name, *args, **kwargs):
        if name == "tokenizers" or name.startswith("tokenizers."):
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing_tokenizers)
    with pytest.raises(MiniMaxM3InputCounterError, match="tokenizers==0.23.1"):
        counter_module._load_tokenizer(b"{}")


def test_count_uses_exact_render_chain_and_returns_bound_evidence(
    tmp_path,
    fake_engines,
    monkeypatch,
    model_request,
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
    counter = MiniMaxM3LocalProviderInputCounter(bundle)

    evidence = counter.count_request(model_request)

    assert render_calls == [model_request]
    assert template.calls == [
        {
            "messages": rendered_messages,
            "tools": None,
            "add_generation_prompt": True,
        }
    ]
    assert "thinking_mode" not in template.calls[0]
    assert tokenizer.calls == [("system text|user text", False)]
    assert evidence.counted_input_tokens == len(FakeEncoding.ids)
    assert evidence.model_request_fingerprint == fingerprint_model_request(model_request)
    assert evidence.provider_id == "minimax"
    assert evidence.model_id == "MiniMax-M3"
    assert evidence.counter_id == counter.counter_id
    assert evidence.token_count_is_exact is True
    serialized = evidence.to_canonical_json()
    assert "system text" not in serialized
    assert "user text" not in serialized
    assert TEMPLATE.decode("utf-8") not in serialized
    assert TOKENIZER.decode("utf-8") not in serialized


@pytest.mark.parametrize(
    "messages",
    [
        [],
        [{"role": "system", "content": "s"}],
        [
            {"role": "system", "content": "s"},
            {"role": "user", "content": "u"},
            {"role": "assistant", "content": "a"},
        ],
        [
            {"role": "user", "content": "s"},
            {"role": "user", "content": "u"},
        ],
        [
            {"role": "system", "content": "s", "extra": "x"},
            {"role": "user", "content": "u"},
        ],
        [
            {"role": "system", "content": "s"},
            {"role": "user", "content": ["u"]},
        ],
    ],
)
def test_message_shape_drift_fails_before_template_and_tokenizer(
    tmp_path,
    fake_engines,
    monkeypatch,
    model_request,
    messages,
):
    bundle = tmp_path / "bundle"
    _write_bundle(bundle)
    template, tokenizer, _ = fake_engines
    monkeypatch.setattr(
        counter_module.external_brain_prompt,
        "render_messages",
        lambda _request: messages,
    )
    counter = MiniMaxM3LocalProviderInputCounter(bundle)

    with pytest.raises(MiniMaxM3InputCounterError):
        counter.count_request(model_request)
    assert template.calls == []
    assert tokenizer.calls == []


def test_request_must_be_exact_model_request(tmp_path, fake_engines, model_request):
    bundle = tmp_path / "bundle"
    _write_bundle(bundle)
    counter = MiniMaxM3LocalProviderInputCounter(bundle)

    class RequestSubclass(ModelRequest):
        pass

    subclass = RequestSubclass(**model_request.__dict__)
    with pytest.raises(MiniMaxM3InputCounterError, match="exact ModelRequest"):
        counter.count_request(subclass)


def test_production_registry_accepts_only_exact_class(tmp_path, fake_engines):
    bundle = tmp_path / "bundle"
    _write_bundle(bundle)
    counter = MiniMaxM3LocalProviderInputCounter(bundle)

    assert budget_module._TRUSTED_LOCAL_COUNTER_TYPES == (
        MiniMaxM3LocalProviderInputCounter,
    )
    assert require_trusted_local_provider_input_counter(counter) is counter

    class CounterSubclass(MiniMaxM3LocalProviderInputCounter):
        pass

    subclass = object.__new__(CounterSubclass)
    with pytest.raises(ProviderInputBudgetError):
        require_trusted_local_provider_input_counter(subclass)
    with pytest.raises(ProviderInputBudgetError):
        require_trusted_local_provider_input_counter(object())


def test_production_module_has_no_network_provider_or_credential_surface():
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
