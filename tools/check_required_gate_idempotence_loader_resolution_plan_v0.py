#!/usr/bin/env python3
"""Check a finite per-consumer loader-resolution proposal from original bytes.

The selected historical entry capture is reconstructed with its unchanged
checker. Original ELF bytes independently determine static consumer occurrences.
No acquisition module is imported, no payload or signature verifier is executed,
and an accepted proposal establishes no new loader-resolution observation.
"""
from __future__ import annotations

import argparse
import copy
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
import check_required_gate_idempotence_entry_stop_v0 as entry
import required_gate_idempotence_elf_v0 as elf
import required_gate_idempotence_exec_stop_hosted_io_v0 as transport

ROOT = Path(__file__).resolve().parents[1]
SELF_REL = "tools/check_required_gate_idempotence_loader_resolution_plan_v0.py"
SCHEMA_REL = "schemas/required_gate_idempotence_loader_resolution_plan_v0.schema.json"
PLAN_REL = "docs/compute/required_gate_idempotence_loader_resolution_plan_v0/plan_v0.json"
BASELINE_REL = ("preservation/required_gate_idempotence_entry_stop_v0/"
                "run_44740993943_attempt_1/control_evidence_v0.zip")
PROFILE = "linux_x86_64_original_launcher_loader_resolution_plan_v0"
PROPOSED_PROFILE = "linux_x86_64_original_launcher_loader_resolution_v0"
CONTROL_BYTES = 1024 * 1024
BASELINE = {"sha256": "75c71960080a22c88f78b92c8c9af293cc28dc41a4fbd3916e0f515755a245d0",
            "size_bytes": 5682024}
