# Release reference external-evidence integration v1

## Purpose

This document defines the current PULSE release-grade external-evidence integration path.

It covers the transition from current-run external detector evidence to verifier-admitted release-required gate state.

The implemented mechanical path is:

```text
current-run raw external evidence
→ canonical external summary
→ detector-specific semantic validation
→ canonical external-summary envelope
→ exact signer-policy admission
→ cryptographic GitHub attestation verification
→ canonical recorded-release candidate production
→ canonical candidate replay
→ recorded release-evidence verification
→ canonical verifier replay
→ policy-derived release-required gate materialization
→ final status.json
→ workflow-effective materialized required gate set
→ PULSE_safe_pack_v0/tools/check_gates.py
→ primary CI allow/block release decision
```

External evidence is not trusted because a file exists, a metric passes, a digest is written, an envelope says `verified`, or a signer identity is declared.

Release-grade external evidence becomes admissible only after the complete implemented verification path succeeds.

## Status

- canonical external-summary schema: implemented
- canonical external-summary envelope schema: implemented
- release-grade signer-policy contract: implemented
- duplicate JSON-key rejection: implemented
- duplicate YAML-key rejection: implemented
- canonical path and non-symlink checks: implemented
- summary-to-envelope digest binding: implemented
- summary/envelope identity consistency: implemented
- exact release-grade signer matching: implemented
- wildcard release-grade signer rejection: implemented
- GitHub attestation verification backend: implemented
- current verifier backend: `github-attestation`
- canonical candidate-builder integration: implemented
- recorded-verifier replay integration: implemented
- verifier-bound release-required materialization: implemented
- exact checked-in operational signer identity: pending
- current-run external-evidence producer lane: pending
- first completed public attested release-grade run: pending

Primary implementation surfaces:

```text
schemas/external_summary_v1.schema.json
schemas/external_summary_envelope_v1.schema.json
policy/external_signers_v1.yml
PULSE_safe_pack_v0/profiles/external_thresholds.yaml

PULSE_safe_pack_v0/tools/check_external_summary_attestation_v1.py
PULSE_safe_pack_v0/tools/build_recorded_release_candidates_v0.py
PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py
PULSE_safe_pack_v0/tools/materialize_release_required_from_verifier_v0.py
PULSE_safe_pack_v0/tools/check_gates.py
```

## Authority boundary

External-evidence validation is an evidence-admission layer.

It is not an independent release-decision engine.

The following do not independently create release authority:

- raw external evidence;
- external summaries;
- external-summary envelopes;
- signer-policy entries;
- signing identities;
- attestation bundles;
- attestation-verifier reports;
- candidate envelopes;
- recorded-verifier reports;
- admissibility maps;
- manifests;
- Quality Ledger;
- audit bundles;
- dashboards;
- Pages;
- publication surfaces.

The normative release path remains:

```text
recorded release evidence
→ final status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ PULSE_safe_pack_v0/tools/check_gates.py
→ primary CI workflow
→ primary CI allow/block release decision
```

Therefore:

```text
external evidence verified
≠ release authorized
```

and:

```text
external evidence admitted
≠ final gate enforcement completed
```

## Mechanical separation

The external-evidence path contains distinct layers.

```text
external-summary schema validation
= structural contract validation

detector-specific semantic validation
= metric, threshold, run, subject, result, and raw-evidence checks

external-summary attestation verification
= envelope, signer, digest, workflow, source, and cryptographic verification

recorded candidate production
= verifier-facing external-evidence candidate construction

recorded release-evidence verifier
= candidate replay, relation verification, and per-entry admissibility

release-required materializer
= complete policy-derived gate coverage and status materialization

PULSE_safe_pack_v0/tools/check_gates.py
= strict final gate enforcement
```

No earlier layer replaces a later layer.

---

## Canonical external-summary contract

Canonical schema:

```text
schemas/external_summary_v1.schema.json
```

A release-grade external summary must be a valid JSON object.

The implemented cryptographic candidate path requires a canonical:

```text
*_summary.json
```

file.

A JSONL summary may still be discovered by lower-level summary handling, but the current release-grade attestation path requires a canonical JSON summary.

Therefore:

