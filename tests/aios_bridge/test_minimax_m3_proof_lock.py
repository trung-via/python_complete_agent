"""Tests for MiniMaxM3ProofLock and canonical path validation (TASK-059 / M11.3B)."""
import hashlib
import json
import pytest

from src.aios_bridge.minimax_m3_proof_lock import (
    MiniMaxM3ProofLock,
    MiniMaxM3ProofLockError,
    validate_canonical_ai_proof_lock_path,
    SCHEMA_VERSION,
    PROVIDER_ID,
    MODEL_ID,
    CREDENTIAL_ENV_NAME,
    SOURCE_REPOSITORY,
    SOURCE_REVISION,
    CHAT_TEMPLATE_PATH,
    TOKENIZER_PATH,
    JINJA2_VERSION,
    TOKENIZERS_VERSION,
    REQUESTS_VERSION,
    ALLOWED_MINIMAX_HOST,
    ALLOWED_MINIMAX_ENDPOINTS,
    MAX_PROOF_LOCK_BYTES,
)


def _valid_lock_dict() -> dict[str, str]:
    return {
        "schema_version": "1",
        "provider_id": "minimax",
        "model_id": "MiniMax-M3",
        "endpoint_url": "https://api.minimax.io/v1/text/chatcompletion_v2",
        "credential_env_name": "MINIMAX_API_KEY",
        "source_repository": "MiniMaxAI/MiniMax-M3",
        "source_revision": "3a41b311ffa5719cef48fed3974ccf2cc03733ea",
        "chat_template_path": "chat_template.jinja",
        "chat_template_sha256": "a" * 64,
        "tokenizer_path": "tokenizer.json",
        "tokenizer_sha256": "b" * 64,
        "jinja2_version": "3.1.6",
        "tokenizers_version": "0.23.1",
        "requests_version": "2.32.3",
    }


class TestMiniMaxM3ProofLockValidation:
    def test_valid_lock_construction(self):
        data = _valid_lock_dict()
        lock = MiniMaxM3ProofLock.from_dict(data)
        assert lock.schema_version == SCHEMA_VERSION
        assert lock.provider_id == PROVIDER_ID
        assert lock.model_id == MODEL_ID
        assert lock.endpoint_url == "https://api.minimax.io/v1/text/chatcompletion_v2"
        assert lock.credential_env_name == CREDENTIAL_ENV_NAME
        assert lock.source_repository == SOURCE_REPOSITORY
        assert lock.source_revision == SOURCE_REVISION
        assert lock.chat_template_path == CHAT_TEMPLATE_PATH
        assert lock.chat_template_sha256 == "a" * 64
        assert lock.tokenizer_path == TOKENIZER_PATH
        assert lock.tokenizer_sha256 == "b" * 64
        assert lock.jinja2_version == JINJA2_VERSION
        assert lock.tokenizers_version == TOKENIZERS_VERSION
        assert lock.requests_version == REQUESTS_VERSION

    def test_valid_json_roundtrip(self):
        data = _valid_lock_dict()
        lock = MiniMaxM3ProofLock.from_dict(data)
        json_str = lock.to_canonical_json()
        lock2 = MiniMaxM3ProofLock.from_json(json_str)
        assert lock == lock2
        assert lock.fingerprint() == lock2.fingerprint()

    def test_alternate_allowed_endpoint(self):
        data = _valid_lock_dict()
        data["endpoint_url"] = "https://api.minimax.io/v1/chat/completions"
        lock = MiniMaxM3ProofLock.from_dict(data)
        assert lock.endpoint_url == "https://api.minimax.io/v1/chat/completions"

    def test_rejects_unallowed_endpoint(self):
        data = _valid_lock_dict()
        data["endpoint_url"] = "https://api.minimax.io/v1/other/endpoint"
        with pytest.raises(MiniMaxM3ProofLockError, match="endpoint_url must be a canonical HTTPS URL in allowlist"):
            MiniMaxM3ProofLock.from_dict(data)

    def test_rejects_http_or_wrong_host(self):
        data = _valid_lock_dict()
        data["endpoint_url"] = "http://api.minimax.io/v1/text/chatcompletion_v2"
        with pytest.raises(MiniMaxM3ProofLockError):
            MiniMaxM3ProofLock.from_dict(data)

        data = _valid_lock_dict()
        data["endpoint_url"] = "https://evil.com/v1/text/chatcompletion_v2"
        with pytest.raises(MiniMaxM3ProofLockError):
            MiniMaxM3ProofLock.from_dict(data)

    def test_rejects_query_fragment_userinfo(self):
        for bad_url in [
            "https://api.minimax.io/v1/text/chatcompletion_v2?key=val",
            "https://api.minimax.io/v1/text/chatcompletion_v2#frag",
            "https://user:pass@api.minimax.io/v1/text/chatcompletion_v2",
        ]:
            data = _valid_lock_dict()
            data["endpoint_url"] = bad_url
            with pytest.raises(MiniMaxM3ProofLockError):
                MiniMaxM3ProofLock.from_dict(data)

    def test_rejects_invalid_schema_version(self):
        data = _valid_lock_dict()
        data["schema_version"] = "2"
        with pytest.raises(MiniMaxM3ProofLockError, match="schema_version"):
            MiniMaxM3ProofLock.from_dict(data)

    def test_rejects_invalid_provider_model(self):
        data = _valid_lock_dict()
        data["provider_id"] = "openai"
        with pytest.raises(MiniMaxM3ProofLockError, match="provider_id"):
            MiniMaxM3ProofLock.from_dict(data)

        data = _valid_lock_dict()
        data["model_id"] = "gpt-4"
        with pytest.raises(MiniMaxM3ProofLockError, match="model_id"):
            MiniMaxM3ProofLock.from_dict(data)

    def test_rejects_invalid_source_revision(self):
        data = _valid_lock_dict()
        data["source_revision"] = "badrevision"
        with pytest.raises(MiniMaxM3ProofLockError, match="source_revision"):
            MiniMaxM3ProofLock.from_dict(data)

    def test_rejects_invalid_dependency_versions(self):
        for field, bad_val in [
            ("jinja2_version", "3.1.5"),
            ("tokenizers_version", "0.23.0"),
            ("requests_version", "2.32.2"),
        ]:
            data = _valid_lock_dict()
            data[field] = bad_val
            with pytest.raises(MiniMaxM3ProofLockError, match=field):
                MiniMaxM3ProofLock.from_dict(data)

    def test_rejects_invalid_sha256_digests(self):
        for field in ["chat_template_sha256", "tokenizer_sha256"]:
            data = _valid_lock_dict()
            data[field] = "A" * 64  # uppercase
            with pytest.raises(MiniMaxM3ProofLockError):
                MiniMaxM3ProofLock.from_dict(data)

            data = _valid_lock_dict()
            data[field] = "abc"  # short
            with pytest.raises(MiniMaxM3ProofLockError):
                MiniMaxM3ProofLock.from_dict(data)

    def test_rejects_duplicate_json_keys(self):
        raw = '{"schema_version":"1","schema_version":"1"}'
        with pytest.raises(MiniMaxM3ProofLockError, match="duplicate"):
            MiniMaxM3ProofLock.from_json(raw)

    def test_rejects_missing_or_extra_keys(self):
        data = _valid_lock_dict()
        del data["requests_version"]
        with pytest.raises(MiniMaxM3ProofLockError):
            MiniMaxM3ProofLock.from_dict(data)

        data = _valid_lock_dict()
        data["extra_field"] = "bad"
        with pytest.raises(MiniMaxM3ProofLockError):
            MiniMaxM3ProofLock.from_dict(data)

    def test_rejects_non_string_types(self):
        data = _valid_lock_dict()
        data["schema_version"] = 1  # int instead of str
        with pytest.raises(MiniMaxM3ProofLockError):
            MiniMaxM3ProofLock.from_dict(data)

    def test_fingerprint_deterministic(self):
        data = _valid_lock_dict()
        lock = MiniMaxM3ProofLock.from_dict(data)
        fp1 = lock.fingerprint()
        fp2 = lock.fingerprint()
        assert fp1 == fp2
        assert len(fp1) == 64


