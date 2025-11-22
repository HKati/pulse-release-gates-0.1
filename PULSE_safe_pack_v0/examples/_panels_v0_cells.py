# _panels_v0_cells.py
# Panel logic for the PULSE trace dashboard demo (v0).
from pathlib import Path
from typing import Dict, Any, Optional, List

import re
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Severity helpers
# ---------------------------------------------------------------------------
from typing import Any
import math
import pandas as pd


def compute_severity_from_tension(tension: Any) -> str:
    """
    Map a tension value to a severity bucket.

    Expected input:
      - numeric in [0.0, 1.0], but we try to be defensive.

    Buckets:
      LOW      : [0.00, 0.25)
      MEDIUM   : [0.25, 0.50)
      HIGH     : [0.50, 0.75)
      CRITICAL : [0.75, 1.00]
      UNKNOWN  : anything missing / invalid
    """
    if tension is None:
        return "UNKNOWN"

    try:
        t = float(tension)
    except (TypeError, ValueError):
        return "UNKNOWN"

    if math.isnan(t):
        return "UNKNOWN"

    # clamp to [0, 1]
    t = max(0.0, min(1.0, t))

    if t < 0.25:
        return "LOW"
    elif t < 0.50:
        return "MEDIUM"
    elif t < 0.75:
        return "HIGH"
    else:
        return "CRITICAL"


def ensure_severity_column(df_runs: pd.DataFrame, source_col: str = "max_tension") -> pd.DataFrame:
    """
    Ensure that df_runs has a 'severity' column.

    Rules:
      - If 'severity' already exists and has at least one non-null value,
        we keep it as-is.
      - Otherwise, if `source_col` exists, we derive severity from it
        using `compute_severity_from_tension`.
      - If neither is available, we fall back to 'UNKNOWN' everywhere.
    """
    if "severity" in df_runs.columns:
        # If there is at least one non-null / non-empty value, respect it.
        if df_runs["severity"].notna().any():
            return df_runs

    if source_col in df_runs.columns:
        df_runs["severity"] = df_runs[source_col].apply(compute_severity_from_tension)
    else:
        # No source tension field available; give a safe default.
        df_runs["severity"] = "UNKNOWN"

    return df_runs
def panel_paradox_axes_pareto(glob: Dict[str, Any]) -> None:
    """
    Pareto-coverage view for paradox axes.

    Goal:
      Show which few axes cover most of the runs
      (runs_seen / total_runs), with a cumulative
      Pareto curve on the same plot.
    """

    env = glob.get("env", {})
    runs_df = env.get("runs_df")
    axes_df = env.get("axes_df")

    if runs_df is None or axes_df is None:
        print("[pareto] runs_df or axes_df missing – skipping Pareto panel.")
        return

    if not isinstance(runs_df, pd.DataFrame) or runs_df.empty:
        print("[pareto] runs_df is not a DataFrame or is empty – skipping Pareto panel.")
        return

    if not isinstance(axes_df, pd.DataFrame) or axes_df.empty:
        print("[pareto] axes_df is not a DataFrame or is empty – skipping Pareto panel.")
        return

    if "axis_id" not in axes_df.columns:
        print("[pareto] axes_df has no 'axis_id' column – cannot build Pareto view.")
        return

    # Prefer an explicit run-count column if present.
    if "runs_seen" in axes_df.columns:
        count_col = "runs_seen"
    else:
        # Fallback: count by axis_id from runs_df.
        if "axis_id" not in runs_df.columns:
            print("[pareto] No 'runs_seen' or 'axis_id' in runs_df – skipping.")
            return
        counts = runs_df["axis_id"].value_counts().rename("runs_seen")
        axes_df = axes_df.merge(
            counts, how="left", left_on="axis_id", right_index=True
        ).fillna({"runs_seen": 0})
        count_col = "runs_seen"

    # Basic stats.
    df = axes_df.copy()
    df = df.sort_values(count_col, ascending=False)
    total_runs = df[count_col].sum()

    if total_runs <= 0:
        print("[pareto] total_runs is 0 – nothing to plot.")
        return

    df["coverage"] = df[count_col] / float(total_runs)
    df["cum_coverage"] = df["coverage"].cumsum()

    # Find how many axes cover ~80% of runs.
    eighty_cutoff = (df["cum_coverage"] >= 0.8).idxmax()
    num_axes_80 = df.index.get_loc(eighty_cutoff) + 1

    print(f"[pareto] {num_axes_80} axes cover ~80% of runs.")

    # Plot: bar for coverage + line for cumulative coverage.
    plt.figure(figsize=(8, 4))
    plt.bar(range(len(df)), df["coverage"], alpha=0.6, label="Per-axis coverage")
    plt.plot(range(len(df)), df["cum_coverage"], marker="o", label="Cumulative")
    plt.axhline(0.8, color="red", linestyle="--", label="80%")
    plt.title("Paradox axes Pareto coverage")
    plt.xlabel("Axes (sorted by coverage)")
    plt.ylabel("Fraction of runs")
    plt.legend()
    plt.tight_layout()
    plt.show()

