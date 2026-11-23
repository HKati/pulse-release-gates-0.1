#!/usr/bin/env python3
"""Evaluate one preserved rebuild under an externally selected source policy.

All signature, package, source and published-service evidence is reconstructed
from bytes.  Without a trusted caller's exact accepted_policy_sha256, successful
evidence verification remains a candidate and source/build admission is blocked.
Selecting that digest enables only the named policy's scoped source/build
decision.  It never authorizes or executes an original loader or a rebuild.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jsonschema
import check_required_gate_idempotence_loader_rebuild_attestation_binding_v0 as prior
import required_gate_idempotence_loader_rebuild_acceptance_v0 as evidence
import required_gate_idempotence_exec_stop_hosted_io_v0 as transport


ROOT = Path(__file__).resolve().parents[1]
SELF_REL = "tools/check_required_gate_idempotence_loader_rebuild_acceptance_v0.py"
SCHEMA_REL = "schemas/required_gate_idempotence_loader_rebuild_acceptance_v0.schema.json"
HELPER_REL = "tools/required_gate_idempotence_loader_rebuild_acceptance_v0.py"
RECORD_REL = "docs/compute/required_gate_idempotence_loader_rebuild_acceptance_v0/record_v0.json"
POLICY_REL = "docs/compute/required_gate_idempotence_loader_rebuild_acceptance_v0/policy_v0.json"
EVIDENCE_REL = "docs/compute/required_gate_idempotence_loader_rebuild_acceptance_v0/preservation/public_service_evidence_v0.zip"
PROFILE = "linux_x86_64_original_loader_rebuild_acceptance_v0"
BASE_COMMIT = "846db3d94d7fc869b6a8d20bdc98efe6d26c81b4"
CONTROL_BYTES = 1024 * 1024
JSON_DEPTH = 24
JSON_NODES = 32768
PRIOR_RECORD = {
    "size_bytes": 15758,
    "sha256": "19c346076b6ec7d5e7d948d13d16a3ba6f45a56b4fdcf9236d9a445dddbc1d7f",
}
PRIOR_SOURCES = {
    "schemas/required_gate_idempotence_loader_rebuild_attestation_binding_v0.schema.json": {
        "size_bytes": 58769,
        "sha256": "98f7b94b7bb0fde41d90b7c5537b179062f050e656616af659b7e43d5fa73512",
    },
    "tools/check_required_gate_idempotence_loader_rebuild_attestation_binding_v0.py": {
        "size_bytes": 17378,
        "sha256": "274cdd111e325a1be80072f9ac232390700affdb0d6b639bf89e60a8f8ce69c8",
    },
    "tools/required_gate_idempotence_loader_rebuild_attestation_v0.py": {
        "size_bytes": 16377,
        "sha256": "0b76e288be6e66e26ec3d9cb3bfc920f901ea02a796702ddf82dd5daf2815f1d",
    },
}
# This is a supported candidate's byte identity, not approval of that policy.
# A trusted caller must separately supply the exact accepted_policy_sha256.
POLICY_BINDING = {
    "size_bytes": 12260,
    "sha256": "1b1e4f414ffa7e56a8494f8a6d6051594c800cae978fa90585c4a02041bed953",
}
NEW_SOURCES = tuple(sorted((SELF_REL, SCHEMA_REL, HELPER_REL)))
SELECTION_CONTRACT = {
    "external_selection_argument": "accepted_policy_sha256",
    "trusted_caller_must_select_exact_policy_digest": True,
    "candidate_record_or_policy_can_select_itself": False,
    "approval_boolean_is_accepted": False,
    "saved_report_is_acceptance_input": False,
    "record_is_unchanged_by_external_selection": True,
    "selection_authenticates_owner_identity_or_adoption": False,
    "selection_is_original_execution_authorization": False,
}
BOUNDARY = {
    **copy.deepcopy(prior.BOUNDARY),
    "source_build_gate_satisfied_under_policy": False,
    "owner_policy_adoption_verified": False,
    "future_host_admitted": False,
    "historical_service_deployment_verified": False,
    "complete_rebuild_execution_observed": False,
    "current_service_role_independently_proved_by_signature_math": False,
    "preserved_https_response_is_live_tls_reauthentication": False,
    "step5c_complete": False,
    "release_authorized": False,
}


class AcceptanceError(ValueError):
    """Stable failure code without reflected evidence or backend diagnostics."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise AcceptanceError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def binding(raw):
    return {"size_bytes": len(raw), "sha256": sha(raw)}


