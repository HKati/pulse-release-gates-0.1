#!/usr/bin/env python3
"""Verify the B2 loader readout contract and explicitly authored test fixtures.

The prior static binding is freshly reconstructed from the pinned historical
carrier and full preserved Debian inputs. Test-fixture consistency never becomes
live qualification, acquisition readiness, consumer observation or authority.
No collector, native probe, subprocess or network operation is invoked here.
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
import check_required_gate_idempotence_loader_binary_binding_v0 as static
import required_gate_idempotence_loader_readout_v0 as readout
import required_gate_idempotence_loader_two_slot_v0 as two_slot
import required_gate_idempotence_exec_stop_hosted_io_v0 as transport


ROOT = Path(__file__).resolve().parents[1]
SELF_REL = "tools/check_required_gate_idempotence_loader_readout_contract_v0.py"
SCHEMA_REL = "schemas/required_gate_idempotence_loader_readout_contract_v0.schema.json"
CONTRACT_REL = "docs/compute/required_gate_idempotence_loader_readout_contract_v0/contract_v0.json"
PROFILE = "linux_x86_64_loader_readout_contract_v0"
CONTROL_BYTES = 1024 * 1024
STATIC_RECORD = {"size_bytes": 132289,
    "sha256": "d5679d1afab1c13db460ad8d818e5a07241b8dfeb079f410069c550c9f10d065"}
STATIC_SOURCES = {
    "tools/check_required_gate_idempotence_loader_binary_binding_v0.py": {
        "size_bytes": 27302, "sha256": "8b23d285d7995d9d33a434ea74be2a873b083f4d531d12074b874c8e9b5aad1f"},
    "schemas/required_gate_idempotence_loader_binary_binding_v0.schema.json": {
        "size_bytes": 103806, "sha256": "a554cf4a4b6a4f0ececd2fe61c06648bee6dc7c3cbf550195b9d5808b3438002"},
    "tools/required_gate_idempotence_loader_binary_v0.py": {
        "size_bytes": 30222, "sha256": "06f6921fd051b2bec7a40949bebafd5222c1cfddff4fad850750fa3c0dc6a369"},
    "tools/required_gate_idempotence_loader_source_v0.py": {
        "size_bytes": 32215, "sha256": "bcc8da48d19666ab8b79a5586b3c486d44c177def9c9c24ec902c050bb92d1ff"},
}
NEW_SOURCES = tuple(sorted((
    SELF_REL, SCHEMA_REL,
    "tools/required_gate_idempotence_loader_readout_v0.py",
    "tools/required_gate_idempotence_loader_two_slot_v0.py",
    "schemas/required_gate_idempotence_loader_readout_event_v0.schema.json",
    "schemas/required_gate_idempotence_loader_two_slot_v0.schema.json",
)))
BOUNDARY = {
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
    "source_build": {
        "original_gate": "exact_original_loader_source_debug_binary_binding",
        "status": "unsatisfied",
        "recorded_gaps": ["source_to_binary_equivalence_not_independently_reproduced",
                          "authenticated_build_process_provenance_not_established"],
        "accepted_build_evidence_policy": "not_selected",
        "alternative_evidence_route_selected": False,
        "package_version_build_id_debuglink_or_DWARF_is_build_provenance": False,
    },
    "invocation_modes": {
        "trace_mode": "decoded_but_selected_invocation_policy_not_qualified",
        "open_mode": "decoded_but_selected_invocation_policy_not_qualified",
        "arbitrary_decoded_values_authorize_acquisition": False,
    },
    "guard_and_environment": "fresh_qualification_and_original_input_admission_required",
    "hardware": "actual_same_environment_two_slot_qualification_required",
    "rflags_resume_policy": "raw_flags_preserved_TF_forbidden_RF_resume_policy_not_qualified",
    "live_readout": "actual_original_private_ABI_readout_not_qualified",
    "original_request_capture_and_collector": "not_implemented_by_this_unit",
    "actual_acquisition": "separate_review_and_owner_authorization_required",
}


class ContractError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(test, code):
    if not test:
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
        raise ContractError("loader_readout_contract_json_value") from exc


def _same(actual, expected, code):
    _need(canonical(actual) == canonical(expected), code)


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        _need(key not in out, "loader_readout_contract_duplicate_key")
        out[key] = value
    return out


def _bad_number(_value):
    raise ContractError("loader_readout_contract_noninteger_number")


def parse(raw):
    _need(type(raw) is bytes and 0 < len(raw) <= CONTROL_BYTES,
          "loader_readout_contract_control_size")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_float=_bad_number, parse_constant=_bad_number)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ContractError("loader_readout_contract_json") from exc


def _bound(raw, wanted, code):
    _need(type(raw) is bytes and len(raw) == wanted["size_bytes"], code)
    _need(sha(raw) == wanted["sha256"], code)


def _source(path):
    _need(path in set(NEW_SOURCES) | set(STATIC_SOURCES) | {static.RECORD_REL},
          "loader_readout_contract_source_path")
    return transport.read_regular(ROOT / path, CONTROL_BYTES)


def _sources():
    originals = {path: _source(path) for path in STATIC_SOURCES}
    for path, raw in originals.items():
        _bound(raw, STATIC_SOURCES[path], "loader_readout_contract_static_source_changed")
    current = {path: _source(path) for path in NEW_SOURCES}
    return originals, current


def _stable(originals, current):
    for path, raw in {**originals, **current}.items():
        _need(_source(path) == raw, "loader_readout_contract_source_changed")


def derive_contract(*, static_record, static_report):
    """Construct the authored contract; this is not an acceptance API."""
    return {
        "record_type": "required_gate_idempotence_loader_readout_contract_v0",
        "profile": PROFILE,
        "evidence_role": "authored_checker_contract_not_live_qualification",
        "static_prerequisite": {
            "record_path": static.RECORD_REL, "record": dict(STATIC_RECORD),
            "verification_report": binding(static.canonical(static_report)),
            "implementation_sources": copy.deepcopy(STATIC_SOURCES),
            "fresh_reconstruction_required": True,
            "saved_report_is_acceptance_input": False,
            "historical_source_count": 81,
        },
        "selected_recipe": copy.deepcopy(static_record["recipe"]),
        "occurrence_obligations": copy.deepcopy(static_record["occurrence_bindings"]),
        "readout_checker": copy.deepcopy(readout.POLICY),
        "two_slot_checker": copy.deepcopy(two_slot.POLICY),
        "fixture_policy": {
            "allowed_evidence_origin": "authored_test_fixture",
            "actual_qualification_evidence_accepted": False,
            "authored_fixture_is_actual_acquisition": False,
            "hardware_fixture_and_original_readout_fixture_are_one_process": False,
            "fixture_clock_is_observed_clock": False,
            "fixture_success_can_close_source_build_gate": False,
        },
        "unresolved_prerequisites": copy.deepcopy(OPEN_PREREQUISITES),
        "implementation_sources": list(NEW_SOURCES),
        "boundary": copy.deepcopy(BOUNDARY),
    }


def _verify(contract_bytes, expected_contract_sha256, static_record_bytes,
            historical_entry_archive_bytes, artifact_members):
    _need(type(expected_contract_sha256) is str and
          re.fullmatch(r"[0-9a-f]{64}", expected_contract_sha256) is not None,
          "loader_readout_contract_external_digest")
    _need(type(contract_bytes) is bytes and 0 < len(contract_bytes) <= CONTROL_BYTES,
          "loader_readout_contract_control_size")
    _need(sha(contract_bytes) == expected_contract_sha256,
          "loader_readout_contract_digest_mismatch")
    value = parse(contract_bytes)
    originals, current = _sources()
    schema = parse(current[SCHEMA_REL])
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(value)
    except (jsonschema.ValidationError, jsonschema.SchemaError) as exc:
        raise ContractError("loader_readout_contract_schema") from exc
    _same(value["boundary"], BOUNDARY, "loader_readout_contract_boundary")
    _same(value["unresolved_prerequisites"], OPEN_PREREQUISITES,
          "loader_readout_contract_prerequisites")
    raw = _source(static.RECORD_REL) if static_record_bytes is None else static_record_bytes
    _bound(raw, STATIC_RECORD, "loader_readout_contract_static_record")
    historical = (transport.read_regular(ROOT / static.BASELINE_REL,
                      static.prior.BASELINE["size_bytes"])
                  if historical_entry_archive_bytes is None else historical_entry_archive_bytes)
    parts = static.read_artifact_members() if artifact_members is None else artifact_members
    report = static.verify_binding(record_bytes=raw,
        expected_record_sha256=STATIC_RECORD["sha256"],
        historical_entry_archive_bytes=historical, artifact_members=parts)
    record = static.parse(raw)
    expected = derive_contract(static_record=record, static_report=report)
    _same(value, expected, "loader_readout_contract_mismatch")
    _stable(originals, current)
    result = {
        "record_type": "required_gate_idempotence_loader_readout_contract_verification_v0",
        "profile": PROFILE, "status": "accepted", "contract": binding(contract_bytes),
        "contract_verified": True, "static_binding_reconstruction_verified": True,
        "qualification_checker_implemented": True,
        "evidence_role": "authored_contract_and_implementation_only",
        "static_report": binding(static.canonical(report)),
        "static_sources": copy.deepcopy(STATIC_SOURCES),
        "implementation_sources": {p: binding(b) for p, b in sorted(current.items())},
        "historical_source_file_count": report["historical_source_file_count"],
        "original_DT_NEEDED_occurrences": len(record["occurrence_bindings"]),
        "unresolved_prerequisites": copy.deepcopy(OPEN_PREREQUISITES),
        **copy.deepcopy(BOUNDARY),
    }
    return result, record, historical, originals, current


def verify_contract(*, contract_bytes, expected_contract_sha256,
                    static_record_bytes=None, historical_entry_archive_bytes=None,
                    artifact_members=None):
    try:
        return _verify(contract_bytes, expected_contract_sha256, static_record_bytes,
                       historical_entry_archive_bytes, artifact_members)[0]
    except ContractError:
        raise
    except (static.BindingError, ValueError, TypeError, KeyError, OSError,
            IndexError, OverflowError, RecursionError) as exc:
        raise ContractError("loader_readout_contract_evidence_rejected") from exc


def verify_fixtures(*, contract_bytes, expected_contract_sha256, events,
                    files_by_event, transcript, transcript_files,
                    static_record_bytes=None, historical_entry_archive_bytes=None,
                    artifact_members=None):
    """Check both independently authored fixture domains; never acquire evidence.

    A synthetic hardware transcript and original-byte readout fixtures are
    different test subjects. This method does not join them into an observation
    or accept a user-supplied prior success report.
    """
    try:
        report, record, historical, originals, current = _verify(
            contract_bytes, expected_contract_sha256, static_record_bytes,
            historical_entry_archive_bytes, artifact_members)
        recovered = static.prior.reconstruct_historical_entry(historical)
        event_report = readout.verify_event_set(events=events, files_by_event=files_by_event,
                                                static_record=record, native=recovered["native"])
        hardware_report = two_slot.verify_transcript(transcript=transcript, files=transcript_files)
        _stable(originals, current)
        complete = hardware_report["complete_fixture_sequence_verified"]
        _need(type(complete) is bool, "loader_readout_contract_fixture_completion_type")
        return {
            "record_type": "required_gate_idempotence_loader_readout_fixture_verification_v0",
            "profile": PROFILE,
            "status": "accepted_test_fixtures" if complete else "incomplete_test_fixtures",
            "evidence_origin": "authored_test_fixture",
            "complete_fixture_pair_verified": complete,
            "contract_report": binding(canonical(report)),
            "readout_fixture": event_report, "two_slot_fixture": hardware_report,
            "fixture_domains_are_one_acquired_process": False,
            **copy.deepcopy(BOUNDARY),
        }
    except ContractError:
        raise
    except (ValueError, TypeError, KeyError, OSError, IndexError, OverflowError,
            RecursionError) as exc:
        raise ContractError("loader_readout_contract_fixture_rejected") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        raw = transport.read_regular(Path(args.contract), CONTROL_BYTES)
        result = verify_contract(contract_bytes=raw, expected_contract_sha256=args.contract_sha256)
        transport.write_new(Path(args.output), canonical(result))
    except (ValueError, OSError) as exc:
        print(getattr(exc, "code", "loader_readout_contract_failed"), file=sys.stderr)
        return 2
    print("loader_readout_contract_accepted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
