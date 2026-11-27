"""Pure-data policy for the minimal containment-entry startup task guard.

No function in this module installs a filter, starts a process or qualifies a
host. The inherited filter restricts the shape of selected task-creation calls;
it cannot identify L/R/T, enforce their order/count, or authenticate pointers.
The separate observer must establish those relationships before each restart.
"""
from __future__ import annotations

import hashlib
import json
import struct


PROFILE = "linux_x86_64_original_bwrap_minimal_entry_task_guard_v0"
CONTRACT_TYPE = "required_gate_idempotence_containment_task_guard_contract_v0"
AUDIT_ARCH_X86_64 = 0xC000003E
X32_SYSCALL_BIT = 0x40000000
ALLOW = 0x7FFF0000
KILL_PROCESS = 0x80000000
CLONE_NUMBER = 56
L_TO_R_FLAGS = 0x7E020011
R_TO_T_FLAGS = 0x01200011
BLOCKED_SYSCALLS = {
    "fork": 57, "vfork": 58, "io_uring_setup": 425,
    "io_uring_enter": 426, "io_uring_register": 427, "clone3": 435,
}
BARRIER_TOKEN = b"PULSEv0\n"
FULL_SEALS = 15
MAX_PROGRAM_INSTRUCTIONS = 4096


class GuardError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(value, code):
    if not value:
        raise GuardError(code)


def _uint(value, bits, code):
    _need(type(value) is int and 0 <= value < (1 << bits), code)
    return value


def canonical(value):
    """Encode finite JSON data without invoking user-selected executables."""
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
    except (TypeError, ValueError, RecursionError) as exc:
        raise GuardError("containment_task_guard_json_invalid") from exc


