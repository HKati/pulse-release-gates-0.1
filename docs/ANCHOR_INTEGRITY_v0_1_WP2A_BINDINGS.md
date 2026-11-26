# Anchor Integrity v0.1 — WP2A local binding checker

**Status:** executable diagnostic candidate, first increment of WP2  
**Preparation base:** `add03e358dd50d45ecd2fd862ab38e3c87c5b49d`  
**Authority effect:** `none`  
**Release-authority activation:** `false`

## 1. Purpose and boundary

Implement offline byte and recorded-reference checks against the unchanged
[WP1 contracts](ANCHOR_INTEGRITY_v0_1_CONTRACT.md). This is not the complete
v0.1 adapter and does not emit `anchor_integrity_output_v0_1`.

```text
independently retained expected input and carrier-manifest SHA-256 values
-> exact input and local-carrier bytes
-> schema-valid packets and exact packet-link digests
-> unique IDs and matching recorded subject/reference fields
-> supplied response/source bytes and exact locator selections
-> separate diagnostic local-binding report
```

A checkable source identifier is not an authenticated source. Equality between
two recorded subject/run identifiers is not evidence of the corresponding
observation. A recorded `supported` result and `verifier_record_id` are not
accepted as semantic verification.

The checker never upgrades the declarations inside an input packet. Even an
input that declares successful identity/integrity/semantic checks still receives
`not_run` / `null` for authentication and semantic checks not performed by WP2A.
Recorded negative results are not rewritten either. A locally consistent bundle
may legitimately retain a recorded external identity mismatch.

## 2. Files and registration

- Checker: [`tools/check_anchor_integrity_bindings_v0_1.py`](../tools/check_anchor_integrity_bindings_v0_1.py).
- Carrier contract: [`anchor_integrity_local_carriers_v0_1.schema.json`](../schemas/anchor_integrity_local_carriers_v0_1.schema.json).
- Report contract: [`anchor_integrity_binding_report_v0_1.schema.json`](../schemas/anchor_integrity_binding_report_v0_1.schema.json).
- Regression suite: [`test_anchor_integrity_v0_1_contract.py`](../tests/test_anchor_integrity_v0_1_contract.py).
- Runnable synthetic input: [`wp2a_local_binding/input.json`](../examples/anchor_integrity_v0_1/wp2a_local_binding/input.json).

Extend the existing Anchor test module, which is already registered in both CI
manifests. No registration, count-consumer update or workflow change is needed.
The original WP1 test functions, five schemas, examples and historical-source
fixture are preserved.

## 3. Inputs and caller responsibility

The CLI requires an explicit bundle root, relative input and carrier-manifest
paths, and **two expected SHA-256 values supplied by the caller**. It never
obtains an approval hash from the same untrusted manifest it is checking.

Those expected values are a caller-controlled comparison boundary, not a
signature or evidence of the caller's identity. Computing new hashes for a
rewritten bundle and supplying them admits a different object; it does not
prove its provenance, execution, meaning or authority.

The carrier manifest binds the exact input SHA-256 and maps:

- the recorded source-response ID to one local response file;
- each supplied source ID, canonical identifier and revision to a local file.

The mapping's identifier/revision must equal the corresponding packet record.
This is consistency of recorded metadata. It does not prove a commit-to-tree-
to-path-to-blob relationship or authenticate a remote URL.

Missing mappings and files are explicit incomplete results. Unexpected source
IDs, duplicate IDs, reused carrier paths or mismatched bindings are invalid.
All declarations and hashes are retained in the original input files; the
checker writes none of them.

Only declared carriers are consumed. Surplus files in the selected directory
are not included in this verification scope and are never executed.

## 4. Checks performed

1. Strict UTF-8 JSON: duplicate keys, non-finite values, invalid encoding,
   unpaired surrogate strings and bounded-complexity violations are rejected.
2. Input and carrier-root digests match the two supplied expectations.
3. The four existing input/claim/evidence/relation schemas validate the packets.
4. Exact stored bytes, not reserialized JSON, determine packet-link SHA-256.
5. Relation packet bindings equal the selected claim/evidence packet bindings.
6. Packet IDs and claim/source/evidence/binding IDs are unambiguous.
7. Packet subjects, evidence expectations and recorded observation IDs agree
   where IDs are provided. Missing observations remain incomplete. Two null
   run IDs do not create a completed run-identity check.
8. Each claim digest matches its UTF-8 text; the supplied response digest and
   exact response locator reproduce that text without trimming.
9. Whole-source and selected-evidence digests are reconstructed independently.
10. Every relation refers to an existing claim and evidence item. Repeated
    relations do not inflate the number of claims with a recorded anchor.

The legacy overlay and optional Paradox graph are **opaque JSON carriers**:
verify bytes and the declared `schema` / `schema_version` tag only. Do not
validate their complete internal schema, consume a legacy gate ratio as claim
coverage, interpret graph edges or execute anything from those carriers.

Partial or invalid declared claim-set materialization gives an incomplete local
result. A complete declaration is recorded, not independently proved complete.
Counts are inventory counts, not verified-binding or semantic-support coverage.
No percentage is emitted.

## 5. Locator profile

