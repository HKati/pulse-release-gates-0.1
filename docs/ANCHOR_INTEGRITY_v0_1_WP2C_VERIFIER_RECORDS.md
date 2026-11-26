# Anchor Integrity v0.1 WP2C — materialized verifier-record bindings

**Status:** offline diagnostic implementation candidate  
**Preparation base:** `9d8e873cbcb0c176624c1fa59cdcc9cc8a9fe8e0`  
**Authority effect:** `none`  
**Release-authority activation:** `false`

## 1. Purpose and increment

WP2A checks local bytes and recorded references; WP2B adds explicitly selected
JSON Pointer projection. WP2C adds a separate executable which checks that each
completed recorded relation has exactly one materialized verifier record and
that the record binds to the same input, carriers, packets, subject, claim,
evidence and declared verifier identity.

A `verifier_record_id` string is not the record itself. A matching record is not
proof that a verifier ran or that its declaration is true. No verifier is executed.
This is local record binding, **not verifier-record trust admission**.

The existing binding checker, projector, schemas, examples and default profile
are unchanged. The new checker reruns the installed base implementation and
does not accept a saved base report as a substitute.

## 2. Contracts and trust inputs

New fixed contracts:

- [Record-set manifest](../schemas/anchor_integrity_verifier_record_set_v0_1.schema.json).
- [Materialized record](../schemas/anchor_integrity_verifier_record_v0_1.schema.json).
- [Diagnostic report](../schemas/anchor_integrity_verifier_record_report_v0_1.schema.json).

The caller must explicitly supply the existing input/carrier paths and expected
SHA-256 values, a record-set manifest path and expected SHA-256, and the base
binding profile (`wp2a` or `wp2b-json-pointer-v1`). The record-set manifest repeats
those exact input/carrier bindings and profile; disagreements fail closed.

The record-set profile is `local_verifier_record_bindings_v1`. Each entry names
one record ID, one relation binding ID, a relative file path, the record's exact
stored-byte SHA-256 and an expected verifier tuple:

```text
verifier_id + method_id + method_version + implementation_sha256
```

This tuple is a caller-pinned expectation, not an authenticated identity or an
allowlist established by a trusted service. An input-selected implementation is
never loaded. The implementation hash is compared as recorded data; there is no
acquisition or execution of a verifier binary.

Each materialized record includes its own ID, exact subject/run identity,
input/carrier digests, all three packet digests and a binding that names:

```text
binding_id, claim_id, claim_digest,
evidence_id, source_id, source_sha256, evidence_sha256, relation_type
```

The record's declared verifier tuple must equal the manifest expectation. Its
completed verification status/result/reason must equal the corresponding
relation declaration, without label inference, coercion or reinterpretation.
Full packet hashes additionally bind claim qualifiers, locators, source metadata,
recording-method fields and the other recorded packet content.

## 3. One retained input snapshot

The new executable uses **one retained** `BundleReader` snapshot for the record
manifest, base input/carriers/packets, response/source bytes and record files.
The existing base checker runs in-process on that same reader. Subsequent record
comparisons consume its already retained packet bytes, not newly opened copies.

This is an invocation-scoped retained-byte snapshot, not an atomic snapshot of
the entire filesystem and not a promise that files cannot change afterwards.
A later disk change does not change which retained bytes the report describes.

Record paths are reserved before base validation. A record cannot alias another
record's path or a base packet, manifest, response, source, legacy-overlay or
optional-graph path. Existing case-collision, no-follow, hard-link, special-file,
per-file, cumulative-byte and JSON-complexity protections are reused.

The installed host, schemas, code and selected root remain trust roots. This
profile requires the existing POSIX safe-file interface. It is not hostile-root
containment and does not add Windows qualification.

## 4. Collection and comparison rules

Every completed relation requires one listed record. Missing manifest coverage
or a missing record file is incomplete. A relation which did not complete must
not be completed implicitly by supplying a record. Orphan entries, duplicate
binding/record IDs and reuse of one record ID across completed relations are
invalid. This first profile does not support one record for multiple relations.

The actual file digest is checked before interpreting the record. Malformed,
ambiguous or schema-invalid JSON is invalid even if the outer manifest was
rehashed. Root, subject, packet, binding, verifier-tuple or result mismatches
are invalid. A failure of the base check prevents the record-comparison stage.

A locally consistent empty record set is possible only when no relation declares
completed verification. Its counts are explicitly **zero**; it does not establish
any matched record, semantic verification or complete requested checks. Unlisted
files in the selected directory are not auto-discovered as evidence.

Where invalid and incomplete findings coexist, invalid takes precedence. Partial
matching-record counts do not make an invalid/incomplete aggregate acceptable.

