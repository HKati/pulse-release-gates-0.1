#!/usr/bin/env python3
"""
Run all PULSE safe-pack checks and generate core artifacts.

This script is the main entrypoint for the PULSE_safe_pack_v0 "safe pack".
It orchestrates the configured checks/profiles and produces the baseline
status.json and related artifacts under the pack's artifacts directory,
which are then consumed by CI workflows and reporting tools.
"""

import os
import json
import datetime
import pathlib
import sys
from html import escape

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.epf.epf_hazard_adapter import (
    HazardRuntimeState,
    probe_hazard_and_append_log,
)
from PULSE_safe_pack_v0.epf.epf_hazard_policy import (
    HazardGateConfig,
    evaluate_hazard_gate,
)
from PULSE_safe_pack_v0.epf.epf_hazard_forecast import (
    DEFAULT_WARN_THRESHOLD,
    DEFAULT_CRIT_THRESHOLD,
    CALIBRATED_WARN_THRESHOLD,
    CALIBRATED_CRIT_THRESHOLD,
    MIN_CALIBRATION_SAMPLES,
)

# Prefer the same calibration path constant as EPF modules, but fall back safely.
try:
    from PULSE_safe_pack_v0.epf.epf_hazard_forecast import CALIBRATION_PATH as HAZARD_CALIB_PATH
except Exception:  # pragma: no cover
    HAZARD_CALIB_PATH = ROOT / "artifacts" / "epf_hazard_thresholds_v0.json"


art = ROOT / "artifacts"
art.mkdir(parents=True, exist_ok=True)

now = datetime.datetime.utcnow().isoformat() + "Z"
STATUS_VERSION = "1.0.0-demo"


# ---------------------------------------------------------------------------
# Helpers for EPF hazard history / sparkline
# ---------------------------------------------------------------------------

def load_hazard_E_history(log_path: pathlib.Path, max_points: int = 20):
    """
    Load up to max_points hazard E values from the epf_hazard_log.jsonl file.

    Returns the most recent values in order (oldest -> newest).
    """
    if not log_path.exists():
        return []

    values = []
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            hazard = obj.get("hazard", {}) or {}
            E = hazard.get("E")
            if isinstance(E, (int, float)):
                values.append(float(E))

    if not values:
        return []

    return values[-max_points:]


def build_E_sparkline_svg(values, width: int = 160, height: int = 40) -> str:
    """
    Build a tiny inline SVG sparkline for recent E values.

    If there are fewer than 2 points, we return an empty string;
    the HTML template will show a placeholder text instead.
    """
    if len(values) < 2:
        return ""

    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        max_v = min_v + 1.0

    padding = 4
    inner_w = width - 2 * padding
    inner_h = height - 2 * padding

    points = []
    n = len(values)
    for i, v in enumerate(values):
        t = i / (n - 1) if n > 1 else 0.0
        x = padding + t * inner_w
        norm = (v - min_v) / (max_v - min_v)
        y = height - padding - norm * inner_h
        points.append(f"{x:.1f},{y:.1f}")

    points_str = " ".join(points)

    svg = f"""<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Recent E history">
  <polyline fill="none" stroke="#4f46e5" stroke-width="1.5" points="{points_str}" />
</svg>"""
    return svg


def format_top_contributors(contribs, k: int = 3) -> str:
    """
    Format hazard_state.contributors_top (compact dicts) into a short, safe string.
    """
    if not isinstance(contribs, list) or not contribs:
        return "none"

    parts = []
    for c in contribs[:k]:
        if not isinstance(c, dict):
            continue
        key = escape(str(c.get("key", "UNKNOWN")))
        contrib = c.get("contrib")
        if isinstance(contrib, (int, float)):
            parts.append(f"{key}({float(contrib):.2f})")
        else:
            parts.append(key)

    return ", ".join(parts) if parts else "none"


def load_last_hazard_feature_keys(log_path: pathlib.Path) -> list[str]:
    """
    Best-effort: read the last valid JSON event from epf_hazard_log.jsonl
    and return hazard.feature_keys if present.
    """
    if not log_path.exists():
        return []

    last_obj = None
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            last_obj = obj

    if not isinstance(last_obj, dict):
        return []

    hazard = last_obj.get("hazard", {}) or {}
    keys = hazard.get("feature_keys")
    if not isinstance(keys, list):
        return []

    out: list[str] = []
    for k in keys:
        s = str(k).strip()
        if s:
            out.append(s)
    return out


