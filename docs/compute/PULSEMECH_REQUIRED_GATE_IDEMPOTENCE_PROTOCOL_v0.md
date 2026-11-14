# Selected snapshot-sanitizer idempotence protocol v0

Implementation continuation: the [offline observation adapter](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_OBSERVATION_v0.md)
now verifies selected bytes and recorded first-to-second application relationships
through an explicit standalone profile. The proposal and its three companions
remain the original selection; actual acquisition, runtime closure, property
calculation and B2 completion remain separate.

The [acquisition continuation](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_ACQUISITION_v0.md)
adds source preparation and bounded worker/process primitives with synthetic
orchestration tests. Observed launch remains closed pending recoverable runtime
closure and review; the original proposal and companion bytes below are retained.

## Status and scope

**Status: proposed for review. B2 is not complete.** This package selects a
concrete finite component protocol for the next implementation review. It adds
no collector, launcher, metric producer, independent checker or release recipe.
No operator, model or workflow is executed; no outputs are acquired and no
metric verdict is recorded.

Protocol ID: `epf_snapshot_idempotence_v0`. Preparation uses repository source
`97ab500bb9936c27632e1f40ab891d2442476786`, after the corrected B1 merge in
[#3018](https://github.com/HKati/pulse-release-gates-0.1/pull/3018).

The [accepted coverage plan](PULSEMECH_COMPUTE_REFERENCE_READINESS_v0.md#186-ordered-implementation-units-and-acceptance-conditions)
requires a concrete protocol before B2/B3 execution work. This proposal follows
the [B1 suite contract](PULSEMECH_REQUIRED_GATE_SUITE_CONTRACT_v0.md) and leaves
its existing schema, checker and fixtures unchanged.

| Companion | Responsibility |
| --- | --- |
| [Protocol proposal](required_gate_idempotence_protocol_v0/protocol_proposal_v0.json) | Fixed configuration, source bindings, finite scope, planned carrier and implementation boundaries. |
| [Selected inputs](required_gate_idempotence_protocol_v0/inputs_v0.json) | Exact twelve public input objects, their identities and byte bindings. |
| [Observation mapping](required_gate_idempotence_protocol_v0/observation_mapping_v0.json) | Planned first/second execution and derived-input relationships; explicit unsupported implementation gaps. |

The candidate gate association is `psf_idempotence_ok`. Its release applicability
has **not** been accepted. All twelve unsupported gate classifications remain;
this component proposal supplies no replacement gate result.

## Selected real component

The selected function is
[`sanitize_snapshot_for_log`](../../PULSE_safe_pack_v0/epf/epf_hazard_adapter.py)
in the existing EPF adapter. Its real caller, `probe_hazard_and_append_log`,
places the returned sanitized snapshot into the logged `snapshot_current` or
`snapshot_reference` field. The selected state is that snapshot component.

The function returns `(sanitized_snapshot, metadata)`. Define the composed
operator as `F(x) = sanitize_snapshot_for_log(x, fixed_configuration)[0]`.
Preserve both metadata records as diagnostics, but exclude metadata from the
composed state and equality comparison. Drop and truncation counters describe
each traversal and may change after the first sanitization. This projection is
fixed before acquisition; it is not chosen to discard an observed difference.

The proposed configuration is explicit:

```json
{
  "max_depth": 2,
  "max_items": 3,
  "allowed_prefixes": ["metrics"],
  "deny_keys": ["metrics.pii", "metrics.secret"]
}
```

The selected module and its three imported EPF modules are byte-bound in the
proposal. The future harness must call the selected function directly. It must
not invoke hazard forecasting, log append operations, calibration discovery or
ambient FieldSpec configuration. Source-byte selection is not proof of an
executed host or complete runtime acquisition.

## Finite input domain

The selected inputs are authored public JSON objects, not captured user data.
The exact objects reside in the input companion; this table states coverage.
All names, numeric values and sentinel strings are invented test material.

| Case ID | Selected boundary |
| --- | --- |
| `idem-01` | Empty object. |
| `idem-02` | Already admissible numeric snapshot. |
| `idem-03` | Boolean and integer coercion. |
| `idem-04` | Numeric strings with whitespace, signed zero and exponent notation. |
| `idem-05` | Public nonnumeric text, null and the string `"NaN"`. |
| `idem-06` | List rejection and nested numeric retention. |
| `idem-07` | Exact-key and subtree deny rules. |
| `idem-08` | Fields outside the allowed `metrics` scope. |
| `idem-09` | Retained depth boundary and a deeper mapping. |
| `idem-10` | Exactly three numeric leaves. |
| `idem-11` | A fourth leaf beyond the fixed item budget. |
| `idem-12` | Empty mappings and branches emptied by filtering. |

The finite roster is fixed before acquisition. No case may be omitted,
substituted or reclassified after its output is observed. There are exactly
twelve first applications and twelve second applications: 24 distinct planned
operator applications in one attempt. Empty cases remain part of the declared
coverage; they do not replace the nonempty cases.

## Composition and exact comparison

For every selected case `x`, the future acquisition must establish:

1. The first execution consumes the pinned initial input and produces `y1`.
2. A distinct second execution consumes the **actual first output** `y1` and
   produces `y2`, using identical selected code and configuration.
3. The independent calculation compares the canonical snapshot bytes of `y1`
   and `y2` and accounts for every declared pair.

The property is `F(F(x)) = F(x)` over this finite suite. Repeating `F(x)` twice
from the original input establishes repeatability, not this consumption and
composition relation. The older
[invariant notes](../STATUS_INVARIANTS_NOTES.md)
describe repeatability; this scoped proposal does not redefine those historical
notes or the canonical release contract.

Use this exact snapshot codec under the proposed CPython 3.11.16 runtime:

```python
(
    json.dumps(snapshot, sort_keys=True, separators=(",", ":"),
               ensure_ascii=True, allow_nan=False)
    + "\n"
).encode("utf-8")
```

JSON loading rejects duplicate keys and nonfinite numeric values. `"NaN"` in
`idem-05` is a string, not a nonfinite JSON number. Preserve the codec's signed
zero representation; use byte equality, not Python's permissive numeric object
equality, numerical tolerance or an unspecified JSON normalization. The future
second execution consumes the first canonical snapshot carrier bytes, with
their exact size, digest, producer execution and state identity retained.

A missing, duplicated or misbound pair is invalid evidence. A complete valid
pair with unequal outputs is a valid negative property result. A finite
positive result would establish only this selected composition property. An
operator that discards everything can also be idempotent: idempotence alone
does not prove useful retention, sanitization effectiveness, privacy protection
or model safety.

## Acquisition, limits and preservation proposal

The proposed runtime is CPython 3.11.16, Unicode 14.0.0, on Linux/POSIX. The
future implementation must bind its actual source and runtime before a run.
No executable adapter or completed runtime closure is supplied here.

| Proposed bound | Limit |
| --- | --- |
| Operator applications | 24, one attempt; no retry or top-up. |
| Worker wall time / CPU time | 5 seconds / 2 seconds. |
| Worker address space | 256 MiB. |
| Whole-suite wall time | 180 seconds. |
| Initial selected input | 1 KiB. |
| Each canonical snapshot, including second-application input | 4 KiB. |
| Metadata / diagnostic bytes per worker | 4 KiB / 4 KiB. |

These are proposed enforceable limits, not observed resource measurements.
Timeout, limit violation or missing output preserves an incomplete attempt;
it cannot be repaired by silently repeating or dropping the affected case.

The exact planned member inventory belongs to the protocol companion. A future
implementation must preserve the selected initial inputs, both snapshot
outputs, both metadata records, occurrence receipts and the existing compute
companions according to that reviewed inventory. No output content, output
digest or completed receipt is fabricated in this package.

The proposed layout separates a 95-member raw `acquisition.zip` from a six-member
outer observation bundle. Subject/runtime packets and the binding/relation
reports belong outside the raw acquisition they reference. Neither layer may
embed the digest of an enclosing manifest or archive that hashes that member.
The future adapter must validate this acyclic binding order; the proposed layout
is not an implemented acquisition profile.

Publish only the explicitly selected public test material and permitted
diagnostics. Generic runtime packets retain identities, digests and byte counts;
payload bytes remain in the separately bound carrier. Do not upload an entire
working directory or add credentials, environment dumps, raw prompts or real
personal information. Retention and cleanup must follow the reviewed companion
contract; publishing synthetic field names creates no real-PII claim. Normal
cleanup requires verified preservation of the actually produced permitted
evidence, including an explicit incomplete inventory when the attempt stopped.
An incomplete summary alone does not permit deleting the produced evidence.

## Two implementation gaps before substantive calculation

**Derived-input binding.** B1 v0 requires an occurrence's input to match its
case's independently selected input bytes. The unknown first output cannot be
preselected as observed evidence. A reviewed extension must represent and
verify the actual first-output-to-second-input relation. Two same-case
occurrences consuming the original input, or a prewritten expected output
substituted for the actual output, cannot satisfy this requirement.

**Supported acquisition profile.** The existing historical and bounded capture
profiles do not automatically support this new two-application suite. A narrow
producer/profile adapter must map its real occurrences into the existing
subject, runtime, binding and planned-observed contracts, with their strict
validators retained. The observation companion specifies the intended mapping;
it does not implement or certify that adapter. No second generic analyzer or
relation engine is proposed.

After both gaps are implemented and reviewed, B3 can add the property-specific
calculation and separate reconstruction. B4 retains coordinated intake and
independent admission; B5 retains separate authorization for the actual selected
reference run. A protocol review does not authorize those executions.

The original verification artifact, historical Q2 FAIL (49/50 with one UNKNOWN),
completed Q3 acquisition lineage and existing release decision remain unchanged.
Keep [#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) open.
`authority_effect=none`; `metric_pass=null`; execution authorization and
production-gate eligibility remain false.
