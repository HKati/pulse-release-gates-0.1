#!/usr/bin/env python3
"""
generate_theory_overlay_v0.py

Populate theory_overlay_v0.json with record-horizon (G/tidality) diagnostics.

- stdlib-only
- deterministic output (no timestamps)
- CI-neutral in v0: exits 0 even on FAIL; status is reflected in gates_shadow/evidence
- allowed gate statuses: PASS/FAIL/MISSING (per contract check)
"""

import argparse
import hashlib
import json
import math
import os
from typing import Any, Dict, Optional, Tuple

REQUIRED_TOP_KEYS = ["schema", "inputs_digest", "gates_shadow", "cases", "evidence"]
ALLOWED_GATE_STATUSES = {"PASS", "FAIL", "MISSING"}

C_DEFAULT = 299792458.0
G_DEFAULT = 6.6743e-11
HORIZON_B_TILDE = 1.0  # record-horizon definition (hard)

# Gate name we populate
GATE_NAME = "g_record_horizon_v0"


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def _sha256_hex(obj: Any) -> str:
    b = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def _as_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _get_env_float(name: str) -> Optional[float]:
    return _as_float(os.environ.get(name))


def _ensure_skeleton(existing: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if isinstance(existing, dict):
        data = existing
    else:
        data = {}

    # Ensure required keys exist
    data.setdefault("schema", "theory_overlay_v0")
    data.setdefault("inputs_digest", "0" * 64)
    data.setdefault("gates_shadow", {})
    data.setdefault("cases", [])
    data.setdefault("evidence", {})

    # Ensure basic types
    if not isinstance(data["gates_shadow"], dict):
        data["gates_shadow"] = {}
    if not isinstance(data["cases"], list):
        data["cases"] = []
    if not isinstance(data["evidence"], dict):
        data["evidence"] = {}

    return data


def _load_bundle(path: Optional[str]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Bundle format (recommended):
    {
      "inputs": {"u":..., "T":... or "lnT":..., "v_L":..., "lambda_eff":...},
      "params": {"eta":..., "chi":..., "ell_0":..., "M_infty":..., "b0_A_bits":..., "epsilon_budget":..., "rho_coding":..., "c_m_per_s":..., "G_m3_per_kg_s2":...}
    }
    """
    if not path:
        return {}, {}
    try:
        obj = _load_json(path)
    except Exception:
        return {}, {}
    if not isinstance(obj, dict):
        return {}, {}
    inputs = obj.get("inputs", {})
    params = obj.get("params", {})
    if not isinstance(inputs, dict):
        inputs = {}
    if not isinstance(params, dict):
        params = {}
    return inputs, params


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--in", dest="in_path", required=True, help="Input overlay JSON path (theory_overlay_v0.json).")
    ap.add_argument("--out", dest="out_path", required=True, help="Output overlay JSON path.")
    ap.add_argument("--bundle", dest="bundle_path", default=None, help="Optional JSON bundle providing inputs/params.")
    ap.add_argument(
        "--require-inputs",
        action="store_true",
        help="If set, partial inputs become FAIL (FAIL_CLOSED). If not set, missing inputs produce MISSING.",
    )
    args = ap.parse_args()

    # Load existing overlay (or create skeleton)
    existing = None
    try:
        existing = _load_json(args.in_path)
    except Exception:
        existing = None

    data = _ensure_skeleton(existing)

    # Pull inputs/params (bundle first, then env fallback)
    bundle_inputs, bundle_params = _load_bundle(args.bundle_path)

    u = _as_float(bundle_inputs.get("u")) if bundle_inputs else None
    T = _as_float(bundle_inputs.get("T")) if bundle_inputs else None
    lnT = _as_float(bundle_inputs.get("lnT")) if bundle_inputs else None
    L = _as_float(bundle_inputs.get("L")) if bundle_inputs else None
    v_L = _as_float(bundle_inputs.get("v_L")) if bundle_inputs else None
    lambda_eff = _as_float(bundle_inputs.get("lambda_eff")) if bundle_inputs else None

    if u is None:
        u = _get_env_float("THEORY_U")
    if T is None:
        T = _get_env_float("THEORY_T")
    if lnT is None:
        lnT = _get_env_float("THEORY_LNT")
    if L is None:
        L = _get_env_float("THEORY_L")
    if v_L is None:
        v_L = _get_env_float("THEORY_V_L")
    if lambda_eff is None:
        lambda_eff = _get_env_float("THEORY_LAMBDA_EFF")

    eta = _as_float(bundle_params.get("eta")) if bundle_params else None
    chi = _as_float(bundle_params.get("chi")) if bundle_params else None
    ell_0 = _as_float(bundle_params.get("ell_0")) if bundle_params else None
    M_infty = _as_float(bundle_params.get("M_infty")) if bundle_params else None
    b0_A_bits = _as_float(bundle_params.get("b0_A_bits")) if bundle_params else None
    epsilon_budget = _as_float(bundle_params.get("epsilon_budget")) if bundle_params else None
    rho_coding = _as_float(bundle_params.get("rho_coding")) if bundle_params else None

    c = _as_float(bundle_params.get("c_m_per_s")) if bundle_params else None
    G = _as_float(bundle_params.get("G_m3_per_kg_s2")) if bundle_params else None

    if eta is None:
        eta = _get_env_float("THEORY_ETA")
    if chi is None:
        chi = _get_env_float("THEORY_CHI")
    if ell_0 is None:
        ell_0 = _get_env_float("THEORY_ELL0")
    if M_infty is None:
        M_infty = _get_env_float("THEORY_MINFTY")
    if b0_A_bits is None:
        b0_A_bits = _get_env_float("THEORY_B0A_BITS")
    if epsilon_budget is None:
        epsilon_budget = _get_env_float("THEORY_EPS")
    if rho_coding is None:
        rho_coding = _get_env_float("THEORY_RHO")
    if c is None:
        c = _get_env_float("THEORY_C")
    if G is None:
        G = _get_env_float("THEORY_G")

    if c is None:
        c = C_DEFAULT
    if G is None:
        G = G_DEFAULT

    # Build evidence block (ensure structure exists)
    ev = data["evidence"]
    rh = ev.get("record_horizon_v0")
    if not isinstance(rh, dict):
        rh = {}
        ev["record_horizon_v0"] = rh

    rh.setdefault("thresholds", {"Btilde_green": 100, "Btilde_yellow": 10, "Btilde_red": 1, "sharp_Xi": 8, "sharp_F": 10})
    rh.setdefault("constants", {"c_m_per_s": c, "G_m3_per_kg_s2": G})
    rh.setdefault("computed", {})
    if not isinstance(rh["computed"], dict):
        rh["computed"] = {}

    computed = rh["computed"]

    # Determine if we have any inputs at all
    required_inputs = {"u": u, "T_or_lnT": (T if T is not None else lnT), "v_L": v_L, "lambda_eff": lambda_eff}
    required_params = {
        "eta": eta,
        "chi": chi,
        "ell_0": ell_0,
        "M_infty": M_infty,
        "b0_A_bits": b0_A_bits,
        "epsilon_budget": epsilon_budget,
        "rho_coding": rho_coding,
    }

    have_any = any(v is not None for v in list(required_inputs.values()) + list(required_params.values()))
    missing = []
    for k, v in required_inputs.items():
        if v is None:
            missing.append(f"input:{k}")
    for k, v in required_params.items():
        if v is None:
            missing.append(f"param:{k}")

    gates = data["gates_shadow"]
    if not isinstance(gates, dict):
        gates = {}
        data["gates_shadow"] = gates

    gate = gates.get(GATE_NAME)
    if not isinstance(gate, dict):
        gate = {}
        gates[GATE_NAME] = gate

    # Defaults
    gate["zone"] = "UNKNOWN"
    gate["mode"] = "UNKNOWN"

    # If nothing provided, keep it as MISSING scaffold (CI-neutral)
    if not have_any:
        gate["status"] = "MISSING"
        gate["reason"] = "No inputs/params provided for record-horizon computation."
        rh["status"] = "MISSING"
        # keep computed fields as-is
        _write_json(args.out_path, data)
        return 0

    # Partial or missing required fields
    if missing:
        if args.require_inputs:
            gate["status"] = "FAIL"
            gate["reason"] = "FAIL_CLOSED: missing required fields: " + ", ".join(missing)
            rh["status"] = "FAIL_CLOSED"
            gate["zone"] = "POST"
            gate["mode"] = "UNKNOWN"
        else:
            gate["status"] = "MISSING"
            gate["reason"] = "Partial inputs/params present but incomplete: " + ", ".join(missing)
            rh["status"] = "MISSING"
        _write_json(args.out_path, data)
        return 0

    # Resolve T from lnT if needed
    if T is None and lnT is not None:
        try:
            T = math.exp(float(lnT))
        except Exception:
            T = None

    # Validate numeric constraints (fail-closed)
    invalid = []
    if T is None or not math.isfinite(T) or T <= 0:
        invalid.append("input:T")
    if v_L is None or not math.isfinite(v_L) or v_L <= 0:
        invalid.append("input:v_L")
    if lambda_eff is None or not math.isfinite(lambda_eff) or lambda_eff <= 0:
        invalid.append("input:lambda_eff")
    if u is None or not math.isfinite(u):
        invalid.append("input:u")
    if eta is None or not math.isfinite(eta) or eta <= 0:
        invalid.append("param:eta")
    if chi is None or not math.isfinite(chi) or chi < 0:
        invalid.append("param:chi")
    if ell_0 is None or not math.isfinite(ell_0) or ell_0 <= 0:
        invalid.append("param:ell_0")
    if M_infty is None or not math.isfinite(M_infty) or M_infty <= 0:
        invalid.append("param:M_infty")
    if b0_A_bits is None or not math.isfinite(b0_A_bits) or b0_A_bits <= 0:
        invalid.append("param:b0_A_bits")
    if epsilon_budget is None or not math.isfinite(epsilon_budget) or not (0 <= epsilon_budget < 1):
        invalid.append("param:epsilon_budget")
    if rho_coding is None or not math.isfinite(rho_coding) or not (0 <= rho_coding < 1):
        invalid.append("param:rho_coding")

    if invalid:
        gate["status"] = "FAIL"
        gate["reason"] = "FAIL_CLOSED: invalid values: " + ", ".join(invalid)
        rh["status"] = "FAIL_CLOSED"
        gate["zone"] = "POST"
        gate["mode"] = "UNKNOWN"
        _write_json(args.out_path, data)
        return 0

    # Compute metrics
    try:
        # Parse thresholds (fail-closed if malformed)
        thr = rh.get("thresholds", {})
        if not isinstance(thr, dict):
            raise ValueError("invalid thresholds: not an object")

        b_green = _as_float(thr.get("Btilde_green"))
        b_yellow = _as_float(thr.get("Btilde_yellow"))
        b_red = _as_float(thr.get("Btilde_red"))
        sharp_Xi_thr = _as_float(thr.get("sharp_Xi"))
        sharp_F_thr = _as_float(thr.get("sharp_F"))

        if b_green is None or b_yellow is None or b_red is None:
            raise ValueError("invalid thresholds: Btilde_green/Btilde_yellow/Btilde_red must be numeric")
        if sharp_F_thr is None:
            raise ValueError("invalid threshold: sharp_F")
        if sharp_Xi_thr is None:
            raise ValueError("invalid threshold: sharp_Xi")

        # Basic sanity: green >= yellow >= red > 0
        if not (b_green >= b_yellow >= b_red > 0):
            raise ValueError("invalid thresholds ordering: require green>=yellow>=red>0")

        lnT_val = math.log(T)
        alpha0 = float(eta) * (float(ell_0) / (float(c) ** 2)) * float(T)
        feedback_F = 1.0 + float(chi) * (float(u) + 1.0)

        denom = alpha0 * float(v_L) * (1.0 + float(chi) * float(u))
        if not (math.isfinite(denom) and denom > 0):
            raise ValueError("non-positive denom")

        B_rem_bits = (float(M_infty) * float(lambda_eff) * math.exp(-float(u))) / denom
        if not (math.isfinite(B_rem_bits) and B_rem_bits > 0):
            raise ValueError("non-positive B_rem_bits")

        B_eff_payload_bits = (1.0 - float(epsilon_budget)) * (1.0 - float(rho_coding)) * B_rem_bits
        if not (math.isfinite(B_eff_payload_bits) and B_eff_payload_bits > 0):
            raise ValueError("non-positive B_eff_payload_bits")

        Btilde = B_eff_payload_bits / float(b0_A_bits)
        if not (math.isfinite(Btilde) and Btilde > 0):
            raise ValueError("non-positive Btilde")

        x_ln = math.log(Btilde)

        # Optional history-based slope/Xi projection inputs
        g_T = None
        Xi = None
        m_data = None
        m_model = None
        m = None
        delta_lnT_to_green = None
        delta_lnT_to_yellow = None
        delta_lnT_to_red = None

        hist = rh.get("history")
        prev_lnT = None
        prev_x = None
        prev_L = None
        if isinstance(hist, list):
            for item in reversed(hist):
                if not isinstance(item, dict):
                    continue
                cand_lnT = _as_float(item.get("lnT"))
                cand_x = _as_float(item.get("x_ln_Btilde"))
                if cand_x is None:
                    cand_x = _as_float(item.get("x"))
                if cand_lnT is None or cand_x is None:
                    continue
                prev_lnT = cand_lnT
                prev_x = cand_x
                prev_L = _as_float(item.get("L"))
                break

        if prev_lnT is not None and prev_x is not None:
            dt = lnT_val - prev_lnT
            dx = x_ln - prev_x
            if dt > 0:
                m_data = abs(dx / dt)

            if L is not None and prev_L is not None:
                dL = L - prev_L
                if dL != 0:
                    g_T_candidate = dt / dL
                    if math.isfinite(g_T_candidate) and g_T_candidate != 0:
                        g_T = g_T_candidate
                        g_C = alpha0 * (1.0 + float(chi) * (float(u) + 1.0))
                        Xi_candidate = g_C / g_T
                        if math.isfinite(Xi_candidate):
                            Xi = Xi_candidate

            if Xi is not None:
                m_model_candidate = 1.0 + Xi
                if math.isfinite(m_model_candidate):
                    m_model = m_model_candidate

            m = 1.0
            if m_data is not None and math.isfinite(m_data):
                m = max(m, m_data)
            if m_model is not None and math.isfinite(m_model):
                m = max(m, m_model)

            delta_lnT_to_green = max(0.0, (x_ln - math.log(b_green)) / m)
            delta_lnT_to_yellow = max(0.0, (x_ln - math.log(b_yellow)) / m)
            delta_lnT_to_red = max(0.0, (x_ln - math.log(b_red)) / m)

        # Zone classification
        zone = "POST"
        if Btilde >= b_green:
            zone = "GREEN"
        elif Btilde >= b_yellow:
            zone = "YELLOW"
        elif Btilde >= HORIZON_B_TILDE:
            zone = "RED"
        else:
            zone = "POST"

        # Mode: Xi+F if Xi exists, otherwise fallback to F-only
        if Xi is not None:
            mode = "SHARP" if (Xi >= sharp_Xi_thr or feedback_F >= sharp_F_thr) else "SLOW"
        else:
            mode = "SHARP" if feedback_F >= sharp_F_thr else "SLOW"

        def _close(a: float, b: float, tol: float = 1e-9) -> bool:
            return math.isclose(a, b, rel_tol=tol, abs_tol=tol)

        # Populate computed
        computed["B_rem_bits"] = B_rem_bits
        computed["B_eff_payload_bits"] = B_eff_payload_bits
        computed["Btilde_core_units"] = Btilde
        computed["horizon_Btilde"] = HORIZON_B_TILDE
        computed["x_ln_Btilde"] = x_ln
        computed["zone"] = zone
        computed["mode"] = mode
        computed["feedback_F"] = feedback_F
        computed["g_T"] = g_T
        computed["Xi"] = Xi
        computed["m_slope"] = m
        computed["delta_lnT_to_green"] = delta_lnT_to_green
        computed["delta_lnT_to_yellow"] = delta_lnT_to_yellow
        computed["delta_lnT_to_red"] = delta_lnT_to_red

        computed["delta_lnT_to_100"] = delta_lnT_to_green if delta_lnT_to_green is not None and _close(b_green, 100.0) else None
        computed["delta_lnT_to_10"] = delta_lnT_to_yellow if delta_lnT_to_yellow is not None and _close(b_yellow, 10.0) else None
        computed["delta_lnT_to_1"] = delta_lnT_to_red if delta_lnT_to_red is not None and _close(b_red, 1.0) else None

        rh["status"] = "OK"

        gate["zone"] = zone
        gate["mode"] = mode

        # Gate status policy (v0):
        # - FAIL if Btilde is below hard record horizon
        # - PASS otherwise (GREEN/YELLOW/RED are diagnostic zones)
        if Btilde < HORIZON_B_TILDE:
            gate["status"] = "FAIL"
            gate["reason"] = f"RECORD_HORIZON: Btilde_core_units < {HORIZON_B_TILDE:g} (zone=POST)"
        else:
            gate["status"] = "PASS"
            if zone == "RED":
                # Optional early warning if configured Btilde_red is above 1 and we are below it
                if b_red is not None and b_red > HORIZON_B_TILDE and Btilde < b_red:
                    gate["reason"] = f"WARN: below configured Btilde_red={b_red:g} (near horizon)"
                else:
                    gate["reason"] = "WARN: zone=RED (near record horizon)"
            else:
                gate["reason"] = ""

        # Update digest (inputs+params used)
        digest_obj = {
            "inputs": {"u": u, "T": T, "lnT": lnT_val, "v_L": v_L, "lambda_eff": lambda_eff},
            "params": {
                "eta": eta,
                "chi": chi,
                "ell_0": ell_0,
                "M_infty": M_infty,
                "b0_A_bits": b0_A_bits,
                "epsilon_budget": epsilon_budget,
                "rho_coding": rho_coding,
                "c_m_per_s": c,
                "G_m3_per_kg_s2": G,
            },
        }
        data["inputs_digest"] = _sha256_hex(digest_obj)

    except Exception as e:
        gate["status"] = "FAIL"
        gate["reason"] = f"FAIL_CLOSED: computation error: {type(e).__name__}: {e}"
        rh["status"] = "FAIL_CLOSED"
        gate["zone"] = "POST"
        gate["mode"] = "UNKNOWN"

    _write_json(args.out_path, data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
