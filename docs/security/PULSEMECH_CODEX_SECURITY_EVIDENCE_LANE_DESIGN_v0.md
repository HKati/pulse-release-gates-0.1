# PULSEmech Codex Security Evidence Lane Design v0

## Document state

```yaml
document_id: pulsemech_codex_security_evidence_lane_design_v0
document_type: design
revision: v0
status: design_only
authority_effect: none
gate_effect: none
policy_effect: none
schema_effect: none
ci_effect: none
release_effect: none
```

This document defines a future PULSEmech evidence lane for importing,
verifying, normalizing, and optionally materializing completed Codex Security
scan evidence.

This document does not:

- run Codex Security;
- add a GitHub Actions workflow;
- add or activate gates;
- change `status.json`;
- change `check_gates.py`;
- modify any required gate set;
- make Codex Security release-required;
- permit Codex Security to authorize a release;
- accept a report, SARIF file, command exit code, or dashboard state as release
  evidence by itself.

Implementation and activation require separate pull requests.

---

## 1. Purpose

Codex Security can inspect a repository and produce structured security
findings together with a record of the reviewed target and the achieved
coverage.

PULSEmech can use that output only after the output becomes a verified,
artifact-bound evidence carrier.

The intended relation is:

```text
Codex Security
produces a security observation

PULSEmech
verifies the carrier, subject, producer, run, coverage, and policy relation

PULSEmech release authority
remains the only mechanism that may produce an enforced ALLOW or BLOCK state
```

The lane therefore separates:

```text
security analysis
```

from:

```text
release authority
```

Codex Security is an external evidence producer.

Codex Security is not a PULSEmech release decision engine.

---

## 2. Core authority invariant

The core invariant is:

```text
Codex Security output ≠ release permission
```

A positive Codex Security result cannot authorize release by:

- command completion;
- process exit code;
- absence of reported findings;
- presence of a report;
- presence of SARIF;
- presence of a scan directory;
- a human-readable statement;
- a workflow check name;
- an uploaded artifact name;
- a severity threshold configured only inside the scanner;
- an unverified adapter summary.

A Codex Security observation may participate in release-state evaluation only
through this path:

```text
recorded canonical scan bundle
→ verified source-bundle integrity
→ exact producer identity
→ exact subject binding
→ exact run and recipe binding
→ complete declared coverage
→ deterministic findings-policy evaluation
→ normalized PULSEmech summary
→ declared candidate gate set
→ separately approved promotion
→ strict PULSEmech enforcement
```

No earlier element in the path has release authority.

---

## 3. Design position

The lane is designed as a dedicated security evidence path.

It must not be flattened into the existing generic external-detector scalar
interface.

A Codex Security result contains several independent authority-relevant
relations:

```text
bundle integrity
producer identity
subject identity
scan recipe
coverage completeness
explicit exclusions
deferred work
finding identity
finding severity
finding-policy evaluation
```

A single numeric `rate` cannot preserve those relations.

The initial integration must therefore use:

```text
dedicated source bundle
dedicated intake packet
dedicated verifier
dedicated normalized summary
dedicated candidate gate set
```

The generic `external_all_pass` path must not be used as the initial authority
carrier.

---

## 4. Scope

### 4.1 Included in v0 design

This design covers:

- an exact Git revision as the scan subject;
- a completed Codex Security canonical scan bundle;
- a separately recorded producer receipt;
- immutable file digests;
- a PULSEmech subject-input packet;
- offline schema validation;
- source-bundle integrity validation;
- producer and tool identity validation;
- current-run binding;
- exact Git revision binding;
- declared scan-recipe binding;
- coverage completeness validation;
- deterministic finding classification;
- deterministic severity-policy evaluation;
- a normalized PULSEmech security summary;
- an inactive candidate gate set;
- negative fixtures and replay proof;
- a later, separate promotion boundary.

### 4.2 Excluded from initial implementation

The following are excluded from the first implementation:

- automatic scanning of untrusted pull-request code with a secret;
- scanning arbitrary external repositories;
- automatic application of generated patches;
- automatic commits;
- automatic pull requests;
- automatic merge;
- scanner-controlled release decisions;
- human workbench triage as release evidence;
- mutable false-positive state as release evidence;
- `git_worktree` targets in a release-capable lane;
- `git_diff` targets in a release-capable lane;
- `directory_snapshot` targets in a release-capable lane;
- cross-scan lifecycle classification as authority evidence;
- organization-wide bulk scanning;
- public publication of raw security findings;
- release-gate activation.

These functions may be designed later through separate boundaries.

---

## 5. Initial operating profile

The first executable lane should use this profile:

```yaml
trigger: workflow_dispatch
target_kind: git_revision
target_revision: exact_full_commit_sha
repository_state: clean
scan_scope: repository
scan_mode: standard
inventory_strategy: repository
producer_location: isolated_ephemeral_job
output_location: outside_git_worktree
raw_result_visibility: restricted_workflow_artifact
authority_mode: candidate_advisory
release_effect: none
blocking_severities:
  - critical
  - high
medium_severity_effect: recorded_non_blocking
low_severity_effect: recorded_non_blocking
unknown_severity_effect: fail_closed
triage_override_supported: false
patch_command_allowed: false
```

The exact package version, plugin version, runtime version, model, reasoning
effort, expected include paths, and expected exclude paths must be bound by the
candidate policy created during implementation.

They must not be inferred from whatever the producer happens to emit.

---

## 6. Canonical Codex Security source contract

A completed Codex Security scan produces three canonical machine-readable
documents:

```text
scan-manifest.json
findings.json
coverage.json
```

The initial PULSEmech intake must use these three documents as its semantic
source.

The following outputs are projections and must not be treated as primary
authority evidence:

```text
report.md
SARIF
CSV
console output
workflow log
human summary
dashboard state
```

The adapter must not recover missing semantic data by parsing `report.md`.

The adapter must not recover missing semantic data by parsing SARIF.

The adapter must not interpret the absence of text in a readable report as the
absence of a finding.

### 6.1 `scan-manifest.json`

The manifest is expected to carry the completed scan identity, including:

- document type;
- schema version;
- scan identifier;
- producer name;
- producer version;
- completed status;
- start time;
- completion time;
- seal time;
- target kind;
- target identity;
- target revision or snapshot identity;
- included paths;
- excluded paths;
- reference to `findings.json`;
- reference to `coverage.json`;
- recorded artifact digests.

The PULSEmech verifier must calculate the digest of `scan-manifest.json`
independently.

