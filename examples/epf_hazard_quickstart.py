from PULSE_safe_pack_v0.epf.epf_hazard_forecast import (
    HazardConfig,
    forecast_hazard,
)


def main():
    cfg = HazardConfig()
    history_T: list[float] = []

    # very small toy loop
    snapshots = [
        {"m": 1.0},
        {"m": 1.05},
        {"m": 1.10},
        {"m": 1.30},
        {"m": 1.80},
    ]
    reference = {"m": 1.0}

    for step, current in enumerate(snapshots):
        stability_metrics = {"RDSI": 0.9}  # pretend fairly stable
        state = forecast_hazard(
            current_snapshot=current,
            reference_snapshot=reference,
            stability_metrics=stability_metrics,
            history_T=history_T,
            cfg=cfg,
        )
        history_T.append(state.T)

        print(
            f"t={step:02d}  T={state.T:.3f}  S={state.S:.2f}  "
            f"D={state.D:.3f}  E={state.E:.3f}  zone={state.zone}"
        )
        print("   reason:", state.reason)

    print("\nDone.")


if __name__ == "__main__":
    main()
