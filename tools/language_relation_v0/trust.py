"""Resolve independently configured, exact-subject reference acceptance.

The trust configuration is an operator premise, not an input package field.
Hashes bind content; they do not authenticate whoever prepared that premise.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path

from .io import (InputError, canonical_bytes, relative_path, safe_read, sha256,
                 strict_json, unique_index, validate_schema)


SCOPES = {"candidate_only": "candidate_structures",
          "accepted_reference": "reference_interpretation",
          "profile_verified": "controlled_source_profile"}
METHODS = {"accepted_reference": "independent_reference_review",
           "profile_verified": "controlled_source_profile_v0"}
REQUIRED_CHECKS = {"source_binding", "subject_binding", "representation_mapping", "coverage"}


def subject_digest(document: dict, side: str) -> str:
    if side not in ("before", "after"):
        raise InputError("subject side must be before or after")
    projection = {key: value for key, value in document.items() if key != "representation_basis"}
    return sha256(canonical_bytes({"projection_version": "language_relation_subject_v0",
                                   "side": side, "input": projection}))


def acceptance_entry_digest(entry: dict) -> str:
    return sha256(canonical_bytes(entry))


def _external(path: Path, package_root: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    for component in (absolute, *absolute.parents):
        if component.is_symlink():
            raise InputError("symlink trust path is not permitted")
    resolved = absolute.resolve(strict=True)
    root = package_root.resolve(strict=True)
    if absolute.is_relative_to(root) or resolved.is_relative_to(root):
        raise InputError("trust configuration and payloads must be outside package_root")
    return absolute


@dataclass
class TrustStore:
    inventories: dict = field(default_factory=dict)
    verifications: dict = field(default_factory=dict)
    processing: dict = field(default_factory=dict)
    config_pin: str | None = None
    payload_pins: dict = field(default_factory=dict)

    @classmethod
    def load(cls, config_path: Path | None, package_root: Path) -> "TrustStore":
        store = cls()
        if config_path is None:
            return store
        path = _external(Path(config_path), package_root)
        root = path.parent.resolve(strict=True)
        config_raw = safe_read(root, path.name)
        config = strict_json(config_raw)
        store.config_pin = "trust-config.sha256:" + sha256(config_raw)
        validate_schema(config, "language_relation_evidence_v0.schema.json")
        if config["schema_version"] != "language_relation_trust_config_v0":
            raise InputError("expected a trust configuration")
        file_kinds = (
            ("inventory_files", "language_relation_acceptance_inventory_v0", "inventory_id",
             store.inventories),
            ("verification_files", "language_relation_source_verification_v0", "verification_id",
             store.verifications),
            ("processing_files", "language_relation_processing_record_v0", "evidence_id",
             store.processing),
        )
        count = sum(len(config[key]) for key, *_ in file_kinds)
        if count > 128:
            raise InputError("trust configuration file limit exceeded")
        seen_paths = set()
        total = 0
        for list_key, version, id_key, destination in file_kinds:
            for ref in config[list_key]:
                parts = relative_path(ref["path"])
                _external(root.joinpath(*parts), package_root)
                if ref["path"] in seen_paths:
                    raise InputError("duplicate trust payload path")
                seen_paths.add(ref["path"])
                raw = safe_read(root, ref["path"])
                total += len(raw)
                if total > 16 * 1024 * 1024:
                    raise InputError("trust configuration total byte limit exceeded")
                if sha256(raw) != ref["content_sha256"]:
                    raise InputError(f"trusted payload digest mismatch: {ref['path']}")
                record = strict_json(raw)
                validate_schema(record, "language_relation_evidence_v0.schema.json")
                if record["schema_version"] != version:
                    raise InputError(f"wrong trusted record type in {list_key}")
                identifier = record[id_key]
                if identifier in destination:
                    raise InputError(f"duplicate trusted {id_key}: {identifier}")
                if list_key == "inventory_files":
                    unique_index(record["entries"], "entry_id")
                elif list_key == "verification_files":
                    unique_index(record["checks"], "check_id")
                else:
                    unique_index(record["source_bindings"], "source_id")
                destination[identifier] = record
                store.payload_pins[(version, identifier)] = "sha256:" + sha256(raw)
        return store

    def acceptance(self, document: dict, side: str, input_ref: dict) -> dict:
        basis = document["representation_basis"][side]
        requested = basis["basis"]
        if requested == "candidate_only":
            return _outcome("unresolved", "candidate input has no independent acceptance")
        reference = basis["acceptance_ref"]
        inventory = self.inventories.get(reference["inventory_id"])
        if inventory is None:
            return _outcome("unresolved", "acceptance inventory is not independently configured")
        entry = next((item for item in inventory["entries"]
                      if item["entry_id"] == reference["entry_id"]), None)
        if entry is None:
            return _outcome("fail", "acceptance entry is absent from the configured inventory")
        if acceptance_entry_digest(entry) != reference["content_sha256"]:
            return _outcome("fail", "acceptance entry digest mismatch")
        expected = {
            "basis": requested, "side": side,
            "representation_id": document["representations"][side]["representation_id"],
            "subject_sha256": subject_digest(document, side),
            "verification_id": basis["verification_ref"],
            "method": METHODS[requested], "claim_scope": SCOPES[requested],
        }
        for key, value in expected.items():
            if entry[key] != value:
                return _outcome("fail", f"acceptance entry {key} mismatch")
        record = self.verifications.get(basis["verification_ref"])
        if record is None:
            return _outcome("unresolved", "source verification record is not independently configured")
        for key, value in {**expected, "input_ref": input_ref,
                           "profile_ref": document["profile_ref"]}.items():
            if record[key] != value:
                return _outcome("fail", f"source verification record {key} mismatch")
        checks = record["checks"]
        if not REQUIRED_CHECKS <= {item["kind"] for item in checks}:
            return _outcome("fail", "source verification record lacks required check kinds")
        if any(item["status"] != "completed" or item["result"] != "pass" for item in checks):
            return _outcome("fail", "source verification record contains an unperformed or unsuccessful check")
        return _outcome("pass", None, [inventory["inventory_id"], entry["entry_id"],
                                        record["verification_id"], self.config_pin,
                                        self.payload_pins[(inventory["schema_version"], inventory["inventory_id"])],
                                        self.payload_pins[(record["schema_version"], record["verification_id"])]])

    def processing_binding(self, document: dict, input_ref: dict) -> dict:
        binding = document["processing_binding"]
        if binding is None:
            return _outcome("unresolved", "no processing event was submitted")
        refs = binding["evidence_refs"]
        if not refs:
            return _outcome("unresolved", "processing event has no independently resolved evidence")
        ids = {binding["before_source_id"], binding["after_source_id"],
               *binding["context_source_ids"]}
        sources = {row["source_id"]: row for row in document["sources"]}
        fields = ("source_id", "role", "language", "revision", "content_sha256", "byte_length")
        expected = [{key: sources[source_id][key] for key in fields} for source_id in sorted(ids)]
        for evidence_id in refs:
            record = self.processing.get(evidence_id)
            if record is None:
                return _outcome("unresolved", f"processing evidence is not independently configured: {evidence_id}")
            if (record["processing_id"] != binding["processing_id"]
                    or record["input_ref"] != input_ref
                    or record["profile_ref"] != document["profile_ref"]):
                return _outcome("fail", "processing event subject/input/profile mismatch")
            actual = sorted(record["source_bindings"], key=lambda row: row["source_id"])
            if actual != expected:
                return _outcome("fail", "processing event source/context instance mismatch")
            execution = record["execution"]
            if execution["status"] != "completed" or execution["result"] != "pass":
                return _outcome("fail", "processing capture was not completed successfully")
        return _outcome("pass", None, [*refs, self.config_pin,
            *[self.payload_pins[("language_relation_processing_record_v0", key)] for key in refs]])


def _outcome(result: str, reason: str | None, evidence: list[str] | None = None) -> dict:
    return {"result": result, "reason": reason, "evidence_refs": sorted(evidence or [])}
