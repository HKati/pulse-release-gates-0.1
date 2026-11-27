#!/usr/bin/env python3
"""Independently reconstruct the selected containment-entry design as data.

The immutable proposal is checked against reviewed policy and original bytes,
not accepted by its authored digest alone. Sources are inspected, never imported,
extracted or executed. No host qualification, signature verification, original
program execution, historical raw-capture replay or release authority is supplied.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import copy
import hashlib
import io
import json
import lzma
import os
from pathlib import Path
import re
import stat
import struct
import sys
import zlib

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
CONTROL_BYTES = 1024 * 1024
TOOL_REL = "tools/check_required_gate_idempotence_containment_entry_plan_v0.py"
SCHEMA_REL = "schemas/required_gate_idempotence_containment_entry_plan_v0.schema.json"
INVENTORY_REL = "docs/compute/required_gate_idempotence_containment_entry_plan_v0/source_bindings_v0.json"
BASELINE_REL = "preservation/required_gate_idempotence_containment_entry_plan_v0/baseline_sources_aa7ca551_v0.zip"



# Independently selected original artifact identities and reviewed policy.
SELECTION = {'authority_effect': 'none',
 'b2_complete': False,
 'baseline_commit': 'aa7ca551a06cf553c5dc13f052693706f1227bbf',
 'baseline_files': [{'path': 'ci/pytest-tests.list',
                     'sha256': 'f3d032e96e751cc0b5dfa8657c52c2be8dfea3f56709bf986ca2e69b60ea4cc7',
                     'size_bytes': 2044},
                    {'path': 'ci/tools-tests.list',
                     'sha256': '4ca6ae37463948b0f825b09f6ccb45b19eb5b6e825315e6550e45fdfb3d9b3e2',
                     'size_bytes': 10531},
                    {'path': 'docs/compute/PULSEMECH_COMPUTE_REFERENCE_READINESS_v0.md',
                     'sha256': 'dec0e3c15071dee6d79d2049e46478a3d416134cd661b06c82526542581b230b',
                     'size_bytes': 170603},
                    {'path': 'docs/compute/PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_BOOTSTRAP_v0.md',
                     'sha256': 'ddbb26e3f5c55f0d6e523c3585b2a630328cc8bda537f9d34417564f73c1b1e4',
                     'size_bytes': 14414},
                    {'path': 'docs/compute/PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_v0.md',
                     'sha256': '417ed90969b6d9e8f972e8cfd7f5b1e4f09e299fa7578873f5b77bbdde274243',
                     'size_bytes': 16113},
                    {'path': 'docs/compute/PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_ENTRY_BUILD_v0.md',
                     'sha256': '25e587dee4e8668102a22bc8b24a17e4021895c492b6097fa6259dbfe470b517',
                     'size_bytes': 27536},
                    {'path': 'docs/compute/PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_RESOLUTION_HOSTED_v0.md',
                     'sha256': 'b58ed8b9b0e34b662e9be9ee32c5651dd437935fb036b39332a73714288b4d4f',
                     'size_bytes': 34514},
                    {'path': 'docs/compute/PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_PROTOCOL_v0.md',
                     'sha256': '66c4328d93341c39e0553e3c881aa077eafdcbcb1118c9f80277a26addb363e2',
                     'size_bytes': 11209},
                    {'path': 'docs/compute/PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_RUNTIME_v0.md',
                     'sha256': '215eb8f8e9e91dc5e99f1baf9065551fd1ea3c35ce4ca5de503d13ecc144beef',
                     'size_bytes': 14709},
                    {'path': 'schemas/required_gate_idempotence_bootstrap_v0.schema.json',
                     'sha256': '8dff32af9d769ee0f7e60b3942ce0b7cd908b61a4393cc5a3a1682b4b9599b7a',
                     'size_bytes': 3041},
                    {'path': 'schemas/required_gate_idempotence_containment_v0.schema.json',
                     'sha256': 'c22eddba2c3dbef425557aa2f6df4c27e499caac44e8710984494927ce5c7bd2',
                     'size_bytes': 4127},
                    {'path': 'schemas/required_gate_idempotence_runtime_v0.schema.json',
                     'sha256': 'fa5b046ebd66f0003becaa040cdae8d6df1d10f8e4fbe16544cff4cc7623f83e',
                     'size_bytes': 8838},
                    {'path': 'scripts/build_normative_shadow_inventory_v0.py',
                     'sha256': '997c554953e9c83445222524b9e48b7a8901e123d5269a047476224032bc8d92',
                     'size_bytes': 68617},
                    {'path': 'scripts/check_markdown_links.py',
                     'sha256': '484ed82f04bcc15c355a380e888ebb8e93e7b4b91b1cedba613598879dfee700',
                     'size_bytes': 7544},
                    {'path': 'tests/test_build_normative_shadow_inventory_v0.py',
                     'sha256': '153cf756f99979a7c2174c1dd5f333a9bbf7ed71aed53ba2558523c2efdc402b',
                     'size_bytes': 56224},
                    {'path': 'tests/test_required_gate_idempotence_containment_v0.py',
                     'sha256': '59c2c556e473bb10d55ee469a097b0a83a89636810c463208187b00741381fe6',
                     'size_bytes': 1294995},
                    {'path': 'tools/acquire_required_gate_idempotence_v0.py',
                     'sha256': 'be8798c2f5db10dd2ee275177e4dbc7ac6e6630e1f601157e2723b715c5241f8',
                     'size_bytes': 32464},
                    {'path': 'tools/check_required_gate_idempotence_containment_v0.py',
                     'sha256': '29f32971aa0a4b3d13ed850579f5eb2970dca9a0da9b07bf124fbbda9ef85af5',
                     'size_bytes': 14903},
                    {'path': 'tools/check_required_gate_idempotence_entry_task_guard_v0.py',
                     'sha256': '25fa48cc1824c0641fe0ba9265fbe3c698a3f36b19cb29adf212ffa8b049b58e',
                     'size_bytes': 24395},
                    {'path': 'tools/check_required_gate_idempotence_loader_rebuild_acceptance_v0.py',
                     'sha256': '45fe95db190c8c29a42baacfe8d5dcab8709e58b5c9b9862e9d5cd8c7ea32623',
                     'size_bytes': 21457},
                    {'path': 'tools/check_required_gate_idempotence_loader_resolution_v0.py',
                     'sha256': '520e9ad09eb568a0698822c564cf104dc1df084e105590dee99e9c13d3b7f43c',
                     'size_bytes': 32770},
                    {'path': 'tools/required_gate_idempotence_bootstrap_probe_v0.py',
                     'sha256': 'e4e410d6cac1142b0e75f1186fbc24abb759e0f6e3f02ab453cbdb9309bf6bde',
                     'size_bytes': 21002},
                    {'path': 'tools/required_gate_idempotence_bootstrap_v0.py',
                     'sha256': '839c87f15c8e56392113f042a79d45a8453000581eaa98778c36283fb30c4c6c',
                     'size_bytes': 26767},
                    {'path': 'tools/required_gate_idempotence_containment_entry_v0.c',
                     'sha256': '0265273af5a51301035bbd4d2418d4ab87e8572a56bddbf028c95e12e7e2631f',
                     'size_bytes': 4598},
                    {'path': 'tools/required_gate_idempotence_containment_policy_v0.py',
                     'sha256': '105c72f436d4c13d21da160eb185fa3fc17663a8e904b43b7c30f88691573a03',
                     'size_bytes': 3823},
                    {'path': 'tools/required_gate_idempotence_containment_v0.py',
                     'sha256': 'b6ec187c154b9cf5419f72208e6dccd391bd9f53600379b3b8ed8e759dc6bfbb',
                     'size_bytes': 27964},
                    {'path': 'tools/required_gate_idempotence_entry_task_guard_v0.py',
                     'sha256': '7d739ea58aa248c6d1785882847ee1d45b9e32925514cc7b0cf510558fbdf83d',
                     'size_bytes': 23130},
                    {'path': 'tools/required_gate_idempotence_loader_rebuild_acceptance_v0.py',
                     'sha256': '9fa78e0754357bbdeabdfaa9e57a747bb6126fd3945862e54b78150a81bd982a',
                     'size_bytes': 30681},
                    {'path': 'tools/required_gate_idempotence_loader_resolution_hosted_v0/Dockerfile',
                     'sha256': '8d3b679546341488e00d3c72d6a979c51eb1f1c12d414da83ddab81478bed6f6',
                     'size_bytes': 868},
                    {'path': 'tools/required_gate_idempotence_loader_resolution_hosted_v0/environment.json',
                     'sha256': '677e221369cd27420ec726974f204b7a2be1444437ae7df494bd12786308762b',
                     'size_bytes': 25705},
                    {'path': 'tools/required_gate_idempotence_loader_resolution_v0.py',
                     'sha256': '153228659283d45b24b2f55aa014f95b68b734534d6081e4188bbe5a9e926bc8',
                     'size_bytes': 27846},
                    {'path': 'tools/required_gate_idempotence_process_v0.py',
                     'sha256': 'fc682fef2753fe4d65a2f0f839b696f77bc27b468ff0191b508df5e1887bd09a',
                     'size_bytes': 18107},
                    {'path': 'tools/required_gate_idempotence_runtime_v0.py',
                     'sha256': '760ea1c13f58d2ec83fef29b9d346a937b3f03c57013fe3320c473e58ac43d8b',
                     'size_bytes': 34677},
                    {'path': 'tools/required_gate_idempotence_worker_v0.py',
                     'sha256': 'cce14b088f8519e24c4c19879a4cb78d0e59025e4c6da1010a321c1ea7437bd2',
                     'size_bytes': 12250}],
 'baseline_repository': 'HKati/pulse-release-gates-0.1',
 'bubblewrap_source': {'build_selection': {'assume_kernel': '5.10.0',
                                           'hardening': '+pie,+bindnow',
                                           'source_format': '3.0 (quilt)'},
                       'joined_compressed_source_index': {'sha256': '6002f81f463a2d976d84b34170367cc16da2d60bd0ba9ab9d868d6e1c1a935d9',
                                                          'size_bytes': 10540436},
                       'matched_stanza': {'directory': 'pool/main/b/bubblewrap',
                                          'exact_bytes_without_blank_separator': {'sha256': 'd8e175fe8cf6fb37ed15273c14df41b6101767b5d72fdbfa9448cf2d7c93b039',
                                                                                  'size_bytes': 1536},
                                          'package': 'bubblewrap',
                                          'version': '0.12.0-1~deb13u1'},
                       'new_source_files': [{'matched_preserved_sources_stanza': True,
                                             'path': 'preservation/required_gate_idempotence_containment_entry_plan_v0/raw/bubblewrap_0.12.0-1~deb13u1.debian.tar.xz',
                                             'retrieval_url': 'https://deb.debian.org/debian/pool/main/b/bubblewrap/bubblewrap_0.12.0-1~deb13u1.debian.tar.xz',
                                             'sha256': '7b54f121aebf5d4b38360ea728274c26fa471582bc3e6658379b679ecd8b5a2f',
                                             'size_bytes': 13728},
                                            {'matched_preserved_sources_stanza': True,
                                             'path': 'preservation/required_gate_idempotence_containment_entry_plan_v0/raw/bubblewrap_0.12.0-1~deb13u1.dsc',
                                             'retrieval_url': 'https://deb.debian.org/debian/pool/main/b/bubblewrap/bubblewrap_0.12.0-1~deb13u1.dsc',
                                             'sha256': '1abef77e6c35ce6c48c8969d31bffcc7a589bfd8e8fea9284fd8d77750f01d39',
                                             'size_bytes': 2362},
                                            {'matched_preserved_sources_stanza': True,
                                             'path': 'preservation/required_gate_idempotence_containment_entry_plan_v0/raw/bubblewrap_0.12.0.orig.tar.xz',
                                             'retrieval_url': 'https://deb.debian.org/debian/pool/main/b/bubblewrap/bubblewrap_0.12.0.orig.tar.xz',
                                             'sha256': '9760d007363e3abba7c747489910f9f82d9fca53ba3bd3282e396fa3c97a3314',
                                             'size_bytes': 126452}],
                       'patch_scope': 'Only the clone EPERM diagnostic text changes; no reviewed '
                                      'process, namespace, seccomp or descriptor operation '
                                      'changes.',
                       'patch_series': ['debian/Change-EPERM-error-message-to-show-Debian-specific-inform.patch'],
                       'pre_5_6_openat_fallback_compiled_out_by_declared_build_selection': True,
                       'required_openat2_resolution': ['RESOLVE_IN_ROOT', 'RESOLVE_NO_MAGICLINKS'],
                       'reviewed_debian_members': [{'member': 'debian/patches/series',
                                                    'sha256': '409749282d0ae668c26a8c8b72ecd0d1f463a96a7906053d5bcfea587d6ab492',
                                                    'size_bytes': 71},
                                                   {'member': 'debian/patches/debian/Change-EPERM-error-message-to-show-Debian-specific-inform.patch',
                                                    'sha256': 'e86a163263e90d0020f40604a85f6525f23c8f8f66fc0ff9ee4c623ef1ed78ea',
                                                    'size_bytes': 1063},
                                                   {'member': 'debian/rules',
                                                    'sha256': '2e15a6db8bc7c8be3ee19456ac3121b19743208c8244ec4bd2c27631d60245ff',
                                                    'size_bytes': 730},
                                                   {'member': 'debian/source/format',
                                                    'sha256': '1be7080d72e6b566df3e236ce2c55efdfbbb8fa1c972d825e5b672ff8773be1a',
                                                    'size_bytes': 12},
                                                   {'member': 'debian/control',
                                                    'sha256': '8b5a7586efeb4f3436a744e21b99208b39c440345174f91ac10b59b27c1ac0e1',
                                                    'size_bytes': 1367},
                                                   {'member': 'debian/copyright',
                                                    'sha256': 'a259c729f78b980b76624f923dad96707754cc7bef5e5e37659466d77da33170',
                                                    'size_bytes': 1897}],
                       'reviewed_original_members': [{'member': 'bubblewrap-0.12.0/bubblewrap.c',
                                                      'sha256': '3f17ee26057cae9d660801ca8d9ba84722f1bafdcd072d5151ee1c64eeeb15f4',
                                                      'size_bytes': 113001},
                                                     {'member': 'bubblewrap-0.12.0/utils.c',
                                                      'sha256': 'b53c73465e0188259a8438396e25531f6b6ae7e2fb88d37bf13cee29acedd222',
                                                      'size_bytes': 21976},
                                                     {'member': 'bubblewrap-0.12.0/safe_openat.c',
                                                      'sha256': '0338ec8e8fbc08caf20c6a3480506f60f510e7e43abacbd40d17cd6d562970d2',
                                                      'size_bytes': 9274},
                                                     {'member': 'bubblewrap-0.12.0/bwrap.xml',
                                                      'sha256': '02a822fe5e3d74da236863cd2157a8dc950e280b50886eac359cb056a7142a48',
                                                      'size_bytes': 33172},
                                                     {'member': 'bubblewrap-0.12.0/meson.build',
                                                      'sha256': '6909022047bcc8c36e1fa07d8b7642f6db39d86df2e62d34be2685fd0e6099ba',
                                                      'size_bytes': 4743},
                                                     {'member': 'bubblewrap-0.12.0/COPYING',
                                                      'sha256': 'dc626520dcd53a22f727af3ee42c770e56c97a64fe3adb063799d8ab032fe551',
                                                      'size_bytes': 26530}],
                       'source_index_parts': [{'path': 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/Sources.xz.part001',
                                               'sha256': '3dd4790f65540cb7004b5b13cc98d60b706fa62ec347da24f34629c18d1bc724',
                                               'size_bytes': 8000000},
                                              {'path': 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/Sources.xz.part002',
                                               'sha256': '4a2df0061f07a5aabc5a976cd4c5c80faa1a25f9455b67780fd87e7d2c5270cf',
                                               'size_bytes': 2540436}]},
 'existing_containment_policy': {'derived_classic_bpf': {'encoding': 'x86_64-little-endian-sock_filter',
                                                         'installed_in_this_unit': False,
                                                         'instruction_count': 145,
                                                         'sha256': '9f3570a87b1fde59299d69d242496cbd9d2f1b1631a40dbc5ed8e4976edfa6ab',
                                                         'size_bytes': 1160},
                                 'source': {'path': 'tools/required_gate_idempotence_containment_policy_v0.py',
                                            'sha256': '105c72f436d4c13d21da160eb185fa3fc17663a8e904b43b7c30f88691573a03',
                                            'size_bytes': 3823}},
 'glibc_source': {'debian_carrier': {'path': 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/glibc_2.41-12+deb13u4.debian.tar.xz',
                                     'sha256': 'dda4153511bfd543502d18e5bc9323110996fe9c531f14ae3fad6eb17f027c7d',
                                     'size_bytes': 499524},
                  'joined_original_archive': {'sha256': 'f24aa441021121a79266f0d75242706cab8843a47901fefe74527491807f1998',
                                              'size_bytes': 20323540},
                  'original_parts': [{'path': 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/glibc_2.41.orig.tar.xz.part001',
                                      'sha256': '4790b9cafe4425b2776884b87f345591accb35232f6db5d891d869d20626fde4',
                                      'size_bytes': 8000000},
                                     {'path': 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/glibc_2.41.orig.tar.xz.part002',
                                      'sha256': '89c780719196bcbdce8ba0290918ea5468a681525b5836d24cbf2d788c9e5f75',
                                      'size_bytes': 8000000},
                                     {'path': 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/glibc_2.41.orig.tar.xz.part003',
                                      'sha256': '875cb7ed49f8f386a6ba4948dad2eeb4da80494ece0c49d566a93271870997ba',
                                      'size_bytes': 4323540}],
                  'patches_touching_reviewed_members': [{'member': 'debian/patches/git-updates.diff',
                                                         'sha256': 'c3c28ea3a3a9ae8478ff7c051202bafefe165e60e11f707389751e7c850956de',
                                                         'size_bytes': 623020,
                                                         'touches_reviewed_members': ['posix/fork.c']}],
                  'review_scope': 'The selected fork patch updates local NSS bookkeeping; the '
                                  'reviewed _Fork/arch_fork clone and wait/waitpid/wait4 chain is '
                                  'unchanged. This is source review, not executed build '
                                  'provenance.',
                  'reviewed_original_members': [{'member': 'glibc-2.41/posix/fork.c',
                                                 'sha256': '00baa38eeb752064ece368d891130297988564601f17ac0bceead9775180f7e2',
                                                 'size_bytes': 4474},
                                                {'member': 'glibc-2.41/sysdeps/nptl/_Fork.c',
                                                 'sha256': '5f01c75b06211489040fe196811bd350b17ed6ffdfc159bd6aaae9e9236132de',
                                                 'size_bytes': 2350},
                                                {'member': 'glibc-2.41/sysdeps/unix/sysv/linux/arch-fork.h',
                                                 'sha256': '34fd5da5e26f2c0d732e993a66882224db97b18da3c808786f2f42a9fc16e2f6',
                                                 'size_bytes': 2124},
                                                {'member': 'glibc-2.41/sysdeps/unix/sysv/linux/kernel-features.h',
                                                 'sha256': 'ce148eed2743d0085a80217f2c0d01e002b37c35ed2d32bdad351981ddb66dc1',
                                                 'size_bytes': 9368},
                                                {'member': 'glibc-2.41/sysdeps/unix/sysv/linux/x86_64/kernel-features.h',
                                                 'sha256': 'ba3b7f8f95a106dc1001dd1b32ae2e9d3e1b7c85ddf6645f708eb6183e882070',
                                                 'size_bytes': 1111},
                                                {'member': 'glibc-2.41/posix/wait.c',
                                                 'sha256': '010e249f36c8b3445307227ea9bc13981b3de9e30ddb1b9c1b8fe14553c678af',
                                                 'size_bytes': 1056},
                                                {'member': 'glibc-2.41/posix/waitpid.c',
                                                 'sha256': '51dbddcfc3873e5dfa064c409bae2863af2d9735117a0ad0b54f56fd987b5f2f',
                                                 'size_bytes': 1683},
                                                {'member': 'glibc-2.41/sysdeps/unix/sysv/linux/wait4.c',
                                                 'sha256': '2d82bfd0292d16c2dcf2d56866ba64faaa656d83d1428808b40e0c356b8fce60',
                                                 'size_bytes': 3570}]},
 'historical_example_runtime': {'can_be_promoted_to_selected_by_relabelling': False,
                                'capsule': {'member': 'capsule/authored-runtime-capsule.zip',
                                            'sha256': 'c5c85a7c2b19b6e2c8be18f743cecea056d8e639ae88fdf4f4fbd2d71fa38ec9',
                                            'size_bytes': 219962},
                                'carrier': {'path': 'preservation/required_gate_idempotence_exec_stop_v0/original_inputs_v0.zip',
                                            'sha256': '70b57f9a40cb375e267e215b3704be21c9f6d8987cadc13d92dfcc8db56d9c8a',
                                            'size_bytes': 24816167},
                                'python': {'member': 'payload/python/bin/python3.11',
                                           'sha256': 'a21685417aaa2029ae4ddb67e0c0f88d8c8e42ff03b949de1cfc1c613c991609',
                                           'size_bytes': 1056},
                                'records': [{'member': 'controls/runtime-selection.json',
                                             'record_status': 'example',
                                             'sha256': '029c4742f7a900b54a7896a8135b7ae5f64ad78766d0dd4ed172a8937289bec6',
                                             'size_bytes': 26110},
                                            {'member': 'controls/operator-selection.json',
                                             'record_status': 'example',
                                             'sha256': '17334a9237b3a2c7063f04af5cf54048a2fa24ba88bda73193e9ac5b89cce3c3',
                                             'size_bytes': 4149},
                                            {'member': 'controls/bootstrap-selection.json',
                                             'record_status': 'example',
                                             'sha256': '39ad34794078aeb1cb2c561dbb9c41670dc7ed9fa17fe9f76ea1cd082ac41a61',
                                             'size_bytes': 804},
                                            {'member': 'controls/containment-selection.json',
                                             'record_status': 'example',
                                             'sha256': '7b95676d06b84d396423a66629f48eb0f177986ed56d2a00b02ea8905fe9b62c',
                                             'size_bytes': 1057}]},
 'historical_loader_observation': {'attempt': 1,
                                   'control_carrier': {'path': 'preservation/required_gate_idempotence_loader_resolution_v0/run_45881405789_attempt_1/control_evidence_v0.zip',
                                                       'sha256': '7f67a1f6dc816ae382d140d91e9f95b754d766cee6645d8607a4b2398ce1ad9c',
                                                       'size_bytes': 5994163},
                                   'fresh_replay_in_this_design_unit': False,
                                   'live_prefix_available': False,
                                   'preservation_record': {'path': 'preservation/required_gate_idempotence_loader_resolution_v0/run_45881405789_attempt_1/verification_record_v0.json',
                                                           'sha256': '60578dd84f76cb89630267699c290f42c41dc90b7285ae9f535e8594bab3bfef',
                                                           'size_bytes': 440911},
                                   'run_id': 45881405789,
                                   'run_number': 3,
                                   'source_commit': 'f2854184ebb069ed6407874a68a4aaa1c84fea5c'},
 'inventory_is_complete_future_execution_closure': False,
 'metric_pass': None,
 'original_native_inputs': {'carrier': {'path': 'preservation/required_gate_idempotence_exec_stop_v0/original_inputs_v0.zip',
                                        'sha256': '70b57f9a40cb375e267e215b3704be21c9f6d8987cadc13d92dfcc8db56d9c8a',
                                        'size_bytes': 24816167},
                            'members': [{'member': 'native/bwrap',
                                         'sha256': '573236e5328ac2ebb08f59ae3a9805b4f8d12bdef14be8af4450d5463294985f',
                                         'size_bytes': 80248},
                                        {'member': 'native/ld-linux-x86-64.so.2',
                                         'sha256': 'c8438e4fde1934e61c88311633f00949ff645d5c04cdb8671fa3d78164d2f307',
                                         'size_bytes': 225672},
                                        {'member': 'native/libc.so.6',
                                         'sha256': '9792e3cbb541c8f44c7acf5f14f4022ea62998ecc787d326bed4d8b6547dfd92',
                                         'size_bytes': 1995216},
                                        {'member': 'native/libcap.so.2',
                                         'sha256': '41217b0af128444f66dee8adda52b2ceaf19da00e5b0b155e2b87b857671286b',
                                         'size_bytes': 47288},
                                        {'member': 'native/libpcre2-8.so.0',
                                         'sha256': '92e9b4167f9bbc237ca8f5526d82ee99ec9f8dbd0270ef1dd0ab24e2217f48e3',
                                         'size_bytes': 711216},
                                        {'member': 'native/libselinux.so.1',
                                         'sha256': '5cb5293b4e7590463b94f7b23152d54807a6a2ccaf8cac9e343908c6692c086c',
                                         'size_bytes': 202984}],
                            'selected_package': {'architecture': 'amd64',
                                                 'name': 'bubblewrap',
                                                 'sha256': '70aca4fa8daeacb677ec00e8063eb586f08ae3d94b1f11e684370b5524c43431',
                                                 'size_bytes': 56876,
                                                 'version': '0.12.0-1~deb13u1'}},
 'record_status': 'authored_design_inventory',
 'record_type': 'required_gate_idempotence_containment_entry_plan_source_inventory_v0',
 'static_entry': {'attempt': 1,
                  'build_carrier': {'path': 'preservation/required_gate_idempotence_entry_build_v0/run_43854478248_attempt_1/required-gate-idempotence-entry-build-43854478248-1.zip',
                                    'sha256': '1ad3f84009ff7446e204ab18cb61bd5494a6d1182878833de017a438a3f36855',
                                    'size_bytes': 64298},
                  'members': [{'member': 'evidence/build-1/entry',
                               'sha256': '7a21b2e4d60dc080149d9a919b604e39f6fb29be42d462e979b46d3c439b95ab',
                               'size_bytes': 9568},
                              {'member': 'evidence/build-2/entry',
                               'sha256': '7a21b2e4d60dc080149d9a919b604e39f6fb29be42d462e979b46d3c439b95ab',
                               'size_bytes': 9568}],
                  'run_id': 43854478248,
                  'source': {'path': 'tools/required_gate_idempotence_containment_entry_v0.c',
                             'sha256': '0265273af5a51301035bbd4d2418d4ab87e8572a56bddbf028c95e12e7e2631f',
                             'size_bytes': 4598},
                  'source_binary_semantic_equivalence_claimed': False,
                  'source_commit': 'f290aee20cd610e4fdb358dbf34d054ec351d390'},
 'trust_limits': {'fresh_attestation_signature_verification': False,
                  'fresh_distribution_signature_verification': False,
                  'future_host_admitted': False,
                  'native_build_performed': False,
                  'patches_applied': False,
                  'source_binary_equivalence_verified': False,
                  'source_bytes_matched_preserved_index': True}}

INPUT_BINDINGS = {'preservation/required_gate_idempotence_containment_entry_plan_v0/baseline_sources_aa7ca551_v0.zip': {'sha256': '0008c5aa1dfce8052d8c0cd06429bef00ee5d499888c7d732bc7e38012089bd1',
                                                                                                       'size_bytes': 522415},
 'preservation/required_gate_idempotence_containment_entry_plan_v0/raw/bubblewrap_0.12.0-1~deb13u1.debian.tar.xz': {'sha256': '7b54f121aebf5d4b38360ea728274c26fa471582bc3e6658379b679ecd8b5a2f',
                                                                                                                    'size_bytes': 13728},
 'preservation/required_gate_idempotence_containment_entry_plan_v0/raw/bubblewrap_0.12.0-1~deb13u1.dsc': {'sha256': '1abef77e6c35ce6c48c8969d31bffcc7a589bfd8e8fea9284fd8d77750f01d39',
                                                                                                          'size_bytes': 2362},
 'preservation/required_gate_idempotence_containment_entry_plan_v0/raw/bubblewrap_0.12.0.orig.tar.xz': {'sha256': '9760d007363e3abba7c747489910f9f82d9fca53ba3bd3282e396fa3c97a3314',
                                                                                                        'size_bytes': 126452},
 'preservation/required_gate_idempotence_entry_build_v0/run_43854478248_attempt_1/required-gate-idempotence-entry-build-43854478248-1.zip': {'sha256': '1ad3f84009ff7446e204ab18cb61bd5494a6d1182878833de017a438a3f36855',
                                                                                                                                             'size_bytes': 64298},
 'preservation/required_gate_idempotence_exec_stop_v0/original_inputs_v0.zip': {'sha256': '70b57f9a40cb375e267e215b3704be21c9f6d8987cadc13d92dfcc8db56d9c8a',
                                                                                'size_bytes': 24816167},
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/Sources.xz.part001': {'sha256': '3dd4790f65540cb7004b5b13cc98d60b706fa62ec347da24f34629c18d1bc724',
                                                                                            'size_bytes': 8000000},
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/Sources.xz.part002': {'sha256': '4a2df0061f07a5aabc5a976cd4c5c80faa1a25f9455b67780fd87e7d2c5270cf',
                                                                                            'size_bytes': 2540436},
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/glibc_2.41-12+deb13u4.debian.tar.xz': {'sha256': 'dda4153511bfd543502d18e5bc9323110996fe9c531f14ae3fad6eb17f027c7d',
                                                                                                             'size_bytes': 499524},
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/glibc_2.41.orig.tar.xz.part001': {'sha256': '4790b9cafe4425b2776884b87f345591accb35232f6db5d891d869d20626fde4',
                                                                                                        'size_bytes': 8000000},
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/glibc_2.41.orig.tar.xz.part002': {'sha256': '89c780719196bcbdce8ba0290918ea5468a681525b5836d24cbf2d788c9e5f75',
                                                                                                        'size_bytes': 8000000},
 'preservation/required_gate_idempotence_loader_binary_binding_v0/raw/glibc_2.41.orig.tar.xz.part003': {'sha256': '875cb7ed49f8f386a6ba4948dad2eeb4da80494ece0c49d566a93271870997ba',
                                                                                                        'size_bytes': 4323540},
 'preservation/required_gate_idempotence_loader_resolution_v0/run_45881405789_attempt_1/control_evidence_v0.zip': {'sha256': '7f67a1f6dc816ae382d140d91e9f95b754d766cee6645d8607a4b2398ce1ad9c',
                                                                                                                   'size_bytes': 5994163},
 'preservation/required_gate_idempotence_loader_resolution_v0/run_45881405789_attempt_1/verification_record_v0.json': {'sha256': '60578dd84f76cb89630267699c290f42c41dc90b7285ae9f535e8594bab3bfef',
                                                                                                                       'size_bytes': 440911}}

PLAN_POLICY = {'acceptance_cases': [{'id': 'original_admission',
                       'positive': 'Fresh original-input, static-entry, source and explicit '
                                   'trust-policy reconstruction succeeds before any native probe '
                                   'or original launch.',
                       'reject_or_incomplete': 'Cached verdict, altered signed bytes, rehashed '
                                               'substitution, missing source member, or '
                                               'example-runtime relabelling.'},
                      {'id': 'minimal_request',
                       'positive': 'Only the declared argv, exact minimal view, two filters and '
                                   'fixed worker phase are selected.',
                       'reject_or_incomplete': 'Unreviewed flags, --try variants, --as-pid-1, '
                                               'external namespace FDs, Python/runtime files or '
                                               'caller-selected executable.'},
                      {'id': 'host_qualification',
                       'positive': 'Fresh same-host qualification establishes exact required '
                                   'namespaces, openat2, cross-namespace tracing/proc reads and '
                                   'owned cleanup, including explicitly selected negative checks.',
                       'reject_or_incomplete': 'Unexpected denial or unsupported return on an '
                                               'operation required to succeed; incomplete '
                                               'qualifier, different observer/kernel/environment, '
                                               'or automatic privileged/unconfined fallback. '
                                               'Expected extra-userns denial is not such a '
                                               'failure.'},
                      {'id': 'task_graph',
                       'positive': 'L creates R once and R creates T once with the two '
                                   'source-bound clone contracts and complete role identities.',
                       'reject_or_incomplete': 'Extra or missing task, wrong parent, clone flags, '
                                               'syscall ABI, role/order, reused PID or ignored '
                                               'task-creation event.'},
                      {'id': 'exec_boundary',
                       'positive': 'The two declared exec transitions occur; T is stopped at the '
                                   'exact static ELF entry after successful exec and before user '
                                   'instructions.',
                       'reject_or_incomplete': 'Wrong executable, signal mistaken for exec event, '
                                               'failed exec, additional exec, altered RIP, or any '
                                               'terminal T restart.'},
                      {'id': 'namespaces',
                       'positive': 'Final R/T namespace handles, maps and per-role observations '
                                   'match the declared new containment relations.',
                       'reject_or_incomplete': 'Early namespace report only, inode inequality '
                                               'alone, missing final maps, alias/reuse, or host '
                                               'namespace substituted.'},
                      {'id': 'readonly_view',
                       'positive': 'Pinned T root, complete path/mount roster, modes and copied '
                                   'entry bytes match the private read-only minimal view.',
                       'reject_or_incomplete': 'Writable effective mount, unexpected path/mount, '
                                               'missing root walk, symlink escape, host directory, '
                                               'proc/dev, or assuming memfd inode equals installed '
                                               'executable.'},
                      {'id': 'policy_submission',
                       'positive': 'Each of R and T has its own exact selected-program '
                                   'syscall-entry bytes, successful return and task-bound '
                                   'installation evidence.',
                       'reject_or_incomplete': 'Seccomp=2 alone, wrong BPF bytes, one role '
                                               'missing, nonzero return, or treating R '
                                               'installation as inherited by already-forked T.'},
                      {'id': 'terminal_state',
                       'positive': 'T has exact stdio descriptors, selected environment including '
                                   'PWD, zero selected capability fields and NNP=1.',
                       'reject_or_incomplete': 'Extra/unknown FD, missing observation, unexpected '
                                               'capability/environment, or claiming the unexecuted '
                                               'shim performed checks/close_range/limits.'},
                      {'id': 'observer_integrity',
                       'positive': 'The owned observer records complete ordered raw events without '
                                   'code, memory, syscall or register substitution.',
                       'reject_or_incomplete': 'Instruction patch, forged register state, syscall '
                                               'substitution, unexplained detach/resume or trusted '
                                               'producer verdict replacing raw data.'},
                      {'id': 'cleanup',
                       'positive': 'Bounded SIGKILL and tracing/adoption/reap drain account for '
                                   'every owned identity and prove no live subject remains.',
                       'reject_or_incomplete': 'Only L reaped, fixed-three-wait shortcut, leaked '
                                               'R/T, stale PGID signal, missing terminal identity, '
                                               'or cleanup overwrites the primary failure.'},
                      {'id': 'independent_replay',
                       'positive': 'A separate data-only checker reconstructs sources, request, '
                                   'raw events, all relations, counts and cleanup without '
                                   'executing subject bytes.',
                       'reject_or_incomplete': 'Missing/duplicate/reordered events, truncated '
                                               'streams, wrong occurrence joins, mutable input, or '
                                               'producer/hosted-summary-only acceptance.'},
                      {'id': 'incomplete_prefix',
                       'positive': 'Every timeout, interruption, budget breach or unsupported '
                                   'event is preserved as incomplete with its exact primary '
                                   'failure.',
                       'reject_or_incomplete': 'Skipped or warning-only qualification treated as '
                                               'success, retry appended to same attempt, or '
                                               'omitted failure prefix.'},
                      {'id': 'claim_scope',
                       'positive': 'A completed future record reports only observed '
                                   'containment-entry relations within declared observer/kernel '
                                   'trust.',
                       'reject_or_incomplete': 'Physical authenticity, kernel filter readback, '
                                               'shim/Python/operator execution, B2 completion, '
                                               'metric pass or release authority inferred from an '
                                               'intermediate success.'}],
 'authority_effect': 'none',
 'b2_complete': False,
 'baseline_commit': 'aa7ca551a06cf553c5dc13f052693706f1227bbf',
 'bootstrap_execution_observed': False,
 'ci_boundary': {'current_manifest_changes': False,
                 'new_tests_append_to_existing_containment_module': True,
                 'new_workflow_requires_explicit_path_and_hash_carrier_classification': True,
                 'preserve_historical_test_prefixes': True},
 'containment_observed': False,
 'entry_source_binary_equivalence_verified': False,
 'execution_authorized': False,
 'execution_ready': False,
 'future_implementation_paths_all_proposed': {'existing_files_with_narrow_future_updates': ['tests/test_required_gate_idempotence_containment_v0.py',
                                                                                            'tests/test_build_normative_shadow_inventory_v0.py',
                                                                                            'scripts/build_normative_shadow_inventory_v0.py',
                                                                                            'docs/INDEX.md',
                                                                                            'CHANGELOG.md'],
                                              'finite_original_observation': ['tools/required_gate_idempotence_containment_entry_v0.py',
                                                                              'tools/prepare_required_gate_idempotence_containment_entry_v0.py',
                                                                              'tools/collect_required_gate_idempotence_containment_entry_v0.py',
                                                                              'tools/check_required_gate_idempotence_containment_entry_v0.py',
                                                                              'schemas/required_gate_idempotence_containment_entry_v0.schema.json'],
                                              'future_observation_documentation': ['docs/compute/PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_ENTRY_v0.md',
                                                                                   'docs/compute/PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_ENTRY_HOSTED_v0.md'],
                                              'plan_checking': ['schemas/required_gate_idempotence_containment_entry_plan_v0.schema.json',
                                                                'tools/check_required_gate_idempotence_containment_entry_plan_v0.py'],
                                              'separate_hosted_route_after_local_review': ['.github/workflows/required_gate_idempotence_containment_entry_v0.yml',
                                                                                           'tools/required_gate_idempotence_containment_entry_hosted_v0.py',
                                                                                           'tools/check_required_gate_idempotence_containment_entry_hosted_v0.py',
                                                                                           'schemas/required_gate_idempotence_containment_entry_hosted_v0.schema.json',
                                                                                           'tools/required_gate_idempotence_containment_entry_hosted_v0/environment.json',
                                                                                           'tools/required_gate_idempotence_containment_entry_hosted_v0/Dockerfile',
                                                                                           'tools/required_gate_idempotence_containment_entry_hosted_v0/requirements.lock',
                                                                                           'tools/required_gate_idempotence_containment_entry_hosted_v0/build_environment.py',
                                                                                           'tools/required_gate_idempotence_containment_entry_hosted_v0/run.py'],
                                              'startup_and_host_qualification': ['tools/required_gate_idempotence_containment_startup_v0.c',
                                                                                 'tools/required_gate_idempotence_containment_task_probe_v0.c',
                                                                                 'tools/required_gate_idempotence_containment_task_guard_v0.py',
                                                                                 'tools/qualify_required_gate_idempotence_containment_task_guard_v0.py',
                                                                                 'tools/check_required_gate_idempotence_containment_task_guard_v0.py',
                                                                                 'schemas/required_gate_idempotence_containment_task_guard_v0.schema.json']},
 'host_environment_qualified': False,
 'implemented': False,
 'independent_plan_checker_implemented': False,
 'metric_pass': None,
 'model_call_count': 0,
 'native_acquisition_performed': False,
 'next_terminal_boundary': {'allowed_post_terminal_T_restarts': 0,
                            'event': 'PTRACE_EVENT_EXEC',
                            'python_executed': False,
                            'rip_requirement': 'Exact admitted static ELF e_entry after successful '
                                               'exec; no interpreter and no user instruction '
                                               'executed.',
                            'role': 'T',
                            'selected_bootstrap_loader_executed': False,
                            'shim_checks_executed': False,
                            'shim_close_range_executed': False,
                            'shim_environment_replacement_executed': False,
                            'shim_rlimits_installed': False},
 'observation_contract': {'R_park': {'options': 0,
                                     'pid_semantics': -1,
                                     'rusage': 0,
                                     'status_pointer': 'dynamic writable task memory bound at '
                                                       'syscall entry',
                                     'syscall_number': 61},
                          'all_subject_identities_required': True,
                          'cleanup': 'At successful terminal collection all three roles are '
                                     'owned/stopped: pidfd_send_signal(SIGKILL,NULL,0) in T/R/L '
                                     'order, then globally drain nonblocking owned '
                                     'trace/adoption/reap notifications until no live owned '
                                     'identity remains; never block on R ahead of T or assume '
                                     'exactly three wait results.',
                          'explicit_stop_state_ledger': 'Never INTERRUPT an already stopped role; '
                                                        'record every stop and restart.',
                          'final_removal': 'Consumed terminal statuses plus qualified final pidfd '
                                           'POLLHUP and drained owned wait state; POLLIN/zombie, '
                                           'WNOHANG=0 or ESRCH alone is insufficient.',
                          'fresh_L_checkpoints': ['initial launcher exec-stop binds '
                                                  'launcher/interpreter identity',
                                                  'separate stopped syscall-entry checkpoint '
                                                  'before first namespace clone binds complete '
                                                  'selected-native mapping/backing roster'],
                          'helper_is_L_preexec_not_fourth_task': True,
                          'historical_capture_can_supply_live_prefix': False,
                          'incomplete_prefix_cleanup': 'Signal and drain only identities actually '
                                                       'created and owned, in reverse role order; '
                                                       'do not wait for absent roles or require '
                                                       'every survivor to reach its intended stop '
                                                       'before SIGKILL. Missing final removal '
                                                       'proof keeps the attempt incomplete.',
                          'initial_barrier': 'EOF, invalid token or observer loss fails closed. '
                                             'SEIZE alone is not a stop; consume INTERRUPT stop '
                                             'before release. No intermediate helper task or '
                                             'shell.',
                          'new_argv_nine_return_observation_claimed': False,
                          'new_startup_helper_required': True,
                          'newborn_stop_join': 'Join parent event-message outer PID and newborn '
                                               'PTRACE_EVENT_STOP/SIGTRAP regardless of '
                                               'notification order; inherited options, no '
                                               'reattach.',
                          'observed_seccomp_submission_roles': ['R', 'T'],
                          'observer_subreaper': 'Set and read back PR_SET_CHILD_SUBREAPER before '
                                                'L; normal SIGCHLD disposition, no SA_NOCLDWAIT or '
                                                'competing wait consumer; restore prior state only '
                                                'after verified cleanup.',
                          'observer_writes_prohibited': ['subject code patch',
                                                         'subject memory mutation',
                                                         'register substitution',
                                                         'syscall substitution'],
                          'old_guard_or_two_slot_qualification_admits_new_profile': False,
                          'post_terminal_T_restart_allowed': False,
                          'ptrace_options': ['PTRACE_O_TRACEFORK',
                                             'PTRACE_O_TRACEVFORK',
                                             'PTRACE_O_TRACECLONE',
                                             'PTRACE_O_TRACEEXEC',
                                             'PTRACE_O_TRACESYSGOOD',
                                             'PTRACE_O_EXITKILL'],
                          'ptrace_strategy': 'PTRACE_SEIZE at owned barrier, PTRACE_INTERRUPT, '
                                             'then bounded PTRACE_SYSCALL; never detach',
                          'ptrace_traceexit_enabled': False,
                          'required_raw_evidence': ['ordered wait/syscall/event records',
                                                    'per-role executable and identity',
                                                    'paired stop samples',
                                                    'final namespace handles and uid/gid maps',
                                                    'task-bound mountinfo and pinned root walk',
                                                    'exact file bytes/modes and descriptor roster',
                                                    'per-role credentials/capabilities/NNP/seccomp '
                                                    'state',
                                                    'R and T sock_fprog and BPF submission '
                                                    'bytes/returns',
                                                    'complete bounded stdout/stderr',
                                                    'all continuation and signal operations',
                                                    'complete cleanup/adoption/reaping records'],
                          'seccomp_claim': 'Exact selected-program submission and successful '
                                           'return, not privileged kernel filter readback or '
                                           'exhaustive future behavior.',
                          'unexpected_native_mapping': 'Reject before further subject execution; '
                                                       'never extend the selected roster from '
                                                       'observations.'},
 'operator_application_count': 0,
 'plan_schema_implemented': False,
 'previous_merged_pr': 3059,
 'profile': 'linux_x86_64_original_bwrap_minimal_entry_exec_stop_v0',
 'proposed_budgets_not_observed_measurements': {'aggregate_control_memory_bytes_per_checkpoint': 1048576,
                                                'argument_bytes': 4096,
                                                'attempts': 1,
                                                'capture_members': 2048,
                                                'capture_payload_bytes': 33554432,
                                                'cleanup_wall_seconds': 5,
                                                'event_stream_storage': 'Bounded sequential '
                                                                        'streams, not one '
                                                                        'filesystem member per '
                                                                        'event.',
                                                'max_bwrap_birth_events': 2,
                                                'max_live_subject_tasks': 3,
                                                'max_ordered_trace_events': 8192,
                                                'on_exceeded': 'Preserve incomplete attempt and '
                                                               'primary failure, perform bounded '
                                                               'owned cleanup; no automatic budget '
                                                               'increase.',
                                                'retries': 0,
                                                'setup_wall_seconds': 30,
                                                'single_control_memory_read_bytes': 65536,
                                                'stderr_bytes': 4096,
                                                'stdout_bytes': 65536},
 'readiness_gates': [{'id': 'new_plan_schema_and_independent_checker', 'satisfied': False},
                     {'id': 'fresh_original_and_explicit_policy_admission', 'satisfied': False},
                     {'id': 'reviewed_startup_helper_and_multitask_guard', 'satisfied': False},
                     {'id': 'source_to_executed_helper_binding', 'satisfied': False},
                     {'id': 'new_capture_schema_collector_and_independent_checker',
                      'satisfied': False},
                     {'id': 'same_host_namespace_ptrace_proc_openat2_qualification',
                      'satisfied': False},
                     {'id': 'tested_owned_graph_cleanup', 'satisfied': False},
                     {'id': 'reviewed_exact_host_environment', 'satisfied': False},
                     {'id': 'separate_owner_execution_authorization', 'satisfied': False}],
 'record_status': 'authored_design_proposal',
 'record_type': 'required_gate_idempotence_containment_entry_plan_v0',
 'selected_bootstrap_follow_on': {'capsule_preparation_required_for_minimal_entry_checkpoint': False,
                                  'current_example_capsule_accepted_as_real': False,
                                  'current_v0_python_version': '3.11.16',
                                  'current_v0_unicode_version': '14.0.0',
                                  'diagnostic_is_property_application': False,
                                  'existing_selected_execution_guards_unchanged': True,
                                  'new_real_capsule_required': True,
                                  'stages': ['new real runtime/operator selections and recoverable '
                                             'capsule',
                                             'separately reviewed selected-loader exec-stop after '
                                             'shim execution',
                                             'separate finite worker bootstrap diagnostic',
                                             'separate finite collector bootstrap diagnostic',
                                             'separate real worker FD/task/exec/input-consumption '
                                             'integration'],
                                  'v0_constraints_change_requires_new_version_or_distinct_profile': True,
                                  'v0_limits_must_be_measured_on_real_inventory': True},
 'selected_runtime_admitted': False,
 'task_graph': {'bwrap_birth_count': 2,
                'creation_contracts': [{'child': 'R',
                                        'child_stack': 0,
                                        'parent': 'L',
                                        'source': 'bubblewrap raw_clone; '
                                                  'NEWNS|NEWUSER|NEWPID|NEWNET|NEWIPC|NEWUTS|NEWCGROUP|SIGCHLD',
                                        'syscall_number': 56,
                                        'trailing_ignored_arguments_must_not_be_required_zero': True},
                                       {'child': 'T',
                                        'child_stack': 0,
                                        'child_tid_pointer': 'dynamic selected glibc TLS address; '
                                                             'bind before syscall; do not prefill',
                                        'parent': 'R',
                                        'source': 'glibc fork -> _Fork -> arch_fork; '
                                                  'CHILD_SETTID|CHILD_CLEARTID|SIGCHLD',
                                        'syscall_number': 56}],
                'deny_creation': ['fork',
                                  'vfork',
                                  'clone3',
                                  'other clone masks',
                                  'x32 ABI',
                                  'io_uring task bypasses'],
                'dynamic_identity_fields': ['pid',
                                            'tid',
                                            'starttime',
                                            'pidfd',
                                            'namespace handles/inodes',
                                            'child-TID address'],
                'expected_ptrace_birth_event': 'PTRACE_EVENT_FORK for SIGCHLD clone calls; '
                                               'selected-host qualification required',
                'guard_and_preexecution_role_validation_required': True,
                'observer_excluded': True,
                'subject_roles': [{'meaning': 'Trusted preexec helper becomes original launcher '
                                              'monitor in the same task.',
                                   'parent': 'observer',
                                   'role': 'L'},
                                  {'meaning': 'Namespace setup task becomes namespace PID 1 and '
                                              'reaper.',
                                   'parent': 'L',
                                   'role': 'R'},
                                  {'meaning': 'Payload task execs exact static entry and remains '
                                              'stopped.',
                                   'parent': 'R',
                                   'role': 'T'}],
                'subject_task_count': 3},
 'this_unit_files': ['CHANGELOG.md',
                     'docs/INDEX.md',
                     'docs/compute/PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_LOADER_RESOLUTION_HOSTED_v0.md',
                     'docs/compute/PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_CONTAINMENT_ENTRY_PLAN_v0.md',
                     'docs/compute/required_gate_idempotence_containment_entry_plan_v0/plan_v0.json',
                     'docs/compute/required_gate_idempotence_containment_entry_plan_v0/source_bindings_v0.json',
                     'preservation/required_gate_idempotence_containment_entry_plan_v0/raw/bubblewrap_0.12.0-1~deb13u1.debian.tar.xz',
                     'preservation/required_gate_idempotence_containment_entry_plan_v0/raw/bubblewrap_0.12.0-1~deb13u1.dsc',
                     'preservation/required_gate_idempotence_containment_entry_plan_v0/raw/bubblewrap_0.12.0.orig.tar.xz'],
 'whole_runtime_issue': {'keep_open': True, 'number': 2879}}

LAUNCH_POLICY = {'argument_change_requires_new_reviewed_selection': True,
 'arguments_encoding': 'ASCII tokens, each terminated by exactly one NUL',
 'argv': ['bubblewrap', '--args', '3'],
 'cwd': '/',
 'environment': {'LC_ALL': 'C', 'TZ': 'UTC'},
 'fd_integer_reuse_is_not_identity_continuity': True,
 'initial_helper_FD_roles': {'0': 'independent empty sealed stdin',
                             '1': 'bounded stdout write end',
                             '2': 'bounded stderr write end',
                             '3': 'sealed NUL-separated arguments; survives initial launcher exec',
                             '4': 'sealed static entry bytes; survives initial launcher exec',
                             '5': 'sealed selected containment BPF; survives initial launcher exec',
                             '6': 'sealed original launcher ELF; CLOEXEC; initial execveat '
                                  'AT_EMPTY_PATH target',
                             '7': 'owned helper barrier; CLOEXEC; no input-controlled commands'},
 'mount_requirement': 'Private read-only root tmpfs and read-only bind of copied entry; exact '
                      'per-mount VFS flags and pinned root walk.',
 'terminal_T_fd_numbers': [0, 1, 2]}


# Scratch integration fragment: definitions only; does not read or execute files.
# Required globals: PlanError, _need, hashlib, io, lzma, re, stat, struct, zlib.
# Error codes intentionally identify parser failures without including input data.


def _archive_limits(count_limit, decoded_limit, member_limit):
    _need(all(type(value) is int and value > 0
              for value in (count_limit, decoded_limit, member_limit)),
          "containment_entry_plan_archive_limits")


def _archive_path(value, *, directory=False, allow_dot_prefix=False):
    _need(type(value) is str and 0 < len(value) <= 512
          and all(32 <= ord(char) < 127 for char in value)
          and "\\" not in value and ":" not in value,
          "containment_entry_plan_archive_path")
    if allow_dot_prefix and value.startswith("./"):
        value = value[2:]
    if directory and value.endswith("/"):
        value = value[:-1]
    _need(value and not value.startswith("/")
          and all(part not in {"", ".", ".."}
                  and re.fullmatch(r"[A-Za-z0-9_.+@#=,%~-]+", part)
                  for part in value.split("/")),
          "containment_entry_plan_archive_path")
    return value


def _xz_chunks(raw, limit):
    _need(type(raw) is bytes and type(limit) is int and limit > 0,
          "containment_entry_plan_xz_input")
    _need(raw.startswith(b"\xfd7zXZ\x00"), "containment_entry_plan_xz_format")
    try:
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ,
                                       memlimit=64 * 1024 * 1024)
        position = total = 0
        while not decoder.eof:
            if decoder.needs_input:
                _need(position < len(raw), "containment_entry_plan_xz_truncated")
                chunk = raw[position:position + 65536]
                position += len(chunk)
            else:
                chunk = b""
            decoded = decoder.decompress(chunk, max_length=65536)
            total += len(decoded)
            _need(total <= limit, "containment_entry_plan_xz_decoded_limit")
            if decoded:
                yield decoded
        _need(not decoder.unused_data and position == len(raw),
              "containment_entry_plan_xz_trailing_data")
    except lzma.LZMAError as exc:
        raise PlanError("containment_entry_plan_xz_invalid") from exc


def _xz_decode(raw, limit):
    """Decode one complete XZ stream, bounded in memory, output and chunks."""
    return b"".join(_xz_chunks(raw, limit))


def _zip_payload(raw, method, expected_size, expected_crc):
    """Bounded ZIP payload decode with exact DEFLATE termination and CRC."""
    if method == 0:
        _need(len(raw) == expected_size, "containment_entry_plan_zip_stored_size")
        _need(zlib.crc32(raw) & 0xffffffff == expected_crc,
              "containment_entry_plan_zip_crc")
        return raw
    _need(method == 8, "containment_entry_plan_zip_method")
    decoder = zlib.decompressobj(-15)
    parts, total, crc, position, pending = [], 0, 0, 0, b""
    try:
        while not decoder.eof:
            if pending:
                chunk, pending = pending, b""
            elif position < len(raw):
                chunk = raw[position:position + 65536]
                position += len(chunk)
            else:
                chunk = b""
            decoded = decoder.decompress(chunk, 65536)
            pending = decoder.unconsumed_tail
            total += len(decoded)
            _need(total <= expected_size, "containment_entry_plan_zip_member_decoded_limit")
            if decoded:
                parts.append(decoded)
                crc = zlib.crc32(decoded, crc)
            _need(decoder.eof or decoded or pending or position < len(raw),
                  "containment_entry_plan_zip_deflate_truncated")
        _need(not decoder.unused_data and not pending and position == len(raw),
              "containment_entry_plan_zip_deflate_trailing_data")
    except zlib.error as exc:
        raise PlanError("containment_entry_plan_zip_deflate_invalid") from exc
    _need(total == expected_size, "containment_entry_plan_zip_member_size")
    _need(crc & 0xffffffff == expected_crc, "containment_entry_plan_zip_crc")
    return b"".join(parts)


def _zip_members(raw, *, count_limit, decoded_limit, member_limit):
    """Closed ordinary ZIP: exact headers, records, payloads and end marker.

    Accepts stored/deflated regular members and bounded signed or unsigned data
    descriptors. Rejects ZIP64, extras/comments, prefixes/trailers, directories,
    links, duplicate/colliding names, hidden local members and overlapping data.
    """
    _archive_limits(count_limit, decoded_limit, member_limit)
    _need(type(raw) is bytes and len(raw) >= 22, "containment_entry_plan_zip_input")
    end = len(raw) - 22
    (signature, disk, central_disk, disk_count, count, central_size,
     central_offset, comment_size) = struct.unpack_from("<4s4H2IH", raw, end)
    _need(signature == b"PK\x05\x06" and disk == central_disk == 0
          and disk_count == count and count != 0xffff and count <= count_limit
          and central_size != 0xffffffff and central_offset != 0xffffffff
          and comment_size == 0 and central_offset + central_size == end,
          "containment_entry_plan_zip_end")
    position = central_offset
    records, names, offsets, decoded_total = [], set(), set(), 0
    for _ in range(count):
        _need(position + 46 <= end, "containment_entry_plan_zip_central_truncated")
        fields = struct.unpack_from("<4s6H3I5H2I", raw, position)
        (signature, made_by, needed, flags, method, mtime, mdate, crc,
         compressed, size, name_size, extra_size, file_comment_size,
         start_disk, internal, external, local_offset) = fields
        _need(signature == b"PK\x01\x02" and made_by >> 8 in {0, 3}
              and needed <= 20 and flags & ~0x0808 == 0 and method in {0, 8}
              and 0 < name_size <= 512 and extra_size == file_comment_size == 0
              and start_disk == 0 and compressed != 0xffffffff
              and size != 0xffffffff and local_offset != 0xffffffff,
              "containment_entry_plan_zip_central")
        _need(position + 46 + name_size <= end,
              "containment_entry_plan_zip_central_truncated")
        name_raw = raw[position + 46:position + 46 + name_size]
        try:
            name = name_raw.decode("utf-8" if flags & 0x800 else "ascii", "strict")
        except UnicodeError as exc:
            raise PlanError("containment_entry_plan_zip_name_encoding") from exc
        name = _archive_path(name)
        mode = external >> 16
        _need(stat.S_IFMT(mode) in {0, stat.S_IFREG} and external & 0x10 == 0,
              "containment_entry_plan_zip_member_type")
        _need(name not in names and local_offset not in offsets,
              "containment_entry_plan_zip_duplicate")
        _need(size <= member_limit and decoded_total + size <= decoded_limit,
              "containment_entry_plan_zip_size_limit")
        names.add(name)
        offsets.add(local_offset)
        decoded_total += size
        records.append((local_offset, name, name_raw, needed, flags, method,
                        mtime, mdate, crc, compressed, size))
        position += 46 + name_size
    _need(position == end, "containment_entry_plan_zip_central_extent")
    for name in names:
        pieces = name.split("/")
        _need(all("/".join(pieces[:index]) not in names
                  for index in range(1, len(pieces))),
              "containment_entry_plan_zip_ancestor_alias")
    result, position = {}, 0
    for record in sorted(records):
        (offset, name, name_raw, needed, flags, method,
         mtime, mdate, crc, compressed, size) = record
        _need(offset == position and offset + 30 <= central_offset,
              "containment_entry_plan_zip_local_extent")
        local = struct.unpack_from("<4s5H3I2H", raw, offset)
        (signature, local_needed, local_flags, local_method, local_time,
         local_date, local_crc, local_compressed, local_size,
         local_name_size, local_extra_size) = local
        _need(signature == b"PK\x03\x04"
              and (local_needed, local_flags, local_method, local_time, local_date)
              == (needed, flags, method, mtime, mdate)
              and local_name_size == len(name_raw) and local_extra_size == 0,
              "containment_entry_plan_zip_local")
        position = offset + 30
        _need(raw[position:position + local_name_size] == name_raw,
              "containment_entry_plan_zip_name_mismatch")
        position += local_name_size
        if flags & 8:
            _need(local_crc in {0, crc} and local_compressed in {0, compressed}
                  and local_size in {0, size},
                  "containment_entry_plan_zip_local_descriptor_values")
        else:
            _need((local_crc, local_compressed, local_size) == (crc, compressed, size),
                  "containment_entry_plan_zip_local_values")
        payload_end = position + compressed
        _need(payload_end <= central_offset, "containment_entry_plan_zip_payload_extent")
        result[name] = _zip_payload(raw[position:payload_end], method, size, crc)
        position = payload_end
        if flags & 8:
            if raw[position:position + 4] == b"PK\x07\x08":
                position += 4
            _need(position + 12 <= central_offset,
                  "containment_entry_plan_zip_descriptor_truncated")
            _need(struct.unpack_from("<3I", raw, position) == (crc, compressed, size),
                  "containment_entry_plan_zip_descriptor")
            position += 12
    _need(position == central_offset, "containment_entry_plan_zip_unlisted_data")
    return result


def _tar_number(raw):
    _need(type(raw) is bytes and bool(raw), "containment_entry_plan_tar_number")
    if raw[0] & 0x80:
        _need(not raw[0] & 0x40, "containment_entry_plan_tar_negative_number")
        return int.from_bytes(bytes([raw[0] & 0x7f]) + raw[1:], "big")
    value = raw.strip(b" \x00")
    _need(len(value) <= 24 and all(char in b"01234567" for char in value),
          "containment_entry_plan_tar_number")
    return int(value, 8) if value else 0


def _tar_text(raw):
    value, nul, padding = raw.partition(b"\x00")
    _need((not nul or not any(padding))
          and all(32 <= char < 127 for char in value),
          "containment_entry_plan_tar_text")
    return value.decode("ascii")


def _pax_fields(raw):
    """Restricted POSIX PAX records; no sparse files or vendor semantics."""
    _need(0 < len(raw) <= 65536, "containment_entry_plan_tar_pax_limit")
    position, result = 0, {}
    permitted = {"path", "linkpath", "size", "mtime", "atime", "ctime",
                 "uid", "gid", "uname", "gname", "hdrcharset", "comment"}
    while position < len(raw):
        space = raw.find(b" ", position, min(len(raw), position + 12))
        _need(space > position, "containment_entry_plan_tar_pax_length")
        digits = raw[position:space]
        _need(digits.isdigit() and not digits.startswith(b"0"),
              "containment_entry_plan_tar_pax_length")
        length = int(digits)
        stop = position + length
        _need(length > space - position + 3 and stop <= len(raw)
              and raw[stop - 1:stop] == b"\n",
              "containment_entry_plan_tar_pax_length")
        pair = raw[space + 1:stop - 1]
        key_raw, equals, value_raw = pair.partition(b"=")
        _need(equals and b"\x00" not in value_raw and b"\n" not in value_raw,
              "containment_entry_plan_tar_pax_value")
        try:
            key, value = key_raw.decode("ascii"), value_raw.decode("utf-8")
        except UnicodeError as exc:
            raise PlanError("containment_entry_plan_tar_pax_encoding") from exc
        _need(key in permitted and key not in result and len(result) < 16,
              "containment_entry_plan_tar_pax_key")
        if key in {"path", "linkpath"}:
            _need(0 < len(value) <= 512, "containment_entry_plan_tar_pax_path_limit")
        elif key in {"size", "uid", "gid"}:
            _need(re.fullmatch(r"0|[1-9][0-9]{0,19}", value) is not None,
                  "containment_entry_plan_tar_pax_number")
        elif key in {"mtime", "atime", "ctime"}:
            _need(len(value) <= 64
                  and re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?", value) is not None,
                  "containment_entry_plan_tar_pax_time")
        elif key == "hdrcharset":
            _need(value == "UTF-8", "containment_entry_plan_tar_pax_charset")
        else:
            _need(len(value) <= 512 and all(32 <= ord(c) < 127 for c in value),
                  "containment_entry_plan_tar_pax_text")
        result[key] = value
        position = stop
    return result


def _tar_members(raw, *, count_limit, decoded_limit, member_limit, selected=None):
    """Read raw TAR or one XZ TAR without extracting, following, or importing.

    Retained regular entries map to bytes. Directories map to
    {'kind':'directory'}; safe links to {'kind':..., 'target':literal_target}.
    With a selected set, other regular members are streamed into size/SHA
    metadata. The selected-member cap does not reject larger unselected source
    files; those have an independent 8 MiB cap. Every decoded byte is consumed.
    """
    _archive_limits(count_limit, decoded_limit, member_limit)
    _need(type(raw) is bytes and bool(raw), "containment_entry_plan_tar_input")
    if selected is not None:
        _need(type(selected) in {set, frozenset, list, tuple}
              and len(selected) <= count_limit
              and all(type(name) is str for name in selected),
              "containment_entry_plan_tar_selection")
        original_selection = list(selected)
        selected = {_archive_path(name) for name in original_selection}
        _need(len(selected) == len(original_selection),
              "containment_entry_plan_tar_selection_duplicate")
    if raw.startswith(b"\xfd7zXZ\x00"):
        chunks = iter(_xz_chunks(raw, decoded_limit))
    else:
        _need(len(raw) <= decoded_limit, "containment_entry_plan_tar_decoded_limit")
        chunks = (raw[index:index + 65536] for index in range(0, len(raw), 65536))
    buffer = bytearray()
    consumed = 0
    exhausted = False

    def read(count, *, exact=True):
        nonlocal consumed, exhausted
        _need(0 <= count <= 65536, "containment_entry_plan_tar_read_limit")
        while len(buffer) < count and not exhausted:
            try:
                buffer.extend(next(chunks))
            except StopIteration:
                exhausted = True
        if exact:
            _need(len(buffer) >= count, "containment_entry_plan_tar_truncated")
        result = bytes(buffer[:count])
        del buffer[:count]
        consumed += len(result)
        return result

    result, entry_kinds = {}, {}
    global_pax, pending_pax = {}, None
    pending_long_name = pending_long_link = None
    header_count = extension_count = 0
    while True:
        header = read(512)
        if not any(header):
            _need(not any(read(512)), "containment_entry_plan_tar_terminator")
            _need(pending_pax is None and pending_long_name is None
                  and pending_long_link is None,
                  "containment_entry_plan_tar_orphan_extension")
            while True:
                tail = read(65536, exact=False)
                if not tail:
                    break
                _need(not any(tail), "containment_entry_plan_tar_trailing_data")
            _need(consumed % 512 == 0, "containment_entry_plan_tar_alignment")
            break
        header_count += 1
        _need(header_count <= count_limit * 4 + 16,
              "containment_entry_plan_tar_header_limit")
        _need(_tar_number(header[148:156])
              == sum(header[:148]) + 8 * 32 + sum(header[156:]),
              "containment_entry_plan_tar_checksum")
        magic = header[257:265]
        if magic == b"ustar\x0000":
            prefix = _tar_text(header[345:500])
            _need(not any(header[500:]), "containment_entry_plan_tar_header_padding")
        elif magic == b"ustar  \x00":
            prefix = ""
            _need(not any(header[345:]), "containment_entry_plan_tar_gnu_extension")
        else:
            _need(not any(header[257:]), "containment_entry_plan_tar_format")
            prefix = ""
        name = _tar_text(header[:100])
        if prefix:
            name = prefix + "/" + name
        link = _tar_text(header[157:257])
        size = _tar_number(header[124:136])
        mode = _tar_number(header[100:108])
        _need(mode <= 0o7777, "containment_entry_plan_tar_mode")
        for field in (header[108:116], header[116:124], header[136:148]):
            _need(_tar_number(field) <= 0xffffffffffffffff,
                  "containment_entry_plan_tar_header_number_limit")
        if magic in {b"ustar\x0000", b"ustar  \x00"}:
            _tar_text(header[265:297])
            _tar_text(header[297:329])
            _need(_tar_number(header[329:337]) == _tar_number(header[337:345]) == 0,
                  "containment_entry_plan_tar_device_numbers")
        kind = header[156:157]
        if kind in {b"x", b"g", b"L", b"K"}:
            extension_count += 1
            _need(extension_count <= count_limit * 3 + 8 and not link
                  and 0 < size <= 65536,
                  "containment_entry_plan_tar_extension_limit")
            if name not in {"././@PaxHeader", "././@LongLink"}:
                _archive_path(name, allow_dot_prefix=True)
            extension = read(size)
            _need(not any(read((-size) % 512)),
                  "containment_entry_plan_tar_padding")
            if kind in {b"x", b"g"}:
                fields = _pax_fields(extension)
                if kind == b"g":
                    _need(not global_pax and not entry_kinds and pending_pax is None
                          and pending_long_name is None and pending_long_link is None
                          and not {"path", "linkpath", "size"}.intersection(fields),
                          "containment_entry_plan_tar_global_pax")
                    global_pax = fields
                else:
                    _need(pending_pax is None, "containment_entry_plan_tar_duplicate_pax")
                    pending_pax = fields
            else:
                _need(extension.endswith(b"\x00")
                      and b"\x00" not in extension[:-1],
                      "containment_entry_plan_tar_long_name")
                value = _tar_text(extension)
                if kind == b"L":
                    _need(pending_long_name is None,
                          "containment_entry_plan_tar_duplicate_long_name")
                    pending_long_name = value
                else:
                    _need(pending_long_link is None,
                          "containment_entry_plan_tar_duplicate_long_link")
                    pending_long_link = value
            continue
        _need(kind in {b"\x00", b"0", b"1", b"2", b"5"},
              "containment_entry_plan_tar_member_type")
        _need(len(entry_kinds) < count_limit, "containment_entry_plan_tar_member_limit")
        # Extended names may lengthen a canonical header name, never hide a
        # traversal or absolute path in the underlying ordinary header.
        _archive_path(name, directory=kind == b"5", allow_dot_prefix=True)
        if link:
            _archive_path(link, allow_dot_prefix=True)
        pax = dict(global_pax)
        if pending_pax is not None:
            pax.update(pending_pax)
        _need(not (pending_long_name is not None and "path" in pax)
              and not (pending_long_link is not None and "linkpath" in pax),
              "containment_entry_plan_tar_conflicting_extensions")
        if pending_long_name is not None:
            name = pending_long_name
        if pending_long_link is not None:
            link = pending_long_link
        name = pax.get("path", name)
        link = pax.get("linkpath", link)
        if "size" in pax:
            size = int(pax["size"])
        pending_pax = pending_long_name = pending_long_link = None
        regular = kind in {b"\x00", b"0"}
        directory = kind == b"5"
        path = _archive_path(name, directory=directory, allow_dot_prefix=True)
        _need(path not in entry_kinds, "containment_entry_plan_tar_duplicate_path")
        _need(regular or size == 0, "containment_entry_plan_tar_nonregular_payload")
        _need(bool(link) if kind in {b"1", b"2"} else not link,
              "containment_entry_plan_tar_link")
        if kind in {b"1", b"2"}:
            _archive_path(link, allow_dot_prefix=True)
        retain = regular and (selected is None or path in selected)
        _need(selected is None or path not in selected or regular,
              "containment_entry_plan_tar_selected_nonregular")
        _need(size <= (member_limit if retain else 8 * 1024 * 1024),
              "containment_entry_plan_tar_member_payload_limit")
        _need(size <= decoded_limit - consumed,
              "containment_entry_plan_tar_declared_size_limit")
        parts, digest, remaining = [], hashlib.sha256(), size
        while remaining:
            chunk = read(min(remaining, 65536))
            digest.update(chunk)
            if retain:
                parts.append(chunk)
            remaining -= len(chunk)
        _need(not any(read((-size) % 512)), "containment_entry_plan_tar_padding")
        entry_kinds[path] = "regular_file" if regular else (
            "directory" if directory else "hardlink" if kind == b"1" else "symlink")
        if retain:
            result[path] = b"".join(parts)
        elif regular:
            result[path] = {"kind": "regular_file", "size_bytes": size,
                            "sha256": digest.hexdigest()}
        elif directory:
            result[path] = {"kind": "directory"}
        else:
            result[path] = {"kind": entry_kinds[path], "target": link}
    for path in entry_kinds:
        pieces = path.split("/")
        _need(all("/".join(pieces[:index]) not in entry_kinds
                  or entry_kinds["/".join(pieces[:index])] == "directory"
                  for index in range(1, len(pieces))),
              "containment_entry_plan_tar_ancestor_alias")
    _need(selected is None or selected.issubset(result),
          "containment_entry_plan_tar_selected_missing")
    return result


"""Data-only review of pinned source members; no native execution or build claim.

