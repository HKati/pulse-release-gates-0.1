#!/usr/bin/env python3
"""Verify preserved rebuilder signatures and exact original byte relationships.

The existing fixed OpenSSL backend verifies public signature data only. The
original loader, probe, collector and build process are never executed. Key
mathematics does not select a rebuilder authority or close the source/build gate.
The preceding build-record/startup/static chain is freshly reconstructed.
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
import check_required_gate_idempotence_loader_build_record_binding_v0 as prior
import required_gate_idempotence_loader_rebuild_attestation_v0 as rebuild
import required_gate_idempotence_exec_stop_hosted_io_v0 as transport

ROOT = Path(__file__).resolve().parents[1]
SELF_REL = "tools/check_required_gate_idempotence_loader_rebuild_attestation_binding_v0.py"
SCHEMA_REL = "schemas/required_gate_idempotence_loader_rebuild_attestation_binding_v0.schema.json"
RECORD_REL = "docs/compute/required_gate_idempotence_loader_rebuild_attestation_binding_v0/record_v0.json"
PRESERVATION_REL = "docs/compute/required_gate_idempotence_loader_rebuild_attestation_binding_v0/preservation"
PROFILE = "linux_x86_64_original_loader_rebuild_attestation_binding_v0"
BASE_COMMIT = "83c5ca277ce94a4d2f03b073d92da66014fb6a24"
CONTROL_BYTES = 1024 * 1024
BACKEND_BYTES = 16 * 1024 * 1024
BUILD_RECORD = {
    "size_bytes": 35194,
    "sha256": "c15c85e2b875a3deff90576c0c0b1162cc0d91a511271598076b703ad71e2309",
}
PRIOR_SOURCES = {'schemas/required_gate_idempotence_loader_build_record_binding_v0.schema.json': {'sha256': '98f6beff59c9c03e7ef2c9790d6a465c6e5c6c78c40e257428ea9078fd326ce7',
                                                                                  'size_bytes': 139559},
 'tools/check_anchor_integrity_record_signatures_v0_1.py': {'sha256': 'd370a07a9587ad143f4ad121f468de4cc936c6128e3f798d7aa9e44ea6d3ac65',
                                                            'size_bytes': 27374},
 'tools/check_required_gate_idempotence_loader_build_record_binding_v0.py': {'sha256': 'c6ee57f9a2aaff50bd0e01fc44cc03c2abe48f477c651167dea1f5f4b95624be',
                                                                             'size_bytes': 15022},
 'tools/required_gate_idempotence_loader_build_envelope_v0.py': {'sha256': 'fcce2caac93cbe904b7fb9aa5e97d2575943ae6de663fb458ffa13c4dc2023ab',
                                                                 'size_bytes': 12544},
 'tools/required_gate_idempotence_loader_buildinfo_v0.py': {'sha256': 'bffa40fae52c173aed442fc3741f353c5487dd9d1b7751b86563cd6abb279fb3',
                                                            'size_bytes': 18819}}
CARRIERS = {'libc6_attestation.json': {'sha256': 'dc7cc8831246e1fac3aa29d02177f5ce85253fde5d586e1848a869c7805df2c6',
                            'size_bytes': 1104},
 'libc6_dbg_attestation.json': {'sha256': '9e7e500b1aa181474a4ceb4bde60779fe6adb95ade3812c82833b037b49ceda4',
                                'size_bytes': 1112},
 'public_keys.json': {'sha256': 'ae30bbb97ab1d57cb8bc874571cc8883f9ea44ca105ff27feb3e621c9ac85761',
                      'size_bytes': 142}}
ATTESTATION_NAMES = ("libc6_attestation.json", "libc6_dbg_attestation.json")
PUBLIC_KEYS_NAME = "public_keys.json"
RETRIEVAL_URLS = {
    "libc6_attestation.json": "https://reproduce.debian.net/amd64/api/v1/builds/269686/artifacts/710018/attestation",
    "libc6_dbg_attestation.json": "https://reproduce.debian.net/amd64/api/v1/builds/269686/artifacts/710019/attestation",
    "public_keys.json": "https://reproduce.debian.net/amd64/api/v1/meta/public-keys",
}
NEW_SOURCES = tuple(sorted((SELF_REL, SCHEMA_REL,
    "tools/required_gate_idempotence_loader_rebuild_attestation_v0.py")))
BOUNDARY = {
    **{key: copy.deepcopy(value) for key, value in prior.BOUNDARY.items()
       if key not in ("signature_verified", "authenticated_payload")},
    "trusted_rebuilder_payload_admitted": False,
    "rebuilder_historical_authority_verified": False,
    "signed_source_input_coverage_complete": False,
    "signed_build_log_binding_verified": False,
    "historical_signing_time_authenticated": False,
    "project_rebuild_policy_selected": False,
    "rebuild_process_independence_verified": False,
    "native_rebuild_performed": False,
    "other_rebuilder_signature_verified": False,
}
MISSING_BUILD_EVIDENCE = {
    "candidate_route": "separately_produced_rebuilder_statement",
    "accepted_build_evidence_policy": "not_selected",
    "current_public_key_endpoint_is_historical_role_authorization": False,
    "signature_math_is_semantic_rebuild_or_source_execution_proof": False,
    "signed_materials_cover_original_buildinfo_only": True,
    "source_archives_or_build_log_directly_bound_by_signed_statement": False,
    "missing_for_candidate_route": [
        "independently_selected_rebuilder_identity_authority_and_verification_time_policy",
        "accepted_source_input_binding_or_explicitly_reviewed_source_resolution_policy",
        "explicit_project_acceptance_of_the_rebuilder_statement_scope",
    ],
    "original_buildd_signer_route_remains_separate_and_unverified": True,
    "both_buildd_authentication_and_independent_rebuild_required": False,
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
        raise BindingError("loader_rebuild_json_value") from exc


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        _need(key not in value, "loader_rebuild_duplicate_key")
        value[key] = item
    return value


def _invalid_number(_value):
    raise BindingError("loader_rebuild_noninteger_number")


def parse(raw):
    _need(type(raw) is bytes and 0 < len(raw) <= CONTROL_BYTES,
          "loader_rebuild_control_size")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_float=_invalid_number, parse_constant=_invalid_number)
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, BindingError):
            raise
        raise BindingError("loader_rebuild_invalid_json") from exc


def _same(actual, expected, code):
    _need(canonical(actual) == canonical(expected), code)


def _bound(raw, wanted, code):
    _need(type(raw) is bytes and len(raw) == wanted["size_bytes"], code + "_size")
    _need(sha(raw) == wanted["sha256"], code + "_sha256")


def _source(path):
    _need(path in set(PRIOR_SOURCES) | set(NEW_SOURCES) | {prior.RECORD_REL},
          "loader_rebuild_source_path")
    return transport.read_regular(ROOT / path, CONTROL_BYTES)


def _sources():
    old = {path: _source(path) for path in PRIOR_SOURCES}
    for path, raw in old.items():
        _bound(raw, PRIOR_SOURCES[path], "loader_rebuild_prior_source_changed")
    return old, {path: _source(path) for path in NEW_SOURCES}


def _stable(old, current):
    for path, raw in {**old, **current}.items():
        _need(_source(path) == raw, "loader_rebuild_source_changed")


def read_carriers():
    return {name: transport.read_regular(ROOT / PRESERVATION_REL / name, wanted["size_bytes"])
            for name, wanted in CARRIERS.items()}


def _carrier_lengths(attestations, public_keys_bytes):
    _need(type(attestations) is dict and set(attestations) == set(ATTESTATION_NAMES),
          "loader_rebuild_attestation_roster")
    # All three new carrier extents precede the first new input hash or parse.
    for name in ATTESTATION_NAMES:
        _need(type(attestations[name]) is bytes and
              len(attestations[name]) == CARRIERS[name]["size_bytes"],
              "loader_rebuild_carrier_size")
    _need(type(public_keys_bytes) is bytes and
          len(public_keys_bytes) == CARRIERS[PUBLIC_KEYS_NAME]["size_bytes"],
          "loader_rebuild_public_keys_size")


def _backend_stable(observation):
    _need(type(observation) is dict and observation.get("path") == "/usr/bin/openssl"
          and observation.get("suite") == "ed25519"
          and observation.get("known_answer_self_test") == "passed",
          "loader_rebuild_backend_observation")
    raw = transport.read_regular(Path("/usr/bin/openssl"), BACKEND_BYTES)
    _need(sha(raw) == observation.get("binary_sha256"), "loader_rebuild_backend_changed")


def derive_record(*, prior_report, rebuild_facts):
    facts = copy.deepcopy(rebuild_facts)
    facts.pop("backend_observation", None)
    return {
        "record_type": "required_gate_idempotence_loader_rebuild_attestation_binding_v0",
        "profile": PROFILE,
        "development_base": BASE_COMMIT,
        "evidence_role": "selected_rebuilder_signature_math_and_exact_material_product_bindings",
        "prior_build_record_prerequisite": {
            "record_path": prior.RECORD_REL,
            "record": dict(BUILD_RECORD),
            "verification_report": binding(prior.canonical(prior_report)),
            "implementation_sources": copy.deepcopy(PRIOR_SOURCES),
            "fresh_build_record_startup_static_source_package_reconstruction_required": True,
            "saved_report_is_acceptance_input": False,
        },
        "preserved_carriers": [
            {"filename": name, "path": PRESERVATION_REL + "/" + name,
             "content": dict(CARRIERS[name]), "retrieval_url": RETRIEVAL_URLS[name],
             "retrieval_location_is_rebuilder_authorization": False}
            for name in CARRIERS
        ],
        "rebuild_attestation_facts": facts,
        "missing_build_evidence": copy.deepcopy(MISSING_BUILD_EVIDENCE),
        "runtime_backend_policy": {
            "path": "/usr/bin/openssl", "suite": "ed25519",
            "existing_verifier_source": "tools/check_anchor_integrity_record_signatures_v0_1.py",
            "positive_and_negative_known_answer_self_tests_required": True,
            "backend_binary_hash_stable_for_verification_required": True,
            "host_specific_backend_identity_is_authored_constant": False,
            "binary_provider_os_closure_attested": False,
        },
        "implementation_sources": list(NEW_SOURCES),
        "boundary": copy.deepcopy(BOUNDARY),
    }


def _verify(record_bytes, expected_record_sha256, build_record_bytes,
            startup_contract_bytes, prior_contract_bytes, static_record_bytes,
            historical_entry_archive_bytes, artifact_members, build_carriers,
            attestations, public_keys_bytes):
    _need(type(expected_record_sha256) is str and
          re.fullmatch(r"[0-9a-f]{64}", expected_record_sha256) is not None,
          "loader_rebuild_external_digest")
    _need(type(record_bytes) is bytes and 0 < len(record_bytes) <= CONTROL_BYTES,
          "loader_rebuild_control_size")
    if attestations is None or public_keys_bytes is None:
        preserved = read_carriers()
        if attestations is None:
            attestations = {name: preserved[name] for name in ATTESTATION_NAMES}
        if public_keys_bytes is None:
            public_keys_bytes = preserved[PUBLIC_KEYS_NAME]
    _carrier_lengths(attestations, public_keys_bytes)
    prior_raw = _source(prior.RECORD_REL) if build_record_bytes is None else build_record_bytes
    _need(type(prior_raw) is bytes and len(prior_raw) == BUILD_RECORD["size_bytes"],
          "loader_rebuild_build_record_size")
    _need(sha(record_bytes) == expected_record_sha256, "loader_rebuild_digest_mismatch")
    for name, raw in {**attestations, PUBLIC_KEYS_NAME: public_keys_bytes}.items():
        _bound(raw, CARRIERS[name], "loader_rebuild_original_carrier")
    _bound(prior_raw, BUILD_RECORD, "loader_rebuild_build_record")
    value = parse(record_bytes)
    old, current = _sources()
    try:
        schema = parse(current[SCHEMA_REL])
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(value)
    except (jsonschema.ValidationError, jsonschema.SchemaError) as exc:
        raise BindingError("loader_rebuild_schema") from exc
    _same(value["boundary"], BOUNDARY, "loader_rebuild_boundary")
    _same(value["missing_build_evidence"], MISSING_BUILD_EVIDENCE,
          "loader_rebuild_missing_evidence")
    prior_old, prior_current = prior._sources()
    static = prior.startup.prior.static
    parts = static.read_artifact_members() if artifact_members is None else artifact_members
    inputs = static._reassemble_inputs(parts)
    build_carriers = prior.read_carriers() if build_carriers is None else build_carriers
    prior._carrier_lengths(build_carriers)
    for name, raw in build_carriers.items():
        _bound(raw, prior.CARRIERS[name], "loader_rebuild_original_build_carrier")
    facts = rebuild.derive_attestation_facts(
        attestations=attestations, public_keys_bytes=public_keys_bytes,
        buildinfo_bytes=build_carriers[prior.BUILDINFO_NAME],
        packages={name: inputs[name] for name in rebuild.PACKAGES})
    # Run the complete prior proof after cryptographic verification, using the
    # same preserved parts and build-record carriers used by the new byte joins.
    prior_report = prior.verify_binding(
        record_bytes=prior_raw, expected_record_sha256=BUILD_RECORD["sha256"],
        startup_contract_bytes=startup_contract_bytes,
        prior_contract_bytes=prior_contract_bytes, static_record_bytes=static_record_bytes,
        historical_entry_archive_bytes=historical_entry_archive_bytes,
        artifact_members=parts, carriers=build_carriers)
    expected = derive_record(prior_report=prior_report, rebuild_facts=facts)
    _same(value, expected, "loader_rebuild_record_mismatch")
    _backend_stable(facts["backend_observation"])
    prior._stable(prior_old, prior_current)
    _stable(old, current)
    return {
        "record_type": "required_gate_idempotence_loader_rebuild_attestation_binding_verification_v0",
        "profile": PROFILE,
        "status": "accepted_rebuild_attestation_binding",
        "evidence_role": "selected_rebuilder_signature_math_and_exact_material_product_bindings",
        "record": binding(record_bytes),
        "record_binding_verified": True,
        "original_rebuild_carrier_bytes_verified": True,
        "prior_build_record_chain_reconstructed": True,
        "rebuild_signature_mathematics_verified": True,
        "signed_buildinfo_and_product_byte_bindings_verified": True,
        "verified_selected_signatures": 2,
        "unverified_other_signatures": 2,
        "selected_original_binary_packages": 2,
        "selected_original_buildinfo_carriers": 1,
        "prior_report": binding(prior.canonical(prior_report)),
        "rebuild_attestation_facts": binding(canonical(expected["rebuild_attestation_facts"])),
        "carriers": copy.deepcopy(CARRIERS),
        "prior_sources": copy.deepcopy(PRIOR_SOURCES),
        "implementation_sources": {path: binding(raw) for path, raw in sorted(current.items())},
        "backend_observation": copy.deepcopy(facts["backend_observation"]),
        "missing_build_evidence": copy.deepcopy(MISSING_BUILD_EVIDENCE),
        **copy.deepcopy(BOUNDARY),
    }


def verify_binding(*, record_bytes, expected_record_sha256, build_record_bytes=None,
                   startup_contract_bytes=None, prior_contract_bytes=None,
                   static_record_bytes=None, historical_entry_archive_bytes=None,
                   artifact_members=None, build_carriers=None, attestations=None,
                   public_keys_bytes=None):
    try:
        return _verify(record_bytes, expected_record_sha256, build_record_bytes,
                       startup_contract_bytes, prior_contract_bytes, static_record_bytes,
                       historical_entry_archive_bytes, artifact_members, build_carriers,
                       attestations, public_keys_bytes)
    except BindingError:
        raise
    except (ValueError, TypeError, KeyError, OSError, IndexError,
            OverflowError, RecursionError) as exc:
        raise BindingError("loader_rebuild_evidence_rejected") from exc


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
        print(getattr(exc, "code", "loader_rebuild_rejected"), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
