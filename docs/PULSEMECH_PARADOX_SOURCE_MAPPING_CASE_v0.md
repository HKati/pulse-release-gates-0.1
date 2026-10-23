# PULSEmech / Paradoxon Diagram

## Source mapping case v0 — a gate–metric relation through M1–M3

**Date:** 2026-10-23  
**Case identifier:** `PD-SM-01`  
**Document role:** source-bound research case with manual derivations  
**Repository snapshot:** `HKati/pulse-release-gates-0.1` at `cbeab94d8532482d34ab857bf38e9e56ae265f84`  
**Predecessor:** [M1–M3 definition contract v0.2](PULSEMECH_PARADOX_M1_M3_DEFINITION_CONTRACT_v0_2.md)  
**Authority effect:** `none`

```text
document_status: research_source_mapping_case
assessment_method: pinned_source_inspection_and_manual_derivation
new_impact_engine_implementation: not_implemented
project_execution: NOT_RUN
software_trials: NOT_RUN
machine_checked_proofs: not_performed
independent_external_validation: not_claimed
authority_effect: none
```

No repository changes, test execution, producer execution, workflow dispatch, new measurement or proof-assistant run were performed for this case. The existing producer and checker programs were read, not executed. Files prepared for delivery are documentation, not generated Paradoxon outputs or verification receipts.

## 0. Result and exact claim

This case maps one existing `gate_metric_tension` relationship into the M1–M3 contract. The source is the repository-local example under `docs/examples/transitions_case_study_v0/`, not a newly invented monitoring fixture. The mapping follows source rows, the adapter's Atom construction, the tension Atom, the exported edge and the relevant checker conditions. [S1, S3–S12]

Three distinctions are preserved:

1. A changed endpoint is detectable even when the Atom population, metric values and number of edges are unchanged.
2. A missing source may remove justification of provenance without changing the internal relation or proving a physical violation.
3. Another correctly supported gate–metric relation may be valid, but a certificate about the original protected target does not thereby become a certificate about the replacement target.

The five variants below have manual reference outcomes. They are **not** recorded software-test results. This is a bounded correspondence for declared artifact relationships, not a proof of full Paradoxon fidelity, a physical mechanism, causal influence, general pre-execution safety or reduced correction cost.

The case also records two source-reading corrections: tension aliases are required by the pinned field checker, despite older prose calling them optional; and the canonical example acceptance entrypoint delegates to an implementation that reads existing field/edge files, rather than itself running the producer pipeline. Neither source is changed here. [S9, S11–S14]

## 1. Sources, scope and provenance boundary

### 1.1. Fixed source selection

All repository references in this document use the snapshot above. A source label identifies a path and, where useful, a function or exact record selector. The source register at the end provides commit-pinned links and connector-reported Git blob identifiers. Those identifiers describe repository blobs; they are not runtime observations or SHA-256 release attestations.

| Part of the case | Existing source | Use here |
|---|---|---|
| Definitions and proof limits | M1–M3 v0.2; glossary | Preserve the existing meanings and distinguish source facts from proposed mathematics. |
| Gate observation record | Gate drift CSV, data row 0 | Bind `gate_latency_budget` to its exact documented record. |
| Two metric records | Metric drift CSV, data rows 0 and 1 | Bind latency and CPU roles separately. |
| Context inputs | Transitions JSON and overlay JSON | Preserve their actual recorded example content and context contribution. |
| Producer rules | Field adapter; edge exporter | Derive the expected relation symbolically, without execution. |
| Contract checks | Field checker; edge checker with `--atoms` | Identify the implemented scope of link and context checks. |
| Example acceptance | Canonical wrapper and its delegated implementation | Identify the additional example-level coverage conditions. |

The example calls itself a docs run-pair and contains `status_sha1` values consisting of forty `1` characters and forty `2` characters. The overlay example similarly uses repeated-character values and explanatory notes. These values are preserved as example data. This work does not establish the existence or authenticity of the historical runs they might resemble. The directory's “non-fixture” label is not an empirical-provenance certificate. [S5, S6, S14]

### 1.2. Selected boundary

The full source example remains the boundary context. The main comparison selects one latency-related edge, its tension Atom, its gate Atom and its metric Atom. The CPU-related edge provides a separately bound alternative target. Overlay relationships remain background, not silently deleted proof premises.

This slice is **not** claimed to be the existing Paradox `Core`. Its sufficiency for the named checks is explained below; no broader isolation of the rest of the field follows. `Anchor`, `Orientation` and `Core` retain the glossary meanings. No new orientation calculation or Core construction is performed. [S2]

The records' A/B labels, source-row locations and run-pair metadata are preserved. They are not promoted into an assumed global time or a causal order for the mechanical theory.

## 2. Concrete input records

### 2.1. Gate record

The gate CSV has one data record, at zero-based data-row index 0: [S3]

