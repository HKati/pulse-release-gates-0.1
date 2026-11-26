# Anchor Integrity v0.1 — WP2D typed dependency-cycle observation

**Status:** offline diagnostic candidate. **Authority effect:** `none`.
**Preparation base:** `31def7a7258fc57b9b73cdad7cddb2a559de77e1`.
**Profile:** `typed-dependencies-v1` (explicit opt-in).

## 1. Purpose and exact result boundary

WP2D implements a structural cycle observation over a digest-bound, explicitly
typed dependency projection. It does not treat every Paradoxon Diagram edge
or cycle as an error. It also does not infer that any caller-declared anchor
is independent, authentic or sufficient.

The existing [WP1 contract](ANCHOR_INTEGRITY_v0_1_CONTRACT.md) reserves an
anchor-aware cycle classification. That classification needs more than a
cycle detector. WP2D therefore reports actual structural observations in a
separate report, without rewriting the original output contract or returning
its `anchored_cycle_observed` / `unanchored_cycle_detected` values prematurely.

A detected dependency cycle is not proof of semantic support, falsity,
unanchored reasoning or release unsafety. Absence of a detected cycle means
only that no directed cycle exists in this particular declared projection.
A missing dependency declaration can conceal a real dependency. Authentication
of graph completeness is outside this package.

## 2. Files and compatibility

- [Checker](../tools/check_anchor_integrity_dependency_cycles_v0_1.py).
- [Graph schema](../schemas/anchor_integrity_dependency_graph_v0_1.schema.json).
- [Report schema](../schemas/anchor_integrity_dependency_cycle_report_v0_1.schema.json).
- [Synthetic example](../examples/anchor_integrity_v0_1/wp2d_dependency_cycles/input.json).
- Regressions extend the existing
  [Anchor test module](../tests/test_anchor_integrity_v0_1_contract.py).

The WP2A/WP2B binding checker, JSON Pointer projector and WP2C record checker
remain byte-identical. Their default behavior and previous reports are not
changed. No previous schema, example, workflow or CI-manifest is modified.

WP2D uses the input contract's existing optional `paradox_graph_binding` slot
but accepts only the new explicit graph schema/profile. It is not a generic
adapter for other existing Paradoxon graph formats. A graph with a different
schema is rejected rather than implicitly converted.

## 3. Fresh input and record binding

The invocation requires three independent caller-retained hash expectations:
input, carriers and verifier-record set, plus the existing base binding
profile and the explicit cycle profile. Caller-supplied expectations are not
signatures or proof of caller identity.

The fixed installed WP2C implementation and its WP2A/WP2B checker run afresh
on one bounded `BundleReader`. No saved successful report is accepted as a
substitute. WP2D starts graph interpretation only after that fresh record
binding result is `LOCAL_RECORD_BINDINGS_CONSISTENT`.

The graph is read through the base check's existing input-graph binding and
retained byte cache. WP2D rechecks its digest and validates its schema, subject,
claim-set ID and all three packet hashes against the same retained packets.
The graph binds packet hashes, not the enclosing input's hash: the input
already binds the graph, so this avoids a circular content-hash definition.

Retained bytes are not an atomic filesystem snapshot and make no claim about
the later state of paths. They ensure the stages analyze the same bytes already
read, within the existing trusted-host/installation/root boundary.

## 4. Projection semantics

The graph declares `coverage = declared_edges_only`. Nodes are all claim and
evidence IDs from the checked packets, including isolated nodes. Node identity
is type-qualified (`claim:<claim_id>` or `evidence:<evidence_id>`), so identical
raw IDs in different namespaces do not collapse into one node.

Edges point from the dependent object to its declared prerequisite:

| Explicit graph edge | From | To |
|---|---|---|
| `supported_by_claim` | claim | claim |
| `derived_from_claim` | claim | claim |
| `claim_depends_on_claim` | claim | claim |
| `evidence_depends_on_claim` | evidence | claim |

