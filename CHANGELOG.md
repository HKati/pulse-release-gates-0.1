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
- Execute `tests/test_parameter_golf_submission_evidence_v0.py` through the CI pytest manifest (`ci/pytest-tests.list`).

### Docs
- Updated glossary terminology to use `PULSE Instrument Review Pack v0` as the active component name, with `Governance Pack` retained only as a legacy alias.
- `CITATION.cff`: add ORCID for Katalin Horvat; add software reference to ChatGPT (GPT-5 Pro).
- Add `docs/GOVERNANCE_PACK_v0.md`: overview of the optional Governance Pack (Stability Map, Decision Engine, EPF/Paradox Playbook, G-field, history tools).
- Add `docs/GLOSSARY_v0.md`: working glossary for core PULSE terms across the safe-pack, Core profile, and Governance Pack.

### Security
- (no changes)

### Post-v1.2.0 development

Comparison basis: [v1.2.0...HEAD][Post-v1.2.0].

#### Added

- Completed the PULSEmech current-run compute automation surface through
  Step 3G:
  - added the observed current-run export-expectation producer, protected
    carrier loader, current-run subject-input wrapper, manual candidate
    workflows, protected candidate-bundle intake, artifact-observed proof
    builder, and checksum-closed proof-bundle contract;
  - reused the existing subject-input producer and analyzer core rather than
    introducing parallel implementations;
  - retained the complete lane as manual, candidate-only, non-active,
    artifact-observed, and pre-authority, with `authority_effect = none`;
  - no manually dispatched Step 3G run, run-bound proof-bundle instance,
    runtime-observation producer, or active or release-required compute
    enforcement is claimed.
  - Provenance:
    - PRs #2789, #2814, #2815, #2818, #2819, #2822, #2823, #2825,
      #2826, and #2827;
    - terminal implementation commit:
      `9bf7fab95dbcc3532238723d0cf76500263106f5`;
    - canonical state-record commit:
      `1edfff9b570f7c29107311cefd9388dd92d4ba9a`.

- Added the reviewed
  [PULSEmech Transition-Bounded Computation Architecture v0](docs/PULSEMECH_TRANSITION_BOUNDED_COMPUTATION_ARCHITECTURE_v0.md)
  and the relational release-authority interpretation:
  - defined event-bound relation changes, dependency deltas, monotone affected
    closure, inspected-frontier accounting, invariant boundaries, computation
    cost accounting, and fail-closed unresolved state;
  - kept the architecture and relational interpretation non-activating and
    separate from the existing release-authority path.
  - Provenance:
    - PRs #2816, #2817, and #2820;
    - reviewed architecture commit:
      `fbfa9b0c03003eef93b23489ab7cb6cc72a9edeb`;
    - relational interpretation commit:
      `934109c89bb5787832f8e2952c2919fc06ee854e`.

- Completed the PULSEmech Device Ledger v0 bounded mechanical proof:
  - added the Device Canonical JSON and iOS observation contracts,
    ledger/signature/manifest/report schemas, deterministic synthetic reference
    artifacts, and the separately implemented standalone Python verifier;
  - added the Swift session-boundary, network-observation, coverage,
    transition, terminal-checkpoint, canonical-ledger, checkpoint-signature,
    manifest, package-signature, and deterministic `.pulseledger`
    materialization path;
  - proved exact Python–Swift reference-carrier byte parity;
  - reproduced an exact canonical verifier result with 49 of 49 checks passed
    and both signatures verified;
  - reproduced byte-identical verifier-report bytes on repeated execution;
  - proved fail-closed rejection of a structurally admissible, CRC-consistent
    package-signature mutation at `package_signature_valid`;
  - recorded the complete bounded proof in
    [PULSEmech Device Ledger Bounded Mechanical Proof v0](docs/PULSEMECH_DEVICE_LEDGER_BOUNDED_MECHANICAL_PROOF_v0.md).
  - Exact reference identities:
    - carrier size: `133568` bytes;
    - carrier SHA-256:
      `a31388c7bf574040893d1d923d684d23318e5d2109a0d72a923888b95d5d42b3`;
    - canonical verifier-report size: `15328` bytes;
    - canonical verifier-report SHA-256:
      `5e93539099e99dd5bfa835ba56c401608a5b5c015209812ebb5f9c31142a74f4`.
  - Provenance:
    - foundation: PR #2828;
    - verifier and relation corrections: PRs #2831, #2833, and #2834;
    - Swift observation, coverage, transition, and ledger closure:
      PRs #2835, #2836, #2837, and #2838;
    - checkpoint signature, manifest, package signature, and carrier:
      PRs #2840, #2842, #2843, and #2844;
    - standalone-verifier round trip and workflow correction:
      PRs #2845 and #2846;
    - runnable demonstrator: PR #2847;
    - canonical proof record: PR #2848;
    - terminal proof-record commit:
      `d2be905bbdf281cb4adff97b98618340d5ca5c39`.

