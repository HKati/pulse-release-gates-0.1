#!/usr/bin/env python3
"""Verify the bounded containment startup source contract as data only.

The helper, guard builder and compiled ELF are never imported or executed.
Freshly reconstruct the unchanged prerequisite plan from its original carriers,
then compare the new authored contract with independently reviewed policy and
source identities. A static ELF check establishes shape and selected section
bytes only; it does not authenticate a build or qualify a host.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import struct
import sys
from types import FunctionType
import warnings

import jsonschema
try:
    from referencing import Registry
    from referencing.exceptions import Unresolvable
except ImportError:
    Registry = None
    class Unresolvable(Exception):
        """No modern reference resolver is installed in this environment."""

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_containment_entry_plan_v0 as prior

_PRIOR_VERIFY_CODE = prior.verify_plan.__code__
_PRIOR_VERIFY_GLOBALS = dict(prior.verify_plan.__globals__)


ROOT = Path(__file__).resolve().parents[1]
TOOL_REL = "tools/check_required_gate_idempotence_containment_task_guard_v0.py"
CORE_REL = "tools/required_gate_idempotence_containment_task_guard_v0.py"
HELPER_REL = "tools/required_gate_idempotence_containment_startup_v0.c"
SCHEMA_REL = "schemas/required_gate_idempotence_containment_task_guard_v0.schema.json"
CONTRACT_REL = "docs/compute/required_gate_idempotence_containment_task_guard_v0/contract_v0.json"
PLAN_REL = "docs/compute/required_gate_idempotence_containment_entry_plan_v0/plan_v0.json"
INVENTORY_REL = prior.INVENTORY_REL
PROFILE = "linux_x86_64_original_bwrap_minimal_entry_exec_stop_v0"
CONTROL_BYTES = 1024 * 1024
ELF_BYTES = 256 * 1024
ELF_PAGE_BYTES = 4096
SCHEMA_ID = "urn:pulsemech:required-gate-idempotence-containment-task-guard:v0"
BASE_COMMIT = "92886ff5c6e86729d5a2837c18710d4c274c8fd7"
PRIOR_IDENTITIES = {
    prior.TOOL_REL: {"sha256": "c8f3f70b1780dc14d8e8b6ef684714bbab6be8d691d5685558424610d1231167", "size_bytes": 154932},
    prior.SCHEMA_REL: {"sha256": "58f46b593fae80fe25ba1911b5aed5134a98d04f5d371e2bdeaebb680c9f28a3", "size_bytes": 65002},
    PLAN_REL: {"sha256": "dee57c7b8e4abf86227404ba4c9efc51ced69633e1128295a2d2cef8b78318e0", "size_bytes": 21284},
    INVENTORY_REL: {"sha256": "80190d88ac4e0b654cd8a315b67062aab171a24f81d9fa99108c6d7351930fd0", "size_bytes": 21350},
    "tools/required_gate_idempotence_entry_task_guard_v0.py": {
        "sha256": "7d739ea58aa248c6d1785882847ee1d45b9e32925514cc7b0cf510558fbdf83d", "size_bytes": 23130},
    "tools/check_required_gate_idempotence_entry_task_guard_v0.py": {
        "sha256": "25fa48cc1824c0641fe0ba9265fbe3c698a3f36b19cb29adf212ffa8b049b58e", "size_bytes": 24395},
}
CURRENT_SOURCES = tuple(sorted((TOOL_REL, CORE_REL, HELPER_REL, SCHEMA_REL)))
# Filled only after source review; caller-supplied or rehashed contract pins
# never choose a different helper or guard implementation.
REVIEWED_SOURCES = {'tools/required_gate_idempotence_containment_startup_v0.c': {'sha256': '0ae15697c524fc13c2ac0f04d2a1c1d44c7e5952e6b285a4add2799a740d4409',
                                                              'size_bytes': 27461},
 'tools/required_gate_idempotence_containment_task_guard_v0.py': {'sha256': 'b073d370c8081337cb658929a53802bdbfa73d4f0bf4bf677dc716ef9dd76802',
                                                                  'size_bytes': 19568}}
EXPECTED_GUARD_HEX = (
    "20000000040000001500001f3e0000c0200000000000000045001d0000000040"
    "15001c003900000015001b003a00000015001a00a901000015001900aa010000"
    "15001800ab01000015001700b301000015000015380000002000000014000000"
    "150000140000000020000000180000001500001200000000200000001c000000"
    "1500001000000000200000001000000015000d001100027e1500000d11002001"
    "20000000200000001500000b0000000020000000240000001500000900000000"
    "2000000030000000150000070000000020000000340000001500000500000000"
    "20000000280000001500000200000000200000002c0000001500010000000000"
    "060000000000ff7f0600000000000080"
)
# Independently reviewed literal policy. Verification never imports the core.
POLICY = {'authority_effect': 'none',
 'b2_complete': False,
 'execution_authorized': False,
 'execution_ready': False,
 'guard': {'allow_action': 2147418112,
           'audit_arch': 3221225534,
           'blocked_syscalls': {'clone3': 435,
                                'fork': 57,
                                'io_uring_enter': 426,
                                'io_uring_register': 427,
                                'io_uring_setup': 425,
                                'vfork': 58},
           'clone_contracts': [{'argument_5': 'ignored',
                                'child': 'R',
                                'child_stack': 0,
                                'child_tid': 'ignored',
                                'flags': 2114060305,
                                'parent': 'L',
                                'parent_tid': 'ignored',
                                'tls': 'ignored'},
                               {'argument_5': 'ignored',
                                'child': 'T',
                                'child_stack': 0,
                                'child_tid': 'nonzero_dynamic',
                                'flags': 18874385,
                                'parent': 'R',
                                'parent_tid': 0,
                                'tls': 0}],
           'clone_syscall_number': 56,
           'deny_action': 2147483648,
           'is_containment_policy': False,
           'kernel_enforces_role_order_count': False,
           'kernel_validates_child_tid_identity_or_writability': False,
           'other_native_syscalls_allowed': True,
           'program': {'sha256': 'cc75cb083fb0f6b235eb429384dfb5aaffdd4653891eb2010cd0fd5b6939a51f',
                       'size_bytes': 272},
           'program_instruction_count': 34,
           'x32_syscall_bit': 1073741824},
 'host_environment_qualified': False,
 'limits': {'aggregate_control_memory_bytes_per_checkpoint': 1048576,
            'argument_bytes': 4096,
            'attempts': 1,
            'capture_members': 2048,
            'capture_payload_bytes': 33554432,
            'cleanup_wall_seconds': 5,
            'max_bwrap_birth_events': 2,
            'max_live_subject_tasks': 3,
            'max_ordered_trace_events': 8192,
            'retries': 0,
            'setup_wall_seconds': 30,
            'single_control_memory_read_bytes': 65536,
            'stderr_bytes': 4096,
            'stdout_bytes': 65536},
 'metric_pass': None,
 'native_acquisition_performed': False,
 'native_qualifier_implemented': False,
 'observer': {'cleanup_global_trace_adoption_reap_drain': True,
              'cleanup_only_created_owned_identities': True,
              'cleanup_order': ['T', 'R', 'L'],
              'cleanup_signal': 'pidfd_send_signal(SIGKILL,NULL,0)',
              'dynamic_child_tid_writability_and_identity_required': True,
              'expected_birth_event': 'PTRACE_EVENT_FORK',
              'final_pidfd_hangup_and_drained_wait_ledger_required': True,
              'fixed_wait_count_is_completion': False,
              'newborn_event_join_order_independent': True,
              'newborn_reattach_allowed': False,
              'normal_SIGCHLD_and_single_wait_consumer': True,
              'per_creation_role_order_count_and_arguments_before_restart': True,
              'primary_and_cleanup_failures_preserved_separately': True,
              'ptrace_options': 1048607,
              'strategy': 'PTRACE_SEIZE_then_INTERRUPT_then_consumed_stop',
              'subreaper_verified_before_L': True,
              'terminal_T_restarts': 0},
 'profile': 'linux_x86_64_original_bwrap_minimal_entry_task_guard_v0',
 'qualification_obligations_pending': ['fresh_original_source_and_explicit_policy_admission',
                                       'source_to_executed_helper_binding',
                                       'same_observer_kernel_image_and_outer_security_selection',
                                       'nonroot_equal_real_effective_ids_and_non_setuid_launcher',
                                       'guard_denials_and_two_source_bound_clone_shapes',
                                       'guard_inheritance_across_exec_and_births',
                                       'owned_barrier_seize_interrupt_stop_and_parent_loss',
                                       'per_role_before_restart_validation_and_unordered_birth_notifications',
                                       'namespace_mount_openat2_and_expected_extra_userns_denial',
                                       'cross_namespace_proc_memory_register_and_descriptor_observation',
                                       'separate_R_and_T_containment_filter_submissions',
                                       'bounded_cancellation_and_owned_graph_cleanup',
                                       'separate_owner_execution_authorization'],
 'record_status': 'authored_source_contract',
 'record_type': 'required_gate_idempotence_containment_task_guard_contract_v0',
 'startup': {'barrier': {'close_after_release': True,
                         'close_after_revalidation': True,
                         'early_eof_rejected': True,
                         'fd': 7,
                         'release_requires_consumed_interrupt_stop': True,
                         'require_eof_after_token': True,
                         'revalidate_descriptors_0_through_6': True,
                         'token_hex': '50554c534576300a',
                         'trailing_bytes_rejected': True},
             'close_range': {'first': 8,
                             'flags': 0,
                             'last': 4294967295,
                             'unsupported_is_failure': True},
             'credentials': {'capability_bounding_or_ambient_readback_claimed': False,
                             'capget_version': 537396514,
                             'gid_nonzero': True,
                             'real_effective_gid_equal': True,
                             'real_effective_uid_equal': True,
                             'required_zero_capability_sets': ['effective', 'permitted', 'inheritable'],
                             'uid_nonzero': True},
             'cwd': '/',
             'deadline': {'clock': 'CLOCK_MONOTONIC',
                          'fixed_inner_loops_statically_bounded': True,
                          'hash_finish_checks_deadline': True,
                          'maximum_hash_read_bytes': 4096,
                          'seconds': 30,
                          'sha_compression_rounds': 64,
                          'sha_update_maximum_block_iterations': 65,
                          'timeout_is_failure': True,
                          'variable_length_loops_and_hash_chunks_check_deadline': True},
             'descriptor_flag_preparation': {'cloexec_clear_fds': [0, 1, 2, 3, 4, 5],
                                             'cloexec_set_fds': [6, 7],
                                             'nonblocking_pipe_fds': [1, 2, 7],
                                             'normalize_cloexec_and_readback': True,
                                             'regular_optional_status_flag': 'O_LARGEFILE'},
             'descriptor_roles_require_distinct_objects': True,
             'descriptors': [{'access_mode': 'O_RDONLY',
                              'allowed_additional_status_flags': 32768,
                              'cloexec': False,
                              'content': {'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
                                          'size_bytes': 0},
                              'current_uid_gid_required': True,
                              'fd': 0,
                              'forbidden_mode_bits': 3072,
                              'kind': 'sealed_regular',
                              'offset': 0,
                              'required_status_flags': 0,
                              'role': 'empty_stdin',
                              'seals': 15},
                             {'access_mode': 'O_WRONLY',
                              'allowed_additional_status_flags': 0,
                              'cloexec': False,
                              'content': None,
                              'current_uid_gid_required': True,
                              'fd': 1,
                              'forbidden_mode_bits': 0,
                              'kind': 'pipe',
                              'offset': None,
                              'required_status_flags': 2049,
                              'role': 'stdout',
                              'seals': None},
                             {'access_mode': 'O_WRONLY',
                              'allowed_additional_status_flags': 0,
                              'cloexec': False,
                              'content': None,
                              'current_uid_gid_required': True,
                              'fd': 2,
                              'forbidden_mode_bits': 0,
                              'kind': 'pipe',
                              'offset': None,
                              'required_status_flags': 2049,
                              'role': 'stderr',
                              'seals': None},
                             {'access_mode': 'O_RDONLY',
                              'allowed_additional_status_flags': 32768,
                              'cloexec': False,
                              'content': {'sha256': '52757caea06d247ac1cf3433c06974bdecba7ecb069e8759f07a91465c882847',
                                          'size_bytes': 454},
                              'current_uid_gid_required': True,
                              'fd': 3,
                              'forbidden_mode_bits': 3072,
                              'kind': 'sealed_regular',
                              'offset': 0,
                              'required_status_flags': 0,
                              'role': 'arguments',
                              'seals': 15},
                             {'access_mode': 'O_RDONLY',
                              'allowed_additional_status_flags': 32768,
                              'cloexec': False,
                              'content': {'sha256': '7a21b2e4d60dc080149d9a919b604e39f6fb29be42d462e979b46d3c439b95ab',
                                          'size_bytes': 9568},
                              'current_uid_gid_required': True,
                              'fd': 4,
                              'forbidden_mode_bits': 3072,
                              'kind': 'sealed_regular',
                              'offset': 0,
                              'required_status_flags': 0,
                              'role': 'static_entry',
                              'seals': 15},
                             {'access_mode': 'O_RDONLY',
                              'allowed_additional_status_flags': 32768,
                              'cloexec': False,
                              'content': {'sha256': '9f3570a87b1fde59299d69d242496cbd9d2f1b1631a40dbc5ed8e4976edfa6ab',
                                          'size_bytes': 1160},
                              'current_uid_gid_required': True,
                              'fd': 5,
                              'forbidden_mode_bits': 3072,
                              'kind': 'sealed_regular',
                              'offset': 0,
                              'required_status_flags': 0,
                              'role': 'containment_bpf',
                              'seals': 15},
                             {'access_mode': 'O_RDONLY',
                              'allowed_additional_status_flags': 32768,
                              'cloexec': True,
                              'content': {'sha256': '573236e5328ac2ebb08f59ae3a9805b4f8d12bdef14be8af4450d5463294985f',
                                          'size_bytes': 80248},
                              'current_uid_gid_required': True,
                              'fd': 6,
                              'forbidden_mode_bits': 3072,
                              'kind': 'sealed_regular',
                              'offset': 0,
                              'required_status_flags': 0,
                              'role': 'original_launcher',
                              'seals': 15},
                             {'access_mode': 'O_RDONLY',
                              'allowed_additional_status_flags': 0,
                              'cloexec': True,
                              'content': None,
                              'current_uid_gid_required': True,
                              'fd': 7,
                              'forbidden_mode_bits': 0,
                              'kind': 'pipe',
                              'offset': None,
                              'required_status_flags': 2048,
                              'role': 'helper_barrier',
                              'seals': None}],
             'error_output': {'best_effort_raw_fd_revalidation_before_write': True,
                              'exit_return_traps': True,
                              'fd': 2,
                              'maximum_message_bytes': 96,
                              'maximum_write_calls': 1,
                              'partial_write_continuation': False,
                              'pipe_and_nonblocking_readback_required': True,
                              'validated_nonblocking_fd_required': True,
                              'write_retries': 0},
             'full_output_limits_enforced_by': 'outer_observer',
             'helper_argv': ['pulsemech-containment-startup-v0', '<observer-pid>'],
             'helper_source': 'tools/required_gate_idempotence_containment_startup_v0.c',
             'input_validation': {'after_release_roster': [0, 1, 2, 3, 4, 5, 6],
                                  'content_fds': [0, 3, 4, 5, 6],
                                  'content_method': 'pread64_size_and_sha256',
                                  'metadata_and_content_revalidated_after_release': True,
                                  'regular_offsets_zero_before_and_after_release': True},
             'installation': {'after_barrier_release': True,
                              'extra_receipt_fd': False,
                              'guard_submission_syscall': 'prctl(PR_SET_SECCOMP,SECCOMP_MODE_FILTER)',
                              'no_new_privs_set_and_readback_required': True,
                              'observed_exact_program_and_successful_return_required': True},
             'launcher_exec': {'argv': ['bubblewrap', '--args', '3'],
                               'eintr_retry': False,
                               'environment': ['LC_ALL=C', 'TZ=UTC'],
                               'fallback_allowed': False,
                               'fd': 6,
                               'flags': 4096,
                               'maximum_calls': 1,
                               'path': '',
                               'syscall_number': 322},
             'parent_death': {'expected_parent_checks': ['before_set', 'after_set', 'after_release'],
                              'observer_loss_is_incomplete': True,
                              'set_and_readback_required': True,
                              'signal': 9},
             'self_authentication': {'barrier_writer_identity': False,
                                     'observer_identity': False,
                                     'tracer_identity': False}},
 'synthetic_data_is_runtime_evidence': False}
BUILD_SELECTION = {
    "kind": "compile_only_recipe_not_authenticated_toolchain",
    "compiler": "gcc",
    "flags": ["-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
              "-ffreestanding", "-fno-builtin", "-fno-stack-protector",
              "-fno-pie", "-no-pie", "-fno-asynchronous-unwind-tables",
              "-fno-unwind-tables", "-nostdlib", "-static",
              "-Wl,--build-id=none", "-Wl,-z,noexecstack", "-Wl,-e,_start"],
    "source": HELPER_REL,
    "entry_symbol": "_start",
    "guard_section": ".pulse_task_guard",
    "output_is_executed": False,
    "compiler_runtime_closure_selected": False,
    "native_qualification_satisfied_by_compilation": False,
}
BOUNDARY = {
    "startup_source_contract_verified": True,
    "guard_policy_bytes_verified": True,
    "prerequisite_plan_reconstructed": True,
    "native_qualifier_implemented": False,
    "native_collector_implemented": False,
    "host_environment_qualified": False,
    "guard_installation_observed": False,
    "helper_execution_observed": False,
    "original_launcher_executed": False,
    "containment_observed": False,
    "native_acquisition_performed": False,
    "source_binary_equivalence_verified": False,
    "authenticated_build_provenance": False,
    "complete_runtime_closure_verified": False,
    "selected_runtime_admitted": False,
    "execution_ready": False,
    "execution_authorized": False,
    "production_gate_eligible": False,
    "b2_complete": False,
    "metric_pass": None,
    "authority_effect": "none",
    "whole_runtime_issue": {"number": 2879, "keep_open": True},
}


class ContractError(ValueError):
    """Stable rejection code without inspected bytes or local path disclosure."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise ContractError(code)