The verifier must not expect a manifest to contain a self-digest.

### 6.2 `findings.json`

The findings document is expected to carry:

- document type;
- schema version;
- scan identifier;
- finding identifiers;
- occurrence identifiers;
- rule identifiers;
- semantic anchors;
- fingerprints;
- severity;
- confidence;
- taxonomy;
- affected locations;
- remediation data;
- validation data when present;
- attack-path data when present;
- provenance.

PULSEmech must evaluate the canonical finding records.

A rendered finding table is not a substitute for the canonical records.

### 6.3 `coverage.json`

The coverage document is expected to carry:

- document type;
- schema version;
- scan identifier;
- requested scan mode;
- coverage completeness;
- inventory strategy;
- included paths;
- excluded paths;
- reviewed surfaces;
- explicit exclusions;
- deferred units;
- receipt references when present.

Coverage must remain a separate decision dimension.

This distinction is mandatory:

```text
no finding was observed
```

is not equivalent to:

```text
the required surface was completely scanned and no blocking finding was found
```

---

## 7. Trust boundaries

The lane crosses the following trust boundaries:

```text
repository content
→ Codex Security runtime

Codex Security runtime
→ generated source bundle

generated source bundle
→ PULSEmech intake staging area

intake staging area
→ PULSEmech verifier

verified intake report
→ normalized PULSEmech summary

normalized summary
→ candidate gate state
```

Each transition must be explicit.

### 7.1 Untrusted inputs

The verifier must treat all of the following as untrusted input:

- repository content;
- generated JSON;
- generated filenames;
- manifest paths;
- artifact references;
- timestamps;
- target identity declared by the producer;
- producer version declared by the producer;
- finding severity;
- finding identifiers;
- coverage completeness;
- include paths;
- exclude paths;
- deferred entries;
- receipt references;
- human-readable reports;
- SARIF;
- console output;
- workflow annotations.

No field becomes trusted because it was generated by a security tool.

Trust is established only by a successful relation between the recorded source
bundle and independently supplied expectations.

---

## 8. Threat model

The design must defend against at least the following failures.

### 8.1 Subject substitution

A valid scan bundle may describe:

- a previous commit;
- another branch;
- another repository;
- a dirty worktree;
- a different pull-request head;
- an unrecorded local modification;
- a partial directory snapshot.

A valid bundle for the wrong subject is not valid release evidence.

### 8.2 Stale evidence

A completed scan may be old while the repository has advanced.

Wall-clock recency alone does not solve this problem.

The primary freshness binding is:

```text
exact current run
+
exact current Git revision
```

### 8.3 Bundle mutation

A findings or coverage document may be modified after finalization.

Every canonical input must be digest-verified.

### 8.4 Producer substitution

A different package, plugin, wrapper, model, or runtime may produce a
structurally similar bundle.

Producer identity must be checked against an independent expected identity.

### 8.5 Recipe drift

A scan may silently change:

- mode;
- scope;
- included paths;
- excluded paths;
- model;
- reasoning effort;
- plugin version;
- package version;
- coverage strategy.

A changed recipe is a different observation process.

### 8.6 Coverage collapse

A scan may complete after reviewing only part of the required surface.

The absence of findings under partial or unknown coverage must fail closed.

### 8.7 Exclusion injection

An attacker or configuration error may exclude a security-sensitive path.

The actual exclusions must exactly match the declared exclusion policy.

### 8.8 Deferred-work collapse

A scan may defer required work while still producing readable output.

Deferred required work must not be converted into a passing result.

### 8.9 Path traversal and symlink substitution

A source-bundle path may:

- escape its staging root;
- traverse through `..`;
- use an absolute path;
- use a symlink;
- point to a replaced file;
- point to a non-regular file.

All input paths must remain inside the authorized staging root and resolve to
regular, non-symlink files.

### 8.10 Credential exposure

The scanning process may inherit unrelated environment credentials.

The producer job must receive only the credentials required for the scan.

### 8.11 Mutable triage substitution

A mutable local workbench may classify a finding as a false positive.

Mutable triage state is not part of the v0 authority carrier.

### 8.12 Report projection substitution

A readable report or exported SARIF file may differ from the canonical JSON
bundle.

Only the verified canonical documents may drive the normalized summary.

---

## 9. End-to-end machine

The complete proposed machine is:

```text
exact selected Git revision
→ clean isolated checkout
→ pinned Codex Security producer
→ completed canonical source bundle
→ producer receipt
→ immutable source-bundle index
→ PULSEmech intake packet
→ PULSEmech intake verifier
→ PULSEmech intake report
→ normalized Codex Security summary
→ inactive candidate gate fold-in
→ candidate proof
→ separate promotion review
```

The release-authority path remains:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ ALLOW or BLOCK
```

The Codex Security lane may connect to that path only after promotion.

---

## 10. Producer job design

### 10.1 Isolation

The producer must run in a dedicated ephemeral job.

The job must not reuse a long-lived development workspace.

The recommended first execution environment is a GitHub-hosted ephemeral
runner.

The job must use:

```yaml
permissions:
  contents: read
```

Checkout must use:

```yaml
persist-credentials: false
fetch-depth: 0
```

The job must not receive:

- repository write permission;
- package publish permission;
- deployment permission;
- cloud credentials unrelated to the scan;
- signing keys unrelated to the scan;
- release tokens;
- mutable production credentials.

### 10.2 Output location

Codex Security state and result directories must be outside the checked-out
Git worktree.

Illustrative layout:

```text
${RUNNER_TEMP}/pulsemech-codex-security/
├── state/
├── results/
└── producer-receipts/
```

Raw output must not be written into:

```text
${GITHUB_WORKSPACE}
```

The repository must not commit raw findings.

### 10.3 Package installation

The implementation must use a package version pinned by an exact dependency
lock.

A floating install is forbidden:

```text
@openai/codex-security@latest
```

The producer wrapper must record:

- package name;
- exact package version;
- package-lock digest;
- package integrity value when available;
- bundled plugin version;
- Codex runtime version;
- selected model;
- selected reasoning effort;
- Node.js version;
- Python version.

The expected values must come from the PULSEmech candidate policy.

### 10.4 Scan command boundary

The producer should run Codex Security in report-producing mode.

The initial PULSEmech lane must not delegate severity policy to the CLI.

The producer should not use the CLI process exit code as the release result.

The lane must separately record:

```text
producer process completion
canonical bundle validity
coverage validity
findings-policy result
```

A successful producer process may still contain blocking findings.

A failed producer process may still leave partial files.

Partial files must not become accepted evidence.

### 10.5 Forbidden producer commands

The automated producer lane must not execute:

```text
codex-security patch
codex-security install-hook
automatic fix application
automatic git commit
automatic git push
automatic pull-request creation
```

A future repair workflow requires a separate design and authority boundary.

---

## 11. Producer receipt

The canonical Codex Security bundle does not by itself carry every
PULSEmech-required producer expectation.

A PULSEmech-controlled wrapper must produce:

```text
codex_security_producer_receipt_v0.json
```

The receipt should contain at least:

```yaml
document_type: pulsemech.codex-security-producer-receipt
schema_version: "0.1"

