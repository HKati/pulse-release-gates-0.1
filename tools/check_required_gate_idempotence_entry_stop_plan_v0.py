#!/usr/bin/env python3
"""Check a finite original-entry observation proposal from preserved bytes only.

This checker reconstructs the selected historical cp0 capture and derives the
six native objects, ELF segments and static dependency occurrences. It does
not implement an entry collector, invoke a process, load an ELF object, verify
signatures, qualify an environment or authorize any acquisition.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import struct
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jsonschema
import check_required_gate_idempotence_exec_stop_v0 as cp0
import required_gate_idempotence_elf_v0 as elf
import required_gate_idempotence_exec_stop_hosted_io_v0 as transport

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_REL = "schemas/required_gate_idempotence_entry_stop_plan_v0.schema.json"
BASELINE_REL = ("preservation/required_gate_idempotence_exec_stop_v0/"
                "run_44375052171_attempt_1/control_evidence_v0.zip")
ORIGINALS_REL = "preservation/required_gate_idempotence_exec_stop_v0/original_inputs_v0.zip"
PROFILE = "linux_x86_64_original_launcher_entry_stop_plan_v0"
PROPOSED_PROFILE = "linux_x86_64_original_launcher_entry_stop_v0"
CONTROL_BYTES = 1024 * 1024
BASELINE = {"sha256": "788aaa185e979f5ecddfa3b17f8a45d8b74ee59671b26033b5b94c249c9359c6",
            "size_bytes": 737502}
ORIGINALS = {"sha256": "70b57f9a40cb375e267e215b3704be21c9f6d8987cadc13d92dfcc8db56d9c8a",
             "size_bytes": 24816167}
PINS = {
    "request": {"sha256": "c23bfc0f22e3f0a52f09c141a4956c2b7431fc2109c72fff9bcf66642043a7a9", "size_bytes": 8106},
    "capture": {"sha256": "0e7bc25175f9c95393ab7bd9a9895e72be5f608b17c2012c4249775e3c5dce13", "size_bytes": 5588},
    "report": {"sha256": "8a2769ae4e7858f73b7cca9285724aabaee152f4dbf6e5bfb6c603cea538b34b", "size_bytes": 2200},
    "receipt": {"sha256": "e57d1d742251dbbcf1f92033273889ead9b3ac23daa6f89ae4847dd613631e6c", "size_bytes": 43080},
    "verified_binding": {"sha256": "e08c4504d77c6b73dd40f6fc38164699583bed9ff82015db7e9f19a5bc2f8e27", "size_bytes": 11522},
}
HISTORICAL_CONTEXT = {
    "run_id": 44375052171, "run_attempt": 1,
    "source_commit": "84b78ff1758ed3db73fbb1db1b37451ca6620373",
    "attempt_id": "d54f64c544090b13d2c2633b32204e02",
}
BOUNDARY = {
    "record_status": "proposal", "diagnostic_only": True,
    "entry_checkpoint_observed": False, "additional_native_objects_observed": False,
    "native_acquisition_performed": False, "collector_implemented": False,
    "host_environment_qualified": False, "physical_execution_authenticated": False,
    "loader_resolution_verified": False, "complete_native_closure_verified": False,
    "containment_enforced": False, "execution_ready": False,
    "execution_authorized": False, "selected_runtime_executed": False,
    "production_gate_eligible": False, "b2_complete": False,
    "metric_pass": None, "authority_effect": "none",
}


class PlanError(ValueError):
    """Stable rejection code; inspected bytes and paths are not echoed."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise PlanError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def binding(raw):
    return {"sha256": sha(raw), "size_bytes": len(raw)}


def canonical(value):
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise PlanError("entry_stop_plan_json_value") from exc


def _same(actual, expected, code):
    # Canonical byte equality distinguishes bool/int and int/float values.
    _need(canonical(actual) == canonical(expected), code)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _need(key not in result, "entry_stop_plan_duplicate_key")
        result[key] = value
    return result


def _constant(_value):
    raise PlanError("entry_stop_plan_nonfinite_json")


def _float(_value):
    raise PlanError("entry_stop_plan_noninteger_number")


def parse(raw):
    _need(type(raw) is bytes and 0 < len(raw) <= CONTROL_BYTES, "entry_stop_plan_control_size")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=_constant, parse_float=_float)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise PlanError("entry_stop_plan_json") from exc


