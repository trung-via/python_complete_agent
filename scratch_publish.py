import subprocess
import sys

notes = """1. DOM Fixture Invocation Fix:
- Extractor scripts are arrow functions (targetProductId) => { ... } evaluated directly through page.evaluate(_SHOPEE_EXTRACTION_SCRIPT, "123") and page.evaluate(_TIKTOK_EXTRACTOR_JS, "123").

2. Nested UGC/Review Contamination Exclusion Verification:
- Playwright DOM fixtures in tests/product_source/test_extractor_dom_fixtures.py now explicitly nest review, comment, rating, and recommendation subtrees directly INSIDE scanned product containers (.product-briefing, .product-image-carousel, .product-detail for Shopee; .pdp-container, .product-image, .seller-description for TikTok) sharing identical CDN hosts.
- Assertions prove that valid seller/gallery images are accepted, while all nested UGC and recommendation subtrees are rejected specifically by container/subtree ownership exclusion.

3. Stray Script Cleanup:
- Removed stray test_pw.py debug script from repository.

4. Durable Verification Evidence:
- Focused suite (tests/product_source/): 48 passed, 0 failed.
- Full repository suite (tests/): 466 passed, 0 failed.

5. Architectural Invariants Preserved:
- Exact identity matching (no substring overlap).
- Structured product fields strictly gated behind identity.
- Model/SKU captured when present.
- Pattern-based URL sensitive parameter redaction.
- Fail-closed on zero accepted seller media.
- Known limitations: M2.2A establishes canonical Product Source Packs; M2.3 cross-platform scoring/ranking and M2.4 queue handoff remain scheduled for future milestones.
- Merge governance: Do not merge automatically. Human review required."""

summary = "TASK-013 FIX: Invoked JS extractor functions properly in Playwright fixture with targetProductId argument, verified nested UGC/recommendation contamination exclusion across scanned product containers, removed stray test_pw.py script, and supplied full verification evidence."

cmd = [
    sys.executable,
    "bridge.py",
    "publish",
    "13",
    "--action",
    "FIX",
    "--test",
    r".\venv\Scripts\python -m pytest tests/product_source/ -v && .\venv\Scripts\python -m pytest tests/ -q -W ignore",
    "--summary",
    summary,
    "--notes",
    notes,
]

ret = subprocess.call(cmd)
sys.exit(ret)