- Added the minimal runnable iPhone bounded-proof demonstrator:
  - executes the existing deterministic synthetic reference materialization;
  - requires the exact generated checkpoint, ledger, manifest, carrier, and
    verifier-report identities;
  - admits only the exact canonical verifier-report bytes bound to the exact
    carrier generated by the current Swift execution;
  - displays the bounded proof result through a read-only result surface;
  - exports the exact current `.pulseledger` bytes;
  - remains `carrier_class = diagnostic_shadow`,
    `authority_effect = none`, and `external_validation_claim = none`;
  - does not execute, import, or reimplement the Python verifier and makes no
    self-verification claim.
  - Provenance:
    - PR #2847;
    - merge commit:
      `6a358187d8fde7321963b76cc50cc77fad695dd0`.

- Completed the PULSEmech Device Ledger Reproduction Capsule v0:
  - closed the exact four-member `ZIP_STORED` Capsule contract around the
    canonical Capsule manifest, canonical `.pulseledger`, unchanged standalone
    verifier, and canonical expected positive verifier report;
  - added the deterministic Capsule builder, strict reproduction-result schema,
    orchestration-only runner, checked-in canonical Capsule, canonical
    reproduction result, permanent execution regression, and dedicated
    reference-environment workflow;
  - constructed Capsule A and Capsule B in separate processes, workspaces, and
    output directories and proved exact A/B/canonical byte equality without
    reusing output, temporary state, materialized members, or computed archive
    bytes;
  - executed the unchanged standalone verifier twice in separate positive
    processes and required exact canonical stdout bytes, exit status `0`, empty
    stderr, `verified_with_declared_unavailability`, and 49 of 49 checks passed;
  - performed one isolated `signature_base64` first-character `O → P` mutation,
    repaired both ZIP CRC32 fields, and required the exact cryptographic
    rejection at `package_signature_valid`;
  - preserved ten protected repository source objects byte-for-byte before and
    after reproduction;
  - bound the reference execution to the externally verified digest-pinned
    Python 3.11.9 slim Bookworm image on `linux/amd64`, with no reproduction
    network, no runtime downloads, read-only repository and attestation mounts,
    and a separate writable output mount;
  - registered the execution regression exactly once and advanced the canonical
    tools-test manifest to `149` active, unique entries.
  - Exact canonical output identities:
    - Capsule path:
      `examples/device_transition_ledger/pulsemech_device_ledger_reproduction_capsule_v0.zip`;
    - Capsule size: `285144` bytes;
    - Capsule SHA-256:
      `49e02cf3daa466170b7ffee681ceb06c23410010b64e23137022541ec7691678`;
    - Capsule Git blob SHA-1:
      `5b2647823e59bde24cf9125851c1490e3149dfab`;
    - reproduction-result path:
      `examples/device_transition_ledger/pulsemech_device_ledger_reproduction_result_reference_v0.json`;
    - reproduction-result size: `31188` bytes;
    - reproduction-result SHA-256:
      `d0a659c572dcde11315f518d350361f6fc7690027c7e2682111f88a519b34ad1`;
    - reproduction-result Git blob SHA-1:
      `9b5a240495b357c64a510e6019e4d7189c29152e`;
    - reproduction-result framing: no UTF-8 BOM, CR, LF, or trailing newline.
  - Provenance:
    - exact Capsule manifest contract: PR #2851;
    - contract merge commit:
      `722fe4e85acfaac67c283862645ac9e42c831236`;
    - deterministic execution: PR #2852;
    - reviewed final PR head:
      `5d8792ffb5c1f555b50f01bb34fa9757e20af5ec`;
    - squash-merge commit:
      `21837e1e54f898a131d3a9bff89527209ddae711`;
    - post-merge review:
      no actionable findings on the squash-merge commit.

#### Fixed

- Closed Device Ledger verifier and proof-parity defects involving:
  - stale-session lifecycle acceptance;
  - interrupted-coverage gap reconstruction;
  - exact canonical verifier-report byte binding;
  - duplicate semantic endpoint-transition materialization;
  - verifier-trigger trailing whitespace.
  - Provenance: PRs #2831, #2833, #2834, and #2846.

