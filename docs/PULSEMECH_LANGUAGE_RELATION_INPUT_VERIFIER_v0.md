# PULSEmech Language Relation Input Verifier v0

Status: LRM-02 implementation contract for source binding and separate
representation verification. The public result is the existing
`language_relation_verification_v0` artifact.

Implementation base: commit
`27db7eef1d2d8b43c05bfcf5791a8d931d32125b` in
`HKati/pulse-release-gates-0.1`.

The historical planning baseline remains commit
`47a3add6667542df6ef176285ed02bb1a741d9cf`, tree
`6d425c83e16fdc95cb2cfe1645a8060f3336dfaf`. These are different bindings:
the implementation base identifies the checkout extended by LRM-02; the
historical baseline identifies the source documents inventoried by LRM-01.
Neither is substituted for the other.

## 1. Scope and authority boundary

This package implements the LRM-02 obligations in the
[development plan](PULSEMECH_LANGUAGE_RELATION_MEASUREMENT_v0_PLAN.md):

| Obligation | Verifier responsibility |
| --- | --- |
| A01 | Bind actual source bytes and UTF-8 byte spans to their declared lengths and digests. |
| A02 | Resolve the actual input, context and processing instance; reject substitution by a record for another subject. |
| A03 | Reject duplicate JSON keys and identifiers, prohibited fields, incorrect types and dangling references. |
| A04 | Preserve actual execution states and independently resolve accepted evidence. A package cannot create its own trust root. |
| A22 | Parse controlled source text independently and detect a lost AND/OR distinction even when both submitted representations contain the same error. |

The verifier supplies the representation-basis boundary needed by later
measurement. It does not implement a relation comparator, consequence
evaluator, automatic language extractor or replay runner. A successful source
mapping check is not a `PRESERVED` result. No preservation, causal or replay
conclusion is inferred from its exit code.

The existing
[LRM-01 contract](PULSEMECH_LANGUAGE_RELATION_MEASUREMENT_v0_CONTRACT.md),
[finite profile](../contracts/language_relation_profile_v0.json) and historical
fixtures remain preserved. The profile's original contract-stage and
unimplemented-status fields describe the recorded LRM-01 artifact; this
document defines the separately implemented LRM-02 capability. Updating a
runtime implementation does not rewrite the immutable profile bytes or the
fixture profile digests.

Every verification artifact retains `authority_effect: "none"`,
`release_authority_activation: false`, and `authority_status: "none"`.
The release-authority chain, Anchor Integrity contract, Transition Meter
status vocabulary and Paradoxon Diagram boundaries remain unchanged. The
verifier does not write normative release evidence or gate decisions.

## 2. Runtime entry point

Run the checker from a repository checkout:

```bash
python tools/check_language_relation_input_v0.py \
  --input /work/case/input.json \
  --package-root /work/case \
  --output /work/results/verification.json
```

For independently accepted reference or profile evidence, additionally supply
`--trust-config /work/independent-trust/trust-config.json`. The trust
configuration and every file it pins must be outside the submitted package.
The operator fixes this configuration independently of the input under test.
Without this configuration, the runtime cannot resolve a submitted
non-candidate acceptance claim.

`--package-root` defaults to the input file's parent directory. The input file
must be inside that root. The output directory must already exist. The CLI
requires a fresh output path and never overwrites an existing file, input,
source or evidence record. It writes and synchronizes a temporary file in
that directory, then publishes the complete validated report with a
non-replacing filesystem operation. A concurrent creation at the destination
is also rejected. Repeated runs use different output paths.

| Exit code | Meaning |
| --- | --- |
| `0` | Verification execution completed and produced a diagnostic artifact. Individual checks can pass, fail or remain unresolved. |
| `2` | Invalid input or configuration: strict loading, schema, structural or resolver-configuration failure. |
| `3` | An input/output operation failed. |

A completed diagnostic failure or unresolved mapping is not a malformed-input
error. An invalid artifact is not converted to a successful diagnostic merely
to obtain exit code zero. The output is validated against
[`language_relation_verification_v0.schema.json`](../schemas/language_relation_verification_v0.schema.json).

## 3. Binding and structural checks