## 5. Report and exit meanings

| Exit | Status | Meaning |
|---|---|---|
| 0 | `LOCAL_RECORD_BINDINGS_CONSISTENT` | All checks in this local binding profile matched. |
| 1 | `LOCAL_RECORD_BINDINGS_INVALID` | A declared requirement was contradicted or input was malformed. |
| 2 | `LOCAL_RECORD_BINDINGS_INCOMPLETE` | Required local evidence was missing; no positive aggregate result. |

CLI or installation failures also exit 2, with no success-shaped JSON report.
The report is the only stdout output. The tool has no output-file, overwrite,
network, Git, model-call or artifact-code execution option.

The report records expected and observed root digests, the fresh base status and
report digest, counts, per-record digest/comparison results, declared result
labels, deterministic issues and installed implementation/schema fingerprints.
A matched declared label remains explicitly `accepted_as_semantic_support=false`.

The base-report digest hashes the same representation as the base CLI's stdout:
`json.dumps(sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False)`, followed
by one LF, encoded as UTF-8. This is a local report representation, not a new
canonicalization rule for input packets or evidence.

These fields remain fixed:

```text
candidate_status = diagnostic_only
authority_effect = none
release_authority_activation = false
requested_checks_complete = false
accepted_as_semantic_support = false
```

All of the following remain `not_run` with null results:

```text
source_identity_authentication
acquisition_authentication
subject_observation_authentication
verifier_identity_authentication
verifier_execution_attestation
semantic_support_verification
typed_evidence_cycle_check
response_mode_recommendation
claim_set_completeness
verified_binding_coverage
verified_support_coverage
```

If an actor rewrites a complete chain and supplies new expected hashes, the chain
can be locally consistent. This checker does not authenticate that actor, those
expectations, a source or a verifier execution. A `supported` label is never
promoted merely because it has been materialized and matched.

## 6. Complete synthetic example

[Example directory](../examples/anchor_integrity_v0_1/wp2c_verifier_records/)
contains ten files. It copies the WP2B source/claim/evidence data into a separate
fixture and adds a synthetic completed `unresolved` record. The original WP2B
example is not changed. The example verifier implementation digest identifies a
synthetic descriptor string, not an executed verifier program.

From the repository root:

```bash
python tools/check_anchor_integrity_verifier_records_v0_1.py \
  --bundle-root examples/anchor_integrity_v0_1/wp2c_verifier_records \
  --input input.json \
  --expected-input-sha256 d7d16dfccf2dce237060e6b77fbb7da907227b1bd56f1275cfb623ce81cd59a8 \
  --carriers carriers.json \
  --expected-carriers-sha256 70a4d15ee35db21a605ef283c531724d921658fa8bc46ca68f6867925b2c91c4 \
  --record-set record-set.json \
  --expected-record-set-sha256 a70299602a9aae82adcd4ff17278eef5a802ad72e05dbdae6fec64a9f98f188e \
  --binding-profile wp2b-json-pointer-v1
```

Expected local outcome: one completed relation, one listed record, one matching
record and `LOCAL_RECORD_BINDINGS_CONSISTENT`. Authentication and semantic
results remain unperformed. The demonstration is not live verifier evidence.

## 7. Tests and integration

Extend the already registered
`tests/test_anchor_integrity_v0_1_contract.py` module. Preserve all previous
WP1/WP2A/WP2B cases and function bodies. The existing direct entrypoint also
collects the new cases. Both CI manifests remain byte-identical; no registration,
manifest-count change, workflow, dependency or normative gate is introduced.

The new regressions exercise root expectations, record-set/record contracts,
exact identifier and packet bindings, declaration changes, rehashed envelopes,
non-completed relations, missing/orphan/reused records, empty sets, strict JSON,
shared read budgets, POSIX file boundaries, retained snapshots, deterministic
reports, CLI exits and non-promotion of unperformed checks.

Run the whole module or its existing direct entrypoint:

```bash
python -m pytest tests/test_anchor_integrity_v0_1_contract.py -q
python tests/test_anchor_integrity_v0_1_contract.py
```

Local test results and environment details are in the separate delivery report.
Hosted CI must validate the uploaded PR head; local testing is not merge approval.

## 8. Remaining work

Authenticated verifier-record admission and provenance, actual verifier execution
and semantic checking, typed dependency-cycle evaluation, claim-set completeness
and full adapter coverage/disposition arithmetic remain separate increments.
No normative status, policy, required gate, release checker, legacy v0 runtime,
Pages, OG, History, SARIF, Q3/W1, DOI or Software Heritage behavior changes here.
