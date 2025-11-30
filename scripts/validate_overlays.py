#!/usr/bin/env python
"""
validate_overlays.py

Validate PULSE overlay JSON files against their JSON Schemas.

This script is CI-neutral:
- If a data file is missing, it prints an INFO message and continues.
- If a data file is present but fails validation, it exits with code 1.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Tuple

try:
    import jsonschema
except ImportError:
    sys.stderr.write(
        "[ERROR] jsonschema package is required. Install with `pip install jsonschema`.\n"
    )
    sys.exit(1)


OverlayPair = Tuple[str, Path, Path]


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_overlay(name: str, schema_path: Path, data_path: Path) -> bool:
    if not data_path.is_file():
        sys.stderr.write(
            f"[INFO] {name}: data file not found, skipping: {data_path}\n"
        )
        return True  # missing is not an error in shadow mode

    if not schema_path.is_file():
        sys.stderr.write(
            f"[ERROR] {name}: schema file not found: {schema_path}\n"
        )
        return False

    schema = _load_json(schema_path)
    data = _load_json(data_path)

    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        sys.stderr.write(
            f"[ERROR] {name}: validation failed for {data_path}\n"
        )
        sys.stderr.write(f"  Message: {e.message}\n")
        if e.path:
            sys.stderr.write(
                f"  Path: {'/'.join(map(str, e.path))}\n"
            )
        return False

    sys.stderr.write(
        f"[INFO] {name}: OK ({data_path} matches {schema_path})\n"
    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate overlay JSON files against their JSON Schemas."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory of the repo (default: current directory).",
    )
    args = parser.parse_args()
    root = Path(args.root)

    overlays: List[OverlayPair] = [
        (
            "g_field_v0",
            root / "schemas" / "g_field_v0.schema.json",
            root / "PULSE_safe_pack_v0" / "artifacts" / "g_field_v0.json",
        ),
        (
            "g_field_stability_v0",
            root / "schemas" / "g_field_stability_v0.schema.json",
            root / "PULSE_safe_pack_v0" / "artifacts" / "g_field_stability_v0.json",
        ),
        (
            "g_epf_overlay_v0",
            root / "schemas" / "g_epf_overlay_v0.schema.json",
            root / "PULSE_safe_pack_v0" / "artifacts" / "g_epf_overlay_v0.json",
        ),
        (
            "gpt_external_detection_v0",
            root / "schemas" / "gpt_external_detection_v0.schema.json",
            root / "PULSE_safe_pack_v0" / "artifacts" / "gpt_external_detection_v0.json",
        ),
    ]

    all_ok = True
    for name, schema_path, data_path in overlays:
        ok = _validate_overlay(name, schema_path, data_path)
        if not ok:
            all_ok = False

    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