This fragment expects _need, PlanError, binding and re in the containing checker.
TAR readers must already have admitted carrier identities, canonical member paths,
member kinds, sizes and bytes. Regular member map values are bytes. Other values
are metadata and must never be treated as source text.
"""


def _sc_text(members, name):
    raw = members.get(name)
    _need(type(raw) is bytes and 0 < len(raw) <= 8 * 1024 * 1024,
          "containment_entry_plan_source_member")
    _need(b"\0" not in raw, "containment_entry_plan_source_nul")
    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PlanError("containment_entry_plan_source_encoding") from exc


def _sc_c_tokens(text):
    """Tokenize the reviewed C subset after line splicing and comment removal.

    Strings and character constants remain single quoted tokens, so an apparent
    call or flag name in a comment or diagnostic cannot satisfy a code check.
    This is not a preprocessor or proof of general C semantics. The carrier pins
    and the selected-function contracts constrain the input to reviewed source.
    """
    _need(type(text) is str and len(text) <= 8 * 1024 * 1024,
          "containment_entry_plan_source_lexer_bound")
    text = re.sub(r"\\\r?\n", "", text)
    token_re = re.compile(
        r"\s+|/\*[\s\S]*?\*/|//[^\r\n]*"
        r'|"(?:\\[^\r\n]|[^"\\\r\n])*"'
        r"|'(?:\\[^\r\n]|[^'\\\r\n])*'"
        r"|[A-Za-z_][A-Za-z_0-9]*"
        r"|0[xX][0-9A-Fa-f]+[uUlL]*|[0-9]+[uUlL]*"
        r"|>>=|<<=|\.\.\.|->|\+\+|--|==|!=|<=|>=|&&|\|\||<<|>>"
        r"|\+=|-=|\*=|/=|%=|&=|\^=|\|=|##"
        r"|[{}()\[\];,:.?~!%^&*+=|/<>\-#\\]"
    )
    tokens, cursor = [], 0
    while cursor < len(text):
        found = token_re.match(text, cursor)
        _need(found is not None, "containment_entry_plan_source_lexer")
        value = found.group(0)
        # A missing block-comment terminator must not degrade into '/' and '*'.
        _need(not (text.startswith("/*", cursor) and not value.startswith("/*")),
              "containment_entry_plan_source_comment")
        if not value.isspace() and not value.startswith(("/*", "//")):
            tokens.append(value)
        cursor = found.end()
    _need(len(tokens) <= 500000, "containment_entry_plan_source_token_bound")
    return tokens


def _sc_match_end(tokens, start, opening, closing):
    _need(start < len(tokens) and tokens[start] == opening,
          "containment_entry_plan_source_delimiter")
    depth = 0
    for pos in range(start, len(tokens)):
        if tokens[pos] == opening:
            depth += 1
        elif tokens[pos] == closing:
            depth -= 1
            if depth == 0:
                return pos
    raise PlanError("containment_entry_plan_source_unbalanced")


def _sc_function(tokens, name):
    """Find one top-level C definition, excluding declarations and calls."""
    found, depth = [], 0
    for pos, value in enumerate(tokens):
        if value == "{":
            depth += 1
        elif value == "}":
            depth -= 1
            _need(depth >= 0, "containment_entry_plan_source_unbalanced")
        elif depth == 0 and value == name and tokens[pos + 1:pos + 2] == ["("]:
            end = _sc_match_end(tokens, pos + 1, "(", ")")
            if tokens[end + 1:end + 2] == ["{"]:
                close = _sc_match_end(tokens, end + 1, "{", "}")
                found.append(tokens[end + 2:close])
    _need(depth == 0 and len(found) == 1,
          "containment_entry_plan_source_function_" + name)
    return found[0]


def _sc_positions(tokens, fragment):
    wanted = _sc_c_tokens(fragment) if type(fragment) is str else fragment
    _need(bool(wanted), "containment_entry_plan_source_empty_contract")
    return [i for i in range(len(tokens) - len(wanted) + 1)
            if tokens[i:i + len(wanted)] == wanted]


def _sc_once(tokens, fragment):
    found = _sc_positions(tokens, fragment)
    _need(len(found) == 1, "containment_entry_plan_source_unique_contract")
    return found[0]


def _sc_order(tokens, fragments):
    cursor = 0
    for fragment in fragments:
        wanted = _sc_c_tokens(fragment) if type(fragment) is str else fragment
        found = [i for i in _sc_positions(tokens, wanted) if i >= cursor]
        _need(bool(found), "containment_entry_plan_source_ordered_contract")
        cursor = found[0] + len(wanted)


def _sc_block(tokens, prefix):
    wanted = _sc_c_tokens(prefix)
    start = _sc_once(tokens, wanted + ["{"]) + len(wanted)
    _need(tokens[start:start + 1] == ["{"],
          "containment_entry_plan_source_expected_block")
    end = _sc_match_end(tokens, start, "{", "}")
    return tokens[start + 1:end]


def _sc_member_bindings(members, names):
    rows = []
    for name in names:
        _sc_text(members, name)
        rows.append({"member": name, **binding(members[name])})
    return rows


def _sc_patch_path(header):
    # Quilt's reviewed series use the ordinary -p1 convention. Timestamp text
    # following a TAB/space is not part of a patch path; quoted paths are absent.
    pieces = header.split()
    _need(bool(pieces), "containment_entry_plan_source_patch_path")
    raw = pieces[0]
    if raw == "/dev/null":
        return None
    _need(re.fullmatch(r"[A-Za-z0-9_.+@~-]+(?:/[A-Za-z0-9_.+@~-]+)+", raw)
          is not None and all(p not in (".", "..") for p in raw.split("/")),
          "containment_entry_plan_source_patch_path")
    return raw.split("/", 1)[1]


def _sc_patch_sections(text):
    """Read unified headers and hunk counts without applying the patch.

    Hunk accounting prevents deleted lines beginning '---' from being mistaken
    for new file headers. Both old and new paths count as touched paths.
    """
    lines, sections, current, pos = text.split("\n"), [], None, 0
    _need(len(lines) <= 200000, "containment_entry_plan_source_patch_bound")
    while pos < len(lines):
        line = lines[pos]
        if line.startswith("--- "):
            _need(pos + 1 < len(lines) and lines[pos + 1].startswith("+++ "),
                  "containment_entry_plan_source_patch_header")
            current = {"old_path": _sc_patch_path(line[4:]),
                       "new_path": _sc_patch_path(lines[pos + 1][4:]),
                       "hunks": []}
            _need(current["old_path"] is not None or current["new_path"] is not None,
                  "containment_entry_plan_source_patch_null_pair")
            sections.append(current)
            pos += 2
            continue
        if line.startswith("@@"):
            match = re.fullmatch(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?:.*)", line)
            _need(current is not None and match is not None,
                  "containment_entry_plan_source_patch_hunk")
            old_start, new_start = int(match[1]), int(match[3])
            old_count = int(match[2]) if match[2] is not None else 1
            new_count = int(match[4]) if match[4] is not None else 1
            _need(max(old_start, new_start, old_count, new_count) <= 10000000,
                  "containment_entry_plan_source_patch_hunk_bound")
            before, after, removed, added = [], [], [], []
            old_left, new_left = old_count, new_count
            pos += 1
            while old_left or new_left:
                _need(pos < len(lines), "containment_entry_plan_source_patch_truncated")
                item = lines[pos]
                if item == "\\ No newline at end of file":
                    pos += 1
                    continue
                # Preserved Debian diffs also use an empty physical line for
                # an empty context line; GNU patch accepts this representation.
                if item == "":
                    item = " "
                _need(item[0] in " +-",
                      "containment_entry_plan_source_patch_line")
                marker, body = item[0], item[1:]
                if marker in " -":
                    before.append(body)
                    old_left -= 1
                if marker in " +":
                    after.append(body)
                    new_left -= 1
                if marker == "-":
                    removed.append(body)
                elif marker == "+":
                    added.append(body)
                _need(old_left >= 0 and new_left >= 0,
                      "containment_entry_plan_source_patch_counts")
                pos += 1
            current["hunks"].append({"old_start": old_start, "new_start": new_start,
                                     "before": before, "after": after,
                                     "removed": removed, "added": added})
            continue
        _need(not line.startswith(("GIT binary patch", "Binary files ", "+++ ")),
              "containment_entry_plan_source_patch_unsupported")
        pos += 1
    _need(bool(sections) and all(s["hunks"] for s in sections),
          "containment_entry_plan_source_patch_empty")
    return sections


def _sc_quilt(members):
    series = []
    for line in _sc_text(members, "debian/patches/series").splitlines():
        line = line.partition("#")[0].strip()
        if not line:
            continue
        _need(re.fullmatch(r"[A-Za-z0-9_.+@~-]+(?:/[A-Za-z0-9_.+@~-]+)*", line)
              is not None and all(p not in (".", "..") for p in line.split("/")),
              "containment_entry_plan_source_quilt_series")
        _need(line not in series, "containment_entry_plan_source_quilt_duplicate")
        series.append(line)
    _need(0 < len(series) <= 1024, "containment_entry_plan_source_quilt_bound")
    # Inspect all preserved patch paths, including patches not active for the
    # selected build. A carrier can contain architecture-specific extra series.
    patch_names = sorted(name for name in members
                         if name.startswith("debian/patches/")
                         and name.endswith((".patch", ".diff")))
    _need(0 < len(patch_names) <= 2048, "containment_entry_plan_source_patch_roster")
    patches = {name: _sc_patch_sections(_sc_text(members, name)) for name in patch_names}
    _need(all("debian/patches/" + name in patches for name in series),
          "containment_entry_plan_source_quilt_missing")
    return series, patches


def _sc_check_hunk_context(original, section):
    lines = original.split("\n")
    for hunk in section["hunks"]:
        start = hunk["old_start"] - 1
        _need(start >= 0 and lines[start:start + len(hunk["before"])] == hunk["before"],
              "containment_entry_plan_source_patch_context")


def _sc_source_build(bwrap_orig, bwrap_debian, safe_tokens):
    rules = _sc_text(bwrap_debian, "debian/rules")
    # Ignore Makefile comments and join recipe continuations before selecting the
    # actual configure target. A commented -D option cannot establish a setting.
    rules = "\n".join(line.partition("#")[0] for line in rules.splitlines())
    rules = re.sub(r"\\\n[ \t]*", " ", rules)
    maintain = re.findall(r"(?m)^export DEB_BUILD_MAINT_OPTIONS\s*=\s*(\S+)\s*$", rules)
    _need(maintain == ["hardening=+pie,+bindnow"],
          "containment_entry_plan_source_hardening")
    matches = re.findall(r"(?m)^override_dh_auto_configure:\s*\n((?:\t[^\n]*\n)+)", rules)
    _need(len(matches) == 1, "containment_entry_plan_source_configure_target")
    recipe = matches[0].split()
    _need(recipe[:2] == ["dh_auto_configure", "--"],
          "containment_entry_plan_source_configure_command")
    assumptions = [item.split("=", 1)[1] for item in recipe if item.startswith("-Dassume_kernel=")]
    _need(assumptions == ["5.10.0"], "containment_entry_plan_source_assume_kernel")
    source_format = _sc_text(bwrap_debian, "debian/source/format").strip()
    _need(source_format == "3.0 (quilt)", "containment_entry_plan_source_format")

    # Meson has no C-style comments; tokenize its non-comment statements only.
    meson = "\n".join(line.partition("#")[0]
                      for line in _sc_text(bwrap_orig, "bubblewrap-0.12.0/meson.build").splitlines())
    meson_tokens = _sc_c_tokens(meson)
    _sc_order(meson_tokens, [
        "assume_kernel = get_option('assume_kernel')", "if assume_kernel != ''",
        "kernel_parts = assume_kernel.split('.')", "if kernel_parts.length() != 3",
        "cdata.set('ASSUMED_KERNEL_MAJOR', kernel_parts[0].to_int())",
        "cdata.set('ASSUMED_KERNEL_MINOR', kernel_parts[1].to_int())",
        "cdata.set('ASSUMED_KERNEL_PATCH', kernel_parts[2].to_int())",
        "cdata.set('HAVE_ASSUMED_KERNEL', 1)",
    ])
    utils_h = _sc_c_tokens(_sc_text(bwrap_orig, "bubblewrap-0.12.0/utils.h"))
    _sc_order(utils_h, [
        "#define BWRAP_KERNEL_VERSION(a,b,c) (((a)<<16)+((b)<<8)+(c))",
        "#ifdef HAVE_ASSUMED_KERNEL",
        "#define ASSUMED_KERNEL BWRAP_KERNEL_VERSION(ASSUMED_KERNEL_MAJOR, ASSUMED_KERNEL_MINOR, ASSUMED_KERNEL_PATCH)",
        "#else", "#define ASSUMED_KERNEL 0", "#endif",
    ])
    _sc_once(safe_tokens, "#if ASSUMED_KERNEL < BWRAP_KERNEL_VERSION(5,6,0) #define USE_OPENAT_FALLBACK 1 #else #define USE_OPENAT_FALLBACK 0 #endif")
    fallback = _sc_function(safe_tokens, "safe_openat_fallback")
    _sc_once(fallback, "#if !USE_OPENAT_FALLBACK (void)dirfd; (void)rootfs; (void)path; (void)flags; (void)mode; errno=ENOSYS; return -1; #else")
    safe_open = _sc_function(safe_tokens, "safe_openat")
    _sc_order(safe_open, [
        "if (openat2_supported && !opt_force_openat_fallback)",
        "syscall_openat2(dirfd,path,flags,mode,RESOLVE_IN_ROOT|RESOLVE_NO_MAGICLINKS)",
        "if (errno == ENOSYS || errno == EINVAL || errno == EPERM) return safe_openat_fallback(dirfd,rootfs,path,flags,mode);",
        "return safe_openat_fallback(dirfd,rootfs,path,flags,mode);",
    ])
    version = re.match(r"bubblewrap \(([^)]+)\) ",
                       _sc_text(bwrap_debian, "debian/changelog"))
    _need(version is not None and version[1] == "0.12.0-1~deb13u1",
          "containment_entry_plan_source_bubblewrap_version")
    assumed = tuple(int(part) for part in assumptions[0].split("."))
    return {"version": version[1],
            "build_selection": {"assume_kernel": assumptions[0],
                                "hardening": maintain[0].split("=", 1)[1],
                                "source_format": source_format},
            "pre_5_6_openat_fallback_compiled_out_by_declared_build_selection": assumed >= (5, 6, 0),
            "required_openat2_resolution": ["RESOLVE_IN_ROOT", "RESOLVE_NO_MAGICLINKS"]}


def _source_contracts(bwrap_orig, bwrap_debian, glibc_orig, glibc_debian):
    """Reconstruct reviewed source relationships from independently pinned maps.

    No patch is applied, no C is compiled or executed, and no source/binary
    equivalence, host syscall observation or runtime qualification follows.
    """
    bwrap_names = ["bubblewrap-0.12.0/" + name for name in
                   ("bubblewrap.c", "utils.c", "safe_openat.c", "bwrap.xml", "meson.build", "COPYING")]
    glibc_relative = ["posix/fork.c", "sysdeps/nptl/_Fork.c", "sysdeps/unix/sysv/linux/arch-fork.h",
                      "sysdeps/unix/sysv/linux/kernel-features.h",
                      "sysdeps/unix/sysv/linux/x86_64/kernel-features.h",
                      "posix/wait.c", "posix/waitpid.c", "sysdeps/unix/sysv/linux/wait4.c"]
    glibc_names = ["glibc-2.41/" + name for name in glibc_relative]
    bwrap_text = _sc_text(bwrap_orig, bwrap_names[0])
    bwrap = _sc_c_tokens(bwrap_text)
    main = _sc_function(bwrap, "main")
    init = _sc_function(bwrap, "do_init")
    load_seccomp = _sc_function(bwrap, "seccomp_program_new")
    apply_seccomp = _sc_function(bwrap, "seccomp_programs_apply")
    raw_clone = _sc_function(_sc_c_tokens(_sc_text(bwrap_orig, bwrap_names[1])), "raw_clone")

    _sc_order(main, [
        "clone_flags = SIGCHLD | CLONE_NEWNS;",
        "if (opt_unshare_user) clone_flags |= CLONE_NEWUSER;",
        "if (opt_unshare_pid && opt_pidns_fd == -1) clone_flags |= CLONE_NEWPID;",
        "if (opt_unshare_net) clone_flags |= CLONE_NEWNET;",
        "if (opt_unshare_ipc) clone_flags |= CLONE_NEWIPC;",
        "if (opt_unshare_uts) clone_flags |= CLONE_NEWUTS;",
        "if (opt_unshare_cgroup)", "clone_flags |= CLONE_NEWCGROUP;",
        "if (opt_unshare_cgroup_try)", "clone_flags |= CLONE_NEWCGROUP;",
        "pid = raw_clone(clone_flags,NULL);",
    ])
    assignments = []
    for pos, token in enumerate(main):
        if token == "clone_flags" and main[pos + 1:pos + 2] in (["="], ["|="]):
            end = main.index(";", pos)
            assignments.append(main[pos + 1:end])
    flag_names = ["CLONE_NEWUSER", "CLONE_NEWPID", "CLONE_NEWNET", "CLONE_NEWIPC",
                  "CLONE_NEWUTS", "CLONE_NEWCGROUP"]
    _need(assignments == [["=", "SIGCHLD", "|", "CLONE_NEWNS"]]
          + [["|=", name] for name in flag_names] + [["|=", "CLONE_NEWCGROUP"]],
          "containment_entry_plan_source_clone_assignments")
    _sc_once(main, "raw_clone(")
    _sc_order(raw_clone, [
        "#if defined(__s390__) || defined(__CRIS__)",
        "return (int)syscall(__NR_clone,child_stack,flags);", "#else",
        "return (int)syscall(__NR_clone,flags,child_stack);", "#endif",
    ])
    _need(len(_sc_positions(raw_clone, "syscall(")) == 2,
          "containment_entry_plan_source_raw_clone_arity")

    _sc_order(load_seccomp, ["load_file_data(*fd,&len)", "close(*fd);", "*fd=-1;",
                             "if (len % 8 != 0)", "self->program.len=len/8;"])
    _sc_once(apply_seccomp, "prctl(PR_SET_SECCOMP,SECCOMP_MODE_FILTER,&program->program)")
    _sc_order(apply_seccomp, ["for (program=seccomp_programs; program!=NULL; program=program->next)",
                             "prctl(PR_SET_SECCOMP,SECCOMP_MODE_FILTER,&program->program)"])
    _sc_once(init, "seccomp_programs_apply()")
    _sc_order(init, ["handle_die_with_parent();", "seccomp_programs_apply();",
                     "child=TEMP_FAILURE_RETRY(wait(&status));"])
    fork_block = _sc_block(main, "if (!opt_as_pid_1 && (opt_unshare_pid || lock_files != NULL || opt_sync_fd != -1))")
    _sc_once(fork_block, "pid=fork();")
    parent_block = _sc_block(fork_block, "if (pid != 0)")
    _sc_order(parent_block, ["drop_all_caps(false);", "fdwalk(close_extra_fds,dont_close);",
                             "return do_init(event_fd,pid);"])
    _sc_once(main, "seccomp_programs_apply()")
    _sc_once(main, "fork()")
    _sc_order(main, ["seccomp_program_new(&opt_seccomp_fd);",
                     "new_cwd = \"/\";", "if (opt_chdir_path)",
                     "chdir(opt_chdir_path)", "new_cwd=opt_chdir_path;",
                     "xsetenv(\"PWD\",new_cwd,1);", "pid=fork();",
                     "return do_init(event_fd,pid);", "if (proc_fd != -1) close(proc_fd);",
                     "seccomp_programs_apply();", "execvp(exec_path,argv)"])

    parser = _sc_function(bwrap, "parse_args_recurse")
    ro_parse = _sc_block(parser, "if (strcmp(arg,\"--ro-bind-data\")==0)")
    _sc_order(ro_parse, ["file_fd=strtol(argv[1],&endptr,10);",
                         "op=setup_op_new(SETUP_MAKE_RO_BIND_FILE);",
                         "op->fd=file_fd;", "op->dest=argv[2];",
                         "if (next_perms>=0) op->perms=next_perms; else op->perms=0600;"])
    setup = _sc_function(bwrap, "setup_newroot")
    ro_copy = _sc_block(setup, "case SETUP_MAKE_BIND_FILE: case SETUP_MAKE_RO_BIND_FILE:")
    _sc_order(ro_copy, ["tmp_fd=mkstemp(tempfile);", "fchmod(tmp_fd,op->perms)",
                        "copy_file_data(op->fd,tmp_fd)", "close(op->fd);", "op->fd=-1;",
                        "setup_op_bind_mount_fd((op->type==SETUP_MAKE_RO_BIND_FILE?BIND_READONLY:0),tmp_fd,\"tmpfile\",dest_fd,op->dest);",
                        "unlink(tempfile);"])

    glibc = {name: _sc_c_tokens(_sc_text(glibc_orig, "glibc-2.41/" + name))
             for name in glibc_relative}
    libc_fork = _sc_function(glibc["posix/fork.c"], "__libc_fork")
    _sc_once(libc_fork, "pid_t pid=_Fork();")
    _sc_order(libc_fork, ["__run_prefork_handlers(multiple_threads)", "pid_t pid=_Fork();",
                          "if (pid==0)", "return pid;"])
    _sc_once(glibc["posix/fork.c"], "weak_alias(__libc_fork,fork)")
    fork = _sc_function(glibc["sysdeps/nptl/_Fork.c"], "_Fork")
    _sc_once(fork, "arch_fork(")
    _sc_order(fork, ["__abort_lock_rdlock(&original_sigmask);",
                     "pid_t pid=arch_fork(&THREAD_SELF->tid);", "if (pid==0)",
                     "__abort_lock_unlock(&original_sigmask);", "return pid;"])
    arch = _sc_function(glibc["sysdeps/unix/sysv/linux/arch-fork.h"], "arch_fork")
    _sc_once(arch, "const int flags=CLONE_CHILD_SETTID|CLONE_CHILD_CLEARTID|SIGCHLD;")
    _sc_once(arch, "#elif defined(__ASSUME_CLONE_DEFAULT) ret=INLINE_SYSCALL_CALL(clone,flags,0,NULL,ctid,0); #else")
    generic_features = glibc["sysdeps/unix/sysv/linux/kernel-features.h"]
    x86_features = glibc["sysdeps/unix/sysv/linux/x86_64/kernel-features.h"]
    _sc_once(generic_features, "#define __ASSUME_CLONE_DEFAULT 1")
    _need(not any(token.startswith("__ASSUME_CLONE_BACKWARDS") for token in generic_features)
          and not any(token.startswith("__ASSUME_CLONE_") for token in x86_features),
          "containment_entry_plan_source_clone_abi_override")
    _sc_once(x86_features, "#include_next <kernel-features.h>")
    wait = _sc_function(glibc["posix/wait.c"], "__wait")
    waitpid = _sc_function(glibc["posix/waitpid.c"], "__waitpid")
    _need(wait == _sc_c_tokens("return __waitpid(WAIT_ANY,stat_loc,0);"),
          "containment_entry_plan_source_wait_chain")
    _need(waitpid == _sc_c_tokens("return __wait4(pid,stat_loc,options,NULL);"),
          "containment_entry_plan_source_waitpid_chain")
    _sc_once(glibc["posix/wait.c"], "weak_alias(__wait,wait)")
    wait4 = _sc_function(glibc["sysdeps/unix/sysv/linux/wait4.c"], "__wait4_time64")
    _sc_once(wait4, "#ifdef __NR_wait4 #if __KERNEL_OLD_TIMEVAL_MATCHES_TIMEVAL64 return SYSCALL_CANCEL(wait4,pid,stat_loc,options,usage); #else")

    bwrap_series, bwrap_patches = _sc_quilt(bwrap_debian)
    _need(len(bwrap_series) == len(bwrap_patches) == 1,
          "containment_entry_plan_source_bubblewrap_patch_count")
    patch_name = "debian/patches/" + bwrap_series[0]
    sections = bwrap_patches[patch_name]
    _need(len(sections) == 1 and sections[0]["old_path"] == sections[0]["new_path"] == "bubblewrap.c"
          and len(sections[0]["hunks"]) == 1,
          "containment_entry_plan_source_bubblewrap_patch_scope")
    _sc_check_hunk_context(bwrap_text, sections[0])
    hunk = sections[0]["hunks"][0]
    old, new = _sc_c_tokens("\n".join(hunk["removed"])), _sc_c_tokens("\n".join(hunk["added"]))
    _need(len(old) == len(new) == 5 and old[:2] == new[:2] == ["die", "("]
          and old[3:] == new[3:] == [")", ";"]
          and old[2].startswith('"') and new[2].startswith('"') and old[2] != new[2],
          "containment_entry_plan_source_bubblewrap_diagnostic_patch")
    _sc_once(main, _sc_c_tokens("else if(errno==EPERM)") + old)

    glibc_series, glibc_patches = _sc_quilt(glibc_debian)
    touches = []
    reviewed = set(glibc_relative)
    for name, sections in glibc_patches.items():
        touched = sorted({path for section in sections for path in
                          (section["old_path"], section["new_path"]) if path in reviewed})
        if touched:
            _need(name.removeprefix("debian/patches/") in glibc_series,
                  "containment_entry_plan_source_inactive_reviewed_patch")
            touches.append({"member": name, **binding(glibc_debian[name]),
                            "touches_reviewed_members": touched})
    _need(len(touches) == 1 and touches[0]["member"] == "debian/patches/git-updates.diff"
          and touches[0]["touches_reviewed_members"] == ["posix/fork.c"],
          "containment_entry_plan_source_glibc_patch_scope")
    fork_sections = [section for section in glibc_patches[touches[0]["member"]]
                     if section["old_path"] == "posix/fork.c" or section["new_path"] == "posix/fork.c"]
    _need(len(fork_sections) == 1 and fork_sections[0]["old_path"] == fork_sections[0]["new_path"]
          and len(fork_sections[0]["hunks"]) == 1,
          "containment_entry_plan_source_glibc_fork_patch")
    _sc_check_hunk_context(_sc_text(glibc_orig, "glibc-2.41/posix/fork.c"), fork_sections[0])
    fork_hunk = fork_sections[0]["hunks"][0]
    _need(_sc_c_tokens("\n".join(fork_hunk["removed"]))
          == _sc_c_tokens("struct nss_database_data nss_database_data;")
          and _sc_c_tokens("\n".join(fork_hunk["added"]))
          == _sc_c_tokens("struct nss_database_for_fork nss_database_data;"),
          "containment_entry_plan_source_glibc_fork_patch_operations")

    build = _sc_source_build(bwrap_orig, bwrap_debian,
                             _sc_c_tokens(_sc_text(bwrap_orig, bwrap_names[2])))
    # Linux x86-64 ABI bit values, joined to the source's selected symbolic
    # expressions. Ignored trailing registers of raw_clone are not constrained.
    abi = {"SIGCHLD": 17, "CLONE_NEWNS": 0x00020000, "CLONE_NEWUSER": 0x10000000,
           "CLONE_NEWPID": 0x20000000, "CLONE_NEWNET": 0x40000000,
           "CLONE_NEWIPC": 0x08000000, "CLONE_NEWUTS": 0x04000000,
           "CLONE_NEWCGROUP": 0x02000000, "CLONE_CHILD_SETTID": 0x01000000,
           "CLONE_CHILD_CLEARTID": 0x00200000}
    initial_flags, fork_flags = 0, 0
    for name in ["SIGCHLD", "CLONE_NEWNS"] + flag_names:
        initial_flags |= abi[name]
    for name in ("CLONE_CHILD_SETTID", "CLONE_CHILD_CLEARTID", "SIGCHLD"):
        fork_flags |= abi[name]
    bwrap_debian_names = ["debian/patches/series", patch_name, "debian/rules",
                         "debian/source/format", "debian/control", "debian/copyright"]
    return {
        "clone_flags": [f"0x{initial_flags:08x}", f"0x{fork_flags:08x}"],
        "bubblewrap_source_version": build.pop("version"),
        "bubblewrap_patch_count": len(bwrap_series),
        "glibc_reviewed_source_members": len(glibc_names),
        "bubblewrap_source": {
            **build, "patch_series": bwrap_series,
            "reviewed_original_members": _sc_member_bindings(bwrap_orig, bwrap_names),
            "reviewed_debian_members": _sc_member_bindings(bwrap_debian, bwrap_debian_names),
        },
        "glibc_source": {
            "reviewed_original_members": _sc_member_bindings(glibc_orig, glibc_names),
            "patches_touching_reviewed_members": touches,
        },
        "patch_scan": {
            "bubblewrap_active_patch_count": len(bwrap_series),
            "bubblewrap_preserved_patch_count": len(bwrap_patches),
            "glibc_active_patch_count": len(glibc_series),
            "glibc_preserved_patch_count": len(glibc_patches),
        },
    }


class PlanError(ValueError):
    """A stable rejection code, without input bytes or filesystem details."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise PlanError(code)


