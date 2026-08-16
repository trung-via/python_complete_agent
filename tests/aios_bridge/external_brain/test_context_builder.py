"""Tests for ContextBuilder, ContextExclusion, ContextBuildResult, and safety gates."""
from __future__ import annotations

import hashlib
import pytest

from src.aios_bridge.external_brain import (
    ContextBudget,
    ContextBuilder,
    ContextExclusionReason,
    ContextIntegrityError,
    ContextItem,
    ContextKind,
    ContractValidationError,
    MandatoryContextBudgetError,
    MissingMandatoryContextError,
    SensitiveContextError,
    render_context_item,
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class FakeExactWordCounter:
    """Deterministic word counter for easy token-math in tests."""

    @property
    def counter_id(self) -> str:
        return "fake-word-counter-v1"

    @property
    def is_exact(self) -> bool:
        return True

    def count(self, text: str) -> int:
        return len(text.split())


class InvalidReturnCounter:
    """Invalid counter returning negative or bool."""

    @property
    def counter_id(self) -> str:
        return "invalid-counter"

    @property
    def is_exact(self) -> bool:
        return False

    def count(self, text: str) -> int:
        return -5


def test_canonical_context_rendering():
    """render_context_item includes kind, path when present, and unmodified content."""
    item_with_path = ContextItem(
        kind=ContextKind.SOURCE,
        content="def foo():\n    return 42\n",
        path="src/foo.py",
    )
    rendered = render_context_item(item_with_path)
    assert rendered == "<<<CONTEXT kind=SOURCE path=src/foo.py>>>\ndef foo():\n    return 42\n\n<<<END_CONTEXT>>>"

    item_without_path = ContextItem(
        kind=ContextKind.TASK,
        content="Implement feature X",
        path=None,
    )
    rendered_no_path = render_context_item(item_without_path)
    assert rendered_no_path == "<<<CONTEXT kind=TASK>>>\nImplement feature X\n<<<END_CONTEXT>>>"


def test_integrity_verification_sha_matching_and_mismatch():
    """Valid SHA-256 is accepted; mismatched SHA-256 raises ContextIntegrityError."""
    builder = ContextBuilder()
    budget = ContextBudget(max_context_tokens=1000)

    content = "Task instruction content"
    valid_sha = _sha(content)
    item_ok = ContextItem(kind=ContextKind.TASK, content=content, content_sha256=valid_sha)

    result = builder.build([item_ok], budget)
    assert len(result.selected) == 1

    # Case-insensitive SHA hex match
    item_upper_sha = ContextItem(kind=ContextKind.TASK, content=content, content_sha256=valid_sha.upper())
    result_upper = builder.build([item_upper_sha], budget)
    assert len(result_upper.selected) == 1

    # Mismatched SHA
    bad_sha = "0" * 64
    item_bad = ContextItem(kind=ContextKind.TASK, content=content, content_sha256=bad_sha)
    with pytest.raises(ContextIntegrityError, match="Content SHA-256 mismatch"):
        builder.build([item_bad], budget)


def test_sensitive_context_safety_gate_path_rejections():
    """Sensitive file paths (.env*, .pem, .key, id_rsa*, Cookies, etc.) are rejected without echoing content."""
    builder = ContextBuilder()
    budget = ContextBudget(max_context_tokens=1000)

    secret_content = "SUPER_SECRET_TOKEN=xyz123"

    sensitive_paths = [
        ".env",
        ".env.local",
        ".env.production",
        ".env.example",  # Explicitly rejected in V1
        "config/.env.test",
        "certs/server.pem",
        "keys/private.key",
        "ssh/id_rsa",
        "ssh/id_rsa.pub",
        "ssh/id_ed25519",
        "ssh/id_ed25519.pub",
        "profile/Cookies",
        "profile/cookies",
        "profile/Login Data",
        "profile/Web Data",
    ]

    for path in sensitive_paths:
        item = ContextItem(kind=ContextKind.SOURCE, content=secret_content, path=path)
        with pytest.raises(SensitiveContextError) as exc_info:
            builder.build([item], budget)
        # Verify secret content is NOT echoed in exception message
        assert secret_content not in str(exc_info.value)
        assert "Sensitive file path rejected" in str(exc_info.value)


def test_sensitive_context_safety_gate_content_rejections():
    """Private key markers inside content are rejected even in ordinary paths."""
    builder = ContextBuilder()
    budget = ContextBudget(max_context_tokens=1000)

    markers = [
        "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASC...",
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...",
        "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAA...",
        "-----BEGIN EC PRIVATE KEY-----\nMHcCAQEEI...",
    ]

    for content in markers:
        item = ContextItem(kind=ContextKind.SOURCE, content=content, path="src/helpers.py")
        with pytest.raises(SensitiveContextError) as exc_info:
            builder.build([item], budget)
        # Verify private key text is NOT echoed in exception message
        assert "MIIE" not in str(exc_info.value)
        assert "Secret key marker detected" in str(exc_info.value)


def test_missing_mandatory_task_error():
    """At least one TASK context item is required."""
    builder = ContextBuilder()
    budget = ContextBudget(max_context_tokens=1000)

    item_src = ContextItem(kind=ContextKind.SOURCE, content="print('hello')", path="src/main.py")
    with pytest.raises(MissingMandatoryContextError, match="No TASK context item provided"):
        builder.build([item_src], budget)


def test_contract_is_mandatory_when_supplied():
    """CONTRACT items are mandatory alongside TASK items."""
    builder = ContextBuilder()
    budget = ContextBudget(max_context_tokens=1000)

    item_task = ContextItem(kind=ContextKind.TASK, content="Task description", priority=10)
    item_contract = ContextItem(kind=ContextKind.CONTRACT, content="Contract rules", priority=5)
    item_src = ContextItem(kind=ContextKind.SOURCE, content="Source code", priority=100)

    result = builder.build([item_src, item_contract, item_task], budget)
    # TASK first, CONTRACT second, then optional SOURCE
    assert len(result.selected) == 3
    assert result.selected[0].kind == ContextKind.TASK
    assert result.selected[1].kind == ContextKind.CONTRACT
    assert result.selected[2].kind == ContextKind.SOURCE


def test_mandatory_context_overflow_fails_closed():
    """If mandatory items exceed budget, builder raises MandatoryContextBudgetError and does not truncate."""
    counter = FakeExactWordCounter()
    builder = ContextBuilder(token_counter=counter)
    # Available budget: 5 words
    budget = ContextBudget(max_context_tokens=5)

    item_task = ContextItem(kind=ContextKind.TASK, content="This task instruction contains way too many words to fit")
    with pytest.raises(MandatoryContextBudgetError, match="Mandatory context tokens .* exceed available budget"):
        builder.build([item_task], budget)


def test_exact_deduplication_collapses_duplicates_and_audits():
    """Exact identical items (kind, path, content) collapse into one and record DUPLICATE exclusions."""
    counter = FakeExactWordCounter()
    builder = ContextBuilder(token_counter=counter)
    budget = ContextBudget(max_context_tokens=1000)

    item_task = ContextItem(kind=ContextKind.TASK, content="Task 1")
    item1 = ContextItem(kind=ContextKind.SOURCE, content="common code", path="src/util.py", priority=10)
    item2 = ContextItem(kind=ContextKind.SOURCE, content="common code", path="src/util.py", priority=5)

    result = builder.build([item_task, item1, item2], budget)
    assert len(result.selected) == 2
    assert result.selected[1].priority == 10  # Highest priority chosen as representative

    assert len(result.excluded) == 1
    assert result.excluded[0].reason == ContextExclusionReason.DUPLICATE
    assert result.excluded[0].path == "src/util.py"
    assert result.excluded[0].kind == ContextKind.SOURCE
    assert result.excluded[0].counted_tokens > 0


def test_different_path_or_kind_does_not_dedupe():
    """Identical content at different paths or under different kinds are distinct candidates."""
    counter = FakeExactWordCounter()
    builder = ContextBuilder(token_counter=counter)
    budget = ContextBudget(max_context_tokens=1000)

    item_task = ContextItem(kind=ContextKind.TASK, content="Task 1")
    item_src1 = ContextItem(kind=ContextKind.SOURCE, content="common code", path="src/a.py")
    item_src2 = ContextItem(kind=ContextKind.SOURCE, content="common code", path="src/b.py")
    item_test = ContextItem(kind=ContextKind.TEST, content="common code", path="src/a.py")

    result = builder.build([item_task, item_src1, item_src2, item_test], budget)
    assert len(result.selected) == 4
    assert len(result.excluded) == 0


def test_input_permutation_invariance_and_stable_fingerprint():
    """Different input orderings of the same candidates yield identical selected ordering and fingerprint."""
    counter = FakeExactWordCounter()
    builder = ContextBuilder(token_counter=counter)
    budget = ContextBudget(max_context_tokens=1000, protocol_reserve_tokens=50)

    t = ContextItem(kind=ContextKind.TASK, content="Task 1", priority=1)
    c = ContextItem(kind=ContextKind.CONTRACT, content="Contract 1", priority=2)
    s1 = ContextItem(kind=ContextKind.SOURCE, content="Source 1", path="src/a.py", priority=5)
    s2 = ContextItem(kind=ContextKind.SOURCE, content="Source 2", path="src/b.py", priority=5)
    e = ContextItem(kind=ContextKind.ERROR, content="Error 1", priority=5)

    list1 = [t, c, s1, s2, e]
    list2 = [e, s2, t, s1, c]
    list3 = [s1, e, c, t, s2]

    res1 = builder.build(list1, budget)
    res2 = builder.build(list2, budget)
    res3 = builder.build(list3, budget)

    assert res1.selected == res2.selected == res3.selected
    assert res1.context_fingerprint == res2.context_fingerprint == res3.context_fingerprint
    assert res1.counted_tokens == res2.counted_tokens == res3.counted_tokens


def test_optional_ranking_order_priority_kind_path_digest():
    """Optional candidates rank by: 1) priority, 2) kind precedence, 3) path, 4) digest."""
    counter = FakeExactWordCounter()
    builder = ContextBuilder(token_counter=counter)
    budget = ContextBudget(max_context_tokens=1000)

    task = ContextItem(kind=ContextKind.TASK, content="Task")

    # High priority beats higher kind precedence
    arch_high_prio = ContextItem(kind=ContextKind.ARCHITECTURE, content="Arch high prio", priority=100)
    error_low_prio = ContextItem(kind=ContextKind.ERROR, content="Error low prio", priority=10)

    # Equal priority: ERROR (80) > TEST (70) > SOURCE (60)
    err_equal = ContextItem(kind=ContextKind.ERROR, content="Err", priority=50, path="b.py")
    test_equal = ContextItem(kind=ContextKind.TEST, content="Test", priority=50, path="a.py")
    src_equal = ContextItem(kind=ContextKind.SOURCE, content="Src", priority=50, path="a.py")

    # Equal priority & kind: path resolves
    src_path_a = ContextItem(kind=ContextKind.SOURCE, content="Src A", priority=20, path="a.py")
    src_path_b = ContextItem(kind=ContextKind.SOURCE, content="Src B", priority=20, path="b.py")

    # Equal priority, kind & path: digest resolves
    src_digest1 = ContextItem(kind=ContextKind.SOURCE, content="Content A", priority=10, path="c.py")
    src_digest2 = ContextItem(kind=ContextKind.SOURCE, content="Content B", priority=10, path="c.py")

    candidates = [
        src_digest2,
        src_path_b,
        error_low_prio,
        src_equal,
        src_digest1,
        test_equal,
        task,
        arch_high_prio,
        err_equal,
        src_path_a,
    ]

    result = builder.build(candidates, budget)
    selected_kinds_and_content = [(item.kind, item.content) for item in result.selected]

    assert selected_kinds_and_content[0] == (ContextKind.TASK, "Task")
    assert selected_kinds_and_content[1] == (ContextKind.ARCHITECTURE, "Arch high prio")  # prio 100
    assert selected_kinds_and_content[2] == (ContextKind.ERROR, "Err")                    # prio 50, kind 80
    assert selected_kinds_and_content[3] == (ContextKind.TEST, "Test")                   # prio 50, kind 70
    assert selected_kinds_and_content[4] == (ContextKind.SOURCE, "Src")                  # prio 50, kind 60
    assert selected_kinds_and_content[5] == (ContextKind.SOURCE, "Src A")                # prio 20, path a.py
    assert selected_kinds_and_content[6] == (ContextKind.SOURCE, "Src B")                # prio 20, path b.py
    assert selected_kinds_and_content[7] == (ContextKind.ERROR, "Error low prio")        # prio 10, kind 80


def test_atomic_greedy_budget_selection_and_skipping():
    """Oversized optional item receives BUDGET exclusion; later smaller item still gets selected."""
    counter = FakeExactWordCounter()
    builder = ContextBuilder(token_counter=counter)

    # Task item takes 3 words (rendered: <<<CONTEXT kind=TASK>>>\nTask\n<<<END_CONTEXT>>> = 3 words)
    task = ContextItem(kind=ContextKind.TASK, content="Task")
    task_tokens = counter.count(render_context_item(task))

    # Optional 1: huge item (100 words)
    huge_opt = ContextItem(kind=ContextKind.ERROR, content=" ".join(["error"] * 100), priority=10)
    huge_tokens = counter.count(render_context_item(huge_opt))

    # Optional 2: tiny item (1 word)
    tiny_opt = ContextItem(kind=ContextKind.SOURCE, content="tiny", priority=5)
    tiny_tokens = counter.count(render_context_item(tiny_opt))

    # Set budget to accommodate task + tiny_opt, but not huge_opt
    budget = ContextBudget(max_context_tokens=task_tokens + tiny_tokens)

    result = builder.build([task, huge_opt, tiny_opt], budget)

    # Selected: task + tiny_opt
    assert len(result.selected) == 2
    assert result.selected[0].content == "Task"
    assert result.selected[1].content == "tiny"

    # Excluded: huge_opt with reason=BUDGET
    assert len(result.excluded) == 1
    assert result.excluded[0].reason == ContextExclusionReason.BUDGET
    assert result.excluded[0].counted_tokens == huge_tokens

    # Verify counted_tokens exactly matches sum of selected
    assert result.counted_tokens == task_tokens + tiny_tokens
    assert result.counted_tokens <= budget.available_context_tokens


def test_context_build_result_immutability_and_audit():
    """ContextBuildResult and ContextExclusion are immutable; exclusions have no content."""
    counter = FakeExactWordCounter()
    builder = ContextBuilder(token_counter=counter)
    budget = ContextBudget(max_context_tokens=1000)

    task = ContextItem(kind=ContextKind.TASK, content="Task")
    res = builder.build([task], budget)

    assert isinstance(res.selected, tuple)
    assert isinstance(res.excluded, tuple)
    assert res.counter_id == "fake-word-counter-v1"
    assert res.token_count_is_exact is True
    assert len(res.context_fingerprint) == 64

    d = res.to_dict()
    assert "selected" in d
    assert "excluded" in d
    assert d["context_fingerprint"] == res.context_fingerprint


def test_invalid_counter_returns_rejected():
    """TokenCounter returning negative or boolean value raises ContractValidationError."""
    builder = ContextBuilder(token_counter=InvalidReturnCounter())
    budget = ContextBudget(max_context_tokens=1000)
    task = ContextItem(kind=ContextKind.TASK, content="Task")

    with pytest.raises(ContractValidationError, match="returned invalid count"):
        builder.build([task], budget)


def test_fingerprint_sensitivity():
    """Fingerprint changes when selected content, budget, or counter identity changes."""
    builder = ContextBuilder()
    b1 = ContextBudget(max_context_tokens=1000, protocol_reserve_tokens=100)
    b2 = ContextBudget(max_context_tokens=2000, protocol_reserve_tokens=100)

    task1 = ContextItem(kind=ContextKind.TASK, content="Task Alpha")
    task2 = ContextItem(kind=ContextKind.TASK, content="Task Beta")

    r1 = builder.build([task1], b1)
    r2 = builder.build([task2], b1)
    r3 = builder.build([task1], b2)

    # Content change -> different fingerprint
    assert r1.context_fingerprint != r2.context_fingerprint

    # Budget change -> different fingerprint
    assert r1.context_fingerprint != r3.context_fingerprint

    # Counter change -> different fingerprint
    exact_builder = ContextBuilder(token_counter=FakeExactWordCounter())
    r4 = exact_builder.build([task1], b1)
    assert r1.context_fingerprint != r4.context_fingerprint


def test_builder_exactness_metadata():
    """ContextBuildResult correctly reflects exactness of injected counter."""
    # Default counter is conservative (is_exact=False)
    default_builder = ContextBuilder()
    task = ContextItem(kind=ContextKind.TASK, content="Task")
    b = ContextBudget(max_context_tokens=1000)
    r_default = default_builder.build([task], b)
    assert r_default.token_count_is_exact is False
    assert r_default.counter_id == "utf8-byte-conservative-v1"

    # Injected exact counter
    exact_builder = ContextBuilder(token_counter=FakeExactWordCounter())
    r_exact = exact_builder.build([task], b)
    assert r_exact.token_count_is_exact is True
    assert r_exact.counter_id == "fake-word-counter-v1"


def test_context_builder_purity_no_filesystem_side_effects(monkeypatch):
    """ContextBuilder is a pure in-memory selector that does not touch the filesystem or crawl files."""
    def forbidden_open(*args, **kwargs):
        raise AssertionError("ContextBuilder must not read or open filesystem files!")

    monkeypatch.setattr("builtins.open", forbidden_open)

    builder = ContextBuilder()
    task = ContextItem(kind=ContextKind.TASK, content="Task content", path="some/path.py")
    source = ContextItem(kind=ContextKind.SOURCE, content="Source content", path="other/path.py")
    budget = ContextBudget(max_context_tokens=1000)

    result = builder.build([task, source], budget)
    assert len(result.selected) == 2


def test_normalized_path_separator_ranking_tie_breaks():
    """Candidates with mixed forward and backslash path separators rank by normalized '/' path order."""
    counter = FakeExactWordCounter()
    builder = ContextBuilder(token_counter=counter)
    budget = ContextBudget(max_context_tokens=1000)

    # 1. Mandatory TASK items with mixed separators: task/a.md before task\b.md
    task_b = ContextItem(kind=ContextKind.TASK, content="Task B", path=r"tasks\b.md", priority=10)
    task_a = ContextItem(kind=ContextKind.TASK, content="Task A", path="tasks/a.md", priority=10)

    # 2. Mandatory CONTRACT items with mixed separators: contract/a.md before contract\b.md
    contract_b = ContextItem(kind=ContextKind.CONTRACT, content="Contract B", path=r"contracts\b.md", priority=5)
    contract_a = ContextItem(kind=ContextKind.CONTRACT, content="Contract A", path="contracts/a.md", priority=5)

    # 3. Optional SOURCE items with mixed separators: src/a.py before src\b.py
    src_b = ContextItem(kind=ContextKind.SOURCE, content="Source B", path=r"src\b.py", priority=1)
    src_a = ContextItem(kind=ContextKind.SOURCE, content="Source A", path="src/a.py", priority=1)

    result = builder.build([task_b, contract_b, src_b, task_a, contract_a, src_a], budget)

    paths = [item.path for item in result.selected]
    assert paths == [
        "tasks/a.md",
        r"tasks\b.md",
        "contracts/a.md",
        r"contracts\b.md",
        "src/a.py",
        r"src\b.py",
    ]


def test_atomic_budget_selection_follows_normalized_path_tie_break():
    """Atomic budget selection chooses the higher normalized-path candidate when budget only fits one."""
    counter = FakeExactWordCounter()
    builder = ContextBuilder(token_counter=counter)

    task = ContextItem(kind=ContextKind.TASK, content="Task")
    task_tokens = counter.count(render_context_item(task))

    # Two equal-priority optional items of identical token size
    # src/a.py vs src\b.py (normalized: src/a.py < src/b.py)
    src_b = ContextItem(kind=ContextKind.SOURCE, content="Source content same size", path=r"src\b.py", priority=10)
    src_a = ContextItem(kind=ContextKind.SOURCE, content="Source content same size", path="src/a.py", priority=10)
    item_tokens = counter.count(render_context_item(src_a))

    # Budget fits task + exactly 1 item
    budget = ContextBudget(max_context_tokens=task_tokens + item_tokens)

    # Regardless of input order:
    res1 = builder.build([task, src_b, src_a], budget)
    res2 = builder.build([task, src_a, src_b], budget)

    # src/a.py is selected as the winner, src\b.py is excluded for budget
    assert len(res1.selected) == 2
    assert res1.selected[1].path == "src/a.py"
    assert len(res1.excluded) == 1
    assert res1.excluded[0].path == r"src\b.py"
    assert res1.excluded[0].reason == ContextExclusionReason.BUDGET

    assert res1.selected == res2.selected
    assert res1.context_fingerprint == res2.context_fingerprint


