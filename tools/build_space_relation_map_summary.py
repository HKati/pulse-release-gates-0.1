#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "tools" / "validate_space_relation_map.py"
RENDERER = REPO_ROOT / "tools" / "render_space_relation_map_summary.py"

DEFAULT_ARTIFACT = REPO_ROOT / "examples" / "space_relation_map_v0.manual.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "topology" / "space_relation_map_v0_summary.md"
DEFAULT_SCHEMA_CANDIDATES = [
    REPO_ROOT / "schemas" / "schemas" / "space_relation_map_v0.schema.json",
    REPO_ROOT / "schemas" / "space_relation_map_v0.schema.json",
]


def _default_schema_path() -> Path:
    for candidate in DEFAULT_SCHEMA_CANDIDATES:
        if candidate.exists():
            return candidate
    return DEFAULT_SCHEMA_CANDIDATES[0]

def _repo_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _run(label: str, *args: Path | str) -> None:
    cp = subprocess.run(
        [sys.executable, *(str(a) for a in args)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if cp.returncode != 0:
        combined = (cp.stdout or "") + (cp.stderr or "")
        raise SystemExit(f"ERROR: {label} failed\n{combined}".rstrip())


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and render the PULSE space_relation_map_v0 summary."
    )
    parser.add_argument(
        "--artifact",
        default=str(DEFAULT_ARTIFACT),
        help="Path to the space_relation_map_v0 JSON artifact.",
    )
    parser.add_argument(
        "--schema",
        default=str(_default_schema_path()),
        help="Path to the JSON Schema for the artifact.",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUTPUT),
        help="Output path for the rendered markdown summary.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

     artifact = _repo_path(args.artifact)
    schema = _repo_path(args.schema)
    out = _repo_path(args.out)

    _run(
        "space relation map validation",
        VALIDATOR,
        artifact,
        "--schema",
        schema,
    )

    out.parent.mkdir(parents=True, exist_ok=True)

    _run(
        "space relation map summary render",
        RENDERER,
        artifact,
        "--out",
        out,
    )

    print(f"OK: built space relation map summary: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