`line_range`: one-based, inclusive endpoints; split only on LF; retain original
terminators, including CRLF. An unterminated final line exists; an empty
phantom line after a final LF does not. No trimming, newline normalization or
file decoding is applied to line-selected evidence bytes.

`character_span`: strict UTF-8; zero-based Unicode code-point offsets and a
half-open `[start, end)` interval. No Unicode normalization, grapheme-cluster
counting or UTF-16 code-unit conversion is performed. Hash the exact selected
text encoded as UTF-8. Integer-valued floats and booleans are not offsets.

`json_pointer`: schema-valid pointers remain accepted as input declarations,
but selection is **not implemented** in this increment. WP1 does not define a
selected-value byte projection for hashing. Rather than silently serialize or
canonicalize a value, emit `not_run` / `null` with an incomplete reason.

## 6. Local-file boundary and limits

Runtime profile: POSIX with directory-relative `open` and `O_NOFOLLOW` support.
Every untrusted relative path component is checked. The trusted host, Python
installation, repository schemas and caller-selected root remain trust roots.
This is not a sandbox against malicious root or concurrent hostile host code.

Relative paths use ASCII letters, digits, underscore, hyphen, dot and slash.
Absolute paths, dot/dot-dot components, backslashes, URL/drive forms, trailing
dots and case-colliding aliases are rejected. Carriers must be regular files;
symlinks, hard-linked files, FIFOs and devices are rejected. No network fetch,
Git command, external executable, artifact import, eval or plugin is used.

Each file is read once into a per-invocation snapshot. Metadata changes during
that read are rejected. The report describes the bytes read, not a guarantee
that the filesystem will remain unchanged after verification.

Limits: 8 MiB per file; 64 MiB total unique file bytes; 4,096 entries per array;
64 JSON nesting levels; 100,000 JSON nodes; 512 characters per relative path.
Missing trusted schemas or unsupported safe-file primitives do not produce a
successful report. The local schemas are self-contained; reference keywords
are rejected before validation, so there is no network schema resolver.

## 7. Report and exit semantics

| Exit | Diagnostic status | Meaning |
|---|---|---|
| 0 | `LOCAL_BINDINGS_CONSISTENT` | All in-scope local checks completed consistently. |
| 1 | `LOCAL_BINDINGS_INVALID` | A mismatch, unsafe carrier or invalid record was observed. |
| 2 | `LOCAL_BINDINGS_INCOMPLETE` | Required local bytes or supported measurements are unavailable. |
| 2 | No report; stderr diagnostic | CLI/implementation/schema installation failure. |

If invalid and incomplete observations coexist, invalid takes precedence;
individual issues are retained. Output ordering is deterministic. No timestamp,
absolute bundle-root path or random value is included. The report binds the
checker and six used schemas by SHA-256, plus expected and observed root hashes.

The report always fixes:

```text
candidate_status = diagnostic_only
authority_effect = none
release_authority_activation = false
requested_checks_complete = false
```

Source/acquisition/observation authentication, semantic support, evidence-cycle
checking, response recommendations, independent claim-set completeness and the
WP1 verified-binding/support coverage measures remain `not_run` with `null`
results. The report is unsigned. A forged report does not become authentic
merely because it validates against a schema.

## 8. Reproducible synthetic example

This example is a synthetic local conformance fixture, not observed experiment
evidence. It contains two explicitly materialized claims and one recorded
reference. No source identity or semantic result is asserted as verified.
The retained baseline commit `34431ec8...` identifies the WP1 historical v0
baseline, not the origin of this synthetic text or the current checker source.

From the repository root on the supported POSIX profile:

```bash
python tools/check_anchor_integrity_bindings_v0_1.py \
  --bundle-root examples/anchor_integrity_v0_1/wp2a_local_binding \
  --input input.json \
  --expected-input-sha256 be4865f6544ce1cc91b5af5dab89357b71fe4629a92ecc079de99f8e95af9d74 \
  --carriers carriers.json \
  --expected-carriers-sha256 4ad4b7301042f2b136cd13cc18f01f7b2d0b7ca823a3e46032e2f3d7e9c4e4b2
```

Expected: exit 0 and `LOCAL_BINDINGS_CONSISTENT`; two claims, one with a recorded
anchor and one without. No semantic support or response authorization follows.
All output goes to stdout; the checker has no output-file/overwrite option.

The older WP1 examples remain illustrative schema fixtures. Without their
missing response/legacy/source carriers they are not a complete runtime input;
WP2A reports that incompleteness instead of silently supplying missing evidence.

## 9. Validation and remaining work

Run the complete already-registered module:

```bash
python -m pytest -q tests/test_anchor_integrity_v0_1_contract.py
python tests/test_anchor_integrity_v0_1_contract.py
```

The separate delivery report records actual results and interpreter versions.
Fixture tests are not real-world hallucination measurements, authenticated
acquisition, hosted execution or a full repository CI result.

Next increments must separately define the semantic-verifier record admission
boundary, JSON-pointer projection, typed evidence-dependency evaluation and the
full adapter's disposition/coverage arithmetic. Neither merge nor a local
`CONSISTENT` result activates those missing components or a release gate.

No changes to v0 runtime, workflows, normative status, gate policy, required
gate materialization, `check_gates.py`, Pages, OG, History, SARIF, DOI or Software
Heritage material are part of this increment.
