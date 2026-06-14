# Kaggle Run 0 Capture Plan v0

- Status: run-capture plan
- Normative status: non-normative diagnostic plan
- Scope: first Kaggle capture smoke for diagnostic artifact production and later `hpc_evidence_bundle_v0`-compatible review

## Core statement

Kaggle Run 0 is a diagnostic capture smoke.

It does not create release authority.

It does not verify evidence.

It does not satisfy relation bindings.

It does not materialize gates.

It does not write `status.json`.

It produces reviewable, downloadable, SHA-256-bound diagnostic artifacts only.

## Core boundary

```text
Kaggle run ≠ verifier
Notebook output ≠ verified evidence
Digest match ≠ relation satisfaction
Metric score ≠ gate materialization
Packet preview ≠ release authority
Public Kaggle URL ≠ recorded evidence
Public score ≠ release authority
```

Kaggle Run 0 must not create or enable:

- `VERIFIED`;
- trusted evidence;
- verified evidence;
- `verified_artifacts`;
- `relation_bindings`;
- relation satisfaction;
- gate materialization;
- `status.json` writing;
- `release_authority_v0.json` writing;
- release-authority audit bundles;
- policy changes;
- registry changes;
- `check_gates.py` changes;
- workflow changes;
- CI allow/block changes;
- `--release-grade-materialized`;
- release authority.

## Purpose

The purpose of Kaggle Run 0 is to prove artifact capture, not scientific authority.

The run should demonstrate that a future Kaggle notebook can produce local, downloadable, SHA-256-bound diagnostic artifacts that can later be reviewed and packaged as a non-authoritative `hpc_evidence_bundle_v0`-compatible diagnostic packet.

The run is successful if it proves the capture path:

```text
Kaggle notebook
→ local diagnostic artifacts
→ SHA-256 digest records
→ hpc_evidence_bundle_v0-compatible packet preview
→ GitHub reviewable artifact packet
```

The run is not successful merely because a notebook executes.

The run is not successful because a public Kaggle URL exists.

The run is not successful because a score, metric, table, plot, or benchmark value exists.

The value of Run 0 is artifact capture and replayability.

## Pre-run checklist

Before running Kaggle Run 0, confirm each condition below.

### Diagnostic-only intent

The run is a capture smoke.

The run is not a verifier.

The run is not release authority.

The run is not a release gate.

The goal is to produce reviewable artifacts, not to authorize a release.

The run must remain outside:

- `status.json`;
- declared release policy;
- gate registry;
- workflow-effective materialized required gates;
- `check_gates.py`;
- CI allow/block behavior;
- release authority.

### Run identity

Define diagnostic run identity metadata before execution.

Required or recommended fields:

- `packet_id`;
- `packet_version`;
- `created_utc`;
- `producer`;
- `purpose`;
- `run_id`;
- `run_started_utc`;
- `run_completed_utc`;
- `run_mode`.

Recommended values:

```text
packet_version = kaggle_hpc_diagnostic_packet_v0
purpose = diagnostic reproducibility and review only
```

These fields are identity metadata only.

They do not create trust.

They do not verify evidence.

They do not create release authority.

### Code identity

Record code identity before or during the run.

Recommended fields:

- repository;
- exact 40-character Git SHA;
- optional ref;
- notebook file or path;
- notebook version metadata, if applicable.

Code identity is diagnostic metadata.

Code identity is not trusted verifier identity.

Code identity does not verify evidence.

Code identity does not satisfy relation bindings.

### Kaggle / source metadata

Record Kaggle / source metadata where applicable.

Allowed metadata-only fields:

- competition ID;
- dataset ID;
- notebook ID;
- notebook version;
- source URL;
- observed timestamp;
- producer / author metadata;
- license / terms note;
- external-state warning;
- availability / drift note.

These fields are metadata only.

They do not create trust.

They do not verify evidence.

They do not satisfy relations.

They do not materialize gates.

A Kaggle public URL is not recorded evidence.

A public score is not release authority.

A screenshot is not artifact-bound evidence.

### Local artifact capture

Every artifact that is meant to be diagnostic evidence must be generated or downloaded locally and SHA-256-bound.

External URLs alone are not sufficient.

Notebook success alone is not sufficient.

Screenshots alone are not sufficient.

Mutable Kaggle state must be marked as external / unavailable / unverified unless locally captured and hash-bound.

### Manifest separation

The input manifest and payload artifacts must remain separated.

Required boundary:

```text
input_manifest.sha256
→ digest of the input manifest file only

payload artifact sha256
→ separate evidence_items[].sha256 or digest_manifest record
```

