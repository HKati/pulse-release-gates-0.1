#!/usr/bin/env python3
"""
Fail-closed markdown link checker for repo-local links.

What it checks:
- README.md + docs/**/*.md + PULSE_safe_pack_v0/docs/**/*.md
- Finds Markdown link targets like: ](path) and image links: ![](path)
- Ignores external URLs (http/https/mailto) and pure anchors (#...)
- Resolves relative paths against the linking file’s directory
- Fails if a referenced local file/dir does not exist
- Fails if a problematic nested path like docs/docs exists (common accidental UI mistake)
- Fails on case-collisions inside docs/ and PULSE_safe_pack_v0/docs (Windows/macOS safety)
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Iterable

RE_LINK = re.compile(r"\]\(([^)]+)\)")  # matches both [x](y) and ![x](y)
RE_MD_FILE = re.compile(r".*\.md$", re.IGNORECASE)

EXTERNAL_PREFIXES = ("http://", "https://", "mailto:")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def iter_markdown_files(root: Path) -> Iterable[Path]:
    candidates = []

    readme = root / "README.md"
    if readme.exists():
        candidates.append(readme)

    docs_dir = root / "docs"
    if docs_dir.exists():
        candidates.extend(p for p in docs_dir.rglob("*.md") if p.is_file())

    sp_docs = root / "PULSE_safe_pack_v0" / "docs"
    if sp_docs.exists():
        candidates.extend(p for p in sp_docs.rglob("*.md") if p.is_file())

    # stable ordering
    return sorted(set(candidates), key=lambda p: str(p).lower())


def normalize_target(raw: str) -> str:
    t = raw.strip()

    # Markdown allows an optional title after the destination:
    #   [text](docs/guide.md "Guide")
    # and also allows angle-bracket destinations:
    #   [text](<docs/guide with spaces.md> "Guide")
    #
    # We only want the destination portion here (not the title).
    if t.startswith("<"):
        end = t.find(">")
        if end != -1:
            # Destination is the content inside <...>
            return t[1:end].strip()
        # If malformed, fall back to token parsing below.

    # Non-angle form: destination ends at first whitespace; the rest is the optional title.
    # Example: docs/guide.md "Guide"
    dest = t.split(None, 1)[0].strip()

    # Drop surrounding quotes if present (rare, but keep backward compatibility)
    if (dest.startswith('"') and dest.endswith('"')) or (dest.startswith("'") and dest.endswith("'")):
        dest = dest[1:-1].strip()

    return dest


def is_external_or_anchor(target: str) -> bool:
    if not target:
        return True
    if target.startswith("#"):
        return True
    low = target.lower()
    return low.startswith(EXTERNAL_PREFIXES) or low.startswith("//")


def strip_fragment_and_query(target: str) -> str:
    # remove #fragment and ?query
    t = target.split("#", 1)[0]
    t = t.split("?", 1)[0]
    return t.strip()


def resolve_local_path(linking_file: Path, path_str: str, root: Path) -> Path:
    # GitHub markdown allows root-relative paths that start with "/"
    if path_str.startswith("/"):
        rel = path_str.lstrip("/")
        candidate = (root / rel).resolve()
    else:
        candidate = (linking_file.parent / path_str).resolve()

    # Keep it bounded to the repo (defensive)
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        # points outside repo; treat as invalid local link
        return Path("__OUTSIDE_REPO__")
    return candidate


def check_nested_docs_dir(root: Path) -> list[str]:
    problems: list[str] = []
    bad = root / "docs" / "docs"
    if bad.exists():
        # treat any docs/docs presence as an error to prevent the common slip
        problems.append(f"Found nested directory: {bad} (likely accidental).")
    return problems


def check_case_collisions(root: Path) -> list[str]:
    problems: list[str] = []

    def scan(dirpath: Path) -> None:
        if not dirpath.exists():
            return
        seen: dict[str, Path] = {}
        for p in dirpath.rglob("*"):
            if not p.is_file():
                continue
            rel = str(p.relative_to(root)).replace(os.sep, "/")
            key = rel.lower()
            if key in seen and seen[key] != p:
                problems.append(
                    "Case-collision detected:\n"
                    f"  - {seen[key]}\n"
                    f"  - {p}\n"
                    "These paths differ only by case and may break on case-insensitive filesystems."
                )
            else:
                seen[key] = p

    scan(root / "docs")
    scan(root / "PULSE_safe_pack_v0" / "docs")
    return problems


def extract_link_targets(md_text: str) -> list[str]:
    targets = []
    for m in RE_LINK.finditer(md_text):
        targets.append(m.group(1))
    return targets


def main() -> int:
    root = repo_root()

    errors: list[str] = []
    warnings: list[str] = []

    # structural hygiene checks
    errors.extend(check_nested_docs_dir(root))
    errors.extend(check_case_collisions(root))

    md_files = list(iter_markdown_files(root))
    if not md_files:
        warnings.append("No markdown files found to check.")
    for f in md_files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            errors.append(f"Failed to read {f}: {e}")
            continue

        for raw in extract_link_targets(text):
            target = normalize_target(raw)
            if is_external_or_anchor(target):
                continue

            target_path = strip_fragment_and_query(target)
            if not target_path:
                continue

            # Ignore “empty” or purely dynamic placeholders
            if target_path.startswith("${"):
                continue

            resolved = resolve_local_path(f, target_path, root)
            if str(resolved) == "__OUTSIDE_REPO__":
                errors.append(f"{f}: link points outside repo: ({target})")
                continue

            if not resolved.exists():
                errors.append(f"{f}: missing link target: ({target}) -> {resolved}")

    if warnings:
        print("Warnings:", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)

    if errors:
        print("\nERRORS (fail-closed):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"OK: checked {len(md_files)} markdown files; all local links resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