Unknown edge types, unknown endpoints, invalid endpoint kinds, duplicate edge
IDs and duplicate typed endpoint triples are invalid. Different declared types
on the same endpoint pair are retained as distinct edge records.

A fifth *generated* edge kind, `claim_to_evidence_relation`, is not accepted as
an explicit graph edge. It is deterministically generated from **every**
relation-packet entry whose `relation_type` is `supports` or `derived_from`:

```text
claim:<claim_id> -> evidence:<evidence_id>
```

This projection uses the declared relation type regardless of its recorded
verification state/result. A `not_run`, `unresolved` or `contradicted` verifier
label cannot erase a declared dependency from this structural observation.
It does not promote any such declaration to verified support. Completed
relations still require matching materialized records through WP2C.

`references`, `contextualizes` and `contradicts` relations are listed as ignored
non-dependency relations under this profile. A reference alone is not a claim
of supporting dependence. An explicit `evidence_depends_on_claim` can still
record an evidence dependency where appropriate; it is never inferred from
natural-language content.

The existing base checker treats partial/invalid claim-set materialization as
incomplete. WP2D preserves that admission stop and does not run the structural
analysis on such a bundle. It does not reclassify partial input as an empty or
complete graph.

No arbitrary decorative, temporal, causal or other Paradoxon edges are read or
classified. No external-anchor field is accepted. A packet's complete claim
materialization declaration is recorded but not independently authenticated.

## 5. Cycle analysis and witnesses

The implementation uses iterative forward/reverse graph traversal to compute
strongly connected components (SCCs), then an iterative directed search to
produce one concrete witness per cyclic component. It does not enumerate all
simple cycles or recurse once per graph node.

A component is cyclic if it has more than one node or contains a self-loop.
Each cyclic component contains its sorted members, all internal edge keys and
one closed directed witness with matching edge keys. The witness starts and
ends at the same node. It is an example cycle, not a shortest-cycle claim.

Explicit edge keys use the `graph:` namespace; generated relation edges use
`relation:`. Reports sort nodes, edges, components and issue records, making
the projection and witness selection deterministic for the same semantic
input graph. Exact root/report fingerprints still change when input bytes,
including JSON ordering, change.

Report observations:

```text
cycle_detection.status = completed
cycle_detection.result = cycle_detected
                      or no_cycle_detected_in_declared_graph
```

Missing/invalid prerequisites never yield either measured result:

```text
cycle_detection.status = not_run
cycle_detection.result = null
cycle_detection.algorithm = null
```

The separate `cycle_anchor_classification` is always `not_run` / `null`.
The original WP1 anchor-aware cycle result is **not** emitted by this tool.
`low`, `medium` and `high` are not measured cycle results.

## 6. Exit status is not an allow/block decision

- **Exit 0:** `LOCAL_DEPENDENCY_GRAPH_ANALYZED`. Analysis completed, including
  when a cycle was found. This is not a safety PASS or a supported-claim verdict.
- **Exit 1:** `LOCAL_DEPENDENCY_GRAPH_INVALID`.
- **Exit 2:** `LOCAL_DEPENDENCY_GRAPH_INCOMPLETE`, or a CLI/installation failure.
  Installation failures do not emit a success-shaped JSON report.

Missing required graph/record/source bytes are incomplete. Malformed input,
stale or mismatched hashes, wrong identities and resource-limit violations
are invalid. Among observed issues, invalid has precedence over incomplete.
A failed upstream stage prevents graph analysis rather than substituting an
empty graph. An actually supplied empty projection can have zero components;
that is still not proof of global completeness or support.

## 7. Bounds and trust assumptions