BASELINE_MEMBER_COUNT = 309
BASELINE_DECODED_BYTES = 12819181
HISTORICAL_SOURCE_COUNT = 81
HISTORICAL_CONTEXT = {
    "run_id": 44740993943, "run_attempt": 1,
    "source_commit": "03d2c76e06d1f4efaf3a9e7e78dcf16a8be62081",
    "attempt_id": "4588122020677e9b3c9d359c987e30e4",
}
PINS = {
    "request": {"sha256": "15341c355cd90e3e4f11e25f5941196c98ad3de0f4dfa9b05acf9a5472f3aeae", "size_bytes": 34686},
    "capture": {"sha256": "f6a8af188cc93ac6ad375ae09252abd7b14e699e4900cca357a6eb165194823d", "size_bytes": 13181},
    "report": {"sha256": "e8cbdb4e7f25a4701be1f2b699d96702e077368cc1ddbe1d9ccc8189cb8e6bdd", "size_bytes": 12542},
    "receipt": {"sha256": "92df084686c47b250b03d6071a8081b277b35bc2a2e09c220d702421faa1a516", "size_bytes": 59475},
    "verified_binding": {"sha256": "6618bbd5fd778d32b87c8b6602c11547dcb4cc8e7cb23dd40e911c63d172d1bf", "size_bytes": 15533},
}
# These large, historically bound inputs cannot use the ordinary 1 MiB source
# limit. Their maximum lengths are selected independently of proposal fields.
SOURCE_LIMITS = {
    entry.plan_check.BASELINE_REL: entry.plan_check.BASELINE["size_bytes"],
    entry.plan_check.ORIGINALS_REL: entry.plan_check.ORIGINALS["size_bytes"],
    entry.PLAN_REL: entry.PLAN["size_bytes"],
}
# Independently selected proposal policy. These are requirements, not completed
# binary qualifications or acquired witness records.
FIXED_CONTRACT = {'future_attempt': {'fresh_attempt_required': True,
                    'fresh_original_input_admission_required': True,
                    'fresh_cp0_required': True,
                    'fresh_task_guard_qualification_required': True,
                    'fresh_two_slot_breakpoint_qualification_required': True,
                    'fresh_source_bound_request_required': True,
                    'historical_entry_report_reusable_as_live_prefix': False,
                    'historical_pid_or_aslr_address_reusable': False,
                    'historical_child_resumable': False,
                    'selected_invocation_must_remain_original': True,
                    'owner_acquisition_authorization_required': True,
                    'authorization_supplied_by_plan': False},
 'witness_design': {'selection_status': 'proposed_unqualified',
                    'mechanism': 'original_loader_openaux_post_map_object_return_and_original_entry_hardware_stops',
                    'upstream_source_reference': 'glibc-2.41',
                    'upstream_source_is_original_binary_qualification': False,
                    'loader_path': 'native/ld-linux-x86-64.so.2',
                    'return_checkpoint': {'source_function': 'openaux',
                                          'source_call': '_dl_map_object',
                                          'phase': 'immediately_after_call_before_return_value_store',
                                          'binary_file_offset': None,
                                          'binary_virtual_address': None,
                                          'args_pointer_recovery_recipe': None,
                                          'private_layout_recipe': None,
                                          'source_debug_binary_binding': None,
                                          'provider_value': 'live_return_register_RAX_under_exact_binary_qualified_calling_convention',
                                          'args_aux_is_fresh_at_this_checkpoint': False,
                                          'argument_pointer_assumed_in_RDI': False,
                                          'exact_instruction_boundary_and_control_flow_proof_required': True,
                                          'target': 'fresh_original_loader_load_bias_plus_qualified_original_instruction_vaddr'},
                    'entry_checkpoint': {'target': 'fresh_auxv_AT_ENTRY_equals_original_launcher_load_bias_plus_original_ELF_e_entry',
                                         'stop_before_entry_instruction_required': True,
                                         'required_after_all_selected_resolution_events': True},
                    'breakpoint_policy': {'mechanism': 'x86_64_hardware_execution_breakpoints',
                                          'return_slot': 0,
                                          'entry_slot': 1,
                                          'debug_register_writes': ['DR0', 'DR1', 'DR6', 'DR7'],
                                          'dr7_enable_value': 5,
                                          'same_two_targets_armed_from_cp0_until_entry': True,
                                          'disarm_after_ninth_return': False,
                                          'debug_programming_readback_and_cause_check_required': True,
                                          'require_only_expected_slot_cause': True,
                                          'stop_signal': 'SIGTRAP',
                                          'siginfo_code': 'TRAP_HWBKPT',
                                          'ptrace_event_bits': 0,
                                          'repeated_hit_resume_behavior_must_be_qualified': True,
                                          'existing_slot_zero_qualification_sufficient': False,
                                          'software_breakpoint_or_target_code_patch': False,
                                          'general_register_or_instruction_pointer_write': False,
                                          'single_step_syscall_trace_or_detach': False},
                    'occurrence_join': {'consumer': 'raw_consumer_link_map_bound_to_original_ELF_load_bias_and_contemporaneous_backing_object',
                                        'name': 'raw_args_name_pointer_and_NUL_terminated_bytes_match_original_consumer_dynstr_occurrence',
                                        'provider': 'live_returned_link_map_bound_to_original_provider_ELF_load_bias_and_contemporaneous_backing_object',
                                        'dynamic_ordinal': 'unique_original_consumer_identity_and_needed_name_join',
                                        'each_consumer_name_pair_must_be_unique': True,
                                        'dynamic_string_token_expansion_allowed': False,
                                        'duplicate_needed_names_within_one_consumer_allowed': False,
                                        'args_contains_dynamic_tag_ordinal': False,
                                        'event_order_is_dynamic_ordinal': False,
                                        'exactly_one_event_per_declared_occurrence': True,
                                        'reused_provider_requires_its_own_consumer_event': True,
                                        'expected_provider_is_observation': False,
                                        'global_map_list_or_initfini_array_is_selected_witness': False},
                    'raw_event_requirements': ['owned_process_pid_tid_starttime_and_pidfd_continuity',
                                               'wait_status_siginfo_registers_and_debug_register_cause',
                                               'qualified_loader_instruction_bytes_and_fresh_load_bias',
                                               'raw_argument_structure_and_recovered_pointer_provenance',
                                               'raw_consumer_link_map_required_fields_and_mapping_identity',
                                               'raw_needed_name_pointer_bytes_and_original_dynamic_tag_join',
                                               'raw_live_return_value_and_provider_link_map_required_fields',
                                               'contemporaneous_maps_descriptor_identity_and_original_file_bindings',
                                               'two_stopped_samples_of_each_required_memory_range_and_register_set',
                                               'raw_unedited_failure_prefix_and_terminal_owned_cleanup'],
                    'positive_acceptance': {'required_dt_needed_events': 9,
                                            'extra_event_allowed': False,
                                            'unknown_consumer_or_provider_allowed': False,
                                            'missing_or_duplicate_event_allowed': False,
                                            'exceptions_or_early_exit_complete': False,
                                            'entry_before_all_events_complete': False,
                                            'selected_event_namespace_must_be_base': True,
                                            'selected_consumer_and_provider_maps_must_be_non_proxy': True,
                                            'absence_of_all_other_namespace_activity_claimed': False,
                                            'all_expected_events_and_entry_and_cleanup_required': True},
                    'rejected_substitutes': ['mapped_provider_presence_or_matching_soname',
                                             'static_candidate_or_producer_success_boolean',
                                             'loader_global_link_map_search_scope_or_first_loader_pointer',
                                             'ldd_loader_list_LD_DEBUG_or_audit_callback_text',
                                             'generic_glibc_version_offsets_or_host_header_layouts',
                                             'historical_entry_capture_relabelled_as_resolution_events',
                                             'rebuilt_patched_or_injected_loader_or_helper_DSO'],
                    'claim_if_later_independently_observed': 'selected_provider_returned_for_each_of_the_nine_original_DT_NEEDED_occurrences',
                    'excluded_claims': ['all_symbol_resolution_or_lazy_binding',
                                        'all_IFUNC_or_initializer_behavior',
                                        'all_loader_search_paths_or_future_dlopen',
                                        'complete_process_memory_or_native_execution_closure',
                                        'observed_whole_containment_or_selected_bootstrap_execution',
                                        'Q3_metric_result_or_release_authority']},
 'execution_policy': {'argv': ['bubblewrap'],
                      'cwd': '/',
                      'environment': {'LC_ALL': 'C', 'TZ': 'UTC'},
                      'owned_tracees': 1,
                      'ptrace_exitkill_required': True,
                      'positive_pre_exec_resumes': 1,
                      'positive_cp0_through_entry_resumes': 10,
                      'positive_total_ptrace_cont': 11,
                      'post_entry_resumes': 0,
                      'original_entry_profile_continuation_policy_changed': False,
                      'task_creation_guard': 'fresh_qualified_existing_deny_clone_clone3_fork_vfork_io_uring_compat_x32_profile',
                      'guard_uninstall_or_relaxation_allowed': False,
                      'native_loader_relocation_IFUNC_and_initialization_may_execute': True,
                      'before_all_userspace_claim': False,
                      'unexpected_stop_action': 'preserve_prefix_then_owned_SIGKILL_and_reap_without_resume',
                      'tenth_return_action': 'preserve_unexpected_event_then_owned_SIGKILL_and_reap_without_resume',
                      'successful_entry_action': 'preserve_entry_then_owned_SIGKILL_and_reap_without_resume',
                      'implicit_retry_deadline_extension_or_fallback': False},
 'evidence_policy': {'new_profile_request_capture_and_event_schema_required': True,
                     'independent_raw_capture_checker_required': True,
                     'original_old_capture_schema_reused_for_new_events': False,
                     'historical_81_source_bindings_and_new_implementation_bindings_separate': True,
                     'fresh_environment_preload_audit_and_configuration_evidence_required': True,
                     'LD_PRELOAD_LD_AUDIT_LD_DEBUG_or_other_environment_injection': False,
                     'etc_ld_so_preload_must_be_proven_absent_or_empty': True,
                     'DT_AUDIT_DT_DEPAUDIT_DT_FILTER_DT_AUXILIARY_allowed': False,
                     'unselected_or_repeated_return_checkpoint_events_allowed': False,
                     'loader_calls_without_selected_return_checkpoint_claimed_observed': False,
                     'vdso_treatment': 'bounded_kernel_mapping_metadata_not_a_selected_DT_NEEDED_provider',
                     'current_bytes_not_readable_or_unbound_pointer': 'incomplete_reject_positive_claim',
                     'register_and_memory_stability_required': True,
                     'original_six_native_file_bindings_required_before_and_after_attempt': True,
                     'cp0_original_launcher_and_interpreter_RX_ranges_required': True,
                     'entry_all_six_original_native_RX_ranges_required': True,
                     'event_loader_instruction_and_RX_samples_match_original': True,
                     'event_consumer_and_provider_identities_bound_to_original_files': True,
                     'runtime_args_and_link_map_fields_are_original_file_bytes': False,
                     'runtime_metadata_checked_by_qualified_pointer_and_identity_relations': True,
                     'event_memory_sample_storage': 'two_bounded_packed_raw_blobs_with_exact_range_offset_length_manifests',
                     'source_debug_qualification_payload_is_separate_hash_bound_carrier': True,
                     'source_debug_qualification_payload_in_live_capture_total': False,
                     'source_debug_qualification_control_in_live_capture_total': True,
                     'pointer_or_pathname_alone_sufficient': False,
                     'error_or_partial_capture_must_be_preserved': True,
                     'termination_and_reaping_required': True,
                     'producer_checker_and_environment_trust_must_be_explicit': True,
                     'physical_execution_authentication_claimed': False,
                     'full_hosted_replay_from_control_selection_claimed': False,
                     'signatures_freshly_verified_by_plan_checker': False},
 'limits': {'wall_seconds': 15,
            'cleanup_seconds': 2,
            'owned_tracees': 1,
            'positive_resolution_events': 9,
            'preserved_resolution_events_max': 10,
            'final_entry_checkpoints': 1,
            'wait_records': 20,
            'ptrace_cont_max': 11,
            'capture_files': 512,
            'total_capture_bytes': 67108864,
            'control_file_bytes': 1048576,
            'proc_file_bytes': 65536,
            'stdout_bytes': 4096,
            'stderr_bytes': 4096,
            'per_event_files': 32,
            'per_event_memory_ranges': 32,
            'memory_samples_per_range': 2,
            'event_memory_sample_blobs': 2,
            'event_memory_sample_blob_bytes': 131072,
            'memory_window_bytes': 4096,
            'per_event_memory_bytes': 262144,
            'pointer_indirections_max': 4,
            'needed_name_bytes_including_NUL': 256,
            'map_rows': 128,
            'source_debug_qualification_control_bytes': 1048576,
            'source_debug_qualification_payload_bytes': 67108864,
            'absolute_addresses_from_old_attempt_allowed': False,
            'raise_limits_after_start_or_implicit_retry': False,
            'loader_rx_samples_per_event': 2,
            'loader_rx_sample_bytes': 160721},
 'implementation_gates': [{'id': 'exact_original_loader_source_debug_binary_binding',
                           'status': 'unsatisfied',
                           'required': 'Bind original loader bytes and build identity to '
                                       'distribution source patches, build provenance and matching '
                                       'debug data; upstream version alone is insufficient.'},
                          {'id': 'exact_return_site_and_live_value_recipe',
                           'status': 'unsatisfied',
                           'required': 'Prove the selected instruction boundary, call target, live '
                                       'RAX value and bounded saved-args recovery recipe in the '
                                       'exact original binary.'},
                          {'id': 'private_structures_and_occurrence_provenance',
                           'status': 'unsatisfied',
                           'required': 'Qualify consumed openaux_args and link_map layouts, '
                                       'namespace and mapping joins, original dynstr pointers and '
                                       'unique dynamic-tag occurrence recovery.'},
                          {'id': 'two_slot_repeated_hardware_stop_qualification',
                           'status': 'unsatisfied',
                           'required': 'Prove simultaneous return and entry breakpoints, readback, '
                                       'repeated-hit resume behavior and exclusive cause '
                                       'attribution in the selected guarded context.'},
                          {'id': 'closed_new_request_capture_and_event_schemas',
                           'status': 'unsatisfied',
                           'required': 'Implement finite new-profile records, raw member inventory '
                                       'and all incomplete-prefix states without altering '
                                       'historical entry schemas.'},
                          {'id': 'bounded_collector_and_independent_raw_checker',
                           'status': 'unsatisfied',
                           'required': 'Implement one owned guarded attempt and independent raw '
                                       'reconstruction of the nine-event bijection, final entry, '
                                       'source identity and terminal cleanup.'},
                          {'id': 'fresh_environment_and_original_input_admission',
                           'status': 'unsatisfied',
                           'required': 'Reconstruct current original input admission and selected '
                                       'environment controls including preloads, audit mechanisms '
                                       'and observed object identity.'},
                          {'id': 'owner_authorized_fresh_acquisition_and_preservation',
                           'status': 'unsatisfied',
                           'required': 'Obtain separate owner authorization after the preceding '
                                       'gates, perform one fresh attempt, preserve its actual '
                                       'outcome and independently verify original evidence.'}],
 'boundary': {'record_status': 'proposal',
              'diagnostic_only': True,
              'witness_design_selected': True,
              'native_acquisition_performed': False,
              'witness_collector_implemented': False,
              'witness_capture_schema_implemented': False,
              'witness_capture_checker_implemented': False,
              'loader_private_abi_qualified': False,
              'two_slot_breakpoint_qualified': False,
              'consumer_resolution_observed': False,
              'loader_resolution_verified': False,
              'host_environment_qualified': False,
              'physical_execution_authenticated': False,
              'complete_native_closure_verified': False,
              'containment_enforced': False,
              'execution_ready': False,
              'execution_authorized': False,
              'selected_runtime_executed': False,
              'production_gate_eligible': False,
              'b2_complete': False,
              'metric_pass': None,
              'authority_effect': 'none'}}


