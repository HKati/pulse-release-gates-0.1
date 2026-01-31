#!/usr/bin/env python3
"""
Ingest Azure eval run results (JSONL) and produce a compact summary (JSON).

Expected input (JSONL):
- one JSON object per line
- fields used:
  - "category" (optional; defaults to "unknown")
  - "passed" (boolean; failures are counted when passed is explicitly False)

Usage:
  python tools/adapters/azure_eval_ingest.py \
    --in azure_eval_results.jsonl \
    --out PULSE_safe_pack_v0/artifacts/external/azure_eval_summary.json

Notes:
- Writes per-category failure_rates (tool-specific detail)
- Writes canonical overall `rate` for generic folding
- Also writes canonical scalar fields for downstream gating consistency:
    - azure_indirect_jailbreak_rate (currently mirrors overall_rate deterministically)
    - value (mirrors the same scalar)
"""
import argparse
import json


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    tot = 0
    cat_tot = {}
    cat_fail = {}

    with open(a.inp, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            tot += 1
            obj = json.loads(line)

            c = obj.get("category") or "unknown"
            cat_tot[c] = cat_tot.get(c, 0) + 1

            if obj.get("passed") is False:
                cat_fail[c] = cat_fail.get(c, 0) + 1

    # Per-category failure rates (detail)
    rates = {c: (cat_fail.get(c, 0) / cat_tot.get(c, 1)) for c in cat_tot}

    # Canonical overall rate for folding into augment_status.py
    fails_total = sum(cat_fail.values())
    overall_rate = (fails_total / tot) if tot else 0.0

    # Deterministic scalar for policy thresholds:
    # At ingestion time we may not have a stable category mapping for "indirect jailbreak".
    # So we mirror the overall failure rate into the named gate scalar for now.
    azure_indirect_jailbreak_rate = overall_rate

    summary = {
        "tool": "azure_eval",
        "total": tot,
        "failures_by_category": cat_fail,
        "failure_rates": rates,

        # Generic canonical key expected by fold_external fallbacks
        "rate": overall_rate,

        # Canonical scalar fields (mirrors the same signal deterministically)
        "azure_indirect_jailbreak_rate": azure_indirect_jailbreak_rate,
        "indirect_jailbreak_rate": azure_indirect_jailbreak_rate,  # helpful alias
        "value": azure_indirect_jailbreak_rate,
    }

    with open(a.out, "w", encoding="utf-8") as f:
        f.write(json.dumps(summary, indent=2))

    print("Wrote", a.out)


if __name__ == "__main__":
    main()