def binding(raw):
    _need(type(raw) is bytes, "containment_task_guard_bytes_required")
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def canonical(value):
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ContractError("containment_task_guard_json_value") from exc


def parse(raw):
    try:
        return prior.parse(raw)
    except prior.PlanError as exc:
        raise ContractError(exc.code.replace("containment_plan_", "containment_task_guard_")) from exc


def _same(actual, expected, code):
    _need(canonical(actual) == canonical(expected), code)


def _bound(raw, expected, code):
    _need(type(raw) is bytes and len(raw) == expected["size_bytes"], code)
    _need(hashlib.sha256(raw).hexdigest() == expected["sha256"], code)


def _read_file(path, limit=CONTROL_BYTES):
    try:
        return prior._read_file(path, limit)
    except prior.PlanError as exc:
        raise ContractError(exc.code.replace("containment_plan_", "containment_task_guard_")) from exc


def _write_new(path, raw):
    try:
        return prior._write_new(path, raw)
    except prior.PlanError as exc:
        raise ContractError(exc.code.replace("containment_plan_", "containment_task_guard_")) from exc


def _source_snapshot():
    names = set(CURRENT_SOURCES) | set(PRIOR_IDENTITIES)
    sources = {name: _read_file(ROOT / name) for name in sorted(names)}
    for name, selected in {**PRIOR_IDENTITIES, **REVIEWED_SOURCES}.items():
        _bound(sources[name], selected, "containment_task_guard_reviewed_source_changed")
    _need(set(REVIEWED_SOURCES) == {CORE_REL, HELPER_REL},
          "containment_task_guard_source_selection_missing")
    return sources