The existing POSIX reader checks safe relative paths, symlinks, hard links,
non-regular files, case collisions, role aliases and changes during reads.
Its per-file, aggregate-byte, JSON depth and item limits are reused. The new
graph accepts at most 4,096 explicit edges; the combined projection is bounded
at 8,192 nodes and 8,192 edges. Generated edges are also counted toward the
combined limit. Installation schemas are fixed, self-contained and trusted.

No network access, Git invocation, model call, artifact code, dynamic verifier
selection or bundle-selected plugin is introduced. Reports go only to stdout;
there is no output-file overwrite option. Fixed module loading disables
bytecode writes while loading and restores the previous interpreter setting.
A hostile host or substituted trusted installation is outside the claim.

## 8. Non-promotion

All results fix:

```text
candidate_status = diagnostic_only
authority_effect = none
release_authority_activation = false
requested_checks_complete = false
accepted_as_semantic_support = false
whole_response_cycle_freedom_established = false
```

Source/acquisition/subject/verifier authentication, verifier execution
attestation, semantic support, dependency-inventory authentication,
claim-set completeness, verified binding/support coverage and response
recommendations remain `not_run` with null results.

Independent-anchor admission, the original anchor-aware cycle classification,
the full adapter, and response enforcement remain separate work. No gate,
normative status or release-authority path consumes this diagnostic report.
No hallucination-reduction percentage or production accuracy is measured.

## 9. Reproduce the synthetic cycle

From the repository root (POSIX, with the existing Python dependencies):

```sh
python tools/check_anchor_integrity_dependency_cycles_v0_1.py \
  --bundle-root examples/anchor_integrity_v0_1/wp2d_dependency_cycles \
  --input input.json \
  --expected-input-sha256 1e3a63612f274b9c3e3f518f0e9528386806403783d10fbd395b3348d8dc2574 \
  --carriers carriers.json \
  --expected-carriers-sha256 ce21a2e7fbdd7f1dfbb3cfdcadd286329684be0bc2ff0a97f9d9953cc4474935 \
  --record-set record-set.json \
  --expected-record-set-sha256 6719379a23cde24a122f8f82c81bb2245ac93a7e49de873295a18fa8532bbfa9 \
  --binding-profile wp2b-json-pointer-v1 \
  --cycle-profile typed-dependencies-v1
```

Expected: exit 0, `LOCAL_DEPENDENCY_GRAPH_ANALYZED`, `cycle_detected`, one cyclic
component with `claim:claim-1 -> evidence:evidence-1 -> claim:claim-1`.
The second claim is isolated. Its presence does not create a cycle.

The example deliberately retains the prior synthetic response/source content
and its IDs. Its declared relation is changed from a reference to `supports`,
with an `unresolved` synthetic verifier declaration and consistently rebound
hashes. No real verifier has executed. This is a dependency-structure fixture,
not an independently authenticated evidence source.

## 10. Regression and integration boundary

The existing Anchor test module is already listed once in both CI manifests;
no manifest or count-consumer changes are needed. At the preparation base the
manifest counts remain 175 tools entries and 31 targeted-pytest entries.

New tests cover self-loops, disconnected cycles, mixed claim/evidence cycles,
acyclic graphs, explicit edge domains, ignored non-dependency relations,
non-completed declarations, stale and rehashed mismatched inputs, missing
prerequisites, reader boundaries, limits, schema non-promotion and CLI exits.
An independent transitive-closure oracle checks every directed graph on three
nodes (512 graphs), plus 64 seeded eight-node graphs. Long chain/ring cases
exercise 5,000 nodes without depending on Python recursion depth. This is a
bounded synthetic corpus, not an exhaustive proof for every allowed graph.

Run the complete module with either:

```sh
python -m pytest -q tests/test_anchor_integrity_v0_1_contract.py
python tests/test_anchor_integrity_v0_1_contract.py
```

Actual preparation execution results and their environment limits are in the
separate delivery report, not asserted as hosted CI success in this document.
A new PR head requires its own CI and review. No workflow dispatch or native
experiment is authorized by this package.
