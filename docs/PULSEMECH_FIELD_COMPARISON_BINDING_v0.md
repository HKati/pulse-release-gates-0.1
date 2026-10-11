# PULSEmech field comparison binding v0

## Evidence-bound comparison of domains, metrics and field samples

```text
document_role: supporting_transition_meter_contract
repository_integration_status: documentation_with_companion_source
implementation_scope: offline_synthetic_comparison_with_diagnostic_status_views
transport_profile: reference_label_and_rational_scalar_identity
transition_path_application_status: specified_not_executed
physical_validation_status: not_performed
authority_effect: none
```

This supporting contract makes field comparability explicit under the existing
Transition Meter architecture. It adds a minimal reference-based carrier and a
finite executable example. The canonical status vocabulary and release-authority
path retain their current definitions.

> A field sample does not establish field identity. Equal observation projections
> do not establish equal transitions.

## 1. Existing basis and the additional carrier

The basis is the reviewed source snapshot
`3aa05dd7f8f95f30d75ab38bdb46419e3735c58c`:

- [Workshop theorem, §§3.2–3.3 and 5.3](PULSEMECH_WORKSHOP_DECIMAL_ACCUMULATION_AND_DIMENSION_OPENING_THEOREM_EN_v0.md):
  fix the common complete-response codomain, input/state embeddings, evaluator
  and any selected response projection before selecting a witness. Embeddings
  must preserve meaning rather than manufacture the claimed difference.
- [Relation-preserving discrimination, §§2 and 8.2–8.4](PULSEMECH_RELATION_PRESERVING_DISCRIMINATION_v0.md):
  identify a named target only when a nonempty compatible set has one target
  value; distinguish this from full configuration or path identity.
- [Transition Meter, §§11, 14–20 and 23](../PULSEMECH_TRANSITION_METER.md):
  preserve domain responsibility, endpoint/relation identity, evidence coverage,
  independent status groups and unresolved alternatives.

Those requirements imply a comparability obligation for field claims. They do
not themselves provide a domain-specific transport verifier. The concrete
addition is `comparison_binding`: references to the domain, field type,
endpoints, transport, observation normalization and target/comparison rule.

The [schema](../schemas/pulsemech_comparison_binding_v0.schema.json) fixes carrier
shape. The [synthetic companion](../examples/comparison_binding_v0/README.md)
checks the supported finite semantics and reference digests. Scientific validity,
calibration and faithful correspondence require the relevant domain verifier.

## 2. Formal comparison boundary

Write the endpoint objects as

```math
(D_0,g_0,F_0,O_0) \xrightarrow{\mathcal T,\phi} (D_1,g_1,F_1,O_1).
```

The domain adapter must bind what the declared domains mean and which
correspondence is justified. Let the verified embeddings into a common reference
domain D be i0 and i1, and their images U0 and U1. For a supported linear field
fiber, typed transports Pi0 and Pi1 permit

```math
\Delta F=\Pi_1 F_1-\Pi_0 F_0\quad\text{on }U_0\cap U_1.
```

A metric comparison similarly requires justified pullbacks to the same tangent
structure. The general metric and tensor transports are obligations, not
implemented operations in this scalar companion. A subtraction of values on
unmatched domains or incompatible fibers is not a valid field comparison.

Record U0 minus U1 and U1 minus U0 separately. A verified removed support point
does not acquire a zero-valued field extension. Observation coverage C0 and C1
is separate from system support: numerical sample differences are available
only on the common, successfully observed support.

A different coordinate description or observation operator is admissible only
through verified normalization preserving the declared comparison meaning.
Literal domain equality or an unchanged instrument is therefore not a universal
requirement. This particular adapter supports identity transport and a fixed
synthetic frame, so unsupported changes remain unbound or rejected.

## 3. Minimal comparison_binding carrier

| Required field | Bound content |
|---|---|
| `schema_version` | Literal `comparison_binding_v0`. |
| `authority_effect` | Literal `none`. |
| `reference_domain_ref` | Common reference domain and its declared meaning. |
| `field_type_ref` | Value/fiber type, units and supported comparison. |
| `source` | State, system support, successful sample coverage, metric and observation frame. |
| `target` | The same endpoint obligations. |
| `transport_ref` | Typed domain/fiber correspondence, checked by the domain adapter. |
| `observation_normalization_ref` | Common observation interpretation fixed before comparison. |
| `comparison_rule_ref` | Target, admissible model, comparator, uncertainty and missing-data rules. |

