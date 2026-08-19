import ast
import hashlib
import inspect
import json
from dataclasses import FrozenInstanceError

import pytest

from src.aios_bridge.continuity.dispatch import DispatchActorKind
from src.aios_bridge.continuity.state import BrainOperation, MAX_SERIALIZED_BYTES
from src.aios_bridge.paid_api_grant import (
    MAX_PAID_API_ACTOR_ID_LENGTH,
    MAX_PAID_API_GRANT_ID_LENGTH,
    MAX_PAID_API_INPUT_TOKENS,
    MAX_PAID_API_MODEL_ID_LENGTH,
    MAX_PAID_API_OUTPUT_TOKENS,
    MAX_PAID_API_PROVIDER_ID_LENGTH,
    PAID_API_GRANT_SCHEMA_VERSION,
    PaidApiGrant,
    validate_paid_api_grant_binding,
    validate_paid_api_grant_budget,
)
import src.aios_bridge.paid_api_grant as paid_api_grant_module


def valid_grant_kwargs():
    return {
        "schema_version": PAID_API_GRANT_SCHEMA_VERSION,
        "grant_id": "grant-049:one-shot",
        "task_id": "TASK-049",
        "actor_kind": DispatchActorKind.BRAIN,
        "brain_id": "brain.primary",
        "provider_id": "minimax",
        "model_id": "MiniMax-Text-01",
        "brain_operation": BrainOperation.TASK,
        "authorized_artifact_path": ".ai/tasks/TASK-049.md",
        "authorized_artifact_blob_sha": "a" * 40,
        "max_input_tokens": 4096,
        "max_output_tokens": 1024,
        "max_calls": 1,
        "expires_at_epoch_seconds": 2_000_000_000,
        "workspace_id": "b" * 64,
    }


def make_grant(**overrides):
    values = valid_grant_kwargs()
    values.update(overrides)
    return PaidApiGrant(**values)


def exact_binding_kwargs(grant):
    return {
        "task_id": grant.task_id,
        "workspace_id": grant.workspace_id,
        "brain_id": grant.brain_id,
        "provider_id": grant.provider_id,
        "model_id": grant.model_id,
        "brain_operation": grant.brain_operation,
        "authorized_artifact_path": grant.authorized_artifact_path,
        "authorized_artifact_blob_sha": grant.authorized_artifact_blob_sha,
    }