def canonical(value):
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise AcceptanceError("loader_rebuild_acceptance_json_value") from exc


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        _need(key not in value, "loader_rebuild_acceptance_duplicate_key")
        value[key] = item
    return value


def _invalid_number(_value):
    raise AcceptanceError("loader_rebuild_acceptance_noninteger_number")


def parse(raw):
    _need(type(raw) is bytes and 0 < len(raw) <= CONTROL_BYTES,
          "loader_rebuild_acceptance_control_size")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_float=_invalid_number, parse_constant=_invalid_number)
    except AcceptanceError:
        raise
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise AcceptanceError("loader_rebuild_acceptance_invalid_json") from exc
    pending = [(value, 0)]
    nodes = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        _need(depth <= JSON_DEPTH and nodes <= JSON_NODES,
              "loader_rebuild_acceptance_json_complexity")
        if type(item) is dict:
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
    return value


def _digest(value, code):
    _need(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None, code)


def _same(actual, expected, code):
    _need(canonical(actual) == canonical(expected), code)


def _bound(raw, wanted, code):
    _need(type(raw) is bytes and len(raw) == wanted["size_bytes"], code + "_size")
    _need(sha(raw) == wanted["sha256"], code + "_sha256")


def _source(path):
    _need(path in set(PRIOR_SOURCES) | set(NEW_SOURCES) | {prior.RECORD_REL},
          "loader_rebuild_acceptance_source_path")
    return transport.read_regular(ROOT / path, CONTROL_BYTES)


def _sources():
    old = {path: _source(path) for path in PRIOR_SOURCES}
    for path, raw in old.items():
        _bound(raw, PRIOR_SOURCES[path], "loader_rebuild_acceptance_prior_source_changed")
    return old, {path: _source(path) for path in NEW_SOURCES}


def _stable(old, current):
    for path, raw in {**old, **current}.items():
        _need(_source(path) == raw, "loader_rebuild_acceptance_source_changed")


def read_evidence_archive():
    return transport.read_regular(ROOT / EVIDENCE_REL,
                                  evidence.EVIDENCE_ARCHIVE_BINDING["size_bytes"])


def _stable_prior_report(report):
    # The backend executable is freshly checked on every host.  Its host-specific
    # identity belongs in the fresh report, never in an authored record constant.
    stable = copy.deepcopy(report)
    stable.pop("backend_observation", None)
    return stable


def derive_record(*, prior_report, service_facts, policy_bytes):
    """Create the candidate record; this function does not perform admission."""
    return {
        "record_type": "required_gate_idempotence_loader_rebuild_acceptance_v0",
        "profile": PROFILE,
        "development_base": BASE_COMMIT,
        "evidence_role": "candidate_current_service_rebuild_acceptance_with_reviewed_source_resolution",
        "candidate_policy": {
            "path": POLICY_REL,
            "content": binding(policy_bytes),
            "external_selection_required": True,
            "record_embeds_policy_approval": False,
        },
        "prior_rebuild_attestation_prerequisite": {
            "record_path": prior.RECORD_REL,
            "record": copy.deepcopy(PRIOR_RECORD),
            "verification_report_without_runtime_backend_observation":
                binding(prior.canonical(_stable_prior_report(prior_report))),
            "implementation_sources": copy.deepcopy(PRIOR_SOURCES),
            "fresh_signature_build_record_startup_static_source_package_reconstruction_required": True,
            "runtime_backend_observation_excluded_from_authored_constant": True,
            "saved_report_is_acceptance_input": False,
        },
        "public_service_facts": copy.deepcopy(service_facts),
        "implementation_sources": list(NEW_SOURCES),
        "selection_contract": copy.deepcopy(SELECTION_CONTRACT),
        "boundary": copy.deepcopy(BOUNDARY),
    }


