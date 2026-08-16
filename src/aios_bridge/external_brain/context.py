"""Deterministic ContextBuilder and token budgeting for AIOS Bridge External Brain."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
from typing import Any, Sequence

from .budget import ContextBudget, TokenCounter, Utf8ByteConservativeCounter
from .contracts import ContextItem, ContextKind
from .errors import (
    ContractValidationError,
    ContextIntegrityError,
    MandatoryContextBudgetError,
    MissingMandatoryContextError,
    SensitiveContextError,
)

_SENSITIVE_CONTENT_MARKERS = (
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----",
    "-----BEGIN OPENSSH PRIVATE KEY-----",
    "-----BEGIN EC PRIVATE KEY-----",
    "-----BEGIN DSA PRIVATE KEY-----",
    "-----BEGIN ENCRYPTED PRIVATE KEY-----",
)

_KIND_PRECEDENCE: dict[ContextKind, int] = {
    ContextKind.ERROR: 80,
    ContextKind.DIFF: 80,
    ContextKind.TEST: 70,
    ContextKind.SOURCE: 60,
    ContextKind.ARCHITECTURE: 50,
}


def render_context_item(item: ContextItem) -> str:
    """
    Renders a ContextItem into deterministic canonical framing for token counting and transmission.
    Preserves exact content and line endings without modification.
    """
    if item.path:
        return f"<<<CONTEXT kind={item.kind.value} path={item.path}>>>\n{item.content}\n<<<END_CONTEXT>>>"
    else:
        return f"<<<CONTEXT kind={item.kind.value}>>>\n{item.content}\n<<<END_CONTEXT>>>"


def _check_sensitive_context(item: ContextItem) -> None:
    """
    Validates that candidate item does not contain sensitive file paths or secret markers.
    Error messages NEVER echo the candidate content.
    """
    # 1. Path-based rejection
    if item.path:
        norm_path = item.path.replace("\\", "/")
        basename = os.path.basename(norm_path).lower()

        # .env and .env.* (including .env.example, .env.local, etc.)
        if basename == ".env" or basename.startswith(".env.") or basename == ".envrc":
            raise SensitiveContextError(
                f"Sensitive file path rejected (kind={item.kind.value}, path={item.path!r}): matches .env* pattern"
            )

        # Sensitive extensions
        if basename.endswith(".pem") or basename.endswith(".key"):
            raise SensitiveContextError(
                f"Sensitive file path rejected (kind={item.kind.value}, path={item.path!r}): matches sensitive extension (.pem/.key)"
            )

        # SSH key basenames
        if basename in ("id_rsa", "id_ed25519", "id_dsa", "id_ecdsa") or (
            basename.startswith("id_rsa.")
            or basename.startswith("id_ed25519.")
            or basename.startswith("id_dsa.")
            or basename.startswith("id_ecdsa.")
        ):
            raise SensitiveContextError(
                f"Sensitive file path rejected (kind={item.kind.value}, path={item.path!r}): matches SSH private key pattern"
            )

        # Sensitive browser-store basenames
        if basename in ("cookies", "login data", "web data", "cookies-journal", "login data-journal", "web data-journal"):
            raise SensitiveContextError(
                f"Sensitive file path rejected (kind={item.kind.value}, path={item.path!r}): matches sensitive browser store basename"
            )

    # 2. Content-based rejection
    for marker in _SENSITIVE_CONTENT_MARKERS:
        if marker in item.content:
            raise SensitiveContextError(
                f"Secret key marker detected in candidate context (kind={item.kind.value}, path={item.path!r})"
            )


class ContextExclusionReason(str, Enum):
    """Reason for context candidate exclusion."""
    DUPLICATE = "DUPLICATE"
    BUDGET = "BUDGET"


@dataclass(frozen=True)
class ContextExclusion:
    """Immutable audit record for an excluded context candidate."""
    kind: ContextKind
    path: str | None
    content_sha256: str
    counted_tokens: int
    reason: ContextExclusionReason

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ContextKind):
            try:
                object.__setattr__(self, "kind", ContextKind(self.kind))
            except Exception as e:
                raise ContractValidationError(f"Invalid ContextKind: {self.kind}") from e

        if not isinstance(self.reason, ContextExclusionReason):
            try:
                object.__setattr__(self, "reason", ContextExclusionReason(self.reason))
            except Exception as e:
                raise ContractValidationError(f"Invalid ContextExclusionReason: {self.reason}") from e

        if not isinstance(self.content_sha256, str) or len(self.content_sha256) != 64:
            raise ContractValidationError(
                f"content_sha256 must be a 64-character hex string, got: {self.content_sha256!r}"
            )

        if isinstance(self.counted_tokens, bool) or not isinstance(self.counted_tokens, int) or self.counted_tokens < 0:
            raise ContractValidationError(
                f"counted_tokens must be a non-negative integer, got: {self.counted_tokens!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Deterministic JSON-serializable dictionary representation."""
        return {
            "kind": self.kind.value,
            "path": self.path,
            "content_sha256": self.content_sha256,
            "counted_tokens": self.counted_tokens,
            "reason": self.reason.value,
        }


