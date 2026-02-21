#!/usr/bin/env python3
"""
Smoke guard: prevent a common GitHub Actions YAML indentation trap.

Failure mode:
- A new step stanza (e.g. "- name: ...") is accidentally indented inside a previous step's `run: |` block.
- YAML still parses, but the runner treats the YAML lines as shell script text and fails in confusing ways.

This guard scans `.github/workflows/*.yml` and `.github/workflows/*.yaml` and fails closed
if it detects step-like lines inside any `run:` block scalar.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import List, Tuple


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"

# "run: |", "run: |-", "run: >", "run: >-" etc.
RUN_BLOCK_START_RE = re.compile(r"^(\s*)run:\s*[|>].*$")

# Step-like YAML list items that must never appear as raw lines inside a run block.
EMBEDDED_STEP_LINE_RE = re.compile(r"^\s*-\s+(name|run|uses)\s*:\s+.+$")


def _scan_workflow(path: Path) -> List[Tuple[int, str]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    hits: List[Tuple[int, str]] = []

    in_run = False
    run_indent = 0

    for idx, line in enumerate(lines, start=1):
        m = RUN_BLOCK_START_RE.match(line)
        if m:
            in_run = True
            run_indent = len(m.group(1))
            continue

        if not in_run:
            continue

        # Still inside a block scalar as long as indentation stays deeper than the `run:` key line.
        if line.strip() == "":
            continue

        indent = len(line) - len(line.lstrip(" "))
        if indent <= run_indent:
            in_run = False
            run_indent = 0
            continue

        if EMBEDDED_STEP_LINE_RE.match(line):
            hits.append((idx, line))

    return hits


def main() -> int:
    if not WORKFLOWS_DIR.is_dir():
        print(f"ERROR: Missing workflows dir: {WORKFLOWS_DIR}")
        return 1

    workflow_files = sorted(list(WORKFLOWS_DIR.glob("*.yml")) + list(WORKFLOWS_DIR.glob("*.yaml")))
    if not workflow_files:
        print(f"ERROR: No workflow files found under: {WORKFLOWS_DIR}")
        return 1

    problems: List[str] = []
    for wf in workflow_files:
        hits = _scan_workflow(wf)
        if hits:
            problems.append(f"{wf}:")
            for lineno, text in hits:
                problems.append(f"  L{lineno}: {text}")

    if problems:
        print("ERROR: Detected embedded workflow step stanzas inside a `run:` block.\n")
        print("\n".join(problems))
        print(
            "\nFix: ensure every '- name:' / '- run:' / '- uses:' stanza is dedented to be a real YAML step,"
            " not part of a previous step's run script."
        )
        return 1

    print("OK: no embedded workflow step stanzas found inside any `run:` block")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