workflow:
  name: string
  repository: string
  run_id: string
  run_attempt: integer
  event_name: string
  ref: string
  git_sha: full_commit_sha

producer:
  package_name: "@openai/codex-security"
  package_version: exact_version
  package_lock_sha256: sha256
  package_integrity: string_or_null
  plugin_name: string
  plugin_version: exact_version
  runtime_version: exact_version
  model: exact_model
  reasoning_effort: exact_effort
  node_version: exact_version
  python_version: exact_version

scan:
  requested_target_kind: git_revision
  requested_revision: full_commit_sha
  requested_mode: string
  requested_include_paths: array
  requested_exclude_paths: array
  started_at: date_time
  completed_at: date_time_or_null
  process_exit_code: integer
  scan_id: string_or_null

outputs:
  scan_manifest_path: relative_path
  findings_path: relative_path
  coverage_path: relative_path
```

The receipt must not contain:

- API keys;
- access tokens;
- cookie values;
- credential paths containing secret material;
- full environment dumps;
- unrelated runner metadata.

The receipt is a carrier.

It is not trusted merely because it exists.

---

## 12. Source-bundle index

The PULSEmech wrapper must produce an immutable source-bundle index after the
producer stops:

```text
codex_security_source_bundle_index_v0.json
```

The index must identify:

```text
scan-manifest.json
findings.json
coverage.json
codex_security_producer_receipt_v0.json
```

For each file it must record:

- relative path;
- byte size;
- SHA-256;
- media type;
- regular-file result;
- symlink result.

### 12.1 Deterministic bundle identity

The initial bundle identity should be calculated as:

```text
sha256(
  "pulsemech-codex-security-source-bundle-v0\n"
  + scan_manifest_sha256 + "\n"
  + findings_sha256 + "\n"
  + coverage_sha256 + "\n"
  + producer_receipt_sha256 + "\n"
)
```

The component order is fixed.

The digest strings use lowercase hexadecimal SHA-256.

The input paths do not participate in the bundle identity.

The index records both:

```text
component digests
bundle identity
```

---

## 13. Intake staging boundary

The PULSEmech verifier must operate on a dedicated staging root.

Illustrative layout:

```text
${RUNNER_TEMP}/pulsemech-codex-security-intake/
├── source/
│   ├── scan-manifest.json
│   ├── findings.json
│   ├── coverage.json
│   ├── codex_security_producer_receipt_v0.json
│   └── codex_security_source_bundle_index_v0.json
├── packet/
│   └── codex_security_intake_packet_v0.json
└── reports/
```

The staging root must not be inside the source repository.

Before parsing JSON, the intake verifier must establish:

- every expected file exists;
- every expected file is a regular file;
- no expected file is a symlink;
- no path escapes the staging root;
- no duplicate resolved path exists;
- no file is empty;
- every file size is below its declared maximum;
- calculated digests match the bundle index.

---

## 14. PULSEmech intake packet

The PULSEmech-controlled packet must be:

```text
codex_security_intake_packet_v0.json
```

The packet supplies independent expectations.

It must not copy expected values from the untrusted source bundle.

### 14.1 Required packet fields

```yaml
document_type: pulsemech.codex-security-intake-packet
schema_version: "0.1"
record_status: example_or_observed
packet_scope: example_or_current_run

subject_expectation:
  repository_identity: string
  target_kind: git_revision
  revision: full_commit_sha

run_expectation:
  workflow_name: string
  workflow_run_id: string
  workflow_run_attempt: integer
  event_name: workflow_dispatch
  ref: string

producer_expectation:
  package_name: "@openai/codex-security"
  package_version: exact_version
  package_lock_sha256: sha256
  plugin_name: exact_name
  plugin_version: exact_version
  runtime_version: exact_version
  model: exact_model
  reasoning_effort: exact_effort

scan_recipe_expectation:
  scan_mode: exact_mode
  inventory_strategy: repository
  include_paths: exact_array
  exclude_paths: exact_array
  required_coverage_completeness: complete
  allowed_explicit_exclusions: exact_array
  deferred_allowed: false

findings_policy_binding:
  policy_id: string
  policy_version: string
  policy_sha256: sha256

verifier_binding:
  verifier_path: repository_relative_path
  verifier_sha256: sha256
  verifier_version: string

source_bundle:
  bundle_index_path: staged_relative_path
  bundle_index_sha256: sha256
  bundle_identity: sha256
```

### 14.2 Expected-value independence

These values must be provided by the caller or declared candidate policy:

- expected Git revision;
- expected package version;
- expected plugin version;
- expected model;
- expected reasoning effort;
- expected scan mode;
- expected paths;
- expected coverage state;
- expected policy identity;
- expected verifier identity.

The packet builder must reject a mode that derives these expectations from:

- `scan-manifest.json`;
- `findings.json`;
- `coverage.json`;
- producer receipt;
- report text;
- command output.

A source artifact cannot supply its own expected identity.

---

## 15. Upstream schema handling

PULSEmech verification must not depend on a live schema download.

The implementation should vendor a reviewed snapshot of the relevant upstream
Codex Security schemas.

Illustrative layout:

```text
vendor/openai/codex-security/
└── <upstream-commit>/
    ├── LICENSE
    ├── SOURCE.json
    └── schemas/
        ├── scan-manifest.schema.json
        ├── findings.schema.json
        └── coverage.schema.json
