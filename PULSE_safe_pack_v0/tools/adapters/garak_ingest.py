#!/usr/bin/env python3
"""
Ingest Garak scan results (JSON).
Expected input JSON: {"findings":[{"severity":"critical|high|...", "rule":"...", "new": true/false}, ...]}
If you have CSV -> convert to JSON first.
Usage:
  python tools/adapters/garak_ingest.py --in garak_report.json --out PULSE_safe_pack_v0/artifacts/external/garak_summary.json
"""
import json, argparse
ap = argparse.ArgumentParser()
ap.add_argument('--in', dest='inp', required=True)
ap.add_argument('--out', required=True)
a = ap.parse_args()

data = json.load(open(a.inp, encoding='utf-8'))
findings = data.get('findings') or []
tot = len(findings)
sev = {}; new_crit = 0
for f in findings:
    s = (f.get('severity') or 'unknown').lower()
    sev[s] = sev.get(s,0)+1
    if f.get('new') and s=='critical':
        new_crit += 1

summary = {"tool":"garak","total_findings":tot,"by_severity":sev,"new_critical":new_crit}
open(a.out,'w',encoding='utf-8').write(json.dumps(summary,indent=2))
print("Wrote", a.out)