def binding(raw):
    _need(type(raw) is bytes, "containment_plan_bytes_required")
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def _pairs(items):
    result = {}
    for key, value in items:
        _need(key not in result, "containment_plan_duplicate_json_key")
        result[key] = value
    return result


def _number_rejected(_text):
    raise PlanError("containment_plan_noninteger_number")


def parse(raw):
    _need(type(raw) is bytes and 0 < len(raw) <= CONTROL_BYTES,
          "containment_plan_control_size")
    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                            parse_float=_number_rejected, parse_constant=_number_rejected)
    except (UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, PlanError):
            raise
        raise PlanError("containment_plan_json_invalid") from exc
    _need(type(result) is dict, "containment_plan_json_object_required")
    pending, count = [(result, 0)], 0
    while pending:
        value, depth = pending.pop()
        count += 1
        _need(depth <= 48 and count <= 100000, "containment_plan_json_complexity")
        if type(value) is dict:
            pending.extend((child, depth + 1) for child in value.values())
        elif type(value) is list:
            pending.extend((child, depth + 1) for child in value)
        elif type(value) is int:
            _need(abs(value) < 2 ** 64, "containment_plan_integer_bound")
        else:
            _need(value is None or type(value) in (str, bool), "containment_plan_json_type")
    return result


def _same(actual, expected, code):
    _need(canonical(actual) == canonical(expected), code)


