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
  - paradox_diagram_v0.json

Copies (best-effort if present):
  - paradox_diagram_v0.svg

Design goals:
  - CI-neutral (pure publish helper; does not compute semantics)
  - deterministic outputs (stable index.html content; no timestamps)
  - fail-closed if required inputs are missing
  - byte-for-byte copying (no metadata preservation)
  - prevent mount path traversal / escaping site_dir
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path, PurePosixPath
from typing import List


# Required artifacts: publishing must fail-closed if any of these are missing.
REQUIRED_FILES: List[str] = [
    "paradox_core_v0.json",
    "paradox_core_summary_v0.md",
    "paradox_core_v0.svg",
    "paradox_core_reviewer_card_v0.html",
    "paradox_diagram_v0.json",
]

# Best-effort artifacts: copy if present, do not fail if absent.
# Rationale: the reviewer bundle may skip diagram SVG generation in valid invocations
# (e.g., legacy renderer requiring --edges when none are provided).
OPTIONAL_FILES: List[str] = [
    "paradox_diagram_v0.svg",
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
        f'  <link rel="canonical" href="{target_html}" />\n'
        "  <title>Paradox Core Reviewer Card v0</title>\n"
        "</head>\n"
        "<body>\n"
        f'  <p>Redirecting to <a href="{target_html}">{target_html}</a>…</p>\n'
        "</body>\n"
        "</html>\n"
    )
    (dst_dir / "index.html").write_text(content, encoding="utf-8")


def _safe_mount_parts(mount: str) -> List[str]:
    """
    Convert a user-provided mount string into safe path parts.

    Reject:
      - empty mounts
      - backslashes
      - absolute mounts
      - '.' or '..' segments
    """
    m = str(mount).strip()
    if not m:
        _fail("Mount must be non-empty")

    # Enforce forward-slash semantics to avoid platform surprises.
    if "\\" in m:
        _fail("Mount must use forward slashes ('/'), not backslashes ('\\')")

    m = m.strip("/")
    if not m:
        _fail("Mount must not be '/' only")

    p = PurePosixPath(m)
    if p.is_absolute():
        _fail(f"Mount must be relative, got absolute mount: {mount!r}")

    parts = [seg for seg in p.parts if seg]
    for seg in parts:
        if seg in (".", ".."):
            _fail(f"Mount contains forbidden path segment {seg!r}: {mount!r}")
    return parts


def _ensure_within_site(site_dir: Path, target_dir: Path) -> None:
    """
    Fail-closed if target_dir resolves outside site_dir.

    Uses resolve(strict=False) to normalize and follow symlinks if present.
    This prevents publishing outside the intended Pages output directory.
    """
    site_res = site_dir.resolve(strict=False)
    target_res = target_dir.resolve(strict=False)
    try:
        target_res.relative_to(site_res)
    except ValueError:
        _fail(f"Mount escapes site-dir: target={target_res} site={site_res}")


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

    if not bundle_dir.exists() or not bundle_dir.is_dir():
        _fail(f"Bundle dir not found: {bundle_dir}")

    # Ensure site-dir exists before resolving containment.
    site_dir.mkdir(parents=True, exist_ok=True)

    parts = _safe_mount_parts(args.mount)
    target_dir = site_dir.joinpath(*parts)

    # Fail-closed: do not allow mount to escape the site directory.
    _ensure_within_site(site_dir, target_dir)

    target_dir.mkdir(parents=True, exist_ok=True)

    # Fail-closed: all required files must exist.
    missing: List[str] = []
    for name in REQUIRED_FILES:
        if not (bundle_dir / name).exists():
            missing.append(name)
    if missing:
        _fail(f"Missing required bundle files in {bundle_dir}: {', '.join(missing)}")

    # Copy required files deterministically
    for name in REQUIRED_FILES:
        _copy_bytes(bundle_dir / name, target_dir / name)

    # Copy optional files deterministically (best-effort)
    for name in OPTIONAL_FILES:
        src = bundle_dir / name
        if src.exists():
            _copy_bytes(src, target_dir / name)

    if args.write_index:
        _write_index(target_dir, "paradox_core_reviewer_card_v0.html")

    # Minimal stdout; stable, no timestamps.
    print(f"Published Paradox Core bundle v0 → {target_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