| Field | Value |
|---|---|
| `gate_id` | `gate_latency_budget` |
| `group` | `perf` |
| `status_a`, `status_b` | `OK`, `FAIL` |
| `pass_a`, `pass_b`, `flip` | `true`, `false`, `1` |
| `value_a`, `value_b`, `threshold` | `120`, `450`, `200` |
| `notes_a`, `notes_b` | `within_budget`, `exceeded_budget` |
| `present_a`, `present_b` | `1`, `1` |

The adapter uses the supplied `flip` value and record fields; this case does not reinterpret `OK` as a different status token or claim that the adapter independently evaluates the gate's threshold. The physical unit of the gate values is not established by this CSV. [S3, S7]

### 2.2. Metric records

| Zero-based data-row index | `metric` | `a` | `b` | `delta` | `rel_delta` | Presence |
|---|---|---|---|---|---|---|
| 0 | `p99_latency` | `0.120` | `0.200` | `0.080` | `0.6667` | `1`, `1` |
| 1 | `cpu_util` | `0.650` | `0.670` | `0.020` | `0.0308` | `1`, `1` |

These are the existing records, not new measurements. The adapter parses their numeric fields and uses the supplied deltas. Its fixed warning thresholds are `0.01`, and critical thresholds are `0.05`, for both absolute and relative delta. Thus latency is critical and CPU is warning under that source rule. Both are eligible for gate–metric tension construction. [S4, S7]

The gate's `120`/`450` values must not be equated with the metric's `0.120`/`0.200` values by an invented unit conversion. The producer pairs eligible records by co-occurrence; it does not establish that either metric causes the gate change or measures the same quantity. [S7]

### 2.3. Background and bounded selection

Both `g_field_v0` and `paradox_field_v0` have nonempty changed-key lists in the overlay example, and both are allowlisted for overlay tension construction. [S6, S7]

Reading the constructor branches gives the following **expected construction counts**, conditional on normal successful execution and unique accepted IDs: one gate Atom, two metric Atoms, two overlay Atoms, two gate–metric tension Atoms and two gate–overlay tension Atoms: nine Atoms and four exported edges. These are manual construction counts, not observed output counts.

The adapter caps selected metric Atoms at 10 and each tension family at 50. Those caps do not truncate this small example. They prevent any unqualified extension of the case's coverage claim to arbitrary larger inputs. [S7, S8]

## 3. Source-bound identities and construction trace

### 3.1. Names used in the derivation

Let `a` and `b` denote the two example `status_sha1` strings in [S5]. Use these symbolic names:

| Symbol | Exact constructor expression or source role |
|---|---|
| `g` | `_atom_id("gate_flip", "gate_latency_budget", a, b)` |
| `mL` | `_atom_id("metric_delta", "p99_latency", a, b)` |
| `mC` | `_atom_id("metric_delta", "cpu_util", a, b)` |
| `tL` | `_tension_atom_id("gate_metric_tension", g, mL)` |
| `tC` | `_tension_atom_id("gate_metric_tension", g, mC)` |
| `kappa` | Adapter/exporter normalized context derived from the four pinned input files. |
| `eL` | `_edge_id("gate_metric_tension", g, mL, tL, kappa.run_pair_id)` |
| `eC` | `_edge_id("gate_metric_tension", g, mC, tC, kappa.run_pair_id)` |

These symbols denote the specified IDs; they are not purported hexadecimal output values. The constructor expressions are not executed here. An executable follow-up must materialize and check their uniqueness. Any ID collision is a failed binding condition, not permission to identify distinct roles.

The source Atom ID uses the first 12 hexadecimal characters of SHA-1 over `type|key|a|b`. The tension Atom ID uses the first 12 over `type:src:dst`. The edge ID uses the first 16 over `type|src|dst|tension|context_id`. These are the pinned programs' naming rules, not a new cryptographic assurance claim. [S7, S8]

In this input, the provided run strings are used for gate and metric Atom IDs rather than the fallback file-context digest. Therefore those Atom IDs are not full content hashes of their evidence payloads. A binding assessment must retain the actual source identity and payload; equality of one short ID is insufficient. [S7]

### 3.2. Context binding

The adapter includes content SHA-1 fields for the gate CSV, metric CSV, overlay JSON and transitions JSON. With no optional `--status` or `--g-field` inputs, these are the relevant file-digest keys. Its `run_pair_id` is derived from sorted `key=value` entries. The exporter carries the allowed stable subset. [S7, S8]

The source commit, program identities and case profile are additional bindings in this research document. They must not be described as fields already emitted in `run_context`.

The field/edge checkers compare recorded context values; they do not reopen all four raw sources to recompute them. Byte-to-context binding is consequently a separate assessment obligation. No independent digest revalidation of generated artifacts is claimed, because no such artifacts were generated or inspected in this task. [S9, S10]

### 3.3. Symbolic baseline records

The relation-bearing subset expected from the source construction is:

