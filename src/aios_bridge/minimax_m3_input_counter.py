"""Exact local provider-input counting for the pinned MiniMax-M3 assets."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import TYPE_CHECKING, Any

from .external_brain.contracts import ModelRequest
from .external_brain import prompt as external_brain_prompt
from .minimax_m3_proof_lock import (
    MiniMaxM3ProofLock,
    PROVIDER_ID,
    MODEL_ID,
    SOURCE_REPOSITORY,
    SOURCE_REVISION,
    CHAT_TEMPLATE_PATH,
    TOKENIZER_PATH,
)

if TYPE_CHECKING:
    from .provider_input_budget import ProviderInputCountEvidence


ASSET_MANIFEST_PATH = "asset-manifest.json"
ASSET_MANIFEST_SCHEMA_VERSION = "1"

MAX_ASSET_MANIFEST_BYTES = 64 * 1024
MAX_CHAT_TEMPLATE_BYTES = 1024 * 1024
MAX_TOKENIZER_BYTES = 32 * 1024 * 1024

_REQUIRED_BUNDLE_FILES = frozenset(
    {ASSET_MANIFEST_PATH, CHAT_TEMPLATE_PATH, TOKENIZER_PATH}
)
_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "source_repository",
        "source_revision",
        "chat_template_path",
        "chat_template_sha256",
        "tokenizer_path",
        "tokenizer_sha256",
    }
)
_LOWERCASE_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class MiniMaxM3InputCounterError(ValueError):
    """Raised when the pinned local counter cannot prove an exact count."""


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise MiniMaxM3InputCounterError("asset manifest contains duplicate keys")
        result[key] = value
    return result


def _read_bounded_regular_file(
    asset_root: Path,
    filename: str,
    maximum_bytes: int,
) -> bytes:
    candidate = asset_root / filename
    try:
        if candidate.is_symlink():
            raise MiniMaxM3InputCounterError(
                f"{filename} must be a non-symlink regular file"
            )
        file_status = candidate.stat(follow_symlinks=False)
    except MiniMaxM3InputCounterError:
        raise
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise MiniMaxM3InputCounterError(f"required asset file is missing: {filename}") from exc
    except OSError as exc:
        raise MiniMaxM3InputCounterError(f"cannot inspect required asset file: {filename}") from exc

    if not stat.S_ISREG(file_status.st_mode):
        raise MiniMaxM3InputCounterError(
            f"{filename} must be a non-symlink regular file"
        )
    if file_status.st_size > maximum_bytes:
        raise MiniMaxM3InputCounterError(f"{filename} exceeds its size limit")

    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise MiniMaxM3InputCounterError(f"cannot resolve required asset file: {filename}") from exc
    if resolved.parent != asset_root:
        raise MiniMaxM3InputCounterError(f"asset path escapes the supplied directory: {filename}")

    try:
        content = candidate.read_bytes()
    except OSError as exc:
        raise MiniMaxM3InputCounterError(f"cannot read required asset file: {filename}") from exc
    if len(content) > maximum_bytes:
        raise MiniMaxM3InputCounterError(f"{filename} exceeds its size limit")
    return content


def _parse_manifest(manifest_bytes: bytes) -> dict[str, object]:
    try:
        manifest_text = manifest_bytes.decode("utf-8", errors="strict")
        value = json.loads(
            manifest_text,
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except MiniMaxM3InputCounterError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MiniMaxM3InputCounterError("asset manifest must be valid UTF-8 JSON") from exc

    if type(value) is not dict or set(value) != _MANIFEST_FIELDS:
        raise MiniMaxM3InputCounterError("asset manifest must contain the exact required fields")
    return value


def _validate_manifest(
    manifest: dict[str, object],
    proof_lock: MiniMaxM3ProofLock,
) -> tuple[str, str]:
    if type(proof_lock) is not MiniMaxM3ProofLock:
        raise MiniMaxM3InputCounterError("proof_lock must be an exact MiniMaxM3ProofLock instance")

    exact_values: tuple[tuple[str, object], ...] = (
        ("schema_version", ASSET_MANIFEST_SCHEMA_VERSION),
        ("source_repository", SOURCE_REPOSITORY),
        ("source_revision", SOURCE_REVISION),
        ("chat_template_path", CHAT_TEMPLATE_PATH),
        ("tokenizer_path", TOKENIZER_PATH),
    )
    for field_name, expected in exact_values:
        if type(manifest[field_name]) is not type(expected) or manifest[field_name] != expected:
            raise MiniMaxM3InputCounterError(
                f"asset manifest has an invalid {field_name}"
            )

    template_sha = manifest["chat_template_sha256"]
    tokenizer_sha = manifest["tokenizer_sha256"]
    for field_name, value in (
        ("chat_template_sha256", template_sha),
        ("tokenizer_sha256", tokenizer_sha),
    ):
        if type(value) is not str or _LOWERCASE_SHA256.fullmatch(value) is None:
            raise MiniMaxM3InputCounterError(
                f"asset manifest has an invalid {field_name}"
            )

    # Bind manifest directly to canonical proof lock
    if template_sha != proof_lock.chat_template_sha256:
        raise MiniMaxM3InputCounterError(
            "manifest chat_template_sha256 does not match proof lock"
        )
    if tokenizer_sha != proof_lock.tokenizer_sha256:
        raise MiniMaxM3InputCounterError(
            "manifest tokenizer_sha256 does not match proof lock"
        )

    return template_sha, tokenizer_sha


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _load_validated_assets(
    asset_directory: str | os.PathLike[str],
    proof_lock: MiniMaxM3ProofLock,
) -> tuple[str, bytes, str, str]:
    if type(proof_lock) is not MiniMaxM3ProofLock:
        raise MiniMaxM3InputCounterError(
            "proof_lock must be an exact MiniMaxM3ProofLock instance"
        )

    try:
        supplied_root = Path(asset_directory)
    except TypeError as exc:
        raise MiniMaxM3InputCounterError("asset_directory must be a local filesystem path") from exc

    try:
        if supplied_root.is_symlink():
            raise MiniMaxM3InputCounterError(
                "asset_directory must be a non-symlink directory"
            )
        root_status = supplied_root.stat(follow_symlinks=False)
        asset_root = supplied_root.resolve(strict=True)
    except MiniMaxM3InputCounterError:
        raise
    except OSError as exc:
        raise MiniMaxM3InputCounterError("asset_directory is not an accessible directory") from exc
    if not stat.S_ISDIR(root_status.st_mode):
        raise MiniMaxM3InputCounterError("asset_directory must be a directory")

    try:
        entries = frozenset(entry.name for entry in asset_root.iterdir())
    except OSError as exc:
        raise MiniMaxM3InputCounterError("cannot inspect asset_directory") from exc
    if entries != _REQUIRED_BUNDLE_FILES:
        raise MiniMaxM3InputCounterError(
            "asset_directory must contain exactly the required bundle files"
        )

    manifest_bytes = _read_bounded_regular_file(
        asset_root,
        ASSET_MANIFEST_PATH,
        MAX_ASSET_MANIFEST_BYTES,
    )
    manifest = _parse_manifest(manifest_bytes)
    template_sha, tokenizer_sha = _validate_manifest(manifest, proof_lock)

    template_bytes = _read_bounded_regular_file(
        asset_root,
        CHAT_TEMPLATE_PATH,
        MAX_CHAT_TEMPLATE_BYTES,
    )
    tokenizer_bytes = _read_bounded_regular_file(
        asset_root,
        TOKENIZER_PATH,
        MAX_TOKENIZER_BYTES,
    )
    actual_template_sha = _sha256(template_bytes)
    actual_tokenizer_sha = _sha256(tokenizer_bytes)

    if actual_template_sha != template_sha:
        raise MiniMaxM3InputCounterError("chat template digest does not match manifest")
    if actual_tokenizer_sha != tokenizer_sha:
        raise MiniMaxM3InputCounterError("tokenizer digest does not match manifest")
    if actual_template_sha != proof_lock.chat_template_sha256:
        raise MiniMaxM3InputCounterError("chat template digest does not match proof lock")
    if actual_tokenizer_sha != proof_lock.tokenizer_sha256:
        raise MiniMaxM3InputCounterError("tokenizer digest does not match proof lock")

    try:
        template_source = template_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise MiniMaxM3InputCounterError("chat template must be valid UTF-8") from exc
    return template_source, tokenizer_bytes, template_sha, tokenizer_sha


def _template_raise_exception(_message: object = None) -> None:
    raise MiniMaxM3InputCounterError("chat template rejected the render input")


def _load_jinja_template(template_source: str) -> Any:
    try:
        from jinja2 import StrictUndefined
        from jinja2.sandbox import SandboxedEnvironment
        from jinja2.utils import Namespace
    except ImportError as exc:
        raise MiniMaxM3InputCounterError(
            "Jinja2==3.1.6 is required for MiniMax-M3 input counting"
        ) from exc

    try:
        environment = SandboxedEnvironment(
            undefined=StrictUndefined,
            loader=None,
            autoescape=False,
        )
        environment.globals.clear()
        environment.globals.update(
            {
                "namespace": Namespace,
                "raise_exception": _template_raise_exception,
            }
        )
        return environment.from_string(template_source)
    except MiniMaxM3InputCounterError:
        raise
    except Exception as exc:
        raise MiniMaxM3InputCounterError("chat template cannot be compiled safely") from exc


def _load_tokenizer(tokenizer_bytes: bytes) -> Any:
    try:
        from tokenizers import Tokenizer
    except ImportError as exc:
        raise MiniMaxM3InputCounterError(
            "tokenizers==0.23.1 is required for MiniMax-M3 input counting"
        ) from exc

    try:
        tokenizer_source = tokenizer_bytes.decode("utf-8", errors="strict")
        return Tokenizer.from_str(tokenizer_source)
    except Exception as exc:
        raise MiniMaxM3InputCounterError("tokenizer asset cannot be parsed") from exc


def _require_exact_messages(value: object) -> list[dict[str, str]]:
    if type(value) is not list or len(value) != 2:
        raise MiniMaxM3InputCounterError(
            "render_messages must return exactly two messages"
        )
    expected_roles = ("system", "user")
    for index, expected_role in enumerate(expected_roles):
        message = value[index]
        if type(message) is not dict or set(message) != {"role", "content"}:
            raise MiniMaxM3InputCounterError(
                "render_messages returned an invalid message shape"
            )
        if type(message["role"]) is not str or message["role"] != expected_role:
            raise MiniMaxM3InputCounterError(
                "render_messages returned an invalid message role"
            )
        if type(message["content"]) is not str:
            raise MiniMaxM3InputCounterError(
                "render_messages returned non-string message content"
            )
    return value


class MiniMaxM3LocalProviderInputCounter:
    """Trusted local exact counter backed by a validated pinned asset bundle and canonical proof lock."""

    def __init__(
        self,
        asset_directory: str | os.PathLike[str],
        proof_lock: MiniMaxM3ProofLock,
    ) -> None:
        if type(proof_lock) is not MiniMaxM3ProofLock:
            raise MiniMaxM3InputCounterError(
                "proof_lock must be an exact MiniMaxM3ProofLock instance"
            )
        (
            template_source,
            tokenizer_bytes,
            template_sha,
            tokenizer_sha,
        ) = _load_validated_assets(asset_directory, proof_lock)
        self._proof_lock = proof_lock
        self._template = _load_jinja_template(template_source)
        self._tokenizer = _load_tokenizer(tokenizer_bytes)
        self._counter_id = (
            f"minimax-m3-local:{SOURCE_REVISION}:{template_sha}:{tokenizer_sha}"
        )

    @property
    def provider_id(self) -> str:
        return PROVIDER_ID

    @property
    def model_id(self) -> str:
        return MODEL_ID

    @property
    def counter_id(self) -> str:
        return self._counter_id

    @property
    def proof_lock(self) -> MiniMaxM3ProofLock:
        return self._proof_lock

    @property
    def is_exact(self) -> bool:
        return True

    def count_request(self, request: ModelRequest) -> ProviderInputCountEvidence:
        if type(request) is not ModelRequest:
            raise MiniMaxM3InputCounterError("request must be an exact ModelRequest")

        messages = _require_exact_messages(
            external_brain_prompt.render_messages(request)
        )
        try:
            rendered_prompt = self._template.render(
                messages=messages,
                tools=None,
                add_generation_prompt=True,
            )
        except MiniMaxM3InputCounterError:
            raise
        except Exception as exc:
            raise MiniMaxM3InputCounterError("chat template rendering failed") from exc
        if type(rendered_prompt) is not str:
            raise MiniMaxM3InputCounterError("chat template must render an exact string")

        try:
            encoding = self._tokenizer.encode(
                rendered_prompt,
                add_special_tokens=False,
            )
            counted_input_tokens = len(encoding.ids)
        except Exception as exc:
            raise MiniMaxM3InputCounterError("local tokenizer encoding failed") from exc

        from .provider_input_budget import (
            ProviderInputCountEvidence,
            fingerprint_model_request,
        )

        return ProviderInputCountEvidence(
            provider_id=PROVIDER_ID,
            model_id=MODEL_ID,
            model_request_fingerprint=fingerprint_model_request(request),
            counted_input_tokens=counted_input_tokens,
            counter_id=self._counter_id,
            token_count_is_exact=True,
        )


__all__ = [
    "MiniMaxM3InputCounterError",
    "MiniMaxM3LocalProviderInputCounter",
    "PROVIDER_ID",
    "MODEL_ID",
    "SOURCE_REPOSITORY",
    "SOURCE_REVISION",
    "CHAT_TEMPLATE_PATH",
    "TOKENIZER_PATH",
    "ASSET_MANIFEST_PATH",
    "ASSET_MANIFEST_SCHEMA_VERSION",
]
