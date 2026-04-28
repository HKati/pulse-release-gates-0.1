#!/usr/bin/env python3
"""Insert a release-authority manifest section into a PULSE Quality Ledger HTML file.

This tool is a pure renderer/post-processor.

It reads:
- report_card.html
- release_authority_v0.json, when present

It writes:
- an updated report_card.html or a separate output file

It does not compute or redefine release decisions.
It does not change status.json, gate policy, check_gates.py behavior, or
shadow-layer authority.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


SECTION_START = "<!-- PULSE_RELEASE_AUTHORITY_MANIFEST_SECTION_START -->"
SECTION_END = "<!-- PULSE_RELEASE_AUTHORITY_MANIFEST_SECTION_END -->"


def _load_manifest(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    return data


def _h(value: Any) -> str:
    if value is None:
        return "UNKNOWN"
    if isinstance(value, (list, tuple)):
        return ", ".join(_h(v) for v in value)
    return html.escape(str(value))


def _count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _manifest_summary(manifest: dict[str, Any] | None, manifest_href: str) -> str:
    if manifest is None:
        rows = [
            ("Status", "MISSING/UNKNOWN"),
            ("Role", "Audit / traceability sidecar"),
            ("Authority", "Non-normative / non-blocking"),
            ("Manifest", manifest_href),
        ]
    else:
        run_identity = manifest.get("run_identity") or {}
        authority = manifest.get("authority") or {}
        evaluation = manifest.get("evaluation") or {}
        decision = manifest.get("decision") or {}
        diagnostics = manifest.get("diagnostics") or {}

        effective_required = authority.get("effective_required_gates") or []
        failed = evaluation.get("failed_required_gates") or []
        missing = evaluation.get("missing_required_gates") or []
        advisory_present = diagnostics.get("advisory_gates_present") or []

        rows = [
            ("Status", "PRESENT"),
            ("Manifest", f'<a href="{html.escape(manifest_href)}">{html.escape(manifest_href)}</a>'),
            ("Role", "Audit / traceability sidecar"),
            ("Authority", "Non-normative / non-blocking"),
            ("Decision state", _h(decision.get("state"))),
            ("Run mode", _h(run_identity.get("run_mode"))),
            ("Policy set", _h(authority.get("policy_set"))),
            ("Effective required gates", str(_count(effective_required))),
            ("Failed required gates", str(_count(failed))),
            ("Missing required gates", str(_count(missing))),
            ("Advisory gates present", str(_count(advisory_present))),
            ("Shadow surfaces non-normative", _h(diagnostics.get("shadow_surfaces_non_normative"))),
        ]

    body = [
        SECTION_START,
        '<section id="release-authority-manifest">',
        "<h2>Release authority manifest</h2>",
        "<p><strong>Audit-only surface.</strong> This section links to the release authority manifest when it is available. The manifest records the evidence-policy-evaluator chain for audit and traceability. It does not change release semantics, gate policy, <code>status.json</code>, <code>check_gates.py</code>, or the primary release decision.</p>",
        "<table>",
        "<thead><tr><th>Field</th><th>Value</th></tr></thead>",
        "<tbody>",
    ]

    for key, value in rows:
        # Values that are already anchors are intentionally trusted locally.
        value_s = value if isinstance(value, str) and value.startswith("<a ") else _h(value)
        body.append(f"<tr><td><code>{html.escape(key)}</code></td><td>{value_s}</td></tr>")

    body.extend(
        [
            "</tbody>",
            "</table>",
            "</section>",
            SECTION_END,
        ]
    )
    return "\n".join(body)


def _replace_or_insert(html_text: str, section: str) -> str:
    start = html_text.find(SECTION_START)
    end = html_text.find(SECTION_END)

    if start != -1 and end != -1 and end > start:
        end += len(SECTION_END)
        return html_text[:start] + section + html_text[end:]

    lower = html_text.lower()
    body_close = lower.rfind("</body>")
    if body_close != -1:
        return html_text[:body_close] + section + "\n" + html_text[body_close:]

    return html_text.rstrip() + "\n" + section + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report",
        default="PULSE_safe_pack_v0/artifacts/report_card.html",
        help="Path to report_card.html / Quality Ledger HTML.",
    )
    parser.add_argument(
        "--manifest",
        default="PULSE_safe_pack_v0/artifacts/release_authority_v0.json",
        help="Path to release_authority_v0.json.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Optional output path. Defaults to in-place update of --report.",
    )
    parser.add_argument(
        "--href",
        default=None,
        help="Optional href to use for the manifest link. Defaults to manifest basename.",
    )
    args = parser.parse_args()

    report = Path(args.report)
    manifest_path = Path(args.manifest)
    out = Path(args.out) if args.out else report
    href = args.href or manifest_path.name

    if not report.exists():
        raise SystemExit(f"ERROR: report not found: {report}")

    report_text = report.read_text(encoding="utf-8", errors="replace")
    manifest = _load_manifest(manifest_path)
    section = _manifest_summary(manifest, href)

    updated = _replace_or_insert(report_text, section)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(updated, encoding="utf-8")

    print(f"OK: wrote release authority manifest section to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