```text
g:  type = gate_flip
    gate_id = gate_latency_budget
    source = pulse_gate_drift_v0.csv, data row 0
    severity = crit

mL: type = metric_delta
    metric.name = p99_latency
    source = pulse_metric_drift_v0.csv, data row 0
    severity = crit

mC: type = metric_delta
    metric.name = cpu_util
    source = pulse_metric_drift_v0.csv, data row 1
    severity = warn

tL: type = gate_metric_tension
    gate_atom_id = src_atom_id = g
    metric_atom_id = dst_atom_id = mL
    rule = gate_flip × metric_delta(warn|crit)
    severity = crit
    copied gate/metric summaries = corresponding g/mL evidence

eL: type = gate_metric_tension
    src_atom_id = g
    dst_atom_id = mL
    tension_atom_id = tL
    rule = tL.evidence.rule
    severity = tL.severity = crit
    run_context = kappa
```

There is an analogous `tC`/`eC` pair with destination `mC`. Its tension and edge severity are also critical because the gate Atom is critical and the producer uses the more severe endpoint classification. Thus severity alone does not discriminate the latency and CPU relationships. [S7, S8]

This block is an annotated mathematical trace, **not** a JSON fixture and not a captured output file.

## 4. Mapping the existing structure into M1–M3

### 4.1. Configuration, Anchor and global correspondence

A case configuration contains typed source references, Atom records, tension records, edge records, a selected relation role, recorded context, and separately typed evidence-availability/justification information. Raw data, model assertions and accepted evidence statements remain distinct types.

The Anchor binds the repository snapshot, the selected source set, the association-only semantics, the case's relevance profile and the declared checker mode. A source and destination in the edge are role bindings, not a temporal or causal arrow.

The correspondence `J` is fixed for the entire comparison. It preserves source identities, program revisions, gate/metric names, ID bindings and record references unless a variant explicitly declares a replacement. It may rename notation such as `mL` in this document consistently; it may not turn the latency subject into the CPU subject by an unrecorded ID substitution. [S1, S2]

### 4.2. Mapping table

| Existing element | M1–M3 representation | Obligation preserved |
|---|---|---|
| Gate and metric CSV records | Typed source objects and source-bound values | Record selector, field meaning and exact source version. |
| Gate/metric Atoms | Elements of `A`, with typed data in `nu` | Distinct subjects, Atom type, source binding and evidence payload. |
| Tension Atom | A first-class Atom plus a higher-arity role relation in `R` | Gate, metric, aliases, rule and copied summaries belong to one record. |
| Exported edge | An edge carrier with an explicit link to its tension Atom | The endpoints must match that same tension's evidence. |
| Field and edge context | Recorded context in `nu`; pinned source map outside the old carrier | Context agreement and actual source provenance are separate predicates. |
| Checker conditions | Precisely scoped predicates | What each checker checks, not a generalized claim of truth. |
| Evidence applicability | Typed accepted premises and proof support | A file's presence, an internally consistent artifact and a source-bound derivation are different. |

This is an extension of the documented data's representation, not a redefinition of association as causal dependence. The higher-arity relation records an existing conjunction of role equalities; it does not claim that the current v0 exporter has implemented a general higher-order impact engine.

### 4.3. Case relevance is declared before the encoding

For this case, relevant distinctions are independently specified as: protected subject identity; source version and selector; endpoint/tension/alias binding; types; rule; severity agreement; context agreement; source-derived summaries; and current provenance justification. These come from the pinned producer/checker contracts and the stated research question, not retrospectively from whichever fields an encoding happens to retain.

The representation must preserve these distinctions. Titles, display paths and record enumeration order are not part of this case's semantic equality, but their exclusion does not authorize deleting them from real artifacts or ignoring byte-level checks.

### 4.4. Joint answer structure

Use one configuration-bound answer vector:

$$
\Phi(C)=\bigl(q_{\rm subject}(C),q_{\rm roles}(C),q_{\rm source}(C),
q_{\rm context}(C),q_{\rm conditions}(C),q_{\rm support}(C)\bigr).
$$

`q_roles` retains the common relation tuple, rather than separate endpoint sets:

$$
\bigl(e.id,e.type,e.src,e.dst,e.tension,\ t.id,
 t.gate,t.metric,t.srcAlias,t.dstAlias,\ g.type,m.type\bigr).
$$

The other coordinates retain the declared source references/values, normalized context, condition values, and typed proof premises and their availability. Condition values are derived annotations: a stored `true` is not accepted instead of the record equalities or the source-bound derivation. The sufficiency argument uses the retained inputs and fixed semantics, not an unverified outcome label. Source-origin claims remain conditional on the independently checked bindings stated in the case. For partial descriptions:

$$
\mathcal A(B)=\{\Phi(C):C\in\Omega(B)\}.
$$

Broken bindings are not removed from `Omega(B)` by assuming the desired invariant. Unknown evidence is not forced to true or false. An inconsistent empty completion family cannot yield a valid-preservation outcome. [S1]

**Bounded sufficiency argument.** On complete case records, each target predicate in Section 5 is a function of the fields retained jointly by `Phi`. Equal answer structures therefore preserve those predicates' possible truth values under M1's T2. Conversely, a different retained protected subject, binding or premise appears in the vector even if every aggregate count is unchanged. This establishes sufficiency for the named predicates, not full abstraction of arbitrary Paradoxon structures.