def _bound(raw, expected, code):
    _need(type(raw) is bytes and len(raw) == expected["size_bytes"]
          and sha(raw) == expected["sha256"], code)


def _relative(name):
    _need(type(name) is str and 0 < len(name) <= 512 and "\\" not in name,
          "entry_stop_plan_member_path")
    path = PurePosixPath(name)
    _need(not path.is_absolute() and path.as_posix() == name
          and all(part not in {"", ".", ".."} for part in path.parts),
          "entry_stop_plan_member_path")
    return path


def _archive(raw, expected, count, decoded_bytes, selected=None):
    _bound(raw, expected, "entry_stop_plan_archive_binding")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            _need(len(infos) == count == len(set(names)), "entry_stop_plan_archive_roster")
            _need(sum(info.file_size for info in infos) == decoded_bytes,
                  "entry_stop_plan_archive_size")
            for info in infos:
                _relative(info.filename)
                mode = info.external_attr >> 16
                _need(not info.is_dir() and not info.flag_bits & 1
                      and stat.S_IFMT(mode) in {0, stat.S_IFREG}
                      and info.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED},
                      "entry_stop_plan_archive_member_type")
            wanted = set(names) if selected is None else set(selected)
            _need(wanted <= set(names), "entry_stop_plan_archive_member_missing")
            result = {name: archive.read(name) for name in sorted(wanted)}
            _need(all(len(result[name]) == archive.getinfo(name).file_size for name in wanted),
                  "entry_stop_plan_archive_member_size")
            return result
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, EOFError) as exc:
        if isinstance(exc, PlanError):
            raise
        raise PlanError("entry_stop_plan_archive_invalid") from exc


def _source(path):
    _relative(path)
    try:
        return transport.read_regular(ROOT / path, CONTROL_BYTES)
    except (OSError, ValueError) as exc:
        raise PlanError("entry_stop_plan_source_unreadable") from exc


def reconstruct_historical_cp0(raw):
    members = _archive(raw, BASELINE, 234, 1513977)
    prefix = "acquisition/observation/capture/"
    capture_tree = {name[len(prefix):]: data for name, data in members.items() if name.startswith(prefix)}
    _need(set(capture_tree) == {"capture.json", *cp0.FILE_NAMES}, "entry_stop_plan_cp0_roster")
    request = members["acquisition/observation/request.json"]
    capture = capture_tree.pop("capture.json")
    report1 = members["verification/verification/capture-check-1.json"]
    report2 = members["verification/verification/capture-check-2.json"]
    receipt_raw = members["acquisition/receipt.json"]
    verified_raw = members["verification/verified-binding.json"]
    for name, data in (("request", request), ("capture", capture), ("report", report1),
                       ("report", report2), ("receipt", receipt_raw), ("verified_binding", verified_raw)):
        _bound(data, PINS[name], "entry_stop_plan_cp0_binding")
    try:
        report = cp0.verify_capture(
            request_bytes=request, expected_request_sha256=PINS["request"]["sha256"],
            capture_bytes=capture, expected_capture_sha256=PINS["capture"]["sha256"], files=capture_tree)
    except (cp0.ExecStopError, OSError, ValueError) as exc:
        raise PlanError("entry_stop_plan_historical_cp0_rejected") from exc
    _need(canonical(report) == report1 == report2
          and report.get("status") == "accepted" and report.get("observation_complete") is True
          and all(report.get(key) is True for key in cp0.NARROW_FLAGS),
          "entry_stop_plan_historical_cp0_incomplete")
    receipt, verified = parse(receipt_raw), parse(verified_raw)
    sources = parse(members["acquisition/source-bindings.json"])
    _need(type(sources) is dict and len(sources) == 62, "entry_stop_plan_historical_sources")
    _same(sources, parse(members["verification/source-bindings.json"]), "entry_stop_plan_historical_sources")
    _same(sources, receipt["source_bindings"], "entry_stop_plan_historical_sources")
    _same(sources, verified["source_bindings"], "entry_stop_plan_historical_sources")
    for path, descriptor in sources.items():
        _same(binding(_source(path)), descriptor, "entry_stop_plan_historical_source_changed")
    _same(receipt["context"], verified["context"], "entry_stop_plan_historical_context")
    context = verified["context"]
    _same({key: context[key] for key in ("run_id", "run_attempt", "source_commit")},
          {key: HISTORICAL_CONTEXT[key] for key in ("run_id", "run_attempt", "source_commit")},
          "entry_stop_plan_historical_context")
    _need(report["attempt_id"] == HISTORICAL_CONTEXT["attempt_id"], "entry_stop_plan_historical_attempt")
    for key in ("request", "capture"):
        _same(receipt[key], PINS[key], "entry_stop_plan_receipt_binding")
        _same(verified[key], PINS[key], "entry_stop_plan_verified_binding")
    for key in ("first_report", "second_report"):
        _same(verified[key], PINS["report"], "entry_stop_plan_verified_binding")
    _same(verified["original_receipt"], PINS["receipt"], "entry_stop_plan_verified_binding")
    for name, data in members.items():
        if name.startswith("acquisition/") and name != "acquisition/receipt.json":
            _same(receipt["files"].get(name[len("acquisition/"):]), binding(data),
                  "entry_stop_plan_selected_receipt_member")
    return parse(request), sources