```text
JSONL summary discovered
≠ release-grade attestation eligible
```

The summary must remain inside:

```text
PULSE_safe_pack_v0/artifacts/external/
```

It must be:

- a regular file;
- non-symlink;
- valid finite JSON;
- free of duplicate object keys;
- valid under `external_summary_v1`.

## External-summary structural fields

The canonical schema records the applicable:

- schema version;
- summary ID;
- tool name;
- tool version;
- run identity;
- model or release-candidate identity;
- dataset digest;
- evaluator digest;
- subject kind;
- subject ID;
- subject digest;
- metric list;
- threshold reference;
- evidence reference;
- raw-evidence digest;
- signing context;
- aggregate result;
- release contribution;
- authority-boundary statement.

Schema validity is required.

Schema validity alone is not sufficient for release-grade admission.

Therefore:

```text
schema valid
≠ semantic pass
```

---

## Detector-specific semantic validation

Detector-specific semantic validation occurs during canonical recorded-candidate production.

Current supported detector IDs are:

```text
llamaguard
promptguard
garak
azure_eval
promptfoo
deepeval
```

The candidate builder discovers the canonical summary filename for each supported detector.

For one detector, both of these must not exist simultaneously:

```text
<detector>_summary.json
<detector>_summary.jsonl
```

If both exist, candidate production fails closed.

At least one supported external detector summary must be present for the external candidate path.

Every discovered summary must pass its complete applicable validation path.

## External overall policy

The current v0 candidate path requires:

```text
external_overall_policy = all
```

from:

```text
PULSE_safe_pack_v0/profiles/external_thresholds.yaml
```

This means every external summary admitted into the current candidate set must pass its applicable checks.

It does not mean that every supported detector must necessarily be present unless another declared contract requires that detector set.

Therefore:

```text
all discovered summaries must pass
≠ every known detector must exist
```

## Current-run binding

The summary must bind to the current release-grade run.

The implemented checks include:

```text
summary.run.run_id
= current PULSE run_key
```

```text
summary.run.model_id
= current release candidate
```

```text
summary.subject.kind
= release_candidate
```

```text
summary.subject.id
= current release candidate
```

The summary subject digest must bind to the current commit SHA under the declared digest algorithm.

The dataset and evaluator digests must be concrete SHA-256 values.

## Tool and detector identity

The summary tool identity must match the detector being admitted.

For example:

```text
llamaguard_summary.json
→ tool.name = llamaguard
```

A generic or substituted tool identity must fail closed.

## Metric identity and threshold binding

Every detector uses its declared canonical metric and threshold key.

The summary must preserve the applicable:

- metric key;
- metric value;
- threshold value;
- threshold comparator;
- threshold reference key;
- threshold-policy URI.

The current threshold comparator for the recorded external candidate path is:

```text
lte
```

The declared metric threshold must equal the canonical threshold loaded from:

```text
PULSE_safe_pack_v0/profiles/external_thresholds.yaml
```

The observed metric value must not exceed that canonical threshold.

Every listed metric entry must have:

```text
passed = true
```

The aggregate result must have:

```text
result.passed = true
result.release_contribution = required
```

Therefore:

```text
metric exists
≠ metric passed
```

and:

```text
aggregate result says passed
≠ canonical threshold binding verified
```

## Raw-evidence binding

The summary must reference a current raw-evidence artifact.

The raw-evidence URI must be:

- non-empty;
- repository-relative;
- contained inside the canonical external-evidence directory;
- a regular file;
- non-symlink;
- different from the summary itself.

The raw artifact must remain inside:

```text
PULSE_safe_pack_v0/artifacts/external/
```

The declared raw-evidence digest must be a concrete SHA-256 value.

The actual raw-evidence digest must equal the declared digest.

Therefore:

```text
raw-evidence path exists
≠ raw-evidence binding verified
```

---

## Canonical external-summary envelope

Canonical envelope schema:

```text
schemas/external_summary_envelope_v1.schema.json
```

The expected envelope filename is derived from the canonical summary filename.

Example:

```text
llamaguard_summary.json
→ llamaguard_summary.envelope.json
```

The envelope must:

