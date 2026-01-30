#!/usr/bin/env python3
"""
Ingest Promptfoo run summary (JSON).

Expected input JSON:
  {"results":[{"pass":true/false, "name":"...", ...}, ...]}

Usage:
  python tools/adapters/promptfoo_ingest.py \
    --in promptfoo_results.json \
    --out PULSE_safe_pack_v0/artifacts/external/promptfoo_summary.json

Notes:
- Writes both tool-specific `fail_rate` and canonical `rate` so augment_status.py can fold
  metrics deterministically without default fallbacks.
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

    res = data.get("results") or []
    n = len(res)
    fails = sum(1 for r in res if not r.get("pass", False))
    rate = (fails / n) if n else 0.0

    summary = {
        "tool": "promptfoo",
        "n": n,
        "fails": fails,
        # Keep tool-specific key (backward compatibility)
        "fail_rate": rate,
        # Canonical key expected by fold_external fallbacks
        "rate": rate,
    }

    with open(a.out, "w", encoding="utf-8") as f:
        f.write(json.dumps(summary, indent=2))

    print("Wrote", a.out)


if __name__ == "__main__":
    main()
