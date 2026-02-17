#!/usr/bin/env python3
"""
Update/normalize artifacts for snapshot publishing.

Design goals:
- Deterministic outputs (sorted file list, stable JSON key order).
- Fail-open: this is a reporting helper, not a release gate.
- Produce a snapshot manifest for audit/debugging and downstream publishing.

Outputs (written next to status.json):
- snapshot_manifest_v1.json
- snapshot_manifest_v1.md
- (optional) index.html copied from report_card.html if index.html is missing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any


def gh_warn(msg: str) -> None:
    print(f"::warning::{msg}")


def gh_notice(msg: str) -> None:
    print(f"::notice::{msg}")


def sha256_file(p: pathlib.Path) -> str | None:
    try:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def safe_read_json(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        gh_warn(f"Failed to read/parse JSON at {path}: {e}")
        return None


def write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: pathlib.Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def iter_artifacts(art_dir: pathlib.Path) -> list[pathlib.Path]:
    """
    Enumerate artifact files deterministically (sorted by relative path).
    Excludes the manifest files themselves to keep output stable.
    """
    exclude_names = {
        "snapshot_manifest_v1.json",
        "snapshot_manifest_v1.md",
    }

    files: list[pathlib.Path] = []
    for p in art_dir.rglob("*"):
        if not p.is_file():
            continue
        if p.name in exclude_names:
            continue
        files.append(p)

    files.sort(key=lambda x: str(x.relative_to(art_dir)))
    return files


def summarize_gates(status: dict[str, Any]) -> dict[str, Any]:
    gates = status.get("gates") or {}
    if not isinstance(gates, dict):
        gates = {}

    items = []
    for k in sorted(gates.keys(), key=lambda x: str(x)):
        ok = (gates.get(k) is True)
        items.append((str(k), ok))

    total = len(items)
    passed = sum(1 for _, ok in items if ok)
    failed = total - passed
    failing = [k for k, ok in items if not ok]

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "all_pass": (failed == 0 and total > 0),
        "failing": failing,
    }


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--status", required=True, help="Path to artifacts/status.json")
    args = ap.parse_args()

    status_path = pathlib.Path(args.status)

    if not status_path.exists():
        gh_warn(f"status.json not found at {status_path}; skipping snapshot artifact update.")
        return 0

    art_dir = status_path.parent
    art_dir.mkdir(parents=True, exist_ok=True)

    status = safe_read_json(status_path)
    if not isinstance(status, dict):
        gh_warn("status.json is not a JSON object; skipping snapshot artifact update.")
        return 0

    version = str(status.get("version", "") or "")
    created_utc = str(status.get("created_utc", "") or "")
    metrics = status.get("metrics") or {}
    if not isinstance(metrics, dict):
        metrics = {}

    run_mode = str(metrics.get("run_mode", "") or "").strip().lower()
    git_sha = metrics.get("git_sha")
    run_key = metrics.get("run_key")

    gate_summary = summarize_gates(status)

    # Ensure common dirs exist (non-fatal helpers)
    (art_dir / "overlay").mkdir(parents=True, exist_ok=True)

    # Optional: if report_card.html exists but index.html does not, copy it.
    report_card = art_dir / "report_card.html"
    index_html = art_dir / "index.html"
    if report_card.exists() and not index_html.exists():
        try:
            index_html.write_text(report_card.read_text(encoding="utf-8"), encoding="utf-8")
            gh_notice(f"Copied report_card.html to index.html: {index_html}")
        except Exception as e:
            gh_warn(f"Failed to copy report_card.html to index.html: {e}")

    # Build deterministic manifest of current artifacts.
    files = iter_artifacts(art_dir)

    file_entries: list[dict[str, Any]] = []
    for p in files:
        rel = str(p.relative_to(art_dir))
        h = sha256_file(p)
        try:
            size = p.stat().st_size
        except Exception:
            size = None

        file_entries.append(
            {
                "path": rel,
                "sha256": h,
                "bytes": size,
            }
        )

    manifest = {
        "schema": "pulse_snapshot_manifest_v1",
        "status": {
            "path": str(status_path),
            "version": version,
            "created_utc": created_utc,
            "run_mode": run_mode,
            "git_sha": git_sha,
            "run_key": run_key,
        },
        "gates": gate_summary,
        "artifacts_dir": str(art_dir),
        "files": file_entries,
    }

    out_json = art_dir / "snapshot_manifest_v1.json"
    out_md = art_dir / "snapshot_manifest_v1.md"

    write_json(out_json, manifest)

    md_lines = []
    md_lines.append("# PULSE snapshot manifest v1")
    md_lines.append("")
    md_lines.append(f"- **version:** `{version}`")
    md_lines.append(f"- **created_utc:** `{created_utc}`")
    md_lines.append(f"- **run_mode:** `{run_mode}`")
    if git_sha:
        md_lines.append(f"- **git_sha:** `{git_sha}`")
    if run_key:
        md_lines.append(f"- **run_key:** `{run_key}`")
    md_lines.append("")
    md_lines.append("## Gate summary")
    md_lines.append(f"- total: **{gate_summary['total']}**")
    md_lines.append(f"- passed: **{gate_summary['passed']}**")
    md_lines.append(f"- failed: **{gate_summary['failed']}**")
    md_lines.append(f"- all_pass: **{str(gate_summary['all_pass']).lower()}**")
    if gate_summary["failing"]:
        md_lines.append("")
        md_lines.append("### Failing gates")
        for g in gate_summary["failing"]:
            md_lines.append(f"- `{g}`")
    md_lines.append("")
    md_lines.append("## Files")
    md_lines.append(f"- count: **{len(file_entries)}**")
    md_lines.append("")
    for ent in file_entries[:200]:
        # keep MD readable; full list is in JSON
        md_lines.append(f"- `{ent['path']}`  ({ent.get('bytes')} bytes)")
    if len(file_entries) > 200:
        md_lines.append(f"- … (+{len(file_entries) - 200} more; see snapshot_manifest_v1.json)")
    md_lines.append("")

    write_text(out_md, "\n".join(md_lines) + "\n")

    print(f"OK: wrote {out_json}")
    print(f"OK: wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
