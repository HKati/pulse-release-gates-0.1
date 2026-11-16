#!/usr/bin/env python3
"""Authenticate selected distribution relationships from original evidence.

An externally selected trust policy and an explicitly selected offline GPG
verifier remain trust inputs. This record does not authenticate its own trust
root, establish present repository/key freshness or verify launcher build origin,
actual loading, host qualification, selected execution or release authority.
Every accepted reconstruction freshly verifies the original detached signature.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_launch_host_v0 as host
import required_gate_idempotence_debian_metadata_v0 as metadata
import required_gate_idempotence_distribution_signature_v0 as signature

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = "schemas/required_gate_idempotence_launcher_distribution_v0.schema.json"
SCHEMA_SHA256 = "0b9b9caf1374d929c3e25377bd0531c1f2538044e4b208c311d2d7e5474f1ea8"
PROFILE = "debian_detached_release_launcher_distribution_v0"
TRUST_PROFILE = "gpg_detached_release_trust_v0"
CONTROL_LIMIT = 1024 * 1024
RELEASE_LIMIT = 1024 * 1024
SIGNATURE_LIMIT = 64 * 1024
KEYRING_LIMIT = 1024 * 1024
INDEX_COMPRESSED_LIMIT = 16 * 1024 * 1024
INDEX_DECODED_LIMIT = 128 * 1024 * 1024
VERIFIER_LIMIT = 32 * 1024 * 1024
PACKAGE_LIMIT = 32 * 1024 * 1024
MAX_EPOCH = 4102444800
MAX_RELEASE_AGE = 31622400
BOUNDARY = {
    **host.BOUNDARY,
    "distribution_trust_freshness_verified": False,
    "current_repository_freshness_verified": False,
    "verifier_runtime_closure_verified": False,
    "launcher_build_origin_verified": False,
}
PENDING_OBLIGATIONS = (
    "upstream_source_and_launcher_build_origin",
    "same_attempt_host_and_actual_mapped_native_identity",
    "strict_namespaces_and_read_only_execution_view",
    "intended_syscall_filter_and_denied_operations",
    "descriptor_closure_and_resource_limits",
    "bounded_stdout_stderr_and_failure_preservation",
    "reviewed_selected_bootstrap_integration",
    "separate_execution_authorization",
)
IMPLEMENTATION_PATHS = (
    "tools/check_required_gate_idempotence_launcher_distribution_v0.py",
    SCHEMA_PATH,
    "tools/required_gate_idempotence_debian_metadata_v0.py",
    "tools/required_gate_idempotence_distribution_signature_v0.py",
    "tools/required_gate_idempotence_process_v0.py",
)
HOST_INPUT_NAMES = frozenset({
    "containment_prepared", "expected_containment_request_sha256",
    "selection_bytes", "expected_selection_sha256", "entry_build_payload",
    "launcher_package_bytes", "native_payload", "host_observation_bytes",
})
HASH = re.compile(r"[0-9a-f]{64}\Z")
FINGERPRINT = re.compile(r"[0-9A-F]{40}\Z")
PART = re.compile(r"[A-Za-z0-9_.+~\-]+\Z")
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+\-]{0,63}\Z")
PACKAGE_NAME = re.compile(r"[a-z0-9][a-z0-9+.\-]{0,127}\Z")
SIGNATURE_FIELDS = frozenset({
    "signing_fingerprint", "primary_fingerprint",
    "signature_created_epoch", "signature_expires_epoch",
    "pubkey_algorithm", "hash_algorithm", "signature_class", "signature_version",
})


class DistributionError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def need(condition, code):
    if not condition:
        raise DistributionError(code)


def sha(raw):
    return host.sha(raw)


def canonical(value):
    return host.canonical(value)


def binding(raw):
    need(type(raw) is bytes, "distribution_bytes_required")
    return {"sha256": sha(raw), "size_bytes": len(raw)}


def parse(raw):
    need(type(raw) is bytes and 0 < len(raw) <= CONTROL_LIMIT,
         "distribution_control_size")
    try:
        return host.parse(raw)
    except host.HostError as exc:
        raise DistributionError(exc.code) from exc


def _hash(value):
    return type(value) is str and HASH.fullmatch(value) is not None


def _fingerprint(value):
    return type(value) is str and FINGERPRINT.fullmatch(value) is not None


def _path(value, *, absolute=False):
    if type(value) is not str or not 0 < len(value) <= 500:
        return False
    if value.startswith("/") != absolute:
        return False
    parts = value[1:].split("/") if absolute else value.split("/")
    return all(part not in {"", ".", ".."} and PART.fullmatch(part) is not None
               for part in parts)


def _text(value):
    return (type(value) is str and 0 < len(value) <= 128
            and value == value.strip()
            and all(32 <= ord(char) <= 126 for char in value))


def _boundary(value):
    need(all(key in value and type(value[key]) is type(expected)
             and value[key] == expected for key, expected in BOUNDARY.items()),
         "distribution_authority_boundary_mismatch")


def _descriptor(value, maximum, code):
    need(type(value) is dict and set(value) == {"sha256", "size_bytes"}
         and _hash(value["sha256"]) and type(value["size_bytes"]) is int
         and 0 < value["size_bytes"] <= maximum, code)


def _bytes(raw, expected, maximum, code):
    need(type(raw) is bytes and 0 < len(raw) <= maximum
         and binding(raw) == expected, code)


def _schema(value, definition):
    safe = host.containment.bootstrap.runtime.observation.safe
    try:
        raw = safe._read_regular(ROOT / SCHEMA_PATH)
        need(sha(raw) == SCHEMA_SHA256, "distribution_schema_source_mismatch")
        safe._validate_schema(value, parse(raw),
            "distribution_" + definition + "_schema_invalid", definition)
    except safe.ContractError as exc:
        raise DistributionError(exc.code) from exc
    except OSError as exc:
        raise DistributionError("distribution_schema_source_unavailable") from exc


def validate_selection(raw, expected_sha256):
    need(_hash(expected_sha256) and type(raw) is bytes
         and 0 < len(raw) <= CONTROL_LIMIT
         and sha(raw) == expected_sha256, "distribution_selection_digest_mismatch")
    value = parse(raw)
    _schema(value, "selection")
    _boundary(value)
    for name, maximum in (
        ("launch_host_plan", host.CONTROL_LIMIT), ("trust_policy", CONTROL_LIMIT),
        ("release", RELEASE_LIMIT), ("release_signature", SIGNATURE_LIMIT),
    ):
        _descriptor(value[name], maximum, "distribution_selection_binding_invalid")
    repository = value["repository"]
    need(all(_text(repository[name]) for name in ("origin", "label", "suite", "codename", "version"))
         and _path(repository["component"])
         and type(repository["architecture"]) is str
         and TOKEN.fullmatch(repository["architecture"]) is not None,
         "distribution_repository_identity_invalid")
    index = value["index"]
    prefix = repository["component"] + "/binary-" + repository["architecture"] + "/Packages"
    for name, suffix, maximum in (
        ("compressed", ".xz", INDEX_COMPRESSED_LIMIT),
        ("decoded", "", INDEX_DECODED_LIMIT),
    ):
        row = index[name]
        need(_path(row["path"]) and row["path"] == prefix + suffix,
             "distribution_index_path_invalid")
        _descriptor({key: row[key] for key in ("sha256", "size_bytes")},
                    maximum, "distribution_index_binding_invalid")
    package = value["package"]
    need(type(package["name"]) is str and PACKAGE_NAME.fullmatch(package["name"]) is not None
         and _text(package["version"]) and package["architecture"] == repository["architecture"]
         and _path(package["filename"]) and package["filename"].startswith("pool/")
         and package["filename"].endswith(".deb"), "distribution_package_identity_invalid")
    _descriptor({key: package[key] for key in ("sha256", "size_bytes")},
                PACKAGE_LIMIT, "distribution_package_binding_invalid")
    return value


def _signer_pairs(rows):
    return [(row["signing_fingerprint"], row["primary_fingerprint"]) for row in rows]


def validate_trust_policy(raw, expected_sha256):
    need(_hash(expected_sha256) and type(raw) is bytes
         and 0 < len(raw) <= CONTROL_LIMIT
         and sha(raw) == expected_sha256, "distribution_trust_policy_digest_mismatch")
    value = parse(raw)
    _schema(value, "trust_policy")
    _descriptor(value["keyring"], KEYRING_LIMIT, "distribution_keyring_binding_invalid")
    verifier = value["verifier"]
    need(verifier["kind"] == "gpg" and _path(verifier["path"], absolute=True),
         "distribution_verifier_identity_invalid")
    _descriptor({key: verifier[key] for key in ("sha256", "size_bytes")},
                VERIFIER_LIMIT, "distribution_verifier_binding_invalid")
    rows = value["required_signers"]
    need(type(rows) is list and 1 <= len(rows) <= 8
         and all(type(row) is dict
                 and set(row) == {"signing_fingerprint", "primary_fingerprint"}
                 and all(_fingerprint(part) for part in row.values()) for row in rows),
         "distribution_required_signers_invalid")
    pairs = _signer_pairs(rows)
    need(len(pairs) == len(set(pairs)), "distribution_required_signers_duplicate")
    need(type(value["evaluation_time"]) is int and 0 < value["evaluation_time"] <= MAX_EPOCH
         and type(value["max_release_age_seconds"]) is int
         and 1 <= value["max_release_age_seconds"] <= MAX_RELEASE_AGE
         and type(value["require_valid_until"]) is bool,
         "distribution_time_policy_invalid")
    return value


def _host_inputs(value):
    need(type(value) is dict and set(value) == HOST_INPUT_NAMES,
         "distribution_launch_host_inputs_required")
    frozen = dict(value)
    for name in ("entry_build_payload", "native_payload"):
        need(type(frozen[name]) is dict, "distribution_launch_host_inputs_invalid")
        frozen[name] = dict(frozen[name])
    return frozen


def _sources():
    safe = host.containment.bootstrap.runtime.observation.safe
    result = []
    try:
        for name in IMPLEMENTATION_PATHS:
            raw = safe._read_regular(ROOT / name)
            need(0 < len(raw) <= CONTROL_LIMIT, "distribution_implementation_source_size")
            result.append({"path": name, **binding(raw)})
    except (OSError, safe.ContractError) as exc:
        raise DistributionError("distribution_implementation_source_unavailable") from exc
    return result


def _signature_result(value, policy, release_date):
    need(type(value) is dict and set(value) == {"verified_signatures", "backend"}
         and canonical(value["backend"]) == canonical(policy["verifier"]),
         "distribution_signature_backend_mismatch")
    rows = value["verified_signatures"]
    need(type(rows) is list and 1 <= len(rows) <= 8
         and all(type(row) is dict and set(row) == SIGNATURE_FIELDS for row in rows),
         "distribution_signature_result_invalid")
    for row in rows:
        need(_fingerprint(row["signing_fingerprint"])
             and _fingerprint(row["primary_fingerprint"]),
             "distribution_signature_identity_invalid")
        need(all(type(row[key]) is int for key in (
                 "signature_created_epoch", "signature_expires_epoch",
                 "pubkey_algorithm", "hash_algorithm", "signature_version"))
             and row["signature_version"] == 4 and row["signature_class"] == "00"
             and row["pubkey_algorithm"] in {1, 19, 22}
             and row["hash_algorithm"] in {8, 9, 10},
             "distribution_signature_profile_invalid")
        created, expires = row["signature_created_epoch"], row["signature_expires_epoch"]
        need(0 < created <= policy["evaluation_time"] and created >= release_date,
             "distribution_signature_release_time_mismatch")
        need(type(expires) is int and 0 <= expires <= MAX_EPOCH
             and (expires == 0 or created < expires and policy["evaluation_time"] < expires),
             "distribution_signature_expired")
    pairs = _signer_pairs(rows)
    need(len(pairs) == len(set(pairs))
         and set(pairs) == set(_signer_pairs(policy["required_signers"])),
         "distribution_signature_signer_roster_mismatch")
    return {"backend": dict(value["backend"]),
            "verified_signatures": sorted((dict(row) for row in rows),
                key=lambda row: (row["signing_fingerprint"], row["primary_fingerprint"]))}


def derive_record(*, launch_host_inputs, launch_host_plan_bytes,
                  expected_launch_host_plan_sha256, selection_bytes,
                  expected_selection_sha256, trust_policy_bytes,
                  expected_trust_policy_sha256, release_bytes,
                  release_signature_bytes, packages_xz_bytes, keyring_bytes,
                  verifier_path, signature_evidence_sink=None):
    """Reconstruct all selected relationships and freshly verify the signature."""
    selection = validate_selection(selection_bytes, expected_selection_sha256)
    policy = validate_trust_policy(trust_policy_bytes, expected_trust_policy_sha256)
    _bytes(trust_policy_bytes, selection["trust_policy"], CONTROL_LIMIT,
           "distribution_trust_policy_binding_mismatch")
    need(selection["trust_policy"]["sha256"] == expected_trust_policy_sha256,
         "distribution_trust_policy_digest_mismatch")
    _bytes(launch_host_plan_bytes, selection["launch_host_plan"], host.CONTROL_LIMIT,
           "distribution_launch_host_plan_binding_mismatch")
    need(_hash(expected_launch_host_plan_sha256)
         and expected_launch_host_plan_sha256 == selection["launch_host_plan"]["sha256"],
         "distribution_launch_host_plan_digest_mismatch")
    _bytes(release_bytes, selection["release"], RELEASE_LIMIT, "distribution_release_binding_mismatch")
    _bytes(release_signature_bytes, selection["release_signature"], SIGNATURE_LIMIT,
           "distribution_release_signature_binding_mismatch")
    _bytes(packages_xz_bytes,
           {key: selection["index"]["compressed"][key] for key in ("sha256", "size_bytes")},
           INDEX_COMPRESSED_LIMIT, "distribution_index_compressed_binding_mismatch")
    _bytes(keyring_bytes, policy["keyring"], KEYRING_LIMIT, "distribution_keyring_binding_mismatch")
    try:
        verifier = Path(verifier_path)
    except (TypeError, ValueError) as exc:
        raise DistributionError("distribution_verifier_path_invalid") from exc
    need(str(verifier) == policy["verifier"]["path"]
         and _path(str(verifier), absolute=True), "distribution_verifier_path_mismatch")
    need(signature_evidence_sink is None or callable(signature_evidence_sink),
         "distribution_signature_sink_invalid")
    sources = _sources()
    originals = _host_inputs(launch_host_inputs)
    try:
        old_report = host.verify_plan(plan_bytes=launch_host_plan_bytes,
            expected_plan_sha256=expected_launch_host_plan_sha256, **originals)
        old_selection = host.validate_selection(originals["selection_bytes"],
                                                originals["expected_selection_sha256"])
    except (host.HostError, ValueError, TypeError, KeyError, OSError) as exc:
        raise DistributionError(getattr(exc, "code", "distribution_launch_host_readmission_failed")) from exc
    need(old_report["record_status"] == selection["record_status"],
         "distribution_record_status_mismatch")
    origin = old_selection["launcher_origin"]
    package = selection["package"]
    need(all(package[key] == origin[key] for key in ("name", "version", "architecture"))
         and {key: package[key] for key in ("sha256", "size_bytes")} == origin["package"],
         "distribution_package_launch_host_mismatch")
    package_bytes = originals["launcher_package_bytes"]
    _bytes(package_bytes, origin["package"], PACKAGE_LIMIT,
           "distribution_package_original_binding_mismatch")
    launcher_bytes = originals["native_payload"][old_selection["launcher_path"]]
    try:
        chain = metadata.inspect_metadata(
            release_bytes=release_bytes, packages_xz_bytes=packages_xz_bytes,
            repository=selection["repository"], index=selection["index"], package=package,
            evaluation_time=policy["evaluation_time"],
            max_release_age_seconds=policy["max_release_age_seconds"],
            require_valid_until=policy["require_valid_until"])
    except metadata.MetadataError as exc:
        raise DistributionError(exc.code) from exc
    _schema(chain, "metadata")
    need(chain["release"]["identity"] == selection["repository"]
         and chain["index"]["compressed"] == selection["index"]["compressed"]
         and chain["index"]["decoded"] == selection["index"]["decoded"]
         and chain["package"] == package, "distribution_metadata_chain_mismatch")
    release_date = chain["release"]["date_epoch"]
    need(type(release_date) is int and 0 < release_date <= policy["evaluation_time"]
         and policy["evaluation_time"] - release_date <= policy["max_release_age_seconds"],
         "distribution_release_time_mismatch")
    valid_until = chain["release"]["valid_until_epoch"]
    need((valid_until is None and not policy["require_valid_until"])
         or type(valid_until) is int and release_date <= valid_until
         and policy["evaluation_time"] <= valid_until,
         "distribution_release_validity_mismatch")
    try:
        verified = signature.verify_detached(
            release_bytes=release_bytes, signature_bytes=release_signature_bytes,
            keyring_bytes=keyring_bytes, expected_keyring_sha256=policy["keyring"]["sha256"],
            verifier_path=verifier, expected_verifier=policy["verifier"],
            required_signers=policy["required_signers"], evaluation_time=policy["evaluation_time"],
            evidence_sink=signature_evidence_sink)
    except signature.SignatureError as exc:
        raise DistributionError(exc.code) from exc
    verified = _signature_result(verified, policy, release_date)
    need(_sources() == sources, "distribution_implementation_source_changed")
    old_report_bytes = host.canonical(old_report)
    record = {
        "record_type": "required_gate_idempotence_launcher_distribution_record_v0",
        "profile": PROFILE, "record_status": selection["record_status"],
        "bindings": {
            "distribution_selection": binding(selection_bytes),
            "trust_policy": binding(trust_policy_bytes),
            "launch_host_plan": binding(launch_host_plan_bytes),
            "launch_host_verification": binding(old_report_bytes),
            "release": binding(release_bytes),
            "release_signature": binding(release_signature_bytes),
            "packages_compressed": binding(packages_xz_bytes),
            "packages_decoded": {key: chain["index"]["decoded"][key] for key in ("sha256", "size_bytes")},
            "keyring": binding(keyring_bytes),
            "launcher_package": binding(package_bytes),
            "launcher": binding(launcher_bytes),
        },
        "verification_policy": {
            "required_signers": sorted((dict(row) for row in policy["required_signers"]),
                key=lambda row: (row["signing_fingerprint"], row["primary_fingerprint"])),
            "evaluation_time": policy["evaluation_time"],
            "max_release_age_seconds": policy["max_release_age_seconds"],
            "require_valid_until": policy["require_valid_until"],
        },
        "signature": verified, "metadata": chain,
        "implementation_sources": sources,
        "pending_obligations": list(PENDING_OBLIGATIONS), **BOUNDARY,
    }
    _schema(record, "record")
    result = canonical(record)
    parse(result)
    return result


def verify_record(record_bytes, expected_record_sha256, **original_inputs):
    """Compare a complete fresh reconstruction with the externally pinned record."""
    need(_hash(expected_record_sha256) and type(record_bytes) is bytes
         and 0 < len(record_bytes) <= CONTROL_LIMIT
         and sha(record_bytes) == expected_record_sha256,
         "distribution_record_digest_mismatch")
    record = parse(record_bytes)
    need(canonical(record) == record_bytes, "distribution_record_noncanonical")
    _schema(record, "record")
    _boundary(record)
    expected = derive_record(**original_inputs)
    need(record_bytes == expected, "distribution_record_reconstruction_mismatch")
    report = {
        "record_type": "required_gate_idempotence_launcher_distribution_verification_v0",
        "profile": PROFILE, "status": "accepted", "record_status": record["record_status"],
        "record_sha256": expected_record_sha256,
        "selection_sha256": original_inputs["expected_selection_sha256"],
        "trust_policy_sha256": original_inputs["expected_trust_policy_sha256"],
        "launch_host_plan_sha256": original_inputs["expected_launch_host_plan_sha256"],
        "distribution_signature_verified": True,
        "release_index_binding_verified": True,
        "index_package_binding_verified": True,
        "package_launcher_binding_verified": True,
        "launcher_distribution_authenticated": True,
        "verification_policy": record["verification_policy"],
        "signature": record["signature"],
        "pending_obligations": list(PENDING_OBLIGATIONS), **BOUNDARY,
    }
    _schema(report, "verification")
    return report


if __name__ == "__main__":
    sys.stdout.buffer.write(canonical({
        "record_type": "required_gate_idempotence_launcher_distribution_verification_v0",
        "profile": PROFILE, "status": "rejected",
        "error_code": "distribution_original_inputs_required", **BOUNDARY,
    }))
    raise SystemExit(1)
