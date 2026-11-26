"""LRM-04 bounded support, condition and independently observed consequences.

The comparator remains the authority for relation states. This optional wrapper
adds orthogonal impact records, then binds the detailed impact artifact before
finalizing verification and measurement. No report hash depends on itself; no
modeled configuration is promoted to an observed event or release authority.
"""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from .comparator import (EVALUATOR_FILES as COMPARATOR_FILES, _check, _expand, _id,
                         _validate_measurement, _witness, measure_bundle)
from .impact_evidence import ImpactTrust
from .impact_logic import evaluate_condition_group
from .io import (InputError, MAX_JSON_DEPTH, ROOT, canonical_bytes, read_input, safe_read, sha256,
                 strict_json, unique_index, validate_schema)
from .logic import LogicProblem
from .support import support_transition
from .trust import SCOPES
from .verifier import PROFILE_PATH


VERSION = "0.1.0"
MAX_IMPACT_PAYLOAD_BYTES = 2 * 1024 * 1024
MAX_IMPACT_PAYLOAD_NODES = 40_000
EVALUATOR_FILES = tuple(sorted(set(COMPARATOR_FILES) | {
    "tools/language_relation_v0/impact.py",
    "tools/language_relation_v0/impact_evidence.py",
    "tools/language_relation_v0/impact_logic.py",
    "tools/language_relation_v0/support.py",
    "schemas/language_relation_impact_v0.schema.json",
    "schemas/language_relation_impact_evidence_v0.schema.json",
}))


class _PublicationBudget:
    """Bound new diagnostic contributions before producing large witness sets.

    This deliberately counts repeated detail/projection/check content more than
    once. It is an admission budget for LRM-04 additions, not a substitute for
    the final exact byte/node/depth check on each complete artifact.
    """

    def __init__(self, remaining_bytes: int = MAX_IMPACT_PAYLOAD_BYTES,
                 remaining_nodes: int = MAX_IMPACT_PAYLOAD_NODES):
        self.remaining_bytes = remaining_bytes
        self.remaining_nodes = remaining_nodes

    def fork(self) -> "_PublicationBudget":
        return _PublicationBudget(self.remaining_bytes, self.remaining_nodes)

    def footprint(self, value: dict) -> tuple[int, int] | None:
        count, pending = 0, [(value, 0)]
        while pending:
            node, depth = pending.pop()
            count += 1
            if count > self.remaining_nodes or depth > MAX_JSON_DEPTH - 8:
                return None
            if isinstance(node, dict):
                pending.extend((key, depth + 1) for key in node)
                pending.extend((child, depth + 1) for child in node.values())
            elif isinstance(node, list):
                pending.extend((child, depth + 1) for child in node)
        # Canonical set/key reordering does not change encoded byte length.
        # Iteration avoids constructing a multi-megabyte rejected JSON string.
        size = 1  # terminal LF
        encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        for chunk in encoder.iterencode(value):
            size += len(chunk.encode("utf-8"))
            if size > self.remaining_bytes:
                return None
        return size, count

    def fits(self, value: dict) -> bool:
        return self.footprint(value) is not None

    def admit(self, value: dict) -> bool:
        cost = self.footprint(value)
        if cost is None:
            return False
        self.remaining_bytes -= cost[0]
        self.remaining_nodes -= cost[1]
        return True


def _compact_evidence(refs: list[str], trust: ImpactTrust) -> list[str]:
    permitted = {identifier for row in trust.evidence_pins
                 for identifier in (row["artifact_id"], "sha256:" + row["content_sha256"])}
    if trust.config_sha256:
        permitted.add("impact-trust.sha256:" + trust.config_sha256)
    return sorted(set(refs) & permitted)