Dataset payloads, downloaded inputs, notebook outputs, logs, tables, plots, and packet previews must not reuse `input_manifest.sha256`.

### No authority writes

The run must not write:

- `status.json`;
- `release_authority_v0.json`;
- `verified_artifacts`;
- `relation_bindings`;
- gate materialization output;
- release decision output;
- policy files;
- registry files;
- workflow files;
- CI allow/block outputs.

The run must not invoke or replace:

- `check_gates.py`;
- release policy materialization;
- release authority builders;
- release-grade materialization paths.

## Notebook requirements

The notebook should be structured as a diagnostic capture notebook with visible non-authority boundaries.

Recommended sections:

1. Boundary / non-authority banner
2. Run identity cell
3. Code identity cell
4. Kaggle / source metadata cell
5. Environment metadata cell
6. Input manifest cell
7. Diagnostic execution cell
8. Artifact digest cell
9. Summary metrics cell
10. Reconstruction / replay instructions cell
11. Final diagnostic packet preview cell

No section may run release gates, update policy, modify registry, write `status.json`, or affect CI allow/block behavior.

## 1. Boundary / non-authority banner

The first notebook cell should visibly state:

```text
This notebook and its packet outputs are diagnostic.
They do not create release authority.
They do not verify evidence.
They do not create trusted evidence or verified evidence.
They do not create VERIFIED.
They do not create verified_artifacts.
They do not create relation_bindings.
They do not satisfy relations.
They do not materialize gates.
They do not write status.json.
They do not change policy, registry, check_gates.py, workflows, CI allow/block behavior, or release authority.
All evidence_items are folded_into_status = false.
```

This text is not decorative.

It prevents the notebook from being misread as a verifier or decision engine.

## 2. Run identity cell

The run identity cell should define diagnostic run identity.

Recommended fields:

- `packet_id`;
- `packet_version`;
- `packet_created_utc`;
- `producer`;
- `purpose`;
- `run_id`;
- `run_mode`;
- `run_started_utc`;
- `run_completed_utc`.

For Kaggle Run 0, the packet preview should use a run mode compatible with the existing `hpc_evidence_bundle_v0` surface.

Recommended value for Kaggle Run 0:

```text
run_identity.run_mode = compute_scale
```

The run identity cell does not create trust.

The packet ID does not create release authority.

## 3. Code identity cell

The code identity cell should record:

- repository;
- 40-character Git SHA;
- optional ref;
- notebook path;
- notebook version metadata.

Code identity is diagnostic metadata.

It does not create trusted verifier identity.

It does not verify evidence.

## 4. Kaggle / source metadata cell

The Kaggle / source metadata cell may record:

- competition ID;
- dataset ID;
- notebook ID;
- notebook version;
- source URL;
- observed timestamp;
- producer / author metadata;
- license / terms note;
- external-state warning;
- availability / drift note.

These fields must remain metadata-only.

They should be nested under an existing diagnostic object, such as:

```text
input_manifest.kaggle
```

Do not add new top-level schema fields for Kaggle-specific metadata in current v0.

## 5. Environment metadata cell

The environment metadata cell should record:

- runtime environment;
- Python version;
- package versions;
- hardware / accelerator class;
- notebook execution path;
- seed / determinism note;
- external-state note.

For Kaggle Run 0, the packet preview should use a runtime surface compatible with the existing `hpc_evidence_bundle_v0` surface.

Recommended value for Kaggle Run 0:

```text
environment.runtime_surface = compute_scale
```

Runtime metadata is not a trusted verifier.

Accelerator class is not release authority.

Notebook execution success is not verified evidence.

## 6. Input manifest cell

The input manifest cell should create or display a local `input_manifest.json`.

The input manifest should describe diagnostic input structure only.

Required boundary:

```text
input_manifest.sha256 = SHA-256 of input_manifest.json only
```

The input manifest may contain:

- schema;
- dataset identity;
- sample identity;
- source dataset reference;
- local artifact list;
- external-state warning;
- notes.

It must not store payload artifact digests in `input_manifest.sha256`.

## 7. Diagnostic execution cell

The diagnostic execution cell may run only diagnostic computations.

Allowed outputs:

- local diagnostic JSON;
- local diagnostic CSV;
- raw trace logs;
- generated tables;
- generated plots;
- metric summaries;
- environment metadata;
- package metadata.

Forbidden outputs:

- `status.json`;
- `release_authority_v0.json`;
- `verified_artifacts`;
- `relation_bindings`;
- gate materialization output;
- release decision output;
- policy changes;
- registry changes;
- CI allow/block output.

The diagnostic execution cell must not run or replace `check_gates.py`.

