"""Delegate one preselected operation through the exact downstream AIOS pin.

The caller supplies a trusted transient Python Agent control checkout.  This
entry imports bootstrap mechanics only from that checkout, proves or creates
the repository-local immutable-pin runtime, and invokes the supplied Operator
arguments once.  It does not select an operation, Executor, profile, or
lifecycle outcome.
"""

from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import sys


def _repo_from_operator_arguments(arguments: list[str]) -> Path:
    positions = [index for index, value in enumerate(arguments) if value == "--repo"]
    if len(positions) != 1 or positions[0] + 1 >= len(arguments):
        raise SystemExit("operator invocation requires exactly one --repo value")
    return Path(arguments[positions[0] + 1]).resolve(strict=True)


def _load_bootstrap(control_source: Path):
    worker_path = (
        control_source
        / ".agents"
        / "skills"
        / "aios-worker"
        / "scripts"
        / "aios_worker.py"
    )
    if not worker_path.is_file():
        raise SystemExit("control source has no trusted AIOS bootstrap")
    specification = importlib.util.spec_from_file_location(
        "_aios_transient_worker_bootstrap", worker_path
    )
    if specification is None or specification.loader is None:
        raise SystemExit("trusted AIOS bootstrap cannot be loaded")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    loaded_path = Path(module.__file__).resolve(strict=True)
    if not loaded_path.is_relative_to(control_source):
        raise SystemExit("AIOS bootstrap did not resolve from the control source")
    return module


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) < 2:
        raise SystemExit(
            "usage: aios_control_entry.py CONTROL_SOURCE [AIOS_ARGS ...]"
        )

    control_source = Path(arguments[0]).resolve(strict=True)
    operator_arguments = arguments[1:]
    repo = _repo_from_operator_arguments(operator_arguments)
    bootstrap = _load_bootstrap(control_source)
    layout = bootstrap.runtime_layout(repo)
    trusted_requirements = (
        control_source
        / ".agents"
        / "skills"
        / "aios-worker"
        / "requirements-aios-renew.txt"
    )
    layout = replace(layout, requirements=trusted_requirements)
    python = bootstrap.ensure_runtime(layout)
    completed = bootstrap.invoke_kernel(
        (str(python), "-m", "aios_renew.operator", *operator_arguments),
        repo=repo,
    )
    bootstrap._emit_completed(completed)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
