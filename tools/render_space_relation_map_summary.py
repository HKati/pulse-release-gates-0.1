#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def _elements_by_id(doc: dict) -> dict[str, dict]:
    return {element["id"]: element for element in doc["elements"]}


def _placements_by_space(doc: dict) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {space["id"]: [] for space in doc["spaces"]}
    for placement in doc["placements"]:
        mapping.setdefault(placement["space_id"], []).append(placement["element_id"])
    return mapping


def _format_endpoint(endpoint: dict) -> str:
    if endpoint["kind"] == "space":
        return f"space:{endpoint['id']}"
    return endpoint["id"]


def _render_markdown(doc: dict) -> str:
    elements = _elements_by_id(doc)
    placements_by_space = _placements_by_space(doc)

    lines: list[str] = []

    lines.append("# PULSE Space Relation Map v0")
    lines.append("")
    lines.append(f"- Schema: `{doc['schema']}`")
    lines.append(f"- Version: `{doc['version']}`")
    lines.append(f"- Mode: `{doc['mode']}`")
    lines.append(f"- Authority: `{doc['authority']}`")
    lines.append(f"- Spaces: **{len(doc['spaces'])}**")
    lines.append(f"- Elements: **{len(doc['elements'])}**")
    lines.append(f"- Relations: **{len(doc['relations'])}**")
    lines.append(f"- Invariants: **{len(doc['invariants'])}**")
    lines.append("")

    lines.append("## Spaces and placements")
    lines.append("")
    for space in doc["spaces"]:
        space_id = space["id"]
        lines.append(f"### `{space_id}`")
        lines.append("")
        lines.append(f"Role: {space['role']}")
        lines.append("")
        member_ids = placements_by_space.get(space_id, [])
        if member_ids:
            for element_id in member_ids:
                kind = elements.get(element_id, {}).get("kind", "unknown")
                lines.append(f"- `{element_id}` ({kind})")
        else:
            lines.append("- _(no elements)_")
        lines.append("")

    lines.append("## Relations")
    lines.append("")
    for relation in doc["relations"]:
        left = _format_endpoint(relation["from"])
        right = _format_endpoint(relation["to"])
        lines.append(
            f"- `{relation['id']}`: `{left}` **{relation['type']}** `{right}`"
        )
    lines.append("")

    non_override = [
        relation for relation in doc["relations"]
        if relation["type"] == "cannot_override"
    ]
    if non_override:
        lines.append("## Non-override relations")
        lines.append("")
        for relation in non_override:
            left = _format_endpoint(relation["from"])
            right = _format_endpoint(relation["to"])
            lines.append(f"- `{left}` cannot override `{right}`")
        lines.append("")

    promotion = [
        relation for relation in doc["relations"]
        if relation["type"] == "may_promote_if_policy"
    ]
    if promotion:
        lines.append("## Policy-dependent promotion relations")
        lines.append("")
        for relation in promotion:
            left = _format_endpoint(relation["from"])
            right = _format_endpoint(relation["to"])
            lines.append(
                f"- `{left}` may become normatively relevant for `{right}` "
                f"only if policy/workflow promotes it"
            )
        lines.append("")

    lines.append("## Invariants")
    lines.append("")
    for invariant in doc["invariants"]:
        lines.append(f"- `{invariant['id']}`: {invariant['statement']}")
    lines.append("")

    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a markdown summary for a PULSE space_relation_map_v0 artifact."
    )
    parser.add_argument(
        "artifact",
        help="Path to the space_relation_map_v0 JSON artifact.",
    )
    parser.add_argument(
        "--out",
        help="Optional output path for the rendered markdown summary.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    artifact_path = Path(args.artifact)
    doc = _load_json(artifact_path)
    rendered = _render_markdown(doc)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered + "\n", encoding="utf-8")
        print(f"OK: wrote space relation map summary: {out_path}")
    else:
        print(rendered)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