## 5. M2 — Exact persistence predicates

### 5.1. Internal relation condition

For the selected gate–metric edge `e` and its resolved records `t,g,m`, define:

$$
\begin{aligned}
K_{\rm link}(C) := {}&\operatorname{UniqueResolvedTyped}(e,t,g,m)\\
&\land e.tension=t.id\\
&\land e.src=t.gate=t.srcAlias=g.id\\
&\land e.dst=t.metric=t.dstAlias=m.id\\
&\land e.severity=t.severity\\
&\land e.rule=t.rule.
\end{aligned}
$$

The types are `gate_metric_tension` for edge and tension, `gate_flip` for the source, and `metric_delta` for the destination. Required aliases are part of this selected full-pipeline profile. Source facts for this condition are in [S8–S10].

This predicate has the same meaning in all variants. Rebinding `e` to a different supported tension changes its arguments and proof obligations, not the requirement itself.

### 5.2. Separate conditions

| Condition | Meaning | Source support / assessment boundary |
|---|---|---|
| `K_context` | All required normalized field/edge context values agree. | Edge and acceptance checks implement comparisons; input-byte binding is separate. |
| `K_origin` | IDs, source selectors, Atom data, summaries and context arise from the pinned inputs under the pinned constructors, with unique IDs. | Manual constructor trace here; not fully rederived by the generic output checkers. |
| `K_eligible` | The selected gate record has `flip=1`; the metric meets the producer's warning/critical selection rule and is not excluded by the bounded selection. | Adapter branch analysis for this exact small example. |
| `K_support` | The needed source bindings, semantics and inference premises have an accepted grounded derivation for this exact claim. | Research-level evidence applicability, not an existing release gate. |
| `K_serial` | The actual serialized files satisfy their canonical ordering and format contracts. | Field/edge validators; distinct from relation-level equality. |

The source-mapped case requirement is:

$$
K_{\rm case}=K_{\rm link}\land K_{\rm context}\land K_{\rm origin}
\land K_{\rm eligible}\land K_{\rm support}.
$$

`K_case` is a research assessment condition. It is not inserted into policy, `status.json`, a gate registry or the release authority. Raw-carrier acceptance also needs `K_serial`; semantic preservation alone cannot bypass it.

### 5.3. Existing enforcement is layered, not interchangeable

The field checker requires both tension aliases and checks their agreement with the type-specific keys. The exporter still has a legacy-key fallback. The edge checker validates aliases when present, and verifies endpoints against the tension's type-specific keys when its Atom lookup is nonempty. These are different contracts; the permissiveness of one component must not be silently treated as the full pipeline's guarantee. [S8–S10]

The edge checker does not recompute edge-ID hashes from all content. Context equality is not raw-source authentication. Optional provenance checks validate the shape of a source pointer, not the truth of the pointed-to source data. The example acceptance checker checks expected metric names via tension summaries/references; this is not a substitute for all endpoint checks or source reconstruction. [S9, S10, S12]

One additional precondition matters: the edge checker's link-validation branch is guarded by `if atoms_by_id`. Supplying `--atoms` must therefore not be summarized as unconditional proof of link coverage for an empty usable Atom map. This case explicitly requires a nonempty, complete lookup and treats missing scope as a coverage failure. No change to the checker is proposed or applied in this document. [S10]

## 6. Five manual variants

All variants are analytical descriptions. They are not file modifications made to the repository, and none has been executed. `PRESERVED`, `VIOLATED` and `UNRESOLVED` below describe a named research predicate, not CI outcomes or release permissions.

### V0 — Pinned baseline construction

**Subject:** the selected latency relation `(eL,tL,g,mL)`.

**Fixed context:** the four input files, the reviewed constructors, and their stated ID/normalization rules. All symbols are distinct as required for an accepted field. The background CPU and overlay relations remain present.

**Manual derivation.** The gate row enters the `flip=1` branch. The latency metric has absolute delta `0.080 >= 0.05`, so it is critical. The bounded candidate list contains only two metrics. The producer writes `g` and `mL` to both aliases and the type-specific keys in `tL`, copies the corresponding summaries, and the exporter takes the same endpoints and tension ID into `eL`. Severity and rule are copied consistently. Context comes from the same field metadata. [S3, S4, S7, S8]

**Result:** `K_link` and `K_eligible` hold for this symbolic construction; `K_origin` is supported as a conditional source derivation. Concrete artifact existence, hash uniqueness, byte identity and successful execution remain unobserved. No runtime success receipt is supplied.

This is a source-derived baseline, not a statement that new generated files have passed the checkers.

### V1 — Storage/enumeration order changes

**Change:** reorder the enumeration of already identified records in the mathematical view, while preserving every record, reference, source binding and protected identity. Let `sigma` be a permutation of that enumeration.

**Manual derivation.** Key-based resolution gives the same `e,t,g,m` tuple. Every equality in `K_link` and every source/support premise is unchanged. Hence:

$$
\Phi(\sigma C)=\Phi(C)
$$