def load_inputs(root=ROOT):
    root = Path(root)
    names = {**prior.INPUT_BINDINGS, PLAN_REL: PRIOR_IDENTITIES[PLAN_REL],
             INVENTORY_REL: PRIOR_IDENTITIES[INVENTORY_REL]}
    return {name: _read_file(root / name, selected["size_bytes"])
            for name, selected in names.items()}


def _closed_validator(schema):
    # requirements.txt permits jsonschema>=4.0. The registry constructor is
    # newer; do not add an undeclared dependency on it or enable retrieval in
    # the supported legacy branch. Both branches also receive only local refs.
    if Registry is not None and "registry" in inspect.signature(
            jsonschema.Draft202012Validator).parameters:
        return jsonschema.Draft202012Validator(schema, registry=Registry())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        resolver_type = getattr(jsonschema, "RefResolver", None)
    _need(resolver_type is not None, "containment_task_guard_schema_resolver_unavailable")

    class ClosedResolver(resolver_type):
        def resolve_remote(self, uri):
            raise ContractError("containment_task_guard_schema_reference")

        def resolve_fragment(self, document, fragment):
            try:
                return super().resolve_fragment(document, fragment)
            except Exception as exc:
                # Legacy releases use a different reference-error hierarchy.
                raise ContractError("containment_task_guard_schema_reference") from exc

    resolver = ClosedResolver.from_schema(schema, cache_remote=False)
    return jsonschema.Draft202012Validator(schema, resolver=resolver)