- Closed current-run compute regression false-green paths involving inherited
  pytest control inputs, plugin injection, deselection, skipped call phases,
  and terminal early exits before complete test execution.
  - Provenance: PRs #2818 and #2819.

- Closed Device Ledger Reproduction Capsule execution false-success and
  exact-byte defects:
  - removed inherited `PYTEST_ADDOPTS`, `PYTEST_PLUGINS`, and
    `PYTEST_CURRENT_TEST` from the no-argument permanent-regression launch;
  - disabled plugin autoload and external conftest or repository-configuration
    influence;
  - required all 15 collected proof tests to produce plain passing call reports,
    rejecting collection-only, deselection, skipped proof execution, xfail,
    xpass, and premature success;
  - restored the exact 31,188-byte canonical reproduction-result object after a
    browser-mediated upload appended one trailing LF byte.
  - Provenance: PR #2852.

#### Security

- Hardened the GitHub Actions supply-chain boundary:
  - pinned external Actions to immutable full commit identities;
  - disabled persisted checkout credentials on the hardened workflow surfaces;
  - added fail-closed workflow lint for mutable or abbreviated Action
    references and unsafe checkout credential persistence.
  - Provenance: PR #2803.

- Restored and hardened the privileged SARIF publication path:
  - retained first-party `actions/download-artifact`;
  - retained first-party `github/codeql-action/upload-sarif`;
  - bound upload eligibility to the exact GitHub-owned source workflow-run,
    repository, event, ref, commit, and pull-request relation;
  - rejected ambiguous, substituted, drifted, unsupported, or unverified
    source-run state.
  - Provenance: PRs #2804, #2805, and #2812.

- Hardened current-run compute construction and intake against:
  - symlink and path-component substitution;
  - hard-link and inode replacement;
  - partial-clone, promisor, lazy-fetch, alternate-object, and replacement-object
    state;
  - unsafe, duplicate, encrypted, malformed, oversized, or checksum-invalid
    archive members;
  - stale, partial, redirected, or attacker-substituted transactional output.
  - Provenance: PRs #2815, #2822, #2823, #2825, and #2826.

- Hardened Device Ledger Reproduction Capsule construction and execution:
  - required host-runtime RepoDigest verification before launching the exact
    declared container digest;
  - covered publication interruption with `BaseException` cleanup while
    re-raising the original interruption;
  - blocked interrupt delivery across directory creation, immediate
    device/inode capture, `O_NOFOLLOW` descriptor acquisition, descriptor
    identity verification, and owned-state publication;
  - removed pathname `stat`-then-`rmdir` cleanup and retained uncertain
    random-name directories rather than risking deletion of substituted
    objects;
  - kept output ownership bound to retained descriptors and exact filesystem
    identities and kept protected-source drift fail-closed.
  - Provenance: PR #2852.

#### Docs

- Synchronized the canonical
  [PULSEmech Technical Overview](PULSEMECH_TECHNICAL_OVERVIEW.md), README,
  compute workstream record, and documentation index with the merged
  implementation state.
  - Provenance: PRs #2795, #2796, #2798, #2806, #2827, and #2848.

- Added reviewed interoperability and measurement-boundary records for:
  - Witness policy and attestation verification;
  - classic in-toto layout/link evidence;
  - synthetic-data information contribution and measurement saturation;
  - restart authority and alternative-path closure.
  - Provenance: PRs #2797, #2801, #2807, #2808, and #2839.

- Added the canonical Device Ledger bounded mechanical proof record and
  separated:
  - mechanical reproducibility;
  - optional external reproduction;
  - external adoption;
  - institutional maturity.
  - Provenance: PR #2848.

- Completed the Device Ledger Reproduction Capsule documentation closure across
  six existing documentation files without creating a second canonical proof
  document:
  - extended the canonical bounded mechanical proof record with the exact
    Capsule contract, deterministic execution, two-construction equality,
    positive and targeted-negative relations, protected-source preservation,
    and distinct execution entrypoints;
  - extended External Verification Path v0 with direct `.pulseledger`
    verification, complete pinned workflow dispatch, portable local proof
    replay, bounded inner-runner execution, Swift round trip, and read-only
    iPhone demonstration;
  - synchronized the README, documentation index, and canonical Technical
    Overview with the merged PR #2851–#2852 state;
  - recorded the complete asynchronous reference-workflow command and the
    separate local 15-test proof-replay command;
  - preserved one canonical Device Ledger proof entrypoint and the distinction
    between proof record, reviewer/operator procedure, and implementation-state
    overview.
  - Provenance: PR #2855.

#### Boundaries

