#!/usr/bin/env python3
"""
pages_publish_paradox_core_bundle_v0.py

Deterministic publisher for the Paradox Core reviewer bundle into a Pages site directory.

Inputs:
  --bundle-dir   Directory produced by scripts/paradox_core_reviewer_bundle_v0.py
  --site-dir     Pages site build output directory (the directory that will be deployed)
  --mount        Mount path within the site (default: paradox/core/v0)
  --write-index  If set, write a tiny index.html redirect to the reviewer card

Copies (fail-closed if missing):
  - paradox_core_v0.json
  - paradox_core_summary_v0.md
  - paradox_core_v0.svg
  - paradox_core_reviewer_card_v0.html

Design goals:
  - CI-neutral (pure publish helper; does not compute semantics)
  - deterministic outputs (stable index.html content; no timestamps)
  - fail-closed if required inputs are missing
  - byte-for-byte copying (no metadata preservation)
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import List


REQUIRED_FILES: List[str] = [
    "paradox_core_v0.json",
    "paradox_core_summary_v0.md",
    "paradox_core_v0.svg",
    "paradox_core_reviewer_card_v0.html",
]


def _fail(msg: str) -> None:
    raise SystemExit(msg)


def _copy_bytes(src: Path, dst: Path) -> None:
    # Copy content only (no mtime/metadata) for deterministic publish behavior.
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def _write_index(dst_dir: Path, target_html: str) -> None:
    # Deterministic redirect page; no timestamps, no dynamic content.
    content = (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8" />\n'
        '  <meta name="viewport" content="width=device-width,initial-scale=1" />\n'
        f'  <meta http-equiv="refresh" content="0; url={target_html}" />\n'
        f"  <link rel=\"canonical\" href=\"{target_html}\" />\n"
        "  <title>Paradox Core Reviewer Card v0</title>\n"
        "</head>\n"
        "<body>\n"
        f'  <p>Redirecting to <a href="{target_html}">{target_html}</a>…</p>\n'
        "</body>\n"
        "</html>\n"
    )
    (dst_dir / "index.html").write_text(content, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--bundle-dir",
        default="out/paradox_core_bundle_v0",
        help="Input bundle directory (default: out/paradox_core_bundle_v0)",
    )
    ap.add_argument(
        "--site-dir",
        required=True,
        help="Pages site build output directory (the directory to be deployed)",
    )
    ap.add_argument(
        "--mount",
        default="paradox/core/v0",
        help="Mount path within the site (default: paradox/core/v0)",
    )
    ap.add_argument(
        "--write-index",
        action="store_true",
        help="Write index.html redirect to paradox_core_reviewer_card_v0.html",
    )
    args = ap.parse_args()

    bundle_dir = Path(args.bundle_dir)
    site_dir = Path(args.site_dir)
    mount = str(args.mount).strip("/")

    if not bundle_dir.exists() or not bundle_dir.is_dir():
        _fail(f"Bundle dir not found: {bundle_dir}")

    target_dir = site_dir / mount
    target_dir.mkdir(parents=True, exist_ok=True)

    # Fail-closed: all required files must exist.
    missing: List[str] = []
    for name in REQUIRED_FILES:
        if not (bundle_dir / name).exists():
            missing.append(name)
    if missing:
        _fail(f"Missing required bundle files in {bundle_dir}: {', '.join(missing)}")

    # Copy files deterministically
    for name in REQUIRED_FILES:
        _copy_bytes(bundle_dir / name, target_dir / name)

    if args.write_index:
        _write_index(target_dir, "paradox_core_reviewer_card_v0.html")

    # Minimal stdout; stable, no timestamps.
    print(f"Published Paradox Core bundle v0 → {target_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