def _validate(schema, definition, value):
    # A modified schema is still untrusted data. Do not let a reference cause
    # implicit network retrieval before fixed-policy/source comparison fails.
    _need(type(schema) is dict and schema.get("$schema") ==
          "https://json-schema.org/draft/2020-12/schema" and
          schema.get("$id") == SCHEMA_ID, "containment_task_guard_schema_identity")
    _need(definition in ("contract", "report"), "containment_task_guard_schema_definition")
    pending, count = [(schema, ())], 0
    while pending:
        node, path = pending.pop()
        count += 1
        _need(len(path) <= 48 and count <= 100000, "containment_task_guard_schema_complexity")
        if type(node) is dict:
            _need("$id" not in node or node is schema, "containment_task_guard_schema_reference")
            _need(not {"$dynamicRef", "$recursiveRef"} & set(node),
                  "containment_task_guard_schema_reference")
            if "$ref" in node:
                # The selected schema needs only its two top-level alternatives.
                # No reference inside a definition is needed or accepted, so
                # cycles cannot recurse through an otherwise local whitelist.
                _need((path, node["$ref"]) in (
                    (("oneOf", 0), "#/$defs/contract"),
                    (("oneOf", 1), "#/$defs/report")),
                      "containment_task_guard_schema_reference")
            pending.extend((child, path + (key,)) for key, child in node.items())
        elif type(node) is list:
            pending.extend((child, path + (index,)) for index, child in enumerate(node))
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        selected = {"$schema": schema["$schema"], "$defs": schema["$defs"],
                    "$ref": "#/$defs/" + definition}
        _closed_validator(selected).validate(value)
    except (jsonschema.SchemaError, jsonschema.ValidationError, Unresolvable,
            KeyError, TypeError, RecursionError) as exc:
        raise ContractError("containment_task_guard_" + definition + "_schema") from exc


