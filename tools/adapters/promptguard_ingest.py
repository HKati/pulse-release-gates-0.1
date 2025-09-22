#!/usr/bin/env python3
"""
Ingest Prompt Guard (or similar prompt attack detector) results.
Input JSONL: {"prompt": "...", "detector": {"attack": true/false, "type":"indirect|direct|..."}}
Usage:
  python tools/adapters/promptguard_ingest.py --in pg.jsonl --out PULSE_safe_pack_v0/artifacts/external/promptguard_summary.json
"""
import json, argparse
ap = argparse.ArgumentParser()
ap.add_argument('--in', dest='inp', required=True)
ap.add_argument('--out', required=True)
a = ap.parse_args()

n=0; attacks=0; types={}
with open(a.inp, encoding='utf-8') as f:
    for line in f:
        line=line.strip()
        if not line: continue
        n += 1
        obj = json.loads(line)
        det = obj.get('detector') or {}
        if det.get('attack'):
            attacks += 1
            t = det.get('type') or 'unknown'
            types[t] = types.get(t,0)+1

rate = (attacks/n) if n else 0.0
summary = {"tool":"promptguard","n":n,"attacks":attacks,"attack_detect_rate":rate,"by_type":types}
open(a.out,'w',encoding='utf-8').write(json.dumps(summary,indent=2))
print("Wrote", a.out)