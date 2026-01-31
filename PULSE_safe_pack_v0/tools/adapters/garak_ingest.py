#!/usr/bin/env python3
"""
Ingest Garak run summary (JSON) and produce a compact summary (JSON).

Expected input JSON (approx):
  {
    "findings": [
      {"severity": "critical|high|medium|low|...", "new": true/false, ...},
      ...
    ]
  }

Usage:
  python tools/adapters/garak_ingest.py \
    --in garak_results.json \
    --out PULSE_safe_pack_v0/artifacts/external/garak_summary.json

Notes:
- Keeps rich detail (by severity, new_critical)
- Emits canonical `value` (mirrors new_critical) so downstream tools can read a stable scalar.
- Also emits `rate` for generic fallbacks (conservative + deterministic):
    new_critical > 0 => rate = 1.0
    else            => rate = 0.0
"""
import argparse
import json


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    with open(a.inp, encoding="utf-8") as f:
        data = json.load(f)

    findings = data.get("findings") or []
    tot = len(findings)

    sev = {}
    new_crit = 0
    for fnd in findings:
        s = (fnd.get("severity") or "unknown").lower()
        sev[s] = sev.get(s, 0) + 1
        if fnd.get("new") and s == "critical":
            new_crit += 1

    # Conservative + deterministic: any new critical finding should fail typical thresholds.
    rate = 1.0 if new_crit else 0.0

    summary = {
        "tool": "garak",
        "total_findings": tot,
        "by_severity": sev,
        "new_critical": new_crit,
        # Canonical scalar (mirrors new_critical)
        "value": new_crit,
        # Canonical-ish fallback used by generic readers
        "rate": rate,
    }

    with open(a.out, "w", encoding="utf-8") as f:
        f.write(json.dumps(summary, indent=2))

    print("Wrote", a.out)


if __name__ == "__main__":
    main()