def _validate_schema(record, policy, raw_schema):
    try:
        schema = parse(raw_schema)
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(record)
        jsonschema.Draft202012Validator(schema["$defs"]["policy"]).validate(policy)
    except (jsonschema.ValidationError, jsonschema.SchemaError, KeyError) as exc:
        raise AcceptanceError("loader_rebuild_acceptance_schema") from exc


def _policy_subject(policy, *, inputs, buildinfo, service_facts):
    """Join the selected policy's subject to the same freshly verified bytes."""
    source = prior.prior.startup.prior.static.source
    subject = {
        "architecture": service_facts["service_metadata"]["architecture"],
        "source_name": source.SOURCE_NAME,
        "source_version": source.VERSION,
        "buildinfo": {"filename": prior.prior.BUILDINFO_NAME, **binding(buildinfo)},
        "products": {name: binding(inputs[name]) for name in prior.rebuild.PACKAGES},
        "source_inputs": {name: binding(inputs[name]) for name in evidence.SOURCE_INPUT_BINDINGS},
        "loader_member": {"path": source.LOADER_MEMBER, **source.LOADER_BINDING},
        "debug_member": {"path": source.DEBUG_MEMBER, **source.DEBUG_BINDING},
    }
    _same(policy["subject"], subject, "loader_rebuild_acceptance_policy_subject")
    role = policy["service_role_selection"]
    _need(role["in_toto_keyid"] == prior.rebuild.SELECTED_KEYID
          and role["public_key_hex"] == prior.rebuild.SELECTED_PUBLIC_HEX
          and role["build_id"] == service_facts["service_metadata"]["id"],
          "loader_rebuild_acceptance_policy_service_role")
    _same(policy["preserved_evidence"], {
        "archive_path": EVIDENCE_REL,
        "archive_binding": evidence.EVIDENCE_ARCHIVE_BINDING,
        "decoded_total_bytes": evidence.EVIDENCE_DECODED_BYTES,
        "members": evidence.EVIDENCE_MEMBERS,
    }, "loader_rebuild_acceptance_policy_evidence")
    _same(policy["prior_rebuild_attestation"], {
        "record_path": prior.RECORD_REL,
        "record": PRIOR_RECORD,
        "fresh_chain_and_signature_verification_required": True,
        "saved_report_is_acceptance_input": False,
    }, "loader_rebuild_acceptance_policy_prior")
    snapshot = service_facts["snapshot"]
    timing = policy["verification_time_policy"]
    _same({
        "snapshot_date_utc": timing["snapshot_date_utc"],
        "retrieval_started_at_utc": timing["retrieval_started_at_utc"],
        "retrieval_finished_at_utc": timing["retrieval_finished_at_utc"],
    }, {
        "snapshot_date_utc": snapshot["snapshot_started_at_utc"][:10],
        "retrieval_started_at_utc": snapshot["snapshot_started_at_utc"],
        "retrieval_finished_at_utc": snapshot["snapshot_completed_at_utc"],
    }, "loader_rebuild_acceptance_policy_time")
    observations = {row["filename"]: row["observed_at_utc"] for row in snapshot["responses"]}
    _same({name: observations[name] for name in evidence.PRIOR_CARRIER_NAMES},
          {name: timing["key_and_two_attestations_observed_at_utc"]
           for name in evidence.PRIOR_CARRIER_NAMES},
          "loader_rebuild_acceptance_policy_key_observation_time")