- remain inside the canonical external-evidence directory;
- be a regular non-symlink file;
- contain valid finite JSON;
- contain no duplicate JSON object keys;
- validate under `external_summary_envelope_v1`.

## Summary reference binding

The envelope summary reference must match the wrapped summary.

Required relations include:

```text
envelope.summary_ref.uri
= canonical repository-relative summary path
```

```text
envelope.summary_ref.schema_version
= external_summary_v1
```

```text
envelope.summary_ref.summary_id
= summary.summary_id
```

A reference to another summary, another path, or another schema must fail closed.

## Summary digest binding

The envelope must declare:

```text
summary_digest.algorithm = sha256
```

The declared digest value must equal the actual SHA-256 digest of the canonical summary file.

Therefore:

```text
envelope exists
≠ envelope wraps this summary
```

The relation is established only when the reference and digest both match.

## Signing-context consistency

The signing mode and identity declared in the summary must exactly match the signing mode and identity declared in the envelope.

```text
summary.signing.mode
= envelope.signing.mode
```

```text
summary.signing.identity
= envelope.signing.identity
```

A mismatch fails closed.

## Verification and fold-in state

For release-grade admission, the envelope must declare:

```text
verification.verified = true
```

and:

```text
policy_context.fold_in_allowed = true
```

The summary and envelope must both declare:

```text
release_contribution = required
```

These declarations remain claims until the implemented verifier proves their associated schema, digest, signer, and cryptographic relations.

Therefore:

```text
verification.verified = true
≠ cryptographic verification completed
```

---

## Canonical policy references

The envelope must bind to the canonical signer policy:

```text
policy/external_signers_v1.yml
```

and the canonical threshold policy:

```text
PULSE_safe_pack_v0/profiles/external_thresholds.yaml
```

Substituted policy paths are rejected.

The current external-attestation verifier also requires the canonical:

```text
schemas/external_summary_v1.schema.json
schemas/external_summary_envelope_v1.schema.json
policy/external_signers_v1.yml
```

paths.

---

## External signer policy

Signer policy:

```text
policy/external_signers_v1.yml
```

The signer policy defines the release-grade expectations for:

- summary schema validity;
- envelope schema validity;
- summary digest presence;
- subject digest presence;
- tool identity;
- tool version;
- threshold reference;
- signer identity;
- verification before fold-in;
- unsigned evidence handling;
- unverified evidence handling;
- signing-mode eligibility;
- tool-specific identity groups;
- release-contribution eligibility.

The signer policy does not create release authority.

## Release-grade defaults

The current verifier requires the policy's release-grade requirements to remain strict.

Applicable requirements include literal-true values for:

```text
require_schema_valid_summary
require_schema_valid_envelope
require_summary_digest
require_subject_digest
require_tool_identity
require_tool_version
require_threshold_ref
require_signer_identity
require_verification_before_fold_in
```

The policy must also preserve:

```text
allow_unsigned_release_grade = false
allow_unverified_fold_in = false
```

If these policy protections are weakened, verification fails closed.

## Policy vocabulary vs implemented backend

The signer policy contains a broader signing-mode vocabulary.

The current implemented cryptographic verifier supports only:

```text
github-attestation
```

for release-grade external-evidence admission.

Other signing modes listed in policy are not implemented by the current verifier backend.

Therefore:

```text
signing mode listed in policy
≠ signing backend operationally implemented
```

## Exact signer identity

The current release-grade verifier requires an exact signer identity.

GitHub attestation identity format:

```text
repo:<owner>/<repo>:workflow:<workflow-name-or-path>
```

Example shape:

```text
repo:HKati/pulse-release-gates-0.1:workflow:.github/workflows/<exact-workflow>.yml
```

The repository encoded in the signer identity must equal the expected current repository.

The workflow identity must be a safe repository-relative workflow path.

The verifier rejects identity patterns containing:

```text
*
?
[
]
```

Therefore:

```text
wildcard signer pattern
≠ release-grade admitted signer identity
```

## Current signer-policy blocker

The checked-in signer policy currently contains deferred wildcard identity patterns.

Those entries are placeholders.

They are deliberately rejected by the implemented release-grade verifier.

They must be replaced by exact operational identities before the current-run attested external-evidence lane can pass.