def test_valid_construction_computes_deterministic_fingerprint():
    grant = make_grant()
    expected_json = json.dumps(
        grant.semantic_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    assert grant.grant_fingerprint == hashlib.sha256(expected_json.encode("utf-8")).hexdigest()
    assert grant.fingerprint() == grant.grant_fingerprint


def test_semantically_identical_grants_have_identical_fingerprints():
    assert make_grant().grant_fingerprint == make_grant().grant_fingerprint


def test_dict_round_trip_is_exact():
    grant = make_grant()
    assert PaidApiGrant.from_dict(grant.to_dict()) == grant


def test_canonical_json_round_trip_is_exact():
    grant = make_grant()
    assert PaidApiGrant.from_json(grant.to_canonical_json()) == grant


def test_strict_utf8_bytes_round_trip_and_invalid_utf8_rejection():
    grant = make_grant(model_id="模型 alpha")
    assert PaidApiGrant.from_json(grant.to_canonical_json().encode("utf-8")) == grant
    with pytest.raises(ValueError):
        PaidApiGrant.from_json(b"\xff")


@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_from_dict_rejects_inexact_field_sets(mutation):
    data = make_grant().to_dict()
    if mutation == "missing":
        data.pop("grant_id")
    else:
        data["unexpected"] = "value"
    with pytest.raises(ValueError):
        PaidApiGrant.from_dict(data)


def test_from_json_rejects_malformed_non_object_and_duplicate_keys():
    with pytest.raises(ValueError):
        PaidApiGrant.from_json("{")
    with pytest.raises(ValueError):
        PaidApiGrant.from_json("[]")
    with pytest.raises(ValueError):
        PaidApiGrant.from_json('{"grant_id":"one","grant_id":"two"}')
    with pytest.raises(ValueError):
        PaidApiGrant.from_json(bytearray(b"{}"))


def test_schema_mismatch_is_rejected():
    with pytest.raises(ValueError):
        make_grant(schema_version="2")


@pytest.mark.parametrize(
    "value",
    [True, 1, "", " padded", "padded ", "UPPER", "bad/character", "a" * (MAX_PAID_API_GRANT_ID_LENGTH + 1)],
)
def test_malformed_grant_id_is_rejected(value):
    with pytest.raises(ValueError):
        make_grant(grant_id=value)


@pytest.mark.parametrize(
    "value",
    [True, 49, "task-049", "TASK-", "X-TASK-049", "TASK-049-X", " TASK-049", "TASK-049 ", "TASK-049\n"],
)
def test_malformed_task_id_is_rejected(value):
    with pytest.raises(ValueError):
        make_grant(task_id=value)


def test_executor_actor_and_unknown_actor_are_rejected():
    with pytest.raises(ValueError):
        make_grant(actor_kind=DispatchActorKind.EXECUTOR)
    with pytest.raises(ValueError):
        make_grant(actor_kind="unknown")


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("brain_id", ""),
        ("brain_id", " brain"),
        ("brain_id", "brain/name"),
        ("brain_id", "brain\nname"),
        ("brain_id", "a" * (MAX_PAID_API_ACTOR_ID_LENGTH + 1)),
        ("provider_id", "provider name"),
        ("provider_id", "provider\x00name"),
        ("provider_id", "a" * (MAX_PAID_API_PROVIDER_ID_LENGTH + 1)),
        ("model_id", ""),
        ("model_id", " model"),
        ("model_id", "model\rname"),
        ("model_id", "a" * (MAX_PAID_API_MODEL_ID_LENGTH + 1)),
    ],
)
def test_malformed_brain_provider_and_model_ids_are_rejected(field_name, value):
    with pytest.raises(ValueError):
        make_grant(**{field_name: value})


def test_invalid_brain_operation_is_rejected():
    with pytest.raises(ValueError):
        make_grant(brain_operation="UNKNOWN")
    with pytest.raises(ValueError):
        make_grant(brain_operation=True)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "tasks/TASK-049.md",
        "/.ai/tasks/TASK-049.md",
        "C:/.ai/tasks/TASK-049.md",
        ".ai\\tasks\\TASK-049.md",
        ".ai/tasks/../TASK-049.md",
        ".ai/./TASK-049.md",
        ".ai//TASK-049.md",
        ".ai/",
        ".ai/tasks/TASK-049.md\n",
    ],
)
def test_noncanonical_artifact_paths_are_rejected(value):
    with pytest.raises(ValueError):
        make_grant(authorized_artifact_path=value)


@pytest.mark.parametrize("value", ["A" * 40, "a" * 39, "a" * 41, "g" * 40, True])
def test_malformed_blob_sha_is_rejected(value):
    with pytest.raises(ValueError):
        make_grant(authorized_artifact_blob_sha=value)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("max_input_tokens", True),
        ("max_input_tokens", 0),
        ("max_input_tokens", -1),
        ("max_input_tokens", MAX_PAID_API_INPUT_TOKENS + 1),
        ("max_output_tokens", True),
        ("max_output_tokens", 0),
        ("max_output_tokens", -1),
        ("max_output_tokens", MAX_PAID_API_OUTPUT_TOKENS + 1),
    ],
)
def test_token_maxima_reject_invalid_values(field_name, value):
    with pytest.raises(ValueError):
        make_grant(**{field_name: value})


@pytest.mark.parametrize("value", [True, 0, 2, 1.0, "1"])
def test_max_calls_accepts_only_exact_integer_one(value):
    with pytest.raises(ValueError):
        make_grant(max_calls=value)
    assert make_grant(max_calls=1).max_calls == 1


@pytest.mark.parametrize("value", [True, 0, -1, 1.0, "2000000000"])
def test_expiry_rejects_non_positive_or_non_integer_values(value):
    with pytest.raises(ValueError):
        make_grant(expires_at_epoch_seconds=value)


@pytest.mark.parametrize("value", ["B" * 64, "b" * 63, "b" * 65, "z" * 64, True])
def test_malformed_workspace_sha_is_rejected(value):
    with pytest.raises(ValueError):
        make_grant(workspace_id=value)


