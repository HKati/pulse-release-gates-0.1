#!/usr/bin/env python3
"""Check authored initial-stack and startup/resume-policy fixtures only.

The original-loader readout and inert two-slot transcript validators remain
unchanged.  This additional acceptance layer joins an authored initial cp0
stack to the nine original-loader readout fixtures, checks the selected normal
startup modes directly in both raw argument samples, and checks Linux-visible
RF/TF values at every hardware stop.  It never acquires a process, executes an
ELF, writes registers, or authenticates a build or a current kernel.

The wrapper independently reconstructs the original source/instruction policy
before calling this module.  Linux v6.11 below is an explanatory implementation
reference, not a selected runtime or an attestation about the host.  Its execute
breakpoint handler sets RF; PTRACE_CONT clears single stepping while preserving
RF.  Architectural execute #DB alone must not be described as setting RF.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jsonschema
import required_gate_idempotence_loader_readout_v0 as readout
import required_gate_idempotence_loader_two_slot_v0 as two_slot


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_REL = "schemas/required_gate_idempotence_loader_startup_invocation_v0.schema.json"
RECORD_TYPE = "required_gate_idempotence_loader_startup_invocation_fixture_v0"
PROFILE = "linux_x86_64_original_loader_startup_invocation_fixture_v0"
TF_MASK = 0x100
RF_MASK = 0x10000
EXPECTED_STRINGS = (b"bubblewrap\0", b"LC_ALL=C\0", b"TZ=UTC\0")
STRING_BYTES = b"".join(EXPECTED_STRINGS)
FILE_NAMES = tuple(sorted((
    "observer.stat.bin", "observer.status.bin", "child.stat.setup.bin",
    "child.status.setup.bin", "child.pidfd.info.bin",
    *("child." + kind + "." + side + ".bin"
      for kind in ("stat", "status") for side in ("before", "after")),
    *(kind + "." + side + ".bin"
      for kind in ("maps", "regs", "auxv", "stack.words", "stack.strings")
      for side in ("before", "after")),
)))

BOUNDARY = {
    "invocation_mode_policy_qualified": False,
    "rflags_resume_policy_qualified": False,
    "initial_stack_acquisition_authenticated": False,
    "contemporaneous_backing_acquisition_authenticated": False,
    "live_private_abi_readout_qualified": False,
    "two_slot_breakpoint_qualified": False,
    "source_build_gate_satisfied": False,
    "original_acquisition_ready": False,
    "consumer_resolution_observed": False,
    "native_acquisition_performed": False,
    "physical_execution_authenticated": False,
    "metric_pass": None,
    "authority_effect": "none",
}

POLICY = {
    "evidence_origin": "authored_test_fixture",
    "invocation_record_type": RECORD_TYPE,
    "invocation_profile": PROFILE,
    "argument_count": 1,
    "argument_strings": ["bubblewrap"],
    "environment_strings": ["LC_ALL=C", "TZ=UTC"],
    "stack_word_bytes": 8,
    "initial_stack_alignment": 16,
    "control_prefix_words": 6,
    "control_prefix": "argc,argv0,NULL,env0,env1,NULL",
    "strings_packing": "argv0_NUL,LC_ALL=C_NUL,TZ=UTC_NUL",
    "string_sample_bytes": len(STRING_BYTES),
    "auxv_max_pairs_including_null": 64,
    "auxv_at_secure": 0,
    "full_auxv_equal_across_cp0_stack_proc_and_readout_events": True,
    "initial_pc": "original_loader_load_bias_plus_original_loader_ELF_entry",
    "launcher_entry_differs_from_loader_entry": True,
    "cp0_original_file_mappings": [readout.LAUNCHER, readout.LOADER],
    "stack_memory_mapping": "one_readable_original_cp0_stack_row",
    "stack_ranges_overlap_allowed": False,
    "register_bytes": 216,
    "samples": 2,
    "raw_files": len(FILE_NAMES),
    "proc_file_bytes": 65536,
    "auxv_bytes": 1024,
    "stack_control_bytes": 1072,
    "raw_total_bytes": 1048576,
    "control_bytes": 1048576,
    "trace_mode": 0,
    "open_mode": 0,
    "mode_member_offsets": [8, 12],
    "mode_member_encoding": "little_endian_signed_32",
    "hardware_stop_rf": 1,
    "hardware_stop_tf": 0,
    "cp0_rf_values": [0, 1],
    "cp0_tf": 0,
    "general_register_writes_allowed": False,
    "readout_event_count": 9,
    "two_slot_subject": "separate_inert_probe",
    "kernel_reference_is_runtime_attestation": False,
    "kernel_policy_references": [
        "https://github.com/torvalds/linux/blob/v6.11/arch/x86/kernel/hw_breakpoint.c#L557-L562",
        "https://github.com/torvalds/linux/blob/v6.11/arch/x86/kernel/ptrace.c#L342-L353",
        "https://github.com/torvalds/linux/blob/v6.11/arch/x86/kernel/step.c#L229-L244",
        "https://github.com/torvalds/linux/blob/v6.11/kernel/ptrace.c#L823-L868",
    ],
    "architecture_reference": "https://www.amd.com/content/dam/amd/en/documents/processor-tech-docs/programmer-references/24593.pdf",
    "architecture_reference_section": "AMD64 Volume 2, RFLAGS Resume Flag (RF), bit 16",
    "fixture_acceptance_is_live_qualification": False,
}


class StartupReadoutError(ValueError):
    """Stable rejection reason without inspected process or memory content."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise StartupReadoutError(code)