def panel_instability_rdsi_scatter(glob: Dict[str, Any]) -> None:
    """
    Instability × RDSI scatter plot for runs.

    Goal:
        Visualise per-run instability_score vs rdsi, highlight quadrants,
        and make it easy to spot outliers.
    """
    env = glob.get("env", {})
    runs_df = env.get("runs_df")

    if runs_df is None:
        print("[instability×rdsi] runs_df missing – skipping panel.")
        return

    if not isinstance(runs_df, pd.DataFrame) or runs_df.empty:
        print("[instability×rdsi] runs_df is not a non-empty DataFrame – skipping panel.")
        return

    required = {"instability_score", "rdsi"}
    missing = required.difference(runs_df.columns)
    if missing:
        print(f"[instability×rdsi] missing columns {missing} – skipping panel.")
        return

    df = runs_df[["instability_score", "rdsi"]].dropna()
    if df.empty:
        print("[instability×rdsi] no valid instability/rdsi rows – nothing to plot.")
        return

    fig, ax = plt.subplots(figsize=(6, 4))

    ax.scatter(df["rdsi"], df["instability_score"], alpha=0.6)

    # Quadrant thresholds (tuning-friendly demo defaults)
    x_thr = 0.8
    y_thr = 0.5

    ax.axvline(x_thr, linestyle="--", linewidth=1)
    ax.axhline(y_thr, linestyle="--", linewidth=1)

    ax.set_xlabel("RDSI (confidence)")
    ax.set_ylabel("Instability score")
    ax.set_title("Instability × RDSI scatter")

    # Simple quadrant labels (axes coordinates)
    ax.text(0.05, 0.9, "low conf / high instab", transform=ax.transAxes, fontsize=8)
    ax.text(0.05, 0.1, "low conf / low instab", transform=ax.transAxes, fontsize=8)
    ax.text(0.55, 0.9, "high conf / high instab", transform=ax.transAxes, fontsize=8)
    ax.text(0.55, 0.1, "high conf / low instab", transform=ax.transAxes, fontsize=8)

    plt.tight_layout()
    plt.show()

# --- panels env helpers (added) ---
from pathlib import Path
import json
import pandas as pd

_ARTIFACT_CANDIDATES = [
    Path("../artifacts"),
    Path("PULSE_safe_pack_v0/artifacts"),
    Path("./artifacts"),
]