class PlanError(ValueError):
    """Stable rejection reason without inspected bytes or paths."""

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
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise PlanError("loader_resolution_plan_json_value") from exc


def _same(actual, expected, code):
    # Distinguish bool/int and int/float even where Python equality would not.
    _need(canonical(actual) == canonical(expected), code)


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        _need(key not in value, "loader_resolution_plan_duplicate_key")
        value[key] = item
    return value


def _constant(_value):
    raise PlanError("loader_resolution_plan_nonfinite_json")


def _float(_value):
    raise PlanError("loader_resolution_plan_noninteger_number")


def parse(raw):
    _need(type(raw) is bytes and 0 < len(raw) <= CONTROL_BYTES,
          "loader_resolution_plan_control_size")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=_constant, parse_float=_float)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise PlanError("loader_resolution_plan_json") from exc


def _bound(raw, expected, code):
    _need(type(raw) is bytes and binding(raw) == expected, code)


def _relative(name):
    _need(type(name) is str and 0 < len(name) <= 512 and "\\" not in name
          and "\0" not in name, "loader_resolution_plan_member_path")
    path = PurePosixPath(name)
    _need(bool(path.parts) and not path.is_absolute() and path.as_posix() == name
          and all(part not in {"", ".", ".."} for part in path.parts),
          "loader_resolution_plan_member_path")
    return path