Each known reference is an `artifact_id`/`sha256` pair. Endpoint support and
coverage use separate typed bindings: `known` with a reference, or `unknown`
with a reason. Unknown is not an empty set. Omitting either binding or supplying
JSON null is invalid. The referenced frame binds operator, units, resolution,
boundary conditions, synthetic ordering and uncertainty.

A digest does not authenticate a producer or prove a correspondence. A
self-asserted verification flag cannot substitute for transport evidence.
The internal evaluator packet is built after fixture validation; its required
boolean flags, exact rational numbers and immutable support memberships are
checked without truth-value or numeric coercion. A hand-constructed valid packet
still does not constitute authenticated physical evidence.

## 4. Target-relative alternatives

Fix the comparison target q and admitted model M before evaluation. Define

```math
C(E)=\{m\in M\mid m\text{ is compatible with the bound evidence }E\},\qquad
V_q(E)=\{q(m)\mid m\in C(E)\}.
```

| Local assessment | Condition |
|---|---|
| `UNBOUND` | Required comparison meaning is unavailable; compatible count and target set are unknown, not empty. |
| `INCOMPATIBLE` | C(E) is genuinely empty; no vacuous identification. |
| `UNRESOLVED` | C(E) is nonempty and more than one target value remains. |
| `IDENTIFIED` | C(E) is nonempty and Vq(E) is a singleton. |

Several configurations may establish one narrow target. This does not identify
a unique path, necessary cause or complete field. A finite candidate set is not
an exhaustive set of physical transitions.

Alternative access-path closure and physical alternative-path closure remain
separate. In the companion, primary and backup support routes read the same
receipt. Removing the primary route leaves the backup. Removing both restores
A/C ambiguity without changing the fixture or evaluator. This is a bounded
binding-ablation control, not process isolation or the Workshop's complete
release-authority graph cut in §16.5.

## 5. Status binding without a new canonical axis

The companion emits target-scoped diagnostic views containing all six canonical
groups from Transition Meter §18 in `status_axes`. Local `IDENTIFIED`, field
identity labels and the unit-test `PASS` do not replace these groups.

| Canonical group | Diagnostic binding in this example |
|---|---|
| `observation_status` | Derived complete comparison → `reconstructed`; missing comparison coverage/support → `partially_observed`; unbound comparison → `not_observed`. These refer to synthetic comparison evidence, not physical observation. |
| `binding_status` | Required claim bindings available → `bound`; support still unresolved in a geometry projection → `partially_bound`; unusable comparison meaning → `unbound`; contradictory endpoint-support receipts → `identity_conflict`. |
| `consistency_status` | One target value → `consistent`; several values or unresolved scalar identity → `ambiguous`; empty compatible set → `conflicting`; unbound comparison → `internally_incomplete`. |
| `reproduction_status` | The same evidence is evaluated again and equality is checked → `bounded_replay_only`. This does not assert physical or cross-instrument reproduction. |
| `causal_status` | Always `not_evaluated`; this example has no path or causal experiment. |
| `authority_status` | Always `diagnostic`, with `authority_effect: none`; no policy activation. |

The more specific obligations discussed during contract design fit inside these
existing groups and the claim/evidence structure:

| Detailed obligation | Existing location and permitted conclusion |
|---|---|
| Relation-change observation | Observation/consistency, with the named field or geometric target; agreeing samples alone cannot identify the full field. |
| Endpoint binding | Binding, with state/support/coverage/metric/frame/transport references. |
| Time ordering | Binding/evidence structure; only synthetic step 0 then step 1 is bound here, not real event timing. |
| Transition-path verification | Path/evidence layer; remains unexecuted in this companion. |
| Alternative-path closure | Alternative-path/consistency layer, with explicit access-versus-physical scope. |
| Causal sufficiency and necessity | Causal group; neither is inferred from geometric target identification. |

These are obligations, not newly activated status axes. The status view is not
a complete physical transition record.

Two controls make the separation executable:

1. B's negative volume-change target is identified with two remaining candidate
   configurations; its geometry view still has `partially_bound` endpoints.
2. A scalar difference can prove nonidentity despite another missing sample;
   consistency becomes `consistent` while observation stays `partially_observed`.
   Conversely, A's geometric expansion remains identified after sample loss
   while whole scalar identity remains ambiguous.

