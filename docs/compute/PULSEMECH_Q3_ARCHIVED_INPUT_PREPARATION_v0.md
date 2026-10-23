# Q3 archived-input preparation v0

## Scope and status

Q3-2A adds a bounded, offline preparer for the existing
[Q3 reference producer and independent checker](PULSEMECH_Q3_REFERENCE_RECOMPUTATION_v0.md).
It continues Step 5C under [#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879),
after PR #2945, using source baseline
`5250c3e2901267909096cda9b6414689cdca8330`.

The preparer validates a separate caller selection, snapshots the selected
original files, and produces a new input package. It does not acquire data,
generate labels, choose groups, score Q3, call a model, execute the producer or
checker, or activate `q3_fairness_ok`. Its tests use synthetic data only.
No accepted real Q3 dataset or actual archived-input execution is asserted here.

`PREPARED` means **the selected bytes were packaged with the documented
structural and binding checks**. It does not mean valid full Q3 semantics,
metric PASS, verified provenance, correct labels, successful model execution,
or readiness for release. Even a structurally prepared package may receive
`INVALID` from the existing producer's complete semantic checks.

## Repository files

| Role | Path |
| --- | --- |
| Offline preparer | `PULSE_safe_pack_v0/tools/prepare_q3_archived_input_bundle_v0.py` |
| Closed selection schema | `schemas/metrics/q3_archived_input_selection_v0.schema.json` |
| Synthetic regression suite | `tests/test_q3_archived_input_preparation.py` |
| Existing reference contract | `docs/compute/PULSEMECH_Q3_REFERENCE_RECOMPUTATION_v0.md` |

Only these three new implementation/test files, this document and append-only
navigation/changelog/test-registration additions belong to Q3-2A. The existing
Q3 producer, checker, profile, schemas, fixtures, metric specifications and
manifest schema are unchanged. No workflow, dispatcher, admission, policy,
registry, root README, DOI or Software Heritage change is included.

## Selection before scoring

The caller supplies `q3_archived_input_selection_v0` independently of a metric
report. There is no command that infers a trusted selection from a submitted
report or automatically chooses whichever dataset produces a positive result.

| Required field | Meaning |
| --- | --- |
| `record_type`, `selection_id`, `contract_profile` | Closed selection format and explicit selection identity. |
| `dataset_id`, `reduction_id`, `observation_subject` | The selected dataset/reduction/subject, compatible with the unchanged input-bundle contract. |
| `selection_origin.kind` | `caller_selected_archived_input` for archived input, or `synthetic_test_anchor` for a synthetic fixture. The subject kind must agree. |
| `selection_origin.basis_reference` | Caller-declared reference explaining the selection. This is not independently authenticated. |
| `selection_origin.access_use_basis` | Caller-recorded access/use basis. A nonempty string does not prove permission or complete a license review. |
| `selection_origin.selected_before_scoring` | Required `true` declaration; the preparer does not prove when a person actually selected the data. |
| `selection_origin.original_runtime_evidence_reference` | Null when original runtime identity is unavailable. Otherwise a separate reference must accompany the declared runtime identity; its content is not verified here. |
| `artifacts` | Exactly the manifest, original examples JSONL and Q1 labels JSONL: safe source-root-relative paths, selected SHA-256 and byte lengths. |
| `resource_bindings` | Exact supported profile, both existing Q3 schemas, manifest schema and canonical Q1/Q3 specification hashes. |
| `expected_producer` | Exact supported producer identity/source bytes and caller-selected Python version for the subsequent reduction. |
| `authority_effect`, `production_gate_eligible` | Fixed `none` and `false`. |

The selection schema and all six resource files are byte-pinned by the preparer.
The accepted producer source is also pinned, read as data and never imported or
executed. Coherently changing a file and its caller-selected digest cannot
change the implementation's accepted contract. Supporting revised resources or
producer bytes requires a separately reviewed preparer/profile revision.

The original archive runtime and the **future reduction runtime** are distinct.
Unknown original runtime identity remains null; it is not filled from this
machine. `expected_producer.python_version` is preserved from the caller's
selection, not silently replaced with the preparer's Python version. The
existing producer must subsequently verify that its actual runtime matches.
A non-null original runtime is marked `caller_declared_not_verified`.

The selection itself is a trust-boundary input. The tool checks its schema,
internal bindings and correspondence with the selected bytes; it does not
establish who authored it, whether its origin statements are true, or whether
its files came from the intended external source. A party able to replace the
selection and the original inputs can select different inputs. This package
must not be described as source authentication.

## Checks and deliberate limits

The tool checks strict UTF-8 JSON/JSONL, duplicate JSON keys, finite numbers,
Unicode encodability, size/row/dimension bounds, the pinned existing record
schemas, manifest structure and dates, dataset identity, original row count,
manifest-to-file hashes, unique example/label IDs, the exact ID join, the full
examples-file digest and each label's exact original example-line digest.

It does **not** compute Q1 eligibility, validate all eligibility/exclusion
relationships, verify label truth or group provenance, calculate coverage,
Wilson bounds or parity, select an acquisition stopping rule, or decide a
metric. Full semantic validation and scoring remain with the unchanged Q3
producer; independent reconstruction remains with the unchanged checker.

There is no normalization, reformatting, row deletion or repair of original
files. CRLF JSONL, absent final LF, invalid encoding and malformed records are
rejected rather than rewritten. The source files are copied as exact bytes.
`UNKNOWN` records and supplied metadata are retained; no demographic attributes
or extra slices are inferred. A format conversion requires a separate adapter
contract with preserved originals.

The existing limits remain 64 MiB per original file, 1 MiB per JSONL line,
100,000 rows and 64 dimensions. The separate selection file is limited to
128 KiB. These are rejection bounds, never silent truncation rules.

## Package and binding order

A successful destination contains exactly seven files:

```text
dataset_manifest.json
examples.jsonl
q1_labels.jsonl
input_bundle.json
expected_context.json
input_selection.json
preparation_manifest.json
```

The three originals and `input_selection.json` retain their input bytes.
Only newly constructed metadata uses sorted UTF-8 JSON, two-space indentation
and one final LF. The binding order is:

```text
caller-selected original identities and subject/resource/producer choices
    -> exact original snapshots and structural preflight
    -> existing-format input bundle
    -> existing-format expected context, including the constructed bundle hash
    -> preparation manifest, binding all six other members and selection origin
```

Computing the expected bundle digest from this construction is not a selection
from a submitted report: the original identities and all choices are already
constrained by the separate caller selection, and no report is read or created.

The preparation manifest includes member hashes/sizes, the selection identity
and origin, pinned selection schema and preparer source identity. No acquisition
timestamp is invented. Identical selections, original bytes and tool/resources
produce identical package metadata, independently of destination path.

There is no `summary.json` or checker receipt at preparation time. Successful
CLI stdout is a small preparation receipt containing the manifest and selection
SHA-256 values. Retain that receipt separately from the package where custody
requirements call for an external reference.

## Filesystem and failure contract

This implementation requires Linux, safe directory-descriptor operations,
no-symlink file opens and `renameat2` with `RENAME_NOREPLACE` supported by the
runtime and destination filesystem. Unsupported facilities fail closed; there
is no replace/overwrite fallback. The existing `jsonschema` dependency is used;
no new third-party runtime dependency is introduced.

Every original is read as a bounded regular-file snapshot. Device/inode identity
also binds hardlink aliases. Changed aliases and changes during a read are
rejected, and all captured source paths are rechecked before publication.
The same immutable bytes supply copying, hashing and structural validation.
This is not a globally simultaneous snapshot of unrelated files, nor proof
against a malicious kernel or privileged manipulation of the executing process.

The output's existing parent directory must be safe and caller-controlled.
The destination itself must not exist, including an empty directory, regular
file, symlink or dangling symlink. Preparation writes to a fresh private
`.q3-preparing-*` sibling (directory mode 0700; member mode 0600), synchronizes
and rereads the members, then publishes the directory with atomic no-replace
semantics. An output created by another actor during the operation is preserved.
Parent/path identity is rechecked; unexpected replacement prevents success.

On an observed failure, cleanup is best-effort and nonrecursive. Only observed
owned file identities are removed; replacements and unrelated files are
preserved. No unowned destination is deleted to make a retry succeed. A failed
cleanup leaves private staging residue and reports `cleanup_complete=false`.
A process kill, machine failure or filesystem failure can also leave staging
residue. Staging directories are never accepted as completed deliveries.

A directory publication can precede a later synchronization or acknowledgement
failure. Therefore **a manifest's presence alone is not a successful operation**:
require exit 0, the delivered receipt, matching manifest/member bytes and the
separate Q3 checks for the claimed use. A nonzero attempt must not be promoted
from leftover files. Failed receipt delivery returns `RECEIPT_WRITE_FAILED`
after retaining the already published package; reconcile that package before
retrying, rather than deleting or overwriting it automatically.

Cleanup identity checks do not constitute an atomic conditional-unlink primitive.
The private directory and caller-controlled parent are part of the trust
boundary; competing malicious same-user/root operations are not a supported
isolation claim. Long-term retention, a second copy and later readback remain
separate from successful local preparation.

## Invocation

The caller must first supply the separately selected file. The following is an
invocation template, not an authorization to acquire or publish real inputs:

```sh
python PULSE_safe_pack_v0/tools/prepare_q3_archived_input_bundle_v0.py \
  --selection /path/to/selected-originals.json \
  --source-root /path/to/originals \
  --out-dir /path/to/new-q3-package
```

`--resources-root` and `--producer-source-root` optionally select exact supported
copies at alternative locations. Defaults are the preparer's repository root.
No source file is executed during preparation.

After successful preparation, invoke the existing producer and checker using
`input_bundle.json` and `expected_context.json` as documented in the
[reference contract](PULSEMECH_Q3_REFERENCE_RECOMPUTATION_v0.md). Their original
exit-code semantics remain unchanged. The preparer exits 0 for preparation
success and 2 for invalid input, unsupported facilities or operational failure.
It never returns a positive or negative Q3 metric verdict.

A readback of an old preparation manifest is not a fresh preparation run. A
future verifier or activation path must not trust a copied status label as proof
of execution or authority.

## Tests and preserved boundaries

The focused tests cover successful preparation followed by the existing producer
and checker; valid negative metrics and all-UNKNOWN input; independent selection
and resource/source substitutions; original-byte and row bindings; deterministic
outputs; fixed claims; runtime distinctions; unsupported representation; unsafe
paths; existing destinations; no-replace races; changed hardlinks; source/output
mutation; partial writes, zero-progress writes and synchronization failures;
cleanup failure and replacement preservation; receipt-delivery failure; and
read-only originals. Fixture selection is synthetic test setup, not a protocol
for manufacturing authentic archived evidence.

The suite is appended to `ci/pytest-tests.list`. Existing entries remain in
place. Registration does not assert that remote CI has already run for this
change. No complete repository-wide regression result is claimed here.

Every prepared package retains `authority_effect=none`,
`production_gate_eligible=false`, `current_run_evidence=false`,
`source_authentication=not_established`, `label_correctness=not_verified`,
`slice_metadata_correctness=not_verified`, `policy_activation=false`,
`metric_evaluated=false`, `full_q3_semantics_verified=false` and
`selection_origin_authenticated=false`.

Historical Q2 49/50 FAIL and release BLOCK remain unchanged. No historical
acquisition, replay, field comparison, label replacement or top-up is repeated.
The paused QRH003 handoff programme is not reopened. Real Q3 source selection,
access/use review, acquisition if needed, coordinated release integration,
whole-runtime Step 5C/5D acceptance, Step 6 resource measurement and Step 7
promotion remain separate. Keep #2879 open.