def _archive(raw):
    _bound(raw, BASELINE, "loader_resolution_plan_archive_binding")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            _need(len(names) == BASELINE_MEMBER_COUNT == len(set(names)),
                  "loader_resolution_plan_archive_roster")
            _need(sum(item.file_size for item in infos) == BASELINE_DECODED_BYTES,
                  "loader_resolution_plan_archive_size")
            for item in infos:
                _relative(item.filename)
                _need(not item.is_dir() and not item.flag_bits & 1
                      and stat.S_IFMT(item.external_attr >> 16) in {0, stat.S_IFREG}
                      and item.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED},
                      "loader_resolution_plan_archive_member_type")
            # Reading every member verifies its CRC; no archive path is extracted.
            members = {name: archive.read(name) for name in sorted(names)}
            _need(all(len(members[item.filename]) == item.file_size for item in infos),
                  "loader_resolution_plan_archive_member_size")
            return members
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, EOFError) as exc:
        if isinstance(exc, PlanError):
            raise
        raise PlanError("loader_resolution_plan_archive_invalid") from exc


def _source(path):
    _relative(path)
    try:
        return transport.read_regular(ROOT / path, SOURCE_LIMITS.get(path, CONTROL_BYTES))
    except (OSError, ValueError) as exc:
        raise PlanError("loader_resolution_plan_source_unreadable") from exc