The loader rejects duplicate JSON object keys before ordinary dictionary
construction. It does not coerce values into the required types. Schema
validation uses the repository's self-contained Draft 2020-12 schemas; schema
identifiers are not instructions to retrieve network resources.

JSON is strict UTF-8 without a BOM. Non-finite numbers, unpaired Unicode
surrogates and excessive nesting are rejected. The runtime limits a JSON file
to 4 MiB, its structure to 100,000 visited nodes and 80 levels, each source to
1 MiB, and the aggregate source bytes to 4 MiB. These resource failures are
invalid input, not successful semantic measurements.

There must be exactly one `before` source and one `after` source. Each
representation must name its corresponding source. Context sources are
explicit. Source, anchor, representation, entity, domain, relation, group,
variant, correspondence, target and obligation identities must resolve in
their proper domains and sides.

### 3.1 Exact bytes and locators

An inline source is reconstructed by encoding its JSON string as UTF-8. A
`package_path` source is read as bytes beneath `--package-root`. Source paths
must not escape that root, including through symlinks. The runtime verifies
the actual source length and whole-source SHA-256 rather than accepting the
declared values.

Each source anchor is the half-open interval `[start_byte, end_byte)` in its
identified source. Require:

- `0 <= start_byte < end_byte <= actual byte length`;
- both boundaries fall between complete UTF-8 characters;
- the selected bytes have the independently reconstructed span SHA-256.

No Unicode normalization, whitespace folding or line-ending rewriting occurs
before this check. Two visually similar strings can have different bytes and
different bindings. Rehashing an outer JSON wrapper cannot repair a stale
source or span binding.

### 3.2 Typed relations and references

Structure validation checks the declared predicate, complete ordered role
signature, argument multiplicity and argument types. It resolves entity,
domain, relation, group and correspondence references, checks lexical variable
binding, and rejects cyclic expression-reference graphs. An empty finite
domain is a declared domain and is not confused with an absent interpretation
family.

The whole role tuple of an n-ary relation is preserved. Pairwise projections
are not substitutes for the declared relation. Matching source labels alone
does not justify identity between entities or events on different sides.

Interpretation variants identify conveyed roots separately from auxiliary
relation declarations. A declaration used as a subexpression, proposition
argument or witness atom is not asserted merely by being declared. Joint
variants remain joint configurations; the runtime does not invent a Cartesian
product of mutually constrained choices.

## 4. Separate controlled-source checking

The checker parses the actual preserved source text through a dedicated
controlled-language path. It does not call an adapter's extraction method
again and treat agreement with itself as independent verification. It does
not receive expected fixture labels or select a judgment by `case_id`.

The source grammar is the immutable profile's exact HU/EN grammar:

- approval and winning atoms;
- explicit `NOT`, `AND`, inclusive `OR` and `IMPLIES` scope;
- finite `FORALL` and `EXISTS` domains with lexically bound variables;
- quotation, permission and obligation contexts.

The document consists of one formula followed by a literal full stop.
Separators, case and parentheses follow the profile exactly. Names are drawn
from its finite lexical domain. Quotation retains speaker and discourse
scope; permission and obligation retain their modalities. A quoted or
permitted proposition is not an observed event.

The general relation model is larger than this source grammar. In particular,
declared `give`, `notify`, `release`, `send` and `tuple` predicates have no
controlled source productions in this profile. Their complete structures can
be validated, but their source semantics require an independently accepted
reference or remain candidate structures. Pronouns, ellipsis, implicit context,
unsupported inflection and unsupported surfaces also remain outside the
controlled parser. Empty source-quantification domains are outside its surface
grammar even though empty domains are representable in the general model.

The checker compares the conveyed structure, including operator and context
scope, with the roots selected for the submitted joint interpretations. A
matching atom somewhere in the source is insufficient. Omitting a conjunct,
negation, quantifier or context wrapper cannot yield a whole-source mapping
pass. This is what prevents equal mistakes in the before and after
representations from concealing a changed source AND/OR distinction.

A completed check of a supported source can fail when its submitted
representation disagrees. Unsupported or unavailable interpretation remains
explicitly unresolved. A check prevented by invalid binding is recorded as
unperformed rather than assigned an invented semantic result.