def expected_guard_program():
    """Independent reviewed bytes, not an import of the generator/installer."""
    raw = bytes.fromhex(EXPECTED_GUARD_HEX)
    _need(0 < len(raw) <= 4096 and len(raw) % 8 == 0,
          "containment_task_guard_golden_program")
    return raw


def _contract(sources):
    program = expected_guard_program()
    return {
        "record_type": "required_gate_idempotence_containment_task_guard_contract_v0",
        "record_status": "authored_source_contract",
        "profile": PROFILE,
        "base_commit": BASE_COMMIT,
        "policy": copy.deepcopy(POLICY),
        "task_guard_program": {**binding(program), "instruction_count": len(program) // 8,
                               "encoding": "linux_classic_bpf_le_sock_filter", "hex": program.hex()},
        "build_selection": copy.deepcopy(BUILD_SELECTION),
        "prerequisite_plan": {"path": PLAN_REL, **PRIOR_IDENTITIES[PLAN_REL]},
        "prerequisite_source_inventory": {"path": INVENTORY_REL, **PRIOR_IDENTITIES[INVENTORY_REL]},
        "source_files": [{"path": name, **binding(raw)} for name, raw in sorted(sources.items())],
        "boundary": {**copy.deepcopy(BOUNDARY), "startup_source_contract_verified": False,
                     "guard_policy_bytes_verified": False, "prerequisite_plan_reconstructed": False},
    }


