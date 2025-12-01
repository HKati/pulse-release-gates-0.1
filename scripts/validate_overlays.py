#!/usr/bin/env python
"""
validate_overlays.py

Validate PULSE overlay JSON files against their JSON Schemas.

This script is CI-neutral:
- If a data file is missing, it prints an INFO message and continues.
- If a data file is present but fails validation, it exits with code 1.

Note: the g_field_stability_v0 overlay is diagnostic-only for now and is
not part of this validation script.
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

try:
    import jsonschema
except ImportError:
    sys.stderr.write(
        "[ERROR] jsonschema package is required. Install with "
        "`pip install jsonschema`.\n"
    )
    sys.exit(1)


@dataclass
class OverlayConfig:
    name: str
    schema_candidates: Sequence[Path]
    data_candidates: Sequence[Path]


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _first_existing(candidates: Sequence[Path]) -> Optional[Path]:
    for p in candidates:
        if p.is_file():
            return p
    return None


def _validate_overlay(name: str, schema_path: Path, data_path: Path) -> bool:
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
            sys.stderr.write(f"  Path: {'/'.join(map(str, e.path))}\n")
        sys.stderr.write(f"  Schema: {schema_path}\n")
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
    root = Path(args.root).resolve()

    # Helper to make candidate lists shorter to write.
    def sp(*parts: str) -> Path:
        return root.joinpath(*parts)

    overlays: List[OverlayConfig] = [
        OverlayConfig(
            name="g_field_v0",
            schema_candidates=[
                sp("schemas", "g_field_v0.schema.json"),
                sp("schemas", "schemas", "g_field_v0.schema.json"),
            ],
            data_candidates=[
                sp("PULSE_safe_pack_v0", "artifacts", "g_field_v0.json"),
                sp("g_field_v0.json"),
            ],
        ),
        # g_field_stability_v0 is intentionally not validated here yet;
        # it is a diagnostic-only overlay and its contract is still evolving.
        OverlayConfig(
            name="g_epf_overlay_v0",
            schema_candidates=[
                sp("schemas", "g_epf_overlay_v0.schema.json"),
                sp("schemas", "schemas", "g_epf_overlay_v0.schema.json"),
            ],
            data_candidates=[
                sp("PULSE_safe_pack_v0", "artifacts", "g_epf_overlay_v0.json"),
                sp("g_epf_overlay_v0.json"),
            ],
        ),
        OverlayConfig(
            name="gpt_external_detection_v0",
            schema_candidates=[
                sp("schemas", "gpt_external_detection_v0.schema.json"),
                sp("schemas", "schemas", "gpt_external_detection_v0.schema.json"),
            ],
            data_candidates=[
                sp(
                    "PULSE_safe_pack_v0",
                    "artifacts",
                    "gpt_external_detection_v0.json",
                ),
                sp("gpt_external_detection_v0.json"),
            ],
        ),
    ]

    all_ok = True

    for cfg in overlays:
        schema_path = _first_existing(cfg.schema_candidates)
        data_path = _first_existing(cfg.data_candidates)

        if data_path is None:
            sys.stderr.write(
                f"[INFO] {cfg.name}: data file not found, skipping.\n"
            )
            continue

        if schema_path is None:
            sys.stderr.write(
                f"[ERROR] {cfg.name}: schema file not found under any of:\n"
            )
            for cand in cfg.schema_candidates:
                sys.stderr.write(f"  - {cand}\n")
            all_ok = False
            continue

        ok = _validate_overlay(cfg.name, schema_path, data_path)
        if not ok:
            all_ok = False

    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