def _keys(value, expected, code):
    _need(type(value) is dict and len(value) == len(expected)
          and all(type(key) is str for key in value) and set(value) == set(expected), code)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _need(key not in result, "loader_startup_duplicate_key")
        result[key] = value
    return result


def _invalid_number(_value):
    raise StartupReadoutError("loader_startup_control_number")


def _control(value):
    if type(value) is bytes:
        _need(0 < len(value) <= POLICY["control_bytes"], "loader_startup_control_size")
        value = json.loads(value.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_float=_invalid_number, parse_constant=_invalid_number)
    # Bound direct Python values, reject ambiguous types and cycles before any
    # serialization, schema loading, input hashing or binary parsing.
    readout._json_bytes(value)
    _need(type(value) is dict, "loader_startup_control_object")
    return value


def _binding(raw):
    return {"size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _descriptor(value, length):
    _keys(value, ("size_bytes", "sha256"), "loader_startup_binding_fields")
    _need(type(value["size_bytes"]) is int and value["size_bytes"] == length,
          "loader_startup_binding_size")
    _need(type(value["sha256"]) is str and
          re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is not None,
          "loader_startup_binding_digest")


def _invocation_lengths(invocation, files):
    _keys(files, FILE_NAMES, "loader_startup_raw_roster")
    _need("raw_files" in invocation, "loader_startup_binding_roster")
    _keys(invocation["raw_files"], FILE_NAMES, "loader_startup_binding_roster")
    total = 0
    for name in FILE_NAMES:
        raw = files[name]
        _need(type(raw) is bytes, "loader_startup_raw_type")
        if name.startswith("regs."):
            valid = len(raw) == POLICY["register_bytes"]
        elif name.startswith("stack.strings."):
            valid = len(raw) == POLICY["string_sample_bytes"]
        elif name.startswith("stack.words."):
            valid = 64 <= len(raw) <= POLICY["stack_control_bytes"] and len(raw) % 8 == 0
        elif name.startswith("auxv."):
            valid = 16 <= len(raw) <= POLICY["auxv_bytes"] and len(raw) % 16 == 0
        else:
            valid = 0 < len(raw) <= POLICY["proc_file_bytes"]
        _need(valid, "loader_startup_raw_size")
        total += len(raw)
        _need(total <= POLICY["raw_total_bytes"], "loader_startup_raw_total")
        _descriptor(invocation["raw_files"][name], len(raw))
    return total


def _transcript_lengths(transcript, files):
    """Preflight the separate complete/prefix input before *any* input hashing.

    Its unchanged validator remains the authority for all transcript semantics.
    Reusing its roster and limits here avoids hashing the nine-event input set
    before discovering an oversized or extra two-slot member.
    """
    for name, maximum in (("events", 10), ("resumes", 11)):
        _need(name in transcript and type(transcript[name]) is list
              and len(transcript[name]) <= maximum, "loader_startup_two_slot_shape")
    expected = two_slot._expected_files(len(transcript["events"]), len(transcript["resumes"]))
    _keys(files, expected, "loader_startup_two_slot_raw_roster")
    _need("raw_files" in transcript, "loader_startup_two_slot_binding_roster")
    _keys(transcript["raw_files"], expected, "loader_startup_two_slot_binding_roster")
    total = 0
    for name in sorted(expected):
        raw = files[name]
        limit, exact = two_slot._file_size(name)
        _need(type(raw) is bytes and 0 < len(raw) <= limit
              and (not exact or len(raw) == limit), "loader_startup_two_slot_raw_size")
        total += len(raw)
        _need(total <= two_slot.POLICY["raw_total_bytes"], "loader_startup_two_slot_raw_total")
        _descriptor(transcript["raw_files"][name], len(raw))


def _schema(invocation):
    raw = readout.transport.read_regular(ROOT / SCHEMA_REL, POLICY["control_bytes"])
    try:
        schema = json.loads(raw, object_pairs_hook=_pairs,
                            parse_float=_invalid_number, parse_constant=_invalid_number)
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(invocation)
    except (jsonschema.ValidationError, jsonschema.SchemaError, json.JSONDecodeError) as exc:
        raise StartupReadoutError("loader_startup_invocation_schema") from exc


def _rflags(raw, *, hardware_stop):
    flags = struct.unpack_from("<Q", raw, 18 * 8)[0]
    _need(flags & TF_MASK == 0, "loader_startup_trap_flag")
    if hardware_stop:
        _need(flags & RF_MASK == RF_MASK, "loader_startup_hardware_resume_flag")


def _stack_range(stack, address, length):
    _need(type(address) is int and 0 < address < readout.ADDRESS_LIMIT
          and length > 0 and length <= readout.ADDRESS_LIMIT - address,
          "loader_startup_stack_address")
    _need(stack["permissions"][0] == "r" and stack["start"] <= address
          and address + length <= stack["end"], "loader_startup_stack_range")
    return address, address + length


def _invocation(invocation, files, events, files_by_event, native, readout_report, raw_total):
    _schema(invocation)
    for name in FILE_NAMES:
        _need(invocation["raw_files"][name] == _binding(files[name]),
              "loader_startup_raw_binding")
    for kind in ("child.stat", "child.status", "maps", "regs", "auxv",
                 "stack.words", "stack.strings"):
        _need(files[kind + ".before.bin"] == files[kind + ".after.bin"],
              "loader_startup_unstable_samples")

    # The original process and inert hardware probe are intentionally separate.
    # Only this invocation and the original-loader readout fixtures are joined.
    readout._processes(invocation, files)
    first = events[0]
    for key in ("attempt_id", "observer_pid", "child_pid", "child_starttime"):
        _need(type(invocation[key]) is type(first[key]) and invocation[key] == first[key],
              "loader_startup_process_context")
    observer = readout.proc.parse_proc_stat(files["observer.stat.bin"])
    first_observer = readout.proc.parse_proc_stat(files_by_event[0]["observer.stat.bin"])
    _need((observer["starttime"], observer["ppid"]) ==
          (first_observer["starttime"], first_observer["ppid"]),
          "loader_startup_observer_context")
    for event_files in files_by_event:
        _need(files["child.pidfd.info.bin"] == event_files["child.pidfd.info.bin"],
              "loader_startup_pidfd_context")
        _need(files["auxv.before.bin"] == event_files["auxv.before.bin"],
              "loader_startup_auxv_context")

    # Backing metadata and the six original byte inputs were already checked by
    # verify_event_set.  Reuse those identities to derive cp0 ELF mapping biases;
    # do not accept a caller-supplied claimed load bias or pathname-only join.
    map_context = {"backings": first["backings"]}
    rows, layouts = readout._maps(map_context, files, native)
    _need(set(layouts) == {readout.LAUNCHER, readout.LOADER},
          "loader_startup_cp0_object_roster")
    auxv = readout._auxv(files, layouts)
    _need(23 in auxv and auxv[23] == 0, "loader_startup_secure_mode")
    loader_bias = layouts[readout.LOADER]["bias"]
    initial_pc = loader_bias + layouts[readout.LOADER]["entry"]
    _need(auxv[9] != initial_pc, "loader_startup_interpreter_route")
    _need(all(join["loader_load_bias"] == loader_bias
              for join in readout_report["occurrence_joins"]),
          "loader_startup_loader_bias_context")
    registers = struct.unpack("<27Q", files["regs.before.bin"])
    _need(registers[16] == initial_pc, "loader_startup_initial_pc")
    rsp = registers[19]
    _need(rsp % POLICY["initial_stack_alignment"] == 0, "loader_startup_stack_alignment")
    for side in ("before", "after"):
        _rflags(files["regs." + side + ".bin"], hardware_stop=False)

    stacks = [row for row in rows if row["path"] == "[stack]"]
    _need(len(stacks) == 1, "loader_startup_stack_mapping")
    stack = stacks[0]
    raw_words = files["stack.words.before.bin"]
    raw_auxv = files["auxv.before.bin"]
    _need(len(raw_words) == 48 + len(raw_auxv) and raw_words[48:] == raw_auxv,
          "loader_startup_stack_auxv")
    argc, argv0, argv_null, env0, env1, env_null = struct.unpack_from("<6Q", raw_words)
    _need(argc == 1 and argv_null == env_null == 0, "loader_startup_stack_vector_shape")
    _need(files["stack.strings.before.bin"] == STRING_BYTES,
          "loader_startup_string_bytes")
    intervals = [_stack_range(stack, rsp, len(raw_words))]
    for pointer, raw_string in zip((argv0, env0, env1), EXPECTED_STRINGS):
        interval = _stack_range(stack, pointer, len(raw_string))
        _need(all(interval[1] <= start or interval[0] >= end for start, end in intervals),
              "loader_startup_stack_range_overlap")
        intervals.append(interval)
    # Fixed packing consumes every string byte exactly once.  The raw pointers
    # supply the virtual addresses of those three samples, not their packed
    # offsets; noncontiguous string addresses are therefore permitted.
    return {
        "fixture_invocation_consistent": True,
        "evidence_origin": "authored_test_fixture",
        "attempt_id": invocation["attempt_id"],
        "argc": argc,
        "argv": ["bubblewrap"],
        "envp": ["LC_ALL=C", "TZ=UTC"],
        "cp0_stack_pointer": rsp,
        "initial_loader_pc": initial_pc,
        "launcher_entry": auxv[9],
        "loader_load_bias": loader_bias,
        "auxv_pairs_including_null": len(raw_auxv) // 16,
        "auxv_at_secure": auxv[23],
        "stack_words": _binding(raw_words),
        "stack_strings": _binding(files["stack.strings.before.bin"]),
        "raw_file_count": len(FILE_NAMES),
        "raw_total_bytes": raw_total,
        **copy.deepcopy(BOUNDARY),
    }


def verify_policy_fixtures(*, invocation, invocation_files, events, files_by_event,
                           transcript, transcript_files, static_record, native):
    """Accept complete or incomplete authored policy fixtures, never live data.

    ``invocation`` and ``transcript`` are strictly typed dictionaries or bounded
    UTF-8 JSON bytes; each raw-file mapping contains externally supplied bytes.
    The nine readout fixtures share the invocation's process/attempt/auxv.
    The two-slot transcript describes a separate inert probe.  A valid incomplete
    transcript remains incomplete even when all nine readout fixtures validate.
    """
    try:
        invocation, transcript = _control(invocation), _control(transcript)
        raw_total = _invocation_lengths(invocation, invocation_files)
        _need(type(events) is list and len(events) == 9
              and type(files_by_event) is list and len(files_by_event) == 9,
              "loader_startup_readout_count")
        for event_files in files_by_event:
            readout._lengths(event_files, native)
        _transcript_lengths(transcript, transcript_files)

        # Both unchanged independent validators run here.  A producer's saved
        # result, schema success or fixture success flag is never accepted.
        event_report = readout.verify_event_set(events=events, files_by_event=files_by_event,
                                               static_record=static_record, native=native)
        transcript_report = two_slot.verify_transcript(transcript=transcript, files=transcript_files)
        invocation_report = _invocation(invocation, invocation_files, events, files_by_event,
                                        native, event_report, raw_total)

        for event, event_files in zip(events, files_by_event):
            args = next(row for row in event["runtime_ranges"] if row["role"] == "args")
            for sample in (0, 1):
                raw = event_files["memory.sample%d.bin" % sample]
                modes = struct.unpack_from("<ii", raw, args["offset"] + 8)
                _need(modes == (0, 0), "loader_startup_argument_modes")
            for side in ("before", "after"):
                _rflags(event_files["regs." + side + ".bin"], hardware_stop=True)
        _rflags(transcript_files["cp0.regs.bin"], hardware_stop=False)
        for number in range(1, len(transcript["events"]) + 1):
            for side in ("a", "b"):
                _rflags(transcript_files["event.%02d.regs.%s.bin" % (number, side)],
                        hardware_stop=True)

        complete = transcript_report["complete_fixture_sequence_verified"]
        return {
            "record_type": "required_gate_idempotence_loader_startup_policy_fixture_verification_v0",
            "evidence_origin": "authored_test_fixture",
            "status": "accepted_test_fixtures" if complete else "incomplete_test_fixtures",
            "complete_fixture_set_verified": complete,
            "fixture_invocation_modes_verified": True,
            "fixture_hardware_resume_flags_verified": True,
            "two_slot_probe_is_original_loader_attempt": False,
            "invocation_fixture": invocation_report,
            "readout_fixture": event_report,
            "two_slot_fixture": transcript_report,
            **copy.deepcopy(BOUNDARY),
        }
    except StartupReadoutError:
        raise
    except (readout.ReadoutError, two_slot.TwoSlotError) as exc:
        raise StartupReadoutError(exc.code) from exc
    except (ValueError, TypeError, KeyError, IndexError, OSError, struct.error,
            OverflowError, UnicodeError, RecursionError, StopIteration) as exc:
        raise StartupReadoutError("loader_startup_fixture_invalid") from exc
