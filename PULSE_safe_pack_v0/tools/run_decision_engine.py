def build_decision_trace(stability_map: dict, state: dict) -> dict:
    decision = state.get("decision") or "UNKNOWN"
    state_type = state.get("type") or "UNSTABLE"

    # Instability + score
    instab = state.get("instability") or {}
    score = float(instab.get("score", 0.0) or 0.0)

    # Az instability payloadban ezek a kulcsok vannak:
    #   safety_component, quality_component, rdsi_component, epf_component
    # Ezeket térképezzük át a schema szerinti nevekre:
    instability_components = {
        "safety": instab.get("safety_component"),
        "quality": instab.get("quality_component"),
        # a séma "rds1"-et vár, de az input "rdsi_component":
        "rds1": instab.get("rdsi_component"),
        "epf": instab.get("epf_component"),
    }

    # Delta curvature (mezőhajlítás) – optional
    delta_curv = state.get("delta_curvature") or {}
    delta_value = delta_curv.get("value")
    delta_band = delta_curv.get("band")

    # Gate- és EPF-információk
    gates = state.get("gate_summary") or {}
    epf = state.get("epf") or {}

    # Paradoxon jelenlét – a Stability Map "paradox.present" flagje alapján
    paradox_info = state.get("paradox") or {}
    paradox_present = bool(
        state.get("paradox_present", paradox_info.get("present", False))
    )

    # Döntési szintű jelölések
    risk_level = compute_risk_level(score)
    action = decide_action(decision, state_type, score)
    dom = dominant_components(instab)

    # Új: stability_tag – külön jelzés a mezőhajlításra érzékeny „jó” döntésekre
    stability_tag: str | None = None
    if score < 0.30:  # „jó” instabilitási tartomány
        if delta_band == "high":
            stability_tag = "unstably_good"
        else:
            stability_tag = "stable_good"

    component_str = ", ".join(
        f"{c['name']}={c['value']:.2f}" for c in dom
    ) or "none"

    summary = (
        f"{action}: {state_type} state with instability {score:.2f} "
        f"(risk={risk_level}, dominant components: {component_str})."
    )

    notes: list[str] = [
        f"Deterministic release decision: {decision}.",
        f"Stability type: {state_type}.",
        f"Instability score: {score:.3f} (risk level: {risk_level}).",
    ]

    if dom:
        notes.append(
            "Dominant instability components: "
            + ", ".join(f"{c['name']}={c['value']:.3f}" for c in dom)
        )

    if gates:
        notes.append(
            "Gate summary: "
            f"safety {gates.get('safety_failed', 0)}/{gates.get('safety_total', 0)} "
            f"failed, quality {gates.get('quality_failed', 0)}/{gates.get('quality_total', 0)} failed."
        )

    # Delta curvature-hez kapcsolódó megjegyzés – csak ha van értelmes jel
    if delta_value is not None and delta_band in {"medium", "high"}:
        band_label = str(delta_band).upper()
        notes.append(
            f"Delta curvature: {delta_value:.3f} ({band_label}); "
            "decision may be field-sensitive even if metrics look clean."
        )

    # Ha van stability_tag, azt is jegyezzük meg emberi nyelven
    if stability_tag is not None:
        notes.append(f"Stability tag: {stability_tag}.")

    # Alap, séma által várt mezők
    details: dict = {
        "release_decision": decision,
        "stability_type": state_type,
        "instability_score": score,
        "instability_components": instability_components,
        "gates": gates,
        "paradox_present": paradox_present,
        "epf": epf,
    }

    # Új, opcionális delta_curvature blokk – séma engedi (additionalProperties: true)
    if delta_value is not None:
        details["delta_curvature"] = {
            "value": float(delta_value),
            "band": delta_band,
        }

    # Új: gép-barát stability_tag is bekerül a details alá (opcionális)
    if stability_tag is not None:
        details["stability_tag"] = stability_tag

    # Extra, fejlesztőbarát mezők
    details["dominant_components"] = dom
    details["gate_summary"] = gates
    details["notes"] = notes

    trace = {
        "version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "state_id": state.get("id"),
        "action": action,
        "risk_level": risk_level,
        "summary": summary,
        "details": details,
    }
    return trace