class TestValidateCanonicalAiProofLockPath:
    def test_valid_paths(self):
        assert validate_canonical_ai_proof_lock_path(".ai/context/proof_lock.json") == ".ai/context/proof_lock.json"
        assert validate_canonical_ai_proof_lock_path(".ai/tasks/lock.json") == ".ai/tasks/lock.json"

    def test_rejects_non_ai_prefix(self):
        with pytest.raises(MiniMaxM3ProofLockError, match=r"must be under the canonical '\.ai/' directory"):
            validate_canonical_ai_proof_lock_path("context/proof_lock.json")

    def test_rejects_backslashes_and_drive(self):
        with pytest.raises(MiniMaxM3ProofLockError, match="normalized repository-relative"):
            validate_canonical_ai_proof_lock_path(r".ai\context\proof_lock.json")

        with pytest.raises(MiniMaxM3ProofLockError, match="normalized repository-relative"):
            validate_canonical_ai_proof_lock_path("C:.ai/context/proof_lock.json")

    def test_rejects_leading_slash(self):
        with pytest.raises(MiniMaxM3ProofLockError, match="normalized repository-relative"):
            validate_canonical_ai_proof_lock_path("/.ai/context/proof_lock.json")

    def test_rejects_traversal(self):
        for bad in [".ai/../proof_lock.json", ".ai/./proof_lock.json", ".ai//proof_lock.json"]:
            with pytest.raises(MiniMaxM3ProofLockError, match="invalid, empty, or traversal"):
                validate_canonical_ai_proof_lock_path(bad)

    def test_rejects_bare_dir_or_empty(self):
        with pytest.raises(MiniMaxM3ProofLockError):
            validate_canonical_ai_proof_lock_path(".ai")
        with pytest.raises(MiniMaxM3ProofLockError):
            validate_canonical_ai_proof_lock_path("")
        with pytest.raises(MiniMaxM3ProofLockError):
            validate_canonical_ai_proof_lock_path(None)
