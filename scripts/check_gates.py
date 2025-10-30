#!/usr/bin/env python3
import argparse, json, os, sys

# engedjük a "saját mappából" az importot
sys.path.append(os.path.dirname(__file__))
from epf_adaptive import EPFAdaptive, EPFConfig  # ugyanebben a mappában lesz

def load_config(path):
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="pulse_gates.yaml")
    p.add_argument("--status", default="status.json")
    p.add_argument("--epf", action="store_true")
    p.add_argument("--epf-shadow", action="store_true")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--defer-policy", choices=["fail","warn"], default="fail")
    args = p.parse_args()

    cfg = load_config(args.config)
    try:
        status = json.load(open(args.status, "r", encoding="utf-8"))
    except Exception:
        status = {}
    metrics = status.get("metrics", {})

    adaptive = EPFAdaptive(seed=args.seed, status_path=args.status)

    decisions = {}
    exp_epf = {}
    all_ok = True

    for g in cfg.get("gates", []):
        gid = g["id"]
        metric_key = g.get("metric_key", gid)
        value = float(metrics.get(metric_key, 0.0))

        # BASELINE: determinisztikus (CI ezt használja)
        base_cfg = EPFConfig(
            threshold=float(g["threshold"]),
            epsilon=float(g.get("epsilon", 0.0)),
            adapt=False,
            max_risk=float(g.get("max_risk", 0.0)),
            ema_alpha=float(g.get("ema_alpha", 0.2)),
            min_samples=int(g.get("min_samples", 5)),
        )
        d_base, _ = adaptive.decide(
            gid, value, base_cfg, {"metric_key": metric_key, "mode": "baseline"}
        )
        decisions[gid] = d_base
        if d_base == "FAIL" or (d_base == "DEFER" and args.defer_policy == "fail"):
            all_ok = False

        # EPF árnyék (nem blokkol CI-t)
        if args.epf or args.epf_shadow:
            epf_cfg = EPFConfig(
                threshold=float(g["threshold"]),
                epsilon=float(g.get("epsilon", 0.0)),
                adapt=bool(g.get("adapt", False)),
                max_risk=float(g.get("max_risk", 0.0)),
                ema_alpha=float(g.get("ema_alpha", 0.2)),
                min_samples=int(g.get("min_samples", 5)),
            )
            d_epf, tr_epf = adaptive.decide(
                gid, value, epf_cfg, {"metric_key": metric_key, "mode": "epf-shadow"}
            )
            exp_epf[gid] = {"decision": d_epf, "trace": tr_epf}

    status.setdefault("decisions", {}).update(decisions)
    if exp_epf:
        status.setdefault("experiments", {})["epf"] = exp_epf
    with open(args.status, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)

    if not all_ok:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
