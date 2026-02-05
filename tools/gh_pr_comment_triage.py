# tools/gh_pr_comment_triage.py
# Használat (CI): python tools/gh_pr_comment_triage.py --summary artifacts/pulse_paradox_gate_summary.json --out triage_comment.md
import argparse, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

TIPS = {
    "settle_time_p95_ms": "Try: enable caching, reduce batch-size, avoid heavy debug logging, precompute hot paths.",
    "downstream_error_rate": "Try: fix top recurring errors, add guard/validation, strengthen tests on failing inputs.",
    "paradox_density": "Try: review prompt/context merges, reduce stochasticity for risky paths, tighten benign transforms."
}

def _decision_key(decision: str) -> str:
    raw_decision = (str(decision) if decision is not None else "").strip()
    if raw_decision.lower().startswith("decision:"):
        raw_decision = raw_decision.split(":", 1)[1].strip()
    if not raw_decision:
        return ""
    return raw_decision.split()[0].split("(")[0].strip().upper()

def _triage_title(decision: str) -> str:
    if _decision_key(decision) == "NORMAL":
        return "### PULSE • Paradox Gate — Triage (shadow)"
    return "### PULSE • Paradox Gate — Why it failed / What to try"

def num(x):
    try:
        return float(x)
    except Exception:
        return None

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True, help="pulse_paradox_gate_summary.json (downloaded artifact)")
    ap.add_argument("--out", default="triage_comment.md", help="Output markdown")
    ap.add_argument(
        "--diagram-json-out",
        default="PULSE_safe_pack_v0/artifacts/paradox_diagram_input_v0.json",
        help="Write paradox diagram input JSON (v0) for future visualization.",
    )
    args = ap.parse_args()

    summary_p = Path(args.summary)
    if not summary_p.exists():
        print(f"ERR: summary not found: {summary_p}", file=sys.stderr)
        sys.exit(2)

    data = json.loads(summary_p.read_text(encoding="utf-8"))
    decision = data.get("decision", "UNKNOWN")
    metrics = data.get("metrics", data)  # fallback: top-level
    # próbáljuk kinyerni budgeteket
    budgets = {}
    for k in ("thresholds", "budgets", "policy"):
        v = data.get(k, {})
        if isinstance(v, dict):
            for kk, vv in v.items():
                if isinstance(vv, (int, float)):
                    budgets[kk] = vv
                elif isinstance(vv, dict):
                    for kkk, vvv in vv.items():
                        if isinstance(vvv, (int, float)):
                            budgets[kkk] = vvv

    keys = ("settle_time_p95_ms", "downstream_error_rate", "paradox_density")
    rows = []
    for k in keys:
        val = num(metrics.get(k))
        bud = budgets.get(k)
        if val is None and k in data:
            val = num(data.get(k))
        line = f"- **{k}**: {val if val is not None else 'n/a'}"
        if isinstance(bud, (int, float)):
            if val is not None:
                delta = val - bud
                sign = ">" if delta > 0 else "≤"
                extra = f" (budget {bud}, Δ{delta:+.3f})"
                line = f"- **{k}**: {val} {sign} {bud}{extra}"
            else:
                line += f" (budget {bud})"
        tip = TIPS.get(k)
        if tip: line += f" — {tip}"
        rows.append(line)

    raw_decision = (str(decision) if decision is not None else "").strip()
    if raw_decision.lower().startswith("decision:"):
        raw_decision = raw_decision.split(":", 1)[1].strip()
    decision_key = _decision_key(raw_decision)
    decision_raw = raw_decision or None

    settle_time_p95_ms = num(metrics.get("settle_time_p95_ms"))
    if settle_time_p95_ms is None:
        settle_time_p95_ms = num(data.get("settle_time_p95_ms"))
    settle_time_budget_ms = num(metrics.get("settle_time_budget_ms"))
    if settle_time_budget_ms is None:
        settle_time_budget_ms = num(data.get("settle_time_budget_ms"))
    if settle_time_budget_ms is None:
        settle_time_budget_ms = num(budgets.get("settle_time_p95_ms"))
    downstream_error_rate = num(metrics.get("downstream_error_rate"))
    if downstream_error_rate is None:
        downstream_error_rate = num(data.get("downstream_error_rate"))
    paradox_density = num(metrics.get("paradox_density"))
    if paradox_density is None:
        paradox_density = num(data.get("paradox_density"))

    missing_metrics: list[str] = []

    def _float_or_none(name: str, v):
        if v is None:
            missing_metrics.append(name)
            return None
        try:
            return float(v)
        except Exception:
            missing_metrics.append(name)
            return None

    settle_time_p95_ms = _float_or_none("settle_time_p95_ms", settle_time_p95_ms)
    settle_time_budget_ms = _float_or_none("settle_time_budget_ms", settle_time_budget_ms)
    downstream_error_rate = _float_or_none("downstream_error_rate", downstream_error_rate)
    paradox_density = _float_or_none("paradox_density", paradox_density)

    md = []
    md.append("<!-- pulse-triage -->")
    md.append(_triage_title(raw_decision))
    md.append("")
    if decision_key == "NORMAL":
        md.append("_Decision is NORMAL (shadow-only; does not gate merges). No action required._")
        md.append("")
    md.append(f"**Decision:** {raw_decision or decision_key} (shadow mode — informational only).")
    if decision_key == "NORMAL":
        md.append("")
        md.append("<details>")
        md.append("<summary>Details (metrics + what to try if this ever fails)</summary>")
        md.append("")
        md.extend(rows)
        md.append("")
        md.append("</details>")
    else:
        md.extend(rows)
    md.append("\n_This comment is auto-generated by the gate workflow triage step._\n")

    out_p = Path(args.out)
    out_p.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Wrote {out_p}")

    # GitHub Actions step output (optional)
    gh_out = os.getenv("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write("triage_body<<EOF\n")
            f.write("\n".join(md) + "\n")
            f.write("EOF\n")

    diagram = {
        "schema_version": "v0",
        "timestamp_utc": _utc_now_iso(),
        "shadow": True,
        "decision_key": decision_key,
        "decision_raw": decision_raw,
        "source": "tools/gh_pr_comment_triage.py",
        "metrics": {
            "settle_time_p95_ms": float(settle_time_p95_ms),
            "settle_time_budget_ms": float(settle_time_budget_ms),
            "downstream_error_rate": float(downstream_error_rate),
            "paradox_density": float(paradox_density),
        },
    }
    if missing_metrics:
        print(
            f"[warn] missing metrics for diagram input: {', '.join(missing_metrics)}",
            file=sys.stderr,
        )
        diagram["missing_metrics"] = missing_metrics
        diagram["notes"] = f"missing metrics: {', '.join(missing_metrics)}"

    outp = Path(args.diagram_json_out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(
        json.dumps(diagram, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"[paradox] wrote diagram input: {outp}")

if __name__ == "__main__":
    main()