The profile bounds are 64 joint variants, 12 expanded Boolean atoms and
256 AST nodes per variant. These are finite resource bounds, not performance
measurements. A resource limit cannot become a successful exhaustive mapping
claim. The family states `complete`, `unknown`, `empty` and `truncated` retain
their distinct meanings.

The two source sides share the joint resource budget. For the resource count,
each distinct `CONTEXT` occurrence has its own scope even when its speaker,
discourse type and modality equal another occurrence. This conservative count
does not rewrite the communicated expression or establish event identity.

Each side is checked independently and the combined before/after cost is then
checked against the joint atom and per-variant AST bounds. Two individually
bounded mapping passes do not evade a joint bound. Selected target relations
must belong to the actually checked root closure before a profile basis can
be accepted. External context constraints, target context sources or context
coverage obligations prevent profile-basis elevation in this implementation;
their bytes alone do not verify their interpretation.

## 5. Representation basis

| Requested basis | Permitted verified scope | Necessary boundary |
| --- | --- | --- |
| `candidate_only` | `candidate_structures` | Remains candidate even when the independent mapping check passes. |
| `accepted_reference` | `reference_interpretation` | Exact independently accepted annotation and completed reference-review evidence resolve. |
| `profile_verified` | `controlled_source_profile` | Exact independent profile acceptance and source-verification evidence resolve; the current controlled-source check must also support the claim. |

A caller's basis string does not authorize the claimed basis. Candidate input
is never automatically promoted. A missing, stale, inconsistent or unresolved
acceptance chain cannot establish a non-candidate result.

Reference acceptance is conditional on the exact accepted interpretation. It
does not establish that the interpreted proposition is true in the world.
Profile verification is similarly limited to faithful representation within
the supported grammar. It is not evidence of an event's occurrence.

The runtime preserves separate byte-binding and semantic records. A successful
source-byte check remains recorded when semantic checking fails, is unsupported
or has not run.

## 6. Independently configured evidence resolver

The additional
[`language_relation_evidence_v0.schema.json`](../schemas/language_relation_evidence_v0.schema.json)
defines four strict record shapes. Every listed field is required, undeclared
properties are rejected, and all schema references are local. All four shapes
retain the two fixed authority fields.

### 6.1 Trust configuration and file pins

`language_relation_trust_config_v0` contains `inventory_files`,
`verification_files` and `processing_files`. Each list item contains a
`path` and `content_sha256`. Lists may be empty. Paths are relative to the
configuration directory. They cannot contain parent traversal, absolute
paths, prohibited separators or symlinks; their resolved targets and the
configuration itself must remain outside the submitted package.

Each pin binds the exact raw file bytes. The runtime verifies these digests
before interpreting the records. A package-provided inventory, or a newly
calculated hash of that inventory, cannot make itself trusted.

The output's check evidence includes the configured trust file's raw digest
as `trust-config.sha256:<digest>`. Successfully used inventory, verification
and processing payloads also contribute `sha256:<digest>` references. A
completed acceptance failure still preserves the configuration pin used for
resolution. These bind content; neither form authenticates its author or
creates trust. The configuration is limited to 128 pinned files and 16 MiB of
aggregate payload bytes.

External placement is a mechanical boundary, not proof of independence. The
operator must choose this configuration independently; copying package-supplied
claims into another directory does not supply the missing acceptance premise.
The CLI does not establish human approval or authenticate an organization
merely from a pathname.

### 6.2 Acceptance inventory

`language_relation_acceptance_inventory_v0` contains `inventory_id` and
nonempty `entries`. An entry contains:

| Field | Meaning |
| --- | --- |
| `entry_id` | Entry identity within the independently configured inventory. |
| `basis` | `accepted_reference` or `profile_verified`. |
| `subject_sha256` | Digest of the versioned, side-specific subject projection below. |
| `side` | `before` or `after`. |
| `representation_id` | Exact representation subject. |
| `verification_id` | Independent source-verification record to resolve. |
| `method` | `independent_reference_review` or `controlled_source_profile_v0`. |
| `claim_scope` | `reference_interpretation` or `controlled_source_profile`. |

