# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- CODEOWNERS to require Code Owners review on `main`.
- Pull request template with the PULSE governance checklist.
- (Optional) Changelog check workflow (soft warning)
- Stability Map JSON generator for Pulse Topology v0:
  - new tool `PULSE_safe_pack_v0/tools/build_stability_map.py`
  - generates `stability_map.json` from existing PULSE artefacts (`status.json` and optional `status_epf.json`)
  - aggregates safety/quality gate outcomes, RDSI and EPF (`epf_L`) into a single instability score with transparent components
  - assigns a coarse stability type per run (`STABLE`, `METASTABLE`, `UNSTABLE`, `PARADOX`, `COLLAPSE`)
  - does not modify any existing fail-closed release-gate behaviour
- Core policy profile `PULSE_safe_pack_v0/profiles/pulse_policy_core.yaml`:
  - documents the minimal recommended deterministic gate set for first-time PULSE adopters
  - encodes a CI-neutral refusal-delta stability policy without changing the existing fail-closed behaviour

### Changed
- README: add DOI badge above the PULSE badges; keep badges.
- README: add **Acknowledgments** section.

### Fixed
- `publish_report_pages.yml`: copy `status.json` to site root; improve concurrency safety.

### Docs
- `CITATION.cff`: add ORCID for Katalin Horvat; add software reference to ChatGPT (GPT‑5 Pro).
- Add `docs/GOVERNANCE_PACK_v0.md`: overview of the optional Governance Pack
  (Stability Map, Decision Engine, EPF/Paradox Playbook, G-field, history tools).
Docs
- Add `docs/GLOSSARY_v0.md`: working glossary for core PULSE terms across the safe-pack, Core profile and Governance Pack.

### Security
- (no changes)
- 

### Changed
- 

### Fixed
- 

### Security
- 

- ### [v1.1.0] – 2025-11-09
+ ## [v1.1.0] – 2025-11-09

- ### [v1.0.3] – 2025-10-XX
+ ## [v1.0.3] – 2025-10-XX

   ### Added
   ...
   ### Notes
   ...


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

[Unreleased]: https://github.com/HKati/pulse-release-gates-0.1/compare/v1.1.0...HEAD
[v1.1.0]:     https://github.com/HKati/pulse-release-gates-0.1/compare/v1.0.3...v1.1.0
[v1.0.3]:     https://github.com/HKati/pulse-release-gates-0.1/compare/v1.0.2...v1.0.3
[v1.0.2]:     https://github.com/HKati/pulse-release-gates-0.1/compare/v1.0.1...v1.0.2
[v1.0.1]:     https://github.com/HKati/pulse-release-gates-0.1/compare/v1.0.0...v1.0.1
[v1.0.0]:     https://github.com/HKati/pulse-release-gates-0.1/releases/tag/v1.0.0

