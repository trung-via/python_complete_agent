"""Offline regressions for the attach-only P8 Real Case Evidence Bundle carrier."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

import pytest

from src.product_intelligence.tiktok_pdp_case_bundle import (
    AUTHORIZED_PDP_URL,
    AUTHORIZED_SOURCE_ID,
    BLOCKED_OR_CHALLENGE,
    CASE_BUNDLE_SCRIPT,
    CLASSIFICATION,
    CONTEXT_ID,
    EPISTEMIC_BOUNDARY,
    IDENTITY_MISMATCH,
    LISTING_UNAVAILABLE,
    LOGIN_GATE,
    MALFORMED_PROJECTION,
    MANIFEST_FILENAME,
    POST_MANIFEST_WRITE_FAILURE,
    PROJECTION_FILENAME,
    SANITATION_POLICY,
    SCREENSHOT_FILENAME,
    TikTokPdpCaseBundleArtifactExistsError,
    TikTokPdpCaseBundleError,
    TikTokPdpCaseBundleJobRootError,
    TikTokPdpCaseBundleOutcome,
    run_tiktok_pdp_case_bundle,
)

OBSERVED_AT = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
ENDPOINT = "http://operator.invalid:9222/devtools/browser/case-bundle-secret"
OBSERVED_URL = f"https://shop.tiktok.com/vn/pdp/den-led-cam-bien-chuyen-dong-3-che-do-sang-sac-usb-c/{AUTHORIZED_SOURCE_ID}"
PNG_PAYLOAD = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"


@pytest.fixture
def external_job_root():
    with tempfile.TemporaryDirectory(prefix="task263-bundle-case-", ignore_cleanup_errors=True) as directory:
        yield Path(directory).resolve()


@pytest.fixture
def tmp_path(external_job_root):
    return external_job_root


def _sample_record(ordinal: int = 1, tag: str = "h1", text: str = "Test Title", **overrides):
    rec = {
        "ordinal": ordinal,
        "tag_name": tag,
        "role": "heading",
        "itemprop": "name",
        "data-testid": "product-title",
        "data-e2e": "pdp-title",
        "class_tokens": ["title-text", "header"],
        "section_heading_context": "Product Information",
        "visible_text": text,
        "is_leaf": True,
    }
    rec.update(overrides)
    return rec


def _valid_projection_payload(**overrides):
    payload = {
        "schema_version": 1,
        "observed_url": OBSERVED_URL,
        "page_state": {
            "identity_bound": True,
            "blocked": False,
            "login": False,
            "unavailable": False,
        },
        "truncation": {
            "is_truncated": False,
            "scanned_nodes_truncated": False,
            "records_truncated": False,
            "text_truncated": False,
            "bytes_truncated": False,
            "total_scanned_nodes": 50,
            "total_records": 2,
        },
        "records": [
            _sample_record(1, "h1", "Đèn LED Cảm Biến Chuyển Động"),
            _sample_record(2, "span", "33.600₫", role="", itemprop="price"),
        ],
    }
    payload.update(overrides)
    return payload


class FakeSession:
    def __init__(self, payload=None, png_bytes=PNG_PAYLOAD, evaluate_exc=None, screenshot_exc=None):
        self.payload = payload if payload is not None else _valid_projection_payload()
        self.png_bytes = png_bytes
        self.evaluate_exc = evaluate_exc
        self.screenshot_exc = screenshot_exc
        self.evaluate_calls = []
        self.screenshot_calls = 0

    async def evaluate(self, script: str):
        self.evaluate_calls.append(script)
        if self.evaluate_exc is not None:
            raise self.evaluate_exc
        return self.payload

    async def screenshot(self) -> bytes:
        self.screenshot_calls += 1
        if self.screenshot_exc is not None:
            raise self.screenshot_exc
        return self.png_bytes


class FakeManager:
    def __init__(self, session: FakeSession | None = None, session_exc=None, close_exc=None):
        self.session = session or FakeSession()
        self.session_exc = session_exc
        self.close_exc = close_exc
        self.acquired_run_ids = []
        self.closed_run_ids = []

    async def get_or_create_session(self, run_id: str):
        if self.session_exc is not None:
            raise self.session_exc
        self.acquired_run_ids.append(run_id)
        return self.session

    async def close_session(self, run_id: str):
        self.closed_run_ids.append(run_id)
        if self.close_exc is not None:
            raise self.close_exc


@pytest.mark.asyncio
async def test_case_bundle_success_flow(tmp_path):
    fake_session = FakeSession()
    fake_manager = FakeManager(session=fake_session)
    job_root = tmp_path / "bundle-run-001"

    outcome = await run_tiktok_pdp_case_bundle(
        job_root=job_root,
        cdp_endpoint=ENDPOINT,
        clock=lambda: OBSERVED_AT,
        manager_factory=lambda cdp_endpoint: fake_manager,
    )

    assert isinstance(outcome, TikTokPdpCaseBundleOutcome)
    assert outcome.manifest_path == job_root / MANIFEST_FILENAME
    assert outcome.projection_path == job_root / PROJECTION_FILENAME
    assert outcome.screenshot_path == job_root / SCREENSHOT_FILENAME

    # Exactly three files created
    files = sorted(p.name for p in job_root.iterdir())
    assert files == [
        "p8-real-case-full-page-v1.png",
        "p8-real-case-manifest-v1.json",
        "p8-real-case-page-projection-v1.json",
    ]

    # Verify manifest contents
    manifest_bytes = outcome.manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    assert manifest["schema_version"] == 1
    assert manifest["bundle_version"] == 1
    assert manifest["classification"] == CLASSIFICATION
    assert manifest["context_id"] == CONTEXT_ID
    assert manifest["source_product_id"] == AUTHORIZED_SOURCE_ID
    assert manifest["requested_url"] == AUTHORIZED_PDP_URL
    assert manifest["stable_listing_reference"] == AUTHORIZED_PDP_URL
    assert manifest["execution_owner"] == "HUMAN_OPERATOR"
    assert manifest["review_status"] == "HUMAN_REVIEW_REQUIRED"
    assert manifest["screenshot_review_status"] == "HUMAN_REVIEW_REQUIRED"
    assert manifest["epistemic_boundary"] == EPISTEMIC_BOUNDARY
    assert manifest["sanitation_policy"] == SANITATION_POLICY

    # Verify projection hash and byte count
    proj_bytes = outcome.projection_path.read_bytes()
    expected_proj_hash = hashlib.sha256(proj_bytes).hexdigest().upper()
    assert manifest["artifacts"]["page_projection"]["sha256"] == expected_proj_hash
    assert manifest["artifacts"]["page_projection"]["byte_count"] == len(proj_bytes)

    # Verify screenshot hash and byte count
    shot_bytes = outcome.screenshot_path.read_bytes()
    expected_shot_hash = hashlib.sha256(shot_bytes).hexdigest().upper()
    assert manifest["artifacts"]["screenshot"]["sha256"] == expected_shot_hash
    assert manifest["artifacts"]["screenshot"]["byte_count"] == len(shot_bytes)
    assert shot_bytes == PNG_PAYLOAD

    # Verify session lifecycle
    assert len(fake_session.evaluate_calls) == 1
    assert fake_session.evaluate_calls[0] == CASE_BUNDLE_SCRIPT
    assert fake_session.screenshot_calls == 1
    assert fake_manager.acquired_run_ids == [f"human-case-bundle:{CONTEXT_ID}"]
    assert fake_manager.closed_run_ids == [f"human-case-bundle:{CONTEXT_ID}"]

    # Verify document presentation
    doc = outcome.to_document()
    assert doc["bundle"]["status"] == "SUCCESS"
    assert doc["bundle"]["classification"] == CLASSIFICATION


@pytest.mark.asyncio
async def test_job_root_inside_repository_fails_without_consuming():
    repo_root = Path(__file__).resolve().parents[2]
    with pytest.raises(TikTokPdpCaseBundleJobRootError) as exc_info:
        await run_tiktok_pdp_case_bundle(
            job_root=repo_root / "inside_repo",
            cdp_endpoint=ENDPOINT,
        )
    assert "must be outside the Git repository" in str(exc_info.value)


@pytest.mark.asyncio
async def test_empty_job_root_or_cdp_fails_without_consuming(tmp_path):
    with pytest.raises(TikTokPdpCaseBundleJobRootError):
        await run_tiktok_pdp_case_bundle(job_root="", cdp_endpoint=ENDPOINT)

    with pytest.raises(TikTokPdpCaseBundleError):
        await run_tiktok_pdp_case_bundle(
            job_root=tmp_path / "valid_root",
            cdp_endpoint="   ",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "existing_name",
    [MANIFEST_FILENAME, PROJECTION_FILENAME, SCREENSHOT_FILENAME],
)
async def test_existing_artifact_in_job_root_fails_before_execution(tmp_path, existing_name):
    job_root = tmp_path / "existing-root"
    job_root.mkdir(parents=True, exist_ok=True)
    (job_root / existing_name).write_text("existing", encoding="utf-8")

    called = False

    def factory(cdp_endpoint):
        nonlocal called
        called = True
        return FakeManager()

    with pytest.raises(TikTokPdpCaseBundleArtifactExistsError):
        await run_tiktok_pdp_case_bundle(
            job_root=job_root,
            cdp_endpoint=ENDPOINT,
            manager_factory=factory,
        )
    assert not called


@pytest.mark.asyncio
async def test_session_acquisition_failure_does_not_consume(tmp_path):
    job_root = tmp_path / "session_fail_root"
    fake_manager = FakeManager(session_exc=RuntimeError("CDP connection refused"))

    with pytest.raises(TikTokPdpCaseBundleError) as exc_info:
        await run_tiktok_pdp_case_bundle(
            job_root=job_root,
            cdp_endpoint=ENDPOINT,
            manager_factory=lambda cdp_endpoint: fake_manager,
        )
    assert "could not be borrowed" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert "CDP connection refused" in str(exc_info.value.__cause__)
    assert not job_root.exists() or list(job_root.iterdir()) == []


@pytest.mark.asyncio
async def test_evaluate_failure_does_not_consume(tmp_path):
    job_root = tmp_path / "eval_fail_root"
    fake_session = FakeSession(evaluate_exc=RuntimeError("JS execution crashed"))
    fake_manager = FakeManager(session=fake_session)

    with pytest.raises(TikTokPdpCaseBundleError) as exc_info:
        await run_tiktok_pdp_case_bundle(
            job_root=job_root,
            cdp_endpoint=ENDPOINT,
            manager_factory=lambda cdp_endpoint: fake_manager,
        )
    assert "bounded page projection evaluation failed" in str(exc_info.value)
    assert not (job_root / MANIFEST_FILENAME).exists()
    assert fake_session.screenshot_calls == 0
    assert fake_manager.closed_run_ids == [f"human-case-bundle:{CONTEXT_ID}"]


@pytest.mark.asyncio
async def test_screenshot_failure_does_not_consume(tmp_path):
    job_root = tmp_path / "shot_fail_root"
    fake_session = FakeSession(screenshot_exc=RuntimeError("Screenshot crashed"))
    fake_manager = FakeManager(session=fake_session)

    with pytest.raises(TikTokPdpCaseBundleError) as exc_info:
        await run_tiktok_pdp_case_bundle(
            job_root=job_root,
            cdp_endpoint=ENDPOINT,
            manager_factory=lambda cdp_endpoint: fake_manager,
        )
    assert "full-page screenshot capture failed" in str(exc_info.value)
    assert not (job_root / MANIFEST_FILENAME).exists()


@pytest.mark.asyncio
async def test_invalid_screenshot_bytes_fail_without_consuming(tmp_path):
    job_root = tmp_path / "invalid_shot_root"
    fake_session = FakeSession(png_bytes=b"not-a-png-file")
    fake_manager = FakeManager(session=fake_session)

    with pytest.raises(TikTokPdpCaseBundleError) as exc_info:
        await run_tiktok_pdp_case_bundle(
            job_root=job_root,
            cdp_endpoint=ENDPOINT,
            manager_factory=lambda cdp_endpoint: fake_manager,
        )
    assert "not a valid PNG image" in str(exc_info.value)
    assert not (job_root / MANIFEST_FILENAME).exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("flag", "error_code"),
    [
        ("blocked", BLOCKED_OR_CHALLENGE),
        ("login", LOGIN_GATE),
        ("unavailable", LISTING_UNAVAILABLE),
    ],
)
async def test_page_state_failures_fail_closed_without_consuming(tmp_path, flag, error_code):
    job_root = tmp_path / f"state_{flag}_root"
    payload = _valid_projection_payload()
    payload["page_state"][flag] = True

    fake_session = FakeSession(payload=payload)
    fake_manager = FakeManager(session=fake_session)

    with pytest.raises(TikTokPdpCaseBundleError) as exc_info:
        await run_tiktok_pdp_case_bundle(
            job_root=job_root,
            cdp_endpoint=ENDPOINT,
            manager_factory=lambda cdp_endpoint: fake_manager,
        )
    assert str(exc_info.value) == error_code
    assert not (job_root / MANIFEST_FILENAME).exists()
    assert fake_session.screenshot_calls == 0
    assert fake_manager.closed_run_ids == [f"human-case-bundle:{CONTEXT_ID}"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_url",
    [
        "https://shop.tiktok.com/vn/pdp/other-slug/9999999999999999999",
        "https://evil.com/vn/pdp/item/1731381331718341815",
        "https://shop.tiktok.com/us/pdp/item/1731381331718341815",
    ],
)
async def test_identity_mismatch_fails_closed_without_consuming(tmp_path, bad_url):
    job_root = tmp_path / "bad_url_root"
    payload = _valid_projection_payload(observed_url=bad_url)
    fake_session = FakeSession(payload=payload)
    fake_manager = FakeManager(session=fake_session)

    with pytest.raises(TikTokPdpCaseBundleError) as exc_info:
        await run_tiktok_pdp_case_bundle(
            job_root=job_root,
            cdp_endpoint=ENDPOINT,
            manager_factory=lambda cdp_endpoint: fake_manager,
        )
    assert str(exc_info.value) == IDENTITY_MISMATCH
    assert not (job_root / MANIFEST_FILENAME).exists()
    assert fake_session.screenshot_calls == 0
    assert fake_manager.closed_run_ids == [f"human-case-bundle:{CONTEXT_ID}"]


@pytest.mark.asyncio
async def test_malformed_projection_fails_closed_without_consuming(tmp_path):
    job_root = tmp_path / "malformed_root"
    fake_session = FakeSession(payload={"invalid": "payload"})
    fake_manager = FakeManager(session=fake_session)

    with pytest.raises(TikTokPdpCaseBundleError) as exc_info:
        await run_tiktok_pdp_case_bundle(
            job_root=job_root,
            cdp_endpoint=ENDPOINT,
            manager_factory=lambda cdp_endpoint: fake_manager,
        )
    assert str(exc_info.value) == MALFORMED_PROJECTION
    assert not (job_root / MANIFEST_FILENAME).exists()
    assert fake_session.screenshot_calls == 0
    assert fake_manager.closed_run_ids == [f"human-case-bundle:{CONTEXT_ID}"]


@pytest.mark.asyncio
async def test_manifest_first_consumption_and_post_manifest_failure(tmp_path, monkeypatch):
    job_root = tmp_path / "post_manifest_fail_root"
    fake_session = FakeSession()
    fake_manager = FakeManager(session=fake_session)

    original_open = Path.open

    def failing_open(self, mode="r", *args, **kwargs):
        if self.name == PROJECTION_FILENAME and "x" in mode:
            raise PermissionError("Simulated disk error writing projection")
        return original_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)

    with pytest.raises(TikTokPdpCaseBundleError) as exc_info:
        await run_tiktok_pdp_case_bundle(
            job_root=job_root,
            cdp_endpoint=ENDPOINT,
            manager_factory=lambda cdp_endpoint: fake_manager,
        )
    assert str(exc_info.value) == POST_MANIFEST_WRITE_FAILURE

    # Manifest was created! The attempt is consumed!
    assert (job_root / MANIFEST_FILENAME).exists()
    assert not (job_root / PROJECTION_FILENAME).exists()

    # Second invocation fails because manifest already exists
    with pytest.raises(TikTokPdpCaseBundleArtifactExistsError):
        await run_tiktok_pdp_case_bundle(
            job_root=job_root,
            cdp_endpoint=ENDPOINT,
            manager_factory=lambda cdp_endpoint: fake_manager,
        )


@pytest.mark.asyncio
async def test_byte_truncation_enforces_limit(tmp_path):
    job_root = tmp_path / "truncation_root"
    # Create large number of records near legal limits to exceed 256 KiB
    large_records = [
        _sample_record(
            ordinal=i + 1,
            tag="div",
            text=f"Item visible description {i:03d} " + "T" * 125,
            role="region_" + "r" * 70,
            itemprop="itemprop_" + "p" * 68,
            class_tokens=["tok1_" + "a" * 38, "tok2_" + "b" * 38, "tok3_" + "c" * 38, "tok4_" + "d" * 38],
            section_heading_context="Section Heading " + "H" * 60,
            **{
                "data-testid": "testid_" + "t" * 70,
                "data-e2e": "e2e_" + "e" * 70,
            },
        )
        for i in range(500)
    ]
    payload = _valid_projection_payload(
        records=large_records,
        truncation={
            "is_truncated": False,
            "scanned_nodes_truncated": False,
            "records_truncated": False,
            "text_truncated": False,
            "bytes_truncated": False,
            "total_scanned_nodes": 500,
            "total_records": 500,
        },
    )
    premise_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    assert len(premise_bytes) > 256 * 1024

    fake_session = FakeSession(payload=payload)
    fake_manager = FakeManager(session=fake_session)

    outcome = await run_tiktok_pdp_case_bundle(
        job_root=job_root,
        cdp_endpoint=ENDPOINT,
        manager_factory=lambda cdp_endpoint: fake_manager,
    )

    proj_bytes = outcome.projection_path.read_bytes()
    assert len(proj_bytes) <= 256 * 1024
    proj_doc = json.loads(proj_bytes)
    assert proj_doc["truncation"]["is_truncated"] is True
    assert proj_doc["truncation"]["bytes_truncated"] is True


def test_ast_no_forbidden_intelligence_or_decision_imports():
    source_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "product_intelligence"
        / "tiktok_pdp_case_bundle.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    forbidden_symbols = {
        "ProductCandidateSnapshot",
        "SignalEvidence",
        "TikTokAffiliateEvidenceProfile",
        "ValueOfInformationPlan",
        "MarketTestEvidenceProfile",
        "CommerceDecisionLoopCase",
        "WinningProductScorer",
        "RankedCandidate",
    }

    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported_names.add(alias.name)

    intersection = imported_names.intersection(forbidden_symbols)
    assert not intersection, f"Forbidden symbols imported: {intersection}"


def test_case_bundle_consumes_canonical_shared_bounded_dom_scope_resolver():
    """Prove case bundle consumes the canonical shared BOUNDED_TIKTOK_PDP_DOM_SCOPE_RESOLUTION resolver."""
    from src.product_intelligence.tiktok_pdp_dom_scope import (
        BOUNDED_TIKTOK_PDP_DOM_SCOPE_RESOLUTION,
        TIKTOK_PDP_DOM_SCOPE_JS,
    )

    source = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "product_intelligence"
        / "tiktok_pdp_case_bundle.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        node.module: [alias.name for alias in node.names]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "src.product_intelligence.tiktok_pdp_dom_scope" in imports
    assert "TIKTOK_PDP_DOM_SCOPE_JS" in imports["src.product_intelligence.tiktok_pdp_dom_scope"]
    assert TIKTOK_PDP_DOM_SCOPE_JS in CASE_BUNDLE_SCRIPT
    assert "resolveBoundedPdpDomScope()" in CASE_BUNDLE_SCRIPT
    assert "scope.root" in CASE_BUNDLE_SCRIPT
    assert BOUNDED_TIKTOK_PDP_DOM_SCOPE_RESOLUTION == "BOUNDED_TIKTOK_PDP_DOM_SCOPE_RESOLUTION"


def test_case_bundle_script_excludes_account_session_profile_navigation_regions():
    """Prove case bundle projection script deterministically excludes account/session/profile/navigation regions."""
    assert "isExcludedRegion" in CASE_BUNDLE_SCRIPT
    assert "skippedTags" in CASE_BUNDLE_SCRIPT
    for excluded_tag in ("header", "nav", "footer", "aside"):
        assert f"'{excluded_tag}'" in CASE_BUNDLE_SCRIPT or f'"{excluded_tag}"' in CASE_BUNDLE_SCRIPT
    for excluded_role in ("navigation", "banner", "contentinfo"):
        assert f"'{excluded_role}'" in CASE_BUNDLE_SCRIPT or f'"{excluded_role}"' in CASE_BUNDLE_SCRIPT
    for term in ("account", "profile", "session", "user", "avatar", "login"):
        assert term in CASE_BUNDLE_SCRIPT


@pytest.mark.parametrize("tag", ["header", "nav", "footer", "aside", "script", "style"])
def test_validate_record_rejects_navigation_and_header_tags(tag: str):
    """Prove projection record validation rejects non-product navigation/header/script tags."""
    from src.product_intelligence.tiktok_pdp_case_bundle import _validate_record

    rec = _sample_record(1, tag=tag)
    with pytest.raises(TikTokPdpCaseBundleError) as exc_info:
        _validate_record(rec, 1)
    assert str(exc_info.value) == MALFORMED_PROJECTION


def test_projection_validation_accepts_clean_product_records():
    """Prove representative product facts validate cleanly in projection payload."""
    from src.product_intelligence.tiktok_pdp_case_bundle import _validate_projection_payload

    payload = _valid_projection_payload(
        records=[
            _sample_record(1, "h1", "Đèn LED Cảm Biến Chuyển Động", **{"data-testid": "product-title", "itemprop": "name"}),
            _sample_record(2, "span", "33.600₫", role="", itemprop="price"),
            _sample_record(3, "span", "Nhựa ABS cao cấp", section_heading_context="Thông số sản phẩm"),
            _sample_record(4, "span", "Lighting Official Store", section_heading_context="Thông tin người bán", **{"data-testid": "shop-name"}),
            _sample_record(5, "span", "Đổi trả 7 ngày miễn phí", section_heading_context="Dịch vụ người bán"),
            _sample_record(6, "button", "Mua ngay", role="button", **{"data-e2e": "buy-now"}),
        ]
    )
    validated = _validate_projection_payload(payload)
    assert len(validated["records"]) == 6
    assert validated["records"][0]["visible_text"] == "Đèn LED Cảm Biến Chuyển Động"
    assert validated["records"][1]["visible_text"] == "33.600₫"
    assert validated["records"][2]["visible_text"] == "Nhựa ABS cao cấp"
    assert validated["records"][3]["visible_text"] == "Lighting Official Store"
    assert validated["records"][4]["visible_text"] == "Đổi trả 7 ngày miễn phí"
    assert validated["records"][5]["visible_text"] == "Mua ngay"


@pytest.mark.asyncio
async def test_case_bundle_projection_offline_dom_sanitation_and_product_capture(tmp_path):
    """Prove non-product account/profile/navigation text outside admitted product scope cannot enter persisted projection

    while representative title, price, attributes/specification, seller/product-service,
    and other intended product-page observations remain capturable within the bounded projection.
    """
    from playwright.async_api import async_playwright

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="utf-8" />
    <title>Đèn LED Cảm Biến Chuyển Động - TikTok Shop</title>
</head>
<body>
    <!-- Non-product global header and navigation outside admitted product scope -->
    <header class="site-header">
        <nav class="top-nav" role="navigation">
            <a href="/home" class="nav-link">Trang chủ TikTok</a>
            <a href="/explore" class="nav-link">Khám phá sản phẩm</a>
            <a href="/trending" class="nav-link">Xu hướng mua sắm</a>
        </nav>
        <div role="banner" class="user-banner">
            <div class="user-profile" data-testid="user-profile">
                <span class="username">user_super_buyer_99</span>
                <span class="user-info">Hồ sơ cá nhân và tài khoản</span>
                <span class="user-avatar">Ảnh đại diện</span>
            </div>
            <div class="account-session-panel" data-e2e="user-session">
                <span>Phiên đăng nhập: SESSION_SECRET_TOKEN_987</span>
                <a href="/account/settings">Cài đặt tài khoản người dùng</a>
                <a href="/logout">Đăng xuất khỏi hệ thống</a>
            </div>
        </div>
    </header>

    <!-- Non-product sidebar navigation outside admitted product scope -->
    <aside role="navigation" class="account-sidebar">
        <a href="/user/orders">Đơn hàng của tôi</a>
        <a href="/user/coupons">Ví voucher của tôi</a>
        <a href="/user/notifications">Thông báo cá nhân</a>
    </aside>

    <!-- Admitted product scope container -->
    <main id="main-product-area">
        <div data-e2e="pdp-container" data-product-id="{AUTHORIZED_SOURCE_ID}" class="pdp-main-container">
            <!-- Non-product account-like widget nested inside product container to prove isExcludedRegion rejection -->
            <div class="user-account-widget" data-e2e="user-avatar">
                <span>Tài khoản khách hàng VIP nội bộ</span>
            </div>

            <!-- Representative Product Title -->
            <h1 data-testid="product-title" itemprop="name" class="product-title">
                Đèn LED Cảm Biến Chuyển Động 3 Chế Độ Sáng Sạc USB-C
            </h1>

            <!-- Representative Product Price -->
            <div class="product-pricing" data-testid="pdp-price">
                <span itemprop="price" class="current-price">33.600₫</span>
                <del class="original-price">50.000₫</del>
            </div>

            <!-- Representative Product Attributes / Specification -->
            <div class="specs-section">
                <h2 class="specs-heading">Thông số sản phẩm</h2>
                <div class="spec-row" data-testid="spec-material">
                    <span class="spec-name">Chất liệu thân đèn:</span>
                    <span class="spec-value">Nhựa ABS cao cấp</span>
                </div>
                <div class="spec-row" data-testid="spec-port">
                    <span class="spec-name">Cổng sạc nguồn:</span>
                    <span class="spec-value">Type-C tiện lợi</span>
                </div>
                <div class="spec-row" data-testid="spec-modes">
                    <span class="spec-name">Chế độ chiếu sáng:</span>
                    <span class="spec-value">3 chế độ thông minh</span>
                </div>
            </div>

            <!-- Representative Seller / Product-Service -->
            <div class="seller-service-section">
                <h2 class="seller-heading">Thông tin người bán và dịch vụ</h2>
                <div class="shop-badge" data-testid="shop-name">
                    <span class="shop-title">Lighting Official Store</span>
                </div>
                <div class="service-guarantees" data-testid="service-policy">
                    <span class="guarantee-item">Đổi trả 7 ngày miễn phí</span>
                    <span class="warranty-item">Bảo hành chính hãng 12 tháng</span>
                </div>
            </div>

            <!-- Other intended product-page observations (Actions) -->
            <div class="action-buttons">
                <button data-e2e="buy-now" role="button" class="btn-buy">Mua ngay</button>
                <button data-e2e="add-to-cart" role="button" class="btn-cart">Thêm vào giỏ hàng</button>
            </div>
        </div>
    </main>

    <!-- Non-product footer outside admitted product scope -->
    <footer role="contentinfo" class="site-footer">
        <div class="footer-links">
            <span>Chính sách bảo mật người dùng</span>
            <span>Điều khoản dịch vụ tài khoản</span>
            <span>Trung tâm trợ giúp và hỗ trợ</span>
        </div>
    </footer>
</body>
</html>"""

    target_url = AUTHORIZED_PDP_URL
    job_root = tmp_path / "bundle-dom-sanitation-001"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.route(
                "https://shop.tiktok.com/**",
                lambda route: route.fulfill(status=200, content_type="text/html", body=html),
            )
            await page.goto(target_url)

            class _LiveSessionManager:
                def __init__(self, *, cdp_endpoint: str):
                    self.cdp_endpoint = cdp_endpoint
                    self.closed = False

                async def get_or_create_session(self, run_id: str):
                    return page

                async def close_session(self, run_id: str):
                    self.closed = True

            outcome = await run_tiktok_pdp_case_bundle(
                job_root=job_root,
                cdp_endpoint=ENDPOINT,
                clock=lambda: OBSERVED_AT,
                manager_factory=_LiveSessionManager,
            )

            assert isinstance(outcome, TikTokPdpCaseBundleOutcome)
            assert outcome.manifest_path == job_root / MANIFEST_FILENAME
            assert outcome.projection_path == job_root / PROJECTION_FILENAME
            assert outcome.screenshot_path == job_root / SCREENSHOT_FILENAME

            # Exactly three artifacts created in the job root
            files = sorted(p.name for p in job_root.iterdir())
            assert files == [
                "p8-real-case-full-page-v1.png",
                "p8-real-case-manifest-v1.json",
                "p8-real-case-page-projection-v1.json",
            ]

            # Read and parse the persisted projection artifact
            persisted_bytes = outcome.projection_path.read_bytes()
            assert len(persisted_bytes) <= 256 * 1024
            projection_doc = json.loads(persisted_bytes.decode("utf-8"))

            assert projection_doc["schema_version"] == 1
            assert projection_doc["record_type"] == "P8_REAL_CASE_PAGE_PROJECTION"
            assert projection_doc["classification"] == CLASSIFICATION
            assert projection_doc["context_id"] == CONTEXT_ID
            assert projection_doc["source_product_id"] == AUTHORIZED_SOURCE_ID
            assert projection_doc["observed_url"] == AUTHORIZED_PDP_URL

            records = projection_doc["records"]
            assert len(records) > 0

            # Gather all persisted strings
            persisted_texts = [r["visible_text"] for r in records if r.get("visible_text")]
            persisted_contexts = [r["section_heading_context"] for r in records if r.get("section_heading_context")]
            combined_persisted_text = " ".join(persisted_texts + persisted_contexts).lower()

            # 1. Non-product account/profile/navigation text MUST NOT enter the persisted projection
            forbidden_non_product_strings = [
                "trang chủ tiktok",
                "khám phá sản phẩm",
                "xu hướng mua sắm",
                "user_super_buyer_99",
                "hồ sơ cá nhân",
                "ảnh đại diện",
                "session_secret_token_987",
                "phiên đăng nhập",
                "cài đặt tài khoản",
                "đăng xuất khỏi hệ thống",
                "đơn hàng của tôi",
                "ví voucher",
                "thông báo cá nhân",
                "khách hàng vip nội bộ",
                "chính sách bảo mật người dùng",
                "điều khoản dịch vụ tài khoản",
                "trung tâm trợ giúp",
            ]
            for forbidden in forbidden_non_product_strings:
                assert forbidden not in combined_persisted_text, (
                    f"Non-product string '{forbidden}' leaked into persisted projection"
                )

            # Ensure non-product structural tags and roles are excluded
            all_tags = [r["tag_name"] for r in records]
            all_roles = [r["role"] for r in records if r.get("role")]
            for excluded_tag in ("header", "nav", "footer", "aside"):
                assert excluded_tag not in all_tags, f"Excluded tag '{excluded_tag}' in projection"
            for excluded_role in ("navigation", "banner", "contentinfo"):
                assert excluded_role not in all_roles, f"Excluded role '{excluded_role}' in projection"

            # 2. Representative product observations MUST remain capturable within bounded projection
            # Title
            title_records = [
                r for r in records
                if "Đèn LED Cảm Biến Chuyển Động" in r.get("visible_text", "")
            ]
            assert len(title_records) >= 1
            assert any(r["tag_name"] == "h1" for r in title_records)

            # Price
            price_records = [
                r for r in records
                if "33.600₫" in r.get("visible_text", "")
            ]
            assert len(price_records) >= 1

            # Attributes / Specification
            spec_records = [
                r for r in records
                if "Nhựa ABS cao cấp" in r.get("visible_text", "")
                or "Type-C tiện lợi" in r.get("visible_text", "")
                or "3 chế độ thông minh" in r.get("visible_text", "")
            ]
            assert len(spec_records) >= 2

            # Seller / Product-Service
            seller_records = [
                r for r in records
                if "Lighting Official Store" in r.get("visible_text", "")
            ]
            assert len(seller_records) >= 1

            service_records = [
                r for r in records
                if "Đổi trả 7 ngày miễn phí" in r.get("visible_text", "")
                or "Bảo hành chính hãng 12 tháng" in r.get("visible_text", "")
            ]
            assert len(service_records) >= 1

            # Intended actions
            action_records = [
                r for r in records
                if "Mua ngay" in r.get("visible_text", "")
                or r.get("data-e2e") == "buy-now"
            ]
            assert len(action_records) >= 1

        finally:
            await browser.close()