It must not update declared policy.

It must not update the gate registry.

It must not affect CI allow/block behavior.

## 8. Artifact digest cell

The artifact digest cell should compute SHA-256 values for every present generated or captured local artifact.

Required digest records:

- SHA-256 of the input manifest file;
- SHA-256 of each present downloaded input payload;
- SHA-256 of each present notebook-generated output artifact;
- SHA-256 of each present raw log;
- SHA-256 of each present generated table;
- SHA-256 of each present generated plot;
- SHA-256 of the diagnostic packet preview, if written.

Payload artifact digests should map to separate records such as:

```text
evidence_items[].path
evidence_items[].sha256
evidence_items[].role
evidence_items[].evidence_status
evidence_items[].folded_into_status = false
```

Every emitted `hpc_evidence_bundle_v0` evidence item must include `folded_into_status`.

For Kaggle Run 0, every evidence item must remain:

```text
folded_into_status = false
```

Digest match does not verify evidence.

Digest match does not create trusted evidence.

Digest match does not satisfy relation bindings.

Digest match does not materialize gates.

## 9. Summary metrics cell

The summary metrics cell may emit descriptive diagnostic metrics.

Allowed examples:

- artifact count;
- row count;
- warning count;
- runtime duration;
- reproducibility flag;
- diagnostic score;
- benchmark value;
- `kaggle_run_performed`;
- `hpc_run_performed`.

Metrics are descriptive.

Metric thresholds are diagnostic unless a later declared policy promotes them into workflow-effective materialized required gates and strict fail-closed CI enforcement.

A metric threshold is not a declared gate by itself.

A score is not release authority.

A benchmark success does not materialize `detectors_materialized_ok`.

## 10. Reconstruction / replay instructions cell

The notebook should include reconstruction / replay instructions.

Recommended content:

- notebook replay steps;
- command or cell-order instructions;
- environment reconstruction notes;
- input acquisition notes;
- expected input manifest path;
- expected input manifest SHA-256;
- expected payload artifact paths;
- expected payload artifact SHA-256 values;
- expected output files;
- nondeterminism caveats;
- external-state caveats.

Replayable output is not a verified relation.

A reproducibility packet is not release authority.

Reproducibility supports review.

It does not replace the artifact-bound PULSEmech release-authority path.

## 11. Final diagnostic packet preview cell

The notebook may assemble a local preview object shaped like `hpc_evidence_bundle_v0`.

If emitted, the preview must use:

```text
schema = hpc_evidence_bundle_v0
authority_status = diagnostic_non_normative
creates_release_authority = false
```

For Kaggle Run 0, the preview should use:

```text
run_identity.run_mode = compute_scale
environment.runtime_surface = compute_scale
```

Every evidence item must include:

```text
evidence_status = present
folded_into_status = false
sha256 = actual SHA-256
```

Every evidence item must omit:

```text
policy_route
```

The packet preview is diagnostic.

The packet preview does not create release authority.

The packet preview must not be written as `status.json`.

The packet preview must not be used as gate materialization.

The packet preview must not be used as relation satisfaction.

## Required output directory

Kaggle Run 0 should produce a local downloadable artifact directory.

Recommended directory shape:

```text
kaggle_run_0_capture/
  input_manifest.json
  diagnostic_output.json
  diagnostic_log.txt
  environment.json
  digest_manifest.json
  reconstruction_instructions.md
  hpc_evidence_bundle_preview.json
```

Optional artifacts, if produced:

```text
kaggle_run_0_capture/
  diagnostic_table.csv
  diagnostic_plot.png
  package_versions.txt
```

Do not include credentials.

Do not include Kaggle API tokens.

Do not include secrets.

Do not include `kaggle.json`.

## Required output artifacts

### `input_manifest.json`

Local manifest describing the diagnostic input structure.

Its digest is recorded in:

```text
hpc_evidence_bundle_preview.json.input_manifest.sha256
```

That digest must be only the digest of `input_manifest.json`.

### `diagnostic_output.json`

Machine-readable run summary.

Should include diagnostic-only result fields and warnings.

May include descriptive metrics.

Must not claim verification, relation satisfaction, gate materialization, or release authority.

### `diagnostic_log.txt`

Raw log text, execution transcript, or notebook-run note.

Must be SHA-256-bound as a separate artifact.

Must not contain secrets or credentials.

### `environment.json`

Runtime and package metadata.

May include:

- runtime surface;
- Python version;
- package versions;
- accelerator class;
- seed;
- determinism note;
- external-state note.

Environment metadata is not a trusted verifier.

### `digest_manifest.json`