def _resource_unresolved(detail: dict, trust: ImpactTrust) -> dict:
    value = deepcopy({key: item for key, item in detail.items()
                      if key not in ("support", "condition", "observation")})
    value.update(assessment_state="UNRESOLVED", conclusion="unresolved",
                 reason="The target exceeds the LRM-04 publication resource bound; no incomplete proof or truncated result is accepted.",
                 claim_ids=[], evidence_refs=_compact_evidence(detail["evidence_refs"], trust),
                 witness_ids=[], support=None, condition=None, observation=None)
    if detail["reason"]:
        value["reason"] += " Prior diagnostic: " + detail["reason"][:250]
    return value


def evaluator_reference() -> dict:
    files = [{"path": name, "content_sha256": sha256(safe_read(ROOT, name))}
             for name in EVALUATOR_FILES]
    return {"tool_id": "language_relation_impact_v0", "version": VERSION,
            "content_sha256": sha256(canonical_bytes({"files": files}))}


@lru_cache(maxsize=1)
def _impact_validator() -> Draft202012Validator:
    schema = strict_json(safe_read(ROOT / "schemas", "language_relation_impact_v0.schema.json"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _detail(target: dict, result: dict, kind: str) -> dict:
    return {"target_id": target["target_id"], "kind": kind,
            "assessment_state": "UNRESOLVED", "representation_basis": result["representation_basis"],
            "claim_scope": result["claim_scope"], "conclusion": "unresolved", "reason": None,
            "claim_ids": [], "evidence_refs": [], "witness_ids": [],
            "support": None, "condition": None, "observation": None,
            "causal_status": "not_evaluated"}


def _base_boundary(document: dict, verification: dict, result: dict, *,
                   accepted: bool) -> tuple[str, str] | None:
    """A model/evidence gate, independent of the structural relation outcome."""
    checks = {row["check_id"]: row for row in verification["checks"]}
    if any(row["result"] != "pass" for row in checks.values() if row["kind"] == "source_binding"):
        return "UNBOUND", "Required source/context bytes are not bound by the input verifier."
    if (document["measurement_request"]["processing_claim"] == "processing_change"
            and checks["processing"]["result"] != "pass"):
        return "UNBOUND", "The claimed processing instance has no passing independent binding."
    if any(checks[f"mapping.{side}"]["result"] == "fail" for side in ("before", "after")):
        return "UNRESOLVED", "A necessary source-to-representation mapping was independently rejected."
    review = checks[_id("lrm03.review", {"target_id": result["target_id"]})]
    if review["result"] == "fail":
        return "UNRESOLVED", "A necessary comparison premise was explicitly rejected: " + review["reason"]
    family = document["interpretations"]
    if family["state"] == "unknown":
        return "UNBOUND", "The interpretation family is unknown."
    if family["state"] == "empty":
        return "INCOMPATIBLE", "An empty interpretation family cannot establish impact or its absence."
    if family["state"] != "complete" or not family["variants"] or len(family["variants"]) > 64:
        return "UNRESOLVED", "The impact scope requires a nonempty, complete family within the 64-variant bound."
    if result["assessment_state"] == "INCOMPATIBLE":
        return "INCOMPATIBLE", result["reason"]
    if accepted and (result["representation_basis"] == "candidate_only" or review["result"] != "pass"):
        return "UNRESOLVED", "Support/event conclusions require independently accepted source and comparison premises."
    if accepted:
        target = next(row for row in document["measurement_request"]["targets"]
                      if row["target_id"] == result["target_id"])
        if (set(result["compatible_variant_ids"]) != {row["variant_id"] for row in family["variants"]}
                or set(result["closed_obligation_ids"]) != set(target["required_obligation_ids"])):
            return "UNRESOLVED", "Support/event premises require complete target-local comparison coverage in every declared variant."
    return None


def _target_roots(document: dict, target: dict) -> tuple[list[str], list[str]]:
    return tuple(sorted(_expand(document, side, target[f"{side}_ids"]))
                 for side in ("before", "after"))


def _condition_witnesses(target: dict, calculation: dict) -> list[dict]:
    identifier = target["target_id"]
    conclusion = calculation["per_target"][identifier]["conclusion"]
    if conclusion == "unresolved":
        return []
    witnesses = []
    for row in calculation["variants"]:
        roots = row["selected_roots"][identifier]
        if conclusion == "changed":
            witnesses.append(_witness(
                target, [row["variant_id"]], roots["before_relation_ids"], roots["after_relation_ids"],
                "configuration", "This complete common valuation changes the selected condition value. "
                "It is a finite-model witness, not an observation or causal claim.",
                valuation=row["counterexamples"][identifier], rules=["LOGIC_01", "LOGIC_02", "VARIANT_01"]))
        else:
            witnesses.append(_witness(
                target, [row["variant_id"]], roots["before_relation_ids"], roots["after_relation_ids"],
                "derivation", f"Exhaustive evaluation of {row['configuration_count']} admitted common "
                "configurations preserves this condition's value in the recorded variant. The bound "
                "impact artifact retains the complete evaluation scope and answer-vector sets.",
                premises=[row["variant_id"]], rules=["LOGIC_01", "LOGIC_02", "VARIANT_01"]))
    return witnesses


def _blocked_group(document: dict, profile: dict, targets: list[dict], reason: str) -> dict:
    # Obtain the engine's resource declaration without evaluating unaccepted
    # premises or fabricating a completed variant result.
    result = evaluate_condition_group(document, profile, [])
    identifiers = sorted(row["target_id"] for row in targets)
    result.update(target_ids=identifiers, reason=reason, joint_reason=reason,
                  per_target={key: {"conclusion": "unresolved", "reason": reason} for key in identifiers})
    return result


def _joint_witnesses(target: dict, calculation: dict) -> list[dict]:
    if calculation["joint_conclusion"] == "unresolved":
        return []
    witnesses = []
    group = _id("lrm04.condition_group", {"target_ids": calculation["target_ids"]})
    for row in calculation["variants"]:
        roots = row["selected_roots"].values()
        before = sorted({key for item in roots for key in item["before_relation_ids"]})
        after = sorted({key for item in row["selected_roots"].values() for key in item["after_relation_ids"]})
        joint = row["joint_witness"]
        if calculation["joint_conclusion"] == "changed":
            description = (f"The joint target vector for {group} has an admissible {joint['side']} "
                           f"value {joint['vector']} absent from the opposite side's exhaustive vector set "
                           "in this same recorded variant. This target_id names a group member; the "
                           "witness is for the whole group, not an independent pairwise consequence.")
            witnesses.append(_witness(target, [row["variant_id"]], before, after, "configuration",
                                       description, valuation=joint["valuation"],
                                       rules=["LOGIC_01", "LOGIC_02", "VARIANT_01"]))
        else:
            witnesses.append(_witness(
                target, [row["variant_id"]], before, after, "derivation",
                f"Exhaustive evaluation of {row['configuration_count']} common configurations preserves "
                f"the complete joint possibility vectors for {group} in this recorded variant. "
                "Equal separate marginals are not substituted for joint-vector equality.",
                premises=[row["variant_id"]], rules=["LOGIC_01", "LOGIC_02", "VARIANT_01"]))
    return witnesses


def _projection(detail: dict, kind: str | None = None, *, group: dict | None = None,
                witness_ids: list[str] | None = None) -> dict:
    conclusion = group["joint_conclusion"] if group is not None else detail["conclusion"]
    basis = group["representation_basis"] if group is not None else detail["representation_basis"]
    reason = group["joint_reason"] if group is not None else detail["reason"]
    actual_kind = (kind or {"support": "support_change", "condition": "condition_satisfaction_change",
                           "observed": "observed_consequence"}.get(detail["kind"], "unresolved"))
    if conclusion == "unresolved":
        actual_kind = "unresolved"
    value = {"target_id": detail["target_id"], "kind": actual_kind, "conclusion": conclusion,
             "representation_basis": basis, "claim_scope": SCOPES[basis],
             "witness_ids": sorted(witness_ids if witness_ids is not None else detail["witness_ids"]),
             "evidence_refs": sorted(group["evidence_refs"] if group is not None else detail["evidence_refs"]),
             "reason": reason}
    if group is not None and conclusion != "unresolved":
        value["reason"] = "Joint possibility result for the ordered target group: " + _id(
            "lrm04.condition_group", {"target_ids": group["target_ids"]})
    return {"impact_id": _id("lrm04.result", {"role": "joint" if group else "target", **value}), **value}


def _validate_bundle(bundle: dict, document: dict) -> None:
    impact, report, verification = (bundle[key] for key in ("impact", "measurement", "verification"))
    error = next(_impact_validator().iter_errors(impact), None)
    if error is not None:
        path = "/".join(str(part) for part in error.absolute_path)
        raise RuntimeError(f"generated impact violates its schema at {path}: {error.message[:250]}")
    _validate_measurement(report, document, verification)
    validate_schema(verification, "language_relation_verification_v0.schema.json")
    targets = unique_index(document["measurement_request"]["targets"], "target_id")
    details = unique_index(impact["targets"], "target_id")
    witnesses = unique_index(report["witnesses"], "witness_id")
    unique_index(report["impacts"], "impact_id")
    expected = {key for key, target in targets.items()
                if target["question"] in ("condition_impact", "support_preservation", "observed_effect")
                or document["impact_model"] is not None}
    if set(details) != expected:
        raise RuntimeError("impact omits or duplicates a requested impact target")
    for row in [*impact["targets"], *report["impacts"]]:
        if row["target_id"] not in details:
            raise RuntimeError("impact result names an unknown target")
        for identifier in row["witness_ids"]:
            if identifier not in witnesses or witnesses[identifier]["target_id"] != row["target_id"]:
                raise RuntimeError("impact witness is missing or belongs to another target")
    for name, key, prefix in (("impact", "impact_id", "lrm04.impact"),
                              ("verification", "verification_id", "lrm04.verification"),
                              ("measurement", "measurement_id", "lrm04.measurement")):
        value = {field: content for field, content in bundle[name].items() if field != key}
        if bundle[name][key] != _id(prefix, value):
            raise RuntimeError("impact bundle artifact identity mismatch")
    artifact_refs = {impact["impact_id"], "lrm04.artifact." + sha256(canonical_bytes(impact))}
    for target_id in targets:
        check_id = _id("lrm04.artifact_binding", {"target_id": target_id})
        matches = [check for check in verification["checks"] if check["check_id"] == check_id]
        if len(matches) != 1 or set(matches[0]["evidence_refs"]) != artifact_refs:
            raise RuntimeError("verification does not bind the exact detailed impact artifact")
    if impact["input_ref"] != report["input_ref"] or impact["profile_ref"] != report["profile_ref"]:
        raise RuntimeError("impact and measurement input/profile subjects differ")
    if any(value["authority_effect"] != "none" or value["release_authority_activation"]
           for value in bundle.values()):
        raise RuntimeError("diagnostics cannot activate release authority")


def measure_impact_bundle(input_path: Path, *, package_root: Path | None = None,
                          trust_config: Path | None = None,
                          comparison_trust_config: Path | None = None,
                          impact_trust_config: Path | None = None) -> dict:
    """Return a deterministically bound measurement/verification/impact bundle.

    Input/profile schemas remain frozen. Impact trust is an additional externally
    configured premise boundary. A successful function call means diagnostics
    completed; inspect each target's conclusion, basis and unresolved records.
    """
    input_path = Path(input_path)
    root = (Path(package_root) if package_root is not None else input_path.absolute().parent).resolve(strict=True)
    raw = read_input(input_path, root)
    document = strict_json(raw)
    bundle = measure_bundle(input_path, package_root=root, trust_config=trust_config,
                            comparison_trust_config=comparison_trust_config,
                            _include_impact_targets=True)
    report, verification = bundle["measurement"], bundle["verification"]
    if report["input_ref"]["content_sha256"] != sha256(raw) or read_input(input_path, root) != raw:
        raise InputError("input changed before impact evaluation")
    profile = strict_json(safe_read(ROOT, PROFILE_PATH))
    trust = ImpactTrust.load(impact_trust_config, root)
    evaluator = evaluator_reference()
    targets = sorted(document["measurement_request"]["targets"], key=lambda row: row["target_id"])
    results = unique_index(report["results"], "target_id")
    variants = sorted(row["variant_id"] for row in document["interpretations"]["variants"])
    witnesses = unique_index(report["witnesses"], "witness_id")
    details, projections = [], []
    new_checks = []
    publication_budget = _PublicationBudget(MAX_IMPACT_PAYLOAD_BYTES, MAX_IMPACT_PAYLOAD_NODES)
    condition_budget = [0]
    support_conflict_seen = False

    for target in targets:
        if (target["question"] not in ("condition_impact", "support_preservation", "observed_effect")
                and document["impact_model"] is None):
            continue
        identifier, question = target["target_id"], target["question"]
        prior_witness_ids = set(witnesses)
        first_new_check = len(new_checks)
        result = results[identifier]
        kind = "condition" if question == "condition_impact" else "observed" if question == "observed_effect" else "support"
        detail = _detail(target, result, kind)
        boundary = _base_boundary(document, verification, result, accepted=kind != "condition")
        if kind == "condition":
            review_check = next(row for row in verification["checks"]
                                if row["check_id"] == _id("lrm03.review", {"target_id": identifier}))
            if result["representation_basis"] != "candidate_only":
                detail["evidence_refs"] = review_check["evidence_refs"]
            if boundary is None and result["assessment_state"] != "IDENTIFIED":
                boundary = (result["assessment_state"], result["reason"] or "Required condition coverage is unresolved.")
            if boundary is not None:
                detail.update(assessment_state=boundary[0], reason=boundary[1])
            else:
                calculation = evaluate_condition_group(document, profile, [target],
                                                        _evaluation_budget=condition_budget)
                detail["condition"] = calculation
                outcome = calculation["per_target"][identifier]
                detail.update(conclusion=outcome["conclusion"], reason=outcome["reason"])
                detail["assessment_state"] = ("IDENTIFIED" if outcome["conclusion"] != "unresolved" else
                                               "INCOMPATIBLE" if calculation["state"] == "incompatible" else "UNRESOLVED")
                for witness in (_condition_witnesses(target, calculation)
                                if publication_budget.fits(detail) else []):
                    witnesses[witness["witness_id"]] = witness
                    detail["witness_ids"].append(witness["witness_id"])
        else:
            review = trust.target_review(document, report["input_ref"], identifier, variant_ids=variants)
            detail.update(claim_ids=review["claim_ids"], evidence_refs=review["evidence_refs"])
            review_result, review_reason = review["result"], review["reason"]
            if review_result == "pass" and review["mode"] != kind:
                review_result, review_reason = "fail", "The independently reviewed impact mode does not match the requested question."
            new_checks.append(_check(_id("lrm04.review", {"target_id": identifier}), "reference_acceptance",
                                      identifier, review_result, review_reason, review["evidence_refs"]))
            if boundary is not None:
                detail.update(assessment_state=boundary[0], reason=boundary[1])
            elif review_result != "pass":
                detail["reason"] = review_reason or "Required impact premises remain unresolved."
            elif kind == "support":
                try:
                    transition = support_transition(review["model"],
                                                    admitted_base_claim_ids=review["admitted_base_claim_ids"],
                                                    admitted_rule_ids=review["admitted_rule_ids"])
                    detail["support"] = transition
                    # A conflict in a required proof component is not evidence
                    # of a consistent supported consequence. Keep the closure
                    # for diagnosis, without explosion or a successful verdict.
                    conflicts = transition["before"]["conflicts"] + transition["after"]["conflicts"]
                    if conflicts:
                        support_conflict_seen = True
                        detail["reason"] = "The required accepted support scope contains an explicit claim/negation conflict."
                    else:
                        goals = set(review["claim_ids"])
                        before = goals & set(transition["before"]["grounded_claim_ids"])
                        after = goals & set(transition["after"]["grounded_claim_ids"])
                        detail.update(assessment_state="IDENTIFIED",
                                      conclusion="preserved" if before == after else "changed",
                                      reason=("The target's grounded-membership vector is unchanged but supplies no "
                                              "grounded support at either boundary; this is not world-false evidence.")
                                      if not before and not after else None)
                        before_roots, after_roots = _target_roots(document, target)
                        witness = _witness(
                            target, variants, before_roots, after_roots, "support_path",
                            "Fresh least grounded closures were computed before and after removing the declared "
                            "base evidence. Every conjunctive premise is required, and all admitted alternative "
                            "proof routes are retained in the bound impact artifact. These premise/rule refs "
                            "are an inventory of that closed proof graph, not one extra conjunctive rule.",
                            premises=review["admitted_base_claim_ids"],
                            rules=["SUPPORT_01", "CONFLICT_01", *review["admitted_rule_ids"]])
                        witnesses[witness["witness_id"]] = witness
                        detail["witness_ids"].append(witness["witness_id"])
                except (LogicProblem, RecursionError) as exc:
                    detail["reason"] = exc.detail if isinstance(exc, LogicProblem) else "The support scope exceeds the cumulative recursion budget."
            else:
                processing = next(row for row in verification["checks"] if row["check_id"] == "processing")
                observed = review["observation"]
                if (document["measurement_request"]["processing_claim"] != "processing_change"
                        or processing["result"] != "pass" or observed is None):
                    detail.update(assessment_state="UNBOUND", reason="Observed consequences require an accepted actual processing instance and a separate before/after event record.")
                else:
                    detail.update(observation=observed, assessment_state="IDENTIFIED",
                                  conclusion="preserved" if observed["before_value"] == observed["after_value"] else "changed",
                                  reason="Independently reviewed before/after observation; causality is not evaluated.")
                    before_roots, after_roots = _target_roots(document, target)
                    witness = _witness(
                        target, variants, before_roots, after_roots, "derivation",
                        "The separately pinned before/after observation binds the exact input, profile, target, "
                        "processing instance, source instances, subject, run and event. Its recorded Boolean "
                        "values are compared directly; no modeled possibility or temporal sequence proves causality.",
                        premises=[observed["observation_id"], *review["evidence_refs"]])
                    witnesses[witness["witness_id"]] = witness
                    detail["witness_ids"].append(witness["witness_id"])
                new_checks.append(_check(_id("lrm04.observation_binding", {"target_id": identifier}),
                                          "subject_binding", identifier,
                                          "pass" if detail["assessment_state"] == "IDENTIFIED" else "unresolved",
                                          detail["reason"], review["evidence_refs"]))
        if detail["conclusion"] == "unresolved" and not detail["reason"]:
            detail["reason"] = "Required impact evaluation is incomplete."
        detail["witness_ids"] = sorted(set(detail["witness_ids"]))
        detail["evidence_refs"] = sorted(set(detail["evidence_refs"]))
        def coverage_check(value: dict) -> dict:
            return _check(_id("lrm04.coverage", {"target_id": identifier}), "coverage", identifier,
                          "pass" if value["assessment_state"] == "IDENTIFIED" else "unresolved",
                          value["reason"] or "The exact target's bounded impact evaluation is complete within its recorded claim scope.",
                          value["evidence_refs"])

        coverage = coverage_check(detail)
        projection = _projection(detail)
        additions = {key: witnesses[key] for key in witnesses.keys() - prior_witness_ids}
        if not publication_budget.admit({"target": detail, "witnesses": list(additions.values()),
                                         "checks": [*new_checks[first_new_check:], coverage], "projection": projection}):
            detail = _resource_unresolved(detail, trust)
            for key in additions:
                witnesses.pop(key)
            for check in new_checks[first_new_check:]:
                check["evidence_refs"] = _compact_evidence(check["evidence_refs"], trust)
                if check["kind"] != "reference_acceptance":
                    check.update(result="unresolved", reason=detail["reason"])
            coverage, projection = coverage_check(detail), _projection(detail)
        new_checks.append(coverage)
        details.append(detail)
        projections.append(projection)

    condition_targets = [target for target in targets if target["question"] == "condition_impact"]
    joint = None
    if condition_targets:
        index = {row["target_id"]: row for row in details}
        selected = [index[target["target_id"]] for target in condition_targets]
        if all(row["condition"] is not None for row in selected):
            joint = evaluate_condition_group(document, profile, condition_targets,
                                               _evaluation_budget=condition_budget)
        else:
            joint = _blocked_group(document, profile, condition_targets,
                                   "At least one required group member has unresolved source/comparison/coverage premises; no member is silently dropped.")
        basis = "candidate_only" if any(row["representation_basis"] == "candidate_only" for row in selected) else "accepted_reference"
        joint.update(representation_basis=basis, claim_scope=SCOPES[basis],
                     evidence_refs=sorted({key for row in selected for key in row["evidence_refs"]}), witness_ids=[])
        # Stage one member at a time. A group never keeps a successful prefix
        # when its complete common-vector proof exceeds the publication budget.
        for attempt in (0, 1):
            staged_witnesses, staged_projections, staged_checks = {}, [], []
            staged_budget = publication_budget.fork()
            fits = attempt == 1 or staged_budget.admit({"joint_conditions": joint})
            if fits:
                for target in condition_targets:
                    own_witnesses = _joint_witnesses(target, joint)
                    own = sorted(row["witness_id"] for row in own_witnesses)
                    projection = _projection(index[target["target_id"]], "model_possibility_change",
                                             group=joint, witness_ids=own)
                    check = _check(_id("lrm04.joint_coverage", {"target_id": target["target_id"]}),
                                   "coverage", target["target_id"],
                                   "pass" if joint["joint_conclusion"] != "unresolved" else "unresolved",
                                   joint["joint_reason"] or "The complete joint target vector was evaluated in common configurations with recorded variant partitions.",
                                   joint["evidence_refs"])
                    if attempt == 0 and not staged_budget.admit({"witnesses": own_witnesses,
                                                                 "joint_witness_ids": own,
                                                                 "projection": projection, "check": check}):
                        fits = False
                        break
                    staged_witnesses.update((row["witness_id"], row) for row in own_witnesses)
                    staged_projections.append(projection)
                    staged_checks.append(check)
            if fits:
                witnesses.update(staged_witnesses)
                projections.extend(staged_projections)
                new_checks.extend(staged_checks)
                joint["witness_ids"] = sorted(staged_witnesses)
                if attempt == 0:
                    publication_budget = staged_budget
                break
            refs = _compact_evidence(joint["evidence_refs"], trust)
            joint = _blocked_group(document, profile, condition_targets,
                                   "The joint group exceeds the LRM-04 publication resource bound; no successful subset is substituted for its complete vector.")
            joint.update(representation_basis=basis, claim_scope=SCOPES[basis],
                         evidence_refs=refs, witness_ids=[])
        joint["witness_ids"] = sorted(set(joint["witness_ids"]))

    handled = {row["target_id"] for row in details}
    report["unresolved"] = [row for row in report["unresolved"]
                            if not (row["reason_code"] == "impact_not_evaluated"
                                    and set(row["target_ids"]) <= handled)]
    for row in details:
        if row["conclusion"] == "unresolved":
            report["unresolved"].append({"obligation_id": _id("lrm04.unresolved", {"target_id": row["target_id"]}),
                                         "target_ids": [row["target_id"]], "reason_code": "impact_unresolved",
                                         "detail": row["reason"], "source_anchor_ids": []})
    if joint is not None and joint["joint_conclusion"] == "unresolved":
        report["unresolved"].append({"obligation_id": _id("lrm04.joint_unresolved", {"target_ids": joint["target_ids"]}),
                                     "target_ids": joint["target_ids"], "reason_code": "joint_impact_unresolved",
                                     "detail": joint["joint_reason"] or "Joint condition possibilities remain unresolved.",
                                     "source_anchor_ids": []})
    verification["checks"].extend(new_checks)
    # Relation, support and event results do not overwrite canonical observation,
    # binding or causal status. Explicit conflicts still remain visible.
    if any(row["result"] == "fail" for row in verification["checks"]) or support_conflict_seen:
        verification["status_axes"]["consistency_status"] = "conflicting"
    axes = deepcopy(verification["status_axes"])
    impact = {"schema_version": "language_relation_impact_v0", "artifact_kind": "language_relation_impact",
              "input_ref": report["input_ref"], "profile_ref": document["profile_ref"], "evaluator_ref": evaluator,
              "execution": {"status": "completed", "reason": None},
              "evidence_config_sha256": trust.config_sha256, "evidence_pins": trust.evidence_pins,
              "targets": details, "joint_conditions": joint, "status_axes": axes,
              "authority_effect": "none", "release_authority_activation": False}
    impact["impact_id"] = _id("lrm04.impact", impact)
    artifact_refs = [impact["impact_id"], "lrm04.artifact." + sha256(canonical_bytes(impact))]
    for target in targets:
        verification["checks"].append(_check(_id("lrm04.artifact_binding", {"target_id": target["target_id"]}),
                                              "subject_binding", target["target_id"], "pass",
                                              "Exact deterministic impact artifact bytes are bound; this is not semantic acceptance or release authority.",
                                              artifact_refs))
    unique_index(verification["checks"], "check_id")
    verification["checks"].sort(key=lambda row: row["check_id"])
    verification["checker_ref"] = evaluator
    verification.pop("verification_id", None)
    verification["verification_id"] = _id("lrm04.verification", verification)
    for result in report["results"]:
        result["verification_ids"] = [verification["verification_id"]]
    report["verification_refs"] = [{"artifact_id": verification["verification_id"],
                                    "content_sha256": sha256(canonical_bytes(verification))}]
    report["evaluator_ref"] = evaluator
    report["status_axes"] = deepcopy(axes)
    report["witnesses"] = sorted(witnesses.values(), key=lambda row: row["witness_id"])
    report["impacts"] = sorted(projections, key=lambda row: (row["target_id"], row["kind"], row["impact_id"]))
    support_rows = [row for row in details if row["kind"] == "support"]
    report["support"] = (support_rows[0]["support"]["after"]
                         if len(support_rows) == 1 and support_rows[0]["assessment_state"] == "IDENTIFIED" else None)
    report["unresolved"].sort(key=lambda row: (row["target_ids"], row["obligation_id"]))
    report.pop("measurement_id", None)
    report["measurement_id"] = _id("lrm04.measurement", report)
    bundle["impact"] = impact
    _validate_bundle(bundle, document)
    for name, artifact in bundle.items():
        try:
            strict_json(canonical_bytes(artifact))
        except InputError as exc:
            raise RuntimeError(f"The complete {name} artifact exceeds the strict publication reader bounds; no files were published: {exc}") from exc
    if read_input(input_path, root) != raw:
        raise InputError("input changed during impact measurement")
    return bundle
