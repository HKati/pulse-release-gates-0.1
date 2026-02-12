# One‑pager: Time as Consequence (v0.1)
**Status:** probe / workshop note (non-normative)

## Core idea
Time is treated as a **consequence** of what can be reliably recorded and compared, not as a primitive coordinate.

We do not “measure time”; we measure:
- **state transitions** (ticks / pulses),
- and whether those transitions become **stable, identifiable records**.

## Minimal objects
- **Pulse:** discrete indexable unit (tick, frame, packet).
- **Record:** pulse that is identifiable at the receiver (decode + index recovered).
- **Clock:** produces countable transitions; “time” is reconstructed from comparisons.

## Three observables (protocol-derived)
- **λ(r):** tick-scale / frequency ratio from signal exchange (λ(∞)=1)
- **s(r):** radial rod scale (dℓ = s(r) dr)
- **κ(r):** record throughput / identifiability ratio (0..1)

## Horizon is not one thing
Different failure modes define different “walls”:
- frequency wall (λ → 0)
- delay wall (∫(s/λ)dr diverges)
- record wall (κ → 0)

These walls can separate and should leave distinct signatures.

## Repo status (baseline guard)
Implemented today:
- Theory Overlay v0 (shadow): contract-checked artifact + CI-visible markdown summary + record-horizon proxy signal.

Not implemented yet:
- first-class λ/s/κ data model + horizon taxonomy gates + derived gravity checks.

## Next pointer
Appendix protocol: `docs/gravity_record_protocol_appendix_v0_1.md`