Lists every emitted local artifact path and SHA-256 digest.

Must not self-hash.

That means it must not include an entry for:

```text
digest_manifest.json
```

### `reconstruction_instructions.md`

Replay and review instructions.

Must identify expected files and hashes.

Must include nondeterminism and external-state caveats.

### `hpc_evidence_bundle_preview.json`

Diagnostic packet preview compatible with `hpc_evidence_bundle_v0`.

It is not release authority.

It must pass the existing `hpc_evidence_bundle_v0` contract checker if committed to the repository.

## Required SHA-256 records

Run 0 must record SHA-256 values for:

1. the local input manifest file;
2. each present downloaded input payload;
3. each notebook-generated output artifact;
4. each raw log;
5. each generated table;
6. each generated plot;
7. the diagnostic packet preview, if written.

Required digest boundary:

```text
input_manifest.sha256
→ digest of the input manifest file only

payload artifact sha256
→ separate evidence_items[].sha256 or digest_manifest record
```

Dataset payload digests must not be stored in `input_manifest.sha256`.

Notebook output digests must not be stored in `input_manifest.sha256`.

Log digests must not be stored in `input_manifest.sha256`.

Plot and table digests must not be stored in `input_manifest.sha256`.

## Required `hpc_evidence_bundle_v0` preview fields

If Run 0 emits a packet preview, it should include these required top-level schema fields:

- `schema`;
- `authority_status`;
- `creates_release_authority`;
- `run_identity`;
- `code_identity`;
- `input_manifest`;
- `environment`;
- `evidence_items`;
- `summary_metrics`;
- `provenance`;
- `reconstruction`;
- `result`.

Required constant values:

```json
{
  "schema": "hpc_evidence_bundle_v0",
  "authority_status": "diagnostic_non_normative",
  "creates_release_authority": false
}
```

Recommended Kaggle Run 0 runtime values:

```json
{
  "run_identity": {
    "run_mode": "compute_scale"
  },
  "environment": {
    "runtime_surface": "compute_scale"
  }
}
```

Each evidence item should include:

```text
path
role
evidence_status = present
sha256
folded_into_status = false
```

The preview must not include:

- `verified_artifacts`;
- `relation_bindings`;
- `status`;
- `status_json`;
- `release_authority`;
- `release_authority_v0`;
- `gate_materialization`;
- `policy_route`.

The required key `creates_release_authority` is allowed only if its value is `false`.

## Metadata-only Kaggle fields

The following Kaggle fields may be captured, but must remain metadata-only:

- competition ID;
- dataset ID;
- notebook ID;
- notebook version;
- source URL;
- observed timestamp;
- producer / author metadata;
- license / terms note;
- external-state warning;
- notebook execution path;
- availability / drift note.

These fields do not create trust.

These fields do not verify evidence.

These fields do not satisfy relations.

These fields do not materialize gates.

They should remain nested diagnostic metadata.

They should not become new top-level schema fields in current v0.

## Forbidden outputs

Kaggle Run 0 must not produce:

```text
status.json
release_authority_v0.json
release-authority audit bundle
verified_artifacts
relation_bindings
gate_materialization
release decision output
policy changes
registry changes
check_gates.py changes
CI allow/block changes
required gate additions
--release-grade-materialized
```

## Forbidden claims

The notebook, logs, packet preview, README, PR, and artifacts must not claim:

```text
Kaggle Run 0 verified evidence.
Notebook output is verified evidence.
Digest match satisfies relations.
Metric score materializes a gate.
Packet preview creates release authority.
Public Kaggle URL is evidence by itself.
Public score is release authority.
Benchmark success materializes detectors_materialized_ok.
```

The following unsafe transitions are out of scope:

```text
Kaggle notebook → verified_artifact
HPC bundle → relation_binding
benchmark success → detector_materialized_ok
external run → trusted verifier
public result → release gate
```

## Post-run GitHub PR shape

A post-run PR should be diagnostic-only.

It must not alter release authority.

Recommended title style:

```text
test(ref): add Kaggle Run 0 diagnostic capture artifacts v0
```

Avoid terms such as:

```text
verified
gate pass
release pass
authority
trusted evidence
```

unless they appear only inside explicit non-authority prose.

## Post-run PR summary

The PR summary should state:

```text
This PR adds non-authoritative Kaggle Run 0 diagnostic capture artifacts.

The outputs are review / reproducibility artifacts only.

The packet preview is hpc_evidence_bundle_v0-compatible only as a diagnostic surface.

Kaggle Run 0 is not a verifier, not verified evidence, not relation satisfaction, not gate materialization, and not release authority.
```

## Post-run artifact list

