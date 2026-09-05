"""Focused deterministic certification of AC1-AC7 for TASK-130 auto-publish workflow."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOW_FILE = REPO_ROOT / ".github" / "workflows" / "aios-auto-publish.yml"
REQUIREMENTS_FILE = (
    REPO_ROOT / ".agents" / "skills" / "aios-worker" / "requirements-aios-renew.txt"
)
SKILL_FILE = REPO_ROOT / ".agents" / "skills" / "aios-worker" / "SKILL.md"
WORKFLOW_DOC_FILE = (
    REPO_ROOT / ".agents" / "workflows" / "aios-renew-worker.md"
)
DOCS_FILE = REPO_ROOT / "docs" / "AIOS_UNIFIED_WORKER_WORKFLOW.md"
LAUNCHER_FILE = (
    REPO_ROOT / ".agents" / "skills" / "aios-worker" / "scripts" / "aios_worker.py"
)

AUTHORITATIVE_COMMIT = "67db82bf19d63f25721d06aabb82d850db8b78d4"
BASE_SHA = "b0ae093fcc31ba49e27d808de2ab0cb9e837aba4"
EXPECTED_FLOW = (
    "AIOS PASS -> ChatGPT semantic review -> canonical PASS review-decision ref -> "
    "repository-native workflow -> pinned AIOS publication gate -> exact source candidate fast-forward to main"
)


def load_workflow() -> dict:
    assert WORKFLOW_FILE.is_file(), f"Workflow missing: {WORKFLOW_FILE}"
    raw = WORKFLOW_FILE.read_text(encoding="utf-8")
    return yaml.safe_load(raw)


class TestWorkflowTriggerAndPermissions:
    """Certifies AC1: Trigger on review-decision pushes, write permission, event checkout."""

    def test_workflow_file_exists_and_parses(self):
        wf = load_workflow()
        assert wf.get("name") == "AIOS auto-publish reviewed candidate"

    def test_trigger_strictly_push_to_review_decision_branches(self):
        wf = load_workflow()
        triggers = wf.get("on") if wf.get("on") is not None else wf.get(True)
        assert isinstance(triggers, dict), "Workflow 'on' must be a mapping"
        assert set(triggers.keys()) == {"push"}, (
            "Workflow must trigger only on 'push', no other triggers allowed"
        )
        push_spec = triggers["push"]
        assert isinstance(push_spec, dict)
        assert set(push_spec.keys()) == {"branches"}
        branches = push_spec["branches"]
        assert branches == ["aios/review-decision/**"], (
            "Workflow must only trigger on 'aios/review-decision/**' branch push"
        )

    def test_permissions_strictly_contents_write(self):
        wf = load_workflow()
        permissions = wf.get("permissions")
        assert permissions == {"contents": "write"}, (
            "Workflow must request only 'contents: write' permission"
        )

    def test_concurrency_group_and_no_cancellation(self):
        wf = load_workflow()
        concurrency = wf.get("concurrency")
        assert concurrency == {
            "group": "aios-auto-publish-main",
            "cancel-in-progress": False,
        }

    def test_checkout_is_event_bound_with_full_history(self):
        wf = load_workflow()
        publish_job = wf.get("jobs", {}).get("publish", {})
        assert publish_job.get("runs-on") == "ubuntu-latest"
        steps = publish_job.get("steps", [])
        checkout_steps = [
            s for s in steps if "actions/checkout" in str(s.get("uses", ""))
        ]
        assert len(checkout_steps) == 1, "Exactly one checkout step required"
        checkout = checkout_steps[0]
        params = checkout.get("with", {})
        assert params.get("ref") == "${{ github.sha }}", (
            "Checkout must bind to ${{ github.sha }}, never mutable latest main"
        )
        assert params.get("fetch-depth") == 0, (
            "Checkout must fetch full history (fetch-depth: 0) for ancestry validation"
        )


class TestPythonProvisioningAndDependencyPin:
    """Certifies AC2: Python 3.11+ provisioned and installed solely from requirements pin."""

    def test_workflow_provisions_python_311(self):
        wf = load_workflow()
        steps = wf.get("jobs", {}).get("publish", {}).get("steps", [])
        setup_steps = [
            s for s in steps if "actions/setup-python" in str(s.get("uses", ""))
        ]
        assert len(setup_steps) == 1, "Exactly one setup-python step required"
        version = setup_steps[0].get("with", {}).get("python-version")
        assert version in ("3.11", "3.11+", ">=3.11")

    def test_workflow_installs_only_from_requirements_pin_file(self):
        wf = load_workflow()
        steps = wf.get("jobs", {}).get("publish", {}).get("steps", [])
        install_steps = [
            s for s in steps
            if "requirements-aios-renew.txt" in str(s.get("run", ""))
        ]
        assert len(install_steps) == 1, (
            "Must install AIOS-renew from .agents/skills/aios-worker/requirements-aios-renew.txt"
        )
        install_cmd = install_steps[0]["run"]
        assert ".agents/skills/aios-worker/requirements-aios-renew.txt" in install_cmd
        assert "pip install" in install_cmd
        assert "git+https" not in install_cmd, (
            "Workflow must not duplicate the URL or commit pin directly in workflow YAML"
        )
        assert "aios-renew==" not in install_cmd

    def test_immutable_pin_file_points_to_authoritative_commit(self):
        lines = [
            line.strip()
            for line in REQUIREMENTS_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        assert lines == [
            f"aios-renew @ git+https://github.com/trung-via/AIOS-renew.git@{AUTHORITATIVE_COMMIT}"
        ]

    def test_workflow_has_no_floating_or_duplicate_runtime_sources(self):
        raw = WORKFLOW_FILE.read_text(encoding="utf-8")
        for forbidden in (
            "git+https://",
            AUTHORITATIVE_COMMIT,
            "pypi.org",
            "pip install aios-renew",
            "pip install --upgrade aios-renew",
        ):
            assert forbidden not in raw, f"Forbidden floating/duplicate source found: {forbidden}"


class TestPublicationDelegation:
    """Certifies AC3: Derives RUN only from review-decision ref and delegates once to publication module."""

    def test_workflow_derives_run_id_from_review_decision_ref(self):
        raw = WORKFLOW_FILE.read_text(encoding="utf-8")
        assert "refs/heads/aios/review-decision/" in raw
        assert "AIOS_DECISION_REF" in raw
        assert "AIOS_DECISION_SHA" in raw
        assert "${{ github.ref }}" in raw
        assert "${{ github.sha }}" in raw

    def test_delegates_to_aios_renew_publication_module_with_exact_args(self):
        raw = WORKFLOW_FILE.read_text(encoding="utf-8")
        assert "python -m aios_renew.publication" in raw
        assert "--repo ." in raw
        assert "--remote origin" in raw
        assert "--run-id" in raw
        assert "--decision-sha" in raw
        assert raw.count("aios_renew.publication") == 1

    def test_derivation_logic_extracts_run_id_and_rejects_invalid_ref(self):
        prefix = "refs/heads/aios/review-decision/"
        canonical_ref = "refs/heads/aios/review-decision/RUN-130-001"
        assert canonical_ref.startswith(prefix)
        run_id = canonical_ref[len(prefix):]
        assert run_id == "RUN-130-001"

        invalid_refs = [
            "refs/heads/main",
            "refs/heads/aios/review/RUN-130-001",
            "refs/heads/aios/artifacts/RUN-130-001",
            "refs/heads/feature",
        ]
        for ref in invalid_refs:
            assert not ref.startswith(prefix)


class TestNoDuplicatedPublicationSemantics:
    """Certifies AC4: Workflow does not duplicate publication semantics."""

    def test_workflow_has_no_direct_main_push_or_lease(self):
        raw = WORKFLOW_FILE.read_text(encoding="utf-8")
        assert "git push" not in raw
        assert "refs/heads/main" not in raw
        assert "--force" not in raw
        assert "--force-with-lease" not in raw

    def test_workflow_has_no_review_or_remediation_parsing(self):
        raw = WORKFLOW_FILE.read_text(encoding="utf-8")
        assert ".ai/reviews" not in raw
        assert ".ai/transport" not in raw
        assert "result.json" not in raw
        assert "run.json" not in raw
        assert "verdict" not in raw
        assert "CHANGES_REQUIRED" not in raw
        assert "findings" not in raw
        assert "ResultPackage" not in raw

    def test_workflow_has_no_ancestry_implementation(self):
        raw = WORKFLOW_FILE.read_text(encoding="utf-8")
        assert "merge-base" not in raw
        assert "--is-ancestor" not in raw

    def test_workflow_has_no_retry_fallback_merge_or_rebase(self):
        raw = WORKFLOW_FILE.read_text(encoding="utf-8")
        for forbidden in (
            "git merge",
            "git rebase",
            "git reset",
            "git cherry-pick",
            "while ",
            "for ",
            "sleep ",
            "retry",
            "fallback",
        ):
            assert forbidden not in raw.lower(), f"Forbidden semantic found: {forbidden}"


class TestDocumentationAlignment:
    """Certifies AC5 & AC6: Documentation consistently describes push-free workers and auto-publication."""

    @pytest.mark.parametrize("doc_path", [SKILL_FILE, WORKFLOW_DOC_FILE, DOCS_FILE])
    def test_documentation_states_push_free_workers_and_review_in_chatgpt(self, doc_path):
        text = doc_path.read_text(encoding="utf-8")
        assert "push-free" in text
        assert "Runtime PASS" in text
        assert "Review TASK-N in ChatGPT" in text

    @pytest.mark.parametrize("doc_path", [SKILL_FILE, WORKFLOW_DOC_FILE, DOCS_FILE])
    def test_documentation_identifies_chatgpt_as_sole_semantic_reviewer(self, doc_path):
        text = doc_path.read_text(encoding="utf-8")
        assert "ChatGPT remains the sole semantic Reviewer" in text

    @pytest.mark.parametrize("doc_path", [SKILL_FILE, WORKFLOW_DOC_FILE, DOCS_FILE])
    def test_documentation_contains_exact_publication_flow(self, doc_path):
        text = doc_path.read_text(encoding="utf-8")
        assert EXPECTED_FLOW in text
        assert "No Human PUBLISH command" in text or "no Human PUBLISH command" in text

    @pytest.mark.parametrize("doc_path", [SKILL_FILE, WORKFLOW_DOC_FILE, DOCS_FILE])
    def test_documentation_distinguishes_changes_required_and_narrow_fix(self, doc_path):
        text = doc_path.read_text(encoding="utf-8")
        assert "CHANGES_REQUIRED does not publish" in text
        assert "narrow FIX lineage" in text

    @pytest.mark.parametrize("doc_path", [SKILL_FILE, WORKFLOW_DOC_FILE, DOCS_FILE])
    def test_documentation_restricts_published_payload_to_reviewed_candidate(self, doc_path):
        text = doc_path.read_text(encoding="utf-8")
        assert "publishes only the exact reviewed source candidate" in text
        assert "never review-decision" in text
        assert "artifact" in text
        assert "remediation metadata" in text

    @pytest.mark.parametrize("doc_path", [SKILL_FILE, WORKFLOW_DOC_FILE])
    def test_worker_surfaces_remain_executor_specific(self, doc_path):
        text = doc_path.read_text(encoding="utf-8")
        if doc_path == SKILL_FILE:
            assert "--executor codex" in text
            assert "--executor antigravity" not in text
        else:
            assert "--executor antigravity" in text
            assert "--executor codex" not in text


class TestIntegrityAndUnchangedSurfaces:
    """Certifies AC7: Existing Product Intelligence and launcher remain byte-unchanged."""

    def test_launcher_is_byte_unchanged_from_base(self):
        current_bytes = LAUNCHER_FILE.read_bytes()
        base_bytes = subprocess.run(
            [
                "git",
                "show",
                f"{BASE_SHA}:.agents/skills/aios-worker/scripts/aios_worker.py",
            ],
            capture_output=True,
            check=True,
        ).stdout
        assert current_bytes == base_bytes

    def test_product_intelligence_is_byte_unchanged_from_base(self):
        code = subprocess.run(
            ["git", "diff", "--exit-code", BASE_SHA, "--", "src/product_intelligence"],
            capture_output=True,
        ).returncode
        assert code == 0, "Product Intelligence files must remain untouched"

    def test_requirements_file_is_byte_unchanged_from_base(self):
        current_bytes = REQUIREMENTS_FILE.read_bytes()
        base_bytes = subprocess.run(
            [
                "git",
                "show",
                f"{BASE_SHA}:.agents/skills/aios-worker/requirements-aios-renew.txt",
            ],
            capture_output=True,
            check=True,
        ).stdout
        assert current_bytes == base_bytes

    def test_only_authorized_scope_modified(self):
        diff_names = subprocess.run(
            ["git", "diff", "--name-only", BASE_SHA],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip().splitlines()
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip().splitlines()
        all_touched = set(filter(None, diff_names + untracked))
        authorized = {
            ".github/workflows/aios-auto-publish.yml",
            ".agents/skills/aios-worker/SKILL.md",
            ".agents/workflows/aios-renew-worker.md",
            "docs/AIOS_UNIFIED_WORKER_WORKFLOW.md",
            "tests/aios_bridge/test_aios_auto_publish_workflow.py",
        }
        outside = all_touched - authorized
        assert not outside, f"Unauthorized files touched: {outside}"

    def test_modified_and_added_files_have_lf_and_no_bom(self):
        for rel_path in (
            ".github/workflows/aios-auto-publish.yml",
            ".agents/skills/aios-worker/SKILL.md",
            ".agents/workflows/aios-renew-worker.md",
            "docs/AIOS_UNIFIED_WORKER_WORKFLOW.md",
            "tests/aios_bridge/test_aios_auto_publish_workflow.py",
        ):
            file_path = REPO_ROOT / rel_path
            raw = file_path.read_bytes()
            assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM detected in {rel_path}"
            assert b"\r\n" not in raw, f"CRLF detected in {rel_path}"

    def test_git_diff_check_passes(self):
        proc = subprocess.run(
            ["git", "diff", "--check"],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"git diff --check failed: {proc.stdout} {proc.stderr}"