def _elf_extra(raw):
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", raw)
    relro, dynamic = [], []
    for index in range(header[10]):
        kind, _flags, offset, address, _physical, filesz, memsz, _align = struct.unpack_from(
            "<IIQQQQQQ", raw, header[5] + index * header[9])
        if kind == 0x6474E552:
            relro.append({"index": index, "vaddr": address, "memsz": memsz})
        if kind == 2:
            dynamic = [struct.unpack_from("<qQ", raw, pos) for pos in range(offset, offset + filesz, 16)]
    _need(len(relro) <= 1, "entry_stop_plan_relro")
    return {
        "gnu_relro": relro,
        "init_declared": any(tag == 12 for tag, _ in dynamic),
        "init_array_bytes": next((value for tag, value in dynamic if tag == 27), 0),
        "preinit_array_bytes": next((value for tag, value in dynamic if tag == 33), 0),
        "text_relocations_declared": any(tag == 22 or tag == 30 and value & 4 for tag, value in dynamic),
    }


def derive_native_obligations(originals_raw):
    native = _archive(originals_raw, ORIGINALS, 114, 72234203, cp0.NATIVE)
    objects, relationships = [], []
    names = {PurePosixPath(path).name: path for path in native}
    for path in sorted(native):
        raw = native[path]
        _bound(raw, cp0.NATIVE[path], "entry_stop_plan_native_binding")
        try:
            metadata = elf.inspect_elf(raw)
            layout = cp0.elf_layout(raw)
            extra = _elf_extra(raw)
        except (ValueError, struct.error) as exc:
            raise PlanError("entry_stop_plan_native_elf") from exc
        _need(metadata["rpath"] is None and metadata["runpath"] is None
              and extra["text_relocations_declared"] is False, "entry_stop_plan_native_profile")
        segments = layout["segments"]
        samples = []
        for segment in segments:
            if segment["flags"] == 5:
                expected = binding(raw[segment["offset"]:segment["offset"] + segment["filesz"]])
                for sample in (0, 1):
                    samples.append({"segment_index": segment["index"], "sample_index": sample,
                                    "file_offset": segment["offset"], "vaddr": segment["vaddr"], **expected})
        objects.append({"path": path, **binding(raw), "elf": layout,
                        "dynamic": metadata, "initialization": extra,
                        "presence": "required_for_positive_entry_observation",
                        "entry_observed": False, "rx_samples": samples})
        declarations = ([] if metadata["interpreter"] is None else
                        [("interpreter", metadata["interpreter"])])
        declarations += [("needed", name) for name in metadata["needed"]]
        for kind, name in declarations:
            provider = names.get(PurePosixPath(name).name)
            _need(provider is not None, "entry_stop_plan_dependency_outside_selection")
            relationships.append({"consumer": path, "kind": kind, "name": name, "provider": provider,
                "static_selection_verified": True, "provider_mapping_observed": False,
                "consumer_resolution_observed": False,
                "entry_obligation": "fresh_kernel_interpreter_continuity" if path == "native/bwrap" and kind == "interpreter"
                else "static_metadata_only" if kind == "interpreter" else "mapped_provider_is_not_consumer_resolution"})
    relationships.sort(key=lambda row: (row["consumer"], row["kind"], row["name"]))
    return objects, relationships


