#!/usr/bin/env python3
"""Guard the split between core and optional analysis dependencies."""

from __future__ import annotations

import shlex
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_REQ = ROOT / "requirements.txt"
ANALYSIS_REQ = ROOT / "requirements-analysis.txt"
PULSE_PD_WORKFLOW = ROOT / ".github" / "workflows" / "pulse_pd_smoke.yml"


ANALYSIS_PACKAGES = {"numpy", "matplotlib"}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _package_name(token: str) -> str:
    """Return the normalized package name from a pip requirement token."""
    token = token.strip()

    for separator in ("==", ">=", "<=", "~=", "!=", ">", "<", "["):
        if separator in token:
            token = token.split(separator, 1)[0]

    return token.strip().lower().replace("_", "-")


def _is_pip_install_line(line: str) -> bool:
    try:
        parts = shlex.split(line)
    except ValueError:
        return False

    if not parts:
        return False

    # python -m pip install ...
    if len(parts) >= 4 and parts[0] == "python" and parts[1:4] == ["-m", "pip", "install"]:
        return True

    # pip install ...
    if len(parts) >= 2 and parts[0] == "pip" and parts[1] == "install":
        return True

    return False


def _inline_analysis_installs(workflow_text: str) -> list[str]:
    offenders: list[str] = []

    for raw_line in workflow_text.splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if not _is_pip_install_line(line):
            continue

        try:
            parts = shlex.split(line)
        except ValueError:
            continue

        normalized_tokens = {_package_name(part) for part in parts}

        if normalized_tokens & ANALYSIS_PACKAGES:
            offenders.append(line)

    return offenders


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

    offenders = _inline_analysis_installs(text)
    assert offenders == [], (
        "PULSE-PD workflow must not install analysis packages inline. "
        "Use requirements-analysis.txt instead. Offending lines: "
        + "; ".join(offenders)
    )


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