An exact identity must identify the actual workflow that:

- produces or controls the external summary;
- creates the GitHub attestation;
- is permitted for the relevant detector;
- is permitted for `release_contribution = required`;
- matches the attestation certificate and verification result.

The external-review identity namespace remains empty until concrete external identities are introduced.

---

## Cryptographic GitHub attestation verification

Verifier:

```text
PULSE_safe_pack_v0/tools/check_external_summary_attestation_v1.py
```

The verifier performs fail-closed cryptographic verification before an external summary can enter canonical candidate production.

## Canonical input boundary

The verifier receives:

```text
repository root
canonical external summary
canonical external-summary envelope
canonical summary schema
canonical envelope schema
canonical signer policy
expected repository
expected source commit digest
```

The attestation bundle path is read from:

```text
envelope.signing.bundle_uri
```

The summary, envelope, and bundle must all remain inside:

```text
PULSE_safe_pack_v0/artifacts/external/
```

They must be regular non-symlink files.

## GitHub CLI verification contract

The current verifier invokes the mechanical equivalent of:

```text
gh attestation verify <summary> \
  --repo <expected-owner/repository> \
  --bundle <attestation-bundle> \
  --signer-workflow <exact-workflow> \
  --source-digest <current-40-hex-commit> \
  --predicate-type https://slsa.dev/provenance/v1 \
  --cert-oidc-issuer https://token.actions.githubusercontent.com \
  --format json
```

The verifier requires:

- the GitHub CLI to be available;
- command execution to complete;
- exit code zero;
- valid JSON output;
- a non-empty verification-result array.

The attestation must bind the summary to:

- the expected repository;
- the exact signer workflow;
- the expected source commit;
- the SLSA provenance v1 predicate type;
- the GitHub Actions OIDC issuer.

A self-declared envelope verification result does not replace this command.

## Fail-closed backend behavior

Verification fails closed when, among other conditions:

- `gh` is unavailable;
- the command times out;
- the command returns non-zero;
- the bundle is missing;
- the bundle is outside the canonical external directory;
- the bundle is a symlink;
- the signer workflow does not match;
- the expected repository does not match;
- the source digest does not match;
- the predicate type does not match;
- the OIDC issuer does not match;
- verification output is malformed;
- verification output is empty.

---

## External attestation-verifier report

The verifier produces a non-authoritative report with schema identity:

```text
external_summary_attestation_verifier_v1
```

The report records the applicable:

- status;
- summary path;
- summary digest;
- summary schema version;
- summary ID;
- envelope path;
- envelope digest;
- envelope schema version;
- envelope ID;
- signer mode;
- signer identity;
- signer repository;
- signer workflow;
- signer-policy path;
- attestation backend;
- bundle path;
- verified attestation count;
- command contract;
- errors;
- authority boundary.

Top-level report status:

```text
verified
failed
```

A verified report requires an empty error list.

The report explicitly remains:

```text
normative = false
creates_release_authority = false
materializes_status = false
materializes_release_required = false
replaces_check_gates = false
```

The CLI can write the report to a declared output path.

During canonical candidate production, the verifier function is invoked directly and its verified result is bound into the candidate-construction path.

---

## Direct verifier command

Example command shape:

```bash
python PULSE_safe_pack_v0/tools/check_external_summary_attestation_v1.py \
  --repo-root . \
  --summary PULSE_safe_pack_v0/artifacts/external/<detector>_summary.json \
  --envelope PULSE_safe_pack_v0/artifacts/external/<detector>_summary.envelope.json \
  --repository HKati/pulse-release-gates-0.1 \
  --source-digest <current-40-hex-git-sha> \
  --out PULSE_safe_pack_v0/artifacts/external/<detector>_attestation_verifier_v1.json
```

Expected successful output:

```text
OK: external summary attestation verified
Verification report written to <path>
```

Failure returns a non-zero exit code and:

```text
ERRORS (fail-closed):
 - ...
Verification report written to <path>
```

A successful direct verifier command does not itself materialize release-required gates.

---

## Canonical recorded-candidate integration

Canonical candidate builder:

```text
PULSE_safe_pack_v0/tools/build_recorded_release_candidates_v0.py
```

