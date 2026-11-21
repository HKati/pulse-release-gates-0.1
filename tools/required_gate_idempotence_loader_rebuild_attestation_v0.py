"""Verify the selected original-package rebuild Link signatures and byte joins.

This is a deliberately narrow in-toto Metablock/Link profile.  It verifies two
selected Ed25519 signatures with an existing fixed OpenSSL backend and joins
their signed material/product digests to complete supplied original bytes.
It does not authenticate a rebuilder identity, historical key role or signing
time, observe a rebuild, or select a project build-evidence acceptance policy.
"""
from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import json
import re
import subprocess

import check_anchor_integrity_record_signatures_v0_1 as crypto


PROFILE = "selected_original_loader_rebuild_attestations_v0"
SELECTED_KEYID = "2980aa6249ad89ce0ef0f0f5e6d0896214301b2818aad33443444cf460df6ed6"
OTHER_KEYID = "c70f1852977e382b45eea36783e59dd5f4413e39bdbed773ad0d83aa4d8212b9"
SELECTED_PUBLIC_HEX = "13ba298a31f08e49f88a736013fd3d4d290867f72dfd2b3e52ba8d30e5451718"
LEGACY_SPKI_PREFIX = bytes.fromhex("302c300706032b65700500032100")
BUILDINFO_NAME = "glibc_2.41-12+deb13u4_amd64.buildinfo"
BUILDINFO_BINDING = {
    "size_bytes": 15502,
    "sha256": "5af18d1a381adb80a101b714b57c7822e5f0442f68e148df26b0dbcc4a1ca1e9",
}
PACKAGES = {
    "libc6_2.41-12+deb13u4_amd64.deb": {
        "size_bytes": 2846580,
        "sha256": "967aa62605721081c3eb2a17650611a792aa802d76a6511d1840242623d204c9",
    },
    "libc6-dbg_2.41-12+deb13u4_amd64.deb": {
        "size_bytes": 7373052,
        "sha256": "0123a767a462c59d75e1bd56c4a0f7192c389f600e4743e807d3d33c679dbcf7",
    },
}
ATTESTATIONS = {
    "libc6_attestation.json": "libc6_2.41-12+deb13u4_amd64.deb",
    "libc6_dbg_attestation.json": "libc6-dbg_2.41-12+deb13u4_amd64.deb",
}
POLICY = {
    "attestation_bytes": 16384,
    "public_keys_bytes": 8192,
    "total_input_bytes": 16 * 1024 * 1024,
    "json_depth": 8,
    "json_nodes": 256,
    "canonical_bytes": 8192,
    "canonical_profile": "sorted_compact_ascii_without_quote_backslash_or_control_strings",
    "canonical_value_types": ["object", "array", "string", "null"],
    "metablock_type": "in_toto_link",
    "signature_algorithm": "ed25519",
    "signatures_per_attestation": 2,
    "selected_verified_signatures_per_attestation": 1,
    "signature_quorum_is_established": False,
    "selected_keyid": SELECTED_KEYID,
    "unverified_keyid": OTHER_KEYID,
    "public_key_response_roster": "one_current_key",
    "source_spki_profile": "ed25519_legacy_explicit_NULL_parameters",
    "backend_spki_profile": "ed25519_absent_parameters",
    "verifier_implementation": "tools/check_anchor_integrity_record_signatures_v0_1.py",
    "verifier_executable": "/usr/bin/openssl",
    "shell_execution": False,
    "network_access": False,
    "arbitrary_caller_selected_key": False,
    "project_rebuild_policy_selected": False,
}
BOUNDARY = {
    "other_signature_verified": False,
    "rebuilder_identity_authenticated": False,
    "historical_rebuilder_key_authority_authenticated": False,
    "historical_signing_time_authenticated": False,
    "project_rebuild_policy_selected": False,
    "source_input_hashes_directly_attested": False,
    "rebuild_process_independence_verified": False,
    "source_binary_equivalence_verified": False,
    "authenticated_build_provenance": False,
    "source_build_gate_satisfied": False,
    "original_buildinfo_signature_verified": False,
    "original_changes_signature_verified": False,
    "native_rebuild_performed": False,
    "consumer_resolution_observed": False,
    "original_acquisition_ready": False,
    "original_acquisition_authorized": False,
    "b2_complete": False,
    "metric_pass": None,
    "authority_effect": "none",
}
LIMITATIONS = {
    "signed_command_is_empty": True,
    "signed_environment_is_null": True,
    "signed_byproducts_are_empty": True,
    "signed_source_archive_digests_present": False,
    "signed_rebuild_log_digest_present": False,
    "signed_builder_identity_present": False,
    "signed_timestamp_present": False,
    "retrieval_url_authenticates_historical_signer_role": False,
    "matching_product_digest_is_direct_observation_of_rebuild_execution": False,
    "other_signature_verification_performed": False,
}