```

`SOURCE.json` should record:

- upstream repository identity;
- upstream commit;
- package version associated with the snapshot when known;
- retrieval date;
- individual file digests;
- license identity;
- reviewer note.

The verifier must bind the expected upstream schema snapshot by digest.

A package upgrade must not silently replace these files.

---

## 16. Intake verifier

The proposed verifier is:

```text
tools/check_codex_security_intake_packet_v0.py
```

The verifier must be offline and deterministic.

The same:

```text
source bundle
+
intake packet
+
candidate policy
+
verifier version
```

must produce the same intake report.

### 16.1 Filesystem checks

The verifier must check:

- staging-root containment;
- regular-file status;
- symlink rejection;
- path normalization;
- duplicate path rejection;
- maximum file sizes;
- expected file presence;
- exact SHA-256 values;
- exact bundle identity.

### 16.2 JSON checks

The verifier must check:

- UTF-8 decoding;
- JSON parseability;
- top-level object type;
- exact expected document type;
- supported schema version;
- vendored schema validity;
- no duplicate semantic artifact path;
- no unresolved required reference.

### 16.3 Cross-document checks

The verifier must require:

```text
manifest scan id
==
findings scan id
==
coverage scan id
==
producer-receipt scan id
```

The verifier must require:

```text
manifest findings reference == findings.json
manifest coverage reference == coverage.json
```

The verifier must independently calculate the findings and coverage digests.

Those digests must match the manifest artifact records.

### 16.4 Manifest checks

The verifier must require:

```text
manifest scan status == completed
```

The manifest target kind must equal:

```text
git_revision
```

The manifest target revision must equal:

```text
intake packet expected revision
```

A shortened SHA is insufficient.

A missing revision is insufficient.

A branch name is insufficient.

A tag name without resolved commit identity is insufficient.

### 16.5 Producer identity checks

The verifier must compare:

```text
manifest producer identity
producer receipt identity
intake packet expected producer identity
```

The required relations must be explicit.

At minimum:

```text
manifest plugin version
==
producer receipt plugin version
==
expected plugin version
```

The package version, lock digest, runtime version, model, and reasoning effort
must match the intake packet expectation.

Unknown or missing required producer identity fails closed.

### 16.6 Current-run checks

The producer receipt must match the current intake packet for:

- repository identity;
- workflow name;
- run identifier;
- run attempt;
- event name;
- ref;
- Git SHA.

A bundle from another workflow run must not satisfy the current-run lane.

A previous-run bundle must not be accepted because it evaluates the same path.

### 16.7 Recipe checks

The verifier must compare the actual scan recipe with the declared expected
recipe.

The following must match:

- target kind;
- target revision;
- requested scan mode;
- actual coverage mode;
- inventory strategy;
- include paths;
- exclude paths.

Path-array comparison must use declared deterministic semantics.

The first implementation should require exact array equality after a declared
normalization step.

The normalization step must:

- reject absolute paths;
- reject `..`;
- normalize separators;
- reject duplicates;
- sort only if the policy declares order-insensitive semantics.

### 16.8 Coverage checks

The initial candidate policy must require:

```text
coverage.completeness == complete
```

It must also require:

```text
coverage.inventoryStrategy == repository
coverage.deferred is empty
```

Actual explicit exclusions must exactly match the policy allowlist.

An extra exclusion fails closed.

A missing required exclusion record fails closed if the policy expects it.

A reviewed surface with a disposition equivalent to unresolved follow-up must
not be treated as complete passing coverage.

The verifier must preserve:

- reviewed surface identifiers;
- surface dispositions;
- explicit exclusions;
- deferred units;
- open questions when present.

### 16.9 Findings checks

The verifier must validate:

- finding identifiers;
- occurrence identifiers;
- fingerprints;
- rule identifiers;
- severity structure;
- confidence structure when present;
- location structures;
- duplicate finding identity;
- supported severity values.

An unknown severity value fails closed.

A missing severity fails closed.

A malformed finding fails closed.

The verifier must not discard a finding because:

- confidence is low;
- remediation is missing;
- a readable report omits it;
- an exported SARIF file omits it;
- a mutable workbench classified it differently.

### 16.10 Findings-policy evaluation

The initial candidate policy is:

```yaml
blocking_severities:
  - critical
  - high

non_blocking_recorded_severities:
  - medium
  - low

unknown_severity: block
missing_severity: block
triage_override: unsupported
```

The policy result is:

```text
findings_policy_pass == true
```

only when:

```text
verified canonical findings document
+
zero critical findings
+
zero high findings
+
zero unknown-severity findings
+
zero malformed findings
```

Medium and low findings remain recorded.

They do not disappear from the summary.

### 16.11 No implicit pass

The verifier must never derive a passing findings policy from:

- an empty directory;
- a missing findings file;
- an empty findings file;
- malformed JSON;
- an unsupported schema version;
- a producer error;
- partial coverage;
- unknown coverage;
- missing surfaces;
- unapproved exclusions;
- deferred work;
- a missing severity;
- an unknown severity;
- absence of a readable report;
- process exit code zero.

Zero findings can contribute to a passing result only after every required
integrity, identity, subject, recipe, and coverage check passes.

---

## 17. Intake report

The verifier must emit:

```text
codex_security_intake_report_v0.json
```

The report should have one of three result classes:

```text
verified_pass
verified_block
unverified
```

### 17.1 `verified_pass`

This means:

- source bundle valid;
- source bundle integrity valid;
- expected producer matched;
- current run matched;
- exact subject matched;
- expected recipe matched;
- coverage requirements passed;
- findings document valid;
- findings policy passed.

### 17.2 `verified_block`

This means:

- source bundle is valid and attributable;
- subject, producer, recipe, and coverage checks passed;
- the findings policy did not pass.

Example:

```text
one verified high-severity finding
```

The evidence is valid.

Its policy result is blocking.

### 17.3 `unverified`

This means the evidence could not be accepted as a valid observation.

Examples:

- missing canonical file;
- digest mismatch;
- wrong revision;
- wrong producer;
- wrong run;
- partial coverage;
- malformed JSON;
- unsupported schema;
- unexpected exclusion;
- deferred required work.

An unverified result must not be rewritten as:

```text
no vulnerabilities found
```

---

## 18. Reason codes

The intake report must use stable machine-readable reason codes.

Initial reason-code families should include:

```text
source_bundle_missing
source_bundle_path_escape
source_bundle_symlink
source_bundle_non_regular_file
source_bundle_digest_mismatch
source_bundle_identity_mismatch

manifest_parse_error
manifest_schema_error
manifest_status_not_completed
manifest_artifact_record_missing
manifest_artifact_record_duplicate
manifest_artifact_digest_mismatch

findings_parse_error
findings_schema_error
findings_scan_id_mismatch
findings_duplicate_identity
findings_unknown_severity
findings_missing_severity
findings_blocking_severity_present