External-summary candidate construction occurs only after:

```text
summary schema validation
+ detector-specific semantic validation
+ raw-evidence digest verification
+ envelope validation
+ signer-policy admission
+ cryptographic GitHub attestation verification
```

The builder requires a canonical JSON summary for the release-grade attestation step.

It derives the expected envelope path from the summary filename.

It invokes the external-attestation verifier with:

- current repository identity;
- current commit identity;
- canonical schemas;
- canonical signer policy;
- canonical summary and envelope paths.

## Candidate-builder attestation checks

The candidate builder requires the returned verifier report to contain:

```text
schema_version = external_summary_attestation_verifier_v1
status = verified
errors = []
```

It also verifies that:

- report summary path matches the canonical summary;
- report summary digest matches the candidate summary digest;
- attestation summary digest matches the candidate summary digest;
- attestation backend is `gh-attestation`;
- attestation verified is literal `true`;
- envelope path matches the canonical expected envelope path;
- envelope digest matches the actual envelope;
- bundle path remains inside the external directory;
- bundle digest is concrete;
- signer identity is non-empty;
- signer workflow is non-empty;
- signer repository matches the current repository;
- signer-policy path is canonical.

A malformed or substituted verifier report cannot produce a candidate.

## External candidate output

For every fully validated external detector summary, the builder produces an external candidate envelope.

The candidate contributes evidence for:

```text
external_summaries_present
external_all_pass
```

The candidate records separate validation checks for:

- detector-specific semantic validity;
- cryptographic attestation validity.

Its recorded inputs include the applicable:

- external summary;
- raw evidence;
- external-summary envelope;
- attestation bundle;
- summary schema;
- envelope schema;
- signer policy;
- attestation verifier;
- threshold policy.

The candidate does not directly set either gate in final `status.json`.

---

## Recorded release-evidence verification

After candidate production, the recorded verifier performs canonical candidate replay.

Current verifier:

```text
PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py
```

The verifier rejects:

- missing canonical external candidates;
- extra non-canonical external candidates;
- modified candidate envelopes;
- substituted candidate envelopes;
- producer-output drift;
- summary digest drift;
- raw-evidence digest drift;
- run-identity mismatch;
- subject-binding mismatch;
- policy-binding mismatch;
- relation-binding failure;
- manifest-declared gate-admissibility failure.

The recorded verifier binds the external semantic and attestation result by replaying the same checked-in candidate producer.

Therefore:

```text
attestation report supplied
≠ attestation path trusted
```

The path is trusted only when canonical candidate replay reproduces the supplied external candidate.

---

## Relation and gate-admissibility boundary

External candidates must be connected to their target gates through verified relations.

Applicable target gates:

```text
external_summaries_present
external_all_pass
```

The verifier requires verified candidate and relation IDs for each manifest-declared gate entry.

Each supporting external candidate must have a satisfied:

```text
artifact_to_gate
```

relation targeting the exact gate.

Per-entry admissibility still does not materialize final gate state.

---

## Complete policy coverage and materialization

Materializer:

```text
PULSE_safe_pack_v0/tools/materialize_release_required_from_verifier_v0.py
```

The materializer:

- reruns the recorded verifier canonically;
- requires the supplied verifier report to match replay;
- derives the complete release-required gate set from policy;
- requires an admissible verifier entry for every policy-derived release-required gate;
- rejects pre-existing release-required gate values;
- rejects stubbed or scaffolded candidate state;
- checks run, subject, policy, and registry bindings;
- fails without partially modifying candidate state.

Only after the complete path succeeds may it write literal `true` values into:

```text
status["gates"]
```

for the policy-derived release-required gate set.

Therefore:

```text
external candidate verified
≠ external gate materialized
```

and:

```text
external gate materialized
≠ release allowed by itself
```

---

## Final external gate semantics

The final release-grade path may contain:

```text
external_summaries_present = true
external_all_pass = true
```

These values must not be interpreted as manually asserted summary state.

In the verifier-bound materialized path:

```text
external_summaries_present = true
```

means the complete policy-derived gate entry was materialized from verifier-admitted candidate evidence.

```text
external_all_pass = true
```

