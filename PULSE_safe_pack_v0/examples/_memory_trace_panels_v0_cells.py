from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import json

import pandas as pd


# All memory / trace artefacts are expected under ../artifacts
ARTIFACT_DIR = Path("../artifacts")


def _ensure_artifact_dir() -> None:
    """
    Make sure the artefact directory exists.
    """
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> Any:
    """
    Best-effort JSON loader.

    - Returns None if the file does not exist.
    - Prints a warning (but does not raise) if parsing fails.
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as exc:
        print(f"[memory-trace] warning: failed to load {path}: {exc}")
        return None


def maybe_load_env(env: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Populate an environment dict with memory/trace artefacts and basic
    DataFrames if they exist under ../artifacts.

    This is safe to call from a notebook driver cell:
    - it will not raise on missing files,
    - it will fall back to empty structures when artefacts are absent.

    The returned env contains (if present):
    - decision_paradox_summary_raw
    - decision_paradox_runs_df
    - paradox_history_raw
    - paradox_axes_df
    - paradox_runs_df
    - paradox_resolution_raw
    - paradox_resolution_df
    """
    if env is None:
        env = {}

    _ensure_artifact_dir()
    env.setdefault("ARTIFACT_DIR", ARTIFACT_DIR)

    # ------------------------------------------------------------------
    # 1) Per-run summaries: decision_paradox_summary_v0.json
    # ------------------------------------------------------------------
    dps_path = ARTIFACT_DIR / "decision_paradox_summary_v0.json"
    dps = _load_json(dps_path)
    if dps is not None:
        env["decision_paradox_summary_raw"] = dps
        # Try a few likely shapes.
        if isinstance(dps, dict):
            if isinstance(dps.get("runs"), list):
                env["decision_paradox_runs_df"] = pd.DataFrame(dps["runs"])
            elif isinstance(dps.get("items"), list):
                env["decision_paradox_runs_df"] = pd.DataFrame(dps["items"])
        elif isinstance(dps, list):
            env["decision_paradox_runs_df"] = pd.DataFrame(dps)
        else:
            env.setdefault("decision_paradox_runs_df", pd.DataFrame())
    else:
        env.setdefault("decision_paradox_summary_raw", {})
        env.setdefault("decision_paradox_runs_df", pd.DataFrame())

    # ------------------------------------------------------------------
    # 2) Aggregated history: paradox_history_v0.json
    # ------------------------------------------------------------------
    ph_path = ARTIFACT_DIR / "paradox_history_v0.json"
    ph = _load_json(ph_path)
    if ph is not None:
        env["paradox_history_raw"] = ph

        axes_df = pd.DataFrame()
        runs_df = pd.DataFrame()

        if isinstance(ph, dict):
            hist = ph.get("paradox_history", ph)

            # Axes-level view
            axes = (
                hist.get("axes")
                or hist.get("axes_history")
                or hist.get("axes_stats")
            )
            if isinstance(axes, list):
                axes_df = pd.DataFrame(axes)

            # Run-level view
            runs = hist.get("runs") or ph.get("runs")
            if isinstance(runs, list):
                runs_df = pd.DataFrame(runs)

        env["paradox_axes_df"] = axes_df
        env["paradox_runs_df"] = runs_df
    else:
        env.setdefault("paradox_history_raw", {})
        env.setdefault("paradox_axes_df", pd.DataFrame())
        env.setdefault("paradox_runs_df", pd.DataFrame())

    # ------------------------------------------------------------------
    # 3) Resolution plan: paradox_resolution_v0.json
    # ------------------------------------------------------------------
    pr_path = ARTIFACT_DIR / "paradox_resolution_v0.json"
    pr = _load_json(pr_path)
    if pr is not None:
        env["paradox_resolution_raw"] = pr

        res_df = pd.DataFrame()
        if isinstance(pr, dict):
            entries = pr.get("axes") or pr.get("items")
            if isinstance(entries, list):
                res_df = pd.DataFrame(entries)
        elif isinstance(pr, list):
            res_df = pd.DataFrame(pr)

        env["paradox_resolution_df"] = res_df
    else:
        env.setdefault("paradox_resolution_raw", {})
        env.setdefault("paradox_resolution_df", pd.DataFrame())

    return env


def run_all_panels(env: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Entry point for the memory / trace dashboard demo.

    For v0 this only prints basic dataset sizes so that the notebook
    can verify wiring without depending on any specific plotting
    library or panel layout.

    Later we can extend this to call concrete panel functions
    (Pareto axes, instability×RDSI quadrants, decision streaks)
    as they stabilise.
    """
    env = maybe_load_env(env)

    dps_df = env.get("decision_paradox_runs_df", None)
    ph_runs_df = env.get("paradox_runs_df", None)
    axes_df = env.get("paradox_axes_df", None)
    res_df = env.get("paradox_resolution_df", None)

    print("[memory-trace] decision_paradox_runs_df rows:",
          0 if dps_df is None else len(dps_df))
    print("[memory-trace] paradox_runs_df rows:",
          0 if ph_runs_df is None else len(ph_runs_df))
    print("[memory-trace] paradox_axes_df rows:",
          0 if axes_df is None else len(axes_df))
    print("[memory-trace] paradox_resolution_df rows:",
          0 if res_df is None else len(res_df))

    # TODO (v1): hook up concrete panels here.
    return env

