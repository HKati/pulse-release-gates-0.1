#!/usr/bin/env python3
"""Verify hosted custody for one bounded original-loader resolution capture.

Only standard-library transport is imported on the host. Native semantics are
reconstructed by two separately recorded, source-bound checker processes in
an offline selected environment. This module joins their raw inputs, outputs,
container contracts and cleanup; it never imports or invokes an acquisition.
Hosted attestation authenticates that statement, not physical execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_loader_two_slot_attempt_v0 as core

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "linux_x86_64_loader_resolution_hosted_v0"
REPOSITORY = "HKati/pulse-release-gates-0.1"
REPOSITORY_ID = "1061766508"
WORKFLOW = ".github/workflows/required_gate_idempotence_loader_resolution_v0.yml"
CONFIG = "tools/required_gate_idempotence_loader_resolution_hosted_v0"
ACKNOWLEDGEMENT = "OBSERVE_ORIGINAL_LOADER_NINE_RETURNS_AND_ENTRY_STOP_ONLY"
PYTHON = "/usr/local/bin/python3.11"
PYTHON_VERSION = "3.11.16"
SCHEMA_PATH = "schemas/required_gate_idempotence_loader_resolution_hosted_v0.schema.json"
CONFIG_FILES = ("Dockerfile", "environment.json", "requirements.lock", "build_environment.py", "run.py")
# Reviewed offline closure, including transitive historical source checks and raw
# carriers. This roster is selected before a run, never inferred from its output.
SOURCE_PATHS = ('.github/workflows/required_gate_idempotence_entry_stop_v0.yml',
 '.github/workflows/required_gate_idempotence_exec_stop_v0.yml',
 '.github/workflows/required_gate_idempotence_loader_resolution_v0.yml',
 'docs/compute/required_gate_idempotence_entry_stop_plan_v0/plan_v0.json',
 'docs/compute/required_gate_idempotence_loader_binary_binding_v0/record_v0.json',
 'docs/compute/required_gate_idempotence_loader_build_record_binding_v0/preservation/glibc_2.41-12+deb13u4_amd64-buildd.changes',
 'docs/compute/required_gate_idempotence_loader_build_record_binding_v0/preservation/glibc_2.41-12+deb13u4_amd64.buildinfo',
 'docs/compute/required_gate_idempotence_loader_build_record_binding_v0/record_v0.json',
 'docs/compute/required_gate_idempotence_loader_readout_contract_v0/contract_v0.json',
 'docs/compute/required_gate_idempotence_loader_rebuild_acceptance_v0/policy_v0.json',
 'docs/compute/required_gate_idempotence_loader_rebuild_acceptance_v0/preservation/public_service_evidence_v0.zip',
 'docs/compute/required_gate_idempotence_loader_rebuild_acceptance_v0/record_v0.json',
 'docs/compute/required_gate_idempotence_loader_rebuild_attestation_binding_v0/preservation/libc6_attestation.json',
 'docs/compute/required_gate_idempotence_loader_rebuild_attestation_binding_v0/preservation/libc6_dbg_attestation.json',
 'docs/compute/required_gate_idempotence_loader_rebuild_attestation_binding_v0/preservation/public_keys.json',
 'docs/compute/required_gate_idempotence_loader_rebuild_attestation_binding_v0/record_v0.json',
 'docs/compute/required_gate_idempotence_loader_resolution_plan_v0/plan_v0.json',
 'docs/compute/required_gate_idempotence_loader_startup_contract_v0/contract_v0.json',
 'docs/compute/required_gate_idempotence_protocol_v0/inputs_v0.json',
 'docs/compute/required_gate_idempotence_protocol_v0/observation_mapping_v0.json',
 'docs/compute/required_gate_idempotence_protocol_v0/protocol_proposal_v0.json',
 'preservation/required_gate_idempotence_entry_stop_v0/run_44740993943_attempt_1/control_evidence_v0.zip',
 'preservation/required_gate_idempotence_exec_stop_v0/ORIGINAL_INPUTS.json',
 'preservation/required_gate_idempotence_exec_stop_v0/original_inputs_v0.zip',
 'preservation/required_gate_idempotence_exec_stop_v0/run_44375052171_attempt_1/control_evidence_v0.zip',
 'preservation/required_gate_idempotence_loader_binary_binding_v0/inputs_v0.json',
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/Sources.xz.part001',
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/Sources.xz.part002',
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/glibc_2.41-12+deb13u4.debian.tar.xz',
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/glibc_2.41-12+deb13u4.dsc',
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/glibc_2.41.orig.tar.xz.part001',
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/glibc_2.41.orig.tar.xz.part002',
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/glibc_2.41.orig.tar.xz.part003',
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/libc6-dbg_2.41-12+deb13u4_amd64.deb',
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/libc6_2.41-12+deb13u4_amd64.deb',
 'schemas/pulsemech_compute_binding_report_v0.schema.json',
 'schemas/pulsemech_compute_planned_observed_relation_v0.schema.json',
 'schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json',
 'schemas/pulsemech_compute_subject_input_packet_v0.schema.json',
 'schemas/pulsemech_integration_plan_v0.schema.json',
 'schemas/required_gate_idempotence_bootstrap_v0.schema.json',
 'schemas/required_gate_idempotence_containment_v0.schema.json',
 'schemas/required_gate_idempotence_entry_build_v0.schema.json',
 'schemas/required_gate_idempotence_entry_stop_plan_v0.schema.json',
 'schemas/required_gate_idempotence_entry_stop_v0.schema.json',
 'schemas/required_gate_idempotence_exec_stop_v0.schema.json',
 'schemas/required_gate_idempotence_launch_host_v0.schema.json',
 'schemas/required_gate_idempotence_launcher_distribution_v0.schema.json',
 'schemas/required_gate_idempotence_loader_binary_binding_v0.schema.json',
 'schemas/required_gate_idempotence_loader_build_record_binding_v0.schema.json',
 'schemas/required_gate_idempotence_loader_readout_contract_v0.schema.json',
 'schemas/required_gate_idempotence_loader_readout_event_v0.schema.json',
 'schemas/required_gate_idempotence_loader_rebuild_acceptance_v0.schema.json',
 'schemas/required_gate_idempotence_loader_rebuild_attestation_binding_v0.schema.json',
 'schemas/required_gate_idempotence_loader_resolution_hosted_v0.schema.json',
 'schemas/required_gate_idempotence_loader_resolution_plan_v0.schema.json',
 'schemas/required_gate_idempotence_loader_resolution_v0.schema.json',
 'schemas/required_gate_idempotence_loader_startup_contract_v0.schema.json',
 'schemas/required_gate_idempotence_loader_startup_invocation_v0.schema.json',
 'schemas/required_gate_idempotence_loader_two_slot_qualification_v0.schema.json',
 'schemas/required_gate_idempotence_loader_two_slot_v0.schema.json',
 'schemas/required_gate_idempotence_mapping_observation_v0.schema.json',
 'schemas/required_gate_idempotence_observation_v0.schema.json',
 'schemas/required_gate_idempotence_runtime_v0.schema.json',
 'schemas/required_gate_suite_contract_v0.schema.json',
 'tests/test_required_gate_idempotence_acquisition_v0.py',
 'tests/test_required_gate_idempotence_bootstrap_v0.py',
 'tests/test_required_gate_idempotence_observation_v0.py',
 'tests/test_required_gate_idempotence_runtime_v0.py',
 'tools/acquire_required_gate_idempotence_v0.py',
 'tools/build_pulsemech_compute_planned_observed_relation_v0.py',
 'tools/check_anchor_integrity_record_signatures_v0_1.py',
 'tools/check_pulsemech_compute_runtime_observation_packet_v0.py',
 'tools/check_required_gate_idempotence_containment_v0.py',
 'tools/check_required_gate_idempotence_entry_build_v0.py',
 'tools/check_required_gate_idempotence_entry_stop_plan_v0.py',
 'tools/check_required_gate_idempotence_entry_stop_v0.py',
 'tools/check_required_gate_idempotence_entry_task_guard_v0.py',
 'tools/check_required_gate_idempotence_exec_stop_v0.py',
 'tools/check_required_gate_idempotence_launch_host_v0.py',
 'tools/check_required_gate_idempotence_launcher_distribution_v0.py',
 'tools/check_required_gate_idempotence_loader_binary_binding_v0.py',
 'tools/check_required_gate_idempotence_loader_build_record_binding_v0.py',
 'tools/check_required_gate_idempotence_loader_readout_contract_v0.py',
 'tools/check_required_gate_idempotence_loader_rebuild_acceptance_v0.py',
 'tools/check_required_gate_idempotence_loader_rebuild_attestation_binding_v0.py',
 'tools/check_required_gate_idempotence_loader_resolution_hosted_v0.py',
 'tools/check_required_gate_idempotence_loader_resolution_plan_v0.py',
 'tools/check_required_gate_idempotence_loader_resolution_v0.py',
 'tools/check_required_gate_idempotence_loader_startup_contract_v0.py',
 'tools/check_required_gate_idempotence_loader_two_slot_attempt_v0.py',
 'tools/check_required_gate_idempotence_loader_two_slot_qualification_v0.py',
 'tools/check_required_gate_idempotence_mapping_observation_v0.py',
 'tools/check_required_gate_idempotence_observation_v0.py',
 'tools/check_required_gate_suite_contract_v0.py',
 'tools/collect_required_gate_idempotence_loader_resolution_v0.py',
 'tools/prepare_required_gate_idempotence_entry_stop_v0.py',
 'tools/prepare_required_gate_idempotence_exec_stop_v0.py',
 'tools/prepare_required_gate_idempotence_loader_resolution_v0.py',
 'tools/pulsemech_compute_binding_analyzer_core_v0.py',
 'tools/pulsemech_compute_standalone_runtime_v0.py',
 'tools/qualify_required_gate_idempotence_entry_stop_v0.py',
 'tools/qualify_required_gate_idempotence_loader_two_slot_v0.py',
 'tools/required_gate_idempotence_bootstrap_probe_v0.py',
 'tools/required_gate_idempotence_bootstrap_v0.py',
 'tools/required_gate_idempotence_containment_entry_v0.c',
 'tools/required_gate_idempotence_containment_policy_v0.py',
 'tools/required_gate_idempotence_containment_v0.py',
 'tools/required_gate_idempotence_debian_metadata_v0.py',
 'tools/required_gate_idempotence_distribution_signature_v0.py',
 'tools/required_gate_idempotence_elf_v0.py',
 'tools/required_gate_idempotence_entry_stop_hosted_v0.py',
 'tools/required_gate_idempotence_entry_stop_hosted_v0/Dockerfile',
 'tools/required_gate_idempotence_entry_stop_hosted_v0/build_environment.py',
 'tools/required_gate_idempotence_entry_stop_hosted_v0/environment.json',
 'tools/required_gate_idempotence_entry_stop_hosted_v0/requirements.lock',
 'tools/required_gate_idempotence_entry_stop_hosted_v0/run.py',
 'tools/required_gate_idempotence_entry_stop_v0.py',
 'tools/required_gate_idempotence_entry_task_guard_v0.py',
 'tools/required_gate_idempotence_exec_stop_hosted_io_v0.py',
 'tools/required_gate_idempotence_exec_stop_hosted_run_v0.py',
 'tools/required_gate_idempotence_exec_stop_hosted_v0.py',
 'tools/required_gate_idempotence_exec_stop_hosted_v0/Dockerfile',
 'tools/required_gate_idempotence_exec_stop_hosted_v0/build_environment.py',
 'tools/required_gate_idempotence_exec_stop_hosted_v0/environment.json',
 'tools/required_gate_idempotence_exec_stop_hosted_v0/requirements.lock',
 'tools/required_gate_idempotence_exec_stop_v0.py',
 'tools/required_gate_idempotence_launch_host_v0.py',
 'tools/required_gate_idempotence_launcher_distribution_v0.py',
 'tools/required_gate_idempotence_launcher_package_v0.py',
 'tools/required_gate_idempotence_loader_binary_v0.py',
 'tools/required_gate_idempotence_loader_build_envelope_v0.py',
 'tools/required_gate_idempotence_loader_buildinfo_v0.py',
 'tools/required_gate_idempotence_loader_readout_v0.py',
 'tools/required_gate_idempotence_loader_rebuild_acceptance_v0.py',
 'tools/required_gate_idempotence_loader_rebuild_attestation_v0.py',
 'tools/required_gate_idempotence_loader_resolution_hosted_v0.py',
 'tools/required_gate_idempotence_loader_resolution_hosted_v0/Dockerfile',
 'tools/required_gate_idempotence_loader_resolution_hosted_v0/build_environment.py',
 'tools/required_gate_idempotence_loader_resolution_hosted_v0/environment.json',
 'tools/required_gate_idempotence_loader_resolution_hosted_v0/requirements.lock',
 'tools/required_gate_idempotence_loader_resolution_hosted_v0/run.py',
 'tools/required_gate_idempotence_loader_resolution_readout_v0.py',
 'tools/required_gate_idempotence_loader_resolution_v0.py',
 'tools/required_gate_idempotence_loader_source_v0.py',
 'tools/required_gate_idempotence_loader_startup_readout_v0.py',
 'tools/required_gate_idempotence_loader_startup_v0.py',
 'tools/required_gate_idempotence_loader_two_slot_v0.py',
 'tools/required_gate_idempotence_mapping_observation_v0.py',
 'tools/required_gate_idempotence_mapping_probe_v0.py',
 'tools/required_gate_idempotence_process_v0.py',
 'tools/required_gate_idempotence_runtime_v0.py',
 'tools/required_gate_idempotence_worker_v0.py')
REQUEST_SOURCE_PATHS = ('docs/compute/required_gate_idempotence_entry_stop_plan_v0/plan_v0.json',
 'schemas/required_gate_idempotence_entry_stop_plan_v0.schema.json',
 'schemas/required_gate_idempotence_entry_stop_v0.schema.json',
 'schemas/required_gate_idempotence_exec_stop_v0.schema.json',
 'schemas/required_gate_idempotence_loader_readout_contract_v0.schema.json',
 'schemas/required_gate_idempotence_loader_readout_event_v0.schema.json',
 'schemas/required_gate_idempotence_loader_rebuild_acceptance_v0.schema.json',
 'schemas/required_gate_idempotence_loader_resolution_v0.schema.json',
 'schemas/required_gate_idempotence_loader_startup_contract_v0.schema.json',
 'schemas/required_gate_idempotence_loader_startup_invocation_v0.schema.json',
 'schemas/required_gate_idempotence_loader_two_slot_qualification_v0.schema.json',
 'schemas/required_gate_idempotence_loader_two_slot_v0.schema.json',
 'schemas/required_gate_idempotence_mapping_observation_v0.schema.json',
 'tools/check_anchor_integrity_record_signatures_v0_1.py',
 'tools/check_required_gate_idempotence_entry_stop_plan_v0.py',
 'tools/check_required_gate_idempotence_entry_stop_v0.py',
 'tools/check_required_gate_idempotence_entry_task_guard_v0.py',
 'tools/check_required_gate_idempotence_exec_stop_v0.py',
 'tools/check_required_gate_idempotence_launcher_distribution_v0.py',
 'tools/check_required_gate_idempotence_loader_binary_binding_v0.py',
 'tools/check_required_gate_idempotence_loader_build_record_binding_v0.py',
 'tools/check_required_gate_idempotence_loader_readout_contract_v0.py',
 'tools/check_required_gate_idempotence_loader_rebuild_acceptance_v0.py',
 'tools/check_required_gate_idempotence_loader_rebuild_attestation_binding_v0.py',
 'tools/check_required_gate_idempotence_loader_resolution_plan_v0.py',
 'tools/check_required_gate_idempotence_loader_resolution_v0.py',
 'tools/check_required_gate_idempotence_loader_startup_contract_v0.py',
 'tools/check_required_gate_idempotence_loader_two_slot_qualification_v0.py',
 'tools/check_required_gate_idempotence_mapping_observation_v0.py',
 'tools/collect_required_gate_idempotence_loader_resolution_v0.py',
 'tools/prepare_required_gate_idempotence_entry_stop_v0.py',
 'tools/prepare_required_gate_idempotence_exec_stop_v0.py',
 'tools/prepare_required_gate_idempotence_loader_resolution_v0.py',
 'tools/qualify_required_gate_idempotence_entry_stop_v0.py',
 'tools/qualify_required_gate_idempotence_loader_two_slot_v0.py',
 'tools/required_gate_idempotence_distribution_signature_v0.py',
 'tools/required_gate_idempotence_elf_v0.py',
 'tools/required_gate_idempotence_entry_stop_v0.py',
 'tools/required_gate_idempotence_entry_task_guard_v0.py',
 'tools/required_gate_idempotence_exec_stop_hosted_io_v0.py',
 'tools/required_gate_idempotence_exec_stop_v0.py',
 'tools/required_gate_idempotence_launch_host_v0.py',
 'tools/required_gate_idempotence_launcher_distribution_v0.py',
 'tools/required_gate_idempotence_loader_binary_v0.py',
 'tools/required_gate_idempotence_loader_build_envelope_v0.py',
 'tools/required_gate_idempotence_loader_buildinfo_v0.py',
 'tools/required_gate_idempotence_loader_readout_v0.py',
 'tools/required_gate_idempotence_loader_rebuild_acceptance_v0.py',
 'tools/required_gate_idempotence_loader_rebuild_attestation_v0.py',
 'tools/required_gate_idempotence_loader_resolution_readout_v0.py',
 'tools/required_gate_idempotence_loader_resolution_v0.py',
 'tools/required_gate_idempotence_loader_source_v0.py',
 'tools/required_gate_idempotence_loader_startup_readout_v0.py',
 'tools/required_gate_idempotence_loader_startup_v0.py',
 'tools/required_gate_idempotence_loader_two_slot_v0.py',
 'tools/required_gate_idempotence_mapping_observation_v0.py',
 'tools/required_gate_idempotence_mapping_probe_v0.py',
 'tools/required_gate_idempotence_process_v0.py')
SOURCE_LIMITS = {'preservation/required_gate_idempotence_entry_stop_v0/run_44740993943_attempt_1/control_evidence_v0.zip': 5682024,
 'preservation/required_gate_idempotence_exec_stop_v0/original_inputs_v0.zip': 24816167,
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/Sources.xz.part001': 8000000,
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/Sources.xz.part002': 2540436,
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/glibc_2.41.orig.tar.xz.part001': 8000000,
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/glibc_2.41.orig.tar.xz.part002': 8000000,
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/glibc_2.41.orig.tar.xz.part003': 4323540,
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/libc6-dbg_2.41-12+deb13u4_amd64.deb': 7373052,
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/libc6_2.41-12+deb13u4_amd64.deb': 2846580}
BOUNDARY = {'original_acquisition_authorized': False,
 'native_acquisition_performed': False,
 'consumer_resolution_observed': False,
 'loader_resolution_verified': False,
 'complete_native_closure_verified': False,
 'physical_execution_authenticated': False,
 'full_runtime_observed': False,
 'containment_enforced': False,
 'selected_runtime_executed': False,
 'production_gate_eligible': False,
 'b2_complete': False,
 'metric_pass': None,
 'authority_effect': 'none'}
CONTROL_LIMIT = MAX_CONTROL_BYTES = 1048576
SOURCE_LIMIT = MAX_SOURCE_BYTES = 32 * 1024 * 1024
COMMAND_LIMIT = 4 * 1024 * 1024
FILE_LIMIT = 256 * 1024 * 1024
TOTAL_LIMIT = 768 * 1024 * 1024
FILE_COUNT_LIMIT = 1024
CAPTURE_LIMIT = 64 * 1024 * 1024
CAPTURE_FILE_COUNT_LIMIT = 512
ACCEPTED_POLICY_SHA256 = "1b1e4f414ffa7e56a8494f8a6d6051594c800cae978fa90585c4a02041bed953"
CAPTURE_PROFILE = "linux_x86_64_original_launcher_loader_resolution_v0"
ENVIRONMENT_BINDING = {'size_bytes': 25603, 'sha256': '5333e5db7fef71514c30a7a4a64412accf520a6d06bd2e9ffa20eaf718495389'}
OBSERVER_BINDING = {"size_bytes": 14472,
    "sha256": "92d7e40ec50be176cb1b790c7568b7e08cd862137b5aa69f1413ba1967886b79"}
SELECTION_TYPE = "required_gate_idempotence_loader_resolution_hosted_selection_v0"
PLAN_TYPE = "required_gate_idempotence_loader_resolution_hosted_container_plan_v0"
SUMMARY_TYPE = "required_gate_idempotence_loader_resolution_hosted_summary_v0"
RECEIPT_TYPE = "required_gate_idempotence_loader_resolution_hosted_receipt_v0"
PREFIX_TYPE = "required_gate_idempotence_loader_resolution_hosted_prefix_v0"
HOST_COMMANDS = (
    "git-head-before", "git-source-tree", "git-head-after", "base-pull",
    "base-inspect", "base-tag", "base-save", "base-load", "base-tag-inspect",
    "base-inspect-after", "image-build", "image-inspect", "container-create",
    "container-inspect", "container-start", "container-state",
    "container-ownership-inspect", "container-remove", "container-absence",
    "artifact-metadata", "attestation-verify",
)
INNER_COMMANDS = ("observe", "capture-check-1", "capture-check-2")
# Fixed build material roster remains readable even after environment drift.
MATERIAL_BINDINGS = {'debs/gpg_2.4.7-21+deb13u1+b5_amd64.deb': {'sha256': '3aeedf3d223e5e6aff08f03227af6ce308f4317472609f383350fd2ec20d33ae',
                                            'size_bytes': 636212},
 'debs/gpgconf_2.4.7-21+deb13u1+b5_amd64.deb': {'sha256': '14668f3f4847d2544bdff03c2ca8dbdd2fe0ad1bc7ded00941db291954c60f1b',
                                                'size_bytes': 128880},
 'debs/libassuan9_3.0.2-2_amd64.deb': {'sha256': '9d78ef8f016e7f24b5e20d1ce91939fe0f1f897e5f9059793201e930ded7eb8e',
                                       'size_bytes': 61520},
 'debs/libgcrypt20_1.11.0-7+deb13u1_amd64.deb': {'sha256': 'f0eb41f8cb40896e0822e9ab65611e8383c12b721c76c54764f744abb4a8c247',
                                                 'size_bytes': 843104},
 'debs/libgpg-error0_1.51-4_amd64.deb': {'sha256': '22b95570fd41c113ef6f5651563b4d748292844baab1278a46eb940c1dec2322',
                                         'size_bytes': 82108},
 'debs/libksba8_1.6.7-2+b1_amd64.deb': {'sha256': '45bc1bfaf41a5e1136b1c1f58c495a950888da33a617de24202f3568e45b9572',
                                        'size_bytes': 136048},
 'debs/libnpth0t64_1.8-3_amd64.deb': {'sha256': '37d489976ef91ca0165a7789a7a7ac5923ee3cfadf316ac3e87582e15d0523d7',
                                      'size_bytes': 23248},
 'native/bwrap': {'sha256': '573236e5328ac2ebb08f59ae3a9805b4f8d12bdef14be8af4450d5463294985f',
                  'size_bytes': 80248},
 'native/ld-linux-x86-64.so.2': {'sha256': 'c8438e4fde1934e61c88311633f00949ff645d5c04cdb8671fa3d78164d2f307',
                                 'size_bytes': 225672},
 'native/libc.so.6': {'sha256': '9792e3cbb541c8f44c7acf5f14f4022ea62998ecc787d326bed4d8b6547dfd92',
                      'size_bytes': 1995216},
 'native/libcap.so.2': {'sha256': '41217b0af128444f66dee8adda52b2ceaf19da00e5b0b155e2b87b857671286b',
                        'size_bytes': 47288},
 'native/libpcre2-8.so.0': {'sha256': '92e9b4167f9bbc237ca8f5526d82ee99ec9f8dbd0270ef1dd0ab24e2217f48e3',
                            'size_bytes': 711216},
 'native/libselinux.so.1': {'sha256': '5cb5293b4e7590463b94f7b23152d54807a6a2ccaf8cac9e343908c6692c086c',
                            'size_bytes': 202984},
 'wheels/attrs-26.1.0-py3-none-any.whl': {'sha256': 'c647aa4a12dfbad9333ca4e71fe62ddc36f4e63b2d260a37a8b83d2f043ac309',
                                          'size_bytes': 67548},
 'wheels/jsonschema-4.26.0-py3-none-any.whl': {'sha256': 'd489f15263b8d200f8387e64b4c3a75f06629559fb73deb8fdfb525f2dab50ce',
                                               'size_bytes': 90630},
 'wheels/jsonschema_specifications-2025.9.1-py3-none-any.whl': {'sha256': '98802fee3a11ee76ecaca44429fda8a41bff98b00a0f2838151b113f210cc6fe',
                                                                'size_bytes': 18437},
 'wheels/pyyaml-6.0.3-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl': {'sha256': 'b8bb0864c5a28024fac8a632c443c87c5aa6f215c0b126c449ae1a150412f31d',
                                                                                                          'size_bytes': 806638},
 'wheels/referencing-0.37.0-py3-none-any.whl': {'sha256': '381329a9f99628c9069361716891d34ad94af76e461dcb0335825aecc7692231',
                                                'size_bytes': 26766},
 'wheels/rpds_py-2026.9.1-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl': {'sha256': '136a1c3fe4402b7008bc81cb62ee538481795b61a7e83df88dff3b3f02b726ff',
                                                                                        'size_bytes': 375426},
 'wheels/typing_extensions-4.16.0-py3-none-any.whl': {'sha256': '481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8',
                                                      'size_bytes': 45571}}
WHEEL_FILENAMES = tuple(path[7:] for path in MATERIAL_BINDINGS if path.startswith("wheels/"))

# Fixed raw roles, including a failed tenth return prefix; success remains nine.
CAPTURE_RAW_LIMITS = {'attempt_start.json': 1048576,
 'backings.prelaunch.json': 1048576,
 'child.fds.setup.json': 1048576,
 'child.pidfd.info.bin': 65536,
 'child.stat.setup.bin': 65536,
 'child.status.setup.bin': 65536,
 'context.after.json': 1048576,
 'context.before.json': 1048576,
 'cp0.auxv.after.bin': 1024,
 'cp0.auxv.before.bin': 1024,
 'cp0.child.exe.link.bin': 4096,
 'cp0.child.stat.after.bin': 65536,
 'cp0.child.stat.before.bin': 65536,
 'cp0.child.status.after.bin': 65536,
 'cp0.child.status.before.bin': 65536,
 'cp0.debug.armed.bin': 48,
 'cp0.debug.before.bin': 48,
 'cp0.environment.json': 1048576,
 'cp0.executable.elf': 65536,
 'cp0.fds.json': 1048576,
 'cp0.maps.after.bin': 65536,
 'cp0.maps.before.bin': 65536,
 'cp0.native.rx.sample0.bin': 3262624,
 'cp0.native.rx.sample1.bin': 3262624,
 'cp0.regs.after.bin': 216,
 'cp0.regs.before.bin': 216,
 'cp0.stack.strings.after.bin': 27,
 'cp0.stack.strings.before.bin': 27,
 'cp0.stack.words.after.bin': 1072,
 'cp0.stack.words.before.bin': 1072,
 'entry.auxv.after.bin': 1024,
 'entry.auxv.before.bin': 1024,
 'entry.child.exe.link.bin': 4096,
 'entry.child.stat.after.bin': 65536,
 'entry.child.stat.before.bin': 65536,
 'entry.child.status.after.bin': 65536,
 'entry.child.status.before.bin': 65536,
 'entry.debug.after.bin': 48,
 'entry.debug.before.bin': 48,
 'entry.environment.json': 1048576,
 'entry.executable.elf': 65536,
 'entry.fds.json': 1048576,
 'entry.maps.after.bin': 65536,
 'entry.maps.before.bin': 65536,
 'entry.native.rx.sample0.bin': 3262624,
 'entry.native.rx.sample1.bin': 3262624,
 'entry.regs.after.bin': 216,
 'entry.regs.before.bin': 216,
 'entry.siginfo.bin': 128,
 'exec.event_message.bin': 8,
 'guard.install.json': 1048576,
 'guard.program.bin': 4096,
 'guard.qualification.json': 1048576,
 'kernel.boot_id.bin': 128,
 'native.41217b0af128444f66dee8adda52b2ceaf19da00e5b0b155e2b87b857671286b.elf': 1995216,
 'native.573236e5328ac2ebb08f59ae3a9805b4f8d12bdef14be8af4450d5463294985f.elf': 1995216,
 'native.5cb5293b4e7590463b94f7b23152d54807a6a2ccaf8cac9e343908c6692c086c.elf': 1995216,
 'native.92e9b4167f9bbc237ca8f5526d82ee99ec9f8dbd0270ef1dd0ab24e2217f48e3.elf': 1995216,
 'native.9792e3cbb541c8f44c7acf5f14f4022ea62998ecc787d326bed4d8b6547dfd92.elf': 1995216,
 'native.c8438e4fde1934e61c88311633f00949ff645d5c04cdb8671fa3d78164d2f307.elf': 1995216,
 'observer.exe.bin': 67108864,
 'observer.stat.bin': 65536,
 'observer.status.bin': 65536,
 'original.admission.json': 1048576,
 'preload.before.json': 1048576,
 'preload.setup.json': 1048576,
 'request.json': 1048576,
 'resume.00.debug.bin': 48,
 'resume.01.debug.bin': 48,
 'resume.02.debug.bin': 48,
 'resume.03.debug.bin': 48,
 'resume.04.debug.bin': 48,
 'resume.05.debug.bin': 48,
 'resume.06.debug.bin': 48,
 'resume.07.debug.bin': 48,
 'resume.08.debug.bin': 48,
 'resume.09.debug.bin': 48,
 'resume.10.debug.bin': 48,
 'return.01.auxv.after.bin': 1024,
 'return.01.auxv.before.bin': 1024,
 'return.01.child.stat.after.bin': 65536,
 'return.01.child.stat.before.bin': 65536,
 'return.01.child.status.after.bin': 65536,
 'return.01.child.status.before.bin': 65536,
 'return.01.debug.after.bin': 48,
 'return.01.debug.before.bin': 48,
 'return.01.environment.json': 1048576,
 'return.01.fds.json': 1048576,
 'return.01.loader.rx.sample0.bin': 160721,
 'return.01.loader.rx.sample1.bin': 160721,
 'return.01.maps.after.bin': 65536,
 'return.01.maps.before.bin': 65536,
 'return.01.memory.sample0.bin': 131072,
 'return.01.memory.sample1.bin': 131072,
 'return.01.regs.after.bin': 216,
 'return.01.regs.before.bin': 216,
 'return.01.siginfo.bin': 128,
 'return.02.auxv.after.bin': 1024,
 'return.02.auxv.before.bin': 1024,
 'return.02.child.stat.after.bin': 65536,
 'return.02.child.stat.before.bin': 65536,
 'return.02.child.status.after.bin': 65536,
 'return.02.child.status.before.bin': 65536,
 'return.02.debug.after.bin': 48,
 'return.02.debug.before.bin': 48,
 'return.02.environment.json': 1048576,
 'return.02.fds.json': 1048576,
 'return.02.loader.rx.sample0.bin': 160721,
 'return.02.loader.rx.sample1.bin': 160721,
 'return.02.maps.after.bin': 65536,
 'return.02.maps.before.bin': 65536,
 'return.02.memory.sample0.bin': 131072,
 'return.02.memory.sample1.bin': 131072,
 'return.02.regs.after.bin': 216,
 'return.02.regs.before.bin': 216,
 'return.02.siginfo.bin': 128,
 'return.03.auxv.after.bin': 1024,
 'return.03.auxv.before.bin': 1024,
 'return.03.child.stat.after.bin': 65536,
 'return.03.child.stat.before.bin': 65536,
 'return.03.child.status.after.bin': 65536,
 'return.03.child.status.before.bin': 65536,
 'return.03.debug.after.bin': 48,
 'return.03.debug.before.bin': 48,
 'return.03.environment.json': 1048576,
 'return.03.fds.json': 1048576,
 'return.03.loader.rx.sample0.bin': 160721,
 'return.03.loader.rx.sample1.bin': 160721,
 'return.03.maps.after.bin': 65536,
 'return.03.maps.before.bin': 65536,
 'return.03.memory.sample0.bin': 131072,
 'return.03.memory.sample1.bin': 131072,
 'return.03.regs.after.bin': 216,
 'return.03.regs.before.bin': 216,
 'return.03.siginfo.bin': 128,
 'return.04.auxv.after.bin': 1024,
 'return.04.auxv.before.bin': 1024,
 'return.04.child.stat.after.bin': 65536,
 'return.04.child.stat.before.bin': 65536,
 'return.04.child.status.after.bin': 65536,
 'return.04.child.status.before.bin': 65536,
 'return.04.debug.after.bin': 48,
 'return.04.debug.before.bin': 48,
 'return.04.environment.json': 1048576,
 'return.04.fds.json': 1048576,
 'return.04.loader.rx.sample0.bin': 160721,
 'return.04.loader.rx.sample1.bin': 160721,
 'return.04.maps.after.bin': 65536,
 'return.04.maps.before.bin': 65536,
 'return.04.memory.sample0.bin': 131072,
 'return.04.memory.sample1.bin': 131072,
 'return.04.regs.after.bin': 216,
 'return.04.regs.before.bin': 216,
 'return.04.siginfo.bin': 128,
 'return.05.auxv.after.bin': 1024,
 'return.05.auxv.before.bin': 1024,
 'return.05.child.stat.after.bin': 65536,
 'return.05.child.stat.before.bin': 65536,
 'return.05.child.status.after.bin': 65536,
 'return.05.child.status.before.bin': 65536,
 'return.05.debug.after.bin': 48,
 'return.05.debug.before.bin': 48,
 'return.05.environment.json': 1048576,
 'return.05.fds.json': 1048576,
 'return.05.loader.rx.sample0.bin': 160721,
 'return.05.loader.rx.sample1.bin': 160721,
 'return.05.maps.after.bin': 65536,
 'return.05.maps.before.bin': 65536,
 'return.05.memory.sample0.bin': 131072,
 'return.05.memory.sample1.bin': 131072,
 'return.05.regs.after.bin': 216,
 'return.05.regs.before.bin': 216,
 'return.05.siginfo.bin': 128,
 'return.06.auxv.after.bin': 1024,
 'return.06.auxv.before.bin': 1024,
 'return.06.child.stat.after.bin': 65536,
 'return.06.child.stat.before.bin': 65536,
 'return.06.child.status.after.bin': 65536,
 'return.06.child.status.before.bin': 65536,
 'return.06.debug.after.bin': 48,
 'return.06.debug.before.bin': 48,
 'return.06.environment.json': 1048576,
 'return.06.fds.json': 1048576,
 'return.06.loader.rx.sample0.bin': 160721,
 'return.06.loader.rx.sample1.bin': 160721,
 'return.06.maps.after.bin': 65536,
 'return.06.maps.before.bin': 65536,
 'return.06.memory.sample0.bin': 131072,
 'return.06.memory.sample1.bin': 131072,
 'return.06.regs.after.bin': 216,
 'return.06.regs.before.bin': 216,
 'return.06.siginfo.bin': 128,
 'return.07.auxv.after.bin': 1024,
 'return.07.auxv.before.bin': 1024,
 'return.07.child.stat.after.bin': 65536,
 'return.07.child.stat.before.bin': 65536,
 'return.07.child.status.after.bin': 65536,
 'return.07.child.status.before.bin': 65536,
 'return.07.debug.after.bin': 48,
 'return.07.debug.before.bin': 48,
 'return.07.environment.json': 1048576,
 'return.07.fds.json': 1048576,
 'return.07.loader.rx.sample0.bin': 160721,
 'return.07.loader.rx.sample1.bin': 160721,
 'return.07.maps.after.bin': 65536,
 'return.07.maps.before.bin': 65536,
 'return.07.memory.sample0.bin': 131072,
 'return.07.memory.sample1.bin': 131072,
 'return.07.regs.after.bin': 216,
 'return.07.regs.before.bin': 216,
 'return.07.siginfo.bin': 128,
 'return.08.auxv.after.bin': 1024,
 'return.08.auxv.before.bin': 1024,
 'return.08.child.stat.after.bin': 65536,
 'return.08.child.stat.before.bin': 65536,
 'return.08.child.status.after.bin': 65536,
 'return.08.child.status.before.bin': 65536,
 'return.08.debug.after.bin': 48,
 'return.08.debug.before.bin': 48,
 'return.08.environment.json': 1048576,
 'return.08.fds.json': 1048576,
 'return.08.loader.rx.sample0.bin': 160721,
 'return.08.loader.rx.sample1.bin': 160721,
 'return.08.maps.after.bin': 65536,
 'return.08.maps.before.bin': 65536,
 'return.08.memory.sample0.bin': 131072,
 'return.08.memory.sample1.bin': 131072,
 'return.08.regs.after.bin': 216,
 'return.08.regs.before.bin': 216,
 'return.08.siginfo.bin': 128,
 'return.09.auxv.after.bin': 1024,
 'return.09.auxv.before.bin': 1024,
 'return.09.child.stat.after.bin': 65536,
 'return.09.child.stat.before.bin': 65536,
 'return.09.child.status.after.bin': 65536,
 'return.09.child.status.before.bin': 65536,
 'return.09.debug.after.bin': 48,
 'return.09.debug.before.bin': 48,
 'return.09.environment.json': 1048576,
 'return.09.fds.json': 1048576,
 'return.09.loader.rx.sample0.bin': 160721,
 'return.09.loader.rx.sample1.bin': 160721,
 'return.09.maps.after.bin': 65536,
 'return.09.maps.before.bin': 65536,
 'return.09.memory.sample0.bin': 131072,
 'return.09.memory.sample1.bin': 131072,
 'return.09.regs.after.bin': 216,
 'return.09.regs.before.bin': 216,
 'return.09.siginfo.bin': 128,
 'return.10.auxv.after.bin': 1024,
 'return.10.auxv.before.bin': 1024,
 'return.10.child.stat.after.bin': 65536,
 'return.10.child.stat.before.bin': 65536,
 'return.10.child.status.after.bin': 65536,
 'return.10.child.status.before.bin': 65536,
 'return.10.debug.after.bin': 48,
 'return.10.debug.before.bin': 48,
 'return.10.environment.json': 1048576,
 'return.10.fds.json': 1048576,
 'return.10.loader.rx.sample0.bin': 160721,
 'return.10.loader.rx.sample1.bin': 160721,
 'return.10.maps.after.bin': 65536,
 'return.10.maps.before.bin': 65536,
 'return.10.memory.sample0.bin': 131072,
 'return.10.memory.sample1.bin': 131072,
 'return.10.regs.after.bin': 216,
 'return.10.regs.before.bin': 216,
 'return.10.siginfo.bin': 128,
 'setup.debug.before.bin': 48,
 'source_build.admission.json': 1048576,
 'stderr.bin': 4096,
 'stdout.bin': 4096,
 'two_slot.qualification.json': 1048576,
 'unexpected.debug.bin': 48,
 'unexpected.event_message.bin': 8,
 'unexpected.regs.bin': 216,
 'unexpected.siginfo.bin': 128}

CONTEXT_KEYS = frozenset(("repository", "repository_id", "source_commit", "workflow_sha",
    "workflow_ref", "run_id", "run_number", "run_attempt", "event_name", "ref",
    "actor", "triggering_actor", "acknowledgement", "accepted_policy_sha256"))
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
IMAGE_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
ERROR_RE = re.compile(r"[a-z][a-z0-9_]{0,127}\Z")


class HostedError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise HostedError(code)


def canonical(value):
    return core.canonical(value)


def binding(value):
    _need(type(value) is bytes, "loader_resolution_hosted_binding_type")
    return {"size_bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}


def _same(actual, expected, code):
    _need(canonical(actual) == canonical(expected), code)


def _keys(value, keys, code):
    _need(type(value) is dict and set(value) == set(keys), code)


def _descriptor(value, maximum=FILE_LIMIT, minimum=0):
    _keys(value, ("size_bytes", "sha256"), "loader_resolution_hosted_descriptor_fields")
    _need(type(value["size_bytes"]) is int and minimum <= value["size_bytes"] <= maximum,
          "loader_resolution_hosted_descriptor_extent")
    _need(type(value["sha256"]) is str and HEX64.fullmatch(value["sha256"]),
          "loader_resolution_hosted_descriptor_digest")


def _pairs(items):
    result = {}
    for key, value in items:
        _need(key not in result, "loader_resolution_hosted_duplicate_key")
        result[key] = value
    return result


def _noninteger(_value):
    raise HostedError("loader_resolution_hosted_noninteger_json")


def _nonfinite(_value):
    raise HostedError("loader_resolution_hosted_nonfinite_json")


def _parse(value, limit, floats):
    _need(type(value) is bytes and 0 < len(value) <= limit, "loader_resolution_hosted_json_extent")
    try:
        result = json.loads(value.decode("ascii"), object_pairs_hook=_pairs,
            parse_float=float if floats else _noninteger, parse_constant=_nonfinite)
        pending, count = [(result, 0)], 0
        while pending:
            item, depth = pending.pop()
            count += 1
            _need(count <= 32768 and depth <= 32, "loader_resolution_hosted_json_structure")
            if type(item) is dict:
                _need(len(item) <= FILE_COUNT_LIMIT, "loader_resolution_hosted_json_structure")
                for key, child in item.items():
                    _need(type(key) is str and len(key) <= 4096, "loader_resolution_hosted_json_key")
                    pending.append((child, depth + 1))
            elif type(item) is list:
                _need(len(item) <= FILE_COUNT_LIMIT, "loader_resolution_hosted_json_structure")
                pending.extend((child, depth + 1) for child in item)
            elif type(item) is str:
                _need(len(item) <= 16384, "loader_resolution_hosted_json_string")
            else:
                _need(item is None or type(item) is bool or
                      (type(item) is int and -(1 << 63) < item < (1 << 63)) or
                      (floats and type(item) is float and math.isfinite(item)),
                      "loader_resolution_hosted_json_value")
        return result
    except HostedError:
        raise
    except (UnicodeError, ValueError, RecursionError, OverflowError) as exc:
        raise HostedError("loader_resolution_hosted_invalid_json") from exc


def parse(value, limit=CONTROL_LIMIT):
    """Small protocol controls permit integers, never floats or duplicate keys."""
    return _parse(value, limit, False)


def parse_external(value, limit=COMMAND_LIMIT):
    """Generic command/Docker diagnostics permit only finite numeric values."""
    return _parse(value, limit, True)


def read_regular(path, limit=CONTROL_LIMIT, *, empty=False):
    return core.read_regular(path, limit, empty=empty)


def write_new(path, value):
    data = value if type(value) is bytes else canonical(value)
    """Publish only through a newly owned descriptor; invalidate on any failure."""
    _need(type(data) is bytes and 0 < len(data) <= CONTROL_LIMIT,
          "loader_resolution_hosted_output_extent")
    parent, name = core._open_parent(path)
    descriptor = None
    owned = None
    closing_descriptor = None
    try:
        descriptor = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
                             | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        owned = os.fstat(descriptor)
        _need(stat.S_ISREG(owned.st_mode) and owned.st_nlink == 1,
              "loader_resolution_hosted_output_identity")
        core._parent_unchanged(path, parent, name)
        remaining = memoryview(data)
        while remaining:
            count = os.write(descriptor, remaining)
            _need(count > 0, "loader_resolution_hosted_output_write")
            remaining = remaining[count:]
        os.fsync(descriptor)
        core._output_exact(descriptor, owned, data)
        current = os.stat(name, dir_fd=parent, follow_symlinks=False)
        _need((owned.st_dev, owned.st_ino) == (current.st_dev, current.st_ino)
              and current.st_nlink == 1, "loader_resolution_hosted_output_replaced")
        core._parent_unchanged(path, parent, name)
        os.fsync(parent)
        core._output_exact(descriptor, owned, data)
        current = os.stat(name, dir_fd=parent, follow_symlinks=False)
        _need((owned.st_dev, owned.st_ino) == (current.st_dev, current.st_ino)
              and current.st_nlink == 1, "loader_resolution_hosted_output_replaced")
        core._parent_unchanged(path, parent, name)
        # Closing is part of publication, not a fallible finally after success.
        # Keep the owned file descriptor while closing the parent, so a failed
        # directory close can still invalidate the exact newly created inode.
        closing_parent = parent
        parent = None
        os.close(closing_parent)
        core._output_exact(descriptor, owned, data)
        closing_descriptor = descriptor
        descriptor = None
        os.close(closing_descriptor)
        closing_descriptor = None
    except BaseException:
        # Do not retry a failed close: it may already have consumed the fd.
        # Identity-checked invalidation can use the still-owned fd or reopen
        # only the exact inode, without closing a possibly reused fd number.
        core._invalidate_output(path, descriptor if descriptor is not None else closing_descriptor, owned)
        raise
    finally:
        for item in (descriptor, parent):
            if item is not None:
                try:
                    os.close(item)
                except OSError:
                    pass

    return binding(data)


def _json(path, limit=CONTROL_LIMIT, *, external=False):
    raw = read_regular(path, limit)
    return parse_external(raw, limit) if external else parse(raw, limit)


def validate_context(ctx):
    _keys(ctx, CONTEXT_KEYS, "loader_resolution_hosted_context_fields")
    _need(ctx["repository"] == REPOSITORY and ctx["repository_id"] == REPOSITORY_ID
          and ctx["actor"] == ctx["triggering_actor"] == "HKati"
          and ctx["event_name"] == "workflow_dispatch" and ctx["ref"] == "refs/heads/main"
          and ctx["workflow_ref"] == REPOSITORY + "/" + WORKFLOW + "@refs/heads/main"
          and ctx["acknowledgement"] == ACKNOWLEDGEMENT
          and ctx["accepted_policy_sha256"] == ACCEPTED_POLICY_SHA256,
          "loader_resolution_hosted_context_selection")
    _need(type(ctx["source_commit"]) is str and
          re.fullmatch(r"[0-9a-f]{40}", ctx["source_commit"]) is not None and
          ctx["workflow_sha"] == ctx["source_commit"], "loader_resolution_hosted_source_commit")
    _need(type(ctx["run_attempt"]) is int and ctx["run_attempt"] == 1 and
          all(type(ctx[key]) is int and 0 < ctx[key] < (1 << 63)
              for key in ("run_id", "run_number")), "loader_resolution_hosted_run_identity")
    return ctx


def context(environ=None):
    env = os.environ if environ is None else environ
    def number(key):
        value = env.get(key, "")
        _need(type(value) is str and re.fullmatch(r"[1-9][0-9]{0,18}", value),
              "loader_resolution_hosted_context_number")
        return int(value)
    ctx = {"repository": env.get("GITHUB_REPOSITORY"),
        "repository_id": env.get("GITHUB_REPOSITORY_ID"),
        "source_commit": env.get("GITHUB_SHA"), "workflow_sha": env.get("GITHUB_WORKFLOW_SHA"),
        "workflow_ref": env.get("GITHUB_WORKFLOW_REF"), "run_id": number("GITHUB_RUN_ID"),
        "run_number": number("GITHUB_RUN_NUMBER"), "run_attempt": number("GITHUB_RUN_ATTEMPT"),
        "event_name": env.get("GITHUB_EVENT_NAME"), "ref": env.get("GITHUB_REF"),
        "actor": env.get("GITHUB_ACTOR"), "triggering_actor": env.get("GITHUB_TRIGGERING_ACTOR"),
        "acknowledgement": env.get("LOADER_RESOLUTION_HOSTED_ACKNOWLEDGEMENT"),
        "accepted_policy_sha256": env.get("ACCEPTED_POLICY_SHA256")}
    validate_context(ctx)
    _need(env.get("EXPECTED_SOURCE_COMMIT") == ctx["source_commit"],
          "loader_resolution_hosted_expected_source")
    return ctx


def request_identity(ctx):
    validate_context(ctx)
    return hashlib.sha256(canonical({"profile": PROFILE, "context": ctx})).hexdigest()[:32]


def environment():
    raw = read_regular(ROOT / CONFIG / "environment.json", CONTROL_LIMIT)
    _same(binding(raw), ENVIRONMENT_BINDING, "loader_resolution_hosted_environment_selection")
    selected = parse(raw)
    _need(selected["profile"] == PROFILE and selected["python"]["observer_binding"] == OBSERVER_BINDING,
          "loader_resolution_hosted_environment_profile")
    return selected


def validate_build_record(record, selected, environment_binding=None, requirements_binding=None):
    """Check the closed offline build statement against selected input bytes."""
    environment_binding = ENVIRONMENT_BINDING if environment_binding is None else environment_binding
    requirements_binding = selected["requirements"] if requirements_binding is None else requirements_binding
    _same(environment_binding, ENVIRONMENT_BINDING, "loader_resolution_hosted_build_environment")
    _same(requirements_binding, selected["requirements"], "loader_resolution_hosted_build_requirements")
    fixed = {
        "record_type": "required_gate_idempotence_loader_resolution_hosted_environment_build_v0",
        "profile": PROFILE, "environment_selection": environment_binding,
        "requirements_lock": requirements_binding,
        "base_image_reference": selected["base_image"]["reference"], "python_version": PYTHON_VERSION,
        "installed_debian_delta": [{"name": item["name"], "version": item["version"]}
                                   for item in selected["debian"]["packages"]],
        "selected_python_packages": [{"name": item["name"], "version": item["version"]}
                                     for item in selected["python"]["packages"]],
        "native_object_restorations": [{**item, "action": "restored_selected_base_original",
            "observed_before": item["before"], "observed_after": item["after"]}
            for item in selected["native_object_restorations"]],
        "offline_install": True, "reproducible_image_claimed": False,
        "host_environment_qualified": False, "native_acquisition_performed": False,
        "authority_effect": "none",
    }
    _keys(record, (*fixed, "checked_files", "original_native_objects", "openssl_backend"),
          "loader_resolution_hosted_build_record_fields")
    for key, value in fixed.items():
        _same(record[key], value, "loader_resolution_hosted_build_record_selection")
    checked = record["checked_files"]
    _need(type(checked) is list and len(checked) == len(selected["expected_files"]),
          "loader_resolution_hosted_build_runtime_roster")
    for actual, wanted in zip(checked, selected["expected_files"]):
        _keys(actual, (*wanted, "resolved_path"), "loader_resolution_hosted_build_runtime_fields")
        _same({key: actual[key] for key in wanted}, wanted, "loader_resolution_hosted_build_runtime_binding")
        _mount_source(actual["resolved_path"])
    native = record["original_native_objects"]
    _need(type(native) is list and len(native) == len(selected["original_native_objects"]),
          "loader_resolution_hosted_build_original_roster")
    for actual, wanted in zip(native, selected["original_native_objects"]):
        _keys(actual, (*wanted, "resolved_path", "action"), "loader_resolution_hosted_build_original_fields")
        _same({key: actual[key] for key in wanted}, wanted, "loader_resolution_hosted_build_original_binding")
        if wanted["host_path"] is None:
            _need(actual["action"] == "retained_data_only" and actual["resolved_path"] is None,
                  "loader_resolution_hosted_build_launcher_data")
        else:
            actions = ("existing_original_verified",) if wanted["installation"] == "require_existing_exact" else (
                "existing_original_verified", "installed_absent_original")
            _need(actual["action"] in actions, "loader_resolution_hosted_build_original_action")
            _mount_source(actual["resolved_path"])
            runtime = next(item for item in checked if item["path"] == wanted["host_path"])
            _need(actual["resolved_path"] == runtime["resolved_path"],
                  "loader_resolution_hosted_build_original_runtime_join")
    for restoration in selected["native_object_restorations"]:
        runtime = next(item for item in checked if item["path"] == restoration["host_path"])
        original = next(item for item in native if item["input"] == restoration["input"])
        _need(runtime["resolved_path"] == original["resolved_path"] == restoration["resolved_path"]
              and original["action"] == "existing_original_verified",
              "loader_resolution_hosted_build_restoration_layout")
        for item in (runtime, original):
            _same({key: item[key] for key in ("size_bytes", "sha256")}, restoration["after"],
                  "loader_resolution_hosted_build_restoration_binding")
    backend = record["openssl_backend"]
    _keys(backend, ("path", "binary_sha256", "version", "suite", "known_answer_self_test"),
          "loader_resolution_hosted_build_backend_fields")
    wanted = next(item for item in selected["expected_files"] if item["path"] == "/usr/bin/openssl")
    _need(backend["path"] == wanted["path"] and backend["binary_sha256"] == wanted["sha256"]
          and backend["suite"] == "ed25519" and backend["known_answer_self_test"] == "passed"
          and type(backend["version"]) is str and 0 < len(backend["version"]) <= 256
          and re.match(r"^OpenSSL 3\.[0-9]+\.", backend["version"]) is not None
          and all(32 <= ord(c) < 127 for c in backend["version"]),
          "loader_resolution_hosted_build_backend_selection")
    return record


def source_limit(path):
    _need(path in SOURCE_PATHS, "loader_resolution_hosted_source_path")
    return SOURCE_LIMITS.get(path, 1048576)


def source_bindings():
    return {name: binding(read_regular(ROOT / name, source_limit(name))) for name in SOURCE_PATHS}


def _sources(value):
    _keys(value, SOURCE_PATHS, "loader_resolution_hosted_source_roster")
    for path, selected in value.items():
        _descriptor(selected, source_limit(path), 1)


def validate_handoff(value):
    _keys(value, ("artifact_id", "artifact_digest", "receipt_sha256"), "loader_resolution_hosted_handoff_fields")
    _need(type(value["artifact_id"]) is int and 0 < value["artifact_id"] < (1 << 63),
          "loader_resolution_hosted_artifact_id")
    _need(type(value["artifact_digest"]) is str and IMAGE_RE.fullmatch(value["artifact_digest"]),
          "loader_resolution_hosted_artifact_digest")
    _need(type(value["receipt_sha256"]) is str and HEX64.fullmatch(value["receipt_sha256"]),
          "loader_resolution_hosted_receipt_digest")
    return value


def handoff(environ=None):
    env = os.environ if environ is None else environ
    value = env.get("LOADER_RESOLUTION_HOSTED_ARTIFACT_ID", "")
    _need(type(value) is str and re.fullmatch(r"[1-9][0-9]{0,18}", value), "loader_resolution_hosted_artifact_id")
    return validate_handoff({"artifact_id": int(value),
        "artifact_digest": env.get("LOADER_RESOLUTION_HOSTED_ARTIFACT_DIGEST"),
        "receipt_sha256": env.get("EXPECTED_RECEIPT_SHA256")})


def make_selection(phase, ctx, image_id, sources, environment_binding, handoff=None):
    result = {"record_type": SELECTION_TYPE, "profile": PROFILE, "phase": phase,
        "context": ctx, "image_id": image_id, "sources": sources,
        "environment": environment_binding, "handoff": handoff, "boundary": dict(BOUNDARY)}
    return validate_selection(result, phase)


def validate_selection(value, phase):
    _keys(value, ("record_type", "profile", "phase", "context", "image_id", "sources",
                  "environment", "handoff", "boundary"), "loader_resolution_hosted_selection_fields")
    _need(phase in ("acquire", "verify") and value["phase"] == phase and
          value["record_type"] == SELECTION_TYPE and value["profile"] == PROFILE,
          "loader_resolution_hosted_selection_profile")
    validate_context(value["context"])
    _need(type(value["image_id"]) is str and IMAGE_RE.fullmatch(value["image_id"]),
          "loader_resolution_hosted_image_id")
    _sources(value["sources"])
    _same(value["environment"], ENVIRONMENT_BINDING, "loader_resolution_hosted_environment_selection")
    _same(value["sources"][CONFIG + "/environment.json"], value["environment"],
          "loader_resolution_hosted_environment_source")
    _same(value["boundary"], BOUNDARY, "loader_resolution_hosted_boundary")
    if phase == "verify":
        validate_handoff(value["handoff"])
    else:
        _need(value["handoff"] is None, "loader_resolution_hosted_acquisition_handoff")
    _need(len(canonical(value)) <= CONTROL_LIMIT, "loader_resolution_hosted_control_extent")
    return value


def expected_env(ctx, phase, image_id, handoff=None):
    validate_context(ctx)
    _need(phase in ("acquire", "verify") and type(image_id) is str and IMAGE_RE.fullmatch(image_id),
          "loader_resolution_hosted_environment_phase")
    result = {"EXPECTED_SOURCE_COMMIT": ctx["source_commit"],
        "ACCEPTED_POLICY_SHA256": ctx["accepted_policy_sha256"],
        "LOADER_RESOLUTION_HOSTED_ACKNOWLEDGEMENT": ACKNOWLEDGEMENT,
        "LOADER_RESOLUTION_HOSTED_PHASE": phase, "LOADER_RESOLUTION_HOSTED_IMAGE_ID": image_id,
        "GITHUB_REPOSITORY": REPOSITORY, "GITHUB_REPOSITORY_ID": REPOSITORY_ID,
        "GITHUB_SHA": ctx["source_commit"], "GITHUB_WORKFLOW_SHA": ctx["workflow_sha"],
        "GITHUB_WORKFLOW_REF": ctx["workflow_ref"], "GITHUB_RUN_ID": str(ctx["run_id"]),
        "GITHUB_RUN_NUMBER": str(ctx["run_number"]), "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
        "GITHUB_ACTOR": "HKati", "GITHUB_TRIGGERING_ACTOR": "HKati",
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "LC_ALL": "C", "TZ": "UTC"}
    if handoff is not None:
        _need(phase == "verify", "loader_resolution_hosted_acquisition_handoff")
        validate_handoff(handoff)
        result.update(LOADER_RESOLUTION_HOSTED_ARTIFACT_ID=str(handoff["artifact_id"]),
            LOADER_RESOLUTION_HOSTED_ARTIFACT_DIGEST=handoff["artifact_digest"],
            EXPECTED_RECEIPT_SHA256=handoff["receipt_sha256"])
    return result


def _environment_map(value):
    _need(type(value) is list and len(value) <= 128, "loader_resolution_hosted_image_environment")
    result = {}
    for entry in value:
        _need(type(entry) is str and "=" in entry and len(entry) <= 8192 and
              "\x00" not in entry and "\n" not in entry, "loader_resolution_hosted_image_environment")
        key, item = entry.split("=", 1)
        _need(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) and key not in result,
              "loader_resolution_hosted_image_environment")
        result[key] = item
    return result


def container_name(ctx, phase):
    return "pulse-loader-resolution-" + str(ctx["run_id"]) + "-1-" + phase


def container_labels(ctx, phase):
    return {"org.pulsemech.loader-resolution.run": str(ctx["run_id"]) + "/1",
        "org.pulsemech.loader-resolution.source": ctx["source_commit"],
        "org.pulsemech.loader-resolution.profile": PROFILE, "org.pulsemech.loader-resolution.phase": phase}


def _mount_source(value):
    _need(type(value) is str and Path(value).is_absolute() and len(value) <= 4096 and
          ".." not in Path(value).parts and not any(c in value for c in (",", "\n", "\r", "\x00")),
          "loader_resolution_hosted_mount_path")


def make_container_plan(phase, ctx, image_id, uid, gid, root, image_environment,
                        selection_binding, previous=None, handoff=None):
    root = Path(root)
    mounts = [{"source": str(root / "source"), "target": "/repo", "readonly": True},
        {"source": str(root / "control"), "target": "/control", "readonly": True},
        {"source": str(root / ("observation" if phase == "acquire" else "verification")),
         "target": "/output", "readonly": False}]
    _need((previous is not None) == (phase == "verify"), "loader_resolution_hosted_input_mount")
    if previous is not None:
        mounts.append({"source": str(previous), "target": "/input", "readonly": True})
    value = {"record_type": PLAN_TYPE, "profile": PROFILE, "phase": phase, "context": ctx,
        "image_id": image_id, "uid": uid, "gid": gid, "name": container_name(ctx, phase),
        "labels": container_labels(ctx, phase), "image_environment": image_environment,
        "environment": expected_env(ctx, phase, image_id, handoff),
        "mounts": sorted(mounts, key=lambda item: item["target"]), "entrypoint": [PYTHON],
        "command": ["-I", "-B", "/repo/" + CONFIG + "/run.py", phase],
        "selection": selection_binding}
    return validate_container_plan(value, phase, handoff=handoff)


def validate_container_plan(value, phase, *, handoff=None):
    _keys(value, ("record_type", "profile", "phase", "context", "image_id", "uid", "gid",
        "name", "labels", "image_environment", "environment", "mounts", "entrypoint",
        "command", "selection"), "loader_resolution_hosted_plan_fields")
    _need(phase in ("acquire", "verify") and value["phase"] == phase and
          value["record_type"] == PLAN_TYPE and value["profile"] == PROFILE,
          "loader_resolution_hosted_plan_profile")
    validate_context(value["context"])
    _need(type(value["image_id"]) is str and IMAGE_RE.fullmatch(value["image_id"]), "loader_resolution_hosted_image_id")
    _need(all(type(value[key]) is int and 0 < value[key] < (1 << 31) for key in ("uid", "gid")),
          "loader_resolution_hosted_nonroot_user")
    _same(value["labels"], container_labels(value["context"], phase), "loader_resolution_hosted_plan_labels")
    _need(value["name"] == container_name(value["context"], phase), "loader_resolution_hosted_plan_name")
    _environment_map(value["image_environment"])
    _same(value["environment"], expected_env(value["context"], phase, value["image_id"], handoff),
          "loader_resolution_hosted_plan_environment")
    _same(value["entrypoint"], [PYTHON], "loader_resolution_hosted_plan_entrypoint")
    _same(value["command"], ["-I", "-B", "/repo/" + CONFIG + "/run.py", phase],
          "loader_resolution_hosted_plan_command")
    _descriptor(value["selection"], CONTROL_LIMIT, 1)
    targets = ["/control", "/input", "/output", "/repo"] if phase == "verify" else ["/control", "/output", "/repo"]
    _need(type(value["mounts"]) is list and len(value["mounts"]) == len(targets), "loader_resolution_hosted_plan_mounts")
    for mount, target in zip(value["mounts"], targets):
        _keys(mount, ("source", "target", "readonly"), "loader_resolution_hosted_plan_mounts")
        _mount_source(mount["source"])
        _need(mount["target"] == target and type(mount["readonly"]) is bool and
              mount["readonly"] == (target != "/output"), "loader_resolution_hosted_plan_mounts")
    return value


def _native_report(value, request_id):
    """Recognize only the closed native checker report, never a scripted result."""
    if type(value) is not dict:
        return False
    fixed = {
        "record_type": "required_gate_idempotence_loader_resolution_verification_v0",
        "profile": CAPTURE_PROFILE, "attempt_id": request_id,
        "evidence_origin": "native_original_loader_capture",
        "status": "accepted_native_loader_resolution_record",
        "record_binding_verified": True, "complete_mechanics_verified": True,
        "native_record_reconstructed": True, "scripted_record_reconstructed": False,
        "original_loader_capture_completed": True, "incomplete_record_preserved": False,
        "failure": None, "ptrace_cont_count": 11, "accepted_return_events": 9,
        "post_entry_resumes": 0, "source_build_policy_admitted_for_replay": True,
        "preserved_admission_summaries_consistent": True,
        "fresh_original_and_rebuild_inputs_reconstructed": True,
        "preserved_backend_execution_authenticated": False,
        "final_original_objects": 6, "final_pt_load_occurrences": 24,
        "original_rx_samples": 16, "return_rx_samples": 18,
        **BOUNDARY, "consumer_resolution_observed": True,
        "loader_resolution_verified": True, "current_backing_read_records_verified": True,
        "original_invocation_record_verified": True,
        "original_acquisition_ready": False, "future_host_admitted": False,
    }
    descriptors = ("request", "capture", "source_build_report", "original_admission",
                   "fresh_source_build_facts", "fresh_original_admission_facts", "task_guard_report")
    variable = (*descriptors, "raw_file_count", "raw_total_bytes", "occurrence_joins",
                "invocation", "qualification_reports")
    if set(value) != set(fixed) | set(variable):
        return False
    if not all(type(value[key]) is type(item) and value[key] == item for key, item in fixed.items()):
        return False
    try:
        for key in descriptors:
            _descriptor(value[key], CONTROL_LIMIT, 1)
        _keys(value["qualification_reports"], ("guard", "two_slot"),
              "loader_resolution_hosted_qualification_reports")
        for item in value["qualification_reports"].values():
            _descriptor(item, CONTROL_LIMIT, 1)
    except ValueError:
        return False
    return (type(value["raw_file_count"]) is int and 0 < value["raw_file_count"] < CAPTURE_FILE_COUNT_LIMIT
        and type(value["raw_total_bytes"]) is int and 0 < value["raw_total_bytes"] <= CAPTURE_LIMIT
        and type(value["occurrence_joins"]) is list and len(value["occurrence_joins"]) == 9
        and type(value["invocation"]) is dict)


def make_summary(phase, selection, *, request_bytes=None, capture_bytes=None,
                 report_bytes=(), error_code=None):
    validate_selection(selection, phase)
    _need(type(report_bytes) in (tuple, list) and len(report_bytes) <= 2,
          "loader_resolution_hosted_summary_reports")
    reports = [parse(raw) for raw in report_bytes]
    request_id = request_identity(selection["context"])
    descriptors = {"request": None if request_bytes is None else binding(request_bytes),
                   "capture": None if capture_bytes is None else binding(capture_bytes)}
    complete = (error_code is None and len(reports) == 2 and report_bytes[0] == report_bytes[1]
        and canonical(reports[0]) == report_bytes[0] and _native_report(reports[0], request_id)
        and all(value is not None for value in descriptors.values())
        and all(reports[0][key] == value for key, value in descriptors.items()))
    value = {"record_type": SUMMARY_TYPE, "profile": PROFILE, "phase": phase,
        "context": selection["context"], "image_id": selection["image_id"],
        "selection": binding(canonical(selection)), "request_id": request_id, **descriptors,
        "reports": [binding(raw) for raw in report_bytes],
        "status": "completed_native_reconstruction" if complete else "preserved_incomplete",
        "error_code": None if complete else (error_code or "loader_resolution_hosted_native_reconstruction_incomplete"),
        "boundary": dict(BOUNDARY)}
    return validate_summary(value, phase)


def validate_summary(value, phase):
    _keys(value, ("record_type", "profile", "phase", "context", "image_id", "selection",
        "request_id", "request", "capture", "reports", "status", "error_code", "boundary"),
        "loader_resolution_hosted_summary_fields")
    _need(value["record_type"] == SUMMARY_TYPE and value["profile"] == PROFILE and
          phase in ("acquire", "verify") and value["phase"] == phase,
          "loader_resolution_hosted_summary_profile")
    validate_context(value["context"])
    _need(type(value["image_id"]) is str and IMAGE_RE.fullmatch(value["image_id"]), "loader_resolution_hosted_image_id")
    _descriptor(value["selection"], CONTROL_LIMIT, 1)
    _need(value["request_id"] == request_identity(value["context"]), "loader_resolution_hosted_request_identity")
    for key in ("request", "capture"):
        if value[key] is not None:
            _descriptor(value[key], CONTROL_LIMIT, 1)
    _need(type(value["reports"]) is list and len(value["reports"]) <= 2, "loader_resolution_hosted_summary_reports")
    for item in value["reports"]:
        _descriptor(item, CONTROL_LIMIT, 1)
    _same(value["boundary"], BOUNDARY, "loader_resolution_hosted_boundary")
    _need(value["status"] in ("completed_native_reconstruction", "preserved_incomplete"),
          "loader_resolution_hosted_summary_status")
    if value["status"] == "completed_native_reconstruction":
        _need(value["error_code"] is None and len(value["reports"]) == 2 and
              all(value[key] is not None for key in ("request", "capture")),
              "loader_resolution_hosted_summary_complete")
    else:
        _need(type(value["error_code"]) is str and ERROR_RE.fullmatch(value["error_code"]),
              "loader_resolution_hosted_summary_error")
    return value


def validate_container_identity(info, cid, image, ctx, phase, plan, ownership_only=False):
    """Bind ownership first, then the actual Docker command, mounts and policy."""
    validate_context(ctx)
    _need(type(cid) is str and HEX64.fullmatch(cid) and type(image) is str and IMAGE_RE.fullmatch(image),
          "loader_resolution_hosted_container_identity")
    _need(type(info) is list and len(info) == 1 and type(info[0]) is dict,
          "loader_resolution_hosted_container_inspect")
    item = info[0]
    config, host = item.get("Config"), item.get("HostConfig")
    _need(type(config) is dict and type(host) is dict, "loader_resolution_hosted_container_inspect")
    _need(item.get("Id") == cid and item.get("Image") == image and
          item.get("Name") == "/" + container_name(ctx, phase), "loader_resolution_hosted_container_ownership")
    _same(config.get("Labels"), container_labels(ctx, phase), "loader_resolution_hosted_container_labels")
    if ownership_only:
        return item
    _need(type(plan) is dict, "loader_resolution_hosted_plan_fields")
    handoff_value = None
    if phase == "verify":
        env = plan.get("environment", {})
        _need(type(env) is dict, "loader_resolution_hosted_plan_environment")
        handoff_value = handoff(env)
    validate_container_plan(plan, phase, handoff=handoff_value)
    _same(plan["context"], ctx, "loader_resolution_hosted_plan_context")
    _need(plan["image_id"] == image, "loader_resolution_hosted_plan_image")
    _same(config.get("Entrypoint"), plan["entrypoint"], "loader_resolution_hosted_container_entrypoint")
    _same(config.get("Cmd"), plan["command"], "loader_resolution_hosted_container_command")
    _need(config.get("User") == str(plan["uid"]) + ":" + str(plan["gid"])
          and config.get("WorkingDir") == "/repo" and config.get("Image") == image,
          "loader_resolution_hosted_container_user")
    expected_environment = {**_environment_map(plan["image_environment"]), **plan["environment"]}
    _same(_environment_map(config.get("Env")), expected_environment, "loader_resolution_hosted_container_environment")
    _need(host.get("Privileged") is False and host.get("ReadonlyRootfs") is True
          and host.get("NetworkMode") == "none" and host.get("CapDrop") == ["ALL"]
          and host.get("CapAdd") in (None, [])
          and host.get("SecurityOpt") in (
              ["no-new-privileges", "apparmor=docker-default"],
              ["no-new-privileges=true", "apparmor=docker-default"])
          and type(host.get("PidsLimit")) is int and host["PidsLimit"] == 64
          and type(host.get("Memory")) is int and host["Memory"] == 1024 ** 3
          and type(host.get("NanoCpus")) is int and host["NanoCpus"] == 10 ** 9
          and host.get("Tmpfs") == {"/tmp": "rw,nosuid,nodev,size=64m"},
          "loader_resolution_hosted_container_policy")
    # No other path may regain a host namespace, device or writable mount.
    for key in ("CapAdd", "Devices", "DeviceRequests", "DeviceCgroupRules", "VolumesFrom", "Binds",
                "GroupAdd", "Links", "Ulimits", "ExtraHosts", "Dns", "DnsOptions", "DnsSearch"):
        _need(host.get(key) in (None, []), "loader_resolution_hosted_container_extra_access")
    _need(host.get("Sysctls") in (None, {}) and host.get("PortBindings") in (None, {})
          and host.get("PublishAllPorts", False) is False, "loader_resolution_hosted_container_extra_access")
    restart = host.get("RestartPolicy", {"Name": "no", "MaximumRetryCount": 0})
    _need(type(restart) is dict and restart.get("Name") in ("", "no") and
          type(restart.get("MaximumRetryCount", 0)) is int and restart.get("MaximumRetryCount", 0) == 0,
          "loader_resolution_hosted_container_restart")
    for key in ("CpuPeriod", "CpuQuota", "CpuRealtimePeriod", "CpuRealtimeRuntime", "CpuShares"):
        _need(type(host.get(key, 0)) is int and host.get(key, 0) == 0, "loader_resolution_hosted_container_cpu_override")
    for key in ("CpusetCpus", "CpusetMems"):
        _need(host.get(key, "") == "", "loader_resolution_hosted_container_cpu_override")
    for key in ("PidMode", "UTSMode", "UsernsMode"):
        _need(host.get(key, "") == "", "loader_resolution_hosted_container_namespace")
    _need(host.get("IpcMode", "private") == "private" and host.get("CgroupnsMode", "private") in ("", "private")
          and host.get("Init") in (None, False) and host.get("AutoRemove", False) is False
          and item.get("AppArmorProfile") == "docker-default",
          "loader_resolution_hosted_container_defaults")
    _need(config.get("Volumes") in (None, {}) and config.get("Healthcheck") in (None, {})
          and config.get("Tty", False) is False and config.get("OpenStdin", False) is False,
          "loader_resolution_hosted_container_config")
    actual_mounts = item.get("Mounts")
    _need(type(actual_mounts) is list and len(actual_mounts) == len(plan["mounts"]),
          "loader_resolution_hosted_container_mounts")
    actual = {}
    for mount in actual_mounts:
        _need(type(mount) is dict and type(mount.get("Destination")) is str and
              mount["Destination"] not in actual and mount.get("Type") == "bind" and
              type(mount.get("RW")) is bool and mount.get("Propagation", "rprivate") == "rprivate",
              "loader_resolution_hosted_container_mounts")
        actual[mount["Destination"]] = {"source": mount.get("Source"),
            "target": mount["Destination"], "readonly": not mount["RW"]}
    _same([actual[key] for key in sorted(actual)], plan["mounts"], "loader_resolution_hosted_container_mounts")
    if "Mounts" in host:
        mounts = host["Mounts"]
        _need(type(mounts) is list and len(mounts) == len(plan["mounts"]), "loader_resolution_hosted_container_mounts")
        normalized = []
        for mount in mounts:
            _need(type(mount) is dict and mount.get("Type") == "bind" and
                  set(mount) <= {"Type", "Source", "Target", "ReadOnly", "Consistency", "BindOptions"} and
                  mount.get("BindOptions") in (None, {}, {"Propagation": "rprivate"}),
                  "loader_resolution_hosted_container_mount_options")
            normalized.append({"source": mount.get("Source"), "target": mount.get("Target"),
                "readonly": mount.get("ReadOnly", False)})
        _same(sorted(normalized, key=lambda entry: entry["target"]), plan["mounts"],
              "loader_resolution_hosted_container_mounts")
    return item


def command_record(root, label, expected_argv=None, *, directory="host-commands", success=True):
    """Check all four fixed command records and byte bindings, including reaping."""
    allowed = HOST_COMMANDS if directory == "host-commands" else INNER_COMMANDS
    _need(label in allowed and directory in ("host-commands", "observation/commands", "verification/commands"),
          "loader_resolution_hosted_command_label")
    base = Path(root) / directory
    argv_record = _json(base / (label + ".argv.json"))
    _keys(argv_record, ("argv",), "loader_resolution_hosted_command_argv_fields")
    argv = argv_record["argv"]
    _need(type(argv) is list and 1 <= len(argv) <= 256 and
          all(type(item) is str and 0 < len(item) <= 4096 and "\x00" not in item for item in argv),
          "loader_resolution_hosted_command_argv")
    if expected_argv is not None:
        _same(argv, expected_argv, "loader_resolution_hosted_command_selection")
    result = _json(base / (label + ".result.json"), external=True)
    _keys(result, ("argv", "returncode", "failure", "stdout", "stderr", "timeout_seconds",
        "stream_cap", "stdout_cap", "overflowed_streams", "elapsed_seconds", "cleanup"),
        "loader_resolution_hosted_command_result_fields")
    _same(result["argv"], argv, "loader_resolution_hosted_command_argv_join")
    _need(result["returncode"] is None or type(result["returncode"]) is int,
          "loader_resolution_hosted_command_returncode")
    _need(result["failure"] is None or (type(result["failure"]) is str and ERROR_RE.fullmatch(result["failure"])),
          "loader_resolution_hosted_command_failure")
    _need(type(result["timeout_seconds"]) in (int, float) and math.isfinite(result["timeout_seconds"])
          and 0 < result["timeout_seconds"] <= 1200 and
          type(result["elapsed_seconds"]) in (int, float) and math.isfinite(result["elapsed_seconds"])
          and result["elapsed_seconds"] >= 0, "loader_resolution_hosted_command_time")
    _need(type(result["stream_cap"]) is int and 0 < result["stream_cap"] <= COMMAND_LIMIT and
          type(result["stdout_cap"]) is int and 0 < result["stdout_cap"] <= FILE_LIMIT and
          (label == "base-save" or result["stdout_cap"] <= COMMAND_LIMIT), "loader_resolution_hosted_command_cap")
    _need(type(result["overflowed_streams"]) is list and
          result["overflowed_streams"] in ([], ["stderr"], ["stdout"], ["stderr", "stdout"]),
          "loader_resolution_hosted_command_overflow")
    cleanup = result["cleanup"]
    _keys(cleanup, ("child_started", "child_reaped", "kill_group_sent", "kill_error_errno",
        "pending_output_drain_attempted"), "loader_resolution_hosted_command_cleanup_fields")
    _need(all(type(cleanup[key]) is bool for key in ("child_started", "child_reaped", "kill_group_sent",
          "pending_output_drain_attempted")) and (cleanup["kill_error_errno"] is None or
          (type(cleanup["kill_error_errno"]) is int and 0 < cleanup["kill_error_errno"] < 65536)),
          "loader_resolution_hosted_command_cleanup")
    streams = {}
    for key in ("stdout", "stderr"):
        cap = result["stdout_cap"] if key == "stdout" else result["stream_cap"]
        _descriptor(result[key], cap)
        streams[key] = read_regular(base / (label + "." + key + ".bin"), cap, empty=True)
        _same(binding(streams[key]), result[key], "loader_resolution_hosted_command_stream_binding")
    if success:
        _need(type(result["returncode"]) is int and result["returncode"] == 0 and result["failure"] is None
              and result["overflowed_streams"] == [] and cleanup["child_started"] is True
              and cleanup["child_reaped"] is True and cleanup["kill_group_sent"] is False
              and cleanup["kill_error_errno"] is None and cleanup["pending_output_drain_attempted"] is True,
              "loader_resolution_hosted_command_incomplete")
    return {"result": result, **streams}


def _plan_root(plan):
    mounts = {entry["target"]: entry for entry in plan["mounts"]}
    root = Path(mounts["/control"]["source"]).parent
    _need(mounts["/control"]["source"] == str(root / "control") and
          mounts["/repo"]["source"] == str(root / "source") and
          mounts["/output"]["source"] == str(root / ("observation" if plan["phase"] == "acquire" else "verification")),
          "loader_resolution_hosted_mount_source_join")
    return root


def docker_create_argv(plan):
    """The retained command must have exactly this argument vector."""
    root = _plan_root(plan)
    argv = ["docker", "create", "--name", plan["name"], "--cidfile", str(root / "environment/container-id.txt"),
        "--platform", "linux/amd64", "--user", str(plan["uid"]) + ":" + str(plan["gid"]),
        "--read-only", "--network", "none", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--security-opt", "apparmor=docker-default",
        "--pids-limit", "64", "--memory", "1g", "--cpus", "1", "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m",
        "--workdir", "/repo"]
    for key, value in sorted(plan["labels"].items()):
        argv += ["--label", key + "=" + value]
    for mount in plan["mounts"]:
        argv += ["--mount", "type=bind,source=" + mount["source"] + ",target=" + mount["target"] +
            (",readonly" if mount["readonly"] else "")]
    for key, value in sorted(plan["environment"].items()):
        argv += ["--env", key + "=" + value]
    return argv + ["--entrypoint", PYTHON, plan["image_id"], *plan["command"]]


def validate_cleanup(root, ctx, phase):
    root = Path(root)
    record = _json(root / "environment/container-cleanup.json")
    _keys(record, ("container_id", "image_id", "phase", "name", "owned_container_verified",
        "inspect_exit_code", "remove_succeeded", "absence_verified", "cleanup_errors"),
        "loader_resolution_hosted_cleanup_fields")
    cid, image = record["container_id"], record["image_id"]
    _need(type(cid) is str and HEX64.fullmatch(cid) and type(image) is str and IMAGE_RE.fullmatch(image)
          and record["phase"] == phase and record["name"] == container_name(ctx, phase)
          and record["owned_container_verified"] is True and record["remove_succeeded"] is True
          and record["absence_verified"] is True and type(record["inspect_exit_code"]) is int
          and record["inspect_exit_code"] == 0 and record["cleanup_errors"] == [],
          "loader_resolution_hosted_cleanup_incomplete")
    _need(read_regular(root / "environment/container-id.txt", 128).decode("ascii").strip() == cid,
          "loader_resolution_hosted_cleanup_cid")
    plan = _json(root / "environment/container-plan.json")
    _need(plan["image_id"] == image, "loader_resolution_hosted_cleanup_image")
    owned = command_record(root, "container-ownership-inspect",
        ["docker", "container", "inspect", record["name"]])
    validate_container_identity(parse_external(owned["stdout"]), cid, image, ctx, phase, plan, True)
    removed = command_record(root, "container-remove", ["docker", "rm", "--force", cid])
    _need(removed["stdout"].decode("ascii").strip() == cid, "loader_resolution_hosted_cleanup_removed_id")
    absent = command_record(root, "container-absence",
        ["docker", "container", "ls", "--all", "--quiet", "--no-trunc", "--filter", "id=" + cid])
    _need(absent["stdout"] == b"", "loader_resolution_hosted_cleanup_absence")
    return binding(read_regular(root / "environment/container-cleanup.json"))


def allowed_files():
    names = {"workflow-start.json", "source-bindings.json", "failure.json", "attestation-identity.json",
        "prefix-verification.json", "verified-binding.json", "attestation.json", "attestation-bundle.json",
        "environment/selection.json", "environment/image-id.txt", "environment/container-id.txt",
        "environment/container-plan.json", "environment/container-cleanup.json", "control/hosted-selection.json"}
    names.update("source/" + path for path in SOURCE_PATHS)
    names.update("materials/" + path for path in CONFIG_FILES)
    names.update("materials/" + path for path in MATERIAL_BINDINGS)
    for label in HOST_COMMANDS:
        names.update("host-commands/" + label + "." + suffix
            for suffix in ("argv.json", "result.json", "stdout.bin", "stderr.bin"))
    for prefix in ("observation", "verification"):
        names.update(prefix + "/" + leaf for leaf in ("request.json", "capture-check-1.json", "capture-check-2.json",
            "build-environment-record.json",
            "acquisition-summary.json" if prefix == "observation" else "verification-summary.json"))
        # Failure publication has a fixed finite vocabulary and does not trust
        # a possibly incomplete capture manifest to authorize additional paths.
        names.update(prefix + "/capture/" + path for path in
            (*CAPTURE_RAW_LIMITS, "capture.json", "verification.json", "attempt.incomplete.json"))
        for label in INNER_COMMANDS:
            names.update(prefix + "/commands/" + label + "." + suffix
                for suffix in ("argv.json", "result.json", "stdout.bin", "stderr.bin"))
    return frozenset(names)


def _file_limit(name):
    if name == "host-commands/base-save.stdout.bin":
        return FILE_LIMIT
    if name.startswith("source/"):
        return source_limit(name[7:])
    if name.startswith("materials/"):
        relative = name[len("materials/"):]
        return MATERIAL_BINDINGS[relative]["size_bytes"] if relative in MATERIAL_BINDINGS else CONTROL_LIMIT
    if "/capture/" in name:
        relative = name.split("/capture/", 1)[1]
        return CAPTURE_RAW_LIMITS.get(relative, CONTROL_LIMIT)
    if name.endswith((".stdout.bin", ".stderr.bin")) or name == "attestation-bundle.json":
        return COMMAND_LIMIT
    return CONTROL_LIMIT


def inventory(root):
    """Read only the predetermined finite roster through pinned directory FDs."""
    permitted = allowed_files()
    directories = {str(Path(name).parent) for name in permitted}
    directories.update(str(parent) for name in permitted for parent in Path(name).parents if str(parent) != ".")
    parent, name = core._open_parent(root)
    descriptor = None
    files, total, nodes = {}, 0, 0
    def visit(fd, prefix):
        nonlocal total, nodes
        before = os.fstat(fd)
        names = sorted(os.listdir(fd))
        for leaf in names:
            nodes += 1
            _need(nodes <= FILE_COUNT_LIMIT + len(directories) + 1, "loader_resolution_hosted_inventory_count")
            child = prefix + leaf
            info = os.stat(leaf, dir_fd=fd, follow_symlinks=False)
            if child == "receipt.json":
                _need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 < info.st_size <= CONTROL_LIMIT,
                      "loader_resolution_hosted_receipt_extent")
                continue
            if stat.S_ISDIR(info.st_mode):
                _need(child in directories, "loader_resolution_hosted_directory_roster")
                nxt = os.open(leaf, core._DIRECTORY_FLAGS, dir_fd=fd)
                try:
                    _need(core._identity(info) == core._identity(os.fstat(nxt)), "loader_resolution_hosted_directory_changed")
                    visit(nxt, child + "/")
                    _need(core._identity(os.fstat(nxt)) == core._identity(os.stat(leaf, dir_fd=fd, follow_symlinks=False)),
                          "loader_resolution_hosted_directory_changed")
                finally:
                    os.close(nxt)
            else:
                _need(child in permitted and stat.S_ISREG(info.st_mode), "loader_resolution_hosted_file_roster")
                raw = core._read_at(fd, leaf, _file_limit(child), empty=True)
                files[child] = binding(raw)
                total += len(raw)
                _need(total <= TOTAL_LIMIT and len(files) <= FILE_COUNT_LIMIT, "loader_resolution_hosted_inventory_limit")
        _need(core._identity(before) == core._identity(os.fstat(fd)) and names == sorted(os.listdir(fd)),
              "loader_resolution_hosted_directory_changed")
    try:
        descriptor = os.open(name, core._DIRECTORY_FLAGS, dir_fd=parent)
        before = os.fstat(descriptor)
        visit(descriptor, "")
        _need(core._identity(before) == core._identity(os.fstat(descriptor)) ==
              core._identity(os.stat(name, dir_fd=parent, follow_symlinks=False)), "loader_resolution_hosted_directory_changed")
        return dict(sorted(files.items())), total
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent)


def _optional_json(root, name):
    try:
        return _json(Path(root) / name)
    except FileNotFoundError:
        return None


def make_receipt(root, ctx, phase="acquire"):
    """Seal the available prefix; never replace the original source selection."""
    validate_context(ctx)
    _need(phase in ("acquire", "verify"), "loader_resolution_hosted_phase")
    files, total = inventory(root)
    sources, error = None, None
    if "source-bindings.json" in files:
        try:
            sources = _json(Path(root) / "source-bindings.json")
            _sources(sources)
        except (OSError, ValueError):
            sources, error = None, "loader_resolution_hosted_source_selection_invalid"
    status = "preserved_incomplete"
    if phase == "acquire":
        try:
            verify_completed_acquisition(root, ctx)
            status = "completed_native_reconstruction"
        except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
            error = getattr(exc, "code", "loader_resolution_hosted_acquisition_incomplete")
    else:
        error = error or "loader_resolution_hosted_verification_prefix"
    location = "observation" if phase == "acquire" else "verification"
    result = {"record_type": RECEIPT_TYPE, "profile": PROFILE, "phase": phase, "context": ctx,
        "sources": sources, "environment": None if sources is None else sources[CONFIG + "/environment.json"],
        "selection": files.get("control/hosted-selection.json"),
        "summary": files.get(location + ("/acquisition-summary.json" if phase == "acquire" else "/verification-summary.json")),
        "request": files.get(location + "/request.json"), "capture": files.get(location + "/capture/capture.json"),
        "files": files, "file_count": len(files), "total_size_bytes": total, "status": status,
        "error_code": None if status == "completed_native_reconstruction" else (error or "loader_resolution_hosted_prefix_incomplete"),
        "boundary": dict(BOUNDARY)}
    return validate_receipt(canonical(result), binding(canonical(result))["sha256"], ctx)


def validate_receipt(raw, expected_sha256, ctx):
    validate_context(ctx)
    _need(type(expected_sha256) is str and HEX64.fullmatch(expected_sha256) and
          binding(raw)["sha256"] == expected_sha256, "loader_resolution_hosted_receipt_digest")
    value = parse(raw)
    _keys(value, ("record_type", "profile", "phase", "context", "sources", "environment", "selection",
        "summary", "request", "capture", "files", "file_count", "total_size_bytes",
        "status", "error_code", "boundary"), "loader_resolution_hosted_receipt_fields")
    _need(value["record_type"] == RECEIPT_TYPE and value["profile"] == PROFILE and
          value["phase"] in ("acquire", "verify"), "loader_resolution_hosted_receipt_profile")
    _same(value["context"], ctx, "loader_resolution_hosted_receipt_context")
    _same(value["boundary"], BOUNDARY, "loader_resolution_hosted_boundary")
    if value["sources"] is not None:
        _sources(value["sources"])
        _same(value["environment"], value["sources"][CONFIG + "/environment.json"], "loader_resolution_hosted_environment_source")
    else:
        _need(value["environment"] is None, "loader_resolution_hosted_receipt_environment")
    permitted = allowed_files()
    _need(type(value["files"]) is dict and set(value["files"]) <= permitted and
          len(value["files"]) <= FILE_COUNT_LIMIT, "loader_resolution_hosted_receipt_roster")
    total = 0
    for name, selected in value["files"].items():
        _descriptor(selected, _file_limit(name))
        total += selected["size_bytes"]
    _need(type(value["file_count"]) is int and value["file_count"] == len(value["files"]) and
          type(value["total_size_bytes"]) is int and value["total_size_bytes"] == total <= TOTAL_LIMIT,
          "loader_resolution_hosted_receipt_totals")
    location = "observation" if value["phase"] == "acquire" else "verification"
    joined = {"selection": "control/hosted-selection.json",
        "summary": location + ("/acquisition-summary.json" if value["phase"] == "acquire" else "/verification-summary.json"),
        "request": location + "/request.json", "capture": location + "/capture/capture.json"}
    for key, name in joined.items():
        _same(value[key], value["files"].get(name), "loader_resolution_hosted_receipt_descriptor_join")
    _need(value["status"] in ("completed_native_reconstruction", "preserved_incomplete"),
          "loader_resolution_hosted_receipt_status")
    if value["status"] == "completed_native_reconstruction":
        _need(value["phase"] == "acquire" and value["sources"] is not None and value["error_code"] is None
              and all(value[key] is not None for key in joined), "loader_resolution_hosted_receipt_complete")
        _same(value["environment"], ENVIRONMENT_BINDING, "loader_resolution_hosted_environment_selection")
        for key in joined:
            _descriptor(value[key], CONTROL_LIMIT, 1)
    else:
        _need(type(value["error_code"]) is str and ERROR_RE.fullmatch(value["error_code"]),
              "loader_resolution_hosted_receipt_error")
    _need(raw == canonical(value), "loader_resolution_hosted_receipt_canonical")
    return value


def verify_preservation(root, raw_or_receipt, sha=None, ctx=None):
    raw = raw_or_receipt if type(raw_or_receipt) is bytes else canonical(raw_or_receipt)
    if ctx is None:
        ctx = parse(raw)["context"]
    selected = validate_receipt(raw, binding(raw)["sha256"] if sha is None else sha, ctx)
    actual_receipt = read_regular(Path(root) / "receipt.json")
    _need(actual_receipt == raw, "loader_resolution_hosted_receipt_preserved_bytes")
    files, total = inventory(root)
    _same(files, selected["files"], "loader_resolution_hosted_preserved_inventory")
    _need(total == selected["total_size_bytes"], "loader_resolution_hosted_preserved_size")
    if selected["sources"] is not None:
        _same(_json(Path(root) / "source-bindings.json"), selected["sources"], "loader_resolution_hosted_preserved_sources")
        for name, descriptor in selected["sources"].items():
            # A failed copy or subsequent drift is itself a useful prefix.
            # Preserve both the original selection and the actual retained
            # bytes; only completion may assert that those are identical.
            if selected["status"] == "completed_native_reconstruction" and "source/" + name in files:
                _same(files["source/" + name], descriptor, "loader_resolution_hosted_preserved_source_bytes")
    return selected


def validate_artifact_metadata(value, ctx, selected_handoff):
    validate_context(ctx)
    validate_handoff(selected_handoff)
    _need(type(value) is dict and type(value.get("id")) is int and
          value["id"] == selected_handoff["artifact_id"] and
          value.get("name") == "required-gate-idempotence-loader-resolution-" + str(ctx["run_id"]) + "-1" and
          value.get("digest") == selected_handoff["artifact_digest"] and value.get("expired") is False,
          "loader_resolution_hosted_artifact_metadata")
    run = value.get("workflow_run")
    _need(type(run) is dict and type(run.get("id")) is int and run["id"] == ctx["run_id"] and
          run.get("head_sha") == ctx["source_commit"] and run.get("head_branch") == "main" and
          type(run.get("repository_id")) is int and run["repository_id"] == int(REPOSITORY_ID) and
          type(run.get("head_repository_id")) is int and run["head_repository_id"] == int(REPOSITORY_ID),
          "loader_resolution_hosted_artifact_run")
    return value


def _verify_sources(root, ctx, phase):
    prefix = _json(root / "workflow-start.json")
    _same(prefix, {"record_type": "required_gate_idempotence_loader_resolution_workflow_start_v0",
        "phase": phase, "context": ctx, "boundary": BOUNDARY}, "loader_resolution_hosted_workflow_start")
    selected = _json(root / "source-bindings.json")
    _sources(selected)
    _same(selected, source_bindings(), "loader_resolution_hosted_current_source_selection")
    raw_sources = {}
    for name, descriptor in selected.items():
        raw_sources[name] = read_regular(root / "source" / name, source_limit(name))
        _same(binding(raw_sources[name]), descriptor, "loader_resolution_hosted_source_snapshot")
    # The original absolute checkout path is evidence, not the verifier's cwd.
    first = command_record(root, "git-head-before")
    argv = first["result"]["argv"]
    fixed = ["git", "--no-pager", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-C"]
    _need(len(argv) == len(fixed) + 4 and argv[:len(fixed)] == fixed and
          argv[-3:] == ["rev-parse", "--verify", "HEAD"], "loader_resolution_hosted_git_command")
    _mount_source(argv[len(fixed)])
    base = argv[:-3]
    _need(first["stdout"] == (ctx["source_commit"] + "\n").encode("ascii"), "loader_resolution_hosted_git_head")
    tree = command_record(root, "git-source-tree", [*base, "ls-tree", "-r", "-z", "--full-tree",
        ctx["source_commit"]])["stdout"]
    _need(tree.endswith(b"\0"), "loader_resolution_hosted_git_tree")
    blobs = {}
    selected_names = {name.encode("ascii"): name for name in selected}
    for row in tree[:-1].split(b"\0"):
        metadata, separator, name = row.partition(b"\t")
        _need(separator and name, "loader_resolution_hosted_git_tree")
        # The fixed full-tree command keeps the argv below the transport limit.
        # Only explicitly selected paths are sources; unrelated tree metadata
        # cannot enlarge the mounted, hashed or executed source closure.
        if name not in selected_names:
            continue
        fields = metadata.split(b" ")
        _need(len(fields) == 3 and fields[0] in (b"100644", b"100755") and fields[1] == b"blob"
              and re.fullmatch(b"[0-9a-f]{40}", fields[2]), "loader_resolution_hosted_git_blob")
        path = selected_names[name]
        _need(path not in blobs, "loader_resolution_hosted_git_roster")
        blobs[path] = fields[2].decode("ascii")
    _need(set(blobs) == set(selected), "loader_resolution_hosted_git_roster")
    for name, raw in raw_sources.items():
        _need(hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest() == blobs[name],
              "loader_resolution_hosted_git_source_bytes")
    last = command_record(root, "git-head-after", [*base, "rev-parse", "--verify", "HEAD"])
    _need(last["stdout"] == first["stdout"], "loader_resolution_hosted_git_head_changed")
    return selected


def _image_info(raw, image):
    value = parse_external(raw)
    _need(type(value) is list and len(value) == 1 and type(value[0]) is dict and
          value[0].get("Id") == image and value[0].get("Architecture") == "amd64" and
          value[0].get("Os") == "linux" and type(value[0].get("Config")) is dict,
          "loader_resolution_hosted_image_inspect")
    _environment_map(value[0]["Config"].get("Env"))
    return value[0]


def _verify_environment(root, selection, plan, previous=None):
    selected = environment()
    phase = selection["phase"]
    original_root = _plan_root(plan)
    base = selected["base_image"]
    base_id = "sha256:" + base["config_sha256"]
    local_tag = "localhost/pulse-loader-resolution-base:" + base["config_sha256"]
    image = selection["image_id"]
    record = _json(root / "environment/selection.json")
    _keys(record, ("record_type", "profile", "base_image", "constructed_image_id", "base_archive",
        "base_loaded_from_preserved_bytes", "base_local_build_tag", "environment_selection",
        "build_inputs_fixed", "image_reproducibility_claimed", "boundary"), "loader_resolution_hosted_image_fields")
    _same(record["base_image"], base, "loader_resolution_hosted_base_selection")
    _same(record["environment_selection"], ENVIRONMENT_BINDING, "loader_resolution_hosted_environment_selection")
    _same(record["boundary"], BOUNDARY, "loader_resolution_hosted_boundary")
    _need(record["record_type"] == "required_gate_idempotence_loader_resolution_hosted_image_v0"
          and record["profile"] == PROFILE and record["constructed_image_id"] == image
          and record["base_local_build_tag"] == local_tag and record["build_inputs_fixed"] is True
          and record["image_reproducibility_claimed"] is False
          and type(record["base_loaded_from_preserved_bytes"]) is bool
          and record["base_loaded_from_preserved_bytes"] == (phase == "verify"), "loader_resolution_hosted_image_selection")
    _need(read_regular(root / "environment/image-id.txt", 128).decode("ascii").strip() == image,
          "loader_resolution_hosted_image_id_binding")
    for name in CONFIG_FILES:
        raw = read_regular(root / "materials" / name, SOURCE_LIMIT)
        _same(binding(raw), selection["sources"][CONFIG + "/" + name], "loader_resolution_hosted_build_source")
    _same(binding(read_regular(root / "materials/requirements.lock", CONTROL_LIMIT)), selected["requirements"],
          "loader_resolution_hosted_requirements_lock")
    selected_materials = {
        **{"wheels/" + item["filename"]: {key: item[key] for key in ("size_bytes", "sha256")}
           for item in selected["python"]["packages"]},
        **{"debs/" + item["filename"]: {key: item[key] for key in ("size_bytes", "sha256")}
           for item in selected["debian"]["packages"]},
        **{item["input"]: {key: item[key] for key in ("size_bytes", "sha256")}
           for item in selected["original_native_objects"]},
    }
    _same(selected_materials, MATERIAL_BINDINGS, "loader_resolution_hosted_material_selection")
    for name, item in selected_materials.items():
        _same(binding(read_regular(root / "materials" / name, item["size_bytes"])), item,
              "loader_resolution_hosted_material_binding")
    build_record = _json(root / ("observation" if phase == "acquire" else "verification") / "build-environment-record.json")
    validate_build_record(build_record, selected)
    if phase == "acquire":
        command_record(root, "base-pull", ["docker", "pull", "--platform", "linux/amd64", base["reference"]])
        inspect_name = base["reference"]
        command_record(root, "base-tag", ["docker", "image", "tag", base_id, local_tag])
        archived = command_record(root, "base-save", ["docker", "image", "save", local_tag])
        _need(len(archived["stdout"]) > 0, "loader_resolution_hosted_base_archive_empty")
        archive_binding = binding(archived["stdout"])
    else:
        _need(previous is not None, "loader_resolution_hosted_verification_input")
        mounts = {item["target"]: item["source"] for item in plan["mounts"]}
        _need(mounts["/input"] == str(Path(previous)), "loader_resolution_hosted_private_input_mount")
        command_record(root, "base-load", ["docker", "image", "load", "--input",
            str(Path(previous) / "host-commands/base-save.stdout.bin")])
        archived = command_record(previous, "base-save", ["docker", "image", "save", local_tag])
        archive_binding = binding(archived["stdout"])
        inspect_name = local_tag
    _same(record["base_archive"], archive_binding, "loader_resolution_hosted_base_archive_binding")
    inspected = command_record(root, "base-inspect", ["docker", "image", "inspect", inspect_name])
    base_info = _image_info(inspected["stdout"], base_id)
    tagged = command_record(root, "base-tag-inspect", ["docker", "image", "inspect", local_tag])
    tagged_info = _image_info(tagged["stdout"], base_id)
    _same(_environment_map(base_info["Config"]["Env"]), _environment_map(tagged_info["Config"]["Env"]),
          "loader_resolution_hosted_base_environment")
    command_record(root, "image-build", ["docker", "build", "--platform", "linux/amd64", "--network", "none",
        "--pull=false", "--no-cache", "--build-arg", "PULSE_LOADER_RESOLUTION_BASE=" + local_tag,
        "--iidfile", str(original_root / "environment/image-id.txt"), str(original_root / "materials")])
    built = command_record(root, "image-inspect", ["docker", "image", "inspect", image])
    built_info = _image_info(built["stdout"], image)
    expected = {**_environment_map(base_info["Config"]["Env"]), **_environment_map(selected["runtime_environment"])}
    _same(_environment_map(built_info["Config"]["Env"]), expected, "loader_resolution_hosted_image_environment")
    _same(plan["image_environment"], built_info["Config"]["Env"], "loader_resolution_hosted_plan_image_environment")
    after = command_record(root, "base-inspect-after", ["docker", "image", "inspect", local_tag])
    after_info = _image_info(after["stdout"], base_id)
    _same(_environment_map(after_info["Config"]["Env"]), _environment_map(base_info["Config"]["Env"]),
          "loader_resolution_hosted_base_changed")
    return record


def _verify_container(root, ctx, phase, selection, previous=None):
    plan = _json(root / "environment/container-plan.json")
    validate_container_plan(plan, phase, handoff=selection["handoff"])
    _same(plan["selection"], binding(canonical(selection)), "loader_resolution_hosted_plan_selection")
    _same(plan["context"], ctx, "loader_resolution_hosted_plan_context")
    _need(plan["image_id"] == selection["image_id"], "loader_resolution_hosted_plan_image")
    image_record = _verify_environment(root, selection, plan, previous)
    cid = read_regular(root / "environment/container-id.txt", 128).decode("ascii").strip()
    _need(HEX64.fullmatch(cid), "loader_resolution_hosted_container_id")
    created = command_record(root, "container-create", docker_create_argv(plan))
    _need(created["stdout"].decode("ascii").strip() == cid, "loader_resolution_hosted_created_id")
    before = command_record(root, "container-inspect", ["docker", "container", "inspect", cid])
    before_info = parse_external(before["stdout"])
    validate_container_identity(before_info, cid, selection["image_id"], ctx, phase, plan)
    before_state = before_info[0].get("State")
    _need(type(before_state) is dict and before_state.get("Status") == "created" and
          before_state.get("Running") is False, "loader_resolution_hosted_container_prestart")
    command_record(root, "container-start", ["docker", "start", "--attach", cid])
    after = command_record(root, "container-state", ["docker", "container", "inspect", cid])
    after_info = parse_external(after["stdout"])
    item = validate_container_identity(after_info, cid, selection["image_id"], ctx, phase, plan)
    state = item.get("State")
    _need(type(state) is dict and type(state.get("ExitCode")) is int and state["ExitCode"] == 0
          and state.get("Running") is False and state.get("Status") == "exited"
          and state.get("OOMKilled") is False and not state.get("Error")
          and state.get("Restarting", False) is False and state.get("Dead", False) is False,
          "loader_resolution_hosted_container_exit")
    cleanup = validate_cleanup(root, ctx, phase)
    return {"container_id": cid, "image": image_record, "cleanup": cleanup}


def _capture_materials(evidence, selection):
    """Bind the entire flat capture before inspecting the selected reports.

    The selected raw checker performs ELF/procfs/signature semantics inside the
    offline image. Here we independently join the exact source, policy, attempt,
    manifest and raw-byte inputs passed to each recorded checker command.
    """
    request_bytes = read_regular(evidence / "request.json")
    request = parse(request_bytes)
    _need(type(request) is dict and canonical(request) == request_bytes,
          "loader_resolution_hosted_request_canonical")
    request_id = request_identity(selection["context"])
    _need(request.get("record_type") == "required_gate_idempotence_loader_resolution_request_v0"
          and request.get("profile") == CAPTURE_PROFILE and request.get("attempt_id") == request_id,
          "loader_resolution_hosted_request_identity")
    _same(request.get("boundary"), BOUNDARY, "loader_resolution_hosted_request_boundary")
    observer = request.get("observer")
    _need(type(observer) is dict and observer.get("path") == PYTHON,
          "loader_resolution_hosted_observer_path")
    _same({key: observer.get(key) for key in ("size_bytes", "sha256")}, OBSERVER_BINDING,
          "loader_resolution_hosted_observer_binding")
    _same(request.get("sources"), {name: selection["sources"][name] for name in REQUEST_SOURCE_PATHS},
          "loader_resolution_hosted_request_sources")
    source_build = request.get("source_build")
    _need(type(source_build) is dict and source_build.get("external_selection_required") is True
          and source_build.get("policy", {}).get("sha256") == selection["context"]["accepted_policy_sha256"],
          "loader_resolution_hosted_request_policy")
    capture_bytes = read_regular(evidence / "capture/capture.json")
    capture = parse(capture_bytes)
    _need(type(capture) is dict and canonical(capture) == capture_bytes
          and capture.get("record_type") == "required_gate_idempotence_loader_resolution_capture_v0"
          and capture.get("profile") == CAPTURE_PROFILE and capture.get("status") == "completed"
          and capture.get("evidence_origin") == "native_original_loader_capture"
          and capture.get("failure") is None and capture.get("attempt_id") == request_id
          and capture.get("request_sha256") == binding(request_bytes)["sha256"],
          "loader_resolution_hosted_native_capture")
    _same(capture.get("boundary"), BOUNDARY, "loader_resolution_hosted_capture_boundary")
    manifest = capture.get("files")
    _need(type(manifest) is dict and set(manifest) <= set(CAPTURE_RAW_LIMITS)
          and len(manifest) + 1 <= CAPTURE_FILE_COUNT_LIMIT, "loader_resolution_hosted_capture_roster")
    total = len(capture_bytes)
    for name, item in manifest.items():
        _descriptor(item, CAPTURE_RAW_LIMITS[name])
        total += item["size_bytes"]
        _need(total <= CAPTURE_LIMIT, "loader_resolution_hosted_capture_total")
    directory = evidence / "capture"
    parent, leaf = core._open_parent(directory)
    descriptor = None
    files = {}
    try:
        descriptor = os.open(leaf, core._DIRECTORY_FLAGS, dir_fd=parent)
        before = os.fstat(descriptor)
        names = set(os.listdir(descriptor))
        _need(names in (set(manifest) | {"capture.json"},
                       set(manifest) | {"capture.json", "verification.json"}),
              "loader_resolution_hosted_capture_members")
        for name, item in manifest.items():
            raw = core._read_at(descriptor, name, item["size_bytes"], empty=True)
            _same(binding(raw), item, "loader_resolution_hosted_capture_raw_binding")
            files[name] = raw
        # Optional saved diagnostics are never a semantic input or oracle.
        if "verification.json" in names:
            core._read_at(descriptor, "verification.json", CONTROL_LIMIT, empty=False)
        _need(core._read_at(descriptor, "capture.json", CONTROL_LIMIT, empty=False) == capture_bytes
              and set(os.listdir(descriptor)) == names
              and core._identity(before) == core._identity(os.fstat(descriptor))
              == core._identity(os.stat(leaf, dir_fd=parent, follow_symlinks=False)),
              "loader_resolution_hosted_capture_changed")
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent)
    _need(files.get("request.json") == request_bytes, "loader_resolution_hosted_capture_request_copy")
    return request_bytes, capture_bytes, files, total


def _verify_reports(root, selection, previous=None):
    phase = selection["phase"]
    location = root / ("observation" if phase == "acquire" else "verification")
    evidence = root / "observation" if phase == "acquire" else Path(previous) / "observation"
    request_bytes, capture_bytes, files, total = _capture_materials(evidence, selection)
    request_id = request_identity(selection["context"])
    inner_root = "/output" if phase == "acquire" else "/input/observation"
    command_directory = ("observation" if phase == "acquire" else "verification") + "/commands"
    if phase == "acquire":
        command_record(root, "observe", [PYTHON, "-I", "-B", "/repo/" + CONFIG + "/run.py", "observe"],
                       directory=command_directory)
    else:
        _need(not any((location / "commands" / ("observe." + suffix)).exists()
              for suffix in ("argv.json", "result.json", "stdout.bin", "stderr.bin")),
              "loader_resolution_hosted_verifier_observation_forbidden")
    reports = []
    for ordinal in (1, 2):
        label = "capture-check-" + str(ordinal)
        raw = read_regular(location / (label + ".json"))
        report = parse(raw)
        _need(_native_report(report, request_id) and raw == canonical(report),
              "loader_resolution_hosted_native_report")
        expected_descriptors = {"request": binding(request_bytes), "capture": binding(capture_bytes),
            "source_build_report": binding(files["source_build.admission.json"]),
            "original_admission": binding(files["original.admission.json"])}
        for key, item in expected_descriptors.items():
            _same(report[key], item, "loader_resolution_hosted_report_input_binding")
        saved_build = parse(files["source_build.admission.json"])
        saved_original = parse_external(files["original.admission.json"], CONTROL_LIMIT)
        _same(report["fresh_source_build_facts"], binding(canonical({key: value
            for key, value in saved_build.items() if key not in ("backend_observation", "prior_report")})),
            "loader_resolution_hosted_rebuild_facts")
        _same(report["fresh_original_admission_facts"], binding(canonical({key: value
            for key, value in saved_original.items() if key != "signature_evidence"})),
            "loader_resolution_hosted_original_facts")
        _need(report["raw_file_count"] == len(files) and report["raw_total_bytes"] == total,
              "loader_resolution_hosted_report_raw_totals")
        command_record(root, label, [PYTHON, "-I", "-B",
            "/repo/tools/check_required_gate_idempotence_loader_resolution_v0.py",
            "--request", inner_root + "/request.json", "--request-sha256", binding(request_bytes)["sha256"],
            "--capture-dir", inner_root + "/capture", "--capture-sha256", binding(capture_bytes)["sha256"],
            "--accepted-policy-sha256", selection["context"]["accepted_policy_sha256"],
            "--output", "/output/" + label + ".json"], directory=command_directory)
        reports.append(raw)
    _need(reports[0] == reports[1], "loader_resolution_hosted_report_divergence")
    leaf = "acquisition-summary.json" if phase == "acquire" else "verification-summary.json"
    summary = _json(location / leaf)
    validate_summary(summary, phase)
    expected_summary = make_summary(phase, selection, request_bytes=request_bytes,
        capture_bytes=capture_bytes, report_bytes=reports)
    _same(summary, expected_summary, "loader_resolution_hosted_summary_binding")
    _need(summary["status"] == "completed_native_reconstruction", "loader_resolution_hosted_summary_incomplete")
    return {"request_id": request_id, "request": binding(request_bytes), "capture": binding(capture_bytes),
        "reports": [binding(raw) for raw in reports], "summary": binding(read_regular(location / leaf))}


def _completed_phase(root, ctx, phase, previous=None):
    root = Path(root)
    validate_context(ctx)
    files, _ = inventory(root)
    _need("failure.json" not in files, "loader_resolution_hosted_recorded_failure")
    opposite = "verification/" if phase == "acquire" else "observation/"
    _need(not any(name.startswith(opposite) for name in files), "loader_resolution_hosted_cross_phase_output")
    forbidden = ("base-load", "artifact-metadata", "attestation-verify") if phase == "acquire" else ("base-pull", "base-save", "base-tag")
    _need(not any("host-commands/" + label + ".argv.json" in files for label in forbidden),
          "loader_resolution_hosted_cross_phase_command")
    sources = _verify_sources(root, ctx, phase)
    raw = read_regular(root / "control/hosted-selection.json")
    selection = validate_selection(parse(raw), phase)
    _need(raw == canonical(selection), "loader_resolution_hosted_selection_canonical")
    _same(selection["context"], ctx, "loader_resolution_hosted_selection_context")
    _same(selection["sources"], sources, "loader_resolution_hosted_selection_sources")
    runtime = _verify_container(root, ctx, phase, selection, previous)
    mechanics = _verify_reports(root, selection, previous)
    return {"selection": selection, "runtime": runtime, "mechanics": mechanics}


def verify_completed_acquisition(root, ctx, receipt=None):
    if receipt is not None:
        raw = canonical(receipt)
        receipt = verify_preservation(root, raw, binding(raw)["sha256"], ctx)
        _need(receipt["phase"] == "acquire" and receipt["status"] == "completed_native_reconstruction",
              "loader_resolution_hosted_incomplete_prefix")
    checked = _completed_phase(root, ctx, "acquire")
    return {"record_type": "required_gate_idempotence_loader_resolution_hosted_acquisition_verification_v0",
        "profile": PROFILE, "status": "completed_native_reconstruction", "context": ctx,
        "image_id": checked["selection"]["image_id"], "container_id": checked["runtime"]["container_id"],
        "selection": binding(canonical(checked["selection"])), "cleanup": checked["runtime"]["cleanup"],
        **checked["mechanics"], "boundary": dict(BOUNDARY)}


def make_verified_binding(root, previous, ctx, selected_handoff, receipt):
    """Join preserved acquisition and independent replay; never run either here."""
    validate_handoff(selected_handoff)
    receipt_raw = read_regular(Path(previous) / "receipt.json")
    _need(binding(receipt_raw)["sha256"] == selected_handoff["receipt_sha256"],
          "loader_resolution_hosted_external_receipt_digest")
    validated = verify_preservation(previous, receipt_raw, selected_handoff["receipt_sha256"], ctx)
    _same(receipt, validated, "loader_resolution_hosted_receipt_selection")
    _same(_json(Path(root) / "prefix-verification.json"), {
        "record_type": "required_gate_idempotence_loader_resolution_hosted_prefix_verification_v0",
        "profile": PROFILE, "context": ctx, "handoff": selected_handoff, "receipt": binding(receipt_raw),
        "preserved_file_count": validated["file_count"] + 1, "all_preserved_bytes_verified": True,
        "preservation_is_capture_acceptance": False, "status": "preserved_prefix_verified",
        "error_code": None, "boundary": BOUNDARY}, "loader_resolution_hosted_verified_prefix")
    acquisition = verify_completed_acquisition(previous, ctx, validated)
    checked = _completed_phase(root, ctx, "verify", previous)
    _same(checked["selection"]["handoff"], selected_handoff, "loader_resolution_hosted_verification_handoff")
    metadata = command_record(root, "artifact-metadata", ["gh", "api", "repos/" + REPOSITORY +
        "/actions/artifacts/" + str(selected_handoff["artifact_id"])])
    validate_artifact_metadata(parse_external(metadata["stdout"]), ctx, selected_handoff)
    for key in ("request_id", "request", "capture", "reports"):
        _same(checked["mechanics"][key], acquisition[key], "loader_resolution_hosted_independent_report_join")
    for ordinal in (1, 2):
        _need(read_regular(Path(root) / "verification" / ("capture-check-" + str(ordinal) + ".json")) ==
              read_regular(Path(previous) / "observation" / ("capture-check-" + str(ordinal) + ".json")),
              "loader_resolution_hosted_independent_report_bytes")
    return {"record_type": "required_gate_idempotence_loader_resolution_hosted_verified_binding_v0",
        "profile": PROFILE, "status": "completed_native_reconstruction", "context": ctx,
        "handoff": selected_handoff, "receipt": binding(receipt_raw),
        "sources": checked["selection"]["sources"], "environment": ENVIRONMENT_BINDING,
        "acquisition_image_id": acquisition["image_id"], "verification_image_id": checked["selection"]["image_id"],
        "acquisition_selection": acquisition["selection"], "verification_selection": binding(canonical(checked["selection"])),
        "acquisition_cleanup": acquisition["cleanup"], "verification_cleanup": checked["runtime"]["cleanup"],
        "request_id": acquisition["request_id"], "request": acquisition["request"], "capture": acquisition["capture"],
        "reports": acquisition["reports"],
        "acquisition_summary": acquisition["summary"], "verification_summary": checked["mechanics"]["summary"],
        "artifact_metadata": binding(metadata["stdout"]), "independent_reconstruction_count": 2,
        "image_reproducibility_claimed": False, "boundary": dict(BOUNDARY)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-directory", required=True, type=Path)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--require-completed", action="store_true")
    args = parser.parse_args(argv)
    try:
        ctx = context()
        raw = read_regular(args.input_directory / "receipt.json")
        receipt = verify_preservation(args.input_directory, raw, args.receipt_sha256, ctx)
        report = {"record_type": PREFIX_TYPE, "profile": PROFILE, "status": "preserved_prefix_verified",
            "context": ctx, "receipt": binding(raw), "file_count": receipt["file_count"],
            "total_size_bytes": receipt["total_size_bytes"], "completion_verified": False, "boundary": dict(BOUNDARY)}
        if args.require_completed:
            report = verify_completed_acquisition(args.input_directory, ctx, receipt)
        write_new(args.output, report)
        return 0 if args.require_completed else 1
    except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError, RecursionError) as exc:
        code = getattr(exc, "code", "loader_resolution_hosted_verification_io")
        sys.stderr.write(code + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