def _bound(raw, expected, code):
    _need(type(raw) is bytes and len(raw) == expected["size_bytes"], code)
    _need(hashlib.sha256(raw).hexdigest() == expected["sha256"], code)


def _control(raw, expected, code):
    _need(type(expected) is str and re.fullmatch(r"[0-9a-f]{64}", expected) is not None, code)
    _need(type(raw) is bytes and len(raw) <= CONTROL_BYTES
          and hashlib.sha256(raw).hexdigest() == expected, code)
    return parse(raw)


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_uid, info.st_gid, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


@contextlib.contextmanager
def _parent(path):
    """Pin every directory; never follow a caller-supplied symlink."""
    supplied = os.fspath(path)
    _need(type(supplied) is str and "\x00" not in supplied
          and ".." not in Path(supplied).parts, "containment_plan_path_invalid")
    absolute = os.path.abspath(supplied)
    parts = Path(absolute).parts
    _need(len(parts) > 1, "containment_plan_file_path_required")
    descriptors, edges = [], []
    try:
        current = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        descriptors.append(current)
        for name in parts[1:-1]:
            following = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                dir_fd=current)
            info = os.fstat(following)
            edges.append((current, name, following, (info.st_dev, info.st_ino, info.st_mode)))
            descriptors.append(following)
            current = following
        yield current, parts[-1]
        for parent, name, child, expected in edges:
            before = os.fstat(child)
            after = os.stat(name, dir_fd=parent, follow_symlinks=False)
            _need((before.st_dev, before.st_ino, before.st_mode) == expected
                  == (after.st_dev, after.st_ino, after.st_mode),
                  "containment_plan_parent_changed")
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _read_file(path, limit):
    try:
        with _parent(path) as (parent, name):
            fd = os.open(name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC,
                         dir_fd=parent)
            try:
                before = os.fstat(fd)
                _need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                      and before.st_size <= limit, "containment_plan_file_shape")
                chunks, total = [], 0
                while True:
                    block = os.read(fd, min(65536, limit + 1 - total))
                    if not block:
                        break
                    total += len(block)
                    _need(total <= limit, "containment_plan_file_limit")
                    chunks.append(block)
                after = os.fstat(fd)
                named = os.stat(name, dir_fd=parent, follow_symlinks=False)
                _need(_identity(before) == _identity(after) == _identity(named)
                      and total == before.st_size, "containment_plan_file_changed")
                return b"".join(chunks)
            finally:
                os.close(fd)
    except OSError as exc:
        raise PlanError("containment_plan_file_unreadable") from exc


