#!/usr/bin/env python3
"""Reconstruct preserved original loader build-record byte relationships.

This checker verifies exact carrier preservation and declared record relations.
It parses OpenPGP envelope structure but does not verify an RSA signature or
admit a builder. The complete prior startup/static chain is reconstructed from
preserved inputs. No saved verdict, key UID or record claim closes a build gate.
No target, verifier subprocess, network request or acquisition is executed.
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
import check_required_gate_idempotence_loader_startup_contract_v0 as startup
import required_gate_idempotence_loader_build_envelope_v0 as envelope
import required_gate_idempotence_loader_buildinfo_v0 as records
import required_gate_idempotence_exec_stop_hosted_io_v0 as transport

ROOT = Path(__file__).resolve().parents[1]
SELF_REL = "tools/check_required_gate_idempotence_loader_build_record_binding_v0.py"
SCHEMA_REL = "schemas/required_gate_idempotence_loader_build_record_binding_v0.schema.json"
RECORD_REL = "docs/compute/required_gate_idempotence_loader_build_record_binding_v0/record_v0.json"
PRESERVATION_REL = "docs/compute/required_gate_idempotence_loader_build_record_binding_v0/preservation"
PROFILE = "linux_x86_64_original_loader_build_record_binding_v0"
BASE_COMMIT = "083c09bbd0ffaf8bc317930feebbb150e8dbd2ff"
CONTROL_BYTES = 1024 * 1024
STARTUP_CONTRACT = {
    "size_bytes": 131850,
    "sha256": "d4cd7d8183aedf83bb92b92a72c714bc4f5cf333a974611364bc67128c3370e1",
}
PRIOR_SOURCES = {'schemas/required_gate_idempotence_loader_startup_contract_v0.schema.json': {'size_bytes': 729419,
                                                                              'sha256': 'b10ff7a7d908b765a235811010428a71011d2502660852a4ba615341f02a46b5'},
 'schemas/required_gate_idempotence_loader_startup_invocation_v0.schema.json': {'size_bytes': 4616,
                                                                                'sha256': '9dccfa3442a37fb45fcd1ce14eb725ecc4ebd86f8ea0e6d0350b94acd15ed00c'},
 'tools/check_required_gate_idempotence_loader_startup_contract_v0.py': {'size_bytes': 15596,
                                                                         'sha256': 'f5db93d233d825805710becff62682aa1d2ed5fe0a5cdfe1d77857b5635c659e'},
 'tools/required_gate_idempotence_loader_startup_readout_v0.py': {'size_bytes': 19108,
                                                                  'sha256': 'a735cddb3f2f287d8706652887f1c49ab7ec2afcb49ffc7c454b827ab562b82a'},
 'tools/required_gate_idempotence_loader_startup_v0.py': {'size_bytes': 51925,
                                                          'sha256': '6a99478d9b1646b6d45bcdfe2ac0e12f83c88280ff65a2a33d59a99238399e52'}}
BUILDINFO_NAME = "glibc_2.41-12+deb13u4_amd64.buildinfo"
CHANGES_NAME = "glibc_2.41-12+deb13u4_amd64-buildd.changes"
CARRIERS = {
    BUILDINFO_NAME: {
        "size_bytes": 15502,
        "sha256": "5af18d1a381adb80a101b714b57c7822e5f0442f68e148df26b0dbcc4a1ca1e9",
    },
    CHANGES_NAME: {
        "size_bytes": 8964,
        "sha256": "9c98aa68df84d1ea077756df7e4e81c3f9972a513fa8da3546a0fc12fcb72e27",
    },
}
RETRIEVAL_URLS = {
    BUILDINFO_NAME: "https://buildinfos.debian.net/buildinfo-pool/g/glibc/glibc_2.41-12%2Bdeb13u4_amd64.buildinfo",
    CHANGES_NAME: "https://snapshot.debian.org/archive/debian/20260801T000000Z/dists/proposed-updates/glibc_2.41-12%2Bdeb13u4_amd64-buildd.changes",
}
NEW_SOURCES = tuple(sorted((
    SELF_REL, SCHEMA_REL,
    "tools/required_gate_idempotence_loader_build_envelope_v0.py",
    "tools/required_gate_idempotence_loader_buildinfo_v0.py",
)))
BOUNDARY = {
    **copy.deepcopy(startup.BOUNDARY),
    "signature_verified": False,
    "buildinfo_signature_verified": False,
    "changes_signature_verified": False,
    "builder_authority_verified": False,
    "authenticated_payload": False,
    "source_input_hashes_directly_attested": False,
    "other_binary_output_bytes_verified": False,
}
MISSING_BUILD_EVIDENCE = {
    "candidate_route": "original_authenticated_Debian_builder_statement",
    "accepted_build_evidence_policy": "not_selected",
    "signer_packet_claim_is_authorization": False,
    "archive_signer_policy_automatically_authorizes_builder": False,
    "missing_for_candidate_route": [
        "exact_signer_public_key_material",
        "independently_authenticated_historical_builder_architecture_and_time_authorization",
        "fresh_mathematical_signature_verification_under_the_selected_authorized_key",
        "explicit_reviewed_acceptance_policy_for_the_statement_and_archive_source_version_join",
    ],
    "direct_source_input_hashes_present_in_binary_only_statement": False,
    "independent_source_binary_rebuild_performed": False,
    "independent_rebuild_also_required_by_this_unit": False,
    "prior_source_build_obligation": copy.deepcopy(startup.OPEN_PREREQUISITES["source_build"]),
    "original_acquisition_remains_separate": True,
}


class BindingError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise BindingError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def binding(raw):
    return {"size_bytes": len(raw), "sha256": sha(raw)}


def canonical(value):
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise BindingError("loader_build_record_json_value") from exc


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _need(key not in result, "loader_build_record_duplicate_key")
        result[key] = value
    return result


def _invalid_number(_value):
    raise BindingError("loader_build_record_noninteger_number")


def parse(raw):
    _need(type(raw) is bytes and 0 < len(raw) <= CONTROL_BYTES,
          "loader_build_record_control_size")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_float=_invalid_number, parse_constant=_invalid_number)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise BindingError("loader_build_record_json") from exc


def _bound(raw, expected, code):
    _need(type(raw) is bytes and len(raw) == expected["size_bytes"], code)
    _need(sha(raw) == expected["sha256"], code)


def _same(actual, expected, code):
    _need(canonical(actual) == canonical(expected), code)


def _source(path):
    _need(path in set(NEW_SOURCES) | set(PRIOR_SOURCES) | {startup.CONTRACT_REL},
          "loader_build_record_source_path")
    return transport.read_regular(ROOT / path, CONTROL_BYTES)


def _sources():
    old = {path: _source(path) for path in PRIOR_SOURCES}
    for path, raw in old.items():
        _bound(raw, PRIOR_SOURCES[path], "loader_build_record_prior_source_changed")
    return old, {path: _source(path) for path in NEW_SOURCES}


def _stable(old, current):
    for path, raw in {**old, **current}.items():
        _need(_source(path) == raw, "loader_build_record_source_changed")


def read_carriers():
    return {name: transport.read_regular(ROOT / PRESERVATION_REL / name, wanted["size_bytes"])
            for name, wanted in CARRIERS.items()}


def _carrier_lengths(carriers):
    _need(type(carriers) is dict and set(carriers) == set(CARRIERS),
          "loader_build_record_carrier_roster")
    # Preflight both complete raw carriers before the first new input hash.
    for name, wanted in CARRIERS.items():
        _need(type(carriers[name]) is bytes and len(carriers[name]) == wanted["size_bytes"],
              "loader_build_record_carrier_size")


def derive_record(*, prior_report, envelope_facts, build_facts):
    """Author a structural binding record, without changing any trust verdict."""
    return {
        "record_type": "required_gate_idempotence_loader_build_record_binding_v0",
        "profile": PROFILE,
        "development_base": BASE_COMMIT,
        "evidence_role": "preserved_original_build_statements_and_structural_relationships_only",
        "prior_startup_prerequisite": {
            "contract_path": startup.CONTRACT_REL,
            "contract": dict(STARTUP_CONTRACT),
            "verification_report": binding(startup.canonical(prior_report)),
            "implementation_sources": copy.deepcopy(PRIOR_SOURCES),
            "fresh_startup_static_source_package_debug_reconstruction_required": True,
            "saved_report_is_acceptance_input": False,
            "historical_source_count": prior_report["historical_source_file_count"],
        },
        "preserved_carriers": [
            {"filename": name, "path": PRESERVATION_REL + "/" + name,
             "content": dict(CARRIERS[name]), "retrieval_url": RETRIEVAL_URLS[name],
             "retrieval_location_is_builder_authorization": False}
            for name in CARRIERS
        ],
        "envelope_structure": copy.deepcopy(envelope_facts),
        "declared_build_record_relationships": copy.deepcopy(build_facts),
        "missing_build_evidence": copy.deepcopy(MISSING_BUILD_EVIDENCE),
        "implementation_sources": list(NEW_SOURCES),
        "boundary": copy.deepcopy(BOUNDARY),
    }


def _verify(record_bytes, expected_record_sha256, startup_contract_bytes,
            prior_contract_bytes, static_record_bytes, historical_entry_archive_bytes,
            artifact_members, carriers):
    _need(type(expected_record_sha256) is str and
          re.fullmatch(r"[0-9a-f]{64}", expected_record_sha256) is not None,
          "loader_build_record_external_digest")
    _need(type(record_bytes) is bytes and 0 < len(record_bytes) <= CONTROL_BYTES,
          "loader_build_record_control_size")
    carriers = read_carriers() if carriers is None else carriers
    _carrier_lengths(carriers)
    _need(sha(record_bytes) == expected_record_sha256, "loader_build_record_digest_mismatch")
    for name, wanted in CARRIERS.items():
        _bound(carriers[name], wanted, "loader_build_record_carrier_binding")
    value = parse(record_bytes)
    old, current = _sources()
    schema = parse(current[SCHEMA_REL])
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(value)
    except (jsonschema.ValidationError, jsonschema.SchemaError) as exc:
        raise BindingError("loader_build_record_schema") from exc
    _same(value["boundary"], BOUNDARY, "loader_build_record_boundary")
    _same(value["missing_build_evidence"], MISSING_BUILD_EVIDENCE,
          "loader_build_record_missing_evidence")
    prior_raw = _source(startup.CONTRACT_REL) if startup_contract_bytes is None else startup_contract_bytes
    _bound(prior_raw, STARTUP_CONTRACT, "loader_build_record_startup_contract")
    static = startup.prior.static
    parts = static.read_artifact_members() if artifact_members is None else artifact_members
    prior_report, _static_record, _historical, startup_old, startup_current, prior_old, prior_current = startup._verify(
        prior_raw, STARTUP_CONTRACT["sha256"], prior_contract_bytes,
        static_record_bytes, historical_entry_archive_bytes, parts)
    inputs = static._reassemble_inputs(parts)
    extracted = {name: envelope.extract_clearsigned_payload(raw) for name, raw in carriers.items()}
    envelope_facts = {name: facts for name, (_payload, facts) in extracted.items()}
    build_facts = records.derive_buildinfo_facts(
        buildinfo_payload=extracted[BUILDINFO_NAME][0],
        changes_payload=extracted[CHANGES_NAME][0],
        buildinfo_envelope=carriers[BUILDINFO_NAME], inputs=inputs)
    expected = derive_record(prior_report=prior_report, envelope_facts=envelope_facts,
                             build_facts=build_facts)
    _same(value, expected, "loader_build_record_mismatch")
    startup.prior._stable(prior_old, prior_current)
    startup._stable(startup_old, startup_current)
    _stable(old, current)
    return {
        "record_type": "required_gate_idempotence_loader_build_record_binding_verification_v0",
        "profile": PROFILE,
        "status": "accepted_record_binding",
        "evidence_role": "preserved_original_build_statements_and_structural_relationships_only",
        "record": binding(record_bytes),
        "record_binding_verified": True,
        "original_carrier_byte_bindings_verified": True,
        "envelope_structure_checked": True,
        "declared_build_record_relationships_verified": True,
        "prior_startup_static_chain_reconstructed": True,
        "shared_binary_output_rows": 20,
        "changes_checksum_rows": 21,
        "selected_binary_package_bytes_verified": 2,
        "other_binary_output_payloads_not_retrieved": 18,
        "prior_report": binding(startup.canonical(prior_report)),
        "envelope_structure": binding(canonical(envelope_facts)),
        "declared_build_record_relationships": binding(canonical(build_facts)),
        "carriers": copy.deepcopy(CARRIERS),
        "prior_sources": copy.deepcopy(PRIOR_SOURCES),
        "implementation_sources": {path: binding(raw) for path, raw in sorted(current.items())},
        "missing_build_evidence": copy.deepcopy(MISSING_BUILD_EVIDENCE),
        **copy.deepcopy(BOUNDARY),
    }


def verify_binding(*, record_bytes, expected_record_sha256, startup_contract_bytes=None,
                   prior_contract_bytes=None, static_record_bytes=None,
                   historical_entry_archive_bytes=None, artifact_members=None, carriers=None):
    try:
        return _verify(record_bytes, expected_record_sha256, startup_contract_bytes,
                       prior_contract_bytes, static_record_bytes, historical_entry_archive_bytes,
                       artifact_members, carriers)
    except BindingError:
        raise
    except (ValueError, TypeError, KeyError, OSError, IndexError,
            OverflowError, RecursionError) as exc:
        raise BindingError("loader_build_record_evidence_rejected") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True)
    parser.add_argument("--record-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        raw = transport.read_regular(Path(args.record), CONTROL_BYTES)
        report = verify_binding(record_bytes=raw, expected_record_sha256=args.record_sha256)
        transport.write_new(Path(args.output), canonical(report))
    except (ValueError, OSError) as exc:
        print(getattr(exc, "code", "loader_build_record_rejected"), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
