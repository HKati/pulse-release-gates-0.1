#!/usr/bin/env python3
"""
Ingest DeepEval summary (JSONL or JSON).
Input can be JSONL lines: {"metric":"...", "passed":true/false, "score":0.0-1.0}
or JSON: {"results":[...]} with same items.
Usage:
  python tools/adapters/deepeval_ingest.py --in deepeval.jsonl --out PULSE_safe_pack_v0/artifacts/external/deepeval_summary.json
"""
import json, argparse, os

ap = argparse.ArgumentParser()
ap.add_argument('--in', dest='inp', required=True)
ap.add_argument('--out', required=True)
a = ap.parse_args()

items = []
with open(a.inp, encoding='utf-8') as f:
    txt = f.read().strip()
    if txt.startswith('{'):
        data = json.loads(txt)
        items = data.get('results', [])
    else:
        for line in txt.splitlines():
            if line.strip():
                items.append(json.loads(line))

n = len(items)
fails = sum(1 for it in items if not it.get('passed', False))
rate = (fails / n) if n else 0.0

by_metric = {}
for it in items:
    m = it.get('metric') or 'unknown'
    by_metric[m] = by_metric.get(m, 0) + (0 if it.get('passed', False) else 1)

summary = {
    "tool": "deepeval",
    "n": n,
    "fails": fails,
    "fail_rate": rate,
    # Canonical keys (mirror fail_rate) for downstream consumers
    "rate": rate,
    "value": rate,
    "fails_by_metric": by_metric,
}

open(a.out, 'w', encoding='utf-8').write(json.dumps(summary, indent=2))
print("Wrote", a.out)
