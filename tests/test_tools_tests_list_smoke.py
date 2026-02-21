#!/usr/bin/env python3
"""
Smoke guard: ensure tools-tests CI suite covers all local smoke scripts.

Field source of truth:
- ci/tools-tests.list

Sanity:
- .github/workflows/pulse_ci.yml must reference "ci/tools-tests.list" (so CI consumes the manifest).

Rules enforced:
- Any tests/ file matching:
    * test_*_smoke.py
    * test_*_fail_closed.py
    * test_*_e2e_smoke.py
  must be present in ci/tools-tests.list (unless allowlisted).
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Set


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "pulse_ci.yml"
MANIFEST = ROOT / "ci" / "tools-tests.list"
TESTS_DIR = ROOT / "tests"

# If you intentionally exclude a smoke script from tools-tests, add it here:
ALLOW_MISSING: Set[str] = set()

SMOKE_GLOBS = [
    "test_*_smoke.py",
    "test_*_fail_closed.py",
    "test_*_e2e_smoke.py",
]


def _assert_no_duplicates(items: List[str], label: str) -> None:
    seen = set()
    dups = set()
    for x in items:
        if x in seen:
            dups.add(x)
        seen.add(x)
    if dups:
        raise AssertionError(
            f"Duplicate entries in {label}:\n"
            + "\n".join(f"  - {d}" for d in sorted(dups))
        )


def _read_manifest() -> List[str]:
    if not MANIFEST.is_file():
        raise AssertionError(f"Missing tools-tests manifest: {MANIFEST}")

    entries: List[str] = []
    for raw in MANIFEST.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue

        # Enforce: one path per line (no internal whitespace)
        parts = line.split()
        if len(parts) != 1:
            raise AssertionError(
                f"Invalid manifest line in {MANIFEST} (expected one path per line): {raw!r}"
            )

        entries.append(parts[0])

    if not entries:
        raise AssertionError(f"Manifest is empty after filtering: {MANIFEST}")

    return entries


def _discover_smoke_scripts() -> Set[str]:
    smoke: Set[str] = set()
    for pat in SMOKE_GLOBS:
        for p in TESTS_DIR.glob(pat):
            smoke.add(f"tests/{p.name}")
    return smoke


def test_tools_tests_list_covers_smoke_scripts() -> None:
    if not WORKFLOW.is_file():
        raise AssertionError(f"Missing workflow file: {WORKFLOW}")

    yml = WORKFLOW.read_text(encoding="utf-8", errors="replace")
    if "ci/tools-tests.list" not in yml:
        raise AssertionError(
            "CI wiring not detected: expected .github/workflows/pulse_ci.yml to reference "
            "ci/tools-tests.list.\n"
            "Fix: update the tools-tests step to read the manifest."
        )

    listed = _read_manifest()
    _assert_no_duplicates(listed, "ci/tools-tests.list")
    listed_set = set(listed)

    # Fail-closed: every listed path must exist
    missing_files = [rel for rel in listed if not (ROOT / rel).is_file()]
    if missing_files:
        raise AssertionError(
            "ci/tools-tests.list references missing files:\n"
            + "\n".join(f"  - {m}" for m in missing_files)
        )

    smoke = _discover_smoke_scripts()
    missing = sorted((smoke - listed_set) - ALLOW_MISSING)
    if missing:
        raise AssertionError(
            "Smoke scripts missing from ci/tools-tests.list:\n"
            + "\n".join(f"  - {m}" for m in missing)
            + "\n\nFix: add them to ci/tools-tests.list."
        )

    # Stale entries: only check those pointing at tests/test_*.py
    all_test_files = {f"tests/{p.name}" for p in TESTS_DIR.glob("test_*.py")}
    stale = sorted({x for x in listed_set if x.startswith("tests/test_")} - all_test_files)
    if stale:
        raise AssertionError(
            "ci/tools-tests.list contains stale test entries:\n"
            + "\n".join(f"  - {s}" for s in stale)
        )


def main() -> int:
    try:
        test_tools_tests_list_covers_smoke_scripts()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1
    print("OK: tools-tests manifest covers all smoke scripts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
