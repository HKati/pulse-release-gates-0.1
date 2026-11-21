#!/usr/bin/env python3
"""Verify the selected original-loader startup and resume acceptance contract.

Reconstruct the unchanged readout/static prerequisites and original Debian
source/binary inputs before checking the new authored contract. Optional
fixtures exercise the acceptance rules; they never constitute a live original
invocation, hardware qualification, acquired capture, or release authority.
This module performs data-only verification and exclusive report publication.
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
import check_required_gate_idempotence_loader_readout_contract_v0 as prior
import required_gate_idempotence_loader_startup_v0 as startup
import required_gate_idempotence_loader_startup_readout_v0 as policy
import required_gate_idempotence_exec_stop_hosted_io_v0 as transport


ROOT = Path(__file__).resolve().parents[1]
SELF_REL = "tools/check_required_gate_idempotence_loader_startup_contract_v0.py"
SCHEMA_REL = "schemas/required_gate_idempotence_loader_startup_contract_v0.schema.json"
CONTRACT_REL = "docs/compute/required_gate_idempotence_loader_startup_contract_v0/contract_v0.json"
PROFILE = "linux_x86_64_original_loader_startup_contract_v0"
CONTROL_BYTES = 1024 * 1024
PRIOR_CONTRACT = {
    "size_bytes": 19301,
    "sha256": "d5e54e6f0f705c3dab757851c953085fa5f9ae7a2ce4341b51baf99b3b6ae117",
}
PRIOR_SOURCES = {
    "tools/check_required_gate_idempotence_loader_readout_contract_v0.py": {
        "size_bytes": 15081,
        "sha256": "257ddf17c697527c9fbf37505206bf49d7441f908da6c4d7b8ad2c633e1339c5"},
    "schemas/required_gate_idempotence_loader_readout_contract_v0.schema.json": {
        "size_bytes": 75757,
        "sha256": "27f9cd74d84d1e19697e88daa30bef87da00c7b3de1ab836590f3e035f8948be"},
    "tools/required_gate_idempotence_loader_readout_v0.py": {
        "size_bytes": 28524,
        "sha256": "4668aba98a97fcbf7f0c12aa2eb9c2a4535e294dd42ddaa4dd79eb78ff17a54e"},
    "tools/required_gate_idempotence_loader_two_slot_v0.py": {
        "size_bytes": 23627,
        "sha256": "4f0e5e3661a204914bfa65e327b7d88dc7a704efc229d97f4f1fa369cdf372f3"},
    "schemas/required_gate_idempotence_loader_readout_event_v0.schema.json": {
        "size_bytes": 7893,
        "sha256": "a22d643569a5c357d87ca8023712fe0f9cd9b36bb1b1163dd4a1d2fef69f0cc3"},
    "schemas/required_gate_idempotence_loader_two_slot_v0.schema.json": {
        "size_bytes": 10547,
        "sha256": "cd380913c5b689abe5fa6be3dabe206e5edf44e4707c7f4819635066211838da"},
}
NEW_SOURCES = tuple(sorted((
    SELF_REL, SCHEMA_REL,
    "tools/required_gate_idempotence_loader_startup_v0.py",
    "tools/required_gate_idempotence_loader_startup_readout_v0.py",
    "schemas/required_gate_idempotence_loader_startup_invocation_v0.schema.json",
)))
BOUNDARY = {
    "original_invocation_observed": False,
    "live_private_abi_readout_qualified": False,
    "two_slot_breakpoint_qualified": False,
    "invocation_mode_policy_qualified": False,
    "rflags_resume_policy_qualified": False,
    "contemporaneous_backing_acquisition_authenticated": False,
    "source_binary_equivalence_verified": False,
    "authenticated_build_provenance": False,
    "source_build_gate_satisfied": False,
    "original_acquisition_ready": False,
    "original_acquisition_authorized": False,
    "native_acquisition_performed": False,
    "consumer_resolution_observed": False,
    "loader_resolution_verified": False,
    "complete_native_closure_verified": False,
    "containment_enforced": False,
    "selected_runtime_executed": False,
    "production_gate_eligible": False,
    "b2_complete": False,
    "metric_pass": None,
    "authority_effect": "none",
}
OPEN_PREREQUISITES = {
    "source_build": copy.deepcopy(prior.OPEN_PREREQUISITES["source_build"]),
    "invocation": "actual_original_initial_stack_and_process_continuity_not_acquired",
    "hardware": "actual_fresh_same_environment_two_slot_qualification_required",
    "resume": "RF_TF_acceptance_rule_implemented_actual_progression_not_observed",
    "backing_objects": "actual_contemporaneous_original_object_acquisition_required",
    "guard_and_environment": "fresh_qualification_and_original_input_admission_required",
    "original_request_capture_and_collector": "complete_live_acquisition_path_not_implemented_by_this_unit",
    "actual_acquisition": "separate_implementation_review_and_owner_authorization_required",
}


class ContractError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise ContractError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def binding(raw):
    return {"size_bytes": len(raw), "sha256": sha(raw)}


def canonical(value):
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ContractError("loader_startup_contract_json_value") from exc


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        _need(key not in out, "loader_startup_contract_duplicate_key")
        out[key] = value
    return out


def _bad_number(_value):
    raise ContractError("loader_startup_contract_noninteger_number")


def parse(raw):
    _need(type(raw) is bytes and 0 < len(raw) <= CONTROL_BYTES,
          "loader_startup_contract_control_size")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_float=_bad_number, parse_constant=_bad_number)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ContractError("loader_startup_contract_json") from exc


def _bound(raw, expected, code):
    _need(type(raw) is bytes and len(raw) == expected["size_bytes"], code)
    _need(sha(raw) == expected["sha256"], code)


def _same(actual, expected, code):
    _need(canonical(actual) == canonical(expected), code)


def _source(path):
    _need(path in set(NEW_SOURCES) | set(PRIOR_SOURCES) | {prior.CONTRACT_REL},
          "loader_startup_contract_source_path")
    return transport.read_regular(ROOT / path, CONTROL_BYTES)


def _sources():
    old = {path: _source(path) for path in PRIOR_SOURCES}
    for path, raw in old.items():
        _bound(raw, PRIOR_SOURCES[path], "loader_startup_contract_prior_source_changed")
    return old, {path: _source(path) for path in NEW_SOURCES}


def _stable(old, current):
    for path, raw in {**old, **current}.items():
        _need(_source(path) == raw, "loader_startup_contract_source_changed")


def derive_contract(*, prior_report, startup_facts):
    """Construct an authored contract from freshly derived facts, never a verdict."""
    return {
        "record_type": "required_gate_idempotence_loader_startup_contract_v0",
        "profile": PROFILE,
        "evidence_role": "authored_acceptance_contract_and_static_recipe_only",
        "prior_readout_prerequisite": {
            "contract_path": prior.CONTRACT_REL,
            "contract": dict(PRIOR_CONTRACT),
            "verification_report": binding(prior.canonical(prior_report)),
            "implementation_sources": copy.deepcopy(PRIOR_SOURCES),
            "fresh_static_and_readout_contract_reconstruction_required": True,
            "saved_report_is_acceptance_input": False,
            "historical_source_count": 81,
        },
        "startup_derivation": copy.deepcopy(startup_facts),
        "selected_acceptance_policy": copy.deepcopy(policy.POLICY),
        "fixture_policy": {
            "allowed_evidence_origin": "authored_test_fixture",
            "initial_stack_and_original_readouts_require_one_fixture_process": True,
            "hardware_probe_is_separate_fixture_subject": True,
            "actual_qualification_or_capture_accepted": False,
            "fixture_success_closes_build_or_acquisition_gate": False,
            "incomplete_hardware_prefix_can_be_complete": False,
        },
        "unresolved_prerequisites": copy.deepcopy(OPEN_PREREQUISITES),
        "implementation_sources": list(NEW_SOURCES),
        "boundary": copy.deepcopy(BOUNDARY),
    }


def _verify(contract_bytes, expected_contract_sha256, prior_contract_bytes,
            static_record_bytes, historical_entry_archive_bytes, artifact_members):
    _need(type(expected_contract_sha256) is str and
          re.fullmatch(r"[0-9a-f]{64}", expected_contract_sha256) is not None,
          "loader_startup_contract_external_digest")
    _need(type(contract_bytes) is bytes and 0 < len(contract_bytes) <= CONTROL_BYTES,
          "loader_startup_contract_control_size")
    _need(sha(contract_bytes) == expected_contract_sha256,
          "loader_startup_contract_digest_mismatch")
    value = parse(contract_bytes)
    old, current = _sources()
    schema = parse(current[SCHEMA_REL])
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(value)
    except (jsonschema.ValidationError, jsonschema.SchemaError) as exc:
        raise ContractError("loader_startup_contract_schema") from exc
    _same(value["boundary"], BOUNDARY, "loader_startup_contract_boundary")
    _same(value["unresolved_prerequisites"], OPEN_PREREQUISITES,
          "loader_startup_contract_prerequisites")
    raw = _source(prior.CONTRACT_REL) if prior_contract_bytes is None else prior_contract_bytes
    _bound(raw, PRIOR_CONTRACT, "loader_startup_contract_prior_contract")
    parts = prior.static.read_artifact_members() if artifact_members is None else artifact_members
    prior_report, record, historical, prior_old, prior_current = prior._verify(
        raw, PRIOR_CONTRACT["sha256"], static_record_bytes,
        historical_entry_archive_bytes, parts)
    inputs = prior.static._reassemble_inputs(parts)
    source = prior.static.source
    originals = {}
    for package_name, filename, member, wanted in (
        ("libc6", "libc6_2.41-12+deb13u4_amd64.deb", source.LOADER_MEMBER, source.LOADER_BINDING),
        ("libc6-dbg", "libc6-dbg_2.41-12+deb13u4_amd64.deb", source.DEBUG_MEMBER, source.DEBUG_BINDING),
    ):
        _facts, originals[package_name] = source._package(
            inputs[filename], package_name,
            record["source_binding"]["packages"][package_name]["index"], member, wanted)
    facts = startup.derive_startup_facts(
        inputs=inputs, loader=originals["libc6"], debug=originals["libc6-dbg"])
    expected = derive_contract(prior_report=prior_report, startup_facts=facts)
    _same(value, expected, "loader_startup_contract_mismatch")
    prior._stable(prior_old, prior_current)
    _stable(old, current)
    report = {
        "record_type": "required_gate_idempotence_loader_startup_contract_verification_v0",
        "profile": PROFILE,
        "status": "accepted",
        "evidence_role": "authored_acceptance_policy_and_static_recipe_only",
        "contract": binding(contract_bytes),
        "contract_verified": True,
        "prior_static_and_readout_contract_reconstructed": True,
        "selected_startup_mode_decision_verified": True,
        "initial_stack_acceptance_checker_implemented": True,
        "hardware_resume_acceptance_rule_implemented": True,
        "prior_report": binding(prior.canonical(prior_report)),
        "startup_derivation": binding(canonical(facts)),
        "prior_sources": copy.deepcopy(PRIOR_SOURCES),
        "implementation_sources": {p: binding(b) for p, b in sorted(current.items())},
        "historical_source_file_count": prior_report["historical_source_file_count"],
        "original_DT_NEEDED_occurrences": prior_report["original_DT_NEEDED_occurrences"],
        "unresolved_prerequisites": copy.deepcopy(OPEN_PREREQUISITES),
        **copy.deepcopy(BOUNDARY),
    }
    return report, record, historical, old, current, prior_old, prior_current


def verify_contract(*, contract_bytes, expected_contract_sha256,
                    prior_contract_bytes=None, static_record_bytes=None,
                    historical_entry_archive_bytes=None, artifact_members=None):
    try:
        return _verify(contract_bytes, expected_contract_sha256, prior_contract_bytes,
                       static_record_bytes, historical_entry_archive_bytes, artifact_members)[0]
    except ContractError:
        raise
    except (ValueError, TypeError, KeyError, OSError, IndexError,
            OverflowError, RecursionError) as exc:
        raise ContractError("loader_startup_contract_evidence_rejected") from exc


def verify_fixtures(*, contract_bytes, expected_contract_sha256, invocation,
                    invocation_files, events, files_by_event, transcript,
                    transcript_files, prior_contract_bytes=None, static_record_bytes=None,
                    historical_entry_archive_bytes=None, artifact_members=None):
    """Check three authored fixture surfaces, preserving their subject boundaries."""
    try:
        report, record, historical, old, current, prior_old, prior_current = _verify(
            contract_bytes, expected_contract_sha256, prior_contract_bytes,
            static_record_bytes, historical_entry_archive_bytes, artifact_members)
        recovered = prior.static.prior.reconstruct_historical_entry(historical)
        result = policy.verify_policy_fixtures(
            invocation=invocation, invocation_files=invocation_files,
            events=events, files_by_event=files_by_event, transcript=transcript,
            transcript_files=transcript_files, static_record=record, native=recovered["native"])
        complete = result["complete_fixture_set_verified"]
        _need(type(complete) is bool, "loader_startup_contract_completion_type")
        prior._stable(prior_old, prior_current)
        _stable(old, current)
        return {
            "record_type": "required_gate_idempotence_loader_startup_fixture_verification_v0",
            "profile": PROFILE,
            "status": "accepted_test_fixtures" if complete else "incomplete_test_fixtures",
            "evidence_origin": "authored_test_fixture",
            "complete_fixture_set_verified": complete,
            "contract_report": binding(canonical(report)),
            "selected_policy_fixture": result,
            "fixture_domains_are_one_acquired_process": False,
            **copy.deepcopy(BOUNDARY),
        }
    except ContractError:
        raise
    except (ValueError, TypeError, KeyError, OSError, IndexError,
            OverflowError, RecursionError) as exc:
        raise ContractError("loader_startup_contract_fixture_rejected") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        raw = transport.read_regular(Path(args.contract), CONTROL_BYTES)
        report = verify_contract(contract_bytes=raw,
                                 expected_contract_sha256=args.contract_sha256)
        transport.write_new(Path(args.output), canonical(report))
    except (ValueError, OSError) as exc:
        print(getattr(exc, "code", "loader_startup_contract_rejected"), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
