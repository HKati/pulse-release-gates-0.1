# Fellowship Submission Record — 2026-05-02

PULSE was submitted to the OpenAI Safety Fellowship as an existing artifact-first release-authority system for AI applications.

## Submitted system

PULSE structures recorded safety, quality, detector, stability, CI, and review evidence into deterministic, fail-closed release decisions under declared policy.

## Public artifact trail

- GitHub repository
- Live Quality Ledger
- status.json
- Software DOI
- Preprint DOI
- release_grade_reference_run_v0.md
- external_detector_summaries.md
- pulse_gate_policy_v0.yml
- STATUS_CONTRACT.md

## Active build track

The active PULSE-REF track is converting the existing PULSE artifact trail and core release-decision mechanics into an externally verifiable release-grade reference path.

## Review-period target

The review-period target includes:

- non-stubbed release-grade reference runs
- materialized detector evidence
- provenance and attestation
- external evidence schema and signer requirements
- atomic publication snapshots
- removal of implicit PASS fallbacks in release-grade paths
- benchmark fixtures
- external verification
- operator documentation for reconstructing release decisions from archived artifacts

## Fellowship-stage validation

The fellowship-stage work would focus on partner-scale validation of the release-grade reference path:

- repeated evidence-to-decision runs
- detector-summary pipelines
- robustness checks
- provenance / attestation tests
- external review
- compute-scale reproducibility experiments

## Authority boundary

The normative release decision is produced by the declared-policy gate-enforcement path and recorded through the CI outcome.

Release-authority manifests, audit bundles, ledgers, dashboards, summaries, and publication surfaces preserve, explain, and reconstruct that decision. They do not authorize, block, override, or create a second release-decision path.