A post-run PR should list local artifact paths:

- input manifest;
- diagnostic output JSON / CSV;
- raw log;
- environment metadata;
- digest manifest;
- reconstruction instructions;
- packet preview, if emitted;
- plots / tables, if emitted.

## Post-run SHA-256 records

The PR should reference or include the digest manifest.

The PR should explicitly state:

```text
input_manifest.sha256 is the digest of the input manifest file only.
```

The PR should explicitly state:

```text
payload artifacts have separate digests.
```

## Post-run checks

A post-run artifact PR should include expected checks.

If a packet preview is committed, it should pass:

```bash
python scripts/check_hpc_evidence_bundle_v0_contract.py \
  --in <path-to-hpc_evidence_bundle_preview.json>
```

A reviewer should compute and compare SHA-256 values for every present artifact.

A reviewer should confirm no forbidden authority artifacts exist.

## Minimal validation checklist

For a real Run 0 artifact PR, the minimal check list is:

1. Digest generation / check
2. Manifest boundary check
3. Packet schema / contract check
4. Non-authority field check
5. Forbidden-surface scan
6. Replay / readability check

## 1. Digest generation / check

Compute SHA-256 for every local artifact.

Confirm the digest manifest matches files on disk.

Confirm the digest manifest does not self-hash.

## 2. Manifest boundary check

Confirm:

```text
input_manifest.sha256
= SHA-256 of input_manifest.json only
```

Confirm dataset payloads, notebook outputs, logs, tables, plots, and packet previews have separate SHA-256 records.

## 3. Packet schema / contract check

If `hpc_evidence_bundle_preview.json` is committed, run the existing contract checker.

Required constants:

```text
schema = hpc_evidence_bundle_v0
authority_status = diagnostic_non_normative
creates_release_authority = false
```

For Kaggle Run 0, expected runtime values:

```text
run_identity.run_mode = compute_scale
environment.runtime_surface = compute_scale
```

Every evidence item:

```text
folded_into_status = false
```

## 4. Non-authority field check

Confirm the packet preview does not include forbidden authority keys:

- `verified_artifacts`;
- `relation_bindings`;
- `status`;
- `status_json`;
- `release_authority`;
- `release_authority_v0`;
- `gate_materialization`;
- `policy_route`.

The key `creates_release_authority` is allowed only if it is present and false.

## 5. Forbidden-surface scan

Confirm the PR does not add or modify:

- `status.json`;
- `release_authority_v0.json`;
- gate registry;
- policy files;
- workflows;
- `check_gates.py`;
- release decision outputs;
- verified artifact outputs;
- relation binding outputs;
- gate materialization outputs.

## 6. Replay / readability check

Confirm reconstruction instructions exist.

Confirm expected files and hashes are listed.

Confirm nondeterminism and external-state caveats are present.

Confirm Kaggle metadata remains metadata-only.

## Authority boundary

Kaggle Run 0 does not change the PULSEmech authority path.

The PULSEmech release-authority path remains:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ CI allow/block release decision
```

Kaggle Run 0 can later become release-relevant only if a future, separately reviewed path records, binds, checks, policy-routes, materializes, and enforces its evidence through strict fail-closed CI.

Until that future path exists, Run 0 remains diagnostic.

## Non-goals

This capture plan does not add:

- a Kaggle run;
- Kaggle credentials;
- Kaggle dataset downloads;
- notebook execution;
- artifact files;
- a schema change;
- a builder change;
- a checker change;
- a workflow change;
- a policy change;
- a registry change;
- a release-authority path.

This capture plan does not create or enable:

- `VERIFIED`;
- trusted evidence;
- verified evidence;
- `verified_artifacts`;
- `relation_bindings`;
- relation satisfaction;
- gate materialization;
- `status.json` writing;
- release authority.

## Recommended staged order

```text
1. Kaggle Run 0 capture plan
2. Kaggle Run 0 notebook preparation
3. Kaggle Run 0 execution
4. artifact download
5. digest verification
6. hpc_evidence_bundle_v0 preview validation
7. diagnostic artifact PR
8. optional later candidate-evidence reference
```

The Kaggle run should not be treated as a verifier.

The artifact packet should remain non-authoritative.

The packet preview should remain folded out of status by default.

## Mechanical anchor

```text
Kaggle run
→ artifact

artifact
→ SHA-256-bound diagnostic packet

diagnostic packet
→ review surface

review surface
≠ release authority
```

A Kaggle run can make an external computation reviewable.

It cannot make an external computation release-authoritative.

Current v0 accepts diagnostic visibility only.

Current v0 does not accept release authority from Kaggle material.