def verify_plan(*, plan_bytes, expected_plan_sha256, baseline_archive_bytes, originals_archive_bytes):
    _need(type(expected_plan_sha256) is str and len(expected_plan_sha256) == 64
          and all(c in "0123456789abcdef" for c in expected_plan_sha256), "entry_stop_plan_external_digest")
    _need(type(plan_bytes) is bytes and 0 < len(plan_bytes) <= CONTROL_BYTES
          and sha(plan_bytes) == expected_plan_sha256, "entry_stop_plan_digest_mismatch")
    plan = parse(plan_bytes)
    schema_raw = _source(SCHEMA_REL)
    implementation_raw = _source("tools/check_required_gate_idempotence_entry_stop_plan_v0.py")
    try:
        jsonschema.Draft202012Validator(parse(schema_raw)).validate(plan)
    except (jsonschema.ValidationError, jsonschema.SchemaError) as exc:
        raise PlanError("entry_stop_plan_schema") from exc
    request, sources = reconstruct_historical_cp0(baseline_archive_bytes)
    objects, relationships = derive_native_obligations(originals_archive_bytes)
    _same(plan["native_objects"], objects, "entry_stop_plan_native_obligations")
    _same(plan["static_relationships"], relationships, "entry_stop_plan_relationships")
    _same(plan["observer"], request["observer"], "entry_stop_plan_observer")
    _same(plan["boundary"], BOUNDARY, "entry_stop_plan_boundary")
    totals = {
        "native_objects": len(objects),
        "pt_load_occurrences": sum(len(obj["elf"]["segments"]) for obj in objects),
        "rx_sample_occurrences": sum(len(obj["rx_samples"]) for obj in objects),
        "rx_sample_bytes": sum(row["size_bytes"] for obj in objects for row in obj["rx_samples"]),
        "distinct_rx_bytes": sum(row["size_bytes"] for obj in objects for row in obj["rx_samples"] if row["sample_index"] == 0),
        "static_relationships": len(relationships),
        "dt_needed_relationships": sum(row["kind"] == "needed" for row in relationships),
        "pt_interp_relationships": sum(row["kind"] == "interpreter" for row in relationships),
    }
    _same(plan["totals"], totals, "entry_stop_plan_totals")
    # Fixed proposal budget covers two complete file snapshots, all declared RX
    # samples, the selected observer and a bounded control/procfs allowance.
    minimum = 2 * sum(obj["size_bytes"] for obj in objects) + totals["rx_sample_bytes"] + request["observer"]["size_bytes"]
    _need(minimum + 8 * CONTROL_BYTES <= plan["limits"]["total_capture_bytes"], "entry_stop_plan_capture_budget")
    _need(_source(SCHEMA_REL) == schema_raw
          and _source("tools/check_required_gate_idempotence_entry_stop_plan_v0.py") == implementation_raw,
          "entry_stop_plan_checker_source_changed")
    for path, descriptor in sources.items():
        _same(binding(_source(path)), descriptor, "entry_stop_plan_historical_source_changed")
    return {"record_type": "required_gate_idempotence_entry_stop_plan_verification_v0",
        "profile": PROFILE, "status": "accepted", "plan": binding(plan_bytes),
        "plan_consistency_verified": True,
        "historical_cp0": {**HISTORICAL_CONTEXT, "lower_level_reconstruction_accepted": True,
                           "report": PINS["report"], "source_file_count": len(sources)},
        "original_native_bytes_verified": True, "totals": totals,
        "native_obligations_sha256": sha(canonical(objects)),
        "static_relationships_sha256": sha(canonical(relationships)),
        "checker_source": binding(implementation_raw), "schema_source": binding(schema_raw),
        "distribution_signature_freshly_verified": False,
        "attestation_signature_freshly_verified": False,
        "full_hosted_replay_performed": False, **BOUNDARY}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        result = verify_plan(
            plan_bytes=transport.read_regular(args.plan, CONTROL_BYTES),
            expected_plan_sha256=args.plan_sha256,
            baseline_archive_bytes=transport.read_regular(ROOT / BASELINE_REL, BASELINE["size_bytes"]),
            originals_archive_bytes=transport.read_regular(ROOT / ORIGINALS_REL, ORIGINALS["size_bytes"]))
        raw = canonical(result)
        if args.output:
            transport.write_new(Path(args.output), raw)
        sys.stdout.buffer.write(raw)
        return 0
    except (PlanError, OSError, ValueError) as exc:
        code = exc.code if isinstance(exc, PlanError) else "entry_stop_plan_io"
        sys.stderr.buffer.write(canonical({"status": "rejected", "reason": code}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