for the declared semantic projection.

**Result:** relation semantics are `PRESERVED`.

**Carrier limit:** an arbitrarily reordered real Atom list or JSONL edge file may violate `K_serial` and be rejected by the existing validators. Recanonicalization may preserve logical records; changed bytes are not automatically the same artifact or signature subject. A raw CSV-row permutation is not the variant defined here: it also changes row pointers and file digests, and therefore requires an explicit rebinding assessment. [S7–S10]

### V2 — Endpoint changes but the supporting tension does not

**Change:** keep the baseline field and all its Atoms unchanged. In the selected edge, change only `dst_atom_id` from `mL` to the existing `mC`; retain `tension_atom_id=tL`, all source records and all other edge fields. No record or metric value is added or removed.

**Manual witness:**

$$
e.dst=mC,\qquad tL.metric=tL.dstAlias=mL,\qquad mC\ne mL.
$$

Therefore `K_link` is false. The distinction is visible in one common tuple even though the node counts, edge counts, source metric values and edge severity remain unchanged.

**Expected existing-checker behavior, not an execution result:** with the complete nonempty field supplied, the edge checker reaches the mismatch between `dst_atom_id` and `tension.evidence.metric_atom_id` and rejects. It checks the legacy keys before the optional alias cross-check. The field itself is unchanged and its link structure remains internally consistent. Keeping the old edge ID does not mask the endpoint mismatch. [S10]

**Result:** a definite model/carrier linkage `VIOLATION`, not evidence of a physical CPU or latency failure.

Changing only a tension alias instead would be a different fault: the pinned field checker would reject alias/key disagreement. That is not silently substituted for this edge-only variant. [S9]

### V3 — A necessary source is unavailable to the assessment

**Change:** retain the baseline symbolic field and edge, but withhold the verified metric source record or its source-version binding from the assessment's accepted evidence base. This is a hypothetical evidence-availability variant, not a deletion of the repository CSV.

**Manual derivation.** The visible edge and tension may still establish their internal ID equalities. That does not supply the missing premise that the metric payload and threshold classification derive from the selected raw source. In the declared positive support profile, no alternative accepted source is supplied; the source-origin conclusion loses its grounded derivation. [S1, S9, S10]

**Result:** `K_link` can remain justified, while source-level `K_origin`/`K_support` is `UNRESOLVED`. Unknown provenance is not encoded as a zero metric, a missing physical relation, or a false physical statement.

**Checker limit:** the generic output checkers do not load the raw metric CSV and may see no new output-contract violation. This is precisely why output-shape/link acceptance is not used here as complete provenance evidence.

**Separate structural omission:** if `mL` itself is removed from the field while `tL` still references it, this is not mere source unavailability. The field checker has a concrete dangling-link rejection, and a nonempty edge lookup cannot resolve the destination either. Entirely absent/empty lookup data must remain a coverage failure, not an automatic successful assessment. [S9, S10]

A later, independently bound copy of the same source could restore the missing premise. Its equivalence would have to be verified; a different metric is not an alternative proof of the original latency claim.

### V4 — A complete, correctly bound replacement target

**Change:** replace the selected latency relation role with the already existing CPU relation `(eC,tC,g,mC)`. Use its own metric row, ID bindings, tension summaries and edge record. Preserve the unchanged complete background field and record the protected target replacement in `J`.

**Manual derivation.** CPU has absolute delta `0.020 >= 0.01` and below `0.05`; its relative delta is also between the warning and critical thresholds. It is eligible at warning severity. The gate is critical, so `tC` and `eC` are critical. The complete CPU tuple satisfies the same `K_link` rule with the new arguments. Its source locator is data row 1, not latency row 0. [S4, S7, S8]

**Result:** the replacement relation is conditionally source-justifiable, but it is **not** identical to the old latency relation. The generic inference rule may be reused; the old target-specific proof leaves must be replaced by CPU-specific leaves.

**Important scope correction:** both relations already exist in the pinned example. This variant changes the assessed target, not the whole original field, and does not create a new CPU relationship. If one simply duplicated `eC` in a serialized full edge list, the duplicate-ID check would reject; no such file edit is part of this variant.

The exact latency claim is not refuted or rewritten. Its historical derivation remains about latency. The CPU claim receives a separate assessment. This is evidence-applicability rebinding, not automatic correction and not permission to replace a protected monitoring requirement.

### 6.1. Outcome table

| Variant | Joint relational result | Source/proof result | Executed test? |
|---|---|---|---|
| V0: baseline | Link equalities hold in the specified construction. | Conditional derivation from the pinned example sources. | No. |
| V1: enumeration permutation | Same semantic tuple; raw ordering may be noncanonical. | No automatic new byte/signature identity. | No. |
| V2: destination-only substitution | Definite endpoint/tension mismatch. | Old support cannot prove the changed binding. | No. |
| V3: unavailable metric source | Internal link may remain intact. | Source-level applicability unresolved without an accepted alternative. | No. |
| V4: complete CPU target replacement | Valid replacement tuple, different protected subject. | New bound premises justify a new target; historical proof is retained. | No. |

