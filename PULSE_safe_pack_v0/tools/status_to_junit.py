#!/usr/bin/env python3
"""
Export PULSE gate results from status.json to a JUnit XML report.

Design goals:
- Deterministic output (sorted gates, stable formatting).
- Backwards compatible CLI/env interface:
    * --status optional; falls back to $PULSE_STATUS, then pack artifacts/status.json
    * --out optional; falls back to $PULSE_JUNIT, then ./reports/junit.xml
- Read contract-aligned gates from status["gates"].

NOTE:
- This is a reporting helper. Fail-closed enforcement is handled by check_gates.py.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from typing import Any


def gh_warn(msg: str) -> None:
    print(f"::warning::{msg}")


def gh_error(msg: str) -> None:
    print(f"::error::{msg}")


def safe_read_json(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        gh_error(f"Failed to read/parse JSON at {path}: {e}")
        return None


def _boolish(v: Any) -> bool:
    # Only literal True counts as pass (consistent with fail-closed conventions)
    return v is True


def _default_status_path() -> pathlib.Path:
    # Preferred: env override (legacy interface)
    env = os.getenv("PULSE_STATUS")
    if isinstance(env, str) and env.strip():
        return pathlib.Path(env.strip())

    # Fallback: pack-local default
    pack_root = pathlib.Path(__file__).resolve().parents[1]  # PULSE_safe_pack_v0
    return pack_root / "artifacts" / "status.json"


def _default_out_path() -> pathlib.Path:
    # Preferred: env override (legacy interface)
    env = os.getenv("PULSE_JUNIT")
    if isinstance(env, str) and env.strip():
        return pathlib.Path(env.strip())

    # Fallback: repo-root relative default (matches workflow artifact path)
    return pathlib.Path("reports") / "junit.xml"


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument(
        "--status",
        default="",
        help="Path to status.json (default: $PULSE_STATUS or pack artifacts/status.json)",
    )
    ap.add_argument(
        "--out",
        default="",
        help="Output path for JUnit XML (default: $PULSE_JUNIT or ./reports/junit.xml)",
    )
    ap.add_argument("--suite", default="PULSE gates", help="JUnit testsuite name")
    args = ap.parse_args()

    status_path = pathlib.Path(args.status) if str(args.status).strip() else _default_status_path()
    out_path = pathlib.Path(args.out) if str(args.out).strip() else _default_out_path()

    if not status_path.exists():
        gh_warn(f"status.json not found at {status_path}; skipping JUnit export.")
        return 0

    status = safe_read_json(status_path)
    if not isinstance(status, dict):
        gh_warn("status.json is not a JSON object; skipping JUnit export.")
        return 0

    gates = status.get("gates") or {}
    metrics = status.get("metrics") or {}
    if not isinstance(gates, dict):
        gates = {}
    if not isinstance(metrics, dict):
        metrics = {}

    version = str(status.get("version", "") or "")
    created_utc = str(status.get("created_utc", "") or "")
    run_mode = str(metrics.get("run_mode", "") or "").strip().lower()

    gate_names = sorted((str(k) for k in gates.keys()), key=lambda x: x)
    total = len(gate_names)
    failures = 0

    ts = created_utc.strip() or datetime.now(timezone.utc).isoformat()

    testsuite = ET.Element(
        "testsuite",
        attrib={
            "name": str(args.suite),
            "tests": str(total),
            "failures": "0",  # fill later
            "errors": "0",
            "skipped": "0",
            "timestamp": ts,
        },
    )

    props = ET.SubElement(testsuite, "properties")
    ET.SubElement(props, "property", attrib={"name": "status_path", "value": str(status_path)})
    if version:
        ET.SubElement(props, "property", attrib={"name": "status_version", "value": version})
    if created_utc:
        ET.SubElement(props, "property", attrib={"name": "created_utc", "value": created_utc})
    if run_mode:
        ET.SubElement(props, "property", attrib={"name": "run_mode", "value": run_mode})

    for name in gate_names:
        ok = _boolish(gates.get(name))
        tc = ET.SubElement(
            testsuite,
            "testcase",
            attrib={
                "classname": "PULSE.gates",
                "name": name,
                "time": "0",
            },
        )
        if not ok:
            failures += 1
            val = gates.get(name)
            msg = f"Gate failed: {name}"
            failure = ET.SubElement(tc, "failure", attrib={"message": msg, "type": "gate_failed"})
            failure.text = f"status.gates[{name!r}]={val!r}"

    testsuite.set("failures", str(failures))

    out_path.parent.mkdir(parents=True, exist_ok=True)

    tree = ET.ElementTree(testsuite)
    try:
        ET.indent(tree, space="  ", level=0)
    except Exception:
        pass

    try:
        tree.write(out_path, encoding="utf-8", xml_declaration=True)
    except Exception as e:
        gh_error(f"Failed to write JUnit XML to {out_path}: {e}")
        return 1

    print(f"OK: wrote JUnit report: {out_path} (tests={total}, failures={failures})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
