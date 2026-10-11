"""Bounded, exact, non-authoritative comparison-binding synthetic probe."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from pathlib import Path
import hashlib
import json
import re

from schema_subset import SchemaError, validate


ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT.parents[1] / "schemas" / "pulsemech_comparison_binding_v0.schema.json"
FULL = frozenset(f"cell:{i:03d}" for i in range(64))
SMALL = frozenset({"cell:000"})
MODEL = tuple(product((Fraction(1, 2), Fraction(2)), (FULL, SMALL)))
FIXTURE_NAMES = (
    "01_expansion_fixed_support.json",
    "02_contraction_fixed_support.json",
    "03_reduced_support_with_flattening.json",
)
OPERATOR = "synthetic_curvature_and_scalar_samples_v0"
UNITS = {"curvature": "reference_length^-2", "volume": "reference_length^3",
         "field": "dimensionless", "scale_factor": "dimensionless"}


class ContractError(ValueError):
    pass


def canonical_bytes(value):
    # A declared local encoding, not an RFC 8785/JCS conformance claim.
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def exact(value):
    if type(value) is not str or re.fullmatch(r"-?(0|[1-9][0-9]*)(/[1-9][0-9]*)?", value) is None:
        raise ContractError("noncanonical rational value")
    answer = Fraction(value)
    if str(answer) != value:
        raise ContractError("rational value is not reduced")
    return answer


def resolve(fixture, ref):
    if type(ref) is not dict or set(ref) != {"artifact_id", "sha256"}:
        raise ContractError("malformed artifact reference")
    item = fixture["artifacts"].get(ref["artifact_id"])
    if type(item) is not dict or set(item) != {"payload", "sha256"}:
        raise ContractError("referenced artifact missing")
    actual = digest(item["payload"])
    if actual != item["sha256"] or actual != ref["sha256"]:
        raise ContractError("artifact digest mismatch")
    return item["payload"]


def known_cells(fixture, binding):
    if binding["status"] == "unknown":
        return None
    payload = resolve(fixture, binding["ref"])
    cells = payload.get("cells")
    if type(cells) is not list or not all(type(c) is str and c in FULL for c in cells):
        raise ContractError("cell outside the reference universe")
    if len(cells) != len(set(cells)):
        raise ContractError("duplicate cell membership")
    return frozenset(cells)


def validate_fixture(fixture):
    schema = json.loads(SCHEMA_PATH.read_text("utf-8"))
    try:
        validate(fixture["comparison_binding"], schema)
    except (SchemaError, KeyError) as exc:
        raise ContractError(str(exc)) from exc
    if fixture.get("record_status") != "synthetic_review_fixture":
        raise ContractError("unexpected fixture record status")
    artifacts = fixture.get("artifacts")
    if type(artifacts) is not dict:
        raise ContractError("artifact table missing")
    for artifact_id, item in artifacts.items():
        if set(item) != {"payload", "sha256"} or digest(item["payload"]) != item["sha256"]:
            raise ContractError(f"invalid stored artifact: {artifact_id}")
    binding = fixture["comparison_binding"]
    reference = resolve(fixture, binding["reference_domain_ref"])
    if (reference.get("kind") != "finite_reference_partition_v0" or
            reference.get("dimension") != 3 or
            reference.get("cell_reference_volume") != "1/64" or
            reference.get("sectional_curvature") != "1" or
            reference.get("cells") != sorted(FULL)):
        raise ContractError("reference domain outside the bounded profile")
    field_type = resolve(fixture, binding["field_type_ref"])
    if field_type != {"kind": "rational_scalar_field_v0", "fiber_map": "identity_v0",
                      "unit": "dimensionless"}:
        raise ContractError("field type outside the bounded profile")
    transport = resolve(fixture, binding["transport_ref"])
    if transport != {"kind": "identity_on_reference_labels_v0", "fiber_map": "identity_v0",
                     "reference_domain_ref": binding["reference_domain_ref"]}:
        raise ContractError("transport is not verified by this bounded adapter")
    normalization = resolve(fixture, binding["observation_normalization_ref"])
    if normalization != {"kind": "identity_v0", "accepted_operator": OPERATOR,
                         "accepted_units": UNITS,
                         "common_codomain": "bound_curvature_and_scalar_samples_v0"}:
        raise ContractError("normalization outside the bounded profile")
    rule = resolve(fixture, binding["comparison_rule_ref"])
    if rule != comparison_rule():
        raise ContractError("comparison rule outside the bounded profile")
    for label in ("source", "target"):
        endpoint = binding[label]
        state = resolve(fixture, endpoint["state_ref"])
        metric = resolve(fixture, endpoint["metric_ref"])
        frame = resolve(fixture, endpoint["observation_frame_ref"])
        support = known_cells(fixture, endpoint["system_support"])
        coverage = known_cells(fixture, endpoint["observation_coverage"])
        for key, kind in (("system_support", "system_support_v0"),
                          ("observation_coverage", "successful_observation_coverage_v0")):
            if endpoint[key]["status"] == "known" and resolve(fixture, endpoint[key]["ref"]).get("kind") != kind:
                raise ContractError("support/coverage reference has the wrong semantic type")
        if metric.get("kind") != "uniform_scale_spatial_metric_v0":
            raise ContractError("unsupported spatial metric")
        scale = exact(metric["scale_factor"])
        if scale <= 0 or exact(state["curvature_observation"]) != 1 / scale**2:
            raise ContractError("metric and curvature observation disagree")
        if type(state.get("step_index")) is not int or state["step_index"] != (0 if label == "source" else 1):
            raise ContractError("source/target order mismatch")
        values = state.get("field_observations")
        if type(values) is not dict or not set(values).issubset(FULL):
            raise ContractError("invalid field observations")
        for value in values.values():
            exact(value)
        if coverage is not None and set(values) != set(coverage):
            raise ContractError("successful coverage and supplied samples disagree")
        if coverage is not None and support is not None and not coverage.issubset(support):
            raise ContractError("observation coverage exceeds system support")
        if type(frame) is not dict:
            raise ContractError("observation frame missing")
    return fixture


def comparison_rule():
    return {
        "target": "sign_of_physical_volume_change_of_declared_domain_v0",
        "geometric_model": "four_uniform_scale_support_candidates_v0",
        "field_comparator": "difference_on_common_observed_support_v0",
        "missing_sample": "unobserved_no_numeric_imputation",
        "outside_support": "outside_support_no_zero_extension",
        "nonempty_consistency_required": True,
        "uncertainty_model": "exact_synthetic_v0",
        "authority_effect": "none",
    }


def load_fixture(name):
    return validate_fixture(json.loads((ROOT / "fixtures" / name).read_text("utf-8")))


def candidate_curvature(candidate):
    scale, _ = candidate
    return 1 / scale**2


def candidate_volume(candidate):
    scale, support = candidate
    return scale**3 * Fraction(len(support), 64)


def candidate_target(candidate):
    difference = candidate_volume(candidate) - 1
    return (difference > 0) - (difference < 0)


@dataclass(frozen=True, kw_only=True)
class GeometryEvidence:
    source_curvature: Fraction
    target_curvature: Fraction
    primary_support: frozenset | None = None
    backup_support: frozenset | None = None
    reference_binding_valid: bool
    observation_binding_valid: bool


def validate_geometry_evidence(evidence):
    """Check the internal packet shape; this is not receipt authentication."""
    if type(evidence) is not GeometryEvidence:
        raise ContractError("expected a constructed GeometryEvidence packet")
    for flag in (evidence.reference_binding_valid, evidence.observation_binding_valid):
        if type(flag) is not bool:
            raise ContractError("binding validity must be an explicit boolean")
    for curvature in (evidence.source_curvature, evidence.target_curvature):
        if type(curvature) is not Fraction:
            raise ContractError("geometry evidence requires exact rational curvature")
    for support in (evidence.primary_support, evidence.backup_support):
        if support is not None and (type(support) is not frozenset or
                any(type(cell) is not str or cell not in FULL for cell in support)):
            raise ContractError("geometry evidence has invalid support membership")


def geometry_evidence(fixture, enabled_bindings=()):
    # Validation is a separate precondition. The evaluator never receives the
    # fixture, labels, unused artifacts, expected answers or hidden field values.
    validate_fixture(fixture)
    binding = fixture["comparison_binding"]
    source = binding["source"]
    target = binding["target"]
    source_state = resolve(fixture, source["state_ref"])
    target_state = resolve(fixture, target["state_ref"])
    if known_cells(fixture, source["system_support"]) != FULL:
        raise ContractError("the geometric witness requires the fixed source support")
    if exact(resolve(fixture, source["metric_ref"])["scale_factor"]) != 1:
        raise ContractError("the geometric witness requires source scale 1")
    frames = [resolve(fixture, ep["observation_frame_ref"]) for ep in (source, target)]
    observation_valid = all(frame == observation_frame() for frame in frames)
    enabled = frozenset(enabled_bindings)
    if not enabled.issubset({"primary_support", "backup_support"}):
        raise ContractError("undeclared geometry evidence path")
    members = known_cells(fixture, target["system_support"]) if enabled else None
    return GeometryEvidence(
        source_curvature=exact(source_state["curvature_observation"]),
        target_curvature=exact(target_state["curvature_observation"]),
        primary_support=members if "primary_support" in enabled else None,
        backup_support=members if "backup_support" in enabled else None,
        reference_binding_valid=True, observation_binding_valid=observation_valid,
    )


def observation_frame():
    return {"operator_id": OPERATOR, "units": UNITS,
            "resolution": "exact_reference_cell_samples_v0",
            "boundary_condition": "declared_support_no_extension_v0",
            "uncertainty": {"kind": "exact_synthetic_v0", "epsilon": "0"},
            "clock": "synthetic_step_index_v0"}


def evaluate_geometry(evidence):
    validate_geometry_evidence(evidence)
    if not evidence.reference_binding_valid or not evidence.observation_binding_valid:
        return ("defined", "UNBOUND", None, None, "diagnostic_only")
    if evidence.source_curvature != 1:
        return ("defined", "INCOMPATIBLE", 0, (), "diagnostic_only")
    compatible = tuple(candidate for candidate in MODEL
        if candidate_curvature(candidate) == evidence.target_curvature
        and all(candidate[1] == support for support in
                (evidence.primary_support, evidence.backup_support) if support is not None))
    targets = tuple(sorted({candidate_target(candidate) for candidate in compatible}))
    status = "INCOMPATIBLE" if not compatible else "IDENTIFIED" if len(targets) == 1 else "UNRESOLVED"
    return ("defined", status, len(compatible), targets, "diagnostic_only")


def replay(fixture, enabled_bindings=()):
    return evaluate_geometry(geometry_evidence(fixture, enabled_bindings))


def compare_field(fixture):
    validate_fixture(fixture)
    binding = fixture["comparison_binding"]
    endpoints = [binding[label] for label in ("source", "target")]
    supports = [known_cells(fixture, ep["system_support"]) for ep in endpoints]
    coverages = [known_cells(fixture, ep["observation_coverage"]) for ep in endpoints]
    frames_valid = all(resolve(fixture, ep["observation_frame_ref"]) == observation_frame()
                       for ep in endpoints)
    if not frames_valid or any(x is None for x in supports + coverages):
        return {"status": "UNBOUND", "global_scalar_field_identity": "UNRESOLVED",
                "reason": "frame_support_or_coverage_binding_unknown",
                "deltas": {cell: {"status": "unbound", "value": None} for cell in sorted(FULL)},
                "authority_effect": "none"}
    source_support, target_support = supports
    source_coverage, target_coverage = coverages
    states = [resolve(fixture, ep["state_ref"]) for ep in endpoints]
    samples = [state["field_observations"] for state in states]
    deltas = {}
    for cell in sorted(FULL):
        if cell not in source_support and cell not in target_support:
            item = {"status": "outside_both_supports", "value": None}
        elif cell not in source_support:
            item = {"status": "outside_source_support", "value": None}
        elif cell not in target_support:
            item = {"status": "outside_target_support", "value": None}
        elif cell not in source_coverage or cell not in target_coverage:
            missing = [label for label, coverage in zip(("source", "target"), coverages)
                       if cell not in coverage]
            item = {"status": "unobserved", "value": None, "missing_endpoints": missing}
        else:
            item = {"status": "observed", "value": str(exact(samples[1][cell]) - exact(samples[0][cell]))}
        deltas[cell] = item
    observed = [item for item in deltas.values() if item["status"] == "observed"]
    unobserved = [item for item in deltas.values() if item["status"] == "unobserved"]
    if source_support != target_support:
        identity = "NOT_EQUAL_SUPPORT"
    elif any(exact(item["value"]) != 0 for item in observed):
        identity = "IDENTIFIED_DIFFERENT"
    elif unobserved:
        identity = "UNRESOLVED"
    else:
        identity = "IDENTIFIED_EQUAL"
    return {"status": "PARTIALLY_OBSERVED" if unobserved else "OBSERVED_ON_COMMON_SUPPORT",
            "global_scalar_field_identity": identity, "deltas": deltas, "authority_effect": "none"}


def _status_axes(observation, binding, consistency):
    # These views perform only deterministic, same-model local replay.
    # Neither target identification nor replay evaluates a physical cause.
    return {"observation_status": observation, "binding_status": binding,
            "consistency_status": consistency, "reproduction_status": "bounded_replay_only",
            "causal_status": "not_evaluated", "authority_status": "diagnostic"}


def geometry_status_view(evidence):
    """Target-scoped diagnostic view using the six canonical status groups."""
    response = evaluate_geometry(evidence)
    if evaluate_geometry(evidence) != response:
        raise ContractError("geometric bounded replay changed the response")
    status = response[1]
    supplied = [s for s in (evidence.primary_support, evidence.backup_support) if s is not None]
    if status == "UNBOUND":
        observation, binding, consistency = "not_observed", "unbound", "internally_incomplete"
    else:
        observation = "reconstructed" if supplied else "partially_observed"
        binding = ("identity_conflict" if len(supplied) == 2 and supplied[0] != supplied[1]
                   else "bound" if supplied else "partially_bound")
        consistency = {"IDENTIFIED": "consistent", "UNRESOLVED": "ambiguous",
                       "INCOMPATIBLE": "conflicting"}[status]
    return {"record_status": "synthetic_diagnostic",
            "claim_id": comparison_rule()["target"],
            "claim_scope": "declared_four_candidate_geometric_model_v0",
            "target_assessment": {"definedness": response[0], "identification_status": status,
                "compatible_candidate_count": response[2], "possible_target_values": response[3]},
            "status_axes": _status_axes(observation, binding, consistency),
            "physical_transition_path_evaluated": False, "authority_effect": "none"}


def field_status_view(fixture):
    """Keep scalar-identity sufficiency separate from sample completeness."""
    result = compare_field(fixture)
    if compare_field(fixture) != result:
        raise ContractError("scalar bounded replay changed the response")
    if result["status"] == "UNBOUND":
        observation, binding, consistency = "not_observed", "unbound", "internally_incomplete"
    else:
        observation = "partially_observed" if result["status"] == "PARTIALLY_OBSERVED" else "reconstructed"
        binding = "bound"
        consistency = "ambiguous" if result["global_scalar_field_identity"] == "UNRESOLVED" else "consistent"
    return {"record_status": "synthetic_diagnostic",
            "claim_id": "scalar_field_identity_on_declared_support_v0",
            "claim_scope": "finite_rational_scalar_field_under_identity_transport_v0",
            "target_assessment": {"comparison_status": result["status"],
                "global_scalar_field_identity": result["global_scalar_field_identity"]},
            "status_axes": _status_axes(observation, binding, consistency),
            "physical_transition_path_evaluated": False, "authority_effect": "none"}
