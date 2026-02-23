#!/usr/bin/env python3
"""
CI guard (mechanical): detect phantom tool/script references.

Checks:
- Every non-comment line in ci/tools-tests.list must exist as a repo path.
- Static "python .../*.py" and "bash .../*.sh" references inside .github/workflows/*.yml must exist.

Notes:
- This is mechanical hygiene only. It does not interpret gate semantics.
- Dynamic references (with ${{ }}, $, wildcards) are skipped.
"""

from __future__ import annotations

import pathlib
import re
import sys
from typing import Iterable


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
TOOLS_LIST = ROOT / "ci" / "tools-tests.list"

# Matches: python [-u|-B|...] path/to/script.py
PY_CALL_RE = re.compile(
    r"""\bpython(?:3)?(?:\s+[-\w]+)*\s+(?P<q>["']?)(?P<path>[A-Za-z0-9_./-]+\.py)(?P=q)\b"""
)

# Matches: bash path/to/script.sh
BASH_CALL_RE = re.compile(
    r"""\bbash(?:\s+[-\w]+)*\s+(?P<q>["']?)(?P<path>[A-Za-z0-9_./-]+\.sh)(?P=q)\b"""
)

DYNAMIC_TOKENS = ("${{", "}}", "$", "*", "?", "[", "]")


def is_dynamic(s: str) -> bool:
    return any(t in s for t in DYNAMIC_TOKENS)


def iter_workflow_files() -> Iterable[pathlib.Path]:
    if not WORKFLOWS_DIR.exists():
        return []
    return sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))


def check_tools_list(missing: list[tuple[str, str]]) -> None:
    if not TOOLS_LIST.exists():
        missing.append((str(TOOLS_LIST.relative_to(ROOT)), "FILE_MISSING"))
        return

    for raw in TOOLS_LIST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # tools-tests.list is "one path per line"
        if is_dynamic(line):
            continue
        p = (ROOT / line).resolve()
        if not p.exists():
            missing.append((str(TOOLS_LIST.relative_to(ROOT)), line))


def check_workflows(missing: list[tuple[str, str]]) -> None:
    for wf in iter_workflow_files():
        rel = str(wf.relative_to(ROOT))
        for raw in wf.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            for m in PY_CALL_RE.finditer(line):
                path = m.group("path")
                if is_dynamic(path):
                    continue
                p = (ROOT / path).resolve()
                if not p.exists():
                    missing.append((rel, path))

            for m in BASH_CALL_RE.finditer(line):
                path = m.group("path")
                if is_dynamic(path):
                    continue
                p = (ROOT / path).resolve()
                if not p.exists():
                    missing.append((rel, path))


def main() -> int:
    missing: list[tuple[str, str]] = []

    check_tools_list(missing)
    check_workflows(missing)

    if missing:
        print("ERROR: phantom/missing path references detected:\n", file=sys.stderr)
        for src, ref in missing:
            print(f"  - {src}: {ref}", file=sys.stderr)
        print("\nFix: remove the reference, guard it properly, or add the missing file.", file=sys.stderr)
        return 1

    print("OK: no phantom tool/script references found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
