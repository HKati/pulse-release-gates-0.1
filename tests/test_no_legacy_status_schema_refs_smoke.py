#!/usr/bin/env python3
"""Smoke guard for legacy status schema references.

We keep the legacy schema file for backward compatibility, but CI/tooling must
not reference it anymore.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
TOOLS_DIR = ROOT / "tools"
PACK_DIR = ROOT / "PULSE_safe_pack_v0"

LEGACY_TOKEN = "status.schema.json"
V1_SCHEMA_PATH = "schemas/status/status_v1.schema.json"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _scan_dir_for_token(base: Path, exts: tuple[str, ...]) -> list[str]:
    """Return repo-relative file paths containing LEGACY_TOKEN.

    Only files with extensions in ``exts`` are scanned.
    """
    hits: list[str] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix not in exts:
            continue
        if LEGACY_TOKEN in _read_text(path):
            hits.append(str(path.relative_to(ROOT)))
    return hits


def test_no_legacy_status_schema_refs_smoke() -> None:
    assert WORKFLOWS_DIR.is_dir(), f"Missing workflows dir: {WORKFLOWS_DIR}"
    assert TOOLS_DIR.is_dir(), f"Missing tools dir: {TOOLS_DIR}"
    assert PACK_DIR.is_dir(), f"Missing pack dir: {PACK_DIR}"

    # Positive sanity: CI should already point at v1 schema.
    pulse_ci = WORKFLOWS_DIR / "pulse_ci.yml"
    assert pulse_ci.is_file(), f"Missing workflow file: {pulse_ci}"
    assert V1_SCHEMA_PATH in _read_text(pulse_ci), (
        "Expected pulse_ci.yml to reference v1 status schema path: "
        f"{V1_SCHEMA_PATH}"
    )

    # Negative checks: no legacy schema refs in CI/tooling locations.
    hits: list[str] = []
    hits.extend(_scan_dir_for_token(WORKFLOWS_DIR, (".yml", ".yaml")))
    hits.extend(_scan_dir_for_token(TOOLS_DIR, (".py",)))
    hits.extend(_scan_dir_for_token(PACK_DIR, (".py",)))

    assert not hits, (
        "Legacy schema reference found (forbidden):\n"
        + "\n".join(f"  - {h}" for h in hits)
        + "\n\nFix: use schemas/status/status_v1.schema.json instead."
    )
