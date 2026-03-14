#!/usr/bin/env python3
"""
Render the PULSE Quality Ledger from an explicit status.json artefact.

This renderer is a pure reader / renderer:
- it reads a provided status.json,
- it writes static HTML,
- it does not mutate status.json,
- it does not redefine release semantics.

Primary CLI:
  python PULSE_safe_pack_v0/tools/render_quality_ledger.py \
    --status PULSE_safe_pack_v0/artifacts/status.json \
    --out PULSE_safe_pack_v0/artifacts/report_card.html
"""

from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import yaml


def jload(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"Expected top-level JSON object in {path}")
    return obj


def as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def as_str_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for x in value:
        s = str(x).strip()
        if s:
            out.append(s)
    return out


def yload(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            obj = yaml.safe_load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def resolve_gate_policy_path(status_path: Path, metrics: Dict[str, Any]) -> Path | None:
    raw = metrics.get("gate_policy_path")
    if not isinstance(raw, str) or not raw.strip():
        return None

    p = Path(raw.strip())
    if p.is_absolute():
        return p

    candidates = [
        (Path.cwd() / p).resolve(),
        (status_path.parent / p).resolve(),
    ]
    for cand in candidates:
        if cand.exists():
            return cand
    return candidates[0]


def policy_gate_sets(policy: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return the gate-set mapping from the policy document.

    Canonical shape in this repo is top-level:
      gates:
        required: [...]
        core_required: [...]
        advisory: [...]

    Keep a nested fallback for compatibility with older or alternate shapes.
    """
    top_level = as_dict(policy.get("gates"))
    if top_level:
        return top_level

    nested = as_dict(as_dict(policy.get("policy")).get("gates"))
    if nested:
        return nested

    return {}


def html_text(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.3f}"
    return escape(str(value))


def html_short_hash(value: Any, prefix_len: int = 12) -> str:
    if not isinstance(value, str):
        return html_text(value)
    s = value.strip()
    if not s:
        return "—"
    if len(s) <= prefix_len:
        return escape(s)
    return f'<span title="{escape(s)}">{escape(s[:prefix_len])}…</span>'


def gate_status_parts(ok: bool) -> Tuple[str, str]:
    return ("PASS", "status-pass") if ok else ("FAIL", "status-fail")


def select_required_gates(status: Dict[str, Any], *, status_path: Path) -> tuple[List[str], str]:
    """
    Resolve the gate IDs that are actually decision-bearing for the ledger banner.

    Resolution order:
    1. metrics.required_gates (explicit future-proof override)
    2. gate policy file + selected set name
       - metrics.required_gate_set when present
       - else heuristic: core/demo -> core_required, prod -> required

    Returns: (gate_ids, source_label)
    """
    metrics = as_dict(status.get("metrics"))

    explicit = as_str_list(metrics.get("required_gates"))
    if explicit:
        return explicit, "metrics.required_gates"

    set_name_raw = metrics.get("required_gate_set")
    if isinstance(set_name_raw, str) and set_name_raw.strip():
        set_name = set_name_raw.strip()
    else:
        run_mode = str(metrics.get("run_mode", "")).strip().lower()
        set_name = "core_required" if run_mode in {"demo", "core"} else "required"

    policy_path = resolve_gate_policy_path(status_path, metrics)
    if policy_path is None:
        return [], "unresolved"

    policy = yload(policy_path)
    gates_block = policy_gate_sets(policy)

    selected = as_str_list(gates_block.get(set_name))
    if selected:
        return selected, f"policy:{set_name}"

    return [], "unresolved"


def decision_from_status(status: Dict[str, Any], *, status_path: Path) -> Tuple[str, str]:
    metrics = as_dict(status.get("metrics"))
    gates = as_dict(status.get("gates"))

    required_gate_ids, _decision_source = select_required_gates(status, status_path=status_path)
    if not required_gate_ids:
        return "UNKNOWN", "badge-unknown"

    all_required_pass = all(gates.get(gate_id) is True for gate_id in required_gate_ids)
    run_mode = str(metrics.get("run_mode", "")).strip().lower()

    if not all_required_pass:
        return "FAIL", "badge-fail"
    if run_mode == "prod":
        return "PROD-PASS", "badge-pass"
    if run_mode == "core":
        return "STAGE-PASS", "badge-pass"
    if run_mode == "demo":
        return "DEMO-PASS", "badge-pass"
    return "PASS", "badge-pass"


def render_meta_list(rows: Iterable[Tuple[str, Any]]) -> str:
    items = []
    for key, value in rows:
        items.append(
            f"<div class='meta-item'><span class='meta-key'>{escape(str(key))}</span>"
            f"<span class='meta-val'>{html_text(value)}</span></div>"
        )
    return "\n".join(items)


def build_gate_buckets(gates: Dict[str, Any]) -> Dict[str, List[Tuple[str, bool]]]:
    buckets: Dict[str, List[Tuple[str, bool]]] = {
        "safety": [],
        "quality": [],
        "stability": [],
        "other": [],
    }

    for name in sorted(gates.keys(), key=str):
        ok = gates.get(name) is True
        s = str(name)

        if s.startswith(("q1_", "q2_", "q3_", "q4_")):
            buckets["quality"].append((s, ok))
        elif (
            s.startswith("pass_controls_")
            or s.startswith("psf_")
            or "sanit" in s
            or s == "effect_present"
        ):
            buckets["safety"].append((s, ok))
        elif s in {"refusal_delta_pass", "epf_hazard_ok"} or s.startswith("external_"):
            buckets["stability"].append((s, ok))
        else:
            buckets["other"].append((s, ok))

    return buckets


def render_gate_table(title: str, rows: List[Tuple[str, bool]]) -> str:
    if not rows:
        return ""
    body = []
    for name, ok in rows:
        status_text, status_class = gate_status_parts(ok)
        body.append(
            "<tr>"
            f"<td><code>{escape(name)}</code></td>"
            f"<td class='{status_class}'>{status_text}</td>"
            "</tr>"
        )
    return (
        f"<section class='panel'>"
        f"<h2>{escape(title)}</h2>"
        "<table class='ledger-table'>"
        "<thead><tr><th>Gate</th><th>Status</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody>"
        "</table>"
        "</section>"
    )


def render_refusal_delta_section(metrics: Dict[str, Any], gates: Dict[str, Any]) -> str:
    keys = [
        "refusal_delta_n",
        "refusal_delta",
        "refusal_delta_ci_low",
        "refusal_delta_ci_high",
        "refusal_policy",
        "refusal_p_mcnemar",
        "refusal_pass_min",
        "refusal_pass_strict",
    ]
    present = any(k in metrics for k in keys) or ("refusal_delta_pass" in gates)
    if not present:
        return ""

    rows = [
        ("metrics.refusal_delta_n", metrics.get("refusal_delta_n")),
        ("metrics.refusal_delta", metrics.get("refusal_delta")),
        ("metrics.refusal_delta_ci_low", metrics.get("refusal_delta_ci_low")),
        ("metrics.refusal_delta_ci_high", metrics.get("refusal_delta_ci_high")),
        ("metrics.refusal_policy", metrics.get("refusal_policy")),
        ("metrics.refusal_p_mcnemar", metrics.get("refusal_p_mcnemar")),
        ("metrics.refusal_pass_min", metrics.get("refusal_pass_min")),
        ("metrics.refusal_pass_strict", metrics.get("refusal_pass_strict")),
        ("gates.refusal_delta_pass", gates.get("refusal_delta_pass")),
    ]
    body = "".join(
        "<tr>"
        f"<td><code>{escape(name)}</code></td>"
        f"<td>{html_text(value)}</td>"
        "</tr>"
        for name, value in rows
    )
    return (
        "<section class='panel'>"
        "<h2>Stability / refusal-delta</h2>"
        "<table class='ledger-table'>"
        "<thead><tr><th>Field</th><th>Value</th></tr></thead>"
        f"<tbody>{body}</tbody>"
        "</table>"
        "</section>"
    )


def render_external_section(status: Dict[str, Any]) -> str:
    external = as_dict(status.get("external"))
    metrics = as_list(external.get("metrics"))
    if not external and not metrics:
        return ""

    summary = [
        ("external.all_pass", external.get("all_pass")),
        ("external.summaries_present", external.get("summaries_present")),
        ("external.summary_count", external.get("summary_count")),
    ]
    summary_html = "".join(
        "<tr>"
        f"<td><code>{escape(name)}</code></td>"
        f"<td>{html_text(value)}</td>"
        "</tr>"
        for name, value in summary
    )

    detector_rows = []
    for row in metrics:
        if not isinstance(row, dict):
            continue
        ok = row.get("pass") is True
        status_text, status_class = gate_status_parts(ok)
        detector_rows.append(
            "<tr>"
            f"<td><code>{escape(str(row.get('name', 'unknown')))}</code></td>"
            f"<td>{html_text(row.get('value'))}</td>"
            f"<td>{html_text(row.get('threshold'))}</td>"
            f"<td class='{status_class}'>{status_text}</td>"
            "</tr>"
        )

    detectors_table = ""
    if detector_rows:
        detectors_table = (
            "<h3>Detector rows</h3>"
            "<table class='ledger-table'>"
            "<thead><tr><th>Name</th><th>Value</th><th>Threshold</th><th>Status</th></tr></thead>"
            f"<tbody>{''.join(detector_rows)}</tbody>"
            "</table>"
        )

    return (
        "<section class='panel'>"
        "<h2>External detectors</h2>"
        "<table class='ledger-table'>"
        "<thead><tr><th>Field</th><th>Value</th></tr></thead>"
        f"<tbody>{summary_html}</tbody>"
        "</table>"
        f"{detectors_table}"
        "</section>"
    )


def render_q1_reference_shadow_section(status: Dict[str, Any]) -> str:
    meta = as_dict(status.get("meta"))
    q1 = as_dict(meta.get("q1_reference_shadow"))
    if not q1:
        return ""

    summary_artifact = as_dict(q1.get("summary_artifact"))

    rows = [
        ("meta.q1_reference_shadow.pass", html_text(q1.get("pass"))),
        ("meta.q1_reference_shadow.grounded_rate", html_text(q1.get("grounded_rate"))),
        ("meta.q1_reference_shadow.wilson_lower_bound", html_text(q1.get("wilson_lower_bound"))),
        ("meta.q1_reference_shadow.n_eligible", html_text(q1.get("n_eligible"))),
        ("meta.q1_reference_shadow.threshold", html_text(q1.get("threshold"))),
        ("meta.q1_reference_shadow.summary_artifact.path", html_text(summary_artifact.get("path"))),
        (
            "meta.q1_reference_shadow.summary_artifact.sha256",
            html_short_hash(summary_artifact.get("sha256")),
        ),
    ]

    body = "".join(
        "<tr>"
        f"<td><code>{escape(name)}</code></td>"
        f"<td>{value_html}</td>"
        "</tr>"
        for name, value_html in rows
    )

    return (
        "<section class='panel'>"
        "<h2>Q1 reference shadow</h2>"
        "<p class='subtle'>"
        "Shadow-only visibility block. Descriptive only; not normative gate evidence."
        "</p>"
        "<table class='ledger-table'>"
        "<thead><tr><th>Field</th><th>Value</th></tr></thead>"
        f"<tbody>{body}</tbody>"
        "</table>"
        "</section>"
    )


def render_hazard_section(metrics: Dict[str, Any]) -> str:
    hazard_keys = [
        "hazard_zone",
        "hazard_E",
        "hazard_T",
        "hazard_S",
        "hazard_D",
        "hazard_reason",
        "hazard_topology_region",
        "hazard_baseline_ok",
        "hazard_gate_id",
        "hazard_T_scaled",
        "hazard_stability_map_schema",
        "hazard_stability_map_path",
    ]
    if not any(k in metrics for k in hazard_keys):
        return ""

    rows = [
        ("metrics.hazard_zone", metrics.get("hazard_zone")),
        ("metrics.hazard_E", metrics.get("hazard_E")),
        ("metrics.hazard_T", metrics.get("hazard_T")),
        ("metrics.hazard_S", metrics.get("hazard_S")),
        ("metrics.hazard_D", metrics.get("hazard_D")),
        ("metrics.hazard_reason", metrics.get("hazard_reason")),
        ("metrics.hazard_topology_region", metrics.get("hazard_topology_region")),
        ("metrics.hazard_baseline_ok", metrics.get("hazard_baseline_ok")),
        ("metrics.hazard_gate_id", metrics.get("hazard_gate_id")),
        ("metrics.hazard_T_scaled", metrics.get("hazard_T_scaled")),
        ("metrics.hazard_stability_map_schema", metrics.get("hazard_stability_map_schema")),
        ("metrics.hazard_stability_map_path", metrics.get("hazard_stability_map_path")),
    ]

    body = "".join(
        "<tr>"
        f"<td><code>{escape(name)}</code></td>"
        f"<td>{html_text(value)}</td>"
        "</tr>"
        for name, value in rows
        if value is not None
    )
    return (
        "<section class='panel'>"
        "<h2>EPF hazard overlay</h2>"
        "<table class='ledger-table'>"
        "<thead><tr><th>Field</th><th>Value</th></tr></thead>"
        f"<tbody>{body}</tbody>"
        "</table>"
        "<p class='subtle'>"
        "Diagnostic overlay only. status.json and gate enforcement remain the source of truth."
        "</p>"
        "</section>"
    )


def render_traceability(status_path: Path, status: Dict[str, Any]) -> str:
    metrics = as_dict(status.get("metrics"))
    rows = [
        ("status.json", str(status_path)),
        ("version", status.get("version")),
        ("created_utc", status.get("created_utc")),
        ("metrics.gate_policy_path", metrics.get("gate_policy_path")),
        ("metrics.gate_policy_sha256", metrics.get("gate_policy_sha256")),
        ("metrics.git_sha", metrics.get("git_sha")),
        ("metrics.run_key", metrics.get("run_key")),
    ]
    body = "".join(
        "<tr>"
        f"<td><code>{escape(name)}</code></td>"
        f"<td>{html_text(value)}</td>"
        "</tr>"
        for name, value in rows
    )
    return (
        "<section class='panel'>"
        "<h2>Traceability</h2>"
        "<table class='ledger-table'>"
        "<thead><tr><th>Field</th><th>Value</th></tr></thead>"
        f"<tbody>{body}</tbody>"
        "</table>"
        "</section>"
    )


def render_quality_ledger(status: Dict[str, Any], *, status_path: Path) -> str:
    metrics = as_dict(status.get("metrics"))
    gates = as_dict(status.get("gates"))
    diagnostics = as_dict(status.get("diagnostics"))

    decision_label, decision_class = decision_from_status(status, status_path=status_path)
    gate_buckets = build_gate_buckets(gates)

    header_meta = render_meta_list(
        [
            ("version", status.get("version")),
            ("created_utc", status.get("created_utc")),
            ("run_mode", metrics.get("run_mode")),
            ("git_sha", metrics.get("git_sha")),
            ("run_key", metrics.get("run_key")),
            ("RDSI", metrics.get("RDSI")),
        ]
    )

    diagnostics_html = ""
    if diagnostics:
        diag_rows = "".join(
            "<tr>"
            f"<td><code>{escape(str(k))}</code></td>"
            f"<td>{html_text(v)}</td>"
            "</tr>"
            for k, v in sorted(diagnostics.items(), key=lambda kv: str(kv[0]))
        )
        diagnostics_html = (
            "<section class='panel'>"
            "<h2>Diagnostics</h2>"
            "<table class='ledger-table'>"
            "<thead><tr><th>Field</th><th>Value</th></tr></thead>"
            f"<tbody>{diag_rows}</tbody>"
            "</table>"
            "</section>"
        )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>PULSE Quality Ledger</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {{
      --bg: #f7f7fb;
      --panel: #ffffff;
      --ink: #1f2430;
      --muted: #5f6b7a;
      --border: #dde3ea;
      --pass-bg: #eaf7ee;
      --pass-fg: #136f3a;
      --fail-bg: #fdecec;
      --fail-fg: #a12626;
      --note-bg: #f3f6fb;
      --shadow: 0 1px 2px rgba(17,24,39,0.06);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 24px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      color: var(--ink);
      background: var(--bg);
      line-height: 1.45;
    }}
    .wrap {{
      max-width: 1100px;
      margin: 0 auto;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px;
      margin: 0 0 16px 0;
      box-shadow: var(--shadow);
    }}
    h1, h2, h3 {{
      margin: 0 0 12px 0;
    }}
    .subtle {{
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .decision {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }}
    .badge {{
      display: inline-block;
      padding: 6px 12px;
      border-radius: 999px;
      font-weight: 700;
      font-size: 0.95rem;
    }}
    .badge-pass {{
      background: var(--pass-bg);
      color: var(--pass-fg);
    }}
    .badge-fail {{
      background: var(--fail-bg);
      color: var(--fail-fg);
    }}
    .badge-unknown {{
      background: var(--note-bg);
      color: var(--muted);
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px 14px;
    }}
    .meta-item {{
      display: flex;
      flex-direction: column;
      gap: 2px;
      padding: 10px 12px;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: #fbfcfe;
    }}
    .meta-key {{
      color: var(--muted);
      font-size: 0.85rem;
    }}
    .meta-val {{
      font-weight: 600;
      word-break: break-word;
    }}
    .ledger-table {{
      width: 100%;
      border-collapse: collapse;
    }}
    .ledger-table th,
    .ledger-table td {{
      text-align: left;
      padding: 9px 10px;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
    }}
    .ledger-table th {{
      color: var(--muted);
      font-weight: 600;
      background: #fbfcfe;
    }}
    .status-pass {{
      color: var(--pass-fg);
      font-weight: 700;
    }}
    .status-fail {{
      color: var(--fail-fg);
      font-weight: 700;
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.92em;
    }}
    .footer {{
      color: var(--muted);
      font-size: 0.92rem;
      margin-top: 12px;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="panel">
      <div class="decision">
        <div>
          <h1>PULSE Quality Ledger</h1>
          <p class="subtle">Human-readable view over a single immutable status.json artefact.</p>
        </div>
        <div class="badge {decision_class}">{escape(decision_label)}</div>
      </div>
      <div class="meta-grid">
        {header_meta}
      </div>
    </section>

    {render_gate_table("Safety gates", gate_buckets["safety"])}
    {render_gate_table("Quality gates", gate_buckets["quality"])}
    {render_refusal_delta_section(metrics, gates)}
    {render_external_section(status)}
    {render_q1_reference_shadow_section(status)}
    {render_hazard_section(metrics)}
    {render_gate_table("Other gates", gate_buckets["other"])}
    {render_gate_table("Stability / auxiliary gates", gate_buckets["stability"])}
    {diagnostics_html}
    {render_traceability(status_path, status)}

    <div class="footer">
      CI and gate enforcement remain anchored to <code>status.json</code>.
      This ledger is a pure reader / renderer.
    </div>
  </div>
</body>
</html>
"""
    return html


def write_quality_ledger(status_path: Path | str, out_path: Path | str) -> Path:
    """
    Render Quality Ledger HTML from an explicit status.json path into an output path.

    Pure reader / renderer:
    - reads status.json
    - writes HTML
    - does not mutate the source artefact
    """
    status_path = Path(status_path).resolve()
    out_path = Path(out_path).resolve()

    status = jload(status_path)
    html = render_quality_ledger(status, status_path=status_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", required=True, help="Path to status.json")
    parser.add_argument("--out", required=True, help="Output HTML path")
    args = parser.parse_args()

    out_path = write_quality_ledger(args.status, args.out)
    print("Rendered", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

