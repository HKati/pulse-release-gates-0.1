#!/usr/bin/env python3
"""
Ingest Promptfoo run summary (JSON).
Expected input JSON: {"results":[{"pass":true/false, "name":"...", ...}, ...]}
Usage:
  python tools/adapters/promptfoo_ingest.py --in promptfoo_results.json --out PULSE_safe_pack_v0/artifacts/external/promptfoo_summary.json
"""
import json, argparse
ap = argparse.ArgumentParser()
ap.add_argument('--in', dest='inp', required=True)
ap.add_argument('--out', required=True)
a = ap.parse_args()

data = json.load(open(a.inp, encoding='utf-8'))
res = data.get('results') or []
n = len(res); fails = sum(1 for r in res if not r.get('pass', False))
rate = (fails/n) if n else 0.0
summary = {"tool":"promptfoo","n":n,"fails":fails,"fail_rate":rate}
open(a.out,'w',encoding='utf-8').write(json.dumps(summary,indent=2))
print("Wrote", a.out)