@pytest.mark.parametrize("value", ["0" * 64, "A" * 64, "0" * 63, True])
def test_forged_or_malformed_fingerprint_is_rejected(value):
    with pytest.raises(ValueError):
        make_grant(grant_fingerprint=value)


def test_binding_validator_accepts_only_the_exact_binding():
    grant = make_grant()
    validate_paid_api_grant_binding(grant, **exact_binding_kwargs(grant))


@pytest.mark.parametrize(
    ("field_name", "mismatch"),
    [
        ("task_id", "TASK-050"),
        ("workspace_id", "c" * 64),
        ("brain_id", "brain.secondary"),
        ("provider_id", "other-provider"),
        ("model_id", "other-model"),
        ("brain_operation", BrainOperation.PLAN),
        ("authorized_artifact_path", ".ai/tasks/TASK-050.md"),
        ("authorized_artifact_blob_sha", "c" * 40),
    ],
)
def test_binding_validator_rejects_each_independent_mismatch(field_name, mismatch):
    grant = make_grant()
    bindings = exact_binding_kwargs(grant)
    bindings[field_name] = mismatch
    with pytest.raises(ValueError):
        validate_paid_api_grant_binding(grant, **bindings)


def test_binding_validator_rejects_stale_stored_fingerprint():
    grant = make_grant()
    object.__setattr__(grant, "grant_fingerprint", "0" * 64)
    with pytest.raises(ValueError):
        validate_paid_api_grant_binding(grant, **exact_binding_kwargs(grant))


def test_budget_validator_accepts_zero_and_exact_maxima():
    grant = make_grant()
    validate_paid_api_grant_budget(grant, input_tokens=0, output_tokens=0)
    validate_paid_api_grant_budget(
        grant,
        input_tokens=grant.max_input_tokens,
        output_tokens=grant.max_output_tokens,
    )


@pytest.mark.parametrize(
    ("input_tokens", "output_tokens"),
    [
        (True, 0),
        (0, False),
        (-1, 0),
        (0, -1),
        (4097, 0),
        (0, 1025),
        (1.0, 0),
        (0, "1"),
    ],
)
def test_budget_validator_rejects_invalid_or_over_budget_values(input_tokens, output_tokens):
    with pytest.raises(ValueError):
        validate_paid_api_grant_budget(
            make_grant(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


def test_canonical_serialized_grant_is_bounded():
    serialized = make_grant().to_canonical_json().encode("utf-8")
    assert len(serialized) <= MAX_SERIALIZED_BYTES


def test_oversize_canonical_serialized_grant_fails_closed():
    with pytest.raises(ValueError, match="MAX_SERIALIZED_BYTES"):
        make_grant(authorized_artifact_path=".ai/" + "x" * MAX_SERIALIZED_BYTES)


@pytest.mark.parametrize(
    "secret_field",
    ["api_key", "access_token", "refresh_token", "secret", "authorization_header", "cookie", "credentials"],
)
def test_secret_bearing_fields_are_absent_and_rejected(secret_field):
    grant = make_grant()
    assert secret_field not in grant.to_dict()
    data = grant.to_dict()
    data[secret_field] = "forbidden"
    with pytest.raises(ValueError):
        PaidApiGrant.from_dict(data)


def test_module_has_no_environment_network_subprocess_or_provider_call_imports():
    source = inspect.getsource(paid_api_grant_module)
    tree = ast.parse(source)
    forbidden_roots = {"os", "subprocess", "socket", "urllib", "requests", "httpx", "openai", "anthropic"}
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    assert imported_roots.isdisjoint(forbidden_roots)


def test_paid_api_grant_is_frozen():
    grant = make_grant()
    with pytest.raises(FrozenInstanceError):
        grant.task_id = "TASK-050"


def test_canonical_json_and_fingerprint_ignore_input_dictionary_key_order():
    grant = make_grant()
    reversed_data = dict(reversed(list(grant.to_dict().items())))
    reordered = PaidApiGrant.from_dict(reversed_data)
    assert reordered.fingerprint() == grant.fingerprint()
    assert reordered.to_canonical_json() == grant.to_canonical_json()
