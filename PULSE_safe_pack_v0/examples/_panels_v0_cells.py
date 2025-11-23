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

def panel_paradox_histogram(
    glob: Dict[str, Any],
    *,
    df_key: str = "runs_df",
    zone_col: str = "paradox_zone",
    value_col: str = "instability",
    weight_col: Optional[str] = "run_weight",
    bins: int = 20,
):
    """
    Weighted paradox histogram by zone.

    Expects `glob[df_key]` to be a pandas DataFrame with at least:
      - zone_col   (e.g. 'paradox_zone')
      - value_col  (e.g. 'instability' / 'tension')
    Optionally:
      - weight_col (e.g. 'run_weight'); if missing or None, weight = 1.0

    Returns:
      matplotlib Figure object, or None if the panel is skipped.
    """
    df = glob.get(df_key)

    if df is None:
        print(
            "[panel_paradox_histogram] "
            f"No dataframe found under key '{df_key}', skipping panel."
        )
        return None

    if df.empty:
        print("[panel_paradox_histogram] Dataframe is empty, skipping panel.")
        return None

    missing = [c for c in (zone_col, value_col) if c not in df.columns]
    if missing:
        print(
            "[panel_paradox_histogram] "
            f"Missing required columns {missing}, skipping panel."
        )
        return None

    # Drop rows without a numeric value for the histogram
    df = df.dropna(subset=[value_col]).copy()
    if df.empty:
        print(
            "[panel_paradox_histogram] "
            f"All rows have NaN in '{value_col}', skipping panel."
        )
        return None

    # Optional weight handling
    if weight_col and weight_col in df.columns:
        df[weight_col] = df[weight_col].fillna(1.0)
    else:
        weight_col = None  # treat as unweighted

    # Shared bin edges across all zones
    vmin = df[value_col].min()
    vmax = df[value_col].max()

    # Guard against degenerate cases
    if not np.isfinite(vmin) or not np.isfinite(vmax):
        print(
            "[panel_paradox_histogram] "
            f"Non‑finite value range ({vmin}, {vmax}), skipping panel."
        )
        return None

    if math.isclose(float(vmin), float(vmax)):
        # Everything is (almost) the same value → widen a bit
        delta = 0.5 if vmin == 0 else abs(vmin) * 0.1
        vmin -= delta
        vmax += delta

    bin_edges = np.linspace(vmin, vmax, bins + 1)

    fig, ax = plt.subplots(figsize=(8, 4))

    for zone, group in df.groupby(zone_col):
        weights = group[weight_col] if weight_col else None

        ax.hist(
            group[value_col],
            bins=bin_edges,
            weights=weights,
            alpha=0.5,
            label=str(zone),
            density=False,  # ha inkább arány kell, lehet True
        )

    title = "Paradox histogram by zone (weighted)"
    ax.set_title(title)
    ax.set_xlabel(value_col)
    ax.set_ylabel("Weighted count")
    ax.legend(title=zone_col, loc="best")

    ax.grid(True, axis="y", linestyle=":", linewidth=0.5)
    fig.tight_layout()

    return fig

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

def panel_instability_timeline(glob: Dict[str, Any]) -> None:
    """
    Instability score timeline per run, with simple risk bands.

    Goal:
      Show how instability_score evolves across runs, with markers at the
      LOW / MEDIUM / HIGH / CRITICAL thresholds (0.25 / 0.50 / 0.75).
    """
    env = glob.get("env", {})
    runs_df = env.get("runs_df")

    # Defensive guards – skip cleanly if something is missing.
    if not isinstance(runs_df, pd.DataFrame) or runs_df.empty:
        print("[timeline] runs_df missing or empty – skipping instability timeline panel.")
        return

    if "instability_score" not in runs_df.columns:
        print("[timeline] runs_df has no 'instability_score' column – skipping.")
        return

    # Convert to numeric, ignore bad values.
    y = pd.to_numeric(runs_df["instability_score"], errors="coerce")
    if y.isna().all():
        print("[timeline] instability_score is all NaN – nothing to plot.")
        return

    x = range(len(y))

    plt.figure(figsize=(8, 4))
    plt.plot(x, y, marker="o", linestyle="-", label="instability_score")

    # Risk bands: 0.25 / 0.50 / 0.75
    for thresh, label in [(0.25, "LOW / MED"), (0.50, "MED / HIGH"), (0.75, "HIGH / CRIT")]:
        plt.axhline(thresh, linestyle="--", linewidth=1)

    plt.ylim(0.0, 1.0)
    plt.xlabel("Run index")
    plt.ylabel("Instability score")
    plt.title("Instability timeline (per run)")
    plt.legend()
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

