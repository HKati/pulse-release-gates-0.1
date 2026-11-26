# Anchor Integrity v0.1 — WP2B explicit JSON Pointer projection

**Status:** offline diagnostic implementation candidate
**Preparation base:** `7bb56fc801673ccf31ec92227bda56a4c240b357`
**Predecessor:** WP2A, merged by PR #2979
**Authority effect:** `none`
**Release-authority activation:** `false`

## 1. Purpose and narrow scope

WP2A intentionally leaves a JSON-pointer locator incomplete because the WP1
contracts specify a pointer but not the digest bytes of its selected value.
WP2B closes that projection gap through an explicit, versioned opt-in profile.
It does not reinterpret old inputs or complete the full Anchor adapter.

The existing input, claim, evidence and relation schemas stay unchanged.
The existing local-carrier/report v0.1 schemas and every historical example
stay unchanged. New local-carrier/report **v0.2** schemas identify this additional
profile; these version numbers do not rename the overall Anchor v0.1 effort.

## 2. Explicit invocation and compatibility

| Invocation | Accepted carrier | JSON-pointer behavior |
|---|---|---|
| No `--profile`, or `--profile wp2a` | `anchor_integrity_local_carriers_v0_1` | Existing incomplete result retained. |
| `--profile wp2b-json-pointer-v1` | `anchor_integrity_local_carriers_v0_2` | Resolve under the fixed profile below. |

The v0.2 carrier requires:

```json
{
  "schema_version": "anchor_integrity_local_carriers_v0_2",
  "json_pointer_profile": "rfc6901_source_spans_v1"
}
```

The caller must still supply both expected input and carrier SHA-256 hashes.
The carrier binds the exact input bytes, and its projection profile is inside
those hashed bytes. Missing/wrong profile or wrong schema is invalid. There is
no automatic migration, profile guessing, fallback or bundle-selected code.

The default old mode retains its report schema and decisions. Its checker
fingerprint necessarily changes when the installed checker source changes.

## 3. What the standard supplies, and what this profile adds

RFC 6901 defines how a pointer resolves a JSON value. It does not define a
hash representation for the selected value. RFC 8259 supplies JSON grammar.
The following two byte projections are **PULSEmech application rules**, not
an assertion that RFC 6901 prescribes canonicalization or digest semantics.

### Claim locator: `decoded_string_utf8`

The selected JSON value must be a string. Decode its JSON escapes, preserve
its exact Unicode scalar sequence, and encode that string as UTF-8. Compare
those bytes with the existing `claim_text` UTF-8 bytes. Independently retain
the full response hash and the original quoted-token byte span and hash.

Do not coerce an object, array, number, boolean or null into a claim string.
Do not normalize Unicode, trim whitespace or change line endings inside text.

### Evidence locator: `source_value_bytes`

Select the exact original byte interval occupied by the JSON value: from its
first token byte through its last token byte, excluding surrounding delimiter
whitespace. For an object or array, retain every internal byte. For a string,
retain the quotes and original escape spelling. For a number, retain the exact
lexeme, including exponent, fractional zeros and negative-zero spelling.

For example, the following selected values have different evidence digests:

```text
7
7.00e+0
"a"
"\u0061"
```

No parse-and-reserialize or canonical JSON fallback is used. Numerical values
are never converted to a binary float for projection. A finite JSON number
lexeme with a large exponent may be retained as bytes; this is not a numerical
range, precision or arithmetic claim.

## 4. Pointer resolution and input policy

Use the JSON string form of RFC 6901. Resolve object names by exact decoded
code points; decode `~1` before `~0`. Do not perform Unicode normalization or
percent decoding. URI-fragment form (`#/...`) is not accepted by this profile.

For arrays, accept only ASCII decimal indices with no sign or leading zero,
except the single index `0`. Reject `-`, nonexistent indices and traversal
through a scalar. Object names such as `01` or `-` remain ordinary names.
The existing packet schemas require pointers beginning with `/`; the empty
root pointer remains rejected there. The internal utility can resolve it,
which does not broaden those packet contracts.

Validate the **entire** source JSON document, not only the selected path.
Reject duplicate decoded object names at every depth, including unused
branches, invalid syntax, invalid UTF-8, BOM, trailing content and unpaired
surrogates. This is a deliberately strict application profile, not a claim
to accept every interoperability edge case permitted by JSON grammar.
JSON `null`, `false`, zero and empty containers are real values, not missing
nodes. Missing members cause an invalid locator result, not a null value.

## 5. Bounded execution and file handling

The existing POSIX `BundleReader` remains responsible for all input-file
reads: explicit root, bounded sizes, directory-relative no-follow opens,
single-link regular files, unique safe relative paths, and changed-file
rejection. A read snapshot is retained for the invocation. No network,
Git command, artifact execution or additional write output is introduced.

The fixed projector module is loaded only in the opt-in mode from the trusted
installation's `tools/` directory. It is not a plugin selected by input data.
Bytecode writing is disabled during that module load and the previous process
setting is restored. The report remains stdout-only.

Additional JSON projection limits:

| Resource | Limit |
|---|---:|
| Per-source JSON bytes | 8 MiB |
| Nesting depth (root depth zero) | 64 |
| Value/key nodes per document | 100,000 |
| Members per object or array | 4,096 |
| Pointer UTF-8 bytes | 4,096 |
| Pointer tokens | 64 |
| Cumulative projected plus selected-token bytes | 64 MiB |

