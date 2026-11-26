# Anchor Integrity v0.1 WP2I — legacy reader boundary correction

**Status:** prepared reader-surface correction; diagnostic only.  
**Preparation base:** `7d5dc991194a641661bd3e6d13c6db6f96e24ebd`.  
**Reader profile:** `legacy-v0-proxy-boundary-v1`.  
**Authority effect:** `none`. **This is not a site deployment.**

## 1. Change the existing reader, not another evidence layer

[WP2H](ANCHOR_INTEGRITY_v0_1_WP2H_DIAGNOSTIC_INTEGRATION.md) added a fresh,
separately versioned diagnostic pipeline. It did not replace the old v0 reader.
WP2I now changes the existing
[`render_anchor_integrity_overlay_v0_md.py`](../scripts/render_anchor_integrity_overlay_v0_md.py)
entrypoint's default Markdown presentation. This is an intentional compatibility
change to rendered labels and headings, not to the legacy producer or its JSON.

The raw v0 JSON is unchanged. The old producer still derives its
`invariants.anchor_coverage` value from heterogeneous gate signals and may emit
`loop_risk=low` without cycle computation. No machine consumer of that raw JSON
is migrated by this package. The producer, schemas, WP1 historical inventory,
WP2A–H tools, gate policy, status and release-authority path are not modified.

The old Markdown reader previously presented legacy state, response mode,
gate action, coverage and risk under summary/invariant headings. WP2I stops
adopting those declarations as evidence conclusions. It does not turn their
absence into an instruction to silence a response.

## 2. Corrected display semantics

| Legacy input | Corrected reader treatment |
|---|---|
| Numeric `invariants.anchor_coverage` within [0,1] | Reported gate-signal proxy only; not recomputed, rounded, or interpreted as claim evidence. |
| Missing/null proxy | Unavailable and null, not zero coverage. |
| Boolean, string, percentage, out-of-range or non-finite proxy | Invalid and null; no coercion or percentage scaling. |
| `anchor_presence`, state and response/gate recommendation | Not adopted as claim presence, support, permission or current recommendation. |
| `loop_risk`, `contradiction_risk`, source presence | No measured result. Evidence/cycle/risk rows remain `not_run` / `null`. |
| Rationale, free-text evidence notes, added success fields | Not rendered as findings; retained only in the original JSON. |
| Selected metadata | Bounded literal text in an explicitly unverified metadata section. |

The heading identifies a **legacy v0 proxy view** and the reader profile. It
always states that fresh evidence checks were not executed and authority is
none. This is not a fresh WP2H run. No signature verification, graph analysis,
claim extraction, semantic verdict, response recommendation or runtime capture
is performed by the renderer.

For actual fresh diagnostics, use the unchanged WP2H entrypoint with explicit
selection, expected digests and evidence roots. A legacy JSON object alone
cannot substitute for those inputs. WP2H reports are not accepted as v0 objects
or relabelled by this reader.

## 3. CLI and input/output behavior

Keep the same `--in` / `--out` arguments and default paths:

```text
input:  PULSE_safe_pack_v0/artifacts/anchor_integrity_v0.json
output: PULSE_safe_pack_v0/artifacts/anchor_integrity_overlay_v0.md
```

Existing callers of this script get the corrected presentation when they run
the updated script. Consumers that parse the old Markdown headings must migrate;
there is no claim of byte-compatible Markdown output. Existing raw JSON and
already published copies are not edited by this source change.

Use only Python standard-library modules. This reader does not inherit the
OpenSSL or JSON Schema runtime requirements of receipt mode. Local validation
was on Linux; no Windows execution qualification is implied.

Read at most 8 MiB plus one overflow-detection byte, decode strict UTF-8 and
reject duplicate JSON keys, non-finite numeric values, malformed/trailing JSON,
unsupported schema tags and non-object invariants. This is format admission,
not complete legacy schema validation or origin authentication. Scalar metadata
is bounded and encoded as ASCII JSON literals with code-delimiter and HTML
characters escaped. Free-form legacy prose is not injected into the view.

A missing, unreadable or malformed input writes an explicit **UNAVAILABLE**
placeholder and returns zero, preserving CI-neutral rendering behavior. The
measurement rows still remain not_run/null; exit zero only means the view was
written, not that any evidence check passed. Invalid proxy values likewise
remain visibly invalid without becoming a gate result.