@dataclass(frozen=True)
class ContextBuildResult:
    """Immutable result of deterministic context building and token budgeting."""
    selected: tuple[ContextItem, ...]
    excluded: tuple[ContextExclusion, ...]
    counted_tokens: int
    max_context_tokens: int
    protocol_reserve_tokens: int
    counter_id: str
    token_count_is_exact: bool
    context_fingerprint: str

    def __post_init__(self) -> None:
        if not isinstance(self.selected, tuple):
            if isinstance(self.selected, Sequence):
                object.__setattr__(self, "selected", tuple(self.selected))
            else:
                raise ContractValidationError("selected must be a sequence of ContextItem")

        for item in self.selected:
            if not isinstance(item, ContextItem):
                raise ContractValidationError(f"All selected items must be ContextItem instances, got: {type(item)}")

        if not isinstance(self.excluded, tuple):
            if isinstance(self.excluded, Sequence):
                object.__setattr__(self, "excluded", tuple(self.excluded))
            else:
                raise ContractValidationError("excluded must be a sequence of ContextExclusion")

        for exc in self.excluded:
            if not isinstance(exc, ContextExclusion):
                raise ContractValidationError(f"All excluded items must be ContextExclusion instances, got: {type(exc)}")

        if isinstance(self.counted_tokens, bool) or not isinstance(self.counted_tokens, int) or self.counted_tokens < 0:
            raise ContractValidationError(
                f"counted_tokens must be a non-negative integer, got: {self.counted_tokens!r}"
            )

        if isinstance(self.max_context_tokens, bool) or not isinstance(self.max_context_tokens, int) or self.max_context_tokens <= 0:
            raise ContractValidationError(
                f"max_context_tokens must be a positive integer, got: {self.max_context_tokens!r}"
            )

        if isinstance(self.protocol_reserve_tokens, bool) or not isinstance(self.protocol_reserve_tokens, int) or self.protocol_reserve_tokens < 0:
            raise ContractValidationError(
                f"protocol_reserve_tokens must be a non-negative integer, got: {self.protocol_reserve_tokens!r}"
            )

        if not self.counter_id or not isinstance(self.counter_id, str):
            raise ContractValidationError("counter_id must be a non-empty string")

        if not isinstance(self.token_count_is_exact, bool):
            raise ContractValidationError("token_count_is_exact must be a boolean")

        if not isinstance(self.context_fingerprint, str) or len(self.context_fingerprint) != 64:
            raise ContractValidationError(
                f"context_fingerprint must be a 64-character hex string, got: {self.context_fingerprint!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Deterministic JSON-serializable dictionary representation."""
        return {
            "selected": [item.to_dict() for item in self.selected],
            "excluded": [exc.to_dict() for exc in self.excluded],
            "counted_tokens": self.counted_tokens,
            "max_context_tokens": self.max_context_tokens,
            "protocol_reserve_tokens": self.protocol_reserve_tokens,
            "counter_id": self.counter_id,
            "token_count_is_exact": self.token_count_is_exact,
            "context_fingerprint": self.context_fingerprint,
        }


class ContextBuilder:
    """
    Deterministic selector and token budgeter for External Brain context candidates.
    Pure component: selects only from explicit candidates without repository discovery.
    """

    def __init__(self, token_counter: TokenCounter | None = None) -> None:
        self._counter = token_counter if token_counter is not None else Utf8ByteConservativeCounter()

    def _count(self, text: str) -> int:
        """Invokes token counter and strictly validates returned integer count."""
        count = self._counter.count(text)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ContractValidationError(
                f"TokenCounter {self._counter.counter_id!r} returned invalid count: {count!r}"
            )
        return count

    def build(
        self,
        candidates: Sequence[ContextItem],
        budget: ContextBudget,
    ) -> ContextBuildResult:
        """
        Builds a deterministic bounded context bundle from explicit candidate items.
        """
        if not isinstance(budget, ContextBudget):
            raise ContractValidationError(f"budget must be a ContextBudget instance, got: {type(budget)}")

        if not isinstance(candidates, Sequence):
            raise ContractValidationError(f"candidates must be a sequence of ContextItem, got: {type(candidates)}")

        # 1. Validate safety & integrity for all candidates
        verified_candidates: list[tuple[ContextItem, str]] = []
        for item in candidates:
            if not isinstance(item, ContextItem):
                raise ContractValidationError(f"Candidate item must be ContextItem, got: {type(item)}")

            _check_sensitive_context(item)

            computed_sha = hashlib.sha256(item.content.encode("utf-8")).hexdigest()
            if item.content_sha256 is not None:
                if item.content_sha256.lower() != computed_sha.lower():
                    raise ContextIntegrityError(
                        f"Content SHA-256 mismatch for item (kind={item.kind.value}, path={item.path!r}): "
                        f"expected {item.content_sha256}, computed {computed_sha}"
                    )
            verified_candidates.append((item, computed_sha))

        # 2. Deterministic exact deduplication
        # Sort candidates deterministically before dedupe to guarantee order-independence
        sorted_for_dedupe = sorted(
            verified_candidates,
            key=lambda t: (-t[0].priority, t[0].kind.value, t[0].path or "", t[1]),
        )

        seen_identities: set[tuple[ContextKind, str, str]] = set()
        unique_candidates: list[tuple[ContextItem, str]] = []
        excluded_duplicates: list[ContextExclusion] = []

        for item, sha in sorted_for_dedupe:
            identity = (item.kind, item.path or "", sha)
            if identity in seen_identities:
                rendered = render_context_item(item)
                token_count = self._count(rendered)
                excluded_duplicates.append(
                    ContextExclusion(
                        kind=item.kind,
                        path=item.path,
                        content_sha256=sha,
                        counted_tokens=token_count,
                        reason=ContextExclusionReason.DUPLICATE,
                    )
                )
            else:
                seen_identities.add(identity)
                unique_candidates.append((item, sha))

        # 3. Partition into Mandatory (TASK, CONTRACT) and Optional
        task_items = [t for t in unique_candidates if t[0].kind == ContextKind.TASK]
        contract_items = [t for t in unique_candidates if t[0].kind == ContextKind.CONTRACT]
        optional_items = [
            t
            for t in unique_candidates
            if t[0].kind not in (ContextKind.TASK, ContextKind.CONTRACT)
        ]

        # 4. Enforce mandatory TASK requirement
        if not task_items:
            raise MissingMandatoryContextError("No TASK context item provided in candidates")

        # 5. Sort mandatory items deterministically
        task_items.sort(key=lambda t: (-t[0].priority, t[0].path or "", t[1]))
        contract_items.sort(key=lambda t: (-t[0].priority, t[0].path or "", t[1]))

        # 6. Evaluate mandatory budget
        selected_items: list[ContextItem] = []
        total_counted_tokens = 0

        for item, sha in task_items + contract_items:
            rendered = render_context_item(item)
            tokens = self._count(rendered)
            selected_items.append(item)
            total_counted_tokens += tokens

        if total_counted_tokens > budget.available_context_tokens:
            raise MandatoryContextBudgetError(
                f"Mandatory context tokens ({total_counted_tokens}) exceed available budget "
                f"({budget.available_context_tokens})"
            )

        # 7. Sort optional candidates deterministically
        optional_items.sort(
            key=lambda t: (
                -t[0].priority,
                -_KIND_PRECEDENCE.get(t[0].kind, 0),
                t[0].path or "",
                t[1],
            )
        )

        # 8. Atomic greedy selection for optional candidates
        excluded_budget: list[ContextExclusion] = []
        for item, sha in optional_items:
            rendered = render_context_item(item)
            tokens = self._count(rendered)
            if total_counted_tokens + tokens <= budget.available_context_tokens:
                selected_items.append(item)
                total_counted_tokens += tokens
            else:
                excluded_budget.append(
                    ContextExclusion(
                        kind=item.kind,
                        path=item.path,
                        content_sha256=sha,
                        counted_tokens=tokens,
                        reason=ContextExclusionReason.BUDGET,
                    )
                )

        # 9. Deterministic exclusions ordering
        all_exclusions = excluded_duplicates + excluded_budget
        all_exclusions.sort(
            key=lambda exc: (
                exc.reason.value,
                -exc.counted_tokens,
                exc.kind.value,
                exc.path or "",
                exc.content_sha256,
            )
        )

        # 10. Compute Context Fingerprint
        fingerprint_payload = {
            "selected": [
                {
                    "kind": item.kind.value,
                    "path": item.path,
                    "priority": item.priority,
                    "content_sha256": hashlib.sha256(item.content.encode("utf-8")).hexdigest(),
                }
                for item in selected_items
            ],
            "max_context_tokens": budget.max_context_tokens,
            "protocol_reserve_tokens": budget.protocol_reserve_tokens,
            "counter_id": self._counter.counter_id,
            "token_count_is_exact": self._counter.is_exact,
        }
        fingerprint_str = json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":"))
        context_fingerprint = hashlib.sha256(fingerprint_str.encode("utf-8")).hexdigest()

        return ContextBuildResult(
            selected=tuple(selected_items),
            excluded=tuple(all_exclusions),
            counted_tokens=total_counted_tokens,
            max_context_tokens=budget.max_context_tokens,
            protocol_reserve_tokens=budget.protocol_reserve_tokens,
            counter_id=self._counter.counter_id,
            token_count_is_exact=self._counter.is_exact,
            context_fingerprint=context_fingerprint,
        )
