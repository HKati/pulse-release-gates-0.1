#!/usr/bin/env python3
# NOTE: Keep all comments and user-facing messages in this file in English.

"""
PULSE stability map naming guard.

This script enforces a consistent naming convention for the stability map file.

Rules:
- The legacy file name 'stability_map.json' must NOT exist in the repository root.
- The versioned file 'stability_map_v0.json' MUST exist in the repository root.
- No text file in the repository may still refer to 'stability_map.json'.

It is intended to be executed in CI (GitHub Actions) but can also be run locally.
"""

from __future__ import annotations

import pathlib
import sys

TEXT_SUFFIXES = {".md", ".py", ".yml", ".yaml", ".json", ".toml", ".txt"}


def find_repo_root(start: pathlib.Path) -> pathlib.Path:
    """
    Heuristically find the repository root by walking upwards from `start`.

    We treat a directory as the repo root if it contains at least one of:
    - a `.git` directory,
    - a `.github` directory,
    - a `PULSE_safe_pack_v0` directory,
    - a `README.md` file.

    If nothing matches, we fall back to the highest parent.
    """
    start = start.resolve()
    candidates = [start] + list(start.parents)

    for candidate in candidates:
        if (
            (candidate / ".git").exists()
            or (candidate / ".github").is_dir()
            or (candidate / "PULSE_safe_pack_v0").is_dir()
            or (candidate / "README.md").is_file()
        ):
            return candidate

    # Fallback: the top-most parent we know about.
    return candidates[-1]


def main() -> int:
    script_path = pathlib.Path(__file__).resolve()
    root = find_repo_root(script_path)

    legacy = root / "stability_map.json"
    current = root / "stability_map_v0.json"

    errors: list[str] = []

    # 1) The legacy file must not exist anymore.
    if legacy.exists():
        errors.append(
            "Legacy file 'stability_map.json' still exists in the repository root. "
            "Please rename it to 'stability_map_v0.json' and remove the old name."
        )

    # 2) The new versioned file must exist.
    if not current.exists():
        errors.append(
            "Expected file 'stability_map_v0.json' in the repository root, "
            "but it is missing."
        )

    # 3) No text files may still reference the legacy name.
    bad_refs: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Skip binary or non-UTF-8 files.
            continue

        if "stability_map.json" in text:
            rel = path.relative_to(root)
            bad_refs.append(str(rel))

    if bad_refs:
        msg_lines = [
            "Found references to legacy name 'stability_map.json' "
            "in the following files:",
            *[f"  - {p}" for p in bad_refs],
        ]
        errors.append("\n".join(msg_lines))

    if errors:
        print("PULSE stability map naming check FAILED.\n")
        for err in errors:
            print("*", err)
        print(
            "\nThis script is intentionally maintained in English only to keep "
            "repository output consistent."
        )
        return 1

    print("PULSE stability map naming check passed.")
    print("The repository only uses the versioned file name 'stability_map_v0.json'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