class RebuildAttestationError(ValueError):
    """Stable rejection code without reflected input or backend diagnostics."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise RebuildAttestationError(code)


def _keys(value, expected, code):
    _need(type(value) is dict and set(value) == set(expected), code)


def _binding(raw):
    return {"size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _digests(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(),
            "sha512": hashlib.sha512(raw).hexdigest()}


def _preflight(attestations, public_keys_bytes, buildinfo_bytes, packages):
    # Inspect every external input extent before any input hash, parse or
    # verifier construction. In particular, a late oversized package cannot
    # cause an earlier signature to be processed first.
    _keys(attestations, ATTESTATIONS, "rebuild_attestation_inventory")
    _keys(packages, PACKAGES, "rebuild_package_inventory")
    total = 0
    for raw in attestations.values():
        _need(type(raw) is bytes and 0 < len(raw) <= POLICY["attestation_bytes"],
              "rebuild_attestation_size")
        total += len(raw)
    _need(type(public_keys_bytes) is bytes
          and 0 < len(public_keys_bytes) <= POLICY["public_keys_bytes"],
          "rebuild_public_keys_size")
    _need(type(buildinfo_bytes) is bytes
          and len(buildinfo_bytes) == BUILDINFO_BINDING["size_bytes"],
          "rebuild_buildinfo_size")
    total += len(public_keys_bytes) + len(buildinfo_bytes)
    for name, expected in PACKAGES.items():
        raw = packages[name]
        _need(type(raw) is bytes and len(raw) == expected["size_bytes"],
              "rebuild_package_size")
        total += len(raw)
    _need(total <= POLICY["total_input_bytes"], "rebuild_input_total")


def _pairs(pairs):
    result = {}
    for name, value in pairs:
        _need(name not in result, "rebuild_json_duplicate_key")
        result[name] = value
    return result


def _number(_value):
    # The selected complete profiles contain no JSON numeric values.
    raise RebuildAttestationError("rebuild_json_number")


def _load(raw):
    try:
        value = json.loads(raw.decode("ascii"), object_pairs_hook=_pairs,
                           parse_int=_number, parse_float=_number, parse_constant=_number)
    except RebuildAttestationError:
        raise
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise RebuildAttestationError("rebuild_json_invalid") from exc
    pending = [(value, 0)]
    nodes = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        _need(depth <= POLICY["json_depth"] and nodes <= POLICY["json_nodes"],
              "rebuild_json_complexity")
        if type(item) is dict:
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
    return value


def _canonical(value):
    """Canonicalize only the selected simple in-toto signed/key grammar.

    These strings require no escaping, so sorted compact ASCII JSON is exactly
    their in-toto canonical form. This is not a general JSON/JCS canonicalizer.
    """
    def validate(item, depth=0):
        _need(depth <= POLICY["json_depth"], "rebuild_canonical_depth")
        if item is None:
            return
        if type(item) is str:
            _need(all(32 <= ord(char) <= 126 and char not in '\\"' for char in item),
                  "rebuild_canonical_string")
        elif type(item) is dict:
            for key, child in item.items():
                _need(type(key) is str, "rebuild_canonical_key")
                validate(key, depth + 1)
                validate(child, depth + 1)
        elif type(item) is list:
            for child in item:
                validate(child, depth + 1)
        else:
            raise RebuildAttestationError("rebuild_canonical_type")
    validate(value)
    raw = json.dumps(value, sort_keys=True, ensure_ascii=True,
                     separators=(",", ":"), allow_nan=False).encode("ascii")
    _need(len(raw) <= POLICY["canonical_bytes"], "rebuild_canonical_size")
    return raw


def _public_key(raw):
    value = _load(raw)
    _keys(value, ("current",), "rebuild_public_key_fields")
    _need(type(value["current"]) is list and len(value["current"]) == 1
          and type(value["current"][0]) is str, "rebuild_public_key_roster")
    pem = value["current"][0]
    match = re.fullmatch(r"-----BEGIN PUBLIC KEY-----\r\n([A-Za-z0-9+/]{62}==)\r\n"
                         r"-----END PUBLIC KEY-----\r\n", pem)
    _need(match is not None, "rebuild_public_key_pem")
    try:
        der = base64.b64decode(match.group(1), validate=True)
    except (ValueError, binascii.Error) as exc:
        raise RebuildAttestationError("rebuild_public_key_pem") from exc
    _need(base64.b64encode(der).decode("ascii") == match.group(1), "rebuild_public_key_pem")
    _need(len(der) == len(LEGACY_SPKI_PREFIX) + 32
          and der.startswith(LEGACY_SPKI_PREFIX), "rebuild_public_key_der")
    key = der[len(LEGACY_SPKI_PREFIX):]
    _need(key.hex() == SELECTED_PUBLIC_HEX, "rebuild_public_key_selected")
    key_object = {"keyid_hash_algorithms": ["sha256", "sha512"],
                  "keytype": "ed25519", "keyval": {"public": key.hex()}, "scheme": "ed25519"}
    canonical_key = _canonical(key_object)
    _need(hashlib.sha256(canonical_key).hexdigest() == SELECTED_KEYID, "rebuild_public_key_id")
    return key, {
        "response": _binding(raw), "pem": _binding(pem.encode("ascii")),
        "original_spki_der": _binding(der),
        "original_spki_explicit_null_parameters": True,
        "raw_public_key_hex": key.hex(), "keyid": SELECTED_KEYID,
        "canonical_key_object": key_object, "canonical_key_bytes": _binding(canonical_key),
        "backend_spki_parameters_absent": True,
        "key_selected_by_exact_bytes": True,
        "historical_role_authenticated": False,
    }


def _hash_object(value):
    _keys(value, ("sha256", "sha512"), "rebuild_digest_fields")
    for algorithm, length in (("sha256", 64), ("sha512", 128)):
        _need(type(value[algorithm]) is str
              and re.fullmatch("[0-9a-f]{" + str(length) + "}", value[algorithm]) is not None,
              "rebuild_digest_value")


def _attestation(name, raw, package, material_digests, product_digests):
    value = _load(raw)
    _keys(value, ("signatures", "signed"), "rebuild_attestation_fields")
    signatures = value["signatures"]
    _need(type(signatures) is list and len(signatures) == 2, "rebuild_signature_roster")
    by_key = {}
    for signature in signatures:
        _keys(signature, ("keyid", "sig"), "rebuild_signature_fields")
        keyid, encoded = signature["keyid"], signature["sig"]
        _need(type(keyid) is str and keyid in (SELECTED_KEYID, OTHER_KEYID)
              and keyid not in by_key, "rebuild_signature_keyid")
        _need(type(encoded) is str and re.fullmatch(r"[0-9a-f]{128}", encoded) is not None,
              "rebuild_signature_value")
        by_key[keyid] = bytes.fromhex(encoded)
    _need(set(by_key) == {SELECTED_KEYID, OTHER_KEYID}, "rebuild_signature_roster")
    signed = value["signed"]
    _keys(signed, ("_type", "name", "materials", "products", "environment", "byproducts", "command"),
          "rebuild_signed_fields")
    _need(signed["_type"] == "link", "rebuild_link_type")
    _need(signed["name"] == "rebuild " + package, "rebuild_link_name")
    _keys(signed["materials"], (BUILDINFO_NAME,), "rebuild_material_inventory")
    _keys(signed["products"], (package,), "rebuild_product_inventory")
    _need(signed["environment"] is None and type(signed["command"]) is list
          and signed["command"] == [] and type(signed["byproducts"]) is dict
          and signed["byproducts"] == {}, "rebuild_statement_scope")
    material = signed["materials"][BUILDINFO_NAME]
    product = signed["products"][package]
    _hash_object(material)
    _hash_object(product)
    _need(material == material_digests, "rebuild_material_digest")
    _need(product == product_digests, "rebuild_product_digest")
    message = _canonical(signed)
    facts = {
        "filename": name, "carrier": _binding(raw), "signed_canonical_bytes": _binding(message),
        "signed_link": copy.deepcopy(signed),
        "listed_signature_count": 2, "selected_verified_signature_count": 1,
        "signatures": [{"keyid": keyid, "signature": _binding(by_key[keyid]),
                        "selected": keyid == SELECTED_KEYID,
                        "signature_verified": keyid == SELECTED_KEYID}
                       for keyid in sorted(by_key)],
        "selected_signature_verified": True, "other_signature_verified": False,
        "signature_quorum_established": False,
        "complete_material_bytes_joined": True, "complete_product_bytes_joined": True,
        "material_filename": BUILDINFO_NAME, "product_filename": package,
    }
    return message, by_key[SELECTED_KEYID], facts


def derive_attestation_facts(*, attestations, public_keys_bytes, buildinfo_bytes, packages):
    """Freshly verify the selected signatures and complete original-byte joins.

    JSON whitespace/key ordering may vary. The caller's outer preservation
    binding selects exact original carrier bytes. The unselected signature is
    structurally accounted for but is never cryptographically verified here.

    ``backend_observation`` is runtime-specific. It belongs in a fresh report,
    not a host-independent authored constant record or historical trust root.
    """
    try:
        _preflight(attestations, public_keys_bytes, buildinfo_bytes, packages)
        material = _digests(buildinfo_bytes)
        _need(material["sha256"] == BUILDINFO_BINDING["sha256"], "rebuild_buildinfo_sha256")
        products = {}
        for name, expected in PACKAGES.items():
            products[name] = _digests(packages[name])
            _need(products[name]["sha256"] == expected["sha256"], "rebuild_package_sha256")
        key, key_facts = _public_key(public_keys_bytes)
        selected = [_attestation(name, attestations[name], package, material, products[package])
                    for name, package in sorted(ATTESTATIONS.items())]
        # All bounded inputs, closed fields and byte joins are complete before
        # constructing the fixed backend (which also executes its self-tests).
        try:
            verifier = crypto.OpenSSLVerifier()
            for message, signature, _facts in selected:
                _need(verifier.verify(key, signature, message), "selected_signature_invalid")
        except RebuildAttestationError:
            raise
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            raise RebuildAttestationError("rebuild_crypto_backend_failure") from exc
        return {
            "record_type": "required_gate_idempotence_loader_rebuild_attestation_facts_v0",
            "profile": PROFILE,
            "selected_signature_verified": True,
            "verified_attestation_count": 2,
            "selected_material_product_hashes_verified": True,
            "public_key": key_facts,
            "attestations": [facts for _message, _signature, facts in selected],
            "input_bindings": {
                "buildinfo": {"filename": BUILDINFO_NAME, "size_bytes": len(buildinfo_bytes), **material},
                "packages": [{"filename": name, "size_bytes": len(packages[name]), **products[name]}
                             for name in sorted(packages)],
            },
            "limitations": copy.deepcopy(LIMITATIONS),
            "boundary": copy.deepcopy(BOUNDARY),
            "backend_observation": copy.deepcopy(verifier.identity),
        }
    except RebuildAttestationError:
        raise
    except (ValueError, TypeError, KeyError, IndexError, UnicodeError, OverflowError,
            RecursionError) as exc:
        raise RebuildAttestationError("rebuild_attestation_invalid") from exc
