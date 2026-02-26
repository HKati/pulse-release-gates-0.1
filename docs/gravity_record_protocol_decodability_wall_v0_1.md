# Gravity Record Protocol — Decodability Wall (v0.1)

## Status (status_v1)
- **Doc ID:** `gravity_record_protocol_decodability_wall_v0_1`
- **Status:** Draft (spec-level: concept → implementation-backed)
- **Last updated:** 2026-02-26
- **Related docs:**
  - `gravity_record_protocol_inputs_v0_1.md`
  - `gravity_record_protocol_appendix_v0_1.md`
  - `CALIBRATION.md`
  - `AMBIGUITY_REGISTER_v0.md`
  - `GLOSSARY_v0.md`

---

## Why this doc exists

This repository uses an applied notion of a *threshold (“wall”)*: a point where a record stream becomes **non-decodable** under a capacity constraint.

This document exists to make the problem statement explicit and non-hand-wavy:

- what “decodable” means operationally,
- what quantity is being compared to what,
- what assumptions are required for a single critical radius to exist,
- how the threshold is computed and calibrated.

> Non-claim: this does **not** assert a physical “horizon” statement.  
> It defines an **operational** threshold in an information/decodability model.

---

## Terms and notation (minimal)

- `r` : radius (monotone coordinate toward a boundary region)
- `Σ` : record alphabet, `|Σ|` its size
- `h_req` : required decodable information rate (bits/tick or nats/tick)
- `κ(r)` : usable fraction of symbol capacity at `r` (typically in `[0,1]`)
- `C(r)` : effective channel capacity at `r` (same units as `h_req`)
- `r_c` : **critical radius** where decodability fails (“the wall”)

**Units:** pick one and be explicit.

- If using bits: `log2`
- If using nats: `ln`

Conversion: `1 bit = ln(2) nats`

---

## Core definition: capacity and requirement

We model a symbol channel whose *per-tick* capacity at radius `r` is:

\[
C(r) = \kappa(r)\,\log |\Sigma|
\]

where:

- `log` is `log2` (bits) or `ln` (nats),
- `κ(r)=1` means full symbol capacity is available,
- `κ(r)=0` means no usable capacity.

We define a required rate `h_req` (protocol + reconstruction target dependent).

Operationally: if the stream requires at least `h_req` per tick to reconstruct to the target fidelity, then:

- **Decodable at r:** `C(r) ≥ h_req`
- **Not decodable at r:** `C(r) < h_req`

---

### The wall criterion

The **Decodability Wall** is defined by:

\[
C(r_c)=h_{\text{req}}
\]

Equivalently:

\[
\kappa(r_c)=\frac{h_{\text{req}}}{\log|\Sigma|}
\]

---

### Existence and uniqueness (when it’s a single “wall”)

A unique wall `r_c` exists on a domain `[r_min, r_max]` if:

1. `κ(r)` is monotone (typically decreasing) on the domain,
2. `0 ≤ h_req ≤ log|Σ|`,
3. `C(r_min) ≥ h_req` and `C(r_max) ≤ h_req` (a sign change / bracket exists).

If monotonicity is not guaranteed, there can be **multiple crossings**; in that case the “wall” must be specified as:

- the outermost crossing,
- the first crossing from a chosen direction,
- or a set of crossings.

---

## Modeling κ(r): baseline + driven degradation (concept spec)

A minimal degradation law along a path-length-like coordinate `L`:

\[
\frac{d\kappa}{dL}=-(\alpha + b\,u)\,\kappa
\]

- `α` : baseline attenuation rate
- `b u` : driven attenuation (environment/geometry forcing term)
- `u=u(r)` and `L=L(r)` come from the chosen scenario

Solution via optical depth:

\[
\kappa(L) = \kappa_0 \exp\left(-\int_0^L (\alpha + b\,u(L'))\,dL'\right)
\]

This separates:

- *what must be true operationally* (threshold definition),
- from *how κ(r) is generated* (model choice).

---

## Computing r_c (robust method)

Compute the root of:

\[
F(r)=C(r)-h_{\text{req}}
\]

Preferred numerics:

- bracket the crossing on `[r_min,r_max]`,
- use a bracketed solver (bisection / Brent),
- emit diagnostics if bracketing fails.

**Diagnostics to record**

- chosen log base (bits vs nats)
- `|Σ|`, `h_req`
- κ-range observed (`min κ`, `max κ`)
- monotonicity check result
- bracket endpoints and `F(r_min), F(r_max)`
- root tolerance

---

## Calibration notes (ties to CALIBRATION.md)

The wall is only meaningful if `h_req` and `κ(r)` are calibrated to the protocol.

---

### Calibrating h_req

`h_req` is not “the entropy of the universe”; it’s a protocol requirement.

Examples:

- “must reconstruct token stream with ≤ ε symbol error”
- “must reconstruct a structured record (fields) with bounded distortion”
- “must reconstruct a proof/trace satisfying an integrity rule”

Practical guidance:

- define *what reconstruction means* (success predicate),
- define the minimal rate (with coding overhead),
- then log it as the “required rate” for this gate/detector.

---

### Calibrating κ(r)

κ encapsulates the net effect of:

- noise,
- erasures,
- redshift/slowdown proxies,
- sampling loss,
- etc.

If you change κ-modeling, you are changing the operational wall.

---

## Suggested artifact schema (informative)

If this wall is produced by a detector/gate, record a minimal payload:

```json
{
  "schema": "decodability_wall_v0_1",
  "units": { "info": "bits_per_tick", "log": "log2" },
  "inputs": {
    "alphabet_size": 0,
    "h_req": 0.0,
    "domain": { "r_min": 0.0, "r_max": 0.0 }
  },
  "model": {
    "kappa_model": "baseline_plus_driven",
    "params": { "kappa0": 1.0, "alpha": 0.0, "b": 0.0 },
    "u_model": "TODO",
    "L_of_r": "TODO"
  },
  "outputs": {
    "rc": null,
    "bracket": { "r_lo": null, "r_hi": null },
    "diagnostics": {
      "kappa_min": null,
      "kappa_max": null,
      "monotone": null
    }
  }
}
```

---

## Ambiguity note

The word “wall” is overloaded (physical horizon, policy wall, safety wall, etc.).

In this repository:

**Decodability Wall** means only:

\[
C(r)=h_{\text{req}}
\]

under the chosen κ-model.

See: `AMBIGUITY_REGISTER_v0.md`.

---

## References (minimal backbone)

These are “why the comparison is non-hand-wavy” references:

- Claude E. Shannon (1948): *A Mathematical Theory of Communication*.
- Thomas M. Cover & Joy A. Thomas: *Elements of Information Theory*.
- Polyanskiy, Poor, Verdú (2010): finite-blocklength coding limits  
  (useful when your “tick” is short).

(If you need GR-specific motivation, keep it separate and explicitly marked as “motivating context”, not as the operational definition.)