def derive_contract():
    """Materialize the authored selection. This supplies no acceptance verdict."""
    sources = _source_snapshot()
    result = _contract(sources)
    _need(_source_snapshot() == sources, "containment_task_guard_implementation_changed")
    return result


def _verify_prerequisite(sources, inputs):
    """Run the unchanged prior verification code on its pinned source snapshot.

    The prior checker normally rereads its own schema twice. Giving only this
    function a private globals dictionary supplies the already pinned immutable
    bytes instead, without monkeypatching the imported module or changing its
    acceptance logic. Otherwise a file replacement between the initial pin
    check and that reread could expose an unselected schema to its validator.
    The remaining prior reconstruction helpers operate on passed bytes; the
    outer source snapshot is checked again before publishing the new report.
    """
    implementation = {name: sources[name] for name in (prior.TOOL_REL, prior.SCHEMA_REL)}
    namespace = dict(_PRIOR_VERIFY_GLOBALS)
    namespace["_implementation"] = lambda: dict(implementation)
    verify = FunctionType(_PRIOR_VERIFY_CODE, namespace, "verify_plan")
    return verify(plan_bytes=inputs[PLAN_REL],
                  expected_plan_sha256=PRIOR_IDENTITIES[PLAN_REL]["sha256"],
                  source_inventory_bytes=inputs[INVENTORY_REL],
                  expected_source_inventory_sha256=PRIOR_IDENTITIES[INVENTORY_REL]["sha256"],
                  inputs={name: inputs[name] for name in prior.INPUT_BINDINGS})