The input's `acceptance_ref.content_sha256` is the SHA-256 of the
deterministically serialized entry, not the raw inventory-file hash. The
configuration separately pins the inventory file. Runtime validation enforces
the basis/method/scope combination; schema shape alone does not authorize it.

### 6.3 Source-verification record

`language_relation_source_verification_v0` contains `verification_id`,
`input_ref`, `profile_ref`, `subject_sha256`, `side`, `representation_id`,
`basis`, `method`, `claim_scope`, `checker_ref` and nonempty `checks`.

`input_ref` binds the final input artifact identity and its exact raw bytes.
Its `artifact_id` is the input's `case_id`.
`profile_ref` binds the preserved profile identity and raw bytes.
`checker_ref` identifies the actual checking implementation, version and
content digest. The remaining subject and acceptance fields must agree with
the independently accepted inventory entry and current input.

Each check contains `check_id`, `kind`, `status`, `result` and `reason`.
Kinds are `source_binding`, `subject_binding`, `representation_mapping` and
`coverage`. A listed check ID or claimed completion flag is not enough:
required checks must actually resolve with the appropriate kinds and successful
results for the accepted subject and method.

Both accepted modes require all four check kinds, with unique check IDs and
`completed`/`pass` results. An `accepted_reference` entry uses
`independent_reference_review` and `reference_interpretation`; a
`profile_verified` entry uses `controlled_source_profile_v0` and
`controlled_source_profile`. Identity, subject and method disagreement block
acceptance. The trusted record's checker identity is a statement from the
independently pinned record; its digest is not treated as self-authentication.

A current controlled-source mapping failure also blocks reference elevation.
An unresolved mapping because a reference source is outside the controlled
grammar does not invalidate an otherwise resolved independent reference
review. It remains conditional reference interpretation, never a controlled
source verification.

### 6.4 Processing record

`language_relation_processing_record_v0` contains `evidence_id`,
`processing_id`, a nonempty `operation`, `input_ref`, `profile_ref`,
`source_bindings` and `execution`.

Each source binding preserves `source_id`, `role`, `language`, nullable
`revision`, `content_sha256` and `byte_length`. The record must bind the exact
before and after instances and the relevant context instances of the named
operation. Its execution record follows the same actual-state rules as a
source check.

`processing_claim: "structural_comparison"` does not require proof of a
processing operation. `processing_claim: "processing_change"` requires a
resolved processing binding and independently configured execution evidence.
Two differing texts, even when their representations are faithful, do not by
themselves show that a particular operation changed one into the other.

## 7. Cycle-free subject binding

The acceptance subject is constructed from the parsed input as follows:

1. Deep-copy the complete input object.
2. Remove only its top-level `representation_basis` field.
3. Wrap the result in an object with `projection_version`, `side` and `input`.
4. Set `projection_version` to `language_relation_subject_v0`; set `side` to
   the actual `before` or `after` subject.
5. Serialize deterministically and calculate SHA-256.

The deterministic JSON encoding is UTF-8 without a BOM, with two-space
indentation, object keys sorted in Unicode code-point order, unescaped Unicode
characters and one terminal LF. Declared ID sets (`*_ids` and `evidence_refs`)
are sorted lexically; named record arrays are sorted by their primary ID.
Source, anchor, entity, domain, relation, group, variant, target,
correspondence, coverage-obligation, claim, rule, check, basis, inventory-entry
and source-binding arrays use their respective primary identity fields.
Ordered argument and AST operand arrays retain their order. This is the
declared encoding, not a claim of RFC 8785 canonicalization.

The projection intentionally binds every other input field, including source
carriers and digests, anchors, both representations, selected roots and
interpretations, correspondence, coverage annotations, measurement request,
processing identity, provenance and case identity. Changing any of those
fields' canonical content invalidates the old acceptance subject. Reordering
a declared set does not change its canonical content. This conservative
dependency boundary can invalidate acceptance more broadly than a single
changed target; it does not silently narrow the accepted subject.

The projection excludes acceptance metadata to avoid a digest cycle. The
inventory entry references a verification ID without embedding the
source-verification record's digest. The completed record separately binds the
final input's raw digest, after the input contains the accepted entry digest.
Finally, the independent configuration pins the inventory and completed-record
files. Rehashing the submitted input cannot update that independent pin chain.