Explicit output writes remain supported. Reject an output path resolving to
the input, a symlink destination, a hard-linked existing destination, and a
non-regular existing target. Output errors return 2. These checks protect the
ordinary caller-controlled local invocation from accidental source overwrite.
They do not provide hostile-filesystem/concurrent-writer containment, atomic
publication, authenticated storage, or a sandbox. The output directory and
host remain trusted; no new repository-write privilege is acquired.

## 4. Reproducible historical reader and design

The original reader and original design note are retained as exact base64 bytes
in the data-only
[`legacy_reader_7d5dc991.source.json`](../tests/fixtures/anchor_integrity_v0_1/legacy_reader_7d5dc991.source.json)
fixture. They are bound to repository, source commit, byte length, Git blob
identity and SHA-256. The runtime renderer never loads or executes this fixture.
The test suite decodes the fixed, digest-checked historical reader into a temporary
directory and reproduces its original output on the synthetic example.

| Original file | Bytes | Git blob |
|---|---:|---|
| `scripts/render_anchor_integrity_overlay_v0_md.py` | 7,966 | `73ec5aeabeb05d6018be62fa79954e1c73dfe0a9` |
| `docs/ANCHOR_INTEGRITY_v0.md` | 8,134 | `31188dfe1a33012d8869f035612d4d3e98515e0a` |

The existing [v0 design note](ANCHOR_INTEGRITY_v0.md) receives a prominent
implementation-boundary notice; its original title and body are retained.
The frozen WP1 inventory remains a record of its original source revision,
not an assertion that the current reader still has the historical blob hash.
No historical evidence digest or example is silently rebound.

## 5. Synthetic example

The [input](../examples/anchor_integrity_v0_1/wp2i_legacy_reader/legacy.json)
contains an authored legacy proxy of 1.0, an ANCHORED/ANSWER/OPEN declaration,
and a low loop-risk label. These are synthetic data, not an observed verifier run.

Run from the repository root, writing to a temporary destination:

```sh
python scripts/render_anchor_integrity_overlay_v0_md.py \
  --in examples/anchor_integrity_v0_1/wp2i_legacy_reader/legacy.json \
  --out /tmp/anchor-wp2i-legacy-view.md
```

The result matches
[`expected.md`](../examples/anchor_integrity_v0_1/wp2i_legacy_reader/expected.md):
reported operational proxy 1.0; every evidence/cycle/risk result null; no adopted
state, response/gate recommendation, semantic support or release permission.
The original input bytes are unchanged. The same example, rendered with the
archived implementation, reproduces the old presentation rather than rewriting
history to look corrected.

## 6. Integration and tests

Append focused regressions to the already registered
[`test_anchor_integrity_v0_1_contract.py`](../tests/test_anchor_integrity_v0_1_contract.py)
module. Preserve the existing tests and direct entrypoint. Neither CI manifest,
count consumer nor workflow is changed. At the preparation base the manifests
contain 175 tools and 31 targeted-pytest entries.

Tests cover exact historical-source binding/replay, original design preservation,
proxy versus evidence separation, unmeasured risks, ignored legacy advice,
wrong formats, duplicate/malformed/oversized input, literal metadata rendering,
determinism, CLI defaults and unavailable placeholders, input/output aliases,
unchanged producer bytes and absence of new network/execution interfaces.

Actual executed test counts and environment are recorded in the separate delivery
report, not invented here as hosted CI. The final PR head needs its own CI and
review. This change is neither an independent security audit nor a production
accuracy measurement.

## 7. Publication scope and remaining work

The source searches at the pinned base locate the producer, reader, documentation,
historical inventory and fixtures. The searches do not establish an exhaustive
inventory of dynamic/external callers or deployed sites. No current workflow
caller or deployed URL is assumed merely because the old design roadmap names it.

This is not a site deployment: no Pages workflow, site manifest, existing artifact,
remote file, normative gate, status or release-authority input is changed. The
source-level human-reader correction is implemented here; migration of direct
v0 JSON consumers and regeneration of any deployed copies remain explicit tasks.
No workflow dispatch, model call, operational verifier/observer execution or
native experiment is authorized by this package.