## 7. M2 — Conditional completions and mutual constraints in this case

Let `x` be the edge's destination role and `y` the tension's metric role. In the selected two-metric slice, the basic internal compatibility condition contains:

$$
x,y\in\{mL,mC\},\qquad x=y.
$$

For valid internal completions:

$$
\mathcal F_{x\mid y}(mL)=\{mL\},\quad
\mathcal F_{x\mid y}(mC)=\{mC\},
$$

and symmetrically:

$$
\mathcal F_{y\mid x}(mL)=\{mL\},\quad
\mathcal F_{y\mid x}(mC)=\{mC\}.
$$

This is mutual constraint on compatible values, not a causal action of an edge on an Atom. With the protected identity `tL` and its pinned evidence fixed, `y=mL`; the proposed `x=mC` in V2 has no completion **satisfying this requirement**.

The violated candidate itself still exists as a structurally representable record assignment. It is not removed from the candidate space by first imposing `x=y`. Thus the mismatch yields a violation witness rather than an empty-domain PASS.

V4 changes the whole selected target and its subject-bound evidence. It does not repair V2 by relaxing `x=y` or silently rewriting `tL` into `tC`.

The pairwise value domains alone are both `{mL,mC}`. The joint condition has only the diagonal pairs. This is a concrete instance of the loss identified in M1's T1, now attached to an existing source-level equality. It does not establish a new general physical form of “intertwining.”

## 8. M3 — Grounded support and proof transport

### 8.1. Exact claims

Keep the following separate:

- `c_link(L)`: the selected latency edge and tension have the required internal correspondence.
- `c_origin(L)`: the selected latency records are the source-derived construction for the pinned inputs and programs.
- `c_observed(L)`: those concrete artifacts were actually produced and verified in a specified execution.
- `c_authorized(L)`: a protected operation is authorized by the existing PULSEmech authority.

This work gives manual derivations for the first two under explicit assumptions. It does not establish the last two. No rule in this case derives observation or authority from source-reading alone. [S1]

### 8.2. Joint support, not mere references

For the source-derived claim, a simplified positive rule is:

$$
\{s_g,s_L,s_{\kappa},s_{\rm producer},s_{\rm identity},s_{\rm match}\}
\Longrightarrow c_{\rm origin}(L).
$$

The premises stand for accepted, exactly bound statements: the gate row, latency row, full context inputs, program semantics, identity resolution, and the constructor-to-record correspondence. Each is needed together for this rule. A producer's self-reported success token is not a substitute for any premise.

For `c_link(L)`, the record/type resolution and all joint equalities form a distinct, narrower derivation. An output checker can support that narrower result without independently supporting the raw-source claim.

An alternative accepted source retrieval may yield the same premise `s_L`; it does not change the statement to CPU. Conjunctive premises and alternative ways of establishing a premise remain distinct.

### 8.3. Withdrawal and replacement

In V3, remove `s_L` from the accepted base without adding an alternative. The source-origin derivation is no longer grounded in the selected rule set. It is incorrect to retain it solely because `eL` references `tL` and `tL` references `mL`: those record references cannot create a missing source-validation premise. M3's least grounded closure, rather than mere mutual reference, governs this assessment. [S1]

In V4, use `s_C` and the CPU-specific identity/correspondence premises to derive `c_origin(C)`. The rule template is reusable; the claim and its leaves are different. One cannot infer `c_origin(C)` merely from `c_origin(L)`. The change is recorded as a new applicability assessment, not a rewrite of the historical proof.

### 8.4. Proposed research record

A future record for this mapping must bind the claim, source snapshot, profile, selected subject, global correspondence, premises, derivation, checker scope and unresolved obligations. Its status fields must separate manual derivation, software execution, observed evidence and authority. This paragraph is a data-contract proposal, not an implemented schema or a change to the Transition Meter's canonical statuses.

## 9. Checker coverage and source discrepancies

| Surface | What source inspection supports | What must not be inferred |
|---|---|---|
| Field adapter | Deterministic construction rules, bounded selection, source pointers and aliases. | Authenticity of example runs; independent validation of raw observations. |
| Field checker | Field shape/order, ID uniqueness, link/type resolution, required tension aliases. | Recalculation of all raw-source digests, summaries or metric selection. |
| Edge exporter | Edge construction from tension records; endpoint existence/types; IDs and sorting. | Complete validation of every field-contract rule. |
| Edge checker with a complete nonempty Atom map | Endpoint/tension/alias agreement, severity/rule agreement, context consistency and edge serialization checks. | Source authenticity, complete raw-input reconstruction, causal meaning, or unconditional coverage with empty lookup data. |
| Example acceptance implementation | Nonempty edge set, context correlation, both expected metric names and expected allowlisted overlay tensions. | Full endpoint validation, complete proof of all possible paths, or running the producer pipeline itself. |

Older case-study prose says the standard aliases are optional; the pinned field checker now requires them. The exporter and edge checker retain their own compatibility behavior. This document reports each layer rather than choosing a convenient blanket interpretation. [S8–S10, S13]

