# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- CODEOWNERS to require Code Owners review on `main`.
- Pull request template with the PULSE governance checklist.
- (Optional) changelog check workflow (soft warning).
- Stability Map JSON generator for Pulse Topology v0:
  - new tool `PULSE_safe_pack_v0/tools/build_stability_map.py`
  - generates `stability_map.json` from existing PULSE artefacts (`status.json` and optional `status_epf.json`)
  - aggregates safety/quality gate outcomes, RDSI and EPF (`epf_L`) into a single instability score with transparent components
  - assigns a coarse stability type per run (`STABLE`, `METASTABLE`, `UNSTABLE`, `PARADOX`, `COLLAPSE`)
  - does not modify any existing fail-closed release-gate behaviour
- Core policy profile `PULSE_safe_pack_v0/profiles/pulse_policy_core.yaml`:
  - documents the minimal recommended deterministic gate set for first-time PULSE adopters
  - encodes a CI-neutral refusal-delta stability policy without changing the existing fail-closed behaviour
- Add a shadow-only `parameter_golf_v0` sidecar for OpenAI Parameter Golf submission evidence: schema, verifier, example artifact, docs, tests, and an upstream issue-comment draft.

### Changed
- README: add DOI badge above the PULSE badges; keep badges.
- README: add **Acknowledgments** section.

### Fixed
- `publish_report_pages.yml`: copy `status.json` to site root; improve concurrency safety.
- Makefile: `reproduce` is now fail-closed locally and no longer hides `run_all.py` failures.
- Makefile: add explicit `reproduce-soft` for permissive local/demo execution.
- Makefile: checksum generation now uses the repo-root `compute_checksums.py`.
- Makefile: checksum manifest is emitted atomically to avoid self-hash inconsistency when hashing the current directory.
- Harden `tools/verify_parameter_golf_submission_v0.py` to fail cleanly when `jsonschema` is missing or the supplied schema is malformed.
- Account for counted tokenizer bytes in `tools/verify_parameter_golf_submission_v0.py` total-size checks.
- Honor `--json` for early evidence/schema load errors so machine-readable verifier output stays structured in failure cases.
- Execute `tests/test_parameter_golf_submission_evidence_v0.py` through the CI pytest manifest (`ci/render-quality-ledger-tests.list`).

### Docs
- `CITATION.cff`: add ORCID for Katalin Horvat; add software reference to ChatGPT (GPT-5 Pro).
- Add `docs/GOVERNANCE_PACK_v0.md`: overview of the optional Governance Pack (Stability Map, Decision Engine, EPF/Paradox Playbook, G-field, history tools).
- Add `docs/GLOSSARY_v0.md`: working glossary for core PULSE terms across the safe-pack, Core profile, and Governance Pack.

### Security
- (no changes)

## [1.1.1] - 2026-01-09

### Fixed
- Retrigger Zenodo ingestion after metadata fix.
- `.zenodo.json`: remove hand-maintained `version` and `publication_date`.
- CI: validate `.zenodo.json` via `json.tool`.

## [1.1.0] - 2025-11-10

### Changed
- Zenodo: add `hasPart` pointing to the Guard repository so Guard appears under the Pulse Zenodo record.
- Remove explicit `version` from `.zenodo.json`; Zenodo derives the version from the Git tag.

### Notes
- Metadata-only release; no code or CI changes; backward compatible.

## [1.0.3] - 2025-10-16

### Added
- External detectors (opt-in): merge JSON/JSONL summaries from safety tools into the gate context and Quality Ledger.
- Refusal-delta: stability signal for refusal policies.
- JUnit and SARIF export artifacts for CI dashboards and code scanning.
- First-run stays simple: defaults unchanged; optional pieces can be enabled later.

### Notes
- Deterministic, fail-closed release gates across Safety (I2–I7), Utility (Q1–Q4), and SLO budgets; optional EPF gate; Quality Ledger plus checksums for audit.
- Backward compatible; all new pieces are opt-in.

## [1.0.2] - 2025-09-27

### Added
- Deterministic, fail-closed gates across Safety (I₂–I₇) and Product Utility (Q₁–Q₄).
- CI-enforced workflow (`.github/workflows/pulse_ci.yml`).
- Human-readable Quality Ledger (`report_card.html`) and `status.json`.
- RDSI (Release Decision Stability Index) with confidence intervals.
- Badges (PASS/FAIL, RDSI, Q-Ledger) under `/badges`.
- Profiles and thresholds under `/profiles`.
- Methods and external-detectors docs under `/docs`.
- Optional GitHub Pages publisher guarded by `PUBLISH_PAGES`.

### Notes
- Release DOI: `10.5281/zenodo.17373002`.
- Concept DOI: `10.5281/zenodo.17214908`.

## [1.0.1] - 2025-09-27

### Added
- GitHub Pages publisher workflow (guarded by `PUBLISH_PAGES`).
- `status.json` exposed at site root on Pages.

### Changed
- README: DOI badge + Acknowledgments section.

### Fixed
- `publish_report_pages.yml`: copy `status.json`, concurrency safety.

### Docs
- `CITATION.cff`: add ORCID and ChatGPT (GPT-5 Pro) software reference.

## [1.0.0] - 2025-09-23

### Added
- Initial PULSE release gates pack (I₂–I₇, Q₁–Q₄).
- CI wiring (`pulse_ci.yml`), badges, Quality Ledger and RDSI reporting.

[Unreleased]: https://github.com/HKati/pulse-release-gates-0.1/compare/V1.1.1...HEAD
[1.1.1]: https://github.com/HKati/pulse-release-gates-0.1/releases/tag/V1.1.1
[1.1.0]: https://github.com/HKati/pulse-release-gates-0.1/releases/tag/v1.1.0
[1.0.3]: https://github.com/HKati/pulse-release-gates-0.1/releases/tag/v1.0.3
[1.0.2]: https://github.com/HKati/pulse-release-gates-0.1/releases/tag/v.1.0.2
[1.0.1]: https://github.com/HKati/pulse-release-gates-0.1/releases/tag/
[1.0.0]: https://github.com/HKati/pulse-release-gates-0.1/releases/tag/v1.0.0