coverage_parse_error
coverage_schema_error
coverage_scan_id_mismatch
coverage_not_complete
coverage_inventory_strategy_mismatch
coverage_include_paths_mismatch
coverage_exclude_paths_mismatch
coverage_unapproved_exclusion
coverage_deferred_work_present
coverage_required_surface_unresolved

producer_receipt_parse_error
producer_receipt_schema_error
producer_package_mismatch
producer_plugin_mismatch
producer_runtime_mismatch
producer_model_mismatch
producer_reasoning_effort_mismatch

subject_repository_mismatch
subject_kind_mismatch
subject_revision_mismatch

run_workflow_mismatch
run_id_mismatch
run_attempt_mismatch
run_event_mismatch
run_ref_mismatch
run_git_sha_mismatch

policy_identity_mismatch
policy_digest_mismatch
verifier_identity_mismatch
verifier_digest_mismatch
```

Human-readable text may accompany the codes.

Human-readable text is not the machine decision surface.

---

## 19. Normalized PULSEmech summary

A successful verifier execution must support generation of:

```text
codex_security_summary_v0.json
```

The proposed builder is:

```text
tools/build_codex_security_summary_v0.py
```

The builder must consume:

```text
verified intake report
+
verified canonical source documents
+
declared findings policy
```

It must not independently reinterpret unverified source files.

### 19.1 Proposed summary shape

```json
{
  "document_type": "pulsemech.codex-security-summary",
  "schema_version": "0.1",
  "record_status": "observed",
  "subject": {
    "repository_identity": "HKati/pulse-release-gates-0.1",
    "target_kind": "git_revision",
    "revision": "<full-sha>"
  },
  "run_binding": {
    "workflow_name": "<name>",
    "run_id": "<id>",
    "run_attempt": 1,
    "event_name": "workflow_dispatch",
    "ref": "<ref>"
  },
  "producer": {
    "package_name": "@openai/codex-security",
    "package_version": "<exact>",
    "plugin_name": "<exact>",
    "plugin_version": "<exact>",
    "runtime_version": "<exact>",
    "model": "<exact>",
    "reasoning_effort": "<exact>"
  },
  "source_bundle": {
    "bundle_identity": "<sha256>",
    "scan_manifest_sha256": "<sha256>",
    "findings_sha256": "<sha256>",
    "coverage_sha256": "<sha256>",
    "producer_receipt_sha256": "<sha256>"
  },
  "coverage": {
    "completeness": "complete",
    "inventory_strategy": "repository",
    "include_paths": [],
    "exclude_paths": [],
    "explicit_exclusion_count": 0,
    "deferred_count": 0,
    "required_coverage_pass": true
  },
  "findings": {
    "total": 0,
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0,
    "unknown": 0,
    "blocking_count": 0
  },
  "verification": {
    "result": "verified_pass",
    "bundle_integrity_ok": true,
    "producer_identity_ok": true,
    "subject_binding_ok": true,
    "run_binding_ok": true,
    "recipe_binding_ok": true,
    "coverage_complete": true,
    "findings_document_valid": true
  },
  "policy_evaluation": {
    "policy_id": "<id>",
    "policy_version": "<version>",
    "policy_sha256": "<sha256>",
    "findings_policy_pass": true,
    "reason_codes": []
  },
  "authority": {
    "mode": "candidate_advisory",
    "release_effect": "none"
  }
}
```

The exact schema becomes normative only in the schema implementation pull
request.

### 19.2 Summary restrictions

The summary must not embed:

- complete source excerpts;
- complete attack-path narratives;
- credentials;
- access tokens;
- private workbench data;
- mutable triage state;
- generated patches;
- large raw logs.

The summary should preserve references and digests to the restricted raw
bundle.

---

## 20. Artifact locations

Raw source bundles should remain outside the repository worktree and be
uploaded as restricted workflow artifacts.

The normalized PULSEmech artifacts may use:

```text
PULSE_safe_pack_v0/artifacts/security/
├── codex_security_intake_report_v0.json
└── codex_security_summary_v0.json
```

The raw canonical files must not initially be copied into the generic:

```text
PULSE_safe_pack_v0/artifacts/external/
```

directory.

This prevents an unimplemented generic wildcard path from treating a new
security source as a recognized detector merely because its filename ends in:

```text
_summary.json
```

A dedicated fold-in must exist before the normalized summary can affect
`status.json`.

---

## 21. Candidate gate design

The proposed inactive gate-set identity is:

```text
codex_security_recorded_intake_candidate
```

The proposed gate members are:

```text
codex_security_evidence_present
codex_security_bundle_integrity_ok
codex_security_producer_identity_ok
codex_security_subject_binding_ok
codex_security_run_binding_ok
codex_security_recipe_binding_ok
codex_security_coverage_complete
codex_security_findings_policy_pass
codex_security_intake_verified
```

### 21.1 Gate semantics

#### `codex_security_evidence_present`

Literal `true` only when every required source-bundle component exists as a
regular non-symlink file.

#### `codex_security_bundle_integrity_ok`

Literal `true` only when every expected digest, manifest artifact relation, and
bundle identity passes.

#### `codex_security_producer_identity_ok`

Literal `true` only when package, plugin, runtime, model, and reasoning effort
match the independently declared expectation.

#### `codex_security_subject_binding_ok`

Literal `true` only when the canonical target is the exact expected repository
revision.

#### `codex_security_run_binding_ok`

Literal `true` only when the producer receipt belongs to the expected current
workflow run and attempt.

#### `codex_security_recipe_binding_ok`

Literal `true` only when target kind, mode, inventory strategy, include paths,
and exclude paths match the declared recipe.

#### `codex_security_coverage_complete`

Literal `true` only when required coverage is complete, required surfaces are
resolved, exclusions are approved, and no required work is deferred.

#### `codex_security_findings_policy_pass`

Literal `true` only when the canonical findings document passes the declared
blocking-severity policy.

#### `codex_security_intake_verified`

Literal `true` when the source evidence is structurally valid, attributable,
subject-bound, run-bound, and deterministically evaluated.

A valid bundle containing a blocking finding may have:

```text
codex_security_intake_verified = true
codex_security_findings_policy_pass = false
```

This preserves the distinction between:

```text
invalid evidence
```

and:

```text
valid evidence proving a blocking security state
```

### 21.2 Candidate-set boundary

The candidate set must not appear in:

- `core_required`;
- `required`;
- `release_required`;
- production blocking sets;
- stage blocking sets;
- tag-release required sets.

Tests must prove that the candidate set remains inactive.

Promotion requires a separate pull request.

---

## 22. Status fold-in boundary

The initial design does not select a final `status.json` namespace.

The later fold-in pull request must create a dedicated mapping.

It must not reduce the evidence to one generic scalar.

The folded state must preserve at least:

- evidence presence;
- bundle integrity;
- producer identity;
- subject binding;
- run binding;
- recipe binding;
- coverage completeness;
- finding counts;
- blocking finding count;
- intake verification result;
- findings-policy result;
- reason codes;
- source-bundle identity.

The fold-in must be deterministic.

The fold-in must not parse readable reports.

The fold-in must not accept unknown fields as success.

The fold-in must not create a literal passing gate from the absence of known
failures.

---

## 23. CLI exit-code boundary

The producer process exit code must be recorded.

It must not be treated as the PULSEmech gate result.

The lane distinguishes:

```text
process completed
canonical bundle completed
canonical bundle verified
coverage complete
findings policy passed
```

A report-only scan may complete while containing high-severity findings.

A runtime or incomplete-coverage failure may produce partial output.

Therefore:

```text
exit code 0
```

does not prove:

```text
codex_security_findings_policy_pass = true
```

and:

```text
output files exist
```

does not prove:

```text
codex_security_intake_verified = true
```

---

## 24. Findings transition boundary

Codex Security may support comparison of findings across scans.

The initial authority lane must not depend on mutable comparison state.

The v0 lane evaluates one current, exact-revision source bundle.

A later transition design may represent:

```text
new
persisting
reopened
resolved
unknown
```

That later design must preserve this rule:

```text
a finding missing from a later incomplete scan is not proven resolved
```

Cross-scan comparison requires:

- both source bundles;
- both exact subject identities;
- both coverage states;
- deterministic matching evidence;
- explicit handling of ambiguous matches;
- a separate transition artifact;
- a separate verifier;
- a separate promotion boundary.

---

## 25. Public and private artifact boundary

Raw Codex Security findings may contain:

- source excerpts;
- vulnerable locations;
- attack paths;
- reproduction details;
- internal architecture details;
- remediation details.

The raw source bundle should remain a restricted workflow artifact.

The repository may retain only a sanitized normalized summary and immutable
digests unless a separate publication review permits more.

Public artifacts must not expose:

- secrets;
- live credentials;
- private source;
- exploitable unpatched details;
- sensitive runner paths;
- unrelated environment metadata.

The public summary may expose:

- subject revision;
- producer identity;
- source-bundle digests;
- coverage state;
- severity counts;
- policy result;
- verification result;
- reason codes that do not disclose exploit details.

---

## 26. Failure matrix

| Condition | Evidence state | Candidate result |
|---|---|---|
| All files absent | Not present | False |
| One canonical file missing | Unverified | False |
| Empty canonical file | Unverified | False |
| JSON parse failure | Unverified | False |
| Schema mismatch | Unverified | False |
| Manifest not completed | Unverified | False |
| Findings digest mismatch | Unverified | False |
| Coverage digest mismatch | Unverified | False |
| Bundle identity mismatch | Unverified | False |
| Symlinked input | Unverified | False |
| Path escapes staging root | Unverified | False |
| Producer package mismatch | Unverified | False |
| Plugin version mismatch | Unverified | False |
| Model mismatch | Unverified | False |
| Reasoning-effort mismatch | Unverified | False |
| Wrong repository | Unverified | False |
| Wrong revision | Unverified | False |
| Previous workflow run | Unverified | False |
| Wrong scan mode | Unverified | False |
| Wrong include paths | Unverified | False |
| Extra exclusion | Unverified | False |
| Coverage `partial` | Unverified | False |
| Coverage `unknown` | Unverified | False |
| Deferred required work | Unverified | False |
| Valid complete scan with critical finding | Verified block | False |
| Valid complete scan with high finding | Verified block | False |
| Valid complete scan with medium finding only | Verified pass under initial policy | True |
| Valid complete scan with low finding only | Verified pass under initial policy | True |
| Valid complete scan with no findings | Verified pass | True |
| No findings with incomplete coverage | Unverified | False |
| Process exit zero with malformed bundle | Unverified | False |
| Readable report says pass but canonical finding blocks | Verified block | False |
| SARIF omits canonical high finding | Verified block | False |

The candidate result in this table has no release effect before promotion.

---

## 27. Required tests

### 27.1 Schema tests

Tests must cover:

- valid source-bundle index;
- valid producer receipt;
- valid intake packet;
- valid intake report;
- valid normalized summary;
- required-field omission;
- unsupported schema version;
- wrong document type;
- invalid digest shape;
- invalid path shape;
- invalid Git revision shape.

### 27.2 Filesystem tests

Tests must cover:

- regular files;
- symlink rejection;
- path traversal;
- absolute paths;
- duplicate resolved paths;
- missing files;
- empty files;
- oversized files;
- replacement after index construction.

### 27.3 Bundle-integrity tests

Tests must cover:

- correct component digests;
- modified manifest;
- modified findings;
- modified coverage;
- modified producer receipt;
- incorrect bundle identity;
- duplicate manifest artifact records;
- missing findings artifact record;
- missing coverage artifact record.

### 27.4 Cross-document tests

Tests must cover:

- matching scan identifiers;
- findings scan-ID mismatch;
- coverage scan-ID mismatch;
- receipt scan-ID mismatch;
- wrong findings reference;
- wrong coverage reference.

### 27.5 Subject-binding tests

Tests must cover:

- exact revision match;
- previous revision;
- shortened revision;
- branch name used as revision;
- missing revision;
- different repository;
- `git_worktree` rejected for candidate lane;
- `git_diff` rejected for candidate lane;
- `directory_snapshot` rejected for candidate lane.

### 27.6 Producer-binding tests

Tests must cover:

- exact package match;
- package mismatch;
- lock-digest mismatch;
- plugin mismatch;
- runtime mismatch;
- model mismatch;
- reasoning-effort mismatch;
- missing producer field.

### 27.7 Run-binding tests

Tests must cover:

- exact current run;
- previous run identifier;
- wrong run attempt;
- wrong workflow name;
- wrong event;
- wrong ref;
- wrong Git SHA.

### 27.8 Coverage tests

Tests must cover:

- complete repository coverage;
- partial coverage;
- unknown coverage;
- unexpected inventory strategy;
- extra exclusion;
- missing declared exclusion;
- deferred unit;
- unresolved required surface;
- include-path mismatch;
- exclude-path mismatch.

### 27.9 Findings-policy tests

Tests must cover:

- zero findings;
- critical finding;
- high finding;
- medium finding;
- low finding;
- mixed severities;
- missing severity;
- unknown severity;
- duplicate finding identity;
- malformed finding;
- low-confidence high finding;
- report projection contradicting canonical findings;
- SARIF projection contradicting canonical findings.

### 27.10 Deterministic replay tests

The same fixed source bundle, packet, policy, and verifier must produce:

- byte-identical machine result where timestamps are input-bound;
- identical reason codes;
- identical gate values;
- identical finding counts;
- identical source-bundle identity.

### 27.11 Activation-guard tests

Tests must prove that:

- the candidate set is registered only as candidate;
- it is absent from all active required sets;
- no workflow makes it a required check;
- no release decision reads it as active authority;
- no generic external summary path implicitly promotes it.

---

## 28. Initial fixtures

The implementation should include fixed synthetic fixtures.

### Positive fixture

```text
exact Git revision
valid completed manifest
valid findings document
valid complete coverage
zero critical findings
zero high findings
matching producer receipt
matching intake packet
```

Expected result:

```text
verified_pass
all candidate gates true
authority effect none
```

### Blocking fixture

```text
exact Git revision
valid completed manifest
valid complete coverage
one high-severity finding
matching producer receipt
matching intake packet
```

Expected result:

```text
verified_block
integrity and binding gates true
findings-policy gate false
authority effect none
```

### Unverified fixture

```text
valid-looking bundle
manifest revision differs from expected revision
```

Expected result:

```text
unverified
subject-binding gate false
candidate set not satisfied
authority effect none
```

### Coverage-collapse fixture

```text
zero findings
coverage completeness partial
```

Expected result:

```text
unverified
coverage gate false
findings absence does not create pass
```

---

## 29. Candidate policy

A separate candidate policy file should be introduced during implementation.

Proposed path:

```text
policies/security/codex_security_candidate_policy_v0.yml
```

Proposed conceptual structure:

```yaml
policy:
  id: pulsemech_codex_security_candidate_policy
  version: "0.1"

