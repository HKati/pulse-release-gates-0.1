# Security Policy

## Supported versions
Main branch (latest) with PULSE CI enabled.

## Reporting a vulnerability
Please email **security@eplabsai.com**
We aim to triage within 72 hours. Include a minimal repro and logs.
Do not open public issues for sensitive reports.

## PULSE threat model

This repository is a CI/local tooling system for PULSE, an artifact-bound release-authority system for AI applications and AI-enabled systems.

PULSE's primary security boundary is the artifact-to-release-decision path: recorded evidence, `status.json`, declared policy, materialized required gates, `check_gates.py`, CI enforcement, artifact integrity, and external verifier trust boundaries.

Classic web-application findings such as SQL injection, CSRF, session fixation, or RBAC bypass are usually not the primary risk class for this repository because the main exposed surfaces are CLI tooling, CI workflows, static Pages outputs, and artifact verification paths. The relevant equivalents are shell/workflow injection, path traversal, symlink escape, static-site XSS in rendered artifacts, supply-chain compromise, and semantic bypass of release-state or verifier checks.

Quality ledgers, dashboards, SARIF/JUnit outputs, manifests, audit bundles, Pages outputs, and RA1 reports are audit/reconstruction surfaces unless they are explicitly bound through declared policy, materialized gates, and strict CI enforcement into the release-authority path.

### Criticality calibration

- **Critical:** vulnerabilities that can directly convert a failing, missing, stale, or forged release-state artifact into a CI allow outcome under declared policy, or that can bypass strict fail-closed gate enforcement on the primary release-authority path.
- **High:** local or CLI verification tools that execute attacker-controlled code, select verifier code from reviewed roots, accept path traversal or symlink escape in verification inputs, read files outside the reviewed root, or allow forged verified packets.
- **High:** CI/workflow injection, supply-chain execution, artifact tampering, or verifier semantic bypass that can alter `status.json`, policy materialization, materialized required gates, `check_gates.py`, CI outcome, artifact integrity, release-state verification, packet verification status, or external verifier trust boundaries.
- **Medium:** issues that can mislead audit/reconstruction readers, dashboards, SARIF/JUnit consumers, Pages viewers, or operator review without directly changing the authoritative allow/block release outcome.
- **Low:** documentation or fixture-only inconsistencies; report formatting issues that do not alter `status.json`, policy materialization, `check_gates.py`, CI outcome, artifact integrity, or external verifier trust boundaries. Local CLI issues are Low only when they cannot affect artifact integrity, verifier trust boundaries, release-state verification, packet verification status, or CI allow/block outcomes.

### Reviewed-root and package-root boundaries

Binding and package verification tools must treat reviewed repository roots and package roots as untrusted input boundaries. File paths may be relative or absolute only if they resolve inside the applicable reviewed repository root or package root.