def _verify(*, record_bytes, expected_record_sha256, policy_bytes,
            accepted_policy_sha256, evidence_archive_bytes, prior_record_bytes,
            build_record_bytes, startup_contract_bytes, prior_contract_bytes,
            static_record_bytes, historical_entry_archive_bytes, artifact_members,
            build_carriers, attestations, public_keys_bytes):
    _digest(expected_record_sha256, "loader_rebuild_acceptance_external_record_digest")
    if accepted_policy_sha256 is not None:
        _digest(accepted_policy_sha256, "loader_rebuild_acceptance_external_policy_digest")
    # Check the new input extents before hashing/parsing or invoking the prior
    # signature backend.  The helper also checks every ZIP/member/source extent.
    for raw in (record_bytes, policy_bytes):
        _need(type(raw) is bytes and 0 < len(raw) <= CONTROL_BYTES,
              "loader_rebuild_acceptance_control_size")
    archive = read_evidence_archive() if evidence_archive_bytes is None else evidence_archive_bytes
    _need(type(archive) is bytes and
          len(archive) == evidence.EVIDENCE_ARCHIVE_BINDING["size_bytes"],
          "loader_rebuild_acceptance_archive_size")
    prior_raw = _source(prior.RECORD_REL) if prior_record_bytes is None else prior_record_bytes
    _need(type(prior_raw) is bytes and len(prior_raw) == PRIOR_RECORD["size_bytes"],
          "loader_rebuild_acceptance_prior_record_size")
    _need(sha(record_bytes) == expected_record_sha256,
          "loader_rebuild_acceptance_record_digest_mismatch")
    _bound(policy_bytes, POLICY_BINDING, "loader_rebuild_acceptance_candidate_policy")
    if accepted_policy_sha256 is not None:
        _need(accepted_policy_sha256 == sha(policy_bytes),
              "loader_rebuild_acceptance_selected_policy_mismatch")
    _bound(prior_raw, PRIOR_RECORD, "loader_rebuild_acceptance_prior_record")
    value, policy = parse(record_bytes), parse(policy_bytes)
    old, current = _sources()
    _validate_schema(value, policy, current[SCHEMA_REL])
    _same(value["boundary"], BOUNDARY, "loader_rebuild_acceptance_boundary")
    _same(value["selection_contract"], SELECTION_CONTRACT,
          "loader_rebuild_acceptance_selection_contract")

    static = prior.prior.startup.prior.static
    parts = static.read_artifact_members() if artifact_members is None else artifact_members
    inputs = static._reassemble_inputs(parts)
    source_inputs = {name: inputs[name] for name in evidence.SOURCE_INPUT_BINDINGS}
    build_carriers = prior.prior.read_carriers() if build_carriers is None else build_carriers
    prior.prior._carrier_lengths(build_carriers)
    buildinfo = build_carriers[prior.prior.BUILDINFO_NAME]
    evidence.preflight_public_service_inputs(
        archive_bytes=archive, buildinfo_bytes=buildinfo, source_inputs=source_inputs)

    if attestations is None or public_keys_bytes is None:
        carriers = prior.read_carriers()
        if attestations is None:
            attestations = {name: carriers[name] for name in prior.ATTESTATION_NAMES}
        if public_keys_bytes is None:
            public_keys_bytes = carriers[prior.PUBLIC_KEYS_NAME]
    prior._carrier_lengths(attestations, public_keys_bytes)
    published = evidence.read_public_service_evidence(archive)
    for name, raw in {**attestations, prior.PUBLIC_KEYS_NAME: public_keys_bytes}.items():
        _need(published[name] == raw, "loader_rebuild_acceptance_current_prior_carrier_mismatch")
    service_facts = evidence.derive_public_service_facts(
        archive_bytes=archive, buildinfo_bytes=buildinfo, source_inputs=source_inputs)

    # There is no saved-report parameter.  The very same selected bytes used by
    # the service/source joins undergo the complete prior signature/static proof.
    prior_old, prior_current = prior._sources()
    prior_report = prior.verify_binding(
        record_bytes=prior_raw, expected_record_sha256=PRIOR_RECORD["sha256"],
        build_record_bytes=build_record_bytes,
        startup_contract_bytes=startup_contract_bytes,
        prior_contract_bytes=prior_contract_bytes, static_record_bytes=static_record_bytes,
        historical_entry_archive_bytes=historical_entry_archive_bytes,
        artifact_members=parts, build_carriers=build_carriers,
        attestations=attestations, public_keys_bytes=public_keys_bytes)
    _policy_subject(policy, inputs=inputs, buildinfo=buildinfo, service_facts=service_facts)
    expected = derive_record(prior_report=prior_report, service_facts=service_facts,
                             policy_bytes=policy_bytes)
    _same(value, expected, "loader_rebuild_acceptance_record_mismatch")
    prior._backend_stable(prior_report["backend_observation"])
    prior._stable(prior_old, prior_current)
    _stable(old, current)
    selected = accepted_policy_sha256 is not None
    return {
        "record_type": "required_gate_idempotence_loader_rebuild_acceptance_verification_v0",
        "profile": PROFILE,
        "status": ("accepted_scoped_rebuild_source_policy" if selected
                   else "candidate_rebuild_acceptance_evidence_verified"),
        "evidence_role": "current_service_rebuild_statement_and_reviewed_source_resolution",
        "record": binding(record_bytes),
        "record_binding_verified": True,
        "candidate_evidence_verified": True,
        "policy": binding(policy_bytes),
        "policy_evaluation": "passed",
        "policy_selection": ("externally_selected_exact_policy" if selected
                             else "pending_external_selection"),
        "accepted_policy_sha256": accepted_policy_sha256,
        "policy_admission_status": ("accepted_scoped_source_build_under_policy" if selected
                                    else "blocked_pending_external_selection"),
        "prior_chain_reconstructed": True,
        "same_selected_current_and_preserved_attestation_bytes_verified": True,
        "prior_report": binding(prior.canonical(prior_report)),
        "prior_report_without_runtime_backend_observation":
            binding(prior.canonical(_stable_prior_report(prior_report))),
        "backend_observation": copy.deepcopy(prior_report["backend_observation"]),
        "public_service_facts": binding(canonical(service_facts)),
        "evidence_archive": binding(archive),
        "prior_sources": copy.deepcopy(PRIOR_SOURCES),
        "implementation_sources": {path: binding(raw) for path, raw in sorted(current.items())},
        "selection_contract": copy.deepcopy(SELECTION_CONTRACT),
        **copy.deepcopy(BOUNDARY),
        "source_build_gate_satisfied_under_policy": selected,
    }