def binding(raw):
    _need(type(raw) is bytes, "containment_task_guard_binding_bytes")
    return {"size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _assemble(operations):
    """Resolve only forward classic-BPF labels; never patch bytecode by hand."""
    labels, instructions = {}, []
    for operation in operations:
        if operation[0] == "label":
            _need(operation[1] not in labels, "containment_task_guard_duplicate_label")
            labels[operation[1]] = len(instructions)
        else:
            instructions.append(operation)

    def distance(label, index):
        _need(label in labels, "containment_task_guard_missing_label")
        result = labels[label] - index - 1
        _need(0 <= result <= 255, "containment_task_guard_jump_range")
        return result

    rows = []
    for index, operation in enumerate(instructions):
        opcode = operation[0]
        if opcode == "load":
            rows.append((0x20, 0, 0, operation[1]))
        elif opcode in ("equal", "bitset"):
            rows.append((0x15 if opcode == "equal" else 0x45,
                         distance(operation[2], index), distance(operation[3], index),
                         operation[1]))
        elif opcode == "return":
            rows.append((0x06, 0, 0, operation[1]))
        else:
            raise GuardError("containment_task_guard_assembler_opcode")
    return tuple(rows)


def guard_instructions():
    """Build the fixed policy from named forward branches.

    seccomp_data has nr/arch at byte offsets 0/4 and six uint64 arguments
    beginning at offset 16. Both halves of constrained arguments are checked.
    L's unused trailing arguments and the unused sixth argument stay ignored.
    """
    return _assemble((
        ("load", 4),
        ("equal", AUDIT_ARCH_X86_64, "native_nr", "kill"),
        ("label", "native_nr"), ("load", 0),
        ("bitset", X32_SYSCALL_BIT, "kill", "deny_fork"),
        ("label", "deny_fork"), ("equal", 57, "kill", "deny_vfork"),
        ("label", "deny_vfork"), ("equal", 58, "kill", "deny_uring_setup"),
        ("label", "deny_uring_setup"), ("equal", 425, "kill", "deny_uring_enter"),
        ("label", "deny_uring_enter"), ("equal", 426, "kill", "deny_uring_register"),
        ("label", "deny_uring_register"), ("equal", 427, "kill", "deny_clone3"),
        ("label", "deny_clone3"), ("equal", 435, "kill", "select_clone"),
        ("label", "select_clone"), ("equal", 56, "flags_high", "allow"),
        ("label", "flags_high"), ("load", 20),
        ("equal", 0, "stack_low", "kill"),
        ("label", "stack_low"), ("load", 24),
        ("equal", 0, "stack_high", "kill"),
        ("label", "stack_high"), ("load", 28),
        ("equal", 0, "flags_low", "kill"),
        ("label", "flags_low"), ("load", 16),
        ("equal", L_TO_R_FLAGS, "allow", "select_reaper_clone"),
        ("label", "select_reaper_clone"),
        ("equal", R_TO_T_FLAGS, "parent_tid_low", "kill"),
        ("label", "parent_tid_low"), ("load", 32),
        ("equal", 0, "parent_tid_high", "kill"),
        ("label", "parent_tid_high"), ("load", 36),
        ("equal", 0, "tls_low", "kill"),
        ("label", "tls_low"), ("load", 48),
        ("equal", 0, "tls_high", "kill"),
        ("label", "tls_high"), ("load", 52),
        ("equal", 0, "child_tid_low", "kill"),
        ("label", "child_tid_low"), ("load", 40),
        ("equal", 0, "child_tid_high", "allow"),
        ("label", "child_tid_high"), ("load", 44),
        ("equal", 0, "kill", "allow"),
        ("label", "allow"), ("return", ALLOW),
        ("label", "kill"), ("return", KILL_PROCESS),
    ))


def guard_program():
    """Return little-endian Linux x86-64 sock_filter bytes; never install them."""
    return b"".join(struct.pack("<HBBI", *row) for row in guard_instructions())


def inspect_program(raw):
    """Parse and structurally check the supported forward-only BPF subset.

    This is not selected-program admission: a structurally valid substitution
    can have different policy. A consumer must separately compare exact bytes.
    """
    _need(type(raw) is bytes and 0 < len(raw) <= MAX_PROGRAM_INSTRUCTIONS * 8
          and len(raw) % 8 == 0, "containment_task_guard_program_size")
    rows = tuple(struct.iter_unpack("<HBBI", raw))
    allowed_offsets = (0, 4, *range(16, 64, 4))
    for index, (code, jt, jf, word) in enumerate(rows):
        if code == 0x20:
            _need(jt == jf == 0 and word in allowed_offsets and index + 1 < len(rows),
                  "containment_task_guard_load_invalid")
        elif code in (0x15, 0x45):
            _need(index + 1 + jt < len(rows) and index + 1 + jf < len(rows),
                  "containment_task_guard_jump_invalid")
        elif code == 0x06:
            _need(jt == jf == 0 and word in (ALLOW, KILL_PROCESS),
                  "containment_task_guard_return_invalid")
        else:
            raise GuardError("containment_task_guard_program_opcode")
    _need(rows[-1][0] == 0x06, "containment_task_guard_program_fallthrough")
    return rows


def _call(arch, number, args):
    _uint(arch, 32, "containment_task_guard_arch_integer")
    _uint(number, 32, "containment_task_guard_syscall_integer")
    _need(type(args) in (tuple, list) and len(args) == 6,
          "containment_task_guard_arguments_shape")
    snapshot = tuple(args)
    for value in snapshot:
        _uint(value, 64, "containment_task_guard_argument_integer")
    return snapshot


def evaluate_program(program, *, arch, number, args):
    """Interpret supported BPF on synthetic seccomp_data, without native calls."""
    arguments = _call(arch, number, args)
    rows = inspect_program(program)
    data = struct.pack("<IIQ6Q", number, arch, 0, *arguments)
    index, accumulator = 0, 0
    for _ in range(len(rows)):
        code, jt, jf, word = rows[index]
        if code == 0x20:
            accumulator = struct.unpack_from("<I", data, word)[0]
            index += 1
        elif code in (0x15, 0x45):
            matched = accumulator == word if code == 0x15 else bool(accumulator & word)
            index += 1 + (jt if matched else jf)
        else:
            return word
    raise GuardError("containment_task_guard_program_nonterminal")


def evaluate_guard(*, arch, number, args):
    """Evaluate the declaration independently from assembly and bytecode."""
    arguments = _call(arch, number, args)
    if arch != AUDIT_ARCH_X86_64 or number & X32_SYSCALL_BIT:
        return KILL_PROCESS
    if number in (57, 58, 425, 426, 427, 435):
        return KILL_PROCESS
    if number != CLONE_NUMBER:
        return ALLOW
    flags, stack, parent_tid, child_tid, tls, _unused = arguments
    if stack != 0:
        return KILL_PROCESS
    if flags == L_TO_R_FLAGS:
        return ALLOW
    if flags == R_TO_T_FLAGS and parent_tid == tls == 0 and child_tid != 0:
        return ALLOW
    return KILL_PROCESS


def validate_birth_sequence(events):
    """Check two authored call descriptions; establish no runtime evidence.

    Each row has exactly parent, child, syscall_number and arguments. The six
    arguments are raw unsigned 64-bit values. Passing this data check does not
    prove task ownership, observed births, pointer writability or host support.
    """
    _need(type(events) is list and len(events) == 2,
          "containment_task_guard_birth_count")
    expected = (("L", "R", L_TO_R_FLAGS), ("R", "T", R_TO_T_FLAGS))
    for row, (parent, child, flags) in zip(events, expected):
        _need(type(row) is dict
              and set(row) == {"parent", "child", "syscall_number", "arguments"},
              "containment_task_guard_birth_shape")
        _need(type(row["parent"]) is str and type(row["child"]) is str
              and row["parent"] == parent and row["child"] == child,
              "containment_task_guard_birth_role_order")
        args = _call(AUDIT_ARCH_X86_64, row["syscall_number"], row["arguments"])
        _need(row["syscall_number"] == CLONE_NUMBER and args[0] == flags
              and evaluate_guard(arch=AUDIT_ARCH_X86_64, number=CLONE_NUMBER,
                                 args=args) == ALLOW,
              "containment_task_guard_birth_arguments")


def contract_spec():
    """Return fresh authored contract data, not a runtime qualification report."""
    contents = {
        0: binding(b""),
        3: {"size_bytes": 454, "sha256":
            "52757caea06d247ac1cf3433c06974bdecba7ecb069e8759f07a91465c882847"},
        4: {"size_bytes": 9568, "sha256":
            "7a21b2e4d60dc080149d9a919b604e39f6fb29be42d462e979b46d3c439b95ab"},
        5: {"size_bytes": 1160, "sha256":
            "9f3570a87b1fde59299d69d242496cbd9d2f1b1631a40dbc5ed8e4976edfa6ab"},
        6: {"size_bytes": 80248, "sha256":
            "573236e5328ac2ebb08f59ae3a9805b4f8d12bdef14be8af4450d5463294985f"},
    }
    roles = ("empty_stdin", "stdout", "stderr", "arguments", "static_entry",
             "containment_bpf", "original_launcher", "helper_barrier")
    descriptors = [{
        "fd": fd, "role": role,
        "kind": "sealed_regular" if fd in contents else "pipe",
        "access_mode": "O_WRONLY" if fd in (1, 2) else "O_RDONLY",
        "required_status_flags": (1 if fd in (1, 2) else 0)
                                 | (0x800 if fd in (1, 2, 7) else 0),
        "allowed_additional_status_flags": 0x8000 if fd in contents else 0,
        "current_uid_gid_required": True,
        "forbidden_mode_bits": 0o6000 if fd in contents else 0,
        "cloexec": fd in (6, 7),
        "seals": FULL_SEALS if fd in contents else None,
        "offset": 0 if fd in contents else None,
        "content": contents.get(fd),
    } for fd, role in enumerate(roles)]
    return {
        "record_type": CONTRACT_TYPE,
        "record_status": "authored_source_contract",
        "profile": PROFILE,
        "guard": {
            "audit_arch": AUDIT_ARCH_X86_64, "x32_syscall_bit": X32_SYSCALL_BIT,
            "allow_action": ALLOW, "deny_action": KILL_PROCESS,
            "blocked_syscalls": dict(BLOCKED_SYSCALLS),
            "clone_syscall_number": CLONE_NUMBER,
            "clone_contracts": [
                {"parent": "L", "child": "R", "flags": L_TO_R_FLAGS,
                 "child_stack": 0, "parent_tid": "ignored", "child_tid": "ignored",
                 "tls": "ignored", "argument_5": "ignored"},
                {"parent": "R", "child": "T", "flags": R_TO_T_FLAGS,
                 "child_stack": 0, "parent_tid": 0, "child_tid": "nonzero_dynamic",
                 "tls": 0, "argument_5": "ignored"},
            ],
            "program": binding(guard_program()),
            "program_instruction_count": len(guard_instructions()),
            "other_native_syscalls_allowed": True,
            "kernel_enforces_role_order_count": False,
            "kernel_validates_child_tid_identity_or_writability": False,
            "is_containment_policy": False,
        },
        "startup": {
            "helper_source": "tools/required_gate_idempotence_containment_startup_v0.c",
            "helper_argv": ["pulsemech-containment-startup-v0", "<observer-pid>"],
            "cwd": "/", "descriptors": descriptors,
            "credentials": {
                "real_effective_uid_equal": True, "uid_nonzero": True,
                "real_effective_gid_equal": True, "gid_nonzero": True,
                "capget_version": 0x20080522,
                "required_zero_capability_sets": ["effective", "permitted", "inheritable"],
                "capability_bounding_or_ambient_readback_claimed": False,
            },
            "descriptor_roles_require_distinct_objects": True,
            "descriptor_flag_preparation": {
                "normalize_cloexec_and_readback": True,
                "cloexec_clear_fds": [0, 1, 2, 3, 4, 5],
                "cloexec_set_fds": [6, 7],
                "nonblocking_pipe_fds": [1, 2, 7],
                "regular_optional_status_flag": "O_LARGEFILE",
            },
            "input_validation": {
                "content_method": "pread64_size_and_sha256",
                "content_fds": [0, 3, 4, 5, 6],
                "regular_offsets_zero_before_and_after_release": True,
                "metadata_and_content_revalidated_after_release": True,
                "after_release_roster": [0, 1, 2, 3, 4, 5, 6],
            },
            "close_range": {"first": 8, "last": 0xFFFFFFFF, "flags": 0,
                            "unsupported_is_failure": True},
            "parent_death": {
                "signal": 9, "set_and_readback_required": True,
                "expected_parent_checks": ["before_set", "after_set", "after_release"],
                "observer_loss_is_incomplete": True,
            },
            "barrier": {
                "fd": 7, "token_hex": BARRIER_TOKEN.hex(), "require_eof_after_token": True,
                "early_eof_rejected": True, "trailing_bytes_rejected": True,
                "release_requires_consumed_interrupt_stop": True,
                "close_after_release": True, "revalidate_descriptors_0_through_6": True,
                "close_after_revalidation": True,
            },
            "deadline": {
                "clock": "CLOCK_MONOTONIC", "seconds": 30,
                "maximum_hash_read_bytes": 4096,
                "variable_length_loops_and_hash_chunks_check_deadline": True,
                "hash_finish_checks_deadline": True,
                "sha_update_maximum_block_iterations": 65,
                "sha_compression_rounds": 64,
                "fixed_inner_loops_statically_bounded": True,
                "timeout_is_failure": True,
            },
            "error_output": {
                "fd": 2, "validated_nonblocking_fd_required": True,
                "best_effort_raw_fd_revalidation_before_write": True,
                "pipe_and_nonblocking_readback_required": True,
                "maximum_message_bytes": 96, "maximum_write_calls": 1,
                "write_retries": 0, "partial_write_continuation": False,
                "exit_return_traps": True,
            },
            "self_authentication": {
                "observer_identity": False, "tracer_identity": False,
                "barrier_writer_identity": False,
            },
            "full_output_limits_enforced_by": "outer_observer",
            "installation": {
                "after_barrier_release": True,
                "no_new_privs_set_and_readback_required": True,
                "guard_submission_syscall": "prctl(PR_SET_SECCOMP,SECCOMP_MODE_FILTER)",
                "observed_exact_program_and_successful_return_required": True,
                "extra_receipt_fd": False,
            },
            "launcher_exec": {
                "syscall_number": 322, "fd": 6, "path": "", "flags": 0x1000,
                "argv": ["bubblewrap", "--args", "3"],
                "environment": ["LC_ALL=C", "TZ=UTC"], "fallback_allowed": False,
                "maximum_calls": 1, "eintr_retry": False,
            },
        },
        "observer": {
            "ptrace_options": 0x0010001F,
            "strategy": "PTRACE_SEIZE_then_INTERRUPT_then_consumed_stop",
            "subreaper_verified_before_L": True,
            "normal_SIGCHLD_and_single_wait_consumer": True,
            "per_creation_role_order_count_and_arguments_before_restart": True,
            "dynamic_child_tid_writability_and_identity_required": True,
            "expected_birth_event": "PTRACE_EVENT_FORK",
            "newborn_event_join_order_independent": True,
            "newborn_reattach_allowed": False,
            "terminal_T_restarts": 0,
            "cleanup_order": ["T", "R", "L"],
            "cleanup_signal": "pidfd_send_signal(SIGKILL,NULL,0)",
            "cleanup_only_created_owned_identities": True,
            "cleanup_global_trace_adoption_reap_drain": True,
            "fixed_wait_count_is_completion": False,
            "final_pidfd_hangup_and_drained_wait_ledger_required": True,
            "primary_and_cleanup_failures_preserved_separately": True,
        },
        "limits": {
            "attempts": 1, "retries": 0, "max_live_subject_tasks": 3,
            "max_bwrap_birth_events": 2, "max_ordered_trace_events": 8192,
            "setup_wall_seconds": 30, "cleanup_wall_seconds": 5,
            "stdout_bytes": 65536, "stderr_bytes": 4096,
            "capture_payload_bytes": 33554432, "capture_members": 2048,
            "argument_bytes": 4096, "single_control_memory_read_bytes": 65536,
            "aggregate_control_memory_bytes_per_checkpoint": 1048576,
        },
        "qualification_obligations_pending": [
            "fresh_original_source_and_explicit_policy_admission",
            "source_to_executed_helper_binding",
            "same_observer_kernel_image_and_outer_security_selection",
            "nonroot_equal_real_effective_ids_and_non_setuid_launcher",
            "guard_denials_and_two_source_bound_clone_shapes",
            "guard_inheritance_across_exec_and_births",
            "owned_barrier_seize_interrupt_stop_and_parent_loss",
            "per_role_before_restart_validation_and_unordered_birth_notifications",
            "namespace_mount_openat2_and_expected_extra_userns_denial",
            "cross_namespace_proc_memory_register_and_descriptor_observation",
            "separate_R_and_T_containment_filter_submissions",
            "bounded_cancellation_and_owned_graph_cleanup",
            "separate_owner_execution_authorization",
        ],
        "synthetic_data_is_runtime_evidence": False,
        "native_qualifier_implemented": False,
        "host_environment_qualified": False,
        "native_acquisition_performed": False,
        "execution_ready": False,
        "execution_authorized": False,
        "b2_complete": False,
        "metric_pass": None,
        "authority_effect": "none",
    }