The canonical acceptance file delegates via `runpy` to `scripts/scripts/check_paradox_examples_transitions_case_study_v0_acceptance.py`. The delegated code reads field/edge outputs; it does not invoke the field adapter or exporter. Consequently this work does not repeat the older prose claim that this wrapper alone reproduces the complete pipeline. [S11–S14]

These are source-bound scope observations, not a newly executed vulnerability or regression report. The inspected files are unchanged. Any later correction or hardening requires its own bounded authorization and tests.

## 10. Relevance, completeness and isolation limits

The mapping covers the named relation tuple, its source records, the five variants and the stated proof-support rules. It does not cover arbitrary additional Atom types, all context keys, all possible CSV formats, every duplicate/normalization case, hash-collision resistance, system-wide impact closure, runtime monitoring or physical execution.

The background overlay inputs contribute to context. Their values cannot be removed while claiming the exact same byte-bound context. Similarly, arbitrary changes to another source may alter file fingerprints or selection behavior. This document makes no whole-field isolation claim from the fact that one local tuple was examined.

Source-binding completeness is stronger than field/edge agreement. Producer correctness, output-checker acceptance and an independently bound source reconstruction are not interchangeable. No new generated output is available here on which to assert their conjunction empirically.

The reference is a separately written table of source records and equalities, not “whatever the producer emits.” It is still authored within this same research effort; organizationally independent validation remains absent.

## 11. Architecture and authority boundary

The Paradoxon role is a typed relational analysis of declared alternatives. The Transition Meter may later carry bound assessment evidence under its existing semantics, but this case does not add statuses or treat an alternative as an observed transition.

The PULSEmech release-authority path remains unchanged. `K_case` and the manual outcomes do not become gates. No new policy requirement, `status.json` field, materialized required set or checker bypass is introduced.

PULSEbox remains outside this artifact-level proof: there is no evidence here of execution-right possession, physical enforcement, route closure or a target-side protected operation. A detected carrier mismatch is not itself proof that a protected real operation was blocked. [S1]

The `gate_latency_budget` name is the example's recorded subject; this document does not establish that it is an active required release gate under any current policy.

## 12. Open obligations and completion assessment

| Obligation | Present result | Still needed |
|---|---|---|
| OM1: source selection | Exact snapshot, paths, row selectors and constructor functions identified. | No additional inventory sweep required for this slice. |
| OM2: semantic mapping | Joint tuple and equalities mapped manually into M1–M3. | Independent review of this mapping. |
| OM3: identity realization | Exact constructor expressions retained; roles are protected. | Materialized IDs, uniqueness and byte bindings under an authorized run. |
| OM4: representation sufficiency | Conditional argument for the named predicates and variants. | No full Paradoxon fidelity claim; broader classes require separate proof. |
| OM5: negative outcomes | Endpoint mismatch and provenance absence distinguished manually. | Executed regressions with a reference independent of producer verdicts. |
| OM6: canonical serialization | Semantics/order distinction specified. | Actual serialization and ordering checks when execution is authorized. |
| OM7: provenance | Example data and source-derived semantics are explicit. | Observed output identity and independent reconstruction, if claimed later. |
| OM8: monitoring/delegation | Not mapped by this artifact case. | Actual protected operations, executors, monitors and complete relevant route bindings. |
| OM9: authority/enforcement | Boundary preserved. | Separate authorized integration and target-side enforcement evidence. |

**D2 progress:** a specific source-level correspondence and its counterexamples are now explicit. This document does not close D2 generally. D3's stronger common-mechanics hypothesis and D4's pilot readiness remain open. An accepted bounded case is not acceptance of the whole theory.

## 13. Bounded next step and file scope

The next authorized research review can examine this exact mapping, particularly the protected-target distinction in V4 and the difference between internal link consistency and source-origin justification in V3. No additional abstract framework is required before that review.

After acceptance, the smallest executable follow-up would materialize these five variants in an isolated setting, use explicit complete Atom/context inputs, and compare observed outcomes with the independently specified equalities. That is a later proposal, not an execution permission granted by this document. The monitoring/delegation pilot requires an additional system-level mapping before it can claim pre-execution safety.

The proposed repository change for preserving this work is one new document at `docs/PULSEMECH_PARADOX_SOURCE_MAPPING_CASE_v0.md` and one accurately classified link under `Paradox field and edges` in `docs/INDEX.md`. The M1–M3 contract, existing case-study sources, code, checkers, policies, workflows, README, DOI and Software Heritage surfaces are not modified by this delivery.

## Source register

All links below are pinned to `cbeab94d8532482d34ab857bf38e9e56ae265f84`. A Git blob identifier is an identity supplied by the repository read, not a newly calculated evidence digest. The complete snapshot/path remains the source locator where no blob value is listed.