def verify_acceptance(*, record_bytes, expected_record_sha256, policy_bytes,
                      accepted_policy_sha256=None, evidence_archive_bytes=None,
                      prior_record_bytes=None, build_record_bytes=None,
                      startup_contract_bytes=None, prior_contract_bytes=None,
                      static_record_bytes=None, historical_entry_archive_bytes=None,
                      artifact_members=None, build_carriers=None, attestations=None,
                      public_keys_bytes=None):
    """Verify candidate evidence and optionally apply a trusted external selection.

    accepted_policy_sha256 is a trust-root input of the embedding caller.  It
    must not be copied from an untrusted record, report, artifact or policy.
    This function cannot authenticate a caller's identity or owner adoption.
    """
    try:
        return _verify(
            record_bytes=record_bytes, expected_record_sha256=expected_record_sha256,
            policy_bytes=policy_bytes, accepted_policy_sha256=accepted_policy_sha256,
            evidence_archive_bytes=evidence_archive_bytes, prior_record_bytes=prior_record_bytes,
            build_record_bytes=build_record_bytes, startup_contract_bytes=startup_contract_bytes,
            prior_contract_bytes=prior_contract_bytes, static_record_bytes=static_record_bytes,
            historical_entry_archive_bytes=historical_entry_archive_bytes,
            artifact_members=artifact_members, build_carriers=build_carriers,
            attestations=attestations, public_keys_bytes=public_keys_bytes)
    except AcceptanceError:
        raise
    except (ValueError, TypeError, KeyError, OSError, IndexError,
            OverflowError, RecursionError) as exc:
        raise AcceptanceError("loader_rebuild_acceptance_evidence_rejected") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True)
    parser.add_argument("--record-sha256", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--accepted-policy-sha256")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        raw = transport.read_regular(Path(args.record), CONTROL_BYTES)
        policy = transport.read_regular(Path(args.policy), CONTROL_BYTES)
        report = verify_acceptance(
            record_bytes=raw, expected_record_sha256=args.record_sha256, policy_bytes=policy,
            accepted_policy_sha256=args.accepted_policy_sha256)
        transport.write_new(Path(args.output), canonical(report))
    except (ValueError, OSError) as exc:
        print(getattr(exc, "code", "loader_rebuild_acceptance_rejected"), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