def load_inputs(root=ROOT):
    root = Path(root)
    return {name: _read_file(root / name, row["size_bytes"])
            for name, row in INPUT_BINDINGS.items()}


def _implementation():
    return {name: _read_file(ROOT / name, CONTROL_BYTES)
            for name in (TOOL_REL, SCHEMA_REL)}


def _validate(schema, definition, value):
    selected = {"$schema": schema["$schema"], "$defs": schema["$defs"],
                "$ref": "#/$defs/" + definition}
    _need(not any(jsonschema.Draft202012Validator(selected).iter_errors(value)),
          "containment_plan_" + definition + "_schema")


def _rows(rows, available, key):
    result = []
    _need(len({row[key] for row in rows}) == len(rows), "containment_plan_selected_duplicate")
    for row in rows:
        name = row[key]
        _need(name in available and type(available[name]) is bytes,
              "containment_plan_selected_regular_missing")
        _bound(available[name], row, "containment_plan_selected_member_binding")
        result.append({**row, **binding(available[name])})
    return result


def _elf(raw, *, static=False):
    """Decode selected ELF bytes; never load a library or invoke a program."""
    _need(type(raw) is bytes and 64 <= len(raw) <= 8 * 1024 * 1024,
          "containment_plan_elf_size")
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", raw)
    ident, kind, machine, version, entry, phoff = header[:6]
    ehsize, phsize, phcount = header[8:11]
    _need(ident[:7] == b"\x7fELF\x02\x01\x01" and kind in (2, 3)
          and machine == 62 and version == 1 and ehsize == 64 and phsize == 56
          and 0 < phcount <= 128 and 64 <= phoff
          and phoff + phcount * phsize <= len(raw), "containment_plan_elf_header")
    loads, interps, dynamics = [], [], []
    for number in range(phcount):
        ptype, flags, offset, address, _physical, size, memory, alignment = struct.unpack_from(
            "<IIQQQQQQ", raw, phoff + number * phsize)
        _need(offset <= len(raw) and size <= len(raw) - offset and flags <= 7,
              "containment_plan_elf_segment_extent")
        if ptype == 1:
            _need(size <= memory and address + memory < 2 ** 64 and flags & 3 != 3
                  and (alignment in (0, 1) or alignment & (alignment - 1) == 0),
                  "containment_plan_elf_load_shape")
            loads.append((offset, address, size, memory, flags))
        elif ptype == 3:
            text = raw[offset:offset + size]
            _need(2 <= size <= 4096 and text.endswith(b"\0") and b"\0" not in text[:-1],
                  "containment_plan_elf_interpreter")
            interps.append(text[:-1].decode("ascii"))
        elif ptype == 2:
            _need(size % 16 == 0 and 0 < size <= 65536, "containment_plan_elf_dynamic_size")
            dynamics.append((offset, size))
    _need(loads and len(interps) <= 1 and len(dynamics) <= 1, "containment_plan_elf_segment_count")
    needed = []
    if static:
        _need(kind == 2 and not interps and not dynamics
              and sum(address <= entry < address + size and flags & 1 != 0
                      for _, address, size, _, flags in loads) == 1,
              "containment_plan_static_entry_shape")
    else:
        _need(len(dynamics) == 1, "containment_plan_elf_dynamic_missing")
        tags, names, terminated = {}, [], False
        offset, size = dynamics[0]
        for at in range(offset, offset + size, 16):
            tag, value = struct.unpack_from("<qQ", raw, at)
            if tag == 0:
                terminated = True
                break
            if tag == 1:
                names.append(value)
            if tag in (5, 10):
                _need(tag not in tags, "containment_plan_elf_dynamic_duplicate")
                tags[tag] = value
        _need(terminated and set(tags) == {5, 10} and 0 < tags[10] <= len(raw),
              "containment_plan_elf_dynamic_strings")
        spans = [o + tags[5] - a for o, a, n, _, _ in loads
                 if a <= tags[5] and tags[5] + tags[10] <= a + n]
        _need(len(spans) == 1, "containment_plan_elf_strings_mapping")
        strings = raw[spans[0]:spans[0] + tags[10]]
        for index in names:
            _need(index < len(strings), "containment_plan_elf_needed_offset")
            end = strings.find(b"\0", index)
            _need(index < end <= index + 255, "containment_plan_elf_needed_name")
            name = strings[index:end].decode("ascii")
            _need(re.fullmatch(r"[A-Za-z0-9_.+-]+", name) is not None,
                  "containment_plan_elf_needed_name")
            needed.append(name)
        _need(len(set(needed)) == len(needed), "containment_plan_elf_needed_duplicate")
    return {"kind": kind, "entry": entry, "interpreter": interps,
            "needed": needed, "load_count": len(loads)}


