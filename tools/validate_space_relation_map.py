#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator


DEFAULT_SCHEMA_CANDIDATES = [
    Path("schemas/schemas/space_relation_map_v0.schema.json"),
    Path("schemas/space_relation_map_v0.schema.json"),
]


def _default_schema_path() -> Path:
    for candidate in DEFAULT_SCHEMA_CANDIDATES:
        if candidate.exists():
            return candidate
    return DEFAULT_SCHEMA_CANDIDATES[0]


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def _index_ids(items: list[dict], label: str) -> set[str]:
    seen: set[str] = set()
    dupes: list[str] = []

    for item in items:
        item_id = item["id"]
        if item_id in seen:
            dupes.append(item_id)
        seen.add(item_id)

    if dupes:
        dupes_str = ", ".join(sorted(set(dupes)))
        raise SystemExit(f"ERROR: duplicate {label} id(s): {dupes_str}")

    return seen


def _validate_schema(doc: dict, schema: dict) -> None:
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    if errors:
        lines = ["ERROR: schema validation failed:"]
        for err in errors:
            path = ".".join(str(p) for p in err.path) or "<root>"
            lines.append(f"  - {path}: {err.message}")
        raise SystemExit("\n".join(lines))


def _validate_semantics(doc: dict) -> None:
    spaces = doc["spaces"]
    elements = doc["elements"]
    placements = doc["placements"]
    relations = doc["relations"]
    invariants = doc["invariants"]

    space_ids = _index_ids(spaces, "space")
    element_ids = _index_ids(elements, "element")
    _index_ids(relations, "relation")
    _index_ids(invariants, "invariant")

    placed_elements: set[str] = set()
    for placement in placements:
        element_id = placement["element_id"]
        space_id = placement["space_id"]

        if element_id not in element_ids:
            raise SystemExit(
                f"ERROR: placement references unknown element_id: {element_id}"
            )
        if space_id not in space_ids:
            raise SystemExit(
                f"ERROR: placement references unknown space_id: {space_id}"
            )
        if element_id in placed_elements:
            raise SystemExit(
                f"ERROR: element placed more than once: {element_id}"
            )

        placed_elements.add(element_id)

    for relation in relations:
        for side in ("from", "to"):
            endpoint = relation[side]
            kind = endpoint["kind"]
            ref_id = endpoint["id"]

            if kind == "element":
                if ref_id not in element_ids:
                    raise SystemExit(
                        f"ERROR: relation {relation['id']} references unknown "
                        f"element on {side}: {ref_id}"
                    )
            elif kind == "space":
                if ref_id not in space_ids:
                    raise SystemExit(
                        f"ERROR: relation {relation['id']} references unknown "
                        f"space on {side}: {ref_id}"
                    )
            else:
                raise SystemExit(
                    f"ERROR: relation {relation['id']} has invalid endpoint kind "
                    f"on {side}: {kind}"
                )

    unplaced = sorted(element_ids - placed_elements)
    if unplaced:
        raise SystemExit(
            f"ERROR: unplaced element(s): {', '.join(unplaced)}"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a PULSE space_relation_map_v0 artifact."
    )
    parser.add_argument(
        "artifact",
        help="Path to the space_relation_map_v0 JSON artifact.",
    )
    parser.add_argument(
        "--schema",
        default=str(_default_schema_path()),
        help="Path to the JSON Schema for the artifact.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    artifact_path = Path(args.artifact)
    schema_path = Path(args.schema)

    doc = _load_json(artifact_path)
    schema = _load_json(schema_path)

    _validate_schema(doc, schema)
    _validate_semantics(doc)

    print(
        "OK: space_relation_map_v0 artifact is schema-valid and "
        "reference-consistent"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