The existing 64 MiB bundle read limit remains. A source document is parsed
once per retained bytes object; parsing failures are cached as failures.
The projection budget is charged after projection, so a final rejected
selection may temporarily process one additional bounded source value.
These are bounded-resource controls, not a host-wide sandbox guarantee.

## 6. Diagnostic report

The opt-in output is `anchor_integrity_binding_report_v0_2`, with
`work_package: WP2B` and the exact profile name. Retain existing root hashes,
checks, issue precedence, subject fields and recorded relation declarations.
Add the installed projector's SHA-256 to the implementation record.

Each successfully resolved pointer records:

- Object ID and claim/evidence purpose.
- Pointer and fixed byte-projection name.
- Complete source SHA-256.
- Zero-based half-open `start_byte` / `end_byte` interval.
- Selected JSON value type.
- Exact source-slice and projected-byte SHA-256 values.

A resolution receipt is not a successful expected-digest comparison by itself.
The separate existing comparison check must match. A parsed selection can be
recorded in an overall invalid report when its source or expected digest differs.
Receipts and checks are deterministically ordered. The schema constrains their
shape; it is not authentication of a saved report or independent replay proof.

Exit codes remain:

| Exit | Result |
|---|---|
| 0 | `LOCAL_BINDINGS_CONSISTENT` in the declared local scope only. |
| 1 | `LOCAL_BINDINGS_INVALID`. |
| 2 | `LOCAL_BINDINGS_INCOMPLETE`, or CLI/installation error. |

Invalid observations take precedence over incomplete observations. Missing
carrier bytes remain incomplete. Existing but malformed JSON, ambiguous keys,
nonexistent pointer targets, wrong projection types and hash mismatches are
invalid. A projection failure does not create a positive selection receipt.

Always preserve:

```text
candidate_status = diagnostic_only
authority_effect = none
release_authority_activation = false
requested_checks_complete = false
```

Authentication, semantic support, typed-cycle checking, response recommendation,
independent claim-set completeness and verified coverage remain unperformed
with null results. Recorded verifier labels cannot become accepted support.

## 7. Complete synthetic example

The eight files in
[`wp2b_json_pointer`](../examples/anchor_integrity_v0_1/wp2b_json_pointer/)
are a separate synthetic bundle. They do not rewrite the WP1/WP2A examples.
It contains two claim-string pointers and one evidence-number pointer; one
claim has a recorded anchor and the other does not. Neither is authenticated
or semantically verified by this checker.

From the repository root:

```bash
python tools/check_anchor_integrity_bindings_v0_1.py \
  --profile wp2b-json-pointer-v1 \
  --bundle-root examples/anchor_integrity_v0_1/wp2b_json_pointer \
  --input input.json \
  --expected-input-sha256 2551b182d5b31477d94df8cadf94a38120499d4ebe72b780dd1f00b1fa7e605a \
  --carriers carriers.json \
  --expected-carriers-sha256 dbed53cc547ea242cf3ef5111513b65dd8dd23a80d1994784a7c98ebf65be19e
```

These pins identify the reviewed synthetic fixture. They are not signatures.
For other inputs, retain expectations independently rather than deriving
"trusted" expectations silently from the untrusted input being checked.

## 8. Regression and integration boundary

Extend the already registered
[`test_anchor_integrity_v0_1_contract.py`](../tests/test_anchor_integrity_v0_1_contract.py).
Preserve all 268 WP1/WP2A cases and add 213 WP2B cases. Both manifests remain
byte-identical at the preparation base: **175 tools / 31 targeted pytest**.
Historical documentation counts remain historical, not current expectations.

Coverage includes explicit opt-in, profile substitution, old incomplete mode,
exact number/string/container bytes, decoded claim strings, escaped key names,
array index failures, duplicate keys outside the selected path, encoding and
resource limits, whole-source versus selected-content substitution, missing
carriers, invalid-over-incomplete precedence, deterministic reports, local
input preservation, and generated-tree comparison against independent decoded
JSON values. This is not exhaustive parser verification.

Local full-module validation: 481 cases passed (268 retained plus 213 added).
The preparation report separately records final-package replay and environment.
No hosted CI, full repository suite, actual acquisition or semantic evaluation
is established by these local results. Python 3.11 grammar checks do not replace
hosted 3.11 execution. The safe-reader profile remains POSIX-only.

## 9. Preserved boundaries and next work

No workflow, test manifest, dependency, existing schema/example, frozen WP1
contract, v0 adapter/renderer, policy, required gate, `status.json`, release
checker, Pages, OG, History, SARIF, Q3/W1, DOI or Software Heritage file changes.
No new test module registration or repository write path is added.

Verifier-record admission, provenance authentication, typed evidence-dependency
cycle evaluation and full adapter coverage/disposition logic remain separate
work. This package grants no workflow dispatch or model/native execution.

## References

- [WP1 contract](ANCHOR_INTEGRITY_v0_1_CONTRACT.md).
- [WP2A binding checker scope](ANCHOR_INTEGRITY_v0_1_WP2A_BINDINGS.md).
- [RFC 6901, sections 3–5 and 7](https://www.rfc-editor.org/rfc/rfc6901.html).
- [RFC 8259, sections 2–9](https://www.rfc-editor.org/rfc/rfc8259.html).
