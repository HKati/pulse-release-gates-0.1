#!/usr/bin/env python3
"""Reconstruct one original-loader binary/debug/source binding without execution.

The authored record is compared with facts freshly derived from complete pinned
artifacts and the unchanged historical entry checker. Acceptance qualifies a
selected static recipe. It does not authenticate a build process, reproduce the
binary from source, qualify a live private-ABI read, or authorize acquisition.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jsonschema
import check_required_gate_idempotence_loader_resolution_plan_v0 as prior
import required_gate_idempotence_loader_binary_v0 as binary
import required_gate_idempotence_loader_source_v0 as source
import required_gate_idempotence_exec_stop_hosted_io_v0 as transport


ROOT = Path(__file__).resolve().parents[1]
SELF_REL = "tools/check_required_gate_idempotence_loader_binary_binding_v0.py"
SCHEMA_REL = "schemas/required_gate_idempotence_loader_binary_binding_v0.schema.json"
RECORD_REL = "docs/compute/required_gate_idempotence_loader_binary_binding_v0/record_v0.json"
CARRIER_REL = "preservation/required_gate_idempotence_loader_binary_binding_v0"
INPUTS_REL = CARRIER_REL + "/inputs_v0.json"
BASELINE_REL = prior.BASELINE_REL
PROFILE = "linux_x86_64_original_loader_binary_binding_v0"
CONTROL_BYTES = 1024 * 1024
PART_BYTES = 8000000
INPUTS = {"size_bytes": 4479,
          "sha256": "593ed408bed5a282258288c465584379ae5158ae890f8f3bd6a7bc7eb80f9fd7"}
PRIOR_SOURCES = {
    prior.PLAN_REL: {"size_bytes": 33641,
        "sha256": "ff33f96d0095f949763125d67da1159112b067b86c2fe3b5f1302f55cb193d7d"},
    prior.SCHEMA_REL: {"size_bytes": 27856,
        "sha256": "f3d7dfa891d69528632f4145ef1677782e238ce73ff66ce301b56159762b5b01"},
    prior.SELF_REL: {"size_bytes": 44623,
        "sha256": "a26b59f804b8000219b85b99dda08869099b3ca82a9093923ac01bf0b00d19b7"},
}
NEW_SOURCES = (
    SELF_REL, SCHEMA_REL,
    "tools/required_gate_idempotence_loader_binary_v0.py",
    "tools/required_gate_idempotence_loader_source_v0.py",
)
SOURCE_LIMITS = {**prior.SOURCE_LIMITS, BASELINE_REL: prior.BASELINE["size_bytes"]}
BOUNDARY = {
    "archive_metadata_relationships_verified": True,
    "original_loader_package_membership_verified": True,
    "matching_debug_package_membership_verified": True,
    "selected_source_patch_relationships_verified": True,
    "selected_instruction_recipe_verified": True,
    "selected_private_layout_bindings_verified": True,
    "source_binary_equivalence_verified": False,
    "authenticated_build_provenance": False,
    "distribution_signature_freshly_verified": False,
    "dsc_signature_freshly_verified": False,
    "attestation_signature_freshly_verified": False,
    "current_repository_freshness_verified": False,
    "full_hosted_replay_performed": False,
    "live_private_abi_readout_qualified": False,
    "two_slot_breakpoint_qualified": False,
    "native_acquisition_performed": False,
    "consumer_resolution_observed": False,
    "loader_resolution_verified": False,
    "complete_native_closure_verified": False,
    "containment_enforced": False,
    "execution_ready": False,
    "execution_authorized": False,
    "selected_runtime_executed": False,
    "production_gate_eligible": False,
    "b2_complete": False,
    "metric_pass": None,
    "authority_effect": "none",
}
FUTURE_LIVE_PREDICATES = {
    "status": "required_not_observed",
    "fresh_original_input_admission_required": True,
    "fresh_task_guard_and_two_slot_hardware_qualification_required": True,
    "fresh_owned_process_and_descriptor_continuity_required": True,
    "fresh_loader_bias_and_instruction_bytes_required": True,
    "two_stopped_register_and_memory_samples_must_agree": True,
    "consumer_and_provider_namespace": "base_LM_ID_BASE_0",
    "selected_maps_l_real_equals_own_map_pointer": True,
    "l_addr_l_ld_match_fresh_original_object_mapping": True,
    "args_strtab_equals_consumer_bias_plus_original_DT_STRTAB": True,
    "args_name_equals_args_strtab_plus_selected_original_name_offset": True,
    "raw_needed_name_including_NUL_matches_original": True,
    "consumer_identity_and_name_select_exactly_one_DT_NEEDED_occurrence": True,
    "returned_provider_is_bound_from_live_RAX_and_current_backing_identity": True,
    "trace_mode_and_open_mode_require_selected_invocation_policy": True,
    "expected_provider_or_event_order_is_observation": False,
    "all_nine_unique_events_then_original_entry_and_owned_cleanup_required": True,
    "any_unexpected_stop_is_preserved_without_resume": True,
    "post_entry_resume_allowed": False,
    "absence_of_all_unselected_namespace_activity_claimed": False,
    "static_binding_supplies_live_evidence_or_authorization": False,
}
GATE_PROGRESS = {
    "historical_plan_edited": False,
    "static_artifact_and_selected_recipe_binding": "verified_in_this_record",
    "source_relationship": "archive_declared_source_and_exact_package_members",
    "source_to_binary_equivalence": "not_independently_reproduced",
    "authenticated_build_process": "not_established",
    "complete_prior_binary_source_build_gate": "not_closed_by_this_record",
    "live_private_abi_readout": "not_qualified",
    "two_slot_hardware_capability": "not_qualified",
    "new_request_capture_collector_and_independent_checker": "not_implemented",
    "fresh_original_loader_resolution_acquisition": "not_performed",
    "b2_issue": 2879,
    "b2_issue_state_required": "open",
}
# Source ranges explain the selected recipe; their bytes are independently
# recovered from the complete original source plus all relevant active patches.
# They are not a proof that compiling that source reproduces the package ELF.
SOURCE_ANCHORS = (
    ("args_and_call", "elf/dl-deps.c", 46, 68,
     (b"struct openaux_args", b"args->aux = _dl_map_object")),
    ("no_token_pointer_identity", "elf/dl-deps.c", 83, 122,
     (b"const char *__result = __str;", b"_dl_dst_count (__str)", b"if (__dst_cnt != 0)")),
    ("consumer_needed_callback", "elf/dl-deps.c", 208, 232,
     (b"args.map = l;", b"args.strtab = strtab;", b"DT_NEEDED",
      b"strtab + d->d_un.d_val", b"_dl_catch_exception (&exception, openaux, &args)")),
    ("no_token_count", "elf/dl-load.c", 227, 235,
     (b"strchr (input, '$')", b"input == NULL", b"return 0;")),
    ("already_loaded_return", "elf/dl-load.c", 1910, 1952,
     (b"_dl_map_object", b"_ns_loaded", b"return l;")),
    ("selected_map_identity", "include/link.h", 95, 115,
     (b"l_addr;", b"*l_ld;", b"*l_real;", b"l_ns;")),
    ("base_namespace", "dlfcn/dlfcn.h", 34, 38,
     (b"typedef long int Lmid_t;", b"LM_ID_BASE\t0")),
)


class BindingError(ValueError):
    """A stable rejection code without inspected content or paths."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise BindingError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def binding(raw):
    return {"sha256": sha(raw), "size_bytes": len(raw)}