def _bpf(source):
    try:
        tree = ast.parse(source.decode("ascii"))
        assignments = [node for node in tree.body if isinstance(node, ast.Assign)
                       and any(isinstance(target, ast.Name) and target.id == "SYSCALLS"
                               for target in node.targets)]
        _need(len(assignments) == 1, "containment_plan_syscall_assignment")
        calls = ast.literal_eval(assignments[0].value)
    except (ValueError, SyntaxError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, PlanError):
            raise
        raise PlanError("containment_plan_policy_source") from exc
    _need(type(calls) is dict and len(calls) == 69
          and all(type(k) is str and type(v) is int and 0 <= v < 512 for k, v in calls.items())
          and len(set(calls.values())) == len(calls), "containment_plan_syscall_roster")
    rows = [(0x20, 0, 0, 4), (0x15, 1, 0, 0xc000003e), (0x06, 0, 0, 0x80000000),
            (0x20, 0, 0, 0), (0x45, 0, 1, 0x40000000), (0x06, 0, 0, 0x80000000)]
    for number in sorted(calls.values()):
        rows.extend(((0x15, 0, 1, number), (0x06, 0, 0, 0x7fff0000)))
    rows.append((0x06, 0, 0, 0x00050001))
    return b"".join(struct.pack("<HBBI", *row) for row in rows), len(rows)


