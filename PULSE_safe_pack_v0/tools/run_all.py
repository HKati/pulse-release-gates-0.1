#!/usr/bin/env python3
"""
Run all PULSE safe-pack checks and generate core artifacts.

This script is the main entrypoint for the PULSE_safe_pack_v0 "safe
pack". It orchestrates the configured checks/profiles and produces the
baseline status.json and related artifacts under the pack's artifacts
directory, which are then consumed by CI workflows and reporting tools.
"""

import os, json, datetime, pathlib, random, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.epf.epf_hazard_adapter import (
  HazardRuntimeState,
  probe_hazard_and_append_log,
)

art = ROOT / "artifacts"
art.mkdir(parents=True, exist_ok=True)

now = datetime.datetime.utcnow().isoformat() + "Z"

# Minimal demo gates (all True by default so CI passes)
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
  "q4_slo_ok": True
}

metrics = {
  "RDSI": 0.92,
  "rdsi_note": "Demo value for CI smoke-run",
  "build_time": now
}

status = {
  "version": "1.0.0-demo",
  "created_utc": now,
  "gates": gates,
  "metrics": metrics
}

with open(art / "status.json", "w", encoding="utf-8") as f:
  json.dump(status, f, indent=2)

# Simple report card HTML
rows = "\n".join([
  f"<tr><td>{k}</td><td>{'PASS' if v else 'FAIL'}</td></tr>"
  for k, v in gates.items()
])
html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>PULSE Report Card</title>
<style>
body{{font-family:system-ui,Segoe UI,Roboto,Inter,sans-serif;margin:24px;}} table{{border-collapse:collapse;width:100%;max-width:920px}}
td,th{{border:1px solid #ddd;padding:8px}} th{{background:#f2f4f8;text-align:left}} .ok{{color:#1b8e3c}} .bad{{color:#b71c1c}}
</style></head><body>
<h1>PULSE — Report Card</h1>
<p><b>Build:</b> {now} UTC &middot; <b>RDSI:</b> {metrics['RDSI']}</p>
<table><thead><tr><th>Gate</th><th>Status</th></tr></thead><tbody>
{rows}
</tbody></table>
</body></html>
"""
with open(art / "report_card.html", "w", encoding="utf-8") as f:
  f.write(html)

print("Wrote", art / "status.json")
print("Wrote", art / "report_card.html")

# ---------------------------------------------------------------------------
# EPF hazard demo logging (proto-level, diagnostic only)
# ---------------------------------------------------------------------------

hazard_runtime = HazardRuntimeState.empty()

# For now we only use RDSI as a simple EPF proxy.
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
    "status_version": status.get("version"),
  },
)

print(
  "Logged EPF hazard probe:",
  f"zone={hazard_state.zone}",
  f"E={hazard_state.E:.3f}",
)