means the complete policy-derived gate entry was materialized from external candidates that passed their implemented semantic, digest, signer, envelope, and cryptographic verification path.

Therefore:

```text
external summary file exists
≠ external_summaries_present = true
```

and:

```text
summary metric says pass
≠ external_all_pass = true
```

Final release authority still requires strict enforcement of the complete workflow-effective gate set.

---

## Retained fixture layers

The existing fixture layers remain useful.

They validate structural and downstream fail-closed behavior.

They do not replace the current-run cryptographic admission path.

### External-summary schema fixtures

Fixture root:

```text
tests/fixtures/external_summary_v1/
```

Test:

```text
tests/test_external_summary_fixture_matrix_v1.py
```

The matrix includes structural cases such as:

- valid summary;
- missing tool version;
- missing subject digest;
- invalid SHA-256;
- empty metrics;
- missing authority boundary.

These fixtures establish schema behavior.

They do not prove runtime attestation.

### External-summary envelope fixtures

Fixture root:

```text
tests/fixtures/external_summary_envelope_v1/
```

Test:

```text
tests/test_external_summary_envelope_fixture_matrix_v1.py
```

The matrix includes:

- valid envelope;
- missing summary digest;
- missing signing identity;
- missing verifier identity;
- unverified fold-in allowed;
- unverified fold-in not allowed.

These fixtures validate the envelope schema contract.

They do not execute `gh attestation verify`.

### Release-reference failure fixtures

The release-reference matrix retains failure-isolation cases such as:

```text
malformed_summary
unsigned_summary
```

These fixtures demonstrate that selected external-evidence failures remain fail-closed in the release-reference surface.

They do not prove that a real current-run external summary was produced, signed, attested, replayed, admitted, and materialized.

Therefore:

```text
release-reference fixture passes
≠ current-run attested external-evidence lane complete
```

---

## Test coverage

Relevant tests include:

```text
tests/test_external_summary_schema_v1.py
tests/test_external_summary_fixture_matrix_v1.py
tests/test_external_summary_envelope_fixture_matrix_v1.py
tests/test_release_reference_fixture_matrix_v1.py
tests/test_check_external_summary_attestation_v1.py
tests/test_release_grade_candidate_evidence_path_v0.py
tests/test_check_recorded_release_evidence_v0.py
tests/test_materialize_release_required_from_verifier_v0.py
```

Run structural fixture tests:

```bash
python tests/test_external_summary_fixture_matrix_v1.py
python tests/test_external_summary_envelope_fixture_matrix_v1.py
python tests/test_release_reference_fixture_matrix_v1.py
```

Run the cryptographic-verifier tests:

```bash
python -m pytest -q tests/test_check_external_summary_attestation_v1.py
```

Run the candidate and recorded-verifier path tests:

```bash
python -m pytest -q \
  tests/test_release_grade_candidate_evidence_path_v0.py \
  tests/test_check_recorded_release_evidence_v0.py \
  tests/test_materialize_release_required_from_verifier_v0.py
```

Passing tests establish checked-in behavior.

They do not by themselves create the first completed public release-grade run.

---

## Failure behavior

The external-evidence path fails closed on, among other conditions:

- no supported external detector summary;
- both JSON and JSONL summaries for one detector;
- JSONL used where release-grade attestation requires JSON;
- malformed summary JSON;
- duplicate summary JSON keys;
- non-finite summary JSON values;
- summary schema failure;
- wrong detector identity;
- wrong run key;
- wrong release-candidate identity;
- wrong subject kind;
- wrong subject ID;
- wrong subject digest;
- missing dataset digest;
- missing evaluator digest;
- wrong threshold reference;
- wrong threshold URI;
- wrong comparator;
- metric threshold mismatch;
- metric value exceeding threshold;
- metric `passed` not literal true;
- aggregate `result.passed` not literal true;
- release contribution not `required`;
- raw-evidence path missing;
- raw-evidence path outside the external directory;
- raw evidence being the summary itself;
- raw-evidence symlink;
- raw-evidence digest mismatch;
- missing envelope;
- envelope outside the external directory;
- malformed envelope;
- duplicate envelope JSON keys;
- envelope schema failure;
- summary-reference mismatch;
- summary-ID mismatch;
- summary-digest mismatch;
- summary/envelope signing mismatch;
- envelope verification not literal true;
- fold-in not explicitly allowed;
- canonical policy-reference mismatch;
- unsupported release-grade signing backend;
- wildcard signer identity;
- signer identity not admitted by policy;
- signer repository mismatch;
- missing attestation bundle;
- attestation bundle outside the external directory;
- attestation bundle symlink;
- missing GitHub CLI;
- GitHub attestation verification failure;
- signer-workflow mismatch;
- source-digest mismatch;
- predicate-type mismatch;
- OIDC-issuer mismatch;
- invalid or empty verification output;
- modified external candidate;
- canonical replay mismatch;
- relation-binding failure;
- missing policy-gate admissibility;
- final strict gate-enforcement failure.