def _check_sources(sources):
    _need(type(sources) is dict and len(sources) == HISTORICAL_SOURCE_COUNT,
          "loader_resolution_plan_historical_sources")
    for path, descriptor in sources.items():
        _same(binding(_source(path)), descriptor,
              "loader_resolution_plan_historical_source_changed")


def _historical_baseline():
    return {**HISTORICAL_CONTEXT, "archive_path": BASELINE_REL, "archive": dict(BASELINE),
        "archive_member_count": BASELINE_MEMBER_COUNT,
        "archive_decoded_size_bytes": BASELINE_DECODED_BYTES,
        "pins": copy.deepcopy(PINS), "source_file_count": HISTORICAL_SOURCE_COUNT,
        "scope": "historical_entry_lower_level_reconstruction_only",
        "historical_child_terminated": True, "historical_child_resumable": False,
        "historical_consumer_resolution_observed": False,
        "fresh_signature_verification_claimed": False,
        "complete_hosted_replay_carrier": False}


def reconstruct_historical_entry(raw):
    """Reconstruct the pinned original entry record, never a saved verdict alone."""
    try:
        return _reconstruct_historical_entry(raw)
    except (ValueError, KeyError, TypeError, IndexError, OSError, struct.error) as exc:
        if isinstance(exc, PlanError):
            raise
        raise PlanError("loader_resolution_plan_historical_entry_invalid") from exc


