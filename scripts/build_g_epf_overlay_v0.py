#!/usr/bin/env python
"""
Build g_epf_overlay_v0.json from EPF experiment artefacts.

Hard assumptions (matching the current repo design):

- Files live in the repo root:
    - status_baseline.json      # deterministic baseline decisions
    - status_epf.json           # EPF shadow decisions (incl. metrics.epf_L)
    - epf_paradox_summary.json  # structured paradox summary per gate (optional)

- Shape of status_baseline.json / status_epf.json (simplified):

    {
      "run_id": "run_2025_12_02_001",
      "gates": {
        "q1_grounded_ok": {
          "decision": "PASS",
          "value": 0.86
        },
        "q3_fairness_ok": { ... }
      },
      "config": { ... },       # EPF config lives here in the EPF status
      "meta": { ... }          # EPF meta lives here in the EPF status
    }

- Shape of epf_paradox_summary.json (simplified):

    {
      "gates": [
        {
          "id": "q3_fairness_ok",
          "severity": "medium",
          "summary": "EPF flags borderline fairness while baseline is PASS.",
          "type": "epf_vs_baseline"
        },
        ...
      ]
    }

Output (repo root):

    g_epf_overlay_v0.json

Overlay shape is aligned with schemas/g_epf_overlay_v0.schema.json:
top-level version / created_at / source, then meta, summary, panels,
g_field, diagnostics.

This is shadow-only: it never touches the main status.json or any gate.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Paths / basic IO
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent

BASELINE_STATUS_PATH = REPO_ROOT / "status_baseline.json"
EPF_STATUS_PATH = REPO_ROOT / "status_epf.json"
PARADOX_SUMMARY_PATH = REPO_ROOT / "epf_paradox_summary.json"
OUTPUT_OVERLAY_PATH = REPO_ROOT / "g_epf_overlay_v0.json"


def _load_required_json(path: Path, label: str) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found at {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_optional_json(path: Path, label: str) -> Optional[Dict[str, Any]]:
    if not path.exists():
        print(f"[build_g_epf_overlay_v0] INFO: {label} not found at {path}, skipping.")
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _now_iso() -> str:
    # aware, seconds precision
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------------
# Core construction
# ---------------------------------------------------------------------------

def build_panels(
    baseline: Dict[str, Any],
    epf: Dict[str, Any],
    paradox_summary: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Build the 'panels' array for g_epf_overlay_v0.json."""

    baseline_gates = baseline["gates"]  # kemény szerződés: kell
    epf_gates = epf.get("gates", {})

    paradox_by_gate: Dict[str, Dict[str, Any]] = {}
    if paradox_summary is not None:
        for item in paradox_summary.get("gates", []):
            gate_id = item.get("id")
            if gate_id:
                paradox_by_gate[gate_id] = item

    panels: List[Dict[str, Any]] = []

    for gate_id, base_info in baseline_gates.items():
        epf_info = epf_gates.get(gate_id, {})
        paradox_info = paradox_by_gate.get(gate_id)

        baseline_decision = str(base_info.get("decision", "UNKNOWN"))
        epf_decision = str(epf_info.get("decision", "UNKNOWN"))

        in_epf_band = bool(epf_info.get("in_epf_band", False))
        distance_to_threshold = epf_info.get("distance_to_threshold")
        epf_L = (epf_info.get("metrics") or {}).get("epf_L")

        panel: Dict[str, Any] = {
            "panel_id": f"epf_gate_{gate_id}",
            "gate_id": gate_id,
            "baseline_decision": baseline_decision,
            "epf_shadow_decision": epf_decision,
            "in_epf_band": in_epf_band,
            "distance_to_threshold": distance_to_threshold,
            "epf_L": epf_L,
            "risk_band": epf_info.get("risk_band"),
            "paradox": {
                "has_paradox": paradox_info is not None,
                "paradox_type": paradox_info.get("type") if paradox_info else None,
                "severity": paradox_info.get("severity") if paradox_info else None,
                "summary": paradox_info.get("summary") if paradox_info else None,
            },
            "metrics": {
                "baseline_value": base_info.get("value"),
                "epf_value": epf_info.get("value"),
            },
            "notes": [],
        }

        # Kis, determinisztikus note‑logika
        if paradox_info is not None:
            panel["notes"].append("EPF paradox candidate: shadow disagrees with baseline.")
        elif in_epf_band and epf_decision == baseline_decision:
            panel["notes"].append("Inside EPF band; EPF agrees with baseline.")
        elif in_epf_band:
            panel["notes"].append("Inside EPF band; EPF differs from baseline.")

        panels.append(panel)

    return panels


def build_overlay(
    baseline: Dict[str, Any],
    epf: Dict[str, Any],
    paradox_summary: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build full g_epf_overlay_v0 structure."""

    panels = build_panels(baseline, epf, paradox_summary)

    total_gates = len(panels)
    gates_in_epf_band = sum(1 for p in panels if p.get("in_epf_band"))
    gates_changed_by_epf = sum(
        1
        for p in panels
        if p.get("epf_shadow_decision") not in (None, "UNKNOWN")
        and p.get("epf_shadow_decision") != p.get("baseline_decision")
    )
    gates_with_paradox_flag = sum(
        1 for p in panels if p.get("paradox", {}).get("has_paradox")
    )

    # Árulkodó, de egyszerű definíció: ha nincs paradox, shadow_pass = True
    shadow_pass = gates_with_paradox_flag == 0

    now = _now_iso()

    overlay: Dict[str, Any] = {
        # v0 szerződés a sémával
        "version": "g_epf_overlay_v0-auto",
        "created_at": now,
        "source": "epf_experiment_shadow",

        "meta": {
            "overlay_id": "g_epf_overlay_v0",
            "epf_version": (epf.get("meta") or {}).get("epf_version", "unknown"),
            "generated_at": now,
            "source_run_id": baseline.get("run_id"),
            "source_files": [
                "status_baseline.json",
                "status_epf.json",
                "epf_paradox_summary.json",
            ],
        },

        "summary": {
            "total_gates": total_gates,
            "gates_in_epf_band": gates_in_epf_band,
            "gates_changed_by_epf": gates_changed_by_epf,
            "gates_with_paradox_flag": gates_with_paradox_flag,
            "shadow_pass": shadow_pass,
            "notes": [
                "EPF overlay v0 built from EPF experiment artefacts.",
                "Deterministic baseline gates remain the source of truth.",
            ],
        },

        "panels": panels,

        # v0 schema kompat: jelenleg üres, de helyet foglal
        "g_field": {},

        "diagnostics": {
            "epf_band_epsilon": (epf.get("config") or {}).get("epsilon"),
            "max_risk": (epf.get("config") or {}).get("max_risk"),
            "min_samples": (epf.get("config") or {}).get("min_samples"),
        },
    }

    return overlay


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    print("[build_g_epf_overlay_v0] Reading EPF artefacts from repo root…")

    baseline = _load_required_json(BASELINE_STATUS_PATH, "baseline status")
    epf = _load_required_json(EPF_STATUS_PATH, "EPF status")
    paradox = _load_optional_json(PARADOX_SUMMARY_PATH, "EPF paradox summary")

    overlay = build_overlay(baseline, epf, paradox)

    OUTPUT_OVERLAY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_OVERLAY_PATH.open("w", encoding="utf-8") as f:
        json.dump(overlay, f, indent=2, sort_keys=True)

    print(f"[build_g_epf_overlay_v0] Wrote overlay to {OUTPUT_OVERLAY_PATH}")


if __name__ == "__main__":
    main()
