#!/usr/bin/env python3
"""
Smoke guard: ensure the render-quality-ledger pytest suite remains coherent.

Field source of truth:
- ci/render-quality-ledger-tests.list

Why dual-mode?
- During migration, CI may still run an inline workflow list while the repo already
  has the manifest. In that phase, we enforce equivalence between the inline list
  and the manifest.
- After migration, the inline list disappears; then we require the workflow to
  reference the manifest.

Rules enforced:
- tests/test_exporters.py must appear in ci/render-quality-ledger-tests.list
- Any tests/ file matching test_render_quality_ledger*.py must appear in the
  manifest unless allowlisted below.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import List, Optional, Set


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "pulse_ci.yml"
MANIFEST = ROOT / "ci" / "render-quality-ledger-tests.list"
TESTS_DIR = ROOT / "tests"

# If you intentionally exclude a renderer-related test from the renderer suite,
# add it here.
ALLOW_MISSING: Set[str] = {
    "tests/test_render_quality_ledger_tests_list_smoke.py",
}

REQUIRED_EXACT: Set[str] = {
    "tests/test_exporters.py",
}

RENDER_GLOBS = [
    "test_render_quality_ledger*.py",
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
        raise AssertionError(f"Missing render-quality-ledger manifest: {MANIFEST}")

    entries: List[str] = []
    for raw in MANIFEST.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) != 1:
            raise AssertionError(
                f"Invalid manifest line in {MANIFEST} (expected one path per line): {raw!r}"
            )

        rel = parts[0]
        if not rel.startswith("tests/"):
            raise AssertionError(
                f"Invalid render-quality-ledger manifest entry (expected tests/* path): {rel!r}"
            )
        if not rel.endswith(".py"):
            raise AssertionError(
                f"Invalid render-quality-ledger manifest entry (expected .py file): {rel!r}"
            )

        entries.append(rel)

    if not entries:
        raise AssertionError(f"Manifest is empty after filtering: {MANIFEST}")

    return entries


def _discover_renderer_tests() -> Set[str]:
    expected: Set[str] = set(REQUIRED_EXACT)
    for pat in RENDER_GLOBS:
        for p in TESTS_DIR.glob(pat):
            expected.add(f"tests/{p.name}")
    return expected


def _extract_inline_suite_from_workflow(yml_text: str) -> Optional[List[str]]:
    """
    Find a tests=(...) bash array block in the workflow that looks like the
    render-quality-ledger suite.

    We select the block that contains these sentinel entries:
      - tests/test_exporters.py
      - tests/test_render_quality_ledger_check_gates_parity.py
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

            raw_text = "\n".join(block_raw)
            if (
                "tests/test_exporters.py" in raw_text
                and "tests/test_render_quality_ledger_check_gates_parity.py" in raw_text
            ):
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


def test_render_quality_ledger_manifest_is_coherent() -> None:
    if not WORKFLOW.is_file():
        raise AssertionError(f"Missing workflow file: {WORKFLOW}")

    manifest = _read_manifest()
    _assert_no_duplicates(manifest, "ci/render-quality-ledger-tests.list")

    yml = WORKFLOW.read_text(encoding="utf-8", errors="replace")
    inline = _extract_inline_suite_from_workflow(yml)

    if inline is not None:
        if inline != manifest:
            raise AssertionError(
                "render-quality-ledger suite drift detected between workflow inline list "
                "and ci/render-quality-ledger-tests.list.\n"
                f"- workflow inline entries: {len(inline)}\n"
                f"- manifest entries:       {len(manifest)}\n\n"
                "Fix: make .github/workflows/pulse_ci.yml and "
                "ci/render-quality-ledger-tests.list match exactly."
            )
    else:
        if "ci/render-quality-ledger-tests.list" not in yml:
            raise AssertionError(
                "CI suite definition not detected.\n"
                "- No tests=(...) inline list found in the workflow\n"
                "- And workflow does not reference ci/render-quality-ledger-tests.list\n\n"
                "Fix: update the renderer pytest step to read "
                "ci/render-quality-ledger-tests.list."
            )

    missing_files = [rel for rel in manifest if not (ROOT / rel).is_file()]
    if missing_files:
        raise AssertionError(
            "ci/render-quality-ledger-tests.list references missing files:\n"
            + "\n".join(f"  - {m}" for m in missing_files)
        )

    listed_set = set(manifest)
    expected = _discover_renderer_tests()
    missing = sorted((expected - listed_set) - ALLOW_MISSING)
    if missing:
        raise AssertionError(
            "Renderer tests missing from ci/render-quality-ledger-tests.list:\n"
            + "\n".join(f"  - {m}" for m in missing)
            + "\n\nFix: add them to ci/render-quality-ledger-tests.list."
        )

    all_test_files = {f"tests/{p.name}" for p in TESTS_DIR.glob("test_*.py")}
    stale = sorted(listed_set - all_test_files)
    if stale:
        raise AssertionError(
            "ci/render-quality-ledger-tests.list contains stale test entries:\n"
            + "\n".join(f"  - {s}" for s in stale)
        )


def main() -> int:
    try:
        test_render_quality_ledger_manifest_is_coherent()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1
    print("OK: render-quality-ledger suite is coherent and manifest covers renderer tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