def _reconstruct_historical_entry(raw):
    members = _archive(raw)
    prefix = "acquisition/observation/capture/"
    capture_tree = {name[len(prefix):]: data for name, data in members.items()
                    if name.startswith(prefix)}
    _need(set(capture_tree) == {"capture.json", *entry.FILE_NAMES},
          "loader_resolution_plan_historical_capture_roster")
    request_raw = members["acquisition/observation/request.json"]
    capture_raw = capture_tree.pop("capture.json")
    report1 = members["verification/verification/capture-check-1.json"]
    report2 = members["verification/verification/capture-check-2.json"]
    receipt_raw = members["acquisition/receipt.json"]
    verified_raw = members["verification/verified-binding.json"]
    for key, data in (("request", request_raw), ("capture", capture_raw),
                      ("report", report1), ("report", report2),
                      ("receipt", receipt_raw), ("verified_binding", verified_raw)):
        _bound(data, PINS[key], "loader_resolution_plan_historical_control_binding")
    _need(capture_tree["request.json"] == request_raw,
          "loader_resolution_plan_historical_request_copy")
    receipt, verified = parse(receipt_raw), parse(verified_raw)
    sources = parse(members["acquisition/source-bindings.json"])
    for other in (parse(members["verification/source-bindings.json"]),
                  receipt["source_bindings"], verified["source_bindings"]):
        _same(sources, other, "loader_resolution_plan_historical_sources")
    _check_sources(sources)
    context = receipt["context"]
    _same(context, verified["context"], "loader_resolution_plan_historical_context")
    _same({key: context[key] for key in ("run_id", "run_attempt", "source_commit")},
          {key: HISTORICAL_CONTEXT[key] for key in ("run_id", "run_attempt", "source_commit")},
          "loader_resolution_plan_historical_context")
    _need(context["workflow_sha"] == HISTORICAL_CONTEXT["source_commit"]
          and context["repository"] == "HKati/pulse-release-gates-0.1"
          and context["ref"] == "refs/heads/main"
          and context["event_name"] == "workflow_dispatch"
          and context["actor"] == context["triggering_actor"] == "HKati",
          "loader_resolution_plan_historical_context")
    for key in ("request", "capture"):
        _same(receipt[key], PINS[key], "loader_resolution_plan_receipt_binding")
        _same(verified[key], PINS[key], "loader_resolution_plan_verified_binding")
    for key in ("first_report", "second_report"):
        _same(verified[key], PINS["report"], "loader_resolution_plan_verified_binding")
    _same(verified["original_receipt"], PINS["receipt"],
          "loader_resolution_plan_verified_binding")
    _need(receipt["file_count"] == 306 and len(receipt["files"]) == 306
          and receipt["total_size_bytes"] == 201458840,
          "loader_resolution_plan_receipt_inventory")
    for name, data in members.items():
        if name.startswith("acquisition/") and name != "acquisition/receipt.json":
            _same(receipt["files"].get(name[len("acquisition/"):]), binding(data),
                  "loader_resolution_plan_selected_receipt_member")
    for kind, capture_name, record_key in (
        ("task-guard", "guard", "task_guard_qualification"),
        ("hardware", "breakpoint", "hardware_qualification")):
        qualification_raw = members["acquisition/observation/qualifications/" + kind + ".json"]
        _need(qualification_raw == capture_tree[capture_name + ".qualification.json"],
              "loader_resolution_plan_qualification_copy")
        _same(binding(qualification_raw), receipt[record_key],
              "loader_resolution_plan_qualification_binding")
        _same(receipt[record_key], verified[record_key],
              "loader_resolution_plan_qualification_binding")
    for phase, key in (("acquisition", "original_container_cleanup"),
                       ("verification", "verification_container_cleanup")):
        cleanup_raw = members[phase + "/environment/container-cleanup.json"]
        _same(binding(cleanup_raw), verified[key], "loader_resolution_plan_cleanup_binding")
        cleanup = parse(cleanup_raw)
        _same(cleanup["context"], context, "loader_resolution_plan_cleanup_context")
        _need(all(cleanup[name] is True for name in ("owned_container_created",
              "owned_container_removed", "removal_absence_observed"))
              and cleanup["failure"] is None, "loader_resolution_plan_outer_cleanup")
    _need(verified["status"] == "accepted" and verified["observation_complete"] is True
          and verified["canonical_reports_byte_identical"] is True
          and verified["owned_outer_cleanup_verified"] is True
          and verified["verification_acquisition_repeated"] is False
          and verified["artifact_id"] == 14631066127,
          "loader_resolution_plan_historical_verified_binding")
    try:
        report = entry.verify_capture(
            request_bytes=request_raw, expected_request_sha256=PINS["request"]["sha256"],
            capture_bytes=capture_raw, expected_capture_sha256=PINS["capture"]["sha256"],
            files=capture_tree)
    except (ValueError, OSError) as exc:
        raise PlanError("loader_resolution_plan_historical_entry_rejected") from exc
    _need(type(report) is dict and report.get("status") == "accepted"
          and report.get("observation_complete") is True
          and all(report.get(name) is True for name in entry.NARROW_FLAGS),
          "loader_resolution_plan_historical_entry_incomplete")
    _need(canonical(report) == report1 == report2,
          "loader_resolution_plan_historical_entry_report_mismatch")
    _same({key: report[key] for key in entry.BOUNDARY}, entry.BOUNDARY,
          "loader_resolution_plan_historical_boundary")
    _need(report["consumer_resolution_observed"] is False
          and report["attempt_id"] == HISTORICAL_CONTEXT["attempt_id"],
          "loader_resolution_plan_historical_attempt_scope")
    native = {}
    for role, path in entry.ROLES.items():
        before = capture_tree["native." + role + ".before.elf"]
        after = capture_tree["native." + role + ".after.elf"]
        _bound(before, entry.NATIVE[path], "loader_resolution_plan_original_native_binding")
        _need(before == after, "loader_resolution_plan_original_native_changed")
        native[path] = before
    _check_sources(sources)
    return {"request": parse(request_raw), "report": report, "sources": sources,
            "native": native, "baseline": _historical_baseline(), "pins": copy.deepcopy(PINS)}


def _program_headers(raw):
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", raw)
    headers = []
    for index in range(header[10]):
        kind, flags, offset, vaddr, _physical, filesz, memsz, align = struct.unpack_from(
            "<IIQQQQQQ", raw, header[5] + index * header[9])
        headers.append({"index": index, "type": kind, "flags": flags,
            "offset": offset, "vaddr": vaddr, "filesz": filesz,
            "memsz": memsz, "align": align})
    return headers