## 8. Actual execution and verification output

The public output keeps the existing verification schema. It binds the exact
input, immutable profile and running checker, records individual checks and
contains exactly one basis record for each side.

The runtime checker identity is `language_relation_input_verifier_v0`, version
`0.1.0`. Its content digest binds a deterministic list of file paths and actual
SHA-256 values for the implementation modules, CLI, input schema, verification
schema, evidence schema and immutable profile. This records the code and
contract dependencies used by the checker; it does not authenticate them as an
independent trust root.

The exact fingerprint input is `{"files": [...]}`, where each item contains
`path` and `content_sha256`, and the explicit `CHECKER_FILES` list is sorted
lexically. The fingerprint is SHA-256 of that object's deterministic JSON
bytes. The preserved profile is also checked against its fixed runtime digest,
not accepted merely because a caller supplies a matching-looking profile ID.

The output `verification_id` is `lrm02.` followed by the first 48 hexadecimal
characters of the SHA-256 of the deterministically serialized report with its
`verification_id` omitted. The ID therefore has no self-digest cycle. Exact
input bytes, including their final basis claims, remain separately bound in
`input_ref`.

| Execution state | Required result and explanation |
| --- | --- |
| `not_run` | `result: null` and a nonempty reason. |
| `error` | `result: null` and a nonempty reason. |
| `completed` | `pass`, `fail` or `unresolved`. |
| Completed failure or unresolved check | A nonempty reason. |

Basis records identify actual supporting check IDs, the permitted claim scope
and the resolved acceptance reference when a non-candidate basis is supported.
Runtime cross-record validation checks side uniqueness, check identity and
the truth of any accepted basis. Mere schema validity is not completed
verification.

Submitted coverage is not independently established coverage. The verifier
records what it checked and leaves unresolved obligations visible. It does
not promote unperformed correspondence, coverage, causal or replay work into
a positive result. An independently checked source mapping does not justify
cross-source entity identity or complete comparator coverage.

Coverage checks for source scope, entities, relations, operator scope and
interpretation families can close only through current supported mapping work
or the independently accepted reference boundary. Reference-based coverage
also requires a nonempty `complete` interpretation family. Acceptance of an
unresolved annotation does not turn an `unknown`, `empty` or `truncated`
family into exhaustive coverage. Context and correspondence coverage remain
unresolved. Cross-source correspondence checks are explicitly `not_run`;
they belong to LRM-03. Generated check IDs are checked for uniqueness,
including collisions introduced by bounded-ID encoding. Aggregate axes
remain conservative:
`partially_bound` does not assert total subject or semantic closure,
`reproduction_status` remains `not_tested`, and `causal_status` remains
`not_evaluated`.

All six Transition Meter axes remain explicit. Causal evaluation and release
authority are outside this package. The artifact reports what actually ran,
including successful byte checks alongside unsuccessful or unavailable
semantic checks; it is not a single whole-document confidence score.

## 9. Acceptance and regression boundaries

The LRM-02 tests must exercise independent failures rather than reproduce the
implementation's own expected answer:

- changed bytes and rehashed wrappers against stale evidence;
- shifted spans and boundaries inside multibyte UTF-8 characters;
- substituted source, context and processing instances;
- duplicate keys and identifiers, invalid types, prohibited fields and
  dangling or cyclic references;
- self-authorizing package inventories and missing independent acceptance;
- unperformed/error states with null results;
- the same incorrect AND/OR representation on both sides;
- lost negation, quantifier scope or discourse/modality context;
- unsupported surfaces and bounded or incomplete interpretation work;
- preservation of complete n-ary argument tuples without claiming an
  unsupported controlled parser;
- candidate basis remaining candidate after a mapping pass.

The existing synthetic corpus remains specification material. Its candidate
bases and synthetic provenance are not converted into owner acceptance,
world-event evidence or preexisting verification history. A real execution on
a synthetic input can produce `verification_run`; the exact bound input still
retains its synthetic provenance. Fixture oracles remain outside the runtime's
input path. Passing LRM-02 tests establishes this verifier boundary; it does
not complete LRM-03 through LRM-06.
