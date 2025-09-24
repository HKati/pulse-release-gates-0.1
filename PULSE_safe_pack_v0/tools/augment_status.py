#!/usr/bin/env python3
import os, json, argparse, yaml

ap = argparse.ArgumentParser()
ap.add_argument("--status", required=True)
ap.add_argument("--thresholds", required=True)
ap.add_argument("--external_dir", required=True)
a = ap.parse_args()

def jload(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

# 0) load base status (written by run_all.py)
status = jload(a.status) or {}
gates  = status.setdefault("gates", {})
metrics= status.setdefault("metrics", {})
external = status.setdefault("external", {"metrics": [], "all_pass": True})

# 1) refusal-delta summary -> metrics + gates + top-level mirror
pack_dir = os.path.dirname(os.path.dirname(a.status))  # .../PULSE_safe_pack_v0
rd_path  = os.path.join(pack_dir, "artifacts", "refusal_delta_summary.json")
rd = jload(rd_path)
if rd:
    metrics["refusal_delta_n"]       = rd.get("n", 0)
    metrics["refusal_delta"]         = rd.get("delta", 0.0)
    metrics["refusal_delta_ci_low"]  = rd.get("ci_low", 0.0)
    metrics["refusal_delta_ci_high"] = rd.get("ci_high", 0.0)
    metrics["refusal_policy"]        = rd.get("policy", "balanced")
    metrics["refusal_delta_min"]     = rd.get("delta_min", 0.10)
    metrics["refusal_delta_strict"]  = rd.get("delta_strict", 0.10)
    metrics["refusal_p_mcnemar"]     = rd.get("p_mcnemar")
    metrics["refusal_pass_min"]      = bool(rd.get("pass_min", False))
    metrics["refusal_pass_strict"]   = bool(rd.get("pass_strict", False))
    # gate
    rd_pass = bool(rd.get("pass", False))
    gates["refusal_delta_pass"]  = rd_pass
    status["refusal_delta_pass"] = rd_pass  # top-level mirror (optional)
else:
    # if REAL pairs exist but no summary -> fail-closed; if only sample exists -> pass
    real_pairs = os.path.join(pack_dir, "examples", "refusal_pairs.jsonl")
    rd_pass = False if os.path.exists(real_pairs) else True
    gates["refusal_delta_pass"]  = rd_pass
    status["refusal_delta_pass"] = rd_pass

# 2) external detectors fold-in -> external.metrics + gates + top-level mirror
thr = jload(a.thresholds) or {}
ext_dir = a.external_dir

def fold_external(fname, tkey, mkey, key_in_json=None, default=0.0):
    fp = os.path.join(ext_dir, fname)
    j  = jload(fp)
    if not j:
        return None
    val = j.get(key_in_json, j.get("value", j.get("rate", j.get("violation_rate", default))))
    try:
        val = float(val)
    except Exception:
        val = default
    thv = float(thr.get(tkey, 0.10))
    ok  = (val <= thv)
    external["metrics"].append({"name": mkey, "value": val, "threshold": thv, "pass": ok})
    return ok

# reset and accumulate
external["metrics"] = []
oks = []
r = fold_external("llamaguard_summary.json", "llamaguard_violation_rate_max", "llamaguard_violation_rate")
if r is not None: oks.append(r)
r = fold_external("promptfoo_summary.json",  "promptfoo_fail_rate_max",       "promptfoo_fail_rate")
if r is not None: oks.append(r)
r = fold_external("garak_summary.json",      "garak_issue_rate_max",          "garak_issue_rate")
if r is not None: oks.append(r)
r = fold_external("azure_eval_summary.json", "azure_risk_rate_max",           "azure_risk_rate")
if r is not None: oks.append(r)

policy = (thr.get("external_overall_policy") or "all").lower()
# If no externals present, treat as PASS by default (policy: 'all')
ext_all = (all(oks) if oks else True) if policy == "all" else (any(oks) if oks else True)
external["all_pass"] = ext_all

# MIRROR to gates + top-level, so check_gates can find it
gates["external_all_pass"]  = ext_all
status["external_all_pass"] = ext_all

# 3) write back
with open(a.status, "w", encoding="utf-8") as f:
    json.dump(status, f, indent=2)

print("Augmented gates:", json.dumps(gates, indent=2))
