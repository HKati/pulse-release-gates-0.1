# Anchor Integrity v0.1 WP2K — legacy format-checker boundary

**Status:** targeted correction to the existing v0 format checker.  
**Preparation base:** `920754daa217f0c44adb7648fa49fd1c5f4765c1`.  
**Checker profile:** `legacy-v0-strict-format-v1`.  
**Authority effect:** `none`; no new gate or evidence admission.

## 1. Why this correction precedes a live collector

[WP2J](ANCHOR_INTEGRITY_v0_1_WP2J_LEGACY_PRODUCER_BOUNDARY.md) stopped the active
producer from deriving evidence measurements from heterogeneous gates.
[WP2I](ANCHOR_INTEGRITY_v0_1_WP2I_LEGACY_READER_BOUNDARY.md) corrected the existing
Markdown reader. Their third existing companion,
[`check_anchor_integrity_v0_contract.py`](../scripts/check_anchor_integrity_v0_contract.py),
still admitted ambiguous or schema-invalid input before this correction.

The exact 9,783-byte preparation-base checker was read and matched to Git blob
`023e3a6e817cc1c1967cf7926763fe9837b6f26e`. Isolated local probes reproduced:

| Input change to the valid WP2J example | Previous observed result | Corrected result |
|---|---|---|
| Boolean `source_date_epoch: true` or `false` | Accepted as an integer | Reject |
| Duplicate `state`, with an invalid first value and valid last value | Last value silently selected; accepted | Reject duplicates, even equal values |
| `anchor_coverage: 1.00000000000000000001` | Rounded to 1.0; accepted | Reject: exact value exceeds 1 |
| `anchor_coverage: -1e-999` | Underflowed to negative zero; accepted | Reject: exact value is below 0 |

A separate API probe also exposed `OverflowError` from converting an enormous
integer coverage value to float. The corrected checker rejects it normally.
These are local format-admission defects, not demonstrated release-authority
bypasses, repository compromises or evidence of exploitation.

No verifier collector, new execution permission or independent audit is added.
The [WP2F execution prerequisites](ANCHOR_INTEGRITY_v0_1_WP2F_EXECUTION_CONTRACT.md)
remain separate. This small corrective package does not complete them.

## 2. Exact scope

Modify the existing checker, add a boundary link to the historical-design notice,
and append regressions to the already registered
`tests/test_anchor_integrity_v0_1_contract.py`. Add this document and a
[source-bound historical checker fixture](../tests/fixtures/anchor_integrity_v0_1/legacy_checker_920754da.source.json).
No prior Anchor test case, fixture, schema, producer, reader or WP2A-H tool is replaced.
Both CI manifests remain unchanged; no test count consumer needs an update.

The [v0 schema](../schemas/anchor_integrity_v0.schema.json) remains byte-identical.
The original [WP1 historical inventory](../contracts/anchor_integrity_v0_1_baseline_inventory.json)
is historical, not a claim that the active checker retains its old bytes.
The snapshot is test data. The production checker never decodes or executes it.

## 3. Byte admission before format checking

The CLI preserves `--in FILE`, reads no network source and never writes files.
The file boundary is deliberately bounded and stricter than generic JSON:

- At most 8 MiB per input; read at most the limit plus one byte.
- At most 64 nested JSON containers. Quoted and escaped delimiters do not
  count as containers. This scanner is a resource precheck, not a second parser.
- At most 1,024 characters per numeric token, including sign/exponent syntax.
- Strict UTF-8 JSON; reject duplicate decoded keys, malformed/trailing JSON,
  `NaN`, `Infinity` and `-Infinity` in every object/array position.
- Reject a final symlink, directory, FIFO or other non-regular input. Use
  nonblocking/no-follow flags where available, and inspect the opened descriptor.
- Compare descriptor identity, size and modification metadata before/after the
  bounded read. Reject an observed change or a byte-count disagreement.

Missing and invalid inputs fail this checker with exit 1. This differs from
the producer/renderer's intentionally CI-neutral unknown/UNAVAILABLE output;
those existing programs are not changed here.

A file can satisfy the frozen abstract schema yet exceed these transport/resource
budgets. Such a file is rejected by this implementation, not silently truncated.
Directory ancestry and the local host remain trusted. These checks are not
hostile-filesystem containment, an atomic snapshot or source authentication.

## 4. Exact numbers and frozen-schema interpretation

Decode integer tokens as bounded Python integers and fractional/exponent tokens
as `Decimal`, preserving their exact numeric value. Do not convert numbers to
float before comparing the [0,1] coverage boundary. Underflow and rounding cannot
make an out-of-range token valid. Oversized or unsupported numeric representations
are rejected, never coerced into a convenient value.

