---- START FILE ----
#!/usr/bin/env python3
import argparse, json, pathlib

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--status", required=True)
    p.add_argument("--ledger", default=None)
    p.add_argument("--out", default="pulse_report.md")
    args = p.parse_args()

    data = json.load(open(args.status, "r", encoding="utf-8"))
    run = data.get("run", {})
    res = data.get("results", {})
    sec = res.get("security", {})
    qua = res.get("quality", {})
    slo = res.get("slo", {})
    rds = data.get("rds_index", {})

    def pf(v):
        return "PASS" if v in ("PASS", True, "true", "True") else ("FAIL" if v in ("FAIL", False, "false", "False") else str(v))

    security_summary = ", ".join([f"{k}:{pf(v)}" for k, v in sec.items()]) or "—"

    qparts = []
    if "q1_grounded_ok" in qua:
        q1 = qua["q1_grounded_ok"]; qparts.append(f"Q1 grounded:{'PASS' if q1.get('pass') else 'FAIL'} (score {q1.get('rag_groundedness','?')} ≥ {q1.get('threshold','?')}, cov {q1.get('coverage','?')})")
    if "q2_consistency_ok" in qua:
        q2 = qua["q2_consistency_ok"]; qparts.append(f"Q2 consistency:{'PASS' if q2.get('pass') else 'FAIL'} (disagree {q2.get('disagreement_rate','?')} ≤ {q2.get('max_allowed','?')})")
    if "q3_fairness_ok" in qua:
        q3 = qua["q3_fairness_ok"]; qparts.append(f"Q3 fairness:{'PASS' if q3.get('pass') else 'FAIL'} (parity {q3.get('group_parity','?')} ≥ {q3.get('min_allowed','?')})")
    quality_summary = " | ".join(qparts) if qparts else "—"

    if "q4_slo_ok" in slo:
        q4 = slo["q4_slo_ok"]
        slo_line = f"p50 {q4.get('p50_latency_ms','?')}ms | p95 {q4.get('p95_latency_ms','?')}ms | cost {q4.get('cost_usd_per_1k_tokens','?')}/1k tok"
    else:
        slo_line = "—"

    decision = data.get("badges", {}).get("pulse") or ("FAIL" if "FAIL" in (security_summary + quality_summary + slo_line) else "PASS")
    rds_line = f"{rds.get('ci_lower','?')} – {rds.get('ci_upper','?')} (runs: {rds.get('runs','?')})" if rds else "—"

    md = []
    md.append("### PULSE Gate Report (LLM Release Gates)\n\n")
    md.append(f"**Commit**: `{run.get('commit','?')}` | **Profile**: `{run.get('profile_id','?')} ({run.get('profile_hash','?')})` | **Seed**: `{run.get('seed','?')}`  \n")
    md.append(f"**RDSI**: `{rds_line}`\n\n")
    md.append(f"**Security (I₂–I₇)**: {security_summary}\n\n")
    md.append(f"**Quality (Q₁–Q₄)**: {quality_summary}\n\n")
    md.append(f"**SLO (Q₄)**: {slo_line}\n\n")
    md.append(f"**Decision**: **{decision}**\n")
    if args.ledger:
        md.append(f"Details → Quality Ledger (`{pathlib.Path(args.ledger).as_posix()}`)\n")

    pathlib.Path(args.out).write_text("".join(md), encoding="utf-8")
    print("".join(md))

if __name__ == "__main__":
    main()
---- END FILE ----