## 6. Three synthetic fixtures

The reference has 64 equal-volume cells, reference volume 1 and nonzero constant
spatial curvature magnitude 1. All source supports are full, with scale 1.
For a uniform spatial scaling g1 = r²g0 in dimension 3, the declared model uses
curvature ratio r⁻² and volume ratio r³f, where f is the retained reference
domain fraction. This is a generic geometric model, not an empirical claim.

| Fixture | Scale ratio r | Support fraction f | Curvature ratio | Volume ratio | Meaning |
|---|---:|---:|---:|---:|---|
| A | 2 | 1 | 1/4 | 8 | Expansion and flattening on fixed support. |
| B | 1/2 | 1 | 4 | 1/8 | Uniform contraction on fixed support. |
| C | 2 | 1/64 | 1/4 | 1/8 | Smaller declared support with locally expanding metric. |

C does not establish physical disappearance or uniform contraction of the whole
space. At real-world intake, the meaning and membership of the domain must be
verified. Sensor coverage alone cannot establish C's support reduction.

The four admitted candidates combine r in {1/2, 2} with support in {all cells,
cell:000}. A and C have the same curvature projection but opposite volume-change
signs. Without support evidence, both signs remain possible. B identifies the
negative sign without selecting a unique configuration.

The R05 sensor-loss control keeps A's system support full while acquiring only
cell:000. Its curvature and available scalar samples then equal C's. Its bound
volume ratio stays 8, while C's is 1/8. No fourth fixture file is added: the
control uses an in-memory copy of A.

## 7. Missingness and regression inventory

| Situation | Numerical difference | Permitted scalar conclusion |
|---|---|---|
| Sample absent on retained support | `unobserved`, `value: null` | Agreeing remaining samples leave full identity unresolved. |
| Coverage unknown | `unbound`, `value: null` | The field comparison is UNBOUND; unknown is not empty. |
| Coverage binding omitted or null | Contract rejection | No result promotion. |
| Known empty acquisition coverage | All retained points unobserved | Does not establish a zero field. |
| Target measured 0, source measured 1 | `observed`, value `"-1"` | Measured difference is retained. |
| Verified removed target support | `outside_target_support`, `value: null` | Support inequality; no zero extension. |

The finite scalar-field identity target includes its declared support. It does
not concern metrics, continuous within-cell fields, full configurations or paths.
JSON null is a missing-difference marker paired with a status, never a number.
Any future consumer must preserve this distinction at its own boundary.

| Test group | Methods | Coverage |
|---|---:|---|
| T01–T12 | 12 | Geometry, equal projections, support discrimination, backup routes, narrow targets, unbound frames and conflicting evidence. |
| Z01–Z06 | 6 | Missing samples, omitted/unknown coverage, empty acquisition, measured zero and removed/unknown support. |
| R01–R05 | 5 | Sixteen per-cell combinations, twelve endpoint binding controls, four absent/null sample controls, strict internal packet types and sensor loss. |
| S01–S06 | 6 | Explicit six-axis views, incomplete bindings despite identification, conflict, partial observation and claim separation. |

The 29 companion methods and two integration tests run through
`tests/test_comparison_binding_v0.py`, registered in the existing targeted pytest
manifest. No workflow edits are required. The
[reference result](../examples/comparison_binding_v0/results.json) records actual
offline execution, payload-source digests and diagnostic status views; the
[test log](../examples/comparison_binding_v0/TEST_RESULTS.txt) records its test run.

## 8. Boundaries

The supported schema subset is checked offline; full Draft 2020-12 conformance
is not claimed. General field bundles, nontrivial coordinate maps, numerical
metric differences, instrument calibration, empirical uncertainty, causal
necessity and full physical transition-path closure require further domain
evidence and implementation. A changed metric can be state evolution under
unchanged dynamics; this example does not establish self-development.

The release-authority path, required gates, policy, workflow source bindings,
Q2 workstream and canonical Transition Meter definitions are unchanged.

```text
A mezőalapú kiegészítés az összehasonlíthatóság kötési szerződése.
Az egyező mezőminták nem bizonyítják a teljes mező azonosságát.
Az azonos vetület mögött eltérő tartomány- és metrikaváltozás állhat.
A hiányzó megfigyelésből nem lesz numerikus nulla vagy fizikai eltávolítás.
A cél azonosítása nem emeli igazolttá az átmeneti utat, az okságot vagy az authorityt.
```