def maybe_load_env(glob: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build an 'env' mapping for panels with runs_df and axes_df.

    Precedence:
    1. If glob["env"] already has DataFrames, use those.
    2. Else, look for top-level 'runs_df' / 'axes_df' in glob.
    3. Else, try to load decision/paradox history JSON artifacts.
    4. As a last resort, return empty DataFrames so panels can skip.
    """
    env: Dict[str, Any] = {}

    # 1) Ha van már env a glob-ban, induljunk abból
    raw_env = glob.get("env")
    if isinstance(raw_env, dict):
        env.update(raw_env)

    # 2) Próbáljuk meg átvenni a top-level runs_df / axes_df-et
    runs_df = env.get("runs_df") or glob.get("runs_df")
    axes_df = env.get("axes_df") or glob.get("axes_df")

    if isinstance(runs_df, pd.DataFrame) and not runs_df.empty:
        env["runs_df"] = runs_df
    if isinstance(axes_df, pd.DataFrame) and not axes_df.empty:
        env["axes_df"] = axes_df

    # 3) Ha még mindig hiányzik valami, próbáljuk JSON artifactokból betölteni
    needs_runs = (
        "runs_df" not in env
        or not isinstance(env["runs_df"], pd.DataFrame)
        or env["runs_df"].empty
    )
    needs_axes = (
        "axes_df" not in env
        or not isinstance(env["axes_df"], pd.DataFrame)
        or env["axes_df"].empty
    )

    if needs_runs or needs_axes:
        raw = _load_json_first(
            [
                "trace_dashboard_v0.json",
                "decision_history_v0.json",
                "paradox_history_v0.json",
            ]
        )

        if isinstance(raw, dict):
            runs_seq = None
            axes_seq = None

            # Tipikus kulcsok per-run adatokhoz
            for key in ["runs", "states", "runs_view"]:
                if isinstance(raw.get(key), list):
                    runs_seq = raw[key]
                    break

            # Tipikus kulcsok per-axis adatokhoz
            for key in ["axes", "axes_view", "axes_summary"]:
                if isinstance(raw.get(key), list):
                    axes_seq = raw[key]
                    break

            if needs_runs and runs_seq is not None:
                env["runs_df"] = pd.json_normalize(runs_seq)

            if needs_axes and axes_seq is not None:
                env["axes_df"] = pd.json_normalize(axes_seq)

    # 4) Végső fallback: legyen mindig DataFrame, még ha üres is
    if "runs_df" not in env or not isinstance(env["runs_df"], pd.DataFrame):
        env["runs_df"] = pd.DataFrame()
    if "axes_df" not in env or not isinstance(env["axes_df"], pd.DataFrame):
        env["axes_df"] = pd.DataFrame()

    return env


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

def panel_paradox_zone_histogram(glob: Dict[str, Any]) -> None:
    """
    Simple bar chart of paradox axes by zone.

    Expects:
      glob = {"env": env}
      env["axes_df"] : DataFrame with at least a 'zone' column
                       (e.g. 'green' / 'yellow' / 'red').
    """
    env = glob.get("env", {}) or {}
    axes_df = env.get("axes_df")

    if not isinstance(axes_df, pd.DataFrame) or axes_df.empty:
        print("[zone_hist] axes_df missing or empty – skipping panel.")
        return

    if "zone" not in axes_df.columns:
        print("[zone_hist] axes_df has no 'zone' column – skipping panel.")
        return

    # stabil sorrend a zónákra
    zone_order = ["green", "yellow", "red"]
    counts = axes_df["zone"].value_counts()

    zones = [z for z in zone_order if z in counts.index]
    values = [int(counts.get(z, 0)) for z in zones]

    if not zones:
        print("[zone_hist] no recognised zones to plot.")
        return

    plt.figure(figsize=(6, 4))
    plt.bar(range(len(zones)), values, tick_label=[z.upper() for z in zones])
    plt.xlabel("Zone")
    plt.ylabel("Number of axes")
    plt.title("Paradox axes by zone")
    plt.tight_layout()
    plt.show()

def panel_paradox_tension_histogram(glob: Dict[str, Any]) -> None:
    """
    Histogram of paradox tension, grouped by zone.
    """

    env = glob.get("env", {})
    axes_df = env.get("axes_df")

    if not isinstance(axes_df, pd.DataFrame) or axes_df.empty:
        print("[hist] axes_df missing or empty – skipping paradox histogram.")
        return

    # Pick a tension-like column
    tension_col = None
    for col in ["tension_score", "avg_tension", "max_tension"]:
        if col in axes_df.columns:
            tension_col = col
            break

    if tension_col is None:
        print(
            "[hist] no tension column found in axes_df – "
            "expected one of 'tension_score', 'avg_tension', 'max_tension'."
        )
        return

    if "zone" not in axes_df.columns:
        print("[hist] axes_df has no 'zone' column – skipping paradox histogram.")
        return

    df = axes_df[[tension_col, "zone"]].dropna()
    if df.empty:
        print("[hist] no rows with both tension and zone – nothing to plot.")
        return

    # Defenzíven 0–1 közé klippeljük a feszültséget
    df[tension_col] = df[tension_col].clip(lower=0.0, upper=1.0)

    bins = np.linspace(0.0, 1.0, 11)
    zones = ["green", "yellow", "red"]

    plt.figure(figsize=(8, 4))
    for zone in zones:
        subset = df.loc[df["zone"] == zone, tension_col]
        if subset.empty:
            continue
        plt.hist(
            subset,
            bins=bins,
            alpha=0.4,
            density=True,
            label=zone.upper(),
        )

    plt.xlabel("Paradox tension")
    plt.ylabel("Density")
    plt.title("Paradox tension distribution by zone")
    plt.legend()
    plt.tight_layout()
    plt.show()

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

def panel_paradox_zone_weighted_histogram(glob: Dict[str, Any]) -> None:
    """
    Weighted histogram of paradox zones using severity as weight.

    - Uses runs_df from env.
    - Ensures a 'severity' column is present (via ensure_severity_column).
    - Aggregates a numeric severity weight per paradox zone.
    - Renders a simple bar chart.
    """
    env = glob.get("env", {}) if isinstance(glob, dict) else {}
    runs_df = env.get("runs_df")

    if not isinstance(runs_df, pd.DataFrame) or runs_df.empty:
        print("[zone_hist] runs_df missing or empty – skipping weighted zone histogram panel.")
        return

    # Make sure we have a severity column.
    runs_df = ensure_severity_column(runs_df.copy(), source_col="max_tension")

    # Try to find a zone column.
    if "paradox_zone" in runs_df.columns:
        zone_col = "paradox_zone"
    elif "zone" in runs_df.columns:
        zone_col = "zone"
    else:
        print("[zone_hist] No 'paradox_zone' or 'zone' column – skipping weighted zone histogram panel.")
        return

    # Map severities to numeric weights.
    severity_weights = {
        "LOW": 1.0,
        "MEDIUM": 2.0,
        "HIGH": 3.0,
        "CRITICAL": 4.0,
    }

    runs_df["severity_weight"] = runs_df["severity"].map(severity_weights).fillna(0.0)

    grouped = (
        runs_df
        .groupby(zone_col)["severity_weight"]
        .sum()
        .reset_index()
    )

    if grouped.empty:
        print("[zone_hist] No data after grouping – nothing to plot.")
        return

    # Order zones in a sensible way if possible.
    preferred_order = [
        "green", "yellow", "red", "unknown",
        "GREEN", "YELLOW", "RED", "UNKNOWN",
    ]

    def _order_index(z: Any) -> int:
        try:
            return preferred_order.index(str(z))
        except ValueError:
            return len(preferred_order)

    grouped["__order"] = grouped[zone_col].apply(_order_index)
    grouped = grouped.sort_values("__order")

    zones = grouped[zone_col].astype(str).tolist()
    weights = grouped["severity_weight"].tolist()

    plt.figure(figsize=(6, 4))
    plt.bar(range(len(zones)), weights)
    plt.xticks(range(len(zones)), [z.upper() for z in zones])
    plt.ylabel("Weighted severity")
    plt.xlabel("Paradox zone")
    plt.title("Paradox zone weighted histogram")
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


def run_all_panels(glob: Dict[str, Any]) -> None:
    """Run all trace dashboard panels in one go.

    Builds an env dict (runs_df, axes_df, ...) and wires it into
    each panel in turn. Missing panels or local errors do not stop
    the rest of the dashboard.
    """
    env = maybe_load_env(glob)
    if not isinstance(env, dict):
        print("[panels] env could not be loaded — aborting.")
        return

    # Share env back through the glob mapping as well (for callers, if needed)
    glob["env"] = env

    runs_df = env.get("runs_df")

    # Panels that expect the full glob (with "env") as input
    panel_env_names = [
        "panel_worry_index_v0",
        "panel_decision_zone_matrix_v0",
        "panel_paradox_zone_histogram",
        "panel_paradox_tension_histogram",
        "panel_instability_rdsi_scatter",
        "panel_paradox_axes_pareto",
        "panel_paradox_histogram",      
        "panel_instability_timeline",
        "panel_epf_overview",
    ]


    

    for name in panel_env_names:
        fn = globals().get(name)
        if not callable(fn):
            print(f"[panels] {name} not found — skipping.")
            continue

        try:
            fn(glob)
        except Exception as exc:
            # Best effort: log and keep going so one panel
            # does not break the whole dashboard run.
            print(f"[panels] {name} raised {exc!r} — skipping.")

    # Decision streaks panel takes runs_df directly
    if isinstance(runs_df, pd.DataFrame) and not runs_df.empty:
        try:
            panel_decision_streaks(runs_df)
        except Exception as exc:
            print(f"[panels] panel_decision_streaks failed: {exc!r}")
    else:
        print("[panels] runs_df missing or empty — skipping decision streaks panel.")

    print("[panels] Done. CSVs in ../artifacts")





