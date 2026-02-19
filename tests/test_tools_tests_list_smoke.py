#!/usr/bin/env python3
"""
Smoke guard: ensure tools-tests CI explicit list covers all local smoke scripts.

Problem:
- CI tools-tests runs an explicit bash array: tests=( ... ) then python "$t".
- New smoke scripts can be added but silently not executed if not added to that list.

Rule enforced here:
- Any tests file matching one of:
  * test_*_smoke.py
  * test_*_fail_closed.py
  * test_*_e2e_smoke.py
  must appear in the tools-tests tests=(...) list.

This test reads .github/workflows/pulse_ci.yml and extracts the tests=(...) block
from the "Run exporter + governance smoke tests" step.
"""

from __future__ import annotations

import pathlib
import re
from typing import List, Set, Tuple


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "pulse_ci.yml"
TESTS_DIR = ROOT / "tests"

# If you *intentionally* want to exclude a smoke script from tools-tests, add it here:
ALLOW_MISSING: Set[str] = set()


SMOKE_PATTERNS = [
    re.compile(r"^test_.*_smoke\.py$"),
    re.compile(r"^test_.*_fail_closed\.py$"),
    re.compile(r"^test_.*_e2e_smoke\.py$"),
]


def _collect_smoke_tests() -> List[str]:
    out: List[str] = []
    for p in sorted(TESTS_DIR.glob("test_*.py")):
        name = p.name
        if any(rx.match(name) for rx in SMOKE_PATTERNS):
            out.append(f"tests/{name}")
    return out


def _extract_tools_tests_list(yml_text: str) -> List[str]:
    """
    Extract entries from the tools-tests bash array:

    tests=(
      "tests/test_exporters.py"
      ...
    )

    but scoped to the step: "Run exporter + governance smoke tests".
    """
    lines = yml_text.splitlines()

    # Find the step header first (so we don't accidentally parse a different tests=(...) somewhere).
    step_idx = None
    for i, ln in enumerate(lines):
        if "name: Run exporter + governance smoke tests" in ln:
            step_idx = i
            break
    if step_idx is None:
        raise AssertionError("Could not find CI step: 'Run exporter + governance smoke tests' in pulse_ci.yml")

    # Find the tests=( start after that step.
    start = None
    for i in range(step_idx, len(lines)):
        if re.search(r"\btests=\(\s*$", lines[i]):
            start = i
            break
    if start is None:
        raise AssertionError("Could not find tests=( ... ) block after the tools-tests step header")

    # Collect until the closing ')'
    collected: List[str] = []
    entry_rx = re.compile(r'"(tests/test_[^"]+\.py)"')

    for i in range(start + 1, len(lines)):
        ln = lines[i].strip()
        if ln == ")":
            break
        m = entry_rx.search(ln)
        if m:
            collected.append(m.group(1))

    if not collected:
        raise AssertionError("Extracted empty tools-tests list from pulse_ci.yml (unexpected).")

    return collected


def _assert_no_duplicates(items: List[str], label: str) -> None:
    seen = set()
    dups = []
    for x in items:
        if x in seen:
            dups.append(x)
        seen.add(x)
    if dups:
        raise AssertionError(f"Duplicate entries in {label}: {sorted(set(dups))}")


def test_tools_tests_list_covers_smoke_scripts() -> None:
    assert WORKFLOW.is_file(), f"Missing workflow file: {WORKFLOW}"

    yml = WORKFLOW.read_text(encoding="utf-8")
    listed = _extract_tools_tests_list(yml)
    _assert_no_duplicates(listed, "CI tools-tests list")

    listed_set = set(listed)

    smoke = _collect_smoke_tests()
    _assert_no_duplicates(smoke, "local smoke test discovery")

    smoke_set = set(smoke)

    # Sanity: ensure the discovered paths exist
    for rel in smoke:
        p = ROOT / rel
        assert p.is_file(), f"Discovered smoke test does not exist on disk: {rel}"

    missing = sorted((smoke_set - listed_set) - ALLOW_MISSING)
    if missing:
        raise AssertionError(
            "Smoke scripts missing from CI tools-tests list:\n"
            + "\n".join(f"  - {m}" for m in missing)
            + "\n\nFix: add them to .github/workflows/pulse_ci.yml tests=(...) array."
        )

    stale = sorted(listed_set - {f"tests/{p.name}" for p in sorted(TESTS_DIR.glob('test_*.py'))})
    # Note: we only flag stale entries for tests/test_*.py references. Other entries are fine.
    if stale:
        raise AssertionError(
            "CI tools-tests list references missing test files:\n"
            + "\n".join(f"  - {s}" for s in stale)
        )


def main() -> int:
    try:
        test_tools_tests_list_covers_smoke_scripts()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1
    print("OK: tools-tests list covers all smoke scripts")
    return 0


def test_smoke() -> None:
    # optional pytest entrypoint
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
