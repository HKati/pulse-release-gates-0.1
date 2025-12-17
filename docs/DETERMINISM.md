# Determinism

PULSE is designed to be deterministic and audit-friendly when its runtime and inputs are pinned.
This document collects the minimal, practical constraints required for reproducible runs.

## What “deterministic” means here

Given the same:
- pack version (code + policies),
- runner image / Python version,
- inputs (logs, configs),
- and fixed seeds,

PULSE should produce identical gate outcomes and stable artefacts.

## Required controls

### 1) Pin the runtime
- Pin the Python version (and any lockfile / environment spec you use).
- Prefer CI runners or containers with explicit versioning.

### 2) Fix hash randomization
Python string hashing can be randomized unless you set `PYTHONHASHSEED`.

Requirement:
- Set the environment variable `PYTHONHASHSEED=0` **before starting** Python.

(How you set environment variables depends on your shell/runtime; keep it fixed across runs.)

### 3) Fix random seeds
If a component uses RNG, ensure the seed is fixed and recorded.
- Prefer explicit `--seed` style knobs where available.

### 4) Avoid non-deterministic accelerators
GPU kernels and some external tools can introduce variance.
- If GPU is used anywhere in the pipeline, pin drivers + runtime and expect possible small numeric drift.
- Shadow layers (e.g. EPF) must never change the deterministic PASS/FAIL gate semantics.

## Recommended practice

- Run the canonical workflow in CI for the reference baseline.
- When comparing runs, always compare artefacts produced by the same pinned environment.
- If you introduce optional detectors/tools, treat them as *inputs* and pin their versions the same way.