- Current-run compute remains manual, candidate-only, non-active,
  artifact-observed, and pre-authority.
- Runtime-observed compute proof, per-axis resource measurement, stable
  measurement coverage, and any compute-gate promotion remain separate work.
- The Device Ledger reference remains:
  - `record_status = synthetic_reference`;
  - `identity_scope = fixture_installation`;
  - `key_origin_profile = fixture_software_p256`.
- The iPhone demonstrator remains a non-authorizing carrier of the already
  closed bounded proof.
- The Device Ledger Reproduction Capsule remains a portable construction and
  execution carrier around the already closed bounded proof.
- The canonical reproduction result remains orchestration evidence:
  - `reproduction_result_role = orchestration_evidence_not_verifier_verdict`;
  - the existing standalone verifier remains the verifier;
  - the runner remains orchestration-only;
  - no producer verdict is trusted.
- The Capsule, reproduction result, workflow artifact, documentation, local
  replay, and optional external reproduction event do not create a gate result,
  release decision, release authority, or device-control authority;
  `authority_effect = none`.
- The digest-pinned reference-environment result does not create a universal
  cross-platform reproducibility claim, production-device claim,
  hardware-backed identity claim, or external-validation claim.
- General-purpose iPhone product development, live production observation,
  persistent storage, restart recovery, production key lifecycle, Secure
  Enclave integration, platform attestation, physical-device identity, and
  App Store qualification remain separate wider work.
- Policy, active gate sets, `status.json`, terminal release decisions, and
  release authority remain unchanged by these milestones.
- The documentation closure modifies no source code, test, workflow, schema,
  contract, canonical JSON artifact, binary artifact, standalone verifier,
  release policy, `.zenodo.json`, DOI identity, Zenodo metadata or relationship,
  `CITATION.cff`, Git tag, or GitHub Release.


## [1.2.0] - 2026-08-04

### Milestone

- Recorded `v1.2.0` as a new milestone in the same continuous PULSE
  development line.
- Established the PULSEmech Transition Meter as the foundational
  evidence-bound transition-measurement architecture.
- Positioned artifact-bound AI release authority as the first concrete
  implementation domain of the broader architecture.
- Recorded the implemented release-transition path:

  ```text
  recorded current-run release evidence
  → exact subject, run, evidence, and artifact binding
  → declared release policy
  → workflow-effective required-gate materialization
  → deterministic verifier replay
  → final gate state
  → strict fail-closed evaluation
  → ALLOW or BLOCK
  ```

-  Included the then-current state of:
  -  release-grade reference-package assembly and verification;
  -  the Tier 0 self-contained evidence floor;
  -  fixed-source PULSE CI #6066 preservation;
  -  current-run export-expectation contracts and validation;
  -  recorded SLSA/VSA candidate evidence intake;
  -  protected control-plane and source-identity hardening.

### Provenance

-  GitHub Release: `PULSEmech Transition Meter — v1.2.0`.
-  Release tag: `v1.2.0`.
-  Tagged commit:
   `b324e733296c200c7d9b799463414c82e533a921`.
-  Published: `2026-08-04`.

### Boundaries

-  The general cross-domain Transition Meter remained a foundational
   architecture and implementation direction.
-  The release did not claim:
  -  a completed universal cross-domain instrument;
  -  automatic causal sufficiency;
  -  replacement of domain instruments;
  -  replacement of domain verification;
  -  automatic authority from transition observation;
  -  downstream deployment coverage after CI `ALLOW` or `BLOCK`.
-  The release event activated no new policy set, required gate, verifier,
   authority path, or external executor.
-  The release created no replacement PULSE project identity or development
   line.

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

[Unreleased]: https://github.com/HKati/pulse-release-gates-0.1/compare/v1.2.0...HEAD
[1.1.1]: https://github.com/HKati/pulse-release-gates-0.1/releases/tag/V1.1.1
[1.1.0]: https://github.com/HKati/pulse-release-gates-0.1/releases/tag/v1.1.0
[1.0.3]: https://github.com/HKati/pulse-release-gates-0.1/releases/tag/v1.0.3
[1.0.2]: https://github.com/HKati/pulse-release-gates-0.1/releases/tag/v.1.0.2
[1.0.1]: https://github.com/HKati/pulse-release-gates-0.1/releases/tag/v.1.0.1
[1.0.0]: https://github.com/HKati/pulse-release-gates-0.1/releases/tag/v1.0.0
[Post-v1.2.0]: https://github.com/HKati/pulse-release-gates-0.1/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/HKati/pulse-release-gates-0.1/releases/tag/v1.2.0