| Label | Source and relevant selector | Git blob identifier where available |
|---|---|---|
| S1 | [M1–M3 contract][S1], Sections 2–6, 9 and 13 | `ad6543d8b2db91b2f8d1fa928e6a2d914fc6ca18` |
| S2 | [Glossary][S2], field-first relational terms | Snapshot/path binding. |
| S3 | [Gate drift CSV][S3], data row 0 | `e1aabd25974f2de48f57954f1c243cb619a59776` |
| S4 | [Metric drift CSV][S4], data rows 0 and 1 | `e9e92d80240297aab1111b7360ee677ba650d032` |
| S5 | [Transitions JSON][S5], `note`, `run_a`, `run_b` | `cdeb822818b65dba3ca9993176926369aa7a42ad` |
| S6 | [Overlay JSON][S6], both named overlay records | `c61d6bee0faa9b74ca00bf564900321400b2b21a` |
| S7 | [Field adapter][S7], `_atom_id`, `_tension_atom_id`, `_metric_severity`, `_build_run_context`, construction branches | `5e7b5a8733692be4a52af893149a996717f1116e` |
| S8 | [Edge exporter][S8], `_edge_id`, `_build_run_context`, `_tension_src_dst`, `main` | `66c517931227bd0414cc4cd8b44d962503c38a3a` |
| S9 | [Field checker][S9], `_require_tension_alias_checks`, provenance checks and `main` | `b5a2f2bb66cbb2f27a2cf0dab2baa3068c667008` |
| S10 | [Edge checker][S10], Atom indexing, `if atoms_by_id` link checks, context and ordering checks | `f43f995e380e560bb0be0971615f7ddce549841f` |
| S11 | [Canonical acceptance wrapper][S11], `main` | `b1ffc61d6a1c9d714e5a6654322723e82bbc58e6` |
| S12 | [Delegated acceptance implementation][S12], `EXPECTED_METRICS`, `main` | `71a0b667c22daddbc21306f073b1ae9e94024a75` |
| S13 | [Existing edge case studies][S13], non-fixture example and alias invariants | `a806899d4dee1c553780353d0f3c3f04e11980c7` |
| S14 | [Example README][S14], inputs and reproduction description | `26859cafbc096901146bff70a7f2b40c3c8d83be` |

[S1]: https://github.com/HKati/pulse-release-gates-0.1/blob/cbeab94d8532482d34ab857bf38e9e56ae265f84/docs/PULSEMECH_PARADOX_M1_M3_DEFINITION_CONTRACT_v0_2.md
[S2]: https://github.com/HKati/pulse-release-gates-0.1/blob/cbeab94d8532482d34ab857bf38e9e56ae265f84/docs/GLOSSARY_v0.md
[S3]: https://github.com/HKati/pulse-release-gates-0.1/blob/cbeab94d8532482d34ab857bf38e9e56ae265f84/docs/examples/transitions_case_study_v0/pulse_gate_drift_v0.csv
[S4]: https://github.com/HKati/pulse-release-gates-0.1/blob/cbeab94d8532482d34ab857bf38e9e56ae265f84/docs/examples/transitions_case_study_v0/pulse_metric_drift_v0.csv
[S5]: https://github.com/HKati/pulse-release-gates-0.1/blob/cbeab94d8532482d34ab857bf38e9e56ae265f84/docs/examples/transitions_case_study_v0/pulse_transitions_v0.json
[S6]: https://github.com/HKati/pulse-release-gates-0.1/blob/cbeab94d8532482d34ab857bf38e9e56ae265f84/docs/examples/transitions_case_study_v0/pulse_overlay_drift_v0.json
[S7]: https://github.com/HKati/pulse-release-gates-0.1/blob/cbeab94d8532482d34ab857bf38e9e56ae265f84/scripts/paradox_field_adapter_v0.py
[S8]: https://github.com/HKati/pulse-release-gates-0.1/blob/cbeab94d8532482d34ab857bf38e9e56ae265f84/scripts/export_paradox_edges_v0.py
[S9]: https://github.com/HKati/pulse-release-gates-0.1/blob/cbeab94d8532482d34ab857bf38e9e56ae265f84/scripts/check_paradox_field_v0_contract.py
[S10]: https://github.com/HKati/pulse-release-gates-0.1/blob/cbeab94d8532482d34ab857bf38e9e56ae265f84/scripts/check_paradox_edges_v0_contract.py
[S11]: https://github.com/HKati/pulse-release-gates-0.1/blob/cbeab94d8532482d34ab857bf38e9e56ae265f84/scripts/check_paradox_examples_transitions_case_study_v0_acceptance.py
[S12]: https://github.com/HKati/pulse-release-gates-0.1/blob/cbeab94d8532482d34ab857bf38e9e56ae265f84/scripts/scripts/check_paradox_examples_transitions_case_study_v0_acceptance.py
[S13]: https://github.com/HKati/pulse-release-gates-0.1/blob/cbeab94d8532482d34ab857bf38e9e56ae265f84/docs/paradox_edges_case_studies.md
[S14]: https://github.com/HKati/pulse-release-gates-0.1/blob/cbeab94d8532482d34ab857bf38e9e56ae265f84/docs/examples/transitions_case_study_v0/README.md
