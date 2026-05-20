#!/usr/bin/env python3
"""Build hpc_evidence_bundle_v0 diagnostic evidence bundles.

This builder does not run HPC jobs.

It materializes a diagnostic evidence bundle from structured run input:
- run identity;
- code identity;
- input manifest identity;
- environment identity;
- evidence items;
- summary metrics;
- provenance;
- reconstruction instructions.

The produced artifact is non-normative and does not create release authority.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCHEMA = "hpc_evidence_bundle_v0"
AUTHORITY_STATUS = "diagnostic_non_normative"


def _load_json_object(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(obj, dict):
        raise ValueError(f"{path} must contain a JSON object")

    return obj


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _require_object(name: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")

    return value


def _require_list(name: str, value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be an array")

    if not value:
        raise ValueError(f"{name} must not be empty")

    out: list[dict[str, Any]] = []

    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{name}[{index}] must be an object")
        out.append(item)

    return out


def _evidence_result(evidence_items: list[dict[str, Any]]) -> str:
    statuses = [item.get("evidence_status") for item in evidence_items]

    if all(status == "present" for status in statuses):
        return "complete"

    return "incomplete"


def build(input_obj: dict[str, Any]) -> dict[str, Any]:
    run_identity = _require_object(
        "run_identity",
        input_obj.get("run_identity"),
    )
    code_identity = _require_object(
        "code_identity",
        input_obj.get("code_identity"),
    )
    input_manifest = _require_object(
        "input_manifest",
        input_obj.get("input_manifest"),
    )
    environment = _require_object(
        "environment",
        input_obj.get("environment"),
    )
    evidence_items = _require_list(
        "evidence_items",
        input_obj.get("evidence_items"),
    )
    summary_metrics = _require_object(
        "summary_metrics",
        input_obj.get("summary_metrics"),
    )
    provenance = _require_object(
        "provenance",
        input_obj.get("provenance"),
    )
    reconstruction = _require_object(
        "reconstruction",
        input_obj.get("reconstruction"),
    )

    result = _evidence_result(evidence_items)

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "authority_status": AUTHORITY_STATUS,
        "creates_release_authority": False,
        "run_identity": run_identity,
        "code_identity": code_identity,
        "input_manifest": input_manifest,
        "environment": environment,
        "evidence_items": evidence_items,
        "summary_metrics": summary_metrics,
        "provenance": provenance,
        "reconstruction": reconstruction,
        "result": result,
    }

    notes = input_obj.get("notes")
    if isinstance(notes, str) and notes:
        out["notes"] = notes

    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an hpc_evidence_bundle_v0 diagnostic evidence artifact."
    )
    parser.add_argument("--input", required=True, help="Input bundle JSON.")
    parser.add_argument("--out", required=True, help="Output diagnostic JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        input_obj = _load_json_object(Path(args.input))
        output_obj = build(input_obj)
        _write_json(Path(args.out), output_obj)
    except Exception as exc:
        print(f"::error::failed to build hpc_evidence_bundle_v0: {exc}")
        return 1

    print(f"OK: wrote hpc_evidence_bundle_v0 artifact: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
