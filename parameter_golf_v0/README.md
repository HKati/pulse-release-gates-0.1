# Parameter Golf v0 — shadow-only evidence companion

This directory is intentionally **not** part of the normative PULSE release-gating path.

Goal:
- add a tiny, machine-readable evidence surface for OpenAI Parameter Golf submissions,
- stay schema-first and audit-friendly,
- remain CI-neutral / shadow-only by default,
- avoid pulling the main PULSE safe-pack into a moving external challenge.

Why this exists:
- Parameter Golf submissions already carry strong claims around artifact size,
  evaluation mode, wallclock, and (for record attempts) statistical significance.
- The upstream challenge is moving quickly. A lightweight companion surface makes
  those claims easier to inspect without turning PULSE into the challenge itself.

v0 scope:
- one JSON contract: `parameter_golf_submission_evidence_v0`
- one verifier: `tools/verify_parameter_golf_submission_v0.py`
- one example artifact
- one docs note
- one draft issue comment for upstream discussion

Non-goals:
- no new PULSE required gates,
- no mutation of `status.json`,
- no attempt to redefine Parameter Golf rules,
- no counted-path integration into `train_gpt.py` in this repo.

Normative boundary:
- This is diagnostic / companion work only.
- Missing or malformed evidence may be reported as INVALID by the verifier,
  but this must not change PULSE release outcomes unless a future policy
  explicitly promotes it.