def _file_offset(headers, address, length):
    matches = [row for row in headers if row["type"] == 1
               and row["vaddr"] <= address
               and 0 <= address - row["vaddr"] <= row["filesz"]
               and length <= row["filesz"] - (address - row["vaddr"])]
    _need(len(matches) == 1, "loader_resolution_plan_elf_virtual_mapping")
    row = matches[0]
    return row["offset"] + address - row["vaddr"]


def derive_native_obligations(native):
    """Derive nine needed occurrences and three interpreter declarations.

    The return values are static candidates. Historical provider mappings never
    become consumer-resolution witnesses through this derivation.
    """
    try:
        return _derive_native_obligations(native)
    except (ValueError, KeyError, TypeError, IndexError, struct.error, UnicodeError) as exc:
        if isinstance(exc, PlanError):
            raise
        raise PlanError("loader_resolution_plan_native_elf") from exc


def _derive_native_obligations(native):
    _need(type(native) is dict and set(native) == set(entry.NATIVE),
          "loader_resolution_plan_native_roster")
    objects, dependencies, interpreters = [], [], []
    roles = {path: role for role, path in entry.ROLES.items()}
    providers = {PurePosixPath(path).name: path for path in native}
    _need(len(providers) == len(native), "loader_resolution_plan_provider_ambiguity")
    for path in sorted(native):
        raw = native[path]
        _bound(raw, entry.NATIVE[path], "loader_resolution_plan_original_native_binding")
        metadata = elf.inspect_elf(raw)
        layout = entry.cp0.elf_layout(raw)
        headers = _program_headers(raw)
        consumer = {"path": path, **binding(raw)}
        objects.append({**consumer, "role": roles[path], "elf": layout,
            "dynamic": metadata, "evidence_role": "static_candidate_only",
            "consumer_resolution_observed": False})
        _need(metadata["rpath"] is None and metadata["runpath"] is None,
              "loader_resolution_plan_native_profile")
        dynamic_headers = [row for row in headers if row["type"] == 2]
        _need(len(dynamic_headers) == 1, "loader_resolution_plan_dynamic_segment")
        dynamic = dynamic_headers[0]
        entries = []
        for ordinal, offset in enumerate(range(dynamic["offset"],
                dynamic["offset"] + dynamic["filesz"], 16)):
            tag, value = struct.unpack_from("<qQ", raw, offset)
            if tag == 0:
                break
            entries.append((ordinal, offset, tag, value))
        strings = {tag: value for _ordinal, _offset, tag, value in entries if tag in {5, 10}}
        _need(set(strings) == {5, 10}, "loader_resolution_plan_string_table")
        string_file_offset = _file_offset(headers, strings[5], strings[10])
        string_bytes = raw[string_file_offset:string_file_offset + strings[10]]
        needed = [(ordinal, offset, value) for ordinal, offset, tag, value in entries if tag == 1]
        _need(len(needed) == len(metadata["needed"]), "loader_resolution_plan_needed_count")
        _need(len(metadata["needed"]) == len(set(metadata["needed"])),
              "loader_resolution_plan_needed_duplicate")
        for needed_ordinal, (ordinal, offset, string_offset) in enumerate(needed):
            _need(0 <= string_offset < len(string_bytes), "loader_resolution_plan_needed_string")
            end = string_bytes.find(b"\0", string_offset)
            _need(end > string_offset, "loader_resolution_plan_needed_string")
            name = string_bytes[string_offset:end].decode("ascii")
            _need(0 < len(name) <= 255 and "$" not in name and "/" not in name,
                  "loader_resolution_plan_needed_name_profile")
            _need(name == metadata["needed"][needed_ordinal] and name in providers,
                  "loader_resolution_plan_needed_provider")
            provider = providers[name]
            dependencies.append({"consumer": dict(consumer),
                "dynamic_program_header_index": dynamic["index"],
                "dynamic_entry_ordinal": ordinal, "dynamic_entry_file_offset": offset,
                "dynamic_entry_vaddr": dynamic["vaddr"] + offset - dynamic["offset"],
                "needed_ordinal": needed_ordinal, "name": name,
                "string_table_offset": string_offset,
                "name_file_offset": string_file_offset + string_offset,
                "expected_provider": {"path": provider, **binding(native[provider])},
                "evidence_role": "static_candidate_only", "consumer_resolution_observed": False})
        for interp in (row for row in headers if row["type"] == 3):
            value = raw[interp["offset"]:interp["offset"] + interp["filesz"]]
            _need(value.endswith(b"\0") and b"\0" not in value[:-1],
                  "loader_resolution_plan_interpreter_string")
            name = value[:-1].decode("ascii")
            _need(name == metadata["interpreter"] and PurePosixPath(name).name in providers,
                  "loader_resolution_plan_interpreter_provider")
            provider = providers[PurePosixPath(name).name]
            interpreters.append({"consumer": dict(consumer),
                "program_header_index": interp["index"], "file_offset": interp["offset"],
                "size_bytes": interp["filesz"], "path": name,
                "expected_provider": {"path": provider, **binding(native[provider])},
                "evidence_role": "historical_kernel_continuity" if path == "native/bwrap"
                                 else "static_metadata_only",
                "consumer_resolution_observed": False})
    _need(len(objects) == 6 and len(dependencies) == 9 and len(interpreters) == 3,
          "loader_resolution_plan_occurrence_counts")
    return objects, dependencies, interpreters