def canonical(value):
    try:
        return (json.dumps(value, ensure_ascii=False, allow_nan=False,
                           sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise BindingError("loader_binary_binding_json_value") from exc


def _same(actual, expected, code):
    # Python equality alone would confuse booleans with integers.
    _need(canonical(actual) == canonical(expected), code)


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        _need(key not in out, "loader_binary_binding_duplicate_key")
        out[key] = value
    return out


def _nonfinite(_value):
    raise BindingError("loader_binary_binding_nonfinite_json")


def _float(_value):
    raise BindingError("loader_binary_binding_noninteger_number")


def parse(raw):
    _need(type(raw) is bytes and 0 < len(raw) <= CONTROL_BYTES,
          "loader_binary_binding_control_size")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=_nonfinite, parse_float=_float)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise BindingError("loader_binary_binding_json") from exc


def _bound(raw, descriptor, code):
    _need(type(raw) is bytes and len(raw) == descriptor["size_bytes"], code)
    _need(sha(raw) == descriptor["sha256"], code)


def _relative(name):
    _need(type(name) is str and 0 < len(name) <= 512 and "\\" not in name
          and "\0" not in name, "loader_binary_binding_relative_path")
    path = PurePosixPath(name)
    _need(bool(path.parts) and not path.is_absolute() and path.as_posix() == name
          and all(part not in {"", ".", ".."} for part in path.parts),
          "loader_binary_binding_relative_path")
    return path


def _source(path):
    _relative(path)
    try:
        return transport.read_regular(ROOT / path, SOURCE_LIMITS.get(path, CONTROL_BYTES))
    except (ValueError, OSError) as exc:
        raise BindingError("loader_binary_binding_source_unreadable") from exc


def _manifest():
    raw = _source(INPUTS_REL)
    _bound(raw, INPUTS, "loader_binary_binding_input_manifest_changed")
    return raw, parse(raw)


def read_artifact_members():
    """Read only the nine selected ordinary-size files, without reassembly I/O."""
    _raw, manifest = _manifest()
    members = {}
    for artifact in manifest["artifacts"]:
        for part in artifact["parts"]:
            path = part["path"]
            _relative(path)
            _need(path not in members, "loader_binary_binding_duplicate_part")
            try:
                members[path] = transport.read_regular(ROOT / CARRIER_REL / path, PART_BYTES)
            except (ValueError, OSError) as exc:
                raise BindingError("loader_binary_binding_part_unreadable") from exc
    return members


def _reassemble_inputs(artifact_members):
    """Verify every part and concatenate complete originals in their fixed order."""
    _raw, manifest = _manifest()
    _need(type(artifact_members) is dict, "loader_binary_binding_part_inventory")
    expected = {p["path"] for a in manifest["artifacts"] for p in a["parts"]}
    _need(len(expected) == manifest["part_count"] == 9
          and set(artifact_members) == expected, "loader_binary_binding_part_inventory")
    result, consumed = {}, set()
    for artifact in manifest["artifacts"]:
        name, chunks, offset = artifact["name"], [], 0
        _need(name not in result, "loader_binary_binding_duplicate_artifact")
        for ordinal, part in enumerate(artifact["parts"], 1):
            path = part["path"]
            _relative(path)
            _need(path not in consumed and part["ordinal"] == ordinal
                  and part["offset_bytes"] == offset
                  and 0 < part["size_bytes"] <= PART_BYTES,
                  "loader_binary_binding_part_layout")
            data = artifact_members[path]
            _bound(data, {key: part[key] for key in ("sha256", "size_bytes")},
                   "loader_binary_binding_part_bytes")
            chunks.append(data)
            consumed.add(path)
            offset += len(data)
        raw = b"".join(chunks)
        _bound(raw, {key: artifact[key] for key in ("sha256", "size_bytes")},
               "loader_binary_binding_artifact_bytes")
        _bound(raw, source.INPUT_BINDINGS[name], "loader_binary_binding_selected_artifact")
        result[name] = raw
    _need(consumed == expected and set(result) == set(source.INPUT_BINDINGS)
          and len(result) == manifest["artifact_count"] == 6
          and sum(map(len, result.values())) == manifest["total_artifact_bytes"] == 41590708
          and manifest["total_artifact_bytes"] < 64 * 1024 * 1024,
          "loader_binary_binding_complete_original_inputs")
    return result


def _distribution_metadata():
    selected = ("distribution-origin/Release", "distribution-origin/Packages",
                "distribution-origin/Release.gpg", "distribution-origin/debian-archive-keyring.gpg",
                "controls/distribution-trust-policy.json", "launcher-distribution-record.json",
                "distribution-origin/gpg-status.original", "distribution-origin/gpg-stderr.original")
    old = prior.entry.plan_check
    return old._archive(_source(old.ORIGINALS_REL), old.ORIGINALS, 114, 72234203, set(selected))


def _line_binding(sources, path, line, identifier):
    _need(path in sources and type(line) is int and line > 0,
          "loader_binary_binding_declaration_source")
    # DWARF physical lines are LF-delimited. str.splitlines() also splits the
    # form feed present in ldsodefs.h and would shift its later declarations.
    lines = sources[path].split(b"\n")
    _need(line <= len(lines), "loader_binary_binding_declaration_line")
    raw = lines[line - 1]
    token = identifier.encode("ascii")
    _need(re.search(rb"(?<![A-Za-z0-9_])" + re.escape(token) + rb"(?![A-Za-z0-9_])", raw)
          is not None, "loader_binary_binding_declaration_identifier")
    return {"source_path": path, "physical_line": line, "identifier": identifier,
            "source": binding(sources[path]), "line_without_LF": binding(raw)}


def _source_joins(facts, sources):
    declarations = []
    for row in facts["source_declarations"]:
        declarations.append({"die_offset": row["die_offset"],
            **_line_binding(sources, row["source_path"], row["decl_line"], row["name"])})
    for kind in ("openaux_args", "link_map"):
        for name, row in facts[kind]["members"].items():
            declarations.append({"die_offset": row["die_offset"],
                **_line_binding(sources, row["source_path"], row["decl_line"], name)})
    line_table = facts["cu"]["line_table"]
    _need(line_table["source_content_hashes_present"] is False,
          "loader_binary_binding_unclaimed_source_hashes")
    selected_rows = [row for row in line_table["openaux_rows"]
                     if row["address"] == facts["return_checkpoint"]["vaddr"]]
    _need(len(selected_rows) == 1, "loader_binary_binding_checkpoint_source_row")
    row = selected_rows[0]
    file_row = line_table["files"][row["file"]]
    checkpoint = _line_binding(sources, file_row["source_path"], row["line"], "_dl_map_object")
    anchors = []
    for role, path, first, last, tokens in SOURCE_ANCHORS:
        lines = sources[path].split(b"\n")
        _need(0 < first <= last <= len(lines), "loader_binary_binding_source_range")
        raw = b"\n".join(lines[first - 1:last]) + b"\n"
        _need(all(token in raw for token in tokens), "loader_binary_binding_source_semantics")
        anchors.append({"role": role, "source_path": path, "first_physical_line": first,
                        "last_physical_line": last, "range": binding(raw),
                        "source": binding(sources[path])})
    return {"physical_line_separator": "LF", "declarations": declarations,
            "checkpoint": checkpoint, "semantic_ranges": anchors,
            "DWARF_embeds_source_content_hashes": False,
            "full_source_to_binary_equivalence_established": False}


def _occurrences(native):
    _objects, dependencies, _interpreters = prior.derive_native_obligations(native)
    dynamic = {}
    forbidden = {0x6FFFFEFB, 0x6FFFFEFC, 0x7FFFFFFD, 0x7FFFFFFF}
    for path, raw in sorted(native.items()):
        headers = prior._program_headers(raw)
        segments = [row for row in headers if row["type"] == 2]
        _need(len(segments) == 1, "loader_binary_binding_dynamic_segment")
        segment = segments[0]
        entries = []
        for offset in range(segment["offset"], segment["offset"] + segment["filesz"], 16):
            tag, value = struct.unpack_from("<qQ", raw, offset)
            if tag == 0:
                break
            _need(tag not in forbidden, "loader_binary_binding_unselected_dynamic_hook")
            entries.append((tag, value))
        strings = [value for tag, value in entries if tag == 5]
        sizes = [value for tag, value in entries if tag == 10]
        _need(len(strings) == len(sizes) == 1, "loader_binary_binding_unique_dynstr")
        dynamic[path] = {"dynamic_vaddr": segment["vaddr"],
            "strtab_vaddr": strings[0], "strtab_size_bytes": sizes[0],
            "strtab_file_offset": prior._file_offset(headers, strings[0], sizes[0])}
    result, unique = [], set()
    for dep in dependencies:
        path, name = dep["consumer"]["path"], dep["name"]
        key = (path, name)
        _need(key not in unique and "$" not in name,
              "loader_binary_binding_unambiguous_original_occurrence")
        unique.add(key)
        row = dynamic[path]
        name_raw = name.encode("ascii") + b"\0"
        offset = row["strtab_file_offset"] + dep["string_table_offset"]
        _need(offset == dep["name_file_offset"]
              and native[path][offset:offset + len(name_raw)] == name_raw,
              "loader_binary_binding_original_name_bytes")
        result.append({**copy.deepcopy(dep), **row,
            "name_pointer_addend_vaddr": row["strtab_vaddr"] + dep["string_table_offset"],
            "name_with_NUL": {**binding(name_raw), "hex": name_raw.hex()},
            "pointer_base": "fresh_consumer_load_bias",
            "runtime_pointer_or_map_observed": False})
    _need(len(result) == len(unique) == 9, "loader_binary_binding_occurrence_count")
    return result


def make_record(*, historical, prior_report, inputs, manifest_raw):
    """Derive an authored static record; this is not an acquisition API."""
    metadata = _distribution_metadata()
    recovered = source.derive_source_facts(release_bytes=metadata["distribution-origin/Release"],
        packages_bytes=metadata["distribution-origin/Packages"], inputs=inputs)
    _need(recovered["loader"] == historical["native"]["native/ld-linux-x86-64.so.2"],
          "loader_binary_binding_package_is_original_loader")
    facts = binary.derive_binary_facts(loader_bytes=recovered["loader"], debug_bytes=recovered["debug"])
    joins = _source_joins(facts, recovered["sources"])
    checkpoint = facts["return_checkpoint"]
    recipe = {
        "status": "selected_static_recipe_only",
        "loader": copy.deepcopy(facts["loader"]),
        "checkpoint_vaddr": checkpoint["vaddr"],
        "checkpoint_file_offset": checkpoint["file_offset"],
        "live_RIP_relation": "fresh_original_loader_load_bias_plus_checkpoint_vaddr",
        "phase": "before_return_value_store_after_map_object_call",
        "args_pointer_register": checkpoint["args_register"],
        "provider_map_register": checkpoint["provider_register"],
        "args_bytes": facts["openaux_args"]["size_bytes"],
        "consumer_map_bytes": facts["link_map"]["required_prefix_bytes"],
        "provider_map_bytes": facts["link_map"]["required_prefix_bytes"],
        "args_fields": {key: {k: row[k] for k in ("offset_bytes", "size_bytes")}
                        for key, row in facts["openaux_args"]["members"].items()},
        "map_fields": {key: {k: row[k] for k in ("offset_bytes", "size_bytes")}
                       for key, row in facts["link_map"]["members"].items()},
        "map_namespace_is_signed": True,
        "selected_namespace_value": 0,
        "needed_name_read_size": "unique_original_name_length_plus_one_NUL",
        "map_pointer_chasing_beyond_selected_prefix": False,
        "args_aux_fresh_at_checkpoint": False,
        "args_pointer_assumed_in_RDI": False,
        "live_readout_qualified": False,
    }
    manifest = parse(manifest_raw)
    return {
        "record_type": "required_gate_idempotence_loader_binary_binding_v0",
        "profile": PROFILE,
        "input_manifest": {"path": INPUTS_REL, **binding(manifest_raw),
            "artifact_count": manifest["artifact_count"], "part_count": manifest["part_count"],
            "total_artifact_bytes": manifest["total_artifact_bytes"], "part_size_bytes_max": PART_BYTES},
        "prior_plan": {"sources": copy.deepcopy(PRIOR_SOURCES),
            "verification_report": binding(prior.canonical(prior_report)),
            "historical_authored_plan_unchanged": True},
        "historical_entry": {**copy.deepcopy(historical["baseline"]),
            "lower_level_reconstruction_accepted": True,
            "source_bindings_sha256": sha(canonical(historical["sources"]))},
        "historical_distribution_inputs": {"carrier_path": prior.entry.plan_check.ORIGINALS_REL,
            "carrier": dict(prior.entry.plan_check.ORIGINALS),
            "selected_members": {name: binding(raw) for name, raw in sorted(metadata.items())},
            "signature_evidence": "unchanged_selected_historical_signature_evidence",
            "externally_selected_archive_keyring_trust_required": True,
            "fresh_signature_verification_performed": False,
            "current_archive_freshness_verified": False},
        "source_binding": recovered["facts"],
        "static_binary": facts,
        "source_line_bindings": joins,
        "recipe": recipe,
        "occurrence_bindings": _occurrences(historical["native"]),
        "future_live_predicates": copy.deepcopy(FUTURE_LIVE_PREDICATES),
        "gate_progress": copy.deepcopy(GATE_PROGRESS),
        "boundary": copy.deepcopy(BOUNDARY),
    }


def verify_binding(*, record_bytes, expected_record_sha256,
                   historical_entry_archive_bytes, artifact_members):
    """Compare the complete control with fresh byte-derived facts and boundaries."""
    try:
        return _verify_binding(record_bytes, expected_record_sha256,
                               historical_entry_archive_bytes, artifact_members)
    except BindingError:
        raise
    except (prior.PlanError, source.SourceError, binary.BinaryError) as exc:
        raise BindingError("loader_binary_binding_evidence_rejected") from exc
    except (ValueError, KeyError, TypeError, IndexError, OSError, struct.error,
            OverflowError, RecursionError) as exc:
        raise BindingError("loader_binary_binding_invalid") from exc


def _verify_binding(record_bytes, expected_record_sha256, historical_entry_archive_bytes, artifact_members):
    _need(type(expected_record_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", expected_record_sha256),
          "loader_binary_binding_external_digest")
    _need(type(record_bytes) is bytes and 0 < len(record_bytes) <= CONTROL_BYTES
          and sha(record_bytes) == expected_record_sha256, "loader_binary_binding_digest_mismatch")
    record = parse(record_bytes)
    originals = {path: _source(path) for path in PRIOR_SOURCES}
    for path, descriptor in PRIOR_SOURCES.items():
        _bound(originals[path], descriptor, "loader_binary_binding_prior_source_changed")
    current = {path: _source(path) for path in NEW_SOURCES}
    manifest_raw, _manifest_value = _manifest()
    try:
        schema = parse(current[SCHEMA_REL])
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(record)
    except (jsonschema.ValidationError, jsonschema.SchemaError) as exc:
        raise BindingError("loader_binary_binding_schema") from exc
    # Fixed policy is checked before the expensive source replay. Evidence facts
    # are still independently derived below; rehashing the record never selects
    # a new policy or replaces raw evidence with caller-supplied assertions.
    for key, expected in (("boundary", BOUNDARY), ("gate_progress", GATE_PROGRESS),
                          ("future_live_predicates", FUTURE_LIVE_PREDICATES)):
        _same(record[key], expected, "loader_binary_binding_boundary_mismatch")
    inputs = _reassemble_inputs(artifact_members)
    previous = prior.verify_plan(plan_bytes=originals[prior.PLAN_REL],
        expected_plan_sha256=PRIOR_SOURCES[prior.PLAN_REL]["sha256"],
        historical_entry_archive_bytes=historical_entry_archive_bytes)
    historical = prior.reconstruct_historical_entry(historical_entry_archive_bytes)
    for path, descriptor in historical["sources"].items():
        _bound(_source(path), descriptor, "loader_binary_binding_historical_source_changed")
    expected = make_record(historical=historical, prior_report=previous,
                           inputs=inputs, manifest_raw=manifest_raw)
    _same(record, expected, "loader_binary_binding_record_mismatch")
    for path, raw in {**originals, **current, INPUTS_REL: manifest_raw}.items():
        _need(_source(path) == raw, "loader_binary_binding_checker_source_changed")
    for path, descriptor in historical["sources"].items():
        _bound(_source(path), descriptor, "loader_binary_binding_historical_source_changed")
    return {
        "record_type": "required_gate_idempotence_loader_binary_binding_verification_v0",
        "profile": PROFILE, "status": "accepted", "record": binding(record_bytes),
        "input_manifest": dict(INPUTS),
        "implementation_sources": {path: binding(raw) for path, raw in sorted(current.items())},
        "prior_sources": copy.deepcopy(PRIOR_SOURCES),
        "historical_source_file_count": len(historical["sources"]),
        "historical_sources_sha256": sha(canonical(historical["sources"])),
        "historical_entry_lower_level_reconstruction_accepted": True,
        "historical_entry_report": dict(prior.PINS["report"]),
        "artifact_count": 6, "artifact_part_count": 9, "original_artifact_bytes": 41590708,
        "source_binding_sha256": sha(canonical(expected["source_binding"])),
        "static_binary_sha256": sha(canonical(expected["static_binary"])),
        "source_line_bindings_sha256": sha(canonical(expected["source_line_bindings"])),
        "recipe_sha256": sha(canonical(expected["recipe"])),
        "occurrence_bindings_sha256": sha(canonical(expected["occurrence_bindings"])),
        "selected_patched_source_files": 7, "active_source_patches_scanned": 80,
        "static_DT_NEEDED_occurrences": 9,
        **copy.deepcopy(BOUNDARY),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True)
    parser.add_argument("--record-sha256", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        result = verify_binding(record_bytes=transport.read_regular(args.record, CONTROL_BYTES),
            expected_record_sha256=args.record_sha256,
            historical_entry_archive_bytes=transport.read_regular(ROOT / BASELINE_REL, prior.BASELINE["size_bytes"]),
            artifact_members=read_artifact_members())
        raw = canonical(result)
        if args.output:
            transport.write_new(Path(args.output), raw)
        sys.stdout.buffer.write(raw)
        return 0
    except (BindingError, OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError) as exc:
        code = exc.code if isinstance(exc, BindingError) else "loader_binary_binding_io"
        sys.stderr.buffer.write(canonical({"status": "rejected", "reason": code}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
