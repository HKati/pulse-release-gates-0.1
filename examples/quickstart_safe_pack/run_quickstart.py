#!/usr/bin/env python3
import json
from pathlib import Path


def load_status():
    here = Path(__file__).resolve().parent
    status_path = here / "status_quickstart.json"
    with status_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def fmt_pct(x):
    if x is None:
        return "n/a"
    return f"{x * 100:.1f}%"


def main() -> None:
    status = load_status()

    model_id = status.get("model", {}).get("id", "<unknown-model>")
    profile = status.get("profile", "<unknown-profile>")
    decision = status.get("decision", "<unknown-decision>")

    rds = status.get("rds_index", {})
    rds_value = rds.get("value")
    rds_ci_low = rds.get("ci_low")
    rds_ci_high = rds.get("ci_high")

    metrics = status.get("metrics", {})
    thresholds = status.get("thresholds", {})
    gates = status.get("gates", {})

    print("PULSE quickstart – demo status.json\n")
    print(f"Model:    {model_id}")
    print(f"Profile:  {profile}")
    print(f"Decision: {decision}")

    if rds_value is not None and rds_ci_low is not None and rds_ci_high is not None:
        print(f"RDSI:     {rds_value:.2f} (CI: {rds_ci_low:.2f}–{rds_ci_high:.2f})")

    print()

    # Refusal delta
    n_pairs = metrics.get("refusal_delta_n")
    delta = metrics.get("refusal_delta")
    delta_min = thresholds.get("refusal_delta_min")
    gate_refusal = gates.get("refusal_delta_pass")

    if n_pairs is not None and delta is not None and delta_min is not None:
        sign = "+" if delta >= 0 else ""
        print(
            f"Refusal delta: {sign}{delta:.2f} on {n_pairs} pairs "
            f"(threshold ≥ {delta_min:.2f}) -> refusal_delta_pass = {gate_refusal}"
        )

    # External detectors
    gate_external = gates.get("external_all_pass")
    if gate_external is not None:
        print(
            f"External detectors: external_all_pass = {gate_external} "
            "(all configured detectors within their thresholds in this demo)"
        )

    # Groundedness (Q1)
    grounded = metrics.get("q1_groundedness")
    grounded_min = thresholds.get("q1_groundedness_min")
    if grounded is not None and grounded_min is not None:
        print(
            f"Groundedness (Q1): {fmt_pct(grounded)} "
            f"(target ≥ {fmt_pct(grounded_min)})"
        )

    # Latency SLO (Q4)
    p95 = metrics.get("q4_latency_p95_ms")
    p95_max = thresholds.get("q4_latency_p95_max_ms")
    if p95 is not None and p95_max is not None:
        print(
            f"Latency p95 (Q4): {p95:.0f} ms "
            f"(SLO ≤ {p95_max:.0f} ms)"
        )

    # Combined quality/SLO gate and overall decision
    gate_quality_slo = gates.get("quality_slo_pass")
    gate_overall = gates.get("overall_pass")

    if gate_quality_slo is not None:
        print(f"\nQuality/SLO gate: quality_slo_pass = {gate_quality_slo}")
    if gate_overall is not None:
        print(f"Overall gate:     overall_pass = {gate_overall}")

    print(
        "\nDone. For a fuller human-readable view, see the Quality Ledger "
        "example in docs/quality_ledger_example.md."
    )


if __name__ == "__main__":
    main()