def make_plan(historical):
    """Package independently derived requirements; this is not an acquisition API."""
    objects, dependencies, interpreters = derive_native_obligations(historical["native"])
    totals = {"native_objects": len(objects),
        "original_native_bytes": sum(row["size_bytes"] for row in objects),
        "pt_load_occurrences": sum(len(row["elf"]["segments"]) for row in objects),
        "dependency_occurrences": len(dependencies),
        "interpreter_declarations": len(interpreters),
        "static_relationships": len(dependencies) + len(interpreters)}
    return {"record_type": "required_gate_idempotence_loader_resolution_plan_v0",
        "profile": PROFILE, "proposed_observation_profile": PROPOSED_PROFILE,
        "historical_baseline": _historical_baseline(), "native_objects": objects,
        "dependency_occurrences": dependencies, "interpreter_declarations": interpreters,
        "totals": totals, **copy.deepcopy(FIXED_CONTRACT)}


def verify_plan(*, plan_bytes, expected_plan_sha256, historical_entry_archive_bytes):
    """Verify a proposal against fixed design and freshly reconstructed history."""
    _need(type(expected_plan_sha256) is str and len(expected_plan_sha256) == 64
          and all(char in "0123456789abcdef" for char in expected_plan_sha256),
          "loader_resolution_plan_external_digest")
    _need(type(plan_bytes) is bytes and 0 < len(plan_bytes) <= CONTROL_BYTES
          and sha(plan_bytes) == expected_plan_sha256, "loader_resolution_plan_digest_mismatch")
    _need(set(FIXED_CONTRACT) == {"future_attempt", "witness_design", "execution_policy",
          "evidence_policy", "limits", "implementation_gates", "boundary"},
          "loader_resolution_plan_fixed_contract_unselected")
    plan = parse(plan_bytes)
    schema_raw = _source(SCHEMA_REL)
    implementation_raw = _source(SELF_REL)
    try:
        schema = parse(schema_raw)
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(plan)
    except (jsonschema.ValidationError, jsonschema.SchemaError) as exc:
        raise PlanError("loader_resolution_plan_schema") from exc
    historical = reconstruct_historical_entry(historical_entry_archive_bytes)
    expected = make_plan(historical)
    _same(plan, expected, "loader_resolution_plan_contract_mismatch")
    _need(_source(SCHEMA_REL) == schema_raw and _source(SELF_REL) == implementation_raw,
          "loader_resolution_plan_checker_source_changed")
    _check_sources(historical["sources"])
    return {"record_type": "required_gate_idempotence_loader_resolution_plan_verification_v0",
        "profile": PROFILE, "status": "accepted", "plan": binding(plan_bytes),
        "plan_consistency_verified": True,
        "historical_entry": {**HISTORICAL_CONTEXT, "lower_level_reconstruction_accepted": True,
            "report": dict(PINS["report"]), "source_file_count": len(historical["sources"]),
            "narrow_flags": {name: historical["report"][name] for name in entry.NARROW_FLAGS}},
        "original_native_bytes_verified": True, "static_occurrences_derived": True,
        "totals": expected["totals"],
        "native_objects_sha256": sha(canonical(expected["native_objects"])),
        "dependency_occurrences_sha256": sha(canonical(expected["dependency_occurrences"])),
        "interpreter_declarations_sha256": sha(canonical(expected["interpreter_declarations"])),
        "historical_sources_sha256": sha(canonical(historical["sources"])),
        "checker_source": binding(implementation_raw), "schema_source": binding(schema_raw),
        "distribution_signature_freshly_verified": False,
        "attestation_signature_freshly_verified": False,
        "full_hosted_replay_performed": False, **copy.deepcopy(FIXED_CONTRACT["boundary"])}


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
            historical_entry_archive_bytes=transport.read_regular(ROOT / BASELINE_REL, BASELINE["size_bytes"]))
        raw = canonical(result)
        if args.output:
            transport.write_new(Path(args.output), raw)
        sys.stdout.buffer.write(raw)
        return 0
    except (PlanError, OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError) as exc:
        code = exc.code if isinstance(exc, PlanError) else "loader_resolution_plan_io"
        sys.stderr.buffer.write(canonical({"status": "rejected", "reason": code}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
