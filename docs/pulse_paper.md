# PULSE preprint: Deterministic Release Gates for Safe & Useful AI

# PULSE preprint: Deterministic Release Gates for Safe & Useful AI

This document collects the basic metadata and pointers for the PULSE preprint.

> Katalin Horvat, *PULSE: Deterministic Release Gates for Safe & Useful AI*, 2025.  
> Preprint, Zenodo. DOI: https://doi.org/10.5281/zenodo.17833583

---

## Citation

If you cite the preprint, you can use for example:

> Horvat, K. (2025). *PULSE: Deterministic Release Gates for Safe & Useful AI*. Preprint. Zenodo. https://doi.org/10.5281/zenodo.17833583

For BibTeX:

    @misc{horvat_pulse_2025,
      author       = {Horvat, Katalin},
      title        = {PULSE: Deterministic Release Gates for Safe \& Useful AI},
      year         = {2025},
      howpublished = {Preprint},
      publisher    = {Zenodo},
      doi          = {10.5281/zenodo.17833583},
      url          = {https://doi.org/10.5281/zenodo.17833583}
    }

---

## DOIs and resources

- **Preprint (this document)**  
  - Zenodo DOI: `10.5281/zenodo.17833583`  
  - URL: <https://doi.org/10.5281/zenodo.17833583>
- **Software safe-pack (this repository, v1.0.2)**  
  - Software DOI: `10.5281/zenodo.17373002`
  - Concept DOI (all software versions): `10.5281/zenodo.17214908`
- **Project page / Quality Ledger**  
  - Live Quality Ledger: <https://hkati.github.io/pulse-release-gates-0.1/>
- **Code**  
  - GitHub repository: <https://github.com/HKati/pulse-release-gates-0.1>

The preprint and this repository are meant to be used together: the paper explains the
mathematical and governance background; the code provides the reference implementation.

---

## What the preprint covers (very brief)

The preprint provides a mathematical specification for PULSE as a deterministic, fail-closed
release-governance layer for LLM applications. Policies are encoded as versioned, hashed gate
maps that must be satisfied before shipping, across:

- **Safety / consistency invariants (I2–I7):** harm monotonicity, context commutativity,
  sanitization effectiveness, idempotence, path-independence and PII-leak monotonicity,
  each defined via benign transforms and acceptance tests over archived traces.
- **Quality gates (Q1–Q4):** groundedness, consistency, equalized-odds parity (EO) and SLO
  budgets (p95 latency and cost), all enforced via conservative Wilson score intervals and
  Newcombe deltas rather than raw point-estimates.
- **Release-Decision Stability Index (RDSI):** a binomial stability metric that re-runs the
  evaluation under small, structured perturbations (prompt shuffles, retrieval noise,
  cost/latency jitter, benign shims) and measures how often the PASS/FAIL decision agrees
  with the reference run, with Wilson confidence intervals and sample-complexity bounds.
- **EPF gate (Vacuum–energy Penalty Functional):** a domain-specific penalty functional
  defined in detector space over archived logs, inspired by the cosmological vacuum-energy
  problem but used purely as an operational safety/instability gate with affine
  reparameterization invariance.
- **Paradox field and `[(0 1)P]` notation:** an original paradox symbol and field over gates
  and overlays, used to mark high-tension release states where safety, utility, fairness,
  SLOs and EPF budgets compete, rather than introducing a third numerical outcome.

The paper also discusses determinism (fixed seeds and detectors), fail-closed behaviour for
missing signals, scaling characteristics (O(N) evaluation with Harrell–Davis quantiles),
and threats to validity (log representativeness, detector drift, small-n parity).

---

## How this repo maps to the preprint

In this repository:

- **Core gate logic (I2–I7, Q1–Q4, SLO budgets)**  
  is implemented in the PULSE safe-pack profiles, schemas and tools, and emitted to
  `status.json` plus the human-readable Quality Ledger.
- **RDSI**  
  is computed by RDSI tooling (scripts/workflows) on top of archived logs, with parameters
  and Wilson intervals recorded in the Quality Ledger and dashboards.
- **EPF gate**  
  is available as an optional, domain-specific gate in policies; the detector-space model
  and its cosmology-inspired origin are summarised in the preprint, with a dedicated
  extractor/derivations preprint in preparation.
- **Paradox field `[(0 1)P]`**  
  is realised in stability maps and overlays as a tension marker over gates and overlays,
  highlighting where binary decisions are under stress rather than replacing them.

For implementation details, see the rest of the `docs/` directory and the
`PULSE_safe_pack_v0/` profile and schema files.