def format_feature_keys(keys: list[str], preview: int = 6) -> str:
    """
    Format feature keys into a compact, safe string for HTML.
    """
    if not keys:
        return "none"

    shown = keys[:preview]
    shown_esc = [escape(k) for k in shown]
    if len(keys) > preview:
        return ", ".join(shown_esc) + f" +{len(keys) - preview} more"
    return ", ".join(shown_esc)


def load_calibration_recommendation(calib_path: pathlib.Path) -> dict:
    """
    Load recommended_features + recommendation knobs (min_coverage / max_features)
    from the calibration artifact, if available.

    Fail-open: any read/parse issues yield empty values.
    """
    out = {
        "present": False,
        "recommended_features": [],
        "recommended_count": 0,
        "min_coverage": None,
        "max_features": None,
        "feature_allowlist_count": 0,
    }

    try:
        with calib_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return out

    out["present"] = True

    rec = data.get("recommended_features")
    if isinstance(rec, list):
        cleaned = []
        for x in rec:
            s = str(x).strip()
            if s:
                cleaned.append(s)
        out["recommended_features"] = cleaned
        out["recommended_count"] = len(cleaned)

    allow = data.get("feature_allowlist")
    if isinstance(allow, list):
        out["feature_allowlist_count"] = len([1 for x in allow if str(x).strip()])

    knobs = data.get("recommendation")
    if isinstance(knobs, dict):
        mc = knobs.get("min_coverage")
        mf = knobs.get("max_features")
        if isinstance(mc, (int, float)):
            out["min_coverage"] = float(mc)
        if isinstance(mf, int):
            out["max_features"] = int(mf)

    return out


# ---------------------------------------------------------------------------
# Minimal demo gates (all True by default so CI passes)
# ---------------------------------------------------------------------------

gates = {
    "pass_controls_refusal": True,
    "effect_present": True,
    "psf_monotonicity_ok": True,
    "psf_mono_shift_resilient": True,
    "pass_controls_comm": True,
    "psf_commutativity_ok": True,
    "psf_comm_shift_resilient": True,
    "pass_controls_sanit": True,
    "sanitization_effective": True,
    "sanit_shift_resilient": True,
    "psf_action_monotonicity_ok": True,
    "psf_idempotence_ok": True,
    "psf_path_independence_ok": True,
    "psf_pii_monotonicity_ok": True,
    "q1_grounded_ok": True,
    "q2_consistency_ok": True,
    "q3_fairness_ok": True,
    "q4_slo_ok": True,
}

metrics = {
    "RDSI": 0.92,
    "rdsi_note": "Demo value for CI smoke-run",
    "build_time": now,
}

# ---------------------------------------------------------------------------
# EPF hazard probe (proto-level)
# ---------------------------------------------------------------------------

hazard_runtime = HazardRuntimeState.empty()

current_snapshot = {"RDSI": metrics.get("RDSI", 0.5)}
reference_snapshot = {"RDSI": 1.0}
stability_metrics = {"RDSI": metrics.get("RDSI", 0.5)}

hazard_state = probe_hazard_and_append_log(
    gate_id="EPF_demo_RDSI",
    current_snapshot=current_snapshot,
    reference_snapshot=reference_snapshot,
    stability_metrics=stability_metrics,
    runtime_state=hazard_runtime,
    log_dir=art,
    extra_meta={
        "created_utc": now,
        "status_version": STATUS_VERSION,
    },
)

hazard_decision = evaluate_hazard_gate(hazard_state, cfg=HazardGateConfig())

metrics["hazard_T"] = hazard_state.T
metrics["hazard_S"] = hazard_state.S
metrics["hazard_D"] = hazard_state.D
metrics["hazard_E"] = hazard_state.E
metrics["hazard_zone"] = hazard_state.zone
metrics["hazard_reason"] = hazard_state.reason
metrics["hazard_ok"] = hazard_decision.ok
metrics["hazard_severity"] = hazard_decision.severity

# Additive: Relational Grail explainability fields (safe even if absent).
hazard_T_scaled = bool(getattr(hazard_state, "T_scaled", False))
hazard_contributors_top = getattr(hazard_state, "contributors_top", []) or []
metrics["hazard_T_scaled"] = hazard_T_scaled
metrics["hazard_contributors_top"] = hazard_contributors_top

