#!/usr/bin/env python3
"""
Smoke guard: ensure tools-tests suite remains coherent and covers all local smoke scripts.

Field source of truth:
- ci/tools-tests.list

Why dual-mode?
- During migration, CI may still run an inline workflow list (tests=(...)) while the repo already
  has the manifest. In that phase, we enforce equivalence between the inline list and the manifest.
- After migration, the inline list disappears; then we require the workflow to reference the manifest.

Rules enforced:
- Any tests/ file matching:
    * test_*_smoke.py
    * test_*_fail_closed.py
    * test_*_e2e_smoke.py
  must appear in ci/tools-tests.list (unless allowlisted).
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import List, Optional, Set


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
            f"Duplicate entries in {label}:\n" + "\n".join(f"  - {d}" for d in sorted(dups))
        )


def _read_manifest() -> List[str]:
    if not MANIFEST.is_file():
        raise AssertionError(f"Missing tools-tests manifest: {MANIFEST}")

    entries: List[str] = []
    for raw in MANIFEST.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue

        # Enforce: one path per line
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


def _extract_inline_suite_from_workflow(yml_text: str) -> Optional[List[str]]:
    """
    Find a tests=(...) bash array block in the workflow that looks like the tools-tests suite.

    We select the block that contains these sentinel entries:
      - tests/test_exporters.py
      - tests/test_tools_tests_list_smoke.py
    """
    lines = yml_text.splitlines()

    start_rx = re.compile(r"^\s*tests=\(\s*$")
    end_rx = re.compile(r"^\s*\)\s*$")
    entry_rx = re.compile(r"""["'](tests/test_[^"']+\.py)["']""")

    best: Optional[List[str]] = None

    i = 0
    while i < len(lines):
        if start_rx.match(lines[i]):
            j = i + 1
            block_entries: List[str] = []
            block_raw: List[str] = []
            while j < len(lines) and not end_rx.match(lines[j]):
                block_raw.append(lines[j])
                m = entry_rx.search(lines[j])
                if m:
                    block_entries.append(m.group(1))
                j += 1

            # Heuristic: pick the suite block containing the two known entries
            raw_text = "\n".join(block_raw)
            if "tests/test_exporters.py" in raw_text and "tests/test_tools_tests_list_smoke.py" in raw_text:
                best = block_entries
                break

            i = j + 1
            continue

        i += 1

    if best is None:
        return None

    if not best:
        raise AssertionError("Found tests=(...) block in workflow but extracted 0 entries (unexpected).")

    return best


def test_tools_tests_list_covers_smoke_scripts() -> None:
    if not WORKFLOW.is_file():
        raise AssertionError(f"Missing workflow file: {WORKFLOW}")

    # Canonical suite definition
    manifest = _read_manifest()
    _assert_no_duplicates(manifest, "ci/tools-tests.list")

    yml = WORKFLOW.read_text(encoding="utf-8", errors="replace")
    inline = _extract_inline_suite_from_workflow(yml)

    if inline is not None:
        # Migration phase (or legacy state): enforce equivalence to prevent drift.
        # Prefer strict order equality (suite is explicit and ordered).
        if inline != manifest:
            raise AssertionError(
                "tools-tests suite drift detected between workflow inline list and ci/tools-tests.list.\n"
                f"- workflow inline entries: {len(inline)}\n"
                f"- manifest entries:       {len(manifest)}\n\n"
                "Fix: make .github/workflows/pulse_ci.yml and ci/tools-tests.list match exactly."
            )
    else:
        # Manifest-based workflow: require wiring reference exists.
        if "ci/tools-tests.list" not in yml:
            raise AssertionError(
                "CI suite definition not detected.\n"
                "- No tests=(...) inline list found in the workflow\n"
                "- And workflow does not reference ci/tools-tests.list\n\n"
                "Fix: update the tools-tests step to read ci/tools-tests.list."
            )

    # Fail-closed: every manifest path must exist
    missing_files = [rel for rel in manifest if not (ROOT / rel).is_file()]
    if missing_files:
        raise AssertionError(
            "ci/tools-tests.list references missing files:\n"
            + "\n".join(f"  - {m}" for m in missing_files)
        )

    # Coverage: all discovered smoke scripts must be listed (unless allowlisted)
    listed_set = set(manifest)
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
    print("OK: tools-tests suite is coherent and manifest covers all smoke scripts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
