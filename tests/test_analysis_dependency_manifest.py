#!/usr/bin/env python3
"""Guard the split between core and optional analysis dependencies."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_REQ = ROOT / "requirements.txt"
ANALYSIS_REQ = ROOT / "requirements-analysis.txt"
PULSE_PD_WORKFLOW = ROOT / ".github" / "workflows" / "pulse_pd_smoke.yml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_analysis_requirements_manifest_exists_and_extends_core() -> None:
    text = _read(ANALYSIS_REQ)

    assert "-r requirements.txt" in text
    assert "numpy>=" in text
    assert "matplotlib>=" in text


def test_core_requirements_remain_minimal_release_authority_runtime() -> None:
    text = _read(CORE_REQ).lower()

    assert "pyyaml" in text
    assert "jsonschema" in text

    # Optional analysis dependencies must not be promoted into the minimal
    # release-authority runtime.
    assert "numpy" not in text
    assert "matplotlib" not in text


def test_pulse_pd_workflow_installs_analysis_manifest_not_inline_packages() -> None:
    text = _read(PULSE_PD_WORKFLOW)

    assert "python -m pip install -r requirements-analysis.txt" in text
    assert "python -m pip install numpy matplotlib" not in text


def main() -> int:
    try:
        test_analysis_requirements_manifest_exists_and_extends_core()
        test_core_requirements_remain_minimal_release_authority_runtime()
        test_pulse_pd_workflow_installs_analysis_manifest_not_inline_packages()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: analysis dependency manifest guard passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