def _paragraphs(raw):
    _need(type(raw) is bytes and raw.endswith(b"\n") and b"\r" not in raw and b"\0" not in raw,
          "containment_plan_debian_index_encoding")
    _need(len(raw) <= 64 * 1024 * 1024, "containment_plan_debian_index_limit")
    paragraphs = raw.split(b"\n\n")
    _need(len(paragraphs) <= 100000, "containment_plan_debian_stanza_count")
    for paragraph in paragraphs:
        if not paragraph:
            continue
        _need(len(paragraph) <= 512 * 1024, "containment_plan_debian_stanza_limit")
        yield paragraph


def _fields(paragraph):
    result, current = {}, None
    for line in paragraph.splitlines():
        if line.startswith((b" ", b"\t")):
            _need(current is not None, "containment_plan_debian_continuation")
            result[current] += b"\n" + line
            continue
        name, sep, value = line.partition(b":")
        _need(sep and re.fullmatch(rb"[A-Za-z0-9-]+", name) is not None,
              "containment_plan_debian_field")
        current = name.decode("ascii").lower()
        _need(current not in result, "containment_plan_debian_duplicate_field")
        result[current] = value.strip()
    return result


def _sha_rows(fields):
    _need("checksums-sha256" in fields, "containment_plan_source_checksums_missing")
    result = {}
    for line in fields["checksums-sha256"].splitlines():
        if not line.strip():
            continue
        bits = line.split()
        _need(len(bits) == 3 and re.fullmatch(rb"[0-9a-f]{64}", bits[0]) is not None
              and re.fullmatch(rb"[0-9]+", bits[1]) is not None,
              "containment_plan_source_checksum_row")
        name = bits[2].decode("ascii")
        _need(re.fullmatch(r"[A-Za-z0-9_.+~-]+", name) is not None and name not in result,
              "containment_plan_source_checksum_name")
        result[name] = {"sha256": bits[0].decode("ascii"), "size_bytes": int(bits[1])}
    _need(result, "containment_plan_source_checksums_empty")
    return result


def _dsc_fields(raw):
    # Inspect the signed message as data; no cryptographic verification is claimed.
    _need(raw.startswith(b"-----BEGIN PGP SIGNED MESSAGE-----\n")
          and raw.count(b"-----BEGIN PGP SIGNATURE-----") == 1,
          "containment_plan_dsc_shape")
    preamble, body = raw.split(b"\n\n", 1)
    _need(preamble == b"-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA512",
          "containment_plan_dsc_hash_header")
    body = body.split(b"-----BEGIN PGP SIGNATURE-----", 1)[0].rstrip(b"\n")
    _need(b"\n- " not in body, "containment_plan_dsc_dash_escape")
    return _fields(body)


def _metadata_relationships(originals, sources_raw, inputs):
    sources = _xz_decode(sources_raw, 64 * 1024 * 1024)
    _bound(sources, {"sha256": "ae99131b13c7e61c53a52c33a2f9088a1bc5db15a664f5d90cc3753ad9b65606",
                     "size_bytes": 57389881}, "containment_plan_source_index_decoded")
    targets = {}
    versions = {b"bubblewrap": b"0.12.0-1~deb13u1", b"glibc": b"2.41-12+deb13u4"}
    for raw in _paragraphs(sources):
        fields = _fields(raw)
        name = fields.get("package")
        if name in versions and fields.get("version") == versions[name]:
            _need(name not in targets, "containment_plan_source_stanza_ambiguous")
            targets[name] = (raw, fields)
    _need(set(targets) == {b"bubblewrap", b"glibc"}, "containment_plan_source_stanza_missing")
    raw, bwrap = targets[b"bubblewrap"]
    _need(bwrap.get("version") == b"0.12.0-1~deb13u1"
          and bwrap.get("directory") == b"pool/main/b/bubblewrap",
          "containment_plan_bwrap_source_identity")
    rows = _sha_rows(bwrap)
    selected = SELECTION["bubblewrap_source"]
    for row in selected["new_source_files"]:
        name = row["path"].rsplit("/", 1)[-1]
        _same(rows.get(name), binding(inputs[row["path"]]), "containment_plan_source_index_artifact")
    dsc_path = next(row["path"] for row in selected["new_source_files"] if row["path"].endswith(".dsc"))
    dsc = _dsc_fields(inputs[dsc_path])
    _need(dsc.get("source") == bwrap.get("package") and dsc.get("version") == bwrap.get("version")
          and dsc.get("format") == b"3.0 (quilt)", "containment_plan_dsc_identity")
    _same(_sha_rows(dsc), {name: row for name, row in rows.items() if not name.endswith(".dsc")},
          "containment_plan_dsc_archive_relationship")
    glibc = targets[b"glibc"][1]
    _need(glibc.get("version") == b"2.41-12+deb13u4"
          and glibc.get("directory") == b"pool/main/g/glibc", "containment_plan_glibc_source_identity")
    grows = _sha_rows(glibc)
    _same(grows.get("glibc_2.41.orig.tar.xz"), SELECTION["glibc_source"]["joined_original_archive"],
          "containment_plan_glibc_source_original")
    debian = SELECTION["glibc_source"]["debian_carrier"]
    _same(grows.get("glibc_2.41-12+deb13u4.debian.tar.xz"), binding(inputs[debian["path"]]),
          "containment_plan_glibc_source_debian")
    package_rows = []
    for stanza in _paragraphs(originals["distribution-origin/Packages"]):
        fields = _fields(stanza)
        if (fields.get("package"), fields.get("version"), fields.get("architecture")) == (
                b"bubblewrap", b"0.12.0-1~deb13u1", b"amd64"):
            package_rows.append(fields)
    _need(len(package_rows) == 1, "containment_plan_binary_package_ambiguous")
    package = package_rows[0]
    artifact = originals["origin/bubblewrap_0.12.0-1~deb13u1_amd64.deb"]
    actual_package = {"name": package["package"].decode("ascii"),
                      "version": package["version"].decode("ascii"),
                      "architecture": package["architecture"].decode("ascii"), **binding(artifact)}
    _need(package.get("sha256", b"").decode("ascii") == actual_package["sha256"]
          and package.get("size") == str(len(artifact)).encode("ascii")
          and package.get("filename") == b"pool/main/b/bubblewrap/bubblewrap_0.12.0-1~deb13u1_amd64.deb"
          and package.get("source", b"bubblewrap") == b"bubblewrap",
          "containment_plan_binary_package_index")
    # Both complete indices are also joined to the exact historical Release bytes.
    release = _fields(originals["distribution-origin/Release"])
    release_rows = {}
    for line in release.get("sha256", b"").splitlines():
        bits = line.split()
        if not bits:
            continue
        _need(len(bits) == 3 and bits[2] not in release_rows, "containment_plan_release_checksum")
        release_rows[bits[2]] = {"sha256": bits[0].decode("ascii"), "size_bytes": int(bits[1])}
    for name, data in ((b"main/source/Sources.xz", sources_raw), (b"main/source/Sources", sources),
                       (b"main/binary-amd64/Packages", originals["distribution-origin/Packages"])):
        _same(release_rows.get(name), binding(data), "containment_plan_release_index_relationship")
    return {"directory": bwrap["directory"].decode("ascii"),
            "package": bwrap["package"].decode("ascii"), "version": bwrap["version"].decode("ascii"),
            "exact_bytes_without_blank_separator": binding(raw)}, actual_package


def _launch(entry_binding):
    namespace_args = ["--unshare-" + name for name in ("user", "ipc", "pid", "net", "uts", "cgroup")]
    arguments = namespace_args + ["--disable-userns", "--cap-drop", "ALL", "--die-with-parent", "--clearenv",
                                  "--setenv", "LC_ALL", "C", "--setenv", "TZ", "UTC"]
    view = []
    for path in ("/", "/empty", "/runtime", "/runtime/bootstrap"):
        arguments.extend(("--perms", "0700", "--tmpfs" if path == "/" else "--dir", path))
        view.append({"kind": "directory", "mode_octal": "0700", "path": path})
    executable = "/runtime/bootstrap/containment-entry"
    arguments.extend(("--perms", "0500", "--ro-bind-data", "4", executable, "--remount-ro", "/",
                      "--seccomp", "5", "--chdir", "/empty", "--", executable, "worker"))
    view.append({"kind": "regular_file", "mode_octal": "0500", "path": executable, **entry_binding})
    encoded = b"".join(token.encode("ascii") + b"\0" for token in arguments)
    return {**copy.deepcopy(LAUNCH_POLICY), "arguments": arguments, "arguments_bytes": binding(encoded),
            "minimal_view": view, "expected_T_environment": {"LC_ALL": "C", "TZ": "UTC", "PWD": "/empty"}}


def _policy_projection(plan):
    policy = copy.deepcopy(plan)
    policy.pop("launch")
    policy.pop("source_inventory")
    for key in ("image_sha256", "image_size_bytes"):
        policy["next_terminal_boundary"].pop(key)
    for row in policy["task_graph"]["creation_contracts"]:
        row.pop("flags_hex")
    policy["observation_contract"].pop("ptrace_options_hex")
    for key in ("current_tools_entries", "current_targeted_pytest_entries"):
        policy["ci_boundary"].pop(key)
    return policy


def _historical_example(originals, baseline):
    selected = SELECTION["historical_example_runtime"]
    capsule = originals[selected["capsule"]["member"]]
    _bound(capsule, selected["capsule"], "containment_plan_example_capsule")
    members = _zip_members(capsule, count_limit=128, decoded_limit=2 * 1024 * 1024,
                           member_limit=1024 * 1024)
    python = members[selected["python"]["member"]]
    _bound(python, selected["python"], "containment_plan_example_python")
    rows = _rows(selected["records"], originals, "member")
    records = {row["member"]: parse(originals[row["member"]]) for row in rows}
    for item in records.values():
        _need(item.get("record_status") == "example" and item.get("execution_authorized") is False
              and item.get("production_gate_eligible") is False and item.get("authority_effect") == "none",
              "containment_plan_example_nonpromotion")
    runtime, operator, bootstrap, containment = [records["controls/" + kind + "-selection.json"]
                                                for kind in ("runtime", "operator", "bootstrap", "containment")]
    for record in (runtime, bootstrap):
        _need(record["operator_selection_sha256"] == binding(originals["controls/operator-selection.json"])["sha256"],
              "containment_plan_example_operator_join")
    _need(bootstrap["runtime_selection_sha256"] == binding(originals["controls/runtime-selection.json"])["sha256"]
          and bootstrap["capsule_sha256"] == binding(capsule)["sha256"], "containment_plan_example_capsule_join")
    _same(runtime["environment"], operator["environment"], "containment_plan_example_environment_join")
    _need(runtime["environment"]["executable_sha256"] == binding(python)["sha256"]
          and runtime["environment"]["python_version"] == "3.11.16"
          and runtime["environment"]["unicode_version"] == "14.0.0", "containment_plan_example_python_join")
    _need(containment["bootstrap_plan_sha256"] == binding(originals["controls/bootstrap-plan.json"])["sha256"],
          "containment_plan_example_bootstrap_join")
    for key in ("entry_source", "policy_source"):
        source = containment[key]
        _bound(baseline[source["path"]], source, "containment_plan_example_source_join")
    _same(containment["entry_shim"], binding(originals["entry-build/build-1/entry"]),
          "containment_plan_example_entry_join")
    _same({key: containment["launcher"][key] for key in ("sha256", "size_bytes")}, binding(originals["native/bwrap"]),
          "containment_plan_example_launcher_join")
    return rows, binding(python)


