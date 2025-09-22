#!/usr/bin/env python3
"""
Ingest Azure AI Risk & Safety Evaluations export (JSONL).
Input JSONL lines example: {"category":"indirect_jailbreak","passed":true/false, ...}
We compute failure rates for key categories.
Usage:
  python tools/adapters/azure_eval_ingest.py --in azure_eval.jsonl --out PULSE_safe_pack_v0/artifacts/external/azure_eval_summary.json
"""
import json, argparse
ap = argparse.ArgumentParser()
ap.add_argument('--in', dest='inp', required=True)
ap.add_argument('--out', required=True)
a = ap.parse_args()

tot=0; cat_tot={}; cat_fail={}
with open(a.inp, encoding='utf-8') as f:
    for line in f:
        line=line.strip()
        if not line: continue
        tot += 1
        obj = json.loads(line)
        c = obj.get('category') or 'unknown'
        cat_tot[c] = cat_tot.get(c,0)+1
        if obj.get('passed') is False:
            cat_fail[c] = cat_fail.get(c,0)+1

rates = {c: (cat_fail.get(c,0)/cat_tot.get(c,1)) for c in cat_tot}
summary = {"tool":"azure_eval","total":tot,"failures_by_category":cat_fail,"failure_rates":rates}
open(a.out,'w',encoding='utf-8').write(json.dumps(summary,indent=2))
print("Wrote", a.out)