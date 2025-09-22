#!/usr/bin/env python3
"""
Ingest Llama Guard classifications and summarize violation rate.
Input JSONL: each line -> {"input": "...", "output": "...", "llamaguard": {"label":"safe|unsafe", "categories":["HATE","VIOLENCE",...]}}
Usage:
  python tools/adapters/llamaguard_ingest.py --in path/to/lg.jsonl --out PULSE_safe_pack_v0/artifacts/external/llamaguard_summary.json
"""
import json, argparse
ap = argparse.ArgumentParser()
ap.add_argument('--in', dest='inp', required=True)
ap.add_argument('--out', required=True)
a = ap.parse_args()

n=0; unsafe=0; cats={}
with open(a.inp, encoding='utf-8') as f:
    for line in f:
        line=line.strip()
        if not line: continue
        n += 1
        obj = json.loads(line)
        lg = (obj.get('llamaguard') or {})
        label = (lg.get('label') or '').lower()
        if label=='unsafe':
            unsafe += 1
            for c in lg.get('categories') or []:
                cats[c] = cats.get(c,0)+1

rate = (unsafe/n) if n else 0.0
summary = {"tool":"llamaguard","n":n,"unsafe":unsafe,"violation_rate":rate,"by_category":cats}
open(a.out,'w',encoding='utf-8').write(json.dumps(summary,indent=2))
print("Wrote", a.out)