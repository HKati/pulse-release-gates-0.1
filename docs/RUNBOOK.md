# PULSE Runbook — 5‑minute quickstart

This page shows the minimal, copy‑pasteable way to run PULSE locally and where to find the outputs.
No external runners are required.

---

## Local (Linux/macOS, Python 3.11)

```bash
python PULSE_safe_pack_v0/tools/run_all.py

# Outputs:
#   Artifacts: PULSE_safe_pack_v0/artifacts/status.json
#   (If exporters are wired) JUnit → reports/junit.xml, SARIF → reports/sarif.json