def _load_json_first(relative_names):
    for base in _ARTIFACT_CANDIDATES:
        for name in relative_names:
            p = base / name
            if p.exists():
                try:
                    with p.open("r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
    return None

def maybe_load_env(glob):
    """Ensure runs_df / axes_df / trace_dashboard exist. Try to load from artifacts, otherwise create safe defaults."""
    runs_df = glob.get("runs_df")
    if not isinstance(runs_df, pd.DataFrame) or runs_df.empty:
        topo = _load_json_first(["topology_dashboard_v0.json"])
        if isinstance(topo, dict) and "states" in topo:
            runs_df = pd.json_normalize(topo["states"])
        else:
            
            runs_df = pd.DataFrame(columns=["run_id", "decision", "type", "paradox_zone", "instability_score"])
    glob["runs_df"] = runs_df

    axes_df = glob.get("axes_df")
    if not isinstance(axes_df, pd.DataFrame):
        axes_df = pd.DataFrame()
    glob["axes_df"] = axes_df

    td = glob.get("trace_dashboard")
    if not isinstance(td, dict):
        td = {}
    glob["trace_dashboard"] = td
    return glob

def run_all_panels(glob):
    """Call all available panel functions; tolerate different signatures and missing frames."""
    glob = maybe_load_env(glob)
    for name in [
        "panel_worry_index_v0",
        "panel_decision_zone_matrix_v0",
        "panel_top_axes_v0",
        "panel_epf_overview_v0",
        "panel_instability_rdsi_grid_v0",
        "panel_decision_streaks_v0",
    ]:
        fn = globals().get(name)
        if callable(fn):
            try:
                fn(glob)          
            except TypeError:
                fn()               
# --- end helpers ---

ARTIFACT_DIR = Path("../artifacts")


def _ensure_artifacts():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def _maybe_load_env(env: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure runs_df, axes_df, trace_dashboard exist in env, else try to load."""
    out = dict(env)
    # runs_df
    if "runs_df" not in out or out["runs_df"] is None or getattr(out["runs_df"], "empty", True):
        # try decision_history_v0.json (if exists)
        dh = Path("../artifacts/decision_history_v0.json")
        if dh.exists():
            try:
                j = json.loads(dh.read_text(encoding="utf-8"))
                out["runs_df"] = pd.DataFrame(j)
            except Exception:
                pass
    # axes_df
    if "axes_df" not in out or out["axes_df"] is None or getattr(out["axes_df"], "empty", True):
        ph = Path("../artifacts/paradox_history_v0.json")
        if ph.exists():
            try:
                j = json.loads(ph.read_text(encoding="utf-8"))
                axes = j.get("axes", j.get("paradox_history", []))
                out["axes_df"] = pd.DataFrame(axes)
            except Exception:
                pass
    # trace_dashboard
    if "trace_dashboard" not in out or not out["trace_dashboard"]:
        td = Path("../artifacts/trace_dashboard_v0.json")
        if td.exists():
            try:
                out["trace_dashboard"] = json.loads(td.read_text(encoding="utf-8"))
            except Exception:
                out["trace_dashboard"] = {}
    return out


def panel_worry_index(runs_df: pd.DataFrame):
    if runs_df is None or runs_df.empty:
        print("[worry] No runs_df.")
        return
    instab_col = None
    for cand in ("instability_score", "instability"):
        if cand in runs_df.columns:
            instab_col = cand
            break
    if instab_col is None:
        print("[worry] No instability column; skipping.")
        return

    zone_rank_map = {"red": 3, "yellow": 2, "green": 1}
    df = runs_df.copy()
    df["paradox_zone_rank"] = df["paradox_zone"].map(zone_rank_map).fillna(0)
    df["worry_score"] = df["paradox_zone_rank"] * 2 + pd.to_numeric(df[instab_col], errors="coerce").fillna(0)

    top_k = 10
    cols = [c for c in ["run_id", "decision", "type", "paradox_zone", instab_col, "worry_score"] if c in df.columns]
    top = df.sort_values(["worry_score", instab_col], ascending=False).head(top_k).loc[:, cols]
    display(top)
    _ensure_artifacts()
    out_csv = ARTIFACT_DIR / "runs_top_worry_v0.csv"
    top.to_csv(out_csv, index=False)
    print("Saved:", out_csv)

    plt.figure(figsize=(8, 4))
    plt.bar(top["run_id"], top["worry_score"])
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("worry_score")
    plt.title(f"Top {top_k} worrying runs (zone + instability)")
    plt.tight_layout()
    plt.show()


def panel_zone_matrix(runs_df: pd.DataFrame):
    if runs_df is None or runs_df.empty:
        print("[zones] No runs_df.")
        return
    df = runs_df.copy()
    if "paradox_zone" not in df.columns:
        print("[zones] No paradox_zone.")
        return
    zone_counts = df["paradox_zone"].fillna("none").value_counts().rename("count").to_frame()
    display(zone_counts)

    combo = (
        df.assign(paradox_zone=df["paradox_zone"].fillna("none"))
          .groupby(["decision", "paradox_zone"])
          .size()
          .reset_index(name="count")
    )
    pivot = combo.pivot(index="decision", columns="paradox_zone", values="count").fillna(0).astype(int)
    display(pivot)
    _ensure_artifacts()
    out_csv = ARTIFACT_DIR / "decision_zone_matrix_v0.csv"
    pivot.to_csv(out_csv)
    print("Saved:", out_csv)

    plt.figure(figsize=(6, 4))
    plt.imshow(pivot.values, aspect="auto")
    plt.colorbar(label="count")
    plt.yticks(ticks=np.arange(len(pivot.index)), labels=pivot.index)
    plt.xticks(ticks=np.arange(len(pivot.columns)), labels=pivot.columns, rotation=45, ha="right")
    plt.title("Decision × Paradox zone — counts")
    plt.tight_layout()
    plt.show()


def panel_top_axes(axes_df: pd.DataFrame):
    if axes_df is None or axes_df.empty:
        print("[top-axes] No axes_df.")
        return
    cols = [c for c in ["axis_id", "severity", "runs_seen", "times_dominant", "max_tension"] if c in axes_df.columns]
    if not cols:
        print("[top-axes] Expected columns missing.")
        return
    df = axes_df[cols].copy()
    sev_map = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    # Accept EN/HU labels; be defensive if column is missing
sev_map = {
    "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4,
    "ALACSONY": 1, "KÖZEPES": 2, "MAGAS": 3, "KRITIKUS": 4,
}

if "severity" in df.columns:
    sev_series = df["severity"].astype(str).str.upper()
else:
    sev_series = pd.Series([""] * len(df), index=df.index)

df["severity_rank"] = sev_series.map(sev_map).fillna(0).astype(int)


    sort_cols = ["severity_rank"]
    if "times_dominant" in df.columns:
        sort_cols.append("times_dominant")
    if "runs_seen" in df.columns:
        sort_cols.append("runs_seen")

    top10 = df.sort_values(sort_cols, ascending=False).head(10)
    display(top10)

    _ensure_artifacts()
    out_csv = ARTIFACT_DIR / "paradox_axes_top_v0.csv"
    top10.to_csv(out_csv, index=False)
    print("Saved:", out_csv)

    if "runs_seen" in top10.columns and "times_dominant" in top10.columns:
        plt.figure()
        plt.scatter(top10["runs_seen"], top10["times_dominant"])
        for _, r in top10.iterrows():
            plt.text(r["runs_seen"], r["times_dominant"], str(r.get("axis_id", "")))
        plt.xlabel("runs_seen")
        plt.ylabel("times_dominant")
        plt.title("Top paradox axes (severity + dominance)")
        plt.tight_layout()
        plt.show()


def panel_epf_overview(trace_dashboard: Dict[str, Any]):
    epf_ov = (trace_dashboard or {}).get("epf_overview", {})
    if not epf_ov:
        print("[epf] No EPF overview present.")
        return
    from pprint import pprint
    print("EPF overview:")
    pprint(epf_ov)


def panel_axes_pareto(axes_df: pd.DataFrame, runs_df: Optional[pd.DataFrame] = None):
    if axes_df is None or axes_df.empty:
        print("[pareto] No axes_df.")
        return
    df = axes_df.copy()
    count_col = None
    for c in ["runs_seen", "times_dominant", "count", "occurrences"]:
        if c in df.columns:
            count_col = c
            break
    if count_col is None:
        print("[pareto] No count-like column.")
        return

    df["_cnt"] = pd.to_numeric(df[count_col], errors="coerce").fillna(0)
    df = df.sort_values("_cnt", ascending=False).reset_index(drop=True)
    if "axis_id" not in df.columns:
        df["axis_id"] = np.arange(1, len(df) + 1)

    df["k"] = df.index + 1
    total = df["_cnt"].sum()
    df["share"] = (df["_cnt"] / total) if total > 0 else 0
    df["cum_share"] = df["share"].cumsum() if total > 0 else 0

    out = df[["k", "axis_id", "_cnt", "cum_share"]].rename(columns={"_cnt": "count"})
    display(out.head(20))
    _ensure_artifacts()
    out_csv = ARTIFACT_DIR / "axes_pareto_coverage_v0.csv"
    out.to_csv(out_csv, index=False)
    print("Saved:", out_csv)

    plt.figure(figsize=(7, 4))
    plt.plot(out["k"], out["cum_share"])
    plt.xlabel("top-k axes")
    plt.ylabel("cumulative share")
    plt.title(f"Axes Pareto coverage by {count_col}")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def panel_instab_rdsi_quadrants(runs_df: pd.DataFrame):
    if runs_df is None or runs_df.empty:
        print("[quadrants] No runs_df.")
        return
    instab_col = None
    for cand in ("instability_score", "instability"):
        if cand in runs_df.columns:
            instab_col = cand
            break
    if instab_col is None or "rdsi" not in runs_df.columns:
        print("[quadrants] Need 'rdsi' and an instability column.")
        return

    x = pd.to_numeric(runs_df[instab_col], errors="coerce")
    y = pd.to_numeric(runs_df["rdsi"], errors="coerce")
    t_x = x.median()
    t_y = y.median()

    def label(ix, iy):
        hi_x = ix >= t_x
        hi_y = iy >= t_y
        if hi_x and hi_y: return "Q1 (high instab, high RDSI)"
        if hi_x and not hi_y: return "Q2 (high instab, low RDSI)"
        if (not hi_x) and hi_y: return "Q3 (low instab,  high RDSI)"
        return "Q4 (low instab,  low RDSI)"

    q = [label(ix, iy) for ix, iy in zip(x.fillna(t_x), y.fillna(t_y))]
    counts = pd.Series(q).value_counts().rename("count").to_frame()
    display(counts)
    _ensure_artifacts()
    out_csv = ARTIFACT_DIR / "instability_rdsi_quadrants_v0.csv"
    counts.to_csv(out_csv)
    print("Saved:", out_csv)

    plt.figure(figsize=(6, 4))
    plt.scatter(x, y, s=14)
    plt.axvline(t_x); plt.axhline(t_y)
    plt.xlabel(instab_col); plt.ylabel("rdsi")
    plt.title("Instability × RDSI (median thresholds)")
    plt.tight_layout()
    plt.show()


def panel_decision_streaks(runs_df: pd.DataFrame):
    if runs_df is None or runs_df.empty:
        print("[streaks] No runs_df.")
        return
    if "decision" not in runs_df.columns or "run_id" not in runs_df.columns:
        print("[streaks] Need 'run_id' and 'decision'.")
        return

    def _infer_order(df: pd.DataFrame) -> pd.Series:
        if "run_index" in df.columns:
            return pd.to_numeric(df["run_index"], errors="coerce").fillna(-1).astype(int)
        if "generated_at" in df.columns:
            ts = pd.to_datetime(df["generated_at"], errors="coerce")
            return ts.rank(method="first").astype(int)
        def parse_num(x):
            m = re.search(r'(\d+)$', str(x))
            return int(m.group(1)) if m else None
        vals = df["run_id"].map(parse_num)
        return pd.to_numeric(vals, errors="coerce").fillna(-1).astype(int)

    df = runs_df.copy()
    df["_order"] = _infer_order(df)
    df = df.sort_values("_order", kind="stable")

    rows = []
    prev_dec, start_run, start_ord, length = None, None, None, 0
    last_run, last_ord = None, None
    for _, r in df.iterrows():
        dec, rid, ordv = r["decision"], r["run_id"], r["_order"]
        if dec != prev_dec:
            if prev_dec is not None:
                rows.append({
                    "decision": prev_dec,
                    "streak_len": length,
                    "start_order": start_ord,
                    "end_order": last_ord,
                    "start_run": start_run,
                    "end_run": last_run,
                })
            prev_dec = dec
            start_run, start_ord = rid, ordv
            length = 1
        else:
            length += 1
        last_run, last_ord = rid, ordv
    if prev_dec is not None:
        rows.append({
            "decision": prev_dec,
            "streak_len": length,
            "start_order": start_ord,
            "end_order": last_ord,
            "start_run": start_run,
            "end_run": last_run,
        })

    st = pd.DataFrame(rows).sort_values(["streak_len", "start_order"], ascending=[False, True])
    display(st.head(15))
    _ensure_artifacts()
    out_csv = ARTIFACT_DIR / "decision_streaks_v0.csv"
    st.to_csv(out_csv, index=False)
    print("Saved:", out_csv)

    N = min(10, len(st))
    if N > 0:
        plt.figure(figsize=(8, 4))
        labels = [f"{d} ({s})" for d, s in zip(st["decision"].head(N), st["streak_len"].head(N))]
        plt.bar(labels, st["streak_len"].head(N))
        plt.xticks(rotation=45, ha="right")
        plt.ylabel("streak length")
        plt.title("Top decision streaks")
        plt.tight_layout()
        plt.show()


def run_all_panels(env: Dict[str, Any]):
    """Entry point the notebook can call."""
    e = _maybe_load_env(env)
    runs_df = e.get("runs_df")
    axes_df = e.get("axes_df")
    trace_dashboard = e.get("trace_dashboard", {})

    print("=== PULSE Trace Panels v0 ===")
    panel_worry_index(runs_df)
    panel_zone_matrix(runs_df)
    panel_top_axes(axes_df)
    panel_epf_overview(trace_dashboard)
    panel_axes_pareto(axes_df, runs_df)
    panel_instab_rdsi_quadrants(runs_df)
    panel_decision_streaks(runs_df)
    print("=== Done. CSVs in ../artifacts ===")
    panel_paradox_axes_pareto({"env": e})