def _historical_observation(inputs, edges):
    selected = SELECTION["historical_loader_observation"]
    record = parse(inputs[selected["preservation_record"]["path"]])
    _need(record["record_role"] == "descriptive_preservation_inventory"
          and record["is_independent_checker_report"] is False, "containment_plan_historical_record_role")
    observed = record["observed_run"]
    for key, expected in (("run_id", selected["run_id"]), ("run_attempt", selected["attempt"]),
                          ("run_number", selected["run_number"]), ("source_commit", selected["source_commit"])):
        _same(observed[key], expected, "containment_plan_historical_run_join")
    raw = inputs[selected["control_carrier"]["path"]]
    members = _zip_members(raw, count_limit=512, decoded_limit=16 * 1024 * 1024, member_limit=4 * 1024 * 1024)
    inventory = record["repository_control_evidence"]
    _bound(raw, inventory, "containment_plan_historical_control_binding")
    rows = inventory["selected_members"]
    _need(len(rows) == inventory["selected_member_count"] == len(members)
          and {row["control_path"] for row in rows} == set(members)
          and sum(len(value) for value in members.values()) == inventory["selected_uncompressed_bytes"],
          "containment_plan_historical_control_roster")
    for row in rows:
        _bound(members[row["control_path"]], row, "containment_plan_historical_control_member")
    joins = record["checked_original_loader_capture"]["occurrence_joins"]
    _need(len(joins) == len(edges) == 9
          and {(row["consumer"], row["name"], row["provider"]) for row in joins} == set(edges),
          "containment_plan_historical_needed_relationship")
    # This joins descriptive preservation bytes, not raw-event replay or a live prefix.


def _manifest_count(raw):
    rows = [line.strip() for line in raw.decode("ascii").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]
    _need(len(set(rows)) == len(rows), "containment_plan_manifest_duplicate")
    return len(rows)


def verify_plan(*, plan_bytes, expected_plan_sha256, source_inventory_bytes,
                expected_source_inventory_sha256, inputs):
    implementation = _implementation()
    schema = parse(implementation[SCHEMA_REL])
    plan = _control(plan_bytes, expected_plan_sha256, "containment_plan_expected_digest")
    inventory = _control(source_inventory_bytes, expected_source_inventory_sha256,
                         "containment_plan_expected_inventory_digest")
    _validate(schema, "plan", plan)
    _validate(schema, "source_inventory", inventory)
    _same(_policy_projection(plan), PLAN_POLICY, "containment_plan_reviewed_policy_changed")
    # These are independently selected identities and policy, never caller-selected pins.
    _same(inventory, SELECTION, "containment_plan_reviewed_source_selection_changed")
    _same(plan["source_inventory"], {"path": INVENTORY_REL, **binding(source_inventory_bytes)},
          "containment_plan_inventory_join")
    _need(type(inputs) is dict and all(type(key) is str and type(value) is bytes
                                     for key, value in inputs.items())
          and set(inputs) == set(INPUT_BINDINGS), "containment_plan_input_roster")
    # Bind one immutable-byte snapshot. A caller can retain/mutate its mapping,
    # but later report rows must describe exactly the bytes verified above.
    inputs = dict(inputs)
    for name, expected in INPUT_BINDINGS.items():
        _bound(inputs[name], expected, "containment_plan_original_carrier_binding")
    # Frozen original sources remain valid when current docs/tests evolve.
    baseline = _zip_members(inputs[BASELINE_REL], count_limit=34, decoded_limit=3 * 1024 * 1024,
                            member_limit=2 * 1024 * 1024)
    _need(set(baseline) == {row["path"] for row in SELECTION["baseline_files"]},
          "containment_plan_baseline_roster")
    reconstructed = copy.deepcopy(SELECTION)
    reconstructed["baseline_files"] = _rows(SELECTION["baseline_files"], baseline, "path")
    original_selection = SELECTION["original_native_inputs"]
    originals = _zip_members(inputs[original_selection["carrier"]["path"]], count_limit=128,
                             decoded_limit=80 * 1024 * 1024, member_limit=64 * 1024 * 1024)
    reconstructed["original_native_inputs"]["members"] = _rows(original_selection["members"], originals, "member")
    providers = {row["member"].rsplit("/", 1)[-1]: row["member"] for row in original_selection["members"]}
    edges, load_count, interpreter_count = [], 0, 0
    for row in original_selection["members"]:
        native = _elf(originals[row["member"]])
        load_count += native["load_count"]
        interpreter_count += len(native["interpreter"])
        _need(all(name == "/lib64/ld-linux-x86-64.so.2" for name in native["interpreter"]),
              "containment_plan_original_interpreter")
        for name in native["needed"]:
            _need(name in providers, "containment_plan_original_provider_missing")
            edges.append((row["member"], name, providers[name]))
    _need(len(edges) == 9 and load_count == 24 and interpreter_count == 3,
          "containment_plan_original_native_shape")
    entry_selection = SELECTION["static_entry"]
    build = _zip_members(inputs[entry_selection["build_carrier"]["path"]], count_limit=32,
                         decoded_limit=1024 * 1024, member_limit=65536)
    reconstructed["static_entry"]["members"] = _rows(entry_selection["members"], build, "member")
    entry = build[entry_selection["members"][0]["member"]]
    _need(entry == build[entry_selection["members"][1]["member"]]
          == originals["entry-build/build-1/entry"] == originals["entry-build/build-2/entry"],
          "containment_plan_static_entry_carrier_join")
    static = _elf(entry, static=True)
    start = parse(build["workflow-start.json"])
    _need(start["source_commit"] == entry_selection["source_commit"]
          and start["run_id"] == entry_selection["run_id"] and start["run_attempt"] == entry_selection["attempt"],
          "containment_plan_entry_build_context")
    source = baseline[entry_selection["source"]["path"]]
    _need(source == build["evidence/source.c"] == originals["entry-build/source.c"],
          "containment_plan_entry_source_carrier_join")
    bpf, instruction_count = _bpf(baseline[SELECTION["existing_containment_policy"]["source"]["path"]])
    reconstructed["existing_containment_policy"]["derived_classic_bpf"].update(
        binding(bpf), instruction_count=instruction_count)
    bwrap_selection, glibc_selection = SELECTION["bubblewrap_source"], SELECTION["glibc_source"]
    sources_raw = b"".join(inputs[row["path"]] for row in bwrap_selection["source_index_parts"])
    glibc_raw = b"".join(inputs[row["path"]] for row in glibc_selection["original_parts"])
    reconstructed["bubblewrap_source"]["joined_compressed_source_index"] = binding(sources_raw)
    reconstructed["glibc_source"]["joined_original_archive"] = binding(glibc_raw)
    stanza, package = _metadata_relationships(originals, sources_raw, inputs)
    reconstructed["bubblewrap_source"]["matched_stanza"] = stanza
    reconstructed["original_native_inputs"]["selected_package"] = package
    bwrap_inputs = {row["path"].rsplit("/", 1)[-1]: inputs[row["path"]] for row in bwrap_selection["new_source_files"]}
    bo = _tar_members(bwrap_inputs["bubblewrap_0.12.0.orig.tar.xz"], count_limit=128,
                      decoded_limit=1024 * 1024, member_limit=2 * 1024 * 1024)
    bd = _tar_members(bwrap_inputs["bubblewrap_0.12.0-1~deb13u1.debian.tar.xz"], count_limit=64,
                      decoded_limit=256 * 1024, member_limit=2 * 1024 * 1024)
    go = _tar_members(glibc_raw, count_limit=24576, decoded_limit=256 * 1024 * 1024,
                      member_limit=2 * 1024 * 1024,
                      selected={row["member"] for row in glibc_selection["reviewed_original_members"]})
    gd = _tar_members(inputs[glibc_selection["debian_carrier"]["path"]], count_limit=512,
                      decoded_limit=4 * 1024 * 1024, member_limit=2 * 1024 * 1024)
    for section, key, archive in (("bubblewrap_source", "reviewed_original_members", bo),
                                  ("bubblewrap_source", "reviewed_debian_members", bd),
                                  ("glibc_source", "reviewed_original_members", go),
                                  ("glibc_source", "patches_touching_reviewed_members", gd)):
        reconstructed[section][key] = _rows(SELECTION[section][key], archive, "member")
    source_facts = _source_contracts(bo, bd, go, gd)
    _need(source_facts["bubblewrap_patch_count"] == 1 and source_facts["glibc_reviewed_source_members"] == 8,
          "containment_plan_source_review_roster")
    for section in ("bubblewrap_source", "glibc_source"):
        reconstructed[section].update(source_facts[section])
    records, python = _historical_example(originals, baseline)
    reconstructed["historical_example_runtime"]["records"] = records
    reconstructed["historical_example_runtime"]["python"].update(python)
    _historical_observation(inputs, edges)
    # Also reconstruct every path binding; retained prose remains reviewed policy.
    def join_paths(value):
        if isinstance(value, dict):
            if {"path", "sha256", "size_bytes"} <= set(value):
                available = inputs if value["path"] in inputs else baseline
                _need(value["path"] in available, "containment_plan_bound_path_missing")
                value.update(binding(available[value["path"]]))
            for child in value.values():
                join_paths(child)
        elif isinstance(value, list):
            for child in value:
                join_paths(child)
    join_paths(reconstructed)
    _same(inventory, reconstructed, "containment_plan_inventory_reconstruction")
    expected = copy.deepcopy(PLAN_POLICY)
    expected["source_inventory"] = {"path": INVENTORY_REL, **binding(source_inventory_bytes)}
    expected["launch"] = _launch(binding(entry))
    expected["next_terminal_boundary"].update(image_sha256=binding(entry)["sha256"], image_size_bytes=len(entry))
    for row, flags in zip(expected["task_graph"]["creation_contracts"], source_facts["clone_flags"]):
        row["flags_hex"] = flags
    options = {"PTRACE_O_TRACESYSGOOD": 0x1, "PTRACE_O_TRACEFORK": 0x2,
               "PTRACE_O_TRACEVFORK": 0x4, "PTRACE_O_TRACECLONE": 0x8,
               "PTRACE_O_TRACEEXEC": 0x10, "PTRACE_O_EXITKILL": 0x100000}
    mask = 0
    for name in expected["observation_contract"]["ptrace_options"]:
        mask |= options[name]
    expected["observation_contract"]["ptrace_options_hex"] = "0x%08x" % mask
    expected["ci_boundary"]["current_tools_entries"] = _manifest_count(baseline["ci/tools-tests.list"])
    expected["ci_boundary"]["current_targeted_pytest_entries"] = _manifest_count(baseline["ci/pytest-tests.list"])
    _same(plan, expected, "containment_plan_relationship_reconstruction")
    boundary = {key: False for key in (
        "historical_raw_capture_replayed", "fresh_signature_verification_performed", "source_binary_equivalence_verified",
        "host_environment_qualified", "native_acquisition_performed", "containment_observed", "bootstrap_execution_observed",
        "selected_runtime_admitted", "execution_ready", "execution_authorized", "physical_execution_authenticated",
        "complete_runtime_closure_verified", "b2_complete", "production_gate_eligible")}
    boundary.update({key: True for key in ("design_relationships_verified", "historical_baseline_bytes_verified",
                                          "source_carrier_bytes_verified", "plan_schema_implemented",
                                          "independent_plan_checker_implemented")})
    boundary.update(metric_pass=None, authority_effect="none", whole_runtime_issue={"number": 2879, "keep_open": True})
    report = {
        "record_type": "required_gate_idempotence_containment_entry_plan_verification_v0",
        "record_status": "verified_design", "profile": plan["profile"],
        "plan": binding(plan_bytes), "source_inventory": binding(source_inventory_bytes),
        "historical_baseline_commit": SELECTION["baseline_commit"],
        "input_files": [{"path": name, **binding(raw)} for name, raw in sorted(inputs.items())],
        "implementation_sources": [{"path": name, **binding(raw)} for name, raw in sorted(implementation.items())],
        "derived": {
            "baseline_source_files": len(baseline), "baseline_decoded_bytes": sum(map(len, baseline.values())),
            "original_native_objects": len(original_selection["members"]), "original_native_dt_needed_edges": len(edges),
            "static_entry": {**binding(entry), "elf_type": "ET_EXEC", "machine": "EM_X86_64",
                             "entry_virtual_address": static["entry"], "has_interpreter": False},
            "argument_bytes": expected["launch"]["arguments_bytes"], "argument_count": len(expected["launch"]["arguments"]),
            "containment_bpf": {**binding(bpf), "instruction_count": instruction_count},
            "bubblewrap_source_version": stanza["version"], "bubblewrap_patch_count": source_facts["bubblewrap_patch_count"],
            "glibc_reviewed_source_members": source_facts["glibc_reviewed_source_members"],
            "clone_flags": [row["flags_hex"] for row in expected["task_graph"]["creation_contracts"]],
            "ptrace_options_hex": expected["observation_contract"]["ptrace_options_hex"],
            "subject_roles": [row["role"] for row in expected["task_graph"]["subject_roles"]],
            "terminal_fd_numbers": expected["launch"]["terminal_T_fd_numbers"],
            "historical_python_size_bytes": python["size_bytes"], "acceptance_case_count": len(expected["acceptance_cases"]),
            "future_implementation_path_count": sum(map(len, expected["future_implementation_paths_all_proposed"].values())),
        }, "boundary": boundary,
    }
    _validate(schema, "report", report)
    _need(_implementation() == implementation, "containment_plan_implementation_changed")
    return report


def _write_new(path, raw):
    fd = parent_copy = None
    created_identity = None
    succeeded = False
    try:
        with _parent(path) as (parent, name):
            parent_copy = os.dup(parent)
            fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                         0o600, dir_fd=parent)
            created = os.fstat(fd)
            created_identity = (created.st_dev, created.st_ino)
            view = memoryview(raw)
            while view:
                count = os.write(fd, view)
                _need(count > 0, "containment_plan_output_short_write")
                view = view[count:]
            os.fsync(fd)
            completed = os.fstat(fd)
            named = os.stat(name, dir_fd=parent, follow_symlinks=False)
            _need(stat.S_ISREG(completed.st_mode) and completed.st_nlink == 1
                  and completed.st_size == len(raw) and _identity(completed) == _identity(named),
                  "containment_plan_output_changed")
            offset = 0
            while offset < len(raw):
                chunk = os.pread(fd, min(65536, len(raw) - offset), offset)
                _need(chunk and chunk == raw[offset:offset + len(chunk)], "containment_plan_output_changed")
                offset += len(chunk)
        # _parent has now validated the complete pinned directory chain too.
        _need(_identity(os.fstat(fd)) == _identity(completed), "containment_plan_output_changed")
        succeeded = True
    except OSError as exc:
        raise PlanError("containment_plan_output_unavailable") from exc
    finally:
        if not succeeded and created_identity is not None:
            # Keep cleanup responsibility through the directory-chain check;
            # never delete a replacement inode or any pre-existing output.
            try:
                now = os.stat(name, dir_fd=parent_copy, follow_symlinks=False)
                if (now.st_dev, now.st_ino) == created_identity:
                    os.unlink(name, dir_fd=parent_copy)
            except FileNotFoundError:
                pass
        if fd is not None:
            os.close(fd)
        if parent_copy is not None:
            os.close(parent_copy)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--expected-plan-sha256", required=True)
    parser.add_argument("--source-inventory", required=True, type=Path)
    parser.add_argument("--expected-source-inventory-sha256", required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        # Existing output must not be replaced, including dangling symlinks.
        _need(not os.path.lexists(args.out), "containment_plan_output_exists")
        plan_raw, inventory_raw = _read_file(args.plan, CONTROL_BYTES), _read_file(args.source_inventory, CONTROL_BYTES)
        report = verify_plan(plan_bytes=plan_raw, expected_plan_sha256=args.expected_plan_sha256,
                             source_inventory_bytes=inventory_raw,
                             expected_source_inventory_sha256=args.expected_source_inventory_sha256,
                             inputs=load_inputs(args.repo_root))
        raw = canonical(report)
        _write_new(args.out, raw)
    except PlanError as exc:
        sys.stderr.write(canonical({"status": "rejected", "code": exc.code}).decode("ascii"))
        return 1
    sys.stdout.write(raw.decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