producer:
  package_name: "@openai/codex-security"
  package_version: "<exact>"
  package_lock_sha256: "<sha256>"
  plugin_name: "<exact>"
  plugin_version: "<exact>"
  runtime_version: "<exact>"
  model: "<exact>"
  reasoning_effort: "<exact>"

target:
  allowed_kind: git_revision
  require_full_revision: true

recipe:
  scan_mode: repository
  inventory_strategy: repository
  include_paths: []
  exclude_paths: []

coverage:
  required_completeness: complete
  allowed_explicit_exclusions: []
  deferred_allowed: false
  unresolved_required_surfaces_allowed: false

findings:
  blocking_severities:
    - critical
    - high
  unknown_severity: block
  missing_severity: block
  triage_override: unsupported

authority:
  mode: candidate_advisory
  release_effect: none
```

The policy digest must be recorded in the intake packet, intake report, and
normalized summary.

---

## 30. Workflow design

The initial workflow should be:

```text
.github/workflows/codex_security_candidate.yml
```

The first workflow must be manual.

It must not run automatically on pull requests.

It must not expose a secret to untrusted fork code.

Conceptual jobs:

```text
resolve-subject
→ codex-security-producer
→ package-source-bundle
→ verify-intake
→ build-normalized-summary
→ upload-pulsemech-summary
```

### 30.1 `resolve-subject`

Responsibilities:

- resolve the selected ref to a full commit;
- require a clean exact Git revision;
- emit expected repository identity;
- emit expected run identity;
- build the independent subject expectation.

### 30.2 `codex-security-producer`

Responsibilities:

- use an isolated checkout;
- install the pinned package;
- run the declared scan recipe;
- write state and output outside the worktree;
- create the producer receipt;
- retain the process exit code;
- never apply a patch.

### 30.3 `package-source-bundle`

Responsibilities:

- verify expected files exist;
- reject symlinks;
- calculate component digests;
- create the source-bundle index;
- calculate the bundle identity;
- upload the raw bundle as a restricted artifact.

### 30.4 `verify-intake`

Responsibilities:

- create the independently expected intake packet;
- run the pinned PULSEmech verifier;
- emit the intake report;
- fail closed on unverified evidence.

### 30.5 `build-normalized-summary`

Responsibilities:

- consume the verified intake report;
- build the sanitized summary;
- preserve source digests;
- preserve coverage and findings counts;
- record `release_effect: none`.

### 30.6 Workflow status

The candidate workflow may fail when:

- the producer fails;
- the bundle is incomplete;
- verification fails;
- blocking findings exist.

Its workflow conclusion is not a PULSEmech release decision before promotion.

---

## 31. Cost and interruption boundary

A scan may be interrupted by:

- cost limit;
- timeout;
- cancellation;
- rate limit;
- authentication failure;
- model-access failure;
- runtime error.

An interrupted scan may leave partial results.

The intake verifier must require completed canonical state.

A partial bundle is not accepted because it contains some findings.

A cost limit is an operational control.

It is not a coverage proof.

If a cost limit stops the required scan before completion:

```text
coverage requirement not established
→ evidence unverified
→ candidate result false
```

---

## 32. Package and contract upgrades

The package currently has a pre-1.0 public interface.

Every package or upstream contract upgrade must use a separate pull request.

The upgrade pull request must include:

- previous expected package version;
- new expected package version;
- previous plugin version;
- new plugin version;
- previous runtime version;
- new runtime version;
- previous vendored schema commit;
- new vendored schema commit;
- schema digest changes;
- adapter compatibility review;
- verifier compatibility review;
- positive fixture replay;
- negative fixture replay;
- candidate proof regeneration.

The workflow must never follow a floating package version.

An upgrade must not silently change the scan recipe.

---

## 33. Proposed implementation files

The implementation is expected to introduce files similar to:

```text
docs/security/
└── PULSEMECH_CODEX_SECURITY_EVIDENCE_LANE_DESIGN_v0.md