---

## Current operational gap

The verification and admission capability is implemented.

The operational current-run production lane is not yet complete.

The checked-in signer policy still contains wildcard placeholder identities.

The implemented verifier rejects those wildcards.

The current workflow does not yet provide the complete canonical sequence that:

1. runs the external evaluator from current-run inputs;
2. writes the raw evidence;
3. writes the canonical external summary;
4. uses one exact admitted workflow identity;
5. creates the GitHub attestation;
6. preserves the attestation bundle;
7. creates the canonical verification envelope;
8. passes the external-attestation verifier;
9. enters canonical candidate production;
10. survives candidate and verifier replay;
11. materializes the complete policy gate set;
12. publishes the complete reference package.

This is the next operational work.

---

## Next operational sequence

The next sequence is:

```text
exact operational workflow identity
→ current-run raw external evidence
→ canonical external summary
→ GitHub attestation bundle
→ canonical external-summary envelope
→ cryptographic verification
→ canonical external candidate
→ recorded verifier replay
→ verifier-bound materialization
→ strict final gate enforcement
→ complete release-grade package
→ completed public reference-run record
```

Required implementation steps:

1. select the exact GitHub Actions workflow responsible for release-grade external evidence;
2. replace deferred wildcard signer-policy entries with the exact workflow identity;
3. implement current-run external evaluator execution;
4. produce current-run raw evidence inside the canonical external directory;
5. produce a canonical `external_summary_v1` JSON summary;
6. create a GitHub attestation for that exact summary;
7. preserve the returned attestation bundle inside the canonical external directory;
8. produce the canonical `.envelope.json` file with matching path, digest, signer identity, bundle URI, and policy references;
9. run the external-attestation verifier;
10. run canonical recorded-candidate production;
11. build and validate the release-evidence input manifest;
12. run recorded release-evidence verification;
13. replay the verifier in the materializer;
14. materialize the complete policy-derived release-required gate set;
15. enforce the complete workflow-effective required gate set;
16. include the summary, raw evidence, envelope, bundle, candidate, manifest, verifier report, final state, decision, and provenance binding in the reference package;
17. record the completed run in:

```text
docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md
```

---

## Non-goals

This integration does not:

- make external detector output inherently trusted;
- make a schema-valid summary release authority;
- make an envelope release authority;
- make an attestation report release authority;
- accept wildcard release-grade identities;
- accept unsigned release-grade evidence;
- accept unverified release-grade fold-in;
- accept a metric pass without threshold binding;
- accept a summary without raw-evidence binding;
- accept a supplied candidate without canonical replay;
- replace the recorded release-evidence verifier;
- replace the release-required materializer;
- replace `PULSE_safe_pack_v0/tools/check_gates.py`;
- create a second release-decision engine;
- create a Quality Ledger override;
- create an independent break-glass path;
- prove that the first public release-grade run already exists.

## Minimal mechanical anchor

```text
summary exists
≠ summary verified

schema valid
≠ semantic pass

envelope says verified
≠ cryptographic verification

signer declared
≠ exact signer admitted

attestation verified
≠ candidate admitted

candidate admitted
≠ gate materialized

gate materialized
≠ release authority by itself
```

The complete path remains:

```text
current-run external evidence
→ canonical verification
→ replay-bound admission
→ policy-derived materialization
→ strict final enforcement
→ primary CI allow/block release decision
```
