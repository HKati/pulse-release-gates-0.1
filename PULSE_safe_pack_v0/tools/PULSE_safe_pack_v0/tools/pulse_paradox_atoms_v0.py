#!/usr/bin/env python3
"""
pulse_paradox_atoms_v0.py

Paradox atom detector for PULSE.

Reads a set of status.json artefacts, builds a run × gate PASS/FAIL matrix,
and finds minimal unsatisfiable gate-sets (paradox atoms) up to a given
maximum size. Outputs a paradox_field_v0 JSON artefact.

This is a diagnostic tool. It does NOT affect core PULSE gating or CI
(check_gates.py). It is intended to feed the Topology v0 / paradox_field_v0
layer and dashboards.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
from itertools import combinations
from typing import Dict, List, Mapping, MutableMapping


def _iter_status_paths(
    status_dir: pathlib.Path,
    exclude: pathlib.Path | None = None,
) -> list[pathlib.Path]:
    """
    Collect candidate status.json files under status_dir.

    We skip the `exclude` path (typically the paradox_field_v0 output file)
    to avoid self-contamination on reruns.
    """
    paths: list[pathlib.Path] = []
    exclude_resolved = exclude.resolve() if exclude is not None else None

    for path in status_dir.rglob("*.json"):
        if not path.is_file():
            continue
        if exclude_resolved is not None and path.resolve() == exclude_resolved:
            # Skip our own output (or any explicitly excluded file).
            continue
        paths.append(path)

    return paths


def load_status_files(
    status_dir: pathlib.Path,
    exclude: pathlib.Path | None = None,
) -> dict[str, dict]:
    """
    Load JSON files that look like PULSE status artefacts.

    We:
      - skip the exclude path (typically the paradox_field_v0 output), and
      - ignore JSON files that don't have a top-level 'results' dict, or that
        clearly belong to other artefact types (e.g. paradox_field_v0).
    """
    status_by_run: dict[str, dict] = {}

    for path in _iter_status_paths(status_dir, exclude=exclude):
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            # Best-effort: skip files that are not valid JSON.
            continue

        # Skip known non-status artefacts explicitly.
        if "paradox_field_v0" in data or "stability_map_v0" in data:
            continue

        results = data.get("results")
        if not isinstance(results, dict):
            # Not a PULSE status artefact (no results block).
            continue

        run_block = data.get("run", {})
        run_id = (
            run_block.get("run_id")
            or run_block.get("timestamp_utc")
            or run_block.get("commit")
            or path.stem
        )

        status_by_run[str(run_id)] = data

    return status_by_run


def _flatten_bool_gates(
    obj: Mapping[str, object],
    prefix: str,
    out: MutableMapping[str, bool],
) -> None:
    """
    Recursively collect boolean fields as gates, using dotted paths as names.

    Example:
      results["quality"]["q3_fairness_ok"] -> "quality.q3_fairness_ok"
    """
    for key, value in obj.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, bool):
            out[path] = value
        elif isinstance(value, dict):
            _flatten_bool_gates(value, path, out)
        # Non-bool, non-dict values are ignored here.


def extract_gate_matrix(status_by_run: Dict[str, dict]) -> Dict[str, Dict[str, bool]]:
    """
    Project status.json into a simple run × gate -> bool matrix.

    We look under status["results"] if present; otherwise we scan the whole
    object. Gate names are flattened dotted paths (e.g. "quality.q3_fairness_ok").
    """
    matrix: Dict[str, Dict[str, bool]] = {}

    for run_id, status in status_by_run.items():
        gates: Dict[str, bool] = {}
        root = status.get("results")
        if isinstance(root, dict):
            _flatten_bool_gates(root, "", gates)
        else:
            # Fallback: scan entire document.
            _flatten_bool_gates(status, "", gates)

        matrix[run_id] = gates

    return matrix


def all_runs_support_subset(
    run_gates: Dict[str, Dict[str, bool]],
    gate_subset: List[str],
) -> bool:
    """
    Return True if some run passes all gates in gate_subset.
    """
    for gates in run_gates.values():
        if all(gates.get(g, False) for g in gate_subset):
            return True
    return False


def find_paradox_atoms(
    run_gates: Dict[str, Dict[str, bool]],
    max_size: int = 4,
) -> List[List[str]]:
    """
    Find minimal unsatisfiable gate-sets up to size max_size.

    A gate-set S is a paradox atom if:

      1) No run passes all gates in S.
      2) Every proper subset of S is satisfiable
         (some run passes all gates in that subset).

    This is analogous to finding minimal unsatisfiable sets (MUS) over the
    empirical gate field defined by the runs.
    """
    gate_names: List[str] = sorted({g for gates in run_gates.values() for g in gates})
    atoms: List[List[str]] = []

    for size in range(2, max_size + 1):
        for subset in combinations(gate_names, size):
            subset_list = list(subset)

            # Condition 1: unsatisfiable (no run passes all gates in S).
            if all_runs_support_subset(run_gates, subset_list):
                continue

            # Condition 2: minimal (all proper subsets satisfiable).
            minimal = True
            for k in range(1, size):
                if not minimal:
                    break
                for sub in combinations(subset_list, k):
                    if not all_runs_support_subset(run_gates, list(sub)):
                        minimal = False
                        break

            if minimal:
                atoms.append(subset_list)

    return atoms


def compute_severity(
    atom: List[str],
    run_gates: Dict[str, Dict[str, bool]],
) -> float:
    """
    Compute a simple severity score in [0, 1]:

      - For each proper subset of the atom, count how many runs support it.
      - Take the minimum support ratio across all proper subsets.
      - Severity = 1 - min_support_ratio.

    Intuition:
      Paradoxons are 'harder' if all their proper subsets are well-supported by
      many runs, but the full set is impossible.
    """
    from math import inf

    runs_count = max(len(run_gates), 1)
    min_support = inf

    for k in range(1, len(atom)):
        for sub in combinations(atom, k):
            support = 0
            for gates in run_gates.values():
                if all(gates.get(g, False) for g in sub):
                    support += 1
            if support < min_support:
                min_support = support

    if min_support is inf:
        # Degenerate case: no subset is ever satisfied.
        return 1.0

    ratio = min_support / float(runs_count)
    return float(1.0 - ratio)


def build_paradox_field(
    run_gates: Dict[str, Dict[str, bool]],
    status_dir: pathlib.Path,
    max_size: int = 4,
) -> dict:
    """
    Build a paradox_field_v0 structure from a run × gate matrix.

    The shape is compatible with schemas/PULSE_paradox_field_v0.schema.json:

      {
        "paradox_field_v0": {
          "version": "PULSE_paradox_field_v0",
          "generated_at_utc": "...",
          "source": { ... },
          "atoms": [ ... ]
        }
      }
    """
    atoms = find_paradox_atoms(run_gates, max_size=max_size)

    paradox_atoms = []
    for idx, gates in enumerate(atoms):
        sev = compute_severity(gates, run_gates)
        atom_id = f"atom_{idx:04d}"
        paradox_atoms.append(
            {
                "atom_id": atom_id,
                "gates": gates,
                "minimal": True,
                "severity": sev,
            }
        )

    now = _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    paradox_field = {
        "paradox_field_v0": {
            "version": "PULSE_paradox_field_v0",
            "generated_at_utc": now,
            "source": {
                "status_dir": str(status_dir),
                "max_atom_size": max_size,
                "run_count": len(run_gates),
            },
            "atoms": paradox_atoms,
        }
    }

    return paradox_field


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compute paradox_field_v0 from PULSE status.json artefacts.\n"
            "This is a diagnostic Topology v0 tool. "
            "It does not affect CI or check_gates.py."
        )
    )
    parser.add_argument(
        "--status-dir",
        type=pathlib.Path,
        required=True,
        help="Directory containing status*.json artefacts (searched recursively).",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        required=True,
        help="Output JSON file for paradox_field_v0.",
    )
    parser.add_argument(
        "--max-atom-size",
        type=int,
        default=4,
        help="Maximum paradox atom size (number of gates). Default: 4.",
    )

    args = parser.parse_args()

    status_dir = args.status_dir
    status_by_run = load_status_files(status_dir, exclude=args.output)
    run_gates = extract_gate_matrix(status_by_run)
    paradox_field = build_paradox_field(
        run_gates, status_dir, max_size=args.max_atom_size
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(paradox_field, f, indent=2, sort_keys=True)

    print(f"[PULSE] paradox_field_v0 written to {args.output}")


if __name__ == "__main__":
    main()
