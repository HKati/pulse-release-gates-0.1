# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]
### Added
- 

### Changed
- 

### Fixed
- 

### Security
- 

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

[Unreleased]: https://github.com/HKati/pulse-release-gates-0.1/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/HKati/pulse-release-gates-0.1/releases/tag/v1.0.1
[1.0.0]: https://github.com/HKati/pulse-release-gates-0.1/releases/tag/v1.0.0
