# Appendix: Gravity as a Record Test (λ/s/κ protocols) — v0.1
**Status:** operational protocol note (probe, non-normative)  
**Goal:** define measurement/analysis procedures for λ(r), s(r), κ(r) and horizon-wall classification.

This appendix is intentionally protocol-first: it specifies *what to measure and how*,
without relying on “time flows” language.

## A. What counts as a “gravity effect” here?
Operationally, gravity changes:
1) **tick comparability** (λ),
2) **radial comparison scale** (s),
3) **record identifiability / throughput** (κ).

“Horizon” is a protocol failure boundary; different protocols fail differently.

## B. Minimal measurement package
Required:
- Two (or more) stations A, B, … at different r-labels (areal radius or a well-defined proxy).
- A stable carrier / oscillator at each station (for λ measurement).
- A bidirectional link (recommended) to control channel drift.
- An indexed pulse stream generator + a decoder (for κ measurement).

Optional:
- Accelerometer/gravimeter for **g(r)** (hover cost).
- A geometric/radar method for **s(r)**. If not available, mark s as MISSING.

## C. Protocol 1 — λ(r): tick-scale / frequency ratio
Procedure (bidirectional recommended):
1) Exchange carrier signals A→B and B→A.
2) Estimate the frequency ratio in both directions.
3) Use the two-way protocol to reduce/diagnose link drift.

Fail-closed rule:
- If the ratio is not stable/estimable under the defined protocol, λ is MISSING (not inferred).

## D. Protocol 2 — κ(r): record throughput (identifiable pulses)
Definition (operational):
- κ = (identifiable_index_count) / (sent_index_count)

Procedure:
1) Send N indexed pulses (e.g. 1..N) from A to B.
2) At B, decode and count:
   - received_count
   - identifiable_count (index recovered correctly)
   - dropout_rate = 1 − identifiable_count/N
3) Log jitter statistics (arrival dispersion) and burst-drop patterns if available.
4) Optionally repeat with/without FEC to probe κ sensitivity.

Fail-closed rule:
- If “identifiable” is not defined (no index/decoder contract), κ is MISSING.

## E. Protocol 3 — g(r): hover acceleration (optional)
If available, measure g(r) at each station with:
- a fixed orientation convention,
- a defined sampling window,
- basic summary stats (mean/std/outlier rate).

## F. Protocol 4 — s(r): radial rod scale (optional)
Definition:
- dℓ = s(r) dr, with r as an areal radius label (C=2πr) or a clearly documented proxy.

Two options:
- Geometric: measure r and a radial length increment dℓ to estimate s.
- Proxy: if r is only a station label and no geometry is defined, s is MISSING.

Fail-closed rule:
- Never emit numeric s unless the protocol is fully specified.

## G. Derived check — consistency of g and λ (optional)
If λ(r), s(r), and g(r) exist on a shared r-grid, test the protocol-level relationship:

g(r) ?= (c² / s(r)) · d/dr [ ln λ(r) ]

Discrete approximation on a grid:
- d/dr ln λ(r_i) ≈ (ln λ_{i+1} − ln λ_{i−1}) / (r_{i+1} − r_{i−1})
- g_pred(r_i) = (c² / s(r_i)) · d/dr ln λ(r_i)

Fail-closed rule:
- If any component is missing, the derived check is MISSING (not “PASS by default”).

## H. Wall classification (horizon taxonomy)
Use measured profiles to classify failure boundaries:

- Frequency wall: λ becomes extremely small and trends toward 0.
- Delay wall: protocol-defined delay cost grows without bound (requires s and λ).
- Record wall: κ trends toward 0 and identifiability collapses (dropout/jitter spikes).

Distinguishing signature of interest:
- λ is not extreme but κ collapses → record wall dominates before frequency wall.

## I. Repo integration note (future)
This appendix is a protocol spec only. A future baseline can:
- introduce a contract-shaped λ/s/κ case structure,
- add fixtures for wall separation signatures,
- and surface derived checks as CI-neutral overlay evidence.