def verify_contract(*, contract_bytes, expected_contract_sha256, inputs):
    _need(type(expected_contract_sha256) is str and
          re.fullmatch(r"[0-9a-f]{64}", expected_contract_sha256) is not None,
          "containment_task_guard_expected_digest")
    value = parse(contract_bytes)
    _need(binding(contract_bytes)["sha256"] == expected_contract_sha256,
          "containment_task_guard_digest_mismatch")
    sources = _source_snapshot()
    schema = parse(sources[SCHEMA_REL])
    _validate(schema, "contract", value)
    _same(value, _contract(sources), "containment_task_guard_reviewed_contract_changed")
    roster = set(prior.INPUT_BINDINGS) | {PLAN_REL, INVENTORY_REL}
    _need(type(inputs) is dict, "containment_task_guard_input_roster")
    inputs = dict(inputs)
    _need(set(inputs) == roster and
          all(type(key) is str and type(raw) is bytes for key, raw in inputs.items()),
          "containment_task_guard_input_roster")
    for name in (PLAN_REL, INVENTORY_REL):
        _bound(inputs[name], PRIOR_IDENTITIES[name], "containment_task_guard_prerequisite_changed")
        _need(inputs[name] == sources[name], "containment_task_guard_prerequisite_source_join")
    try:
        prerequisite = _verify_prerequisite(sources, inputs)
    except prior.PlanError as exc:
        raise ContractError("containment_task_guard_prerequisite_" + exc.code) from exc
    _need(prerequisite["record_status"] == "verified_design" and
          prerequisite["derived"]["clone_flags"] == ["0x7e020011", "0x01200011"] and
          prerequisite["derived"]["ptrace_options_hex"] == "0x0010001f" and
          prerequisite["boundary"]["execution_authorized"] is False,
          "containment_task_guard_prerequisite_relationship")
    report = {
        "record_type": "required_gate_idempotence_containment_task_guard_verification_v0",
        "record_status": "verified_source_contract", "profile": PROFILE,
        "contract": binding(contract_bytes), "base_commit": BASE_COMMIT,
        "prerequisite_report": binding(prior.canonical(prerequisite)),
        "input_files": [{"path": name, **binding(raw)} for name, raw in sorted(inputs.items())],
        "implementation_sources": [{"path": name, **binding(raw)} for name, raw in sorted(sources.items())],
        "task_guard_program": {**binding(expected_guard_program()),
                               "instruction_count": len(expected_guard_program()) // 8},
        "build_selection": copy.deepcopy(BUILD_SELECTION),
        "boundary": copy.deepcopy(BOUNDARY),
    }
    _validate(schema, "report", report)
    _need(_source_snapshot() == sources, "containment_task_guard_implementation_changed")
    return report


def verify_compiled_helper(elf_bytes, *, expected_elf_sha256):
    """Inspect one compiler output as data; never load or run the helper.

    Accept only a bounded static ELF with one read-only selected guard section.
    This deliberately cannot claim that executable instructions implement the
    reviewed C: a future authenticated build/admission must bind that relation.
    """
    raw = elf_bytes
    _need(type(raw) is bytes and 64 <= len(raw) <= ELF_BYTES,
          "containment_task_guard_elf_size")
    _need(type(expected_elf_sha256) is str and
          re.fullmatch(r"[0-9a-f]{64}", expected_elf_sha256) is not None and
          binding(raw)["sha256"] == expected_elf_sha256, "containment_task_guard_elf_digest")
    fields = struct.unpack_from("<16sHHIQQQIHHHHHH", raw)
    ident, kind, machine, version, entry, phoff, shoff, flags, ehsize, phsize, phcount, shsize, shcount, shstrings = fields
    _need(ident[:7] == b"\x7fELF\x02\x01\x01" and not any(ident[7:]) and
          kind == 2 and machine == 62 and version == 1 and flags == 0 and ehsize == 64 and
          phsize == 56 and 0 < phcount <= 16 and 64 <= phoff and phoff + phcount * 56 <= len(raw) and
          shsize == 64 and 0 < shcount <= 64 and 64 <= shoff and shoff + shcount * 64 <= len(raw) and
          0 < shstrings < shcount, "containment_task_guard_elf_header")
    loads, stacks = [], []
    for index in range(phcount):
        ptype, mode, offset, address, physical, size, memory, alignment = struct.unpack_from(
            "<IIQQQQQQ", raw, phoff + index * 56)
        _need(offset <= len(raw) and size <= len(raw) - offset and mode <= 7 and
              ptype not in (2, 3, 7), "containment_task_guard_elf_segment")
        if ptype == 1:
            _need(0 < memory <= ELF_BYTES and size <= memory and address + memory < 2 ** 64 and
                  mode & 3 != 3 and mode & 4 != 0 and
                  address % ELF_PAGE_BYTES == offset % ELF_PAGE_BYTES and
                  (alignment in (0, 1) or alignment <= 2 ** 21 and
                   alignment & (alignment - 1) == 0 and address % alignment == offset % alignment),
                  "containment_task_guard_elf_load")
            for old in loads:
                _need(address + memory <= old[1] or old[1] + old[3] <= address,
                      "containment_task_guard_elf_load_overlap")
                _need(size == 0 or old[2] == 0 or offset + size <= old[0] or old[0] + old[2] <= offset,
                      "containment_task_guard_elf_load_alias")
                page_start = address // ELF_PAGE_BYTES
                page_end = (address + memory + ELF_PAGE_BYTES - 1) // ELF_PAGE_BYTES
                old_start = old[1] // ELF_PAGE_BYTES
                old_end = (old[1] + old[3] + ELF_PAGE_BYTES - 1) // ELF_PAGE_BYTES
                _need(page_end <= old_start or old_end <= page_start,
                      "containment_task_guard_elf_load_page_overlap")
            loads.append((offset, address, size, memory, mode))
        elif ptype == 0x6474e551:
            stacks.append((mode, size, memory))
    _need(loads and stacks == [(6, 0, 0)] and
          sum(address <= entry < address + size and mode & 1 != 0
              for _, address, size, _, mode in loads) == 1,
          "containment_task_guard_elf_entry_or_stack")
    sections = [struct.unpack_from("<IIQQQQIIQQ", raw, shoff + index * 64)
                for index in range(shcount)]
    _need(sections[0] == (0,) * 10, "containment_task_guard_elf_null_section")
    names_section = sections[shstrings]
    _need(names_section[1] == 3 and names_section[2] == 0 and
          names_section[4] <= len(raw) and 0 < names_section[5] <= 8192 and
          names_section[5] <= len(raw) - names_section[4], "containment_task_guard_elf_string_table")
    names = raw[names_section[4]:names_section[4] + names_section[5]]
    _need(names[:1] == b"\0" and names[-1:] == b"\0", "containment_task_guard_elf_string_table")
    seen, guard = set(), None
    for section in sections[1:]:
        name_at, stype, sflags, address, offset, size, link, info, alignment, entsize = section
        _need(0 < name_at < len(names) and link < shcount and
              (alignment in (0, 1) or alignment <= 2 ** 21 and
               alignment & (alignment - 1) == 0),
              "containment_task_guard_elf_section_header")
        end = names.find(b"\0", name_at)
        _need(name_at < end <= name_at + 128, "containment_task_guard_elf_section_name")
        name = names[name_at:end]
        _need(name not in seen and all(32 < byte < 127 for byte in name),
              "containment_task_guard_elf_section_duplicate")
        seen.add(name)
        _need(offset <= len(raw) and (stype == 8 or size <= len(raw) - offset),
              "containment_task_guard_elf_section_extent")
        _need(stype not in (4, 6, 9) and not (sflags & 0x400),
              "containment_task_guard_elf_dynamic_or_tls_section")
        if sflags & 2:
            count = sum(a <= address and address + size <= a + m and
                        (stype == 8 or o + address - a == offset and address + size <= a + n) and
                        (not sflags & 1 or mode & 2) and (not sflags & 4 or mode & 1)
                        for o, a, n, m, mode in loads)
            _need(count == 1, "containment_task_guard_elf_section_mapping")
        if name == b".pulse_task_guard":
            _need(stype == 1 and sflags == 2 and alignment >= 4 and entsize == 0 and
                  any(a <= address and address + size <= a + n and mode == 4 and
                      o + address - a == offset for o, a, n, m, mode in loads),
                  "containment_task_guard_elf_guard_mapping")
            guard = raw[offset:offset + size]
    _need(guard == expected_guard_program(), "containment_task_guard_elf_guard_bytes")
    return {
        "record_type": "required_gate_idempotence_containment_startup_compiled_shape_v0",
        "helper_elf": binding(raw), "entry_virtual_address": entry,
        "machine": "EM_X86_64", "elf_type": "ET_EXEC", "load_segments": len(loads),
        "guard_section": {"name": ".pulse_task_guard", **binding(guard)},
        "static_shape_verified": True, "guard_section_bytes_verified": True,
        "source_binary_equivalence_verified": False, "authenticated_build_provenance": False,
        "host_environment_qualified": False, "native_execution_performed": False,
        "execution_authorized": False, "metric_pass": None, "authority_effect": "none",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--expected-contract-sha256", required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        _need(not os.path.lexists(args.out), "containment_task_guard_output_exists")
        raw = _read_file(args.contract)
        report = verify_contract(contract_bytes=raw,
                                 expected_contract_sha256=args.expected_contract_sha256,
                                 inputs=load_inputs(args.repo_root))
        encoded = canonical(report)
        _write_new(args.out, encoded)
    except ContractError as exc:
        sys.stderr.write(canonical({"status": "rejected", "code": exc.code}).decode("ascii"))
        return 1
    sys.stdout.write(encoded.decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
