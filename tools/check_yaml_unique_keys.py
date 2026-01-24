#!/usr/bin/env python3
"""
Fail-closed YAML duplicate-key checker.

Why:
- PyYAML by default accepts duplicate mapping keys and keeps the last one.
- For stable-core files (gate registry, policy, specs) this can silently change meaning.

Exit codes:
- 0: OK
- 2: Duplicate key or YAML parse failure (fail-closed)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

import yaml


def _gh_error(msg: str) -> None:
    print(f"::error::{msg}")


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: UniqueKeyLoader, node: yaml.nodes.MappingNode, deep: bool = False) -> Dict[Any, Any]:
    mapping: Dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)

        # Only hashable keys make sense here; if not hashable, treat as violation.
        try:
            is_dup = key in mapping
        except Exception:
            mark = getattr(key_node, "start_mark", None)
            loc = f"{mark.name}:{mark.line+1}:{mark.column+1}" if mark else "(unknown location)"
            raise ValueError(f"Non-hashable YAML mapping key at {loc}: {repr(key)}")

        if is_dup:
            mark = getattr(key_node, "start_mark", None)
            loc = f"{mark.name}:{mark.line+1}:{mark.column+1}" if mark else "(unknown location)"
            raise ValueError(f"Duplicate YAML key '{key}' at {loc}")

        mapping[key] = loader.construct_object(value_node, deep=deep)

    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


def check_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(str(path))

    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        yaml.load(text, Loader=UniqueKeyLoader)
    except Exception as e:
        raise ValueError(f"{path}: {e}") from e


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="YAML files to validate (no duplicate keys).")
    args = ap.parse_args()

    failures = 0
    for raw in args.files:
        p = Path(raw).resolve()
        try:
            check_file(p)
            print(f"OK: {p}")
        except Exception as e:
            failures += 1
            _gh_error(str(e))

    if failures:
        sys.exit(2)


if __name__ == "__main__":
    main()