`source_date_epoch` follows the frozen schema's mathematical integer meaning:
null, nonnegative integers and exact nonnegative integral numeric values such as
`1.0` and `1e3` satisfy its format. Booleans, strings, fractions and non-finite
values do not. The schema imposes no maximum epoch; this checker does not
invent a trusted time range. The producer's separate metadata bounds remain
unchanged. A valid epoch here is not a trusted clock or signing-time proof.

Two previously over-strict manual-checker rules are explicitly aligned with the
unchanged schema: integral number values are integers, and `minLength: 1` means
one or more characters, not a nonempty result after whitespace stripping.
Whitespace-only strings may therefore be format-valid where the schema permits
them. This is not an assertion that such metadata is useful, authenticated or
acceptable for evidence admission. No schema is weakened to obtain this result.

The Python `check_contract(doc)` API validates the in-memory values supplied to
it; it cannot recover duplicate keys or numeric information already discarded by
another parser. Use this checker's own CLI/read path for byte admission. It also
accepts finite Python floats, checking the value actually supplied. `Decimal`
values produced by this checker must not be reserialized or used to recompute
historical packet digests; the checker does not rewrite the input.

## 5. Format success is not evidence verification

The CLI writes its diagnostic to stderr, as before, and leaves stdout empty:

```text
[OK] anchor_integrity_v0 format contract check passed; profile=legacy-v0-strict-format-v1; scope=format_only; evidence_verification=not_run; authority_effect=none
```

| Exit | Meaning |
|---|---|
| 0 | The selected file passed this bounded format check. `--help` also exits 0 without a success marker. |
| 1 | File/JSON admission or the legacy contract failed. |
| 2 | Argument parsing failure, not an evidence result. |

A valid historical file may still contain `ANCHORED`, `ANSWER`, `OPEN` or `low`,
because the unchanged schema permits these values as data. This checker neither
adopts those labels nor verifies their measurement basis. Accepting a historical
format is not a release decision, permission to assert, successful cycle check,
semantic-support result or execution attestation.

Only [WP2H](ANCHOR_INTEGRITY_v0_1_WP2H_DIAGNOSTIC_INTEGRATION.md) performs its
selected fresh diagnostics on explicit evidence inputs. No check is invoked or
inferred from this legacy format result. No output feeds normative gate state.

## 6. Bounded and inert diagnostics

Do not echo the input path, raw JSON, unknown key names, supplied enum values or
OS exception text into workflow annotations. Parse failures use fixed codes;
shape errors contain only fixed field names and bounded numeric list indices.
Retain at most 64 contract errors and report that further errors may be omitted.
Reaching that limit cannot change rejection into success. This is deliberately
not an exhaustive diagnosis of every fault in malformed input.

Diagnostic wording intentionally changes. Consumers must use exit status and the
explicit `format_only` boundary, not treat `[OK]` as a safety or authority PASS.
The successful function API remains `(True, [])`; failures remain `(False, errors)`.
There is no private key, signing interface, subprocess, model call or file-output
option in the corrected checker.

## 7. Reproduction and tests

The historical fixture pins repository/path, source commit, Git blob, byte count
and SHA-256 and stores the exact source as base64 data. Tests verify those bytes
before loading the archived checker in a temporary directory. They reproduce the
five observed false acceptances and demonstrate rejection by the corrected code.
The old failure modes are retained as test history, not as a selectable runtime
compatibility mode.

Additional regressions cover current and historical positive files, missing and
extra fields, an independent frozen-schema comparison, exact numeric boundaries,
malformed input, quoted delimiters, resource limits, symlinks/FIFO rejection,
observed read mutation, descriptor closure, diagnostic injection resistance and
the producer -> checker -> reader path. The current producer still emits null
measurements even when every operational gate is true.

From a reviewed checkout with the existing development dependencies:

```sh
python -m pytest -q tests/test_anchor_integrity_v0_1_contract.py -k wp2k
python -m pytest -q tests/test_anchor_integrity_v0_1_contract.py
python tests/test_anchor_integrity_v0_1_contract.py
python scripts/check_anchor_integrity_v0_contract.py --in examples/anchor_integrity_v0_1/wp2j_legacy_producer/expected.json
python scripts/check_anchor_integrity_v0_contract.py --in examples/anchor_integrity_v0_1/wp2i_legacy_reader/legacy.json
```

The last two are format-only positives, including the explicitly historical file.
Test results and preparation environment are reported in the delivery evidence,
separately from a future hosted PR check. The checker uses only the standard
library. The inherited Anchor suite still needs its existing dependencies and
OpenSSL runtime. POSIX file-boundary regressions are not Windows qualification.

No workflow, CI manifest, dependency, producer, renderer, schema, prior WP2A-H
tool, gate policy, status carrier, required gate or release-authority change is
included. No historical artifact or published site is rewritten. A native
collector and evidence-acceptance policy remain later, separately bounded work.
