# Time as Consequence (v0.1)
**Status:** probe / workshop spec (non-normative)  
**Scope:** operational language + falsification program (no release-gate semantics)

This document proposes an operational reframing: **time is not a primitive coordinate**.  
Instead, “time” is the reconstructed imprint of **state transitions** that become **stable, cross-comparable records**.

## Status / implementation map (baseline guard)
**Implemented in this repo today**
- Theory Overlay v0 (shadow) engine: schema + fail-closed contract checks + CI wiring + markdown renderer.
- A record-horizon proxy signal (shadow gate) surfaced via the overlay artifact and CI Job Summary.

**Not implemented yet**
- A first-class λ/s/κ data model (profiles, stations, uncertainty fields) in the overlay inputs/outputs.
- Horizon taxonomy gates (frequency wall / delay wall / record wall) derived from λ/s/κ.
- Derived gravity consistency check (g vs d/dr ln λ) as a computed evidence block.
- Any “p-closure family” or fitted closure parameters as code (probe-only ideas for later).

Nothing in this document changes the normative PULSE release gates. It is a **spec/probe** only.

## Operational primitives (minimal)
- **Pulse:** a discrete, indexable signal unit (tick, frame, packet).
- **Record:** a pulse that is *identifiable* at the receiver (decodable + index recoverable).
- **Clock:** a system producing repeatable, countable state transitions; it does not “measure time” as a substance.

**Operational time (in this framework):**
- ordering reconstructed from records, plus
- constraints/rates of record creation and record comparison.

## Three core observables (future-facing)
To avoid “time” as a primitive, we prefer protocol-derived observables:

- **λ(r)** — tick-scale / frequency ratio from signal exchange (dimensionless), with λ(∞)=1 by convention.
- **s(r)** — radial rod scale, defined by dℓ = s(r) dr where r is an areal radius label (C = 2πr).
- **κ(r)** — record throughput / identifiability ratio: 0 ≤ κ ≤ 1.

These are **observables** (or protocol outputs), not metaphysical commitments.

## Horizon taxonomy (operational)
A single “horizon” is not one thing. Different protocols fail in different ways:

- **Frequency wall:** λ → 0
- **Delay wall:** ∫ (s/λ) dr diverges (protocol-defined delay cost becomes unbounded)
- **Record wall:** κ → 0 (signals may arrive energetically, but no stable identifiable record remains)

The key claim is not which wall is “real”, but that **they can separate** and produce distinct testable signatures.

## Relativity without “time flows”
Instead of “time dilates”, we say:
- **recordable tick ratios differ** (λ),
- and **record comparison costs differ** (s/λ and protocol delays).

No global time axis is required to state or test these relationships.

## Entropy and arrow of time (record-centric)
Rather than “entropy increases in time”, we track:
- degradation of reconstructible correlations,
- loss of stable record structure,
- and constraints on record comparison.

The “arrow” is the macroscopic imprint of what becomes reliably recordable and what does not.

## Falsification program (what would count as new)
This framework is only useful if it produces concrete signatures, for example:
- **wall separation:** λ is not extreme but κ collapses (“record wall before frequency wall”),
- **last stable index:** identifiable pulse indices stop being recoverable beyond a regime boundary,
- dropout/jitter profiles that cannot be reduced to a single “redshift only” narrative.

To prevent “rubber models”, any κ/λ/s claim must be tied to:
- explicit protocols,
- contract-shaped outputs,
- and regression fixtures.

## Where to go next
- Measurement protocols and practical wall detection:  
  `docs/gravity_record_protocol_appendix_v0_1.md`
- Theory Overlay v0 (shadow) wiring and current record-horizon proxy:  
  `docs/theory_overlay_v0.md`