vendor/openai/codex-security/
└── <upstream-commit>/
    ├── LICENSE
    ├── SOURCE.json
    └── schemas/
        ├── scan-manifest.schema.json
        ├── findings.schema.json
        └── coverage.schema.json

policies/security/
└── codex_security_candidate_policy_v0.yml

schemas/security/
├── codex_security_producer_receipt_v0.schema.json
├── codex_security_source_bundle_index_v0.schema.json
├── codex_security_intake_packet_v0.schema.json
├── codex_security_intake_report_v0.schema.json
└── codex_security_summary_v0.schema.json

tools/
├── build_codex_security_source_bundle_index_v0.py
├── build_codex_security_intake_packet_v0.py
├── check_codex_security_intake_packet_v0.py
└── build_codex_security_summary_v0.py

examples/security/
├── codex_security_producer_receipt_example_v0.json
├── codex_security_source_bundle_index_example_v0.json
├── codex_security_intake_packet_example_v0.json
├── codex_security_intake_report_example_v0.json
└── codex_security_summary_example_v0.json

tests/
├── test_codex_security_source_bundle_index_v0.py
├── test_codex_security_intake_packet_v0.py
├── test_codex_security_intake_verifier_v0.py
├── test_codex_security_summary_v0.py
├── test_codex_security_candidate_gate_set_v0.py
└── test_codex_security_candidate_activation_guard_v0.py