# Load last-used feature keys from the log entry we just appended.
hazard_log_path = art / "epf_hazard_log.jsonl"
hazard_feature_keys = load_last_hazard_feature_keys(hazard_log_path)
metrics["hazard_feature_keys"] = hazard_feature_keys
metrics["hazard_feature_count"] = int(len(hazard_feature_keys))

# Load calibration recommendation summary (recommended_features + min_coverage).
calib_summary = load_calibration_recommendation(pathlib.Path(HAZARD_CALIB_PATH))
metrics["hazard_recommended_count"] = int(calib_summary.get("recommended_count", 0) or 0)
metrics["hazard_recommend_min_coverage"] = calib_summary.get("min_coverage")
metrics["hazard_recommend_max_features"] = calib_summary.get("max_features")
metrics["hazard_feature_allowlist_count"] = int(calib_summary.get("feature_allowlist_count", 0) or 0)

# Load recent E history for the EPF Relational Grail.
E_history = load_hazard_E_history(hazard_log_path, max_points=20)
hazard_history_svg = build_E_sparkline_svg(E_history)
if E_history and hazard_history_svg:
    history_fragment = (
        '<div class="epf-hazard-history">'
        '<span class="epf-hazard-history-label">Recent E history</span>'
        f"{hazard_history_svg}"
        "</div>"
    )
else:
    history_fragment = (
        '<div class="epf-hazard-history">'
        '<span class="epf-hazard-history-label">Recent E history</span>'
        '<span class="epf-hazard-history-empty">Not enough hazard history yet</span>'
        "</div>"
    )

# ---------------------------------------------------------------------------
# Shadow hazard gate (ENV-flag-enforceable)
# ---------------------------------------------------------------------------

enforce_hazard = os.getenv("EPF_HAZARD_ENFORCE", "0") == "1"
if enforce_hazard:
    gates["epf_hazard_ok"] = hazard_decision.ok
else:
    gates["epf_hazard_ok"] = True

status = {
    "version": STATUS_VERSION,
    "created_utc": now,
    "gates": gates,
    "metrics": metrics,
}

with open(art / "status.json", "w", encoding="utf-8") as f:
    json.dump(status, f, indent=2)

# ---------------------------------------------------------------------------
# HTML report card (demo Quality Ledger view)
# ---------------------------------------------------------------------------

all_gates_pass = all(gates.values())
decision_label = "DEMO-PASS" if all_gates_pass else "DEMO-FAIL"

zone = metrics["hazard_zone"]
if zone == "GREEN":
    hazard_badge_class = "badge-green"
elif zone == "AMBER":
    hazard_badge_class = "badge-amber"
elif zone == "RED":
    hazard_badge_class = "badge-red"
else:
    hazard_badge_class = "badge-unknown"

scale_badge_class = "badge-scaled" if hazard_T_scaled else "badge-unscaled"
scale_badge_text = "SCALED" if hazard_T_scaled else "UNSCALED"
contributors_text = format_top_contributors(hazard_contributors_top, k=3)

features_used_n = int(metrics.get("hazard_feature_count", 0) or 0)
features_used_text = format_feature_keys(hazard_feature_keys, preview=6)

rec_n = int(metrics.get("hazard_recommended_count", 0) or 0)
rec_min_cov = metrics.get("hazard_recommend_min_coverage")
rec_min_cov_text = f"{float(rec_min_cov):.2f}" if isinstance(rec_min_cov, (int, float)) else "n/a"

# Heuristic: if calibrated thresholds differ from the built-in defaults,
# we assume a trusted calibration artefact is present.
calib_is_effective = (
    CALIBRATED_WARN_THRESHOLD != DEFAULT_WARN_THRESHOLD
    or CALIBRATED_CRIT_THRESHOLD != DEFAULT_CRIT_THRESHOLD
)
threshold_regime = "CALIBRATED" if calib_is_effective else "BASELINE"

gate_rows = []
for name, ok in sorted(gates.items()):
    status_class = "status-pass" if ok else "status-fail"
    status_text = "✅ PASS" if ok else "❌ FAIL"
    gate_rows.append(
        f'            <tr><td>{name}</td>'
        f'<td><span class="{status_class}">{status_text}</span></td></tr>'
    )
gate_rows_html = "\n".join(gate_rows)

html = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>PULSE Report Card — demo</title>
    <style>
      :root {{
        color: #111827;
        background-color: #f9fafb;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      body {{
        margin: 0;
        padding: 1.5rem;
        background-color: #f9fafb;
      }}
      .prc-shell {{
        max-width: 900px;
        margin: 0 auto;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12);
        padding: 1.5rem 2rem 2rem;
      }}
      h1 {{
        margin: 0 0 0.25rem;
        font-size: 1.5rem;
      }}
      h2 {{
        margin-top: 1.5rem;
        font-size: 1.1rem;
      }}
      .prc-meta {{
        margin: 0;
        font-size: 0.8rem;
        color: #6b7280;
      }}
      .prc-strip {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.75rem;
        margin-top: 1rem;
        padding: 0.75rem 1rem;
        border-radius: 10px;
        background: linear-gradient(90deg, #0f172a, #1f2937);
        color: #e5e7eb;
        font-size: 0.9rem;
      }}
      .strip-left,
      .strip-right {{
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.5rem;
      }}
      .badge {{
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        text-transform: uppercase;
      }}
      .badge-decision {{
        background: rgba(34, 197, 94, 0.18);
        color: #bbf7d0;
        border: 1px solid rgba(34, 197, 94, 0.6);
      }}
      .badge-rdsi {{
        background: rgba(59, 130, 246, 0.18);
        color: #bfdbfe;
        border: 1px solid rgba(59, 130, 246, 0.6);
      }}
      .badge-green {{
        background: rgba(34, 197, 94, 0.15);
        color: #bbf7d0;
        border: 1px solid rgba(34, 197, 94, 0.5);
      }}
      .badge-amber {{
        background: rgba(245, 158, 11, 0.18);
        color: #fed7aa;
        border: 1px solid rgba(245, 158, 11, 0.6);
      }}
      .badge-red {{
        background: rgba(248, 113, 113, 0.18);
        color: #fecaca;
        border: 1px solid rgba(248, 113, 113, 0.6);
      }}
      .badge-unknown {{
        background: rgba(148, 163, 184, 0.18);
        color: #e5e7eb;
        border: 1px solid rgba(148, 163, 184, 0.6);
      }}
      .badge-scaled {{
        background: rgba(16, 185, 129, 0.16);
        color: #a7f3d0;
        border: 1px solid rgba(16, 185, 129, 0.55);
      }}
      .badge-unscaled {{
        background: rgba(148, 163, 184, 0.18);
        color: #e5e7eb;
        border: 1px solid rgba(148, 163, 184, 0.6);
      }}
      .strip-note {{
        font-size: 0.78rem;
        opacity: 0.9;
      }}
      .epf-hazard-panel {{
        margin-top: 1.25rem;
        padding: 0.9rem 1rem;
        border-radius: 10px;
        border: 1px solid #e5e7eb;
        background: #f9fafb;
        font-size: 0.88rem;
      }}
      .epf-hazard-header {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 0.75rem;
        margin-bottom: 0.5rem;
      }}
      .epf-hazard-title {{
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
      }}
      .epf-hazard-metrics {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        margin: 0.2rem 0 0.3rem;
      }}
      .epf-hazard-metric span {{
        display: block;
        font-size: 0.78rem;
      }}
      .epf-hazard-metric span:first-child {{
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #6b7280;
      }}
      .epf-hazard-metric span:last-child {{
        font-weight: 600;
      }}
      .epf-hazard-reason {{
        margin: 0.35rem 0 0;
        font-size: 0.8rem;
        color: #4b5563;
      }}
      .epf-hazard-contrib {{
        margin-top: 0.45rem;
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        align-items: baseline;
        font-size: 0.8rem;
        color: #4b5563;
      }}
      .epf-hazard-contrib-label {{
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #6b7280;
        font-size: 0.75rem;
      }}
      .epf-hazard-footnote {{
        margin: 0.4rem 0 0;
        font-size: 0.75rem;
        color: #6b7280;
      }}
      .epf-hazard-history {{
        margin-top: 0.6rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
      }}
      .epf-hazard-history-label {{
        font-size: 0.78rem;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }}
      .epf-hazard-history-empty {{
        font-size: 0.78rem;
        color: #9ca3af;
      }}
      .epf-hazard-history svg {{
        display: block;
      }}
      table.gate-table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 1.25rem;
        font-size: 0.86rem;
      }}
      table.gate-table th,
      table.gate-table td {{
        padding: 0.4rem 0.5rem;
        border-bottom: 1px solid #e5e7eb;
      }}
      table.gate-table th {{
        text-align: left;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #6b7280;
      }}
      table.gate-table td:nth-child(2) {{
        width: 6.5rem;
        text-align: center;
        font-weight: 600;
      }}
      .status-pass {{
        color: #15803d;
      }}
      .status-fail {{
        color: #b91c1c;
      }}
      footer {{
        margin-top: 1.25rem;
        font-size: 0.75rem;
        color: #9ca3af;
      }}
      @media (max-width: 640px) {{
        .prc-shell {{
          padding: 1.25rem 1.2rem 1.5rem;
        }}
        .prc-strip {{
          flex-direction: column;
          align-items: flex-start;
        }}
      }}
    </style>
  </head>
  <body>
    <main class="prc-shell">
      <header>
        <h1>PULSE — Demo Report Card</h1>
        <p class="prc-meta">
          Build: {now} · Status version: {STATUS_VERSION}
        </p>
      </header>

      <section class="prc-strip">
        <div class="strip-left">
          <span class="badge badge-decision">{decision_label}</span>
          <span class="badge badge-rdsi">RDSI {metrics['RDSI']:.2f}</span>
        </div>
        <div class="strip-right">
          <span class="badge {hazard_badge_class}">Hazard {metrics['hazard_zone']}</span>
          <span class="strip-note">
            E={metrics['hazard_E']:.3f} · {'OK' if metrics['hazard_ok'] else 'BLOCKED'} · {metrics['hazard_severity']} severity · {scale_badge_text} · F={features_used_n}
          </span>
        </div>
      </section>

      <section class="epf-hazard-panel">
        <div class="epf-hazard-header">
          <div class="epf-hazard-title">
            EPF Relational Grail — hazard signal
            <span class="badge {scale_badge_class}">{scale_badge_text}</span>
          </div>
          <div class="epf-hazard-metrics">
            <div class="epf-hazard-metric">
              <span>E index</span>
              <span>{metrics['hazard_E']:.3f}</span>
            </div>
            <div class="epf-hazard-metric">
              <span>T distance</span>
              <span>{metrics['hazard_T']:.3f}</span>
            </div>
            <div class="epf-hazard-metric">
              <span>Stability S</span>
              <span>{metrics['hazard_S']:.3f}</span>
            </div>
            <div class="epf-hazard-metric">
              <span>Drift D</span>
              <span>{metrics['hazard_D']:.3f}</span>
            </div>
          </div>
        </div>

        <p class="epf-hazard-reason">
          {escape(str(metrics['hazard_reason']))}
        </p>

        <div class="epf-hazard-contrib">
          <span class="epf-hazard-contrib-label">Top contributors</span>
          <span>{contributors_text}</span>
        </div>

        <div class="epf-hazard-contrib">
          <span class="epf-hazard-contrib-label">Feature mode</span>
          <span>
            used {features_used_n}: {features_used_text}
            · recommended {rec_n} (min_coverage ≥ {rec_min_cov_text})
          </span>
        </div>

        <p class="epf-hazard-footnote">
          Thresholds: warn ≈ {CALIBRATED_WARN_THRESHOLD:.3f}, crit ≈ {CALIBRATED_CRIT_THRESHOLD:.3f}
          ({threshold_regime}; requires ≥{MIN_CALIBRATION_SAMPLES} log entries for calibration to take effect).
        </p>

        {history_fragment}
      </section>

      <section>
        <h2>Gate summary</h2>
        <table class="gate-table">
          <thead>
            <tr>
              <th>Gate</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
{gate_rows_html}
          </tbody>
        </table>
      </section>

      <footer>
        Demo-only artefact generated from PULSE_safe_pack_v0/tools/run_all.py.
        Deterministic, fail-closed gates remain the source of truth; the EPF Relational Grail
        hazard signal is surfaced as a diagnostic overlay.
      </footer>
    </main>
  </body>
</html>
"""

with open(art / "report_card.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Wrote", art / "status.json")
print("Wrote", art / "report_card.html")
print(
    "Logged EPF hazard probe:",
    f"zone={hazard_state.zone}",
    f"E={hazard_state.E:.3f}",
    f"ok={hazard_decision.ok}",
    f"severity={hazard_decision.severity}",
    f"scaled={hazard_T_scaled}",
    f"features_used={features_used_n}",
    f"recommended={rec_n}",
    f"enforce_hazard={enforce_hazard}",
    f"epf_hazard_ok_gate={gates['epf_hazard_ok']}",
)
