# tools/pulse_init_mvp.py
# Baseline NDJSON -> suggested budgets/thresholds for the paradox gate (MVP).
# Usage:
#   python tools/pulse_init_mvp.py --log ./logs/decision_log.ndjson --out policy_suggest_paradox.yaml
import argparse, json, math, sys
from pathlib import Path

def wilson_interval(k, n, z=1.96):
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1.0 + (z*z)/n
    center = (p + (z*z)/(2*n)) / denom
    half = (z * math.sqrt((p*(1-p))/n + (z*z)/(4*n*n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))

def p95(values):
    if not values:
        return None
    values = sorted(values)
    idx = max(0, math.ceil(0.95 * len(values)) - 1)
    return int(values[idx])

def fmt_rate(k, n):
    if n <= 0: return "n/a"
    return f"{k}/{n} = {k/n:.3f}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True, help="NDJSON decision log (e.g., ./logs/decision_log.ndjson)")
    ap.add_argument("--out", default="policy_suggest_paradox.yaml", help="Output YAML path")
    ap.add_argument("--headroom_pct", type=float, default=10.0, help="Headroom for p95 latency (%)")
    ap.add_argument("--z", type=float, default=1.96, help="z-score for Wilson (default 1.96 ~95%)")
    ap.add_argument("--rate_eps", type=float, default=0.005, help="extra absolute headroom for rates")
    args = ap.parse_args()

    log_path = Path(args.log)
    if not log_path.exists():
        print(f"ERR: log not found: {log_path}", file=sys.stderr)
        sys.exit(2)

    settles, err_flags, paradox_flags = [], [], []
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = rec.get("settle_ms")
            if isinstance(t, (int, float)) and t >= 0:
                settles.append(int(t))
            e = rec.get("error")
            if isinstance(e, bool):
                err_flags.append(e)
            px = rec.get("paradox")
            if isinstance(px, bool):
                paradox_flags.append(px)

    # p95 latency
    p95_latency = p95(settles)
    budget_latency = None
    if p95_latency is not None:
        budget_latency = int(round(p95_latency * (1.0 + args.headroom_pct/100.0)))

    # error rate
    n_err = len(err_flags)
    k_err = sum(1 for v in err_flags if v)
    _, u_err = wilson_interval(k_err, n_err, z=args.z)
    budget_err = None if n_err == 0 else round(min(1.0, u_err + args.rate_eps), 3)

    # paradox density
    n_px = len(paradox_flags)
    k_px = sum(1 for v in paradox_flags if v)
    _, u_px = wilson_interval(k_px, n_px, z=args.z)
    budget_px = None if n_px == 0 else round(min(1.0, u_px + args.rate_eps), 3)

    # Output YAML
    out_p = Path(args.out)
    lines = ["# Suggested budgets for the 'paradox gate' (MVP)",
             f"# source_log: {log_path}",
             "paradox_gate:",
             "  budgets:"]
    if budget_latency is not None:
        lines.append(f"    settle_time_p95_ms: {budget_latency}  # observed {p95_latency} ms + {args.headroom_pct:.0f}% headroom")
    lines.append("  thresholds:")
    if budget_err is not None:
        lines.append(f"    downstream_error_rate_max: {budget_err}  # Wilson upper + {args.rate_eps:.3f}")
    if budget_px is not None:
        lines.append(f"    paradox_density_max: {budget_px}  # Wilson upper + {args.rate_eps:.3f}")

    out_p.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Human summary
    print("=== PULSE init (paradox gate • MVP) ===")
    print(f"log: {log_path}")
    if p95_latency is not None:
        print(f"settle_time_p95_ms: observed {p95_latency} -> budget {budget_latency}")
    else:
        print("settle_time_p95_ms: n/a (no settle_ms in log)")
    print(f"downstream_error_rate: {fmt_rate(k_err, n_err)} -> budget {budget_err if budget_err is not None else 'n/a'}")
    print(f"paradox_density: {fmt_rate(k_px, n_px)} -> budget {budget_px if budget_px is not None else 'n/a'}")
    print(f"wrote: {out_p}")

if __name__ == "__main__":
    main()