.github/workflows/
└── codex_security_candidate.yml
```

Final filenames may change only through explicit implementation review.

---

## 34. Implementation sequence

### PR 1 — Design record

Add only this document.

Authority effect:

```text
none
```

### PR 2 — Upstream contract snapshot

Add:

- upstream source record;
- license record;
- vendored schemas;
- digest checks;
- schema-source tests.

Authority effect:

```text
none
```

### PR 3 — PULSEmech carrier schemas

Add:

- producer receipt schema;
- source-bundle index schema;
- intake packet schema;
- synthetic examples;
- positive and negative schema tests.

Authority effect:

```text
none
```

### PR 4 — Intake verifier

Add:

- offline verifier;
- filesystem checks;
- bundle-integrity checks;
- cross-document checks;
- producer checks;
- subject checks;
- run checks;
- coverage checks;
- finding checks;
- reason codes;
- fixed fixtures.

Authority effect:

```text
none
```

### PR 5 — Normalized summary

Add:

- intake report schema;
- normalized summary schema;
- deterministic summary builder;
- sanitized output tests;
- replay tests.

Authority effect:

```text
none
```

### PR 6 — Inactive candidate registration

Add:

- candidate policy;
- candidate gate definitions;
- candidate gate-set registration;
- activation guards;
- proof that active required sets remain unchanged.

Authority effect:

```text
none
```

### PR 7 — Manual producer workflow

Add:

- isolated workflow;
- exact-revision target;
- pinned package installation;
- minimal permissions;
- external state and result paths;
- raw artifact upload;
- intake verification;
- normalized summary upload.

Authority effect:

```text
none
```

### PR 8 — Fixed-source candidate proof

Record:

- exact repository revision;
- workflow run identity;
- producer identity;
- source-bundle identity;
- intake packet digest;
- intake report digest;
- normalized summary digest;
- expected candidate gate state;
- deterministic replay result.

Authority effect:

```text
none
```

### PR 9 — Promotion criteria

Define:

- operational stability threshold;
- package update process;
- coverage policy;
- cost policy;
- secret boundary;
- retention policy;
- required scan cadence;
- failure handling;
- exact promotion prerequisites.

Authority effect:

```text
none
```

### PR 10 — Separate promotion

Only this pull request may propose moving the candidate set into a required
release policy.

The promotion pull request must be independently reviewable.

The promotion pull request must not contain unrelated implementation work.

---

## 35. Promotion prerequisites

Promotion must not occur until all of the following are proven.

### 35.1 Producer proof

- exact package identity recorded;
- exact plugin identity recorded;
- exact runtime identity recorded;
- exact model and reasoning effort recorded;
- package lock verified;
- minimal environment established;
- no unrelated credential inheritance;
- output outside the worktree;
- no patch application.

### 35.2 Carrier proof

- every source file digest verified;
- source-bundle identity deterministic;
- source bundle replayable;
- source bundle retained for the declared period;
- raw bundle access controlled.

### 35.3 Subject proof

- exact Git revision binding;
- current workflow run binding;
- previous-run reuse rejected;
- wrong-revision fixture rejected;
- dirty-worktree substitution rejected.

### 35.4 Coverage proof

- complete required coverage;
- declared inventory strategy;
- exact include/exclude relation;
- unapproved exclusions rejected;
- deferred work rejected;
- incomplete coverage never converted into no-findings success.

### 35.5 Findings-policy proof

- critical finding blocks;
- high finding blocks;
- medium and low findings remain visible;
- unknown severity blocks;
- malformed finding blocks;
- readable projections cannot override canonical findings.

### 35.6 Determinism proof

- fixed bundle replay;
- fixed policy replay;
- fixed verifier replay;
- identical gate output;
- identical reason-code output;
- no live network dependency in verification.

### 35.7 Authority proof

- only declared materialized gates affect release;
- candidate set inactive before promotion;
- no alternate release path;
- no scanner exit code used as release authority;
- no workflow name used as release authority;
- no report text used as release authority;
- `check_gates.py` remains the strict final evaluator.

---

## 36. Acceptance criteria for the completed candidate lane

The candidate lane is complete only when:

```text
1. A real Codex Security scan runs against an exact repository revision.

2. The scan produces the three canonical JSON documents.

3. The producer wrapper records its independently reviewable identity.

4. The source bundle is indexed and digest-bound.

5. The intake packet supplies expectations independently of the source bundle.

6. The verifier rejects stale, mismatched, malformed, partial, and substituted
   evidence.

7. The verifier distinguishes valid blocking evidence from invalid evidence.

8. The normalized summary preserves subject, producer, coverage, findings,
   policy, and source-bundle identities.

9. The candidate gate set is fully materializable.

10. The candidate gate set remains absent from every active required set.

11. Positive, blocking, and unverified fixtures all reproduce deterministically.

12. A fixed real-run proof is recorded.

13. No raw security finding is committed to the repository without a separate
    publication review.

14. No release authority changes occur.
```

---

## 37. Final boundary

The completed relation is intended to be:

```text
Codex Security
finds and records repository security observations

PULSEmech intake
proves which producer, run, subject, recipe, and coverage produced them

PULSEmech policy
determines whether the verified findings satisfy the declared security rule

PULSEmech authority
remains the only mechanism that may convert materialized evidence into an
enforced release state
```

The security scanner does not replace PULSEmech.

PULSEmech does not replace the security scanner.

The connection between them is the verified evidence carrier.

Without that carrier:

```text
there is a scan
```

With the complete carrier and declared mapping:

```text
there is reviewable, subject-bound security evidence
```

Only a later explicit promotion may make that evidence release-required.
