#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import dataclasses
import hashlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any, Callable, Mapping

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = (
    ROOT
    / "tools"
    / "load_pulsemech_compute_current_run_export_candidate_bundle_v0.py"
)
TOOLS_TESTS_MANIFEST = ROOT / "ci" / "tools-tests.list"
TEST_RELATIVE_PATH = (
    "tests/test_load_pulsemech_compute_current_run_export_candidate_bundle_v0.py"
)
PREVIOUS_COMPUTE_REGRESSION = (
    "tests/test_pulsemech_compute_current_run_export_candidate_workflow_v0.py"
)
FOLLOWING_COMPUTE_ANCHOR = (
    "tests/test_pulsemech_compute_subject_input_packet_schema_v0.py"
)

EXPECTED_TOOL_LINES = 5503
EXPECTED_TOOL_BYTES = 200118
EXPECTED_TOOL_SHA256 = (
    "698bb10f84de263127ee57b9c014070073b1b6b35cfffc794a2b05a9f8be641e"
)
EXPECTED_TOOL_GIT_BLOB_SHA1 = "bd8541cef0bc1044c71928602ad2f0e590324d16"

EXPECTED_TESTS = frozenset(
    {
        "test_loader_artifact_identity_matches_reviewed_fix",
        "test_tools_tests_manifest_registers_loader_regression_exactly_once",
        "test_authoritative_launcher_sanitizes_pytest_environment_and_requires_completed_contract",
        "test_direct_authoritative_launcher_rejects_terminal_pytest_early_exit",
        "test_direct_nonisolated_execution_fails_before_argument_parsing",
        "test_isolated_help_exposes_complete_cli_surface",
        "test_failure_diagnostic_and_authority_boundary_are_non_authoritative",
        "test_provider_artifact_metadata_binding_is_exact",
        "test_candidate_manifest_closes_exact_member_surface",
        "test_outer_archive_rejects_unsafe_flat_members",
        "test_packet_artifact_graph_resolves_exact_carrier_bytes",
        "test_packet_artifact_digest_forgery_is_rejected",
        "test_packet_unresolved_role_binding_is_rejected",
        "test_packet_semantically_wrong_role_binding_is_rejected",
        "test_packet_forged_coverage_is_rejected",
        "test_packet_provider_binding_drift_is_rejected",
        "test_carrier_expectation_and_packet_producer_digests_are_bound",
        "test_preservation_local_verification_is_derived",
        "test_negative_structural_completeness_is_rejected",
        "test_negative_independent_verification_is_rejected",
        "test_preservation_local_verification_mismatch_is_rejected",
        "test_shared_nested_artifact_budget_fails_closed",
        "test_output_parent_must_be_exclusively_owned",
        "test_output_files_are_created_relative_to_directory_descriptor",
        "test_temporary_directory_path_replacement_cannot_redirect_writes",
        "test_materialized_output_rejects_file_identity_replacement",
        "test_build_success_is_deterministic_and_read_only",
        "test_build_failure_leaves_no_partial_or_stale_output",
        "test_postpublication_reverification_failure_removes_owned_output",
        "test_intake_does_not_create_authority_or_transition_state",
    }
)
EXPECTED_COLLECTED_TEST_ITEMS = len(EXPECTED_TESTS)
CRITICAL_TESTS = frozenset(
    {
        "test_loader_artifact_identity_matches_reviewed_fix",
        "test_packet_artifact_graph_resolves_exact_carrier_bytes",
        "test_packet_artifact_digest_forgery_is_rejected",
        "test_packet_unresolved_role_binding_is_rejected",
        "test_packet_forged_coverage_is_rejected",
        "test_negative_structural_completeness_is_rejected",
        "test_negative_independent_verification_is_rejected",
        "test_preservation_local_verification_mismatch_is_rejected",
        "test_temporary_directory_path_replacement_cannot_redirect_writes",
        "test_build_success_is_deterministic_and_read_only",
        "test_build_failure_leaves_no_partial_or_stale_output",
        "test_postpublication_reverification_failure_removes_owned_output",
    }
)

_AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS = (
    "PYTEST_ADDOPTS",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    "PYTEST_PLUGINS",
)
_AUTHORITATIVE_LAUNCH_PROBE_CHILD = (
    "PULSEMECH_STEP_3G_BUNDLE_LOADER_REGRESSION_LAUNCH_PROBE_CHILD"
)


def _load_tool() -> Any:
    spec = importlib.util.spec_from_file_location(
        "pulsemech_step_3g_candidate_bundle_loader_under_test",
        TOOL,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


M = _load_tool()


def git_blob_sha1(payload: bytes) -> str:
    framed = f"blob {len(payload)}\0".encode("ascii") + payload
    try:
        return hashlib.sha1(framed, usedforsecurity=False).hexdigest()
    except TypeError:
        return hashlib.sha1(framed).hexdigest()


def manifest_entries() -> list[str]:
    entries: list[str] = []
    for raw in TOOLS_TESTS_MANIFEST.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            entries.append(line)
    return entries


def _collected_test_name(item: Any) -> str:
    original = getattr(item, "originalname", None)
    if isinstance(original, str) and original:
        return original
    return str(item.name).split("[", 1)[0]


class _AuthoritativeRegressionContract:
    def __init__(self) -> None:
        self._expected_nodeids: set[str] = set()
        self._completed_nodeids: set[str] = set()
        self._skipped_nodeids: set[str] = set()
        self._collection_validated = False
        self._session_finished = False
        self._contract_satisfied = False

    @property
    def completed_successfully(self) -> bool:
        return self._contract_satisfied

    def pytest_collection_finish(self, session: Any) -> None:
        current = Path(__file__).resolve()
        collected = [
            item
            for item in session.items
            if Path(str(item.path)).resolve() == current
        ]
        observed_names = [str(item.name) for item in collected]
        observed_functions = {_collected_test_name(item) for item in collected}
        duplicate_names = sorted(
            name for name in set(observed_names) if observed_names.count(name) > 1
        )
        missing = sorted(EXPECTED_TESTS - set(observed_names))
        unexpected = sorted(set(observed_names) - EXPECTED_TESTS)
        missing_functions = sorted(EXPECTED_TESTS - observed_functions)
        unexpected_functions = sorted(observed_functions - EXPECTED_TESTS)
        if (
            len(collected) != EXPECTED_COLLECTED_TEST_ITEMS
            or duplicate_names
            or missing
            or unexpected
            or missing_functions
            or unexpected_functions
        ):
            raise pytest.UsageError(
                "authoritative_step_3g_bundle_loader_collection_contract_mismatch: "
                + json.dumps(
                    {
                        "duplicate_names": duplicate_names,
                        "expected_items": EXPECTED_COLLECTED_TEST_ITEMS,
                        "missing_functions": missing_functions,
                        "missing_items": missing,
                        "observed_items": len(collected),
                        "unexpected_functions": unexpected_functions,
                        "unexpected_items": unexpected,
                    },
                    sort_keys=True,
                )
            )
        missing_critical = sorted(CRITICAL_TESTS - set(observed_names))
        if missing_critical:
            raise pytest.UsageError(
                "authoritative_step_3g_bundle_loader_critical_items_missing: "
                + json.dumps(missing_critical)
            )
        self._expected_nodeids = {item.nodeid for item in collected}
        self._collection_validated = True

    def pytest_runtest_logreport(self, report: Any) -> None:
        if report.nodeid not in self._expected_nodeids:
            return
        if report.skipped:
            self._skipped_nodeids.add(report.nodeid)
        if report.when == "call" and (report.passed or report.failed):
            self._completed_nodeids.add(report.nodeid)

    def pytest_sessionfinish(self, session: Any, exitstatus: int) -> None:
        self._session_finished = True
        missing_execution = sorted(
            self._expected_nodeids - self._completed_nodeids
        )
        skipped = sorted(self._skipped_nodeids)
        if (
            self._collection_validated
            and not missing_execution
            and not skipped
            and int(exitstatus) == int(pytest.ExitCode.OK)
        ):
            self._contract_satisfied = True
            return
        terminal = session.config.pluginmanager.get_plugin("terminalreporter")
        detail = json.dumps(
            {
                "collection_validated": self._collection_validated,
                "missing_execution": missing_execution,
                "skipped": skipped,
            },
            sort_keys=True,
        )
        if terminal is not None:
            terminal.write_sep(
                "=",
                "authoritative Step 3G candidate-bundle loader regression failed",
            )
            terminal.write_line(detail)
        if int(exitstatus) == int(pytest.ExitCode.OK):
            session.exitstatus = int(pytest.ExitCode.TESTS_FAILED)


def _run_authoritative_regression(
    *,
    pytest_main: Callable[..., Any] | None = None,
) -> int:
    previous = {
        key: os.environ.get(key)
        for key in _AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS
    }
    try:
        os.environ.pop("PYTEST_ADDOPTS", None)
        os.environ.pop("PYTEST_PLUGINS", None)
        os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        contract = _AuthoritativeRegressionContract()
        runner = pytest.main if pytest_main is None else pytest_main
        result = int(
            runner(
                [
                    "-o",
                    "addopts=",
                    "--noconftest",
                    str(Path(__file__).resolve()),
                ],
                plugins=[contract],
            )
        )
        if result == int(pytest.ExitCode.OK) and not contract.completed_successfully:
            return int(pytest.ExitCode.TESTS_FAILED)
        return result
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

def j(obj: Mapping[str, Any]) -> bytes:
    return M.render_json(obj)
def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()
def z(members: Mapping[str, bytes]) -> bytes:
    s=io.BytesIO()
    with zipfile.ZipFile(s,'w',compression=zipfile.ZIP_STORED,allowZip64=False) as a:
        for name in sorted(members):
            info=zipfile.ZipInfo(name, date_time=(1980,1,1,0,0,0))
            info.create_system=3
            info.external_attr=(stat.S_IFREG|0o444)<<16
            info.compress_type=zipfile.ZIP_STORED
            a.writestr(info,members[name])
    return s.getvalue()

def component(path: str, rev: str, version: str = '0.1.0') -> dict[str, Any]:
    return {'path':path,'sha256':sha(path.encode()),'source_revision':rev,'version':version}

def fixture(workdir: Path) -> dict[str, Any]:
    repository='HKati/pulse-release-gates-0.1'; source_id=12345; source_num=77; attempt=1
    subject_rev='1'*40; provider_rev='2'*40; updated='2026-08-20T10:00:00Z'
    source_key=f'GITHUB_RUN_ID={source_id}|GITHUB_RUN_ATTEMPT={attempt}|GITHUB_WORKFLOW=PULSE CI'
    candidate_id=f'pulse-ci-current-run:{source_id}:{attempt}'
    subj=M.SourceSubject(repository,source_id,source_num,attempt,source_key,subject_rev,updated,candidate_id)

    # Complete package payloads, with required singleton roles and one candidate record.
    base_members={
      'run_metadata_v0.json': j({'run_id':source_id}),
      'artifacts/status.json': j({'status':'ok'}),
      'artifacts/status_baseline.json': j({'status':'baseline'}),
      'artifacts/release_decision_v0.json': j({'decision':'ALLOW'}),
      'artifacts/release_authority_v0.json': j({'authority':'audit'}),
      'artifacts/artifact_provenance_binding_v0.json': j({'binding':'ok'}),
      'artifacts/release_evidence_input_manifest_v0.json': j({'evidence':'ok'}),
      'artifacts/recorded_release_evidence_verifier_v0.json': j({'verified':True}),
      'artifacts/required_gate_evidence_v0.json': j({'gates':[]}),
      'artifacts/recorded_release_candidate_index_v0.json': j({'candidates':['candidate.json']}),
      'artifacts/recorded_release_candidates/candidate.json': j({'candidate':'ok'}),
    }
    inv_rows=[{'path':p,'sha256':sha(b),'size_bytes':len(b)} for p,b in sorted(base_members.items())]
    inventory=j({'files':inv_rows})
    complete_members={'package_digest_inventory_v0.json':inventory, **base_members}
    complete_zip=z(complete_members)
    completeness_doc={'errors':[],'ok':True,'status':'complete','summary':{'checks_failed':0,'checks_passed':3,'checks_total':3}}
    verification_doc={'errors':[],'status':'verified','summary':{'checks_failed':0,'checks_passed':4,'checks_total':4},'verified':True}
    completeness_bytes=j(completeness_doc); verification_bytes=j(verification_doc)
    completeness_zip=z({'release_grade_package_completeness_v1.json':completeness_bytes})
    verification_zip=z({'release_grade_reference_package_verification_v0.json':verification_bytes})

    created='2026-08-20T10:01:00Z'; expires='2026-09-20T10:01:00Z'
    zip_by_key={'complete':complete_zip,'completeness':completeness_zip,'verification':verification_zip}
    selection={}
    for idx,key in enumerate(sorted(M.SOURCE_ARTIFACT_ROLES), start=101):
       name=f"{M.SOURCE_ARTIFACT_NAME_PREFIXES[key]}-{source_id}-{attempt}"
       payload=zip_by_key[key]
       selection[key]={'artifact_id':idx,'artifact_name':name,'created_at':created,'download_file_name':name+'.zip','expires_at':expires,'expected_sha256':sha(payload),'expected_size_bytes':len(payload),'key':key,'role':M.SOURCE_ARTIFACT_ROLES[key]}
    source_selection={'artifacts':[selection[k] for k in sorted(selection)],'authority_boundary':M.EXPECTED_SELECTION_AUTHORITY,'document_type':'pulsemech_compute_current_run_candidate_artifact_selection','ok':True,'schema_version':'pulsemech_compute_current_run_candidate_artifact_selection_v0','source_run_attempt':attempt,'source_run_id':source_id}
    source_resolution={'authority_boundary':M.EXPECTED_SOURCE_RESOLUTION_AUTHORITY,'control_plane':{'repository':repository,'revision':provider_rev,'workflow_ref':f'{repository}/{M.PROVIDER_WORKFLOW_PATH}@refs/heads/main'},'document_type':'pulsemech_compute_current_run_candidate_source_resolution','ok':True,'schema_version':'pulsemech_compute_current_run_candidate_source_resolution_v0','source_run':{'event':'workflow_dispatch','head_branch':'main','html_url':'https://example.invalid/run','release_candidate_id':candidate_id,'repository':repository,'run_attempt':attempt,'run_id':source_id,'run_key':source_key,'run_number':source_num,'source_ref':'refs/heads/main','subject_revision':subject_rev,'updated_utc':updated,'workflow_name':'PULSE CI','workflow_path':M.SOURCE_WORKFLOW_PATH}}

    local_ver={'all_outer_artifact_digests_match_github':True,'all_outer_artifact_sizes_match_github':True,'complete_package_inventory_entries':len(inv_rows),'complete_package_inventory_errors':[],'complete_package_unlisted_members_excluding_inventory':[],'complete_package_zip_members':len(complete_members),'independent_verification_checks_total':4,'independent_verification_errors':[],'independent_verification_status':'verified','independent_verification_verified':True,'structural_completeness_checks_failed':0,'structural_completeness_checks_total':3,'structural_completeness_ok':True,'structural_completeness_status':'complete'}
    gh_rows=[]
    for key in sorted(selection, key=lambda k: selection[k]['download_file_name']):
       s=selection[key]
       gh_rows.append({'artifact_id':s['artifact_id'],'artifact_name':s['artifact_name'],'created_at':s['created_at'],'downloaded_sha256':s['expected_sha256'],'downloaded_size_bytes':s['expected_size_bytes'],'expires_at':s['expires_at'],'file_name':s['download_file_name'],'github_digest_match':True,'github_sha256':s['expected_sha256'],'github_size_match':True,'role':s['role'],'size_bytes':s['expected_size_bytes']})
    preservation={'active_policy_sets':['required','release_required'],'authority_boundary':M.EXPECTED_PRESERVATION_AUTHORITY,'created_utc':updated,'github_artifacts':gh_rows,'llamaguard_evidence_mode':'hosted_full_runtime','local_verification':local_ver,'primary_gate_result':'allow','release_decision':'PROD-PASS','repository':repository,'retention_risk':{'earliest_expiry_utc':expires,'original_github_artifacts_expire':True,'reason_for_preservation':'synthetic regression'},'run_mode':'prod','schema_id':'pulse_ci_release_grade_artifact_preservation_manifest_v0','schema_version':'0.1.0','source_commit':subject_rev,'source_ref':'refs/heads/main','strict_external_evidence':True,'workflow':'PULSE CI','workflow_run_attempt':attempt,'workflow_run_id':source_id,'workflow_run_number':source_num}
    preservation_bytes=j(preservation); readme=b'Synthetic Step 3G candidate carrier.\n'
    sums_entries={'PRESERVATION_MANIFEST_v0.json':preservation_bytes,'README.md':readme}
    for key,s in selection.items(): sums_entries['original-github-artifacts/'+s['download_file_name']]=zip_by_key[key]
    sums=''.join(f"{sha(b)}  {p}\n" for p,b in sorted(sums_entries.items())).encode()
    root_prefix=f'pulsemech-current-run-export-{source_id}-{attempt}-v0/'
    carrier_name=f'pulsemech-current-run-export-{source_id}-{attempt}-v0.zip'
    carrier_members={root_prefix+'PRESERVATION_MANIFEST_v0.json':preservation_bytes,root_prefix+'README.md':readme,root_prefix+'SHA256SUMS':sums}
    for key,s in selection.items(): carrier_members[root_prefix+'original-github-artifacts/'+s['download_file_name']]=zip_by_key[key]
    carrier=z(carrier_members)

    paths={
      'carrier_loader':'tools/load_pulsemech_compute_current_run_export_carrier_v0.py',
      'control_plane_workflow':M.PROVIDER_WORKFLOW_PATH,
      'expectation_builder':'tools/build_pulsemech_compute_current_run_export_expectation_v0.py',
      'expectation_schema':'schemas/pulsemech_compute_current_run_export_expectation_v0.schema.json',
      'expectation_validator':'tools/check_pulsemech_compute_current_run_export_expectation_v0.py',
      'subject_input_producer_core':'tools/pulsemech_compute_subject_input_packet_producer_core_v0.py',
      'subject_input_producer_wrapper':'tools/build_pulsemech_compute_subject_input_packet_current_run_v0.py',
      'subject_input_schema':'schemas/pulsemech_compute_subject_input_packet_v0.schema.json',
      'subject_input_validator':'tools/check_pulsemech_compute_subject_input_packet_v0.py',
    }
    comps={k:component(p,provider_rev,'0' if 'schema' in k else '0.1.0') for k,p in paths.items()}
    carrier_meta={'artifact_payload_mode':'external_carrier','carrier_id':f'carrier:pulsemech/current-run-export/pulse-ci-{source_num}/v0','carrier_kind':'current_run_export_archive','finalized':True,'finalized_utc':updated,'immutable':True,'media_type':'application/zip','path_base':'current_run_export_staging_root','producer':{'ci_workflow_or_job_identity':'Step3F synthetic','producer_id':'producer:pulsemech-current-run-export-carrier-loader-v0','producer_name':'PULSEmech current-run export carrier loader','producer_run_key':source_key,'producer_source':paths['carrier_loader'],'producer_source_revision':provider_rev,'producer_source_sha256':comps['carrier_loader']['sha256'],'producer_version':'0.1.0','production_mode':'current_run_export_carrier_builder'},'provider_binding':None,'root_prefix':root_prefix,'sha256':sha(carrier),'size_bytes':len(carrier),'staged_relative_path':'exports/'+carrier_name}
    policy_sha='3'*64; final_sha=sha(base_members['artifacts/status.json']); decision_sha=sha(base_members['artifacts/release_decision_v0.json'])
    subjdoc={'active_policy_sets':['required','release_required'],'decision':'ALLOW','event_name':'workflow_dispatch','final_status_sha256':final_sha,'materialized_gate_set_sha256':None,'policy_id':'pulse-gate-policy-v0','policy_sha256':policy_sha,'release_candidate_id':candidate_id,'release_decision_sha256':decision_sha,'repository':repository,'run_mode':'prod','source_commit':subject_rev,'source_ref':'refs/heads/main','subject_run_key':source_key,'workflow_name':'PULSE CI','workflow_path':M.SOURCE_WORKFLOW_PATH,'workflow_ref':f'{repository}/{M.SOURCE_WORKFLOW_PATH}@refs/heads/main','workflow_run_attempt':attempt,'workflow_run_id':source_id,'workflow_run_number':source_num}
    authority_sources={'workflow':{'path_or_uri':M.SOURCE_WORKFLOW_PATH,'role':'workflow','sha256':'4'*64,'size_bytes':1,'source_id':'source:workflow','source_revision':subject_rev,'workflow_name':'PULSE CI','workflow_ref':f'{repository}/{M.SOURCE_WORKFLOW_PATH}@refs/heads/main'},'policy':{'path_or_uri':'pulse_gate_policy_v0.yml','policy_id':'pulse-gate-policy-v0','role':'policy','sha256':policy_sha,'size_bytes':1,'source_id':'source:policy','source_revision':subject_rev},'gate_registry':{'path_or_uri':'pulse_gate_registry_v0.yml','registry_id':'pulse-gate-registry-v0','role':'gate_registry','sha256':'5'*64,'size_bytes':1,'source_id':'source:gate-registry','source_revision':subject_rev},'additional_sources':[{'path_or_uri':'policy/external_signers_v1.yml','role':'external_signer_policy','sha256':'6'*64,'size_bytes':1,'source_id':'source:external-signers','source_revision':subject_rev},{'path_or_uri':'PULSE_safe_pack_v0/profiles/external_thresholds.yaml','role':'threshold_policy','sha256':'7'*64,'size_bytes':1,'source_id':'source:thresholds','source_revision':subject_rev}]}
    expectation={'archive_layout':{'complete_package_name':selection['complete']['download_file_name'],'completeness_archive_name':selection['completeness']['download_file_name'],'expected_provider_artifact_count':3,'layout_id':'pulsemech_current_run_export_layout_v0','layout_version':'0.1.0','original_artifacts_prefix':root_prefix+'original-github-artifacts/','outer_prefix':root_prefix,'verification_archive_name':selection['verification']['download_file_name']},'authority_boundary':M.EXPECTED_EXPECTATION_AUTHORITY,'authority_sources':authority_sources,'carrier':carrier_meta,'content_boundary':M.EXPECTED_EXPECTATION_CONTENT,'document_type':'pulsemech_compute_current_run_export_expectation','errors':[],'expectation_identity':{'canonicalization':'json-sort-keys-utf8-newline','expectation_created_utc':updated,'expectation_id':f'current-run-export-expectation:{repository}/{source_id}/{attempt}','expectation_scope':'current_run_export','subject_run_key':source_key},'expectation_producer':{'ci_workflow_or_job_identity':'Step3F synthetic','producer_id':'producer:pulsemech-current-run-export-expectation-builder-v0','producer_name':'PULSEmech current-run export expectation builder','producer_run_key':source_key,'producer_source':paths['expectation_builder'],'producer_source_revision':provider_rev,'producer_source_sha256':comps['expectation_builder']['sha256'],'producer_version':'0.1.0','production_mode':'current_run_expectation_builder'},'ok':True,'packet_contract':{'artifact_payload_mode':'external_carrier','carrier_kind':'current_run_export_archive','packet_scope':'current_run','packet_type':'pulsemech_compute_subject_input_packet','production_mode':'current_run_export','record_status':'observed','schema_version':'pulsemech_compute_subject_input_packet_v0','write_mode':'subject_input_only'},'packet_producer_profile':{'expected_archive_layout_id':'pulsemech_current_run_export_layout_v0','expected_carrier_artifact_payload_mode':'external_carrier','expected_carrier_id_namespace':'pulsemech/current-run-export','expected_carrier_kind':'current_run_export_archive','expected_carrier_media_type':'application/zip','expected_packet_identity_mode':'current-run','expected_packet_scope':'current_run','expected_producer_source_path':paths['subject_input_producer_wrapper'],'expected_production_mode':'current_run_export','expected_repository':repository,'expected_signer_policy_path':'policy/external_signers_v1.yml','expected_source_commit':subject_rev,'expected_subject_run_key':source_key,'profile_id':'pulsemech_current_run_export_candidate_v0'},'record_status':'observed','schema_version':'pulsemech_compute_current_run_export_expectation_v0','subject':subjdoc,'trusted_control_plane':{'checkout_role':'protected_control_plane','components':comps,'repository':repository,'revision':provider_rev,'separate_from_subject_checkout':True,'subject_may_select_revision':False,'trust_mode':'protected_exact_revision'}}

    packet_carrier=M._expected_packet_carrier(carrier_meta)
    carrier_loc=packet_carrier['path_or_uri']; packet_root=packet_carrier['root_prefix']; original=packet_root+'/original-github-artifacts/'
    def kind(path): return M._packet_content_identity(path)
    def aid(path,parent=None): return ('artifact:'+path) if parent is None else parent+'/'+path
    rows=[]
    def add(path,payload,role,parent=None,provider_binding=None):
       k,media=kind(path); a=aid(path,parent)
       if parent is None: display=carrier_loc+'!/'+path
       else: display=next(r['display_path_or_uri'] for r in rows if r['artifact_id']==parent)+'!/'+path
       rows.append({'artifact_id':a,'container_artifact_id':parent,'container_path_verified':True,'content_kind':k,'digest_verified':True,'display_path_or_uri':display,'media_type':media,'member_path':path,'provider_binding':provider_binding,'required_for_analysis':role not in M.NON_ANALYSIS_ROLES,'role':role,'sha256':sha(payload),'size_bytes':len(payload),'size_verified':True})
       return a
    add(packet_root+'/PRESERVATION_MANIFEST_v0.json',preservation_bytes,'preservation_manifest')
    add(packet_root+'/README.md',readme,'preservation_readme')
    add(packet_root+'/SHA256SUMS',sums,'preservation_checksums')
    provider_ids={}
    for key in sorted(selection):
       s=selection[key]; role='complete_package' if key=='complete' else 'provider_artifact_archive'
       binding={'created_utc':s['created_at'],'downloaded_sha256_matches':True,'downloaded_size_matches':True,'expires_utc':s['expires_at'],'provider':'github_actions','provider_artifact_id':str(s['artifact_id']),'provider_artifact_name':s['artifact_name'],'provider_sha256':s['expected_sha256'],'provider_size_bytes':s['expected_size_bytes']}
       provider_ids[key]=add(original+s['download_file_name'],zip_by_key[key],role,provider_binding=binding)
    for p,b in sorted(complete_members.items()):
       role=M.ROLE_BY_PACKAGE_MEMBER.get(p,'candidate_record' if p.startswith('artifacts/recorded_release_candidates/') else 'other')
       add(p,b,role,parent=provider_ids['complete'])
    add('release_grade_package_completeness_v1.json',completeness_bytes,'package_completeness_report',parent=provider_ids['completeness'])
    add('release_grade_reference_package_verification_v0.json',verification_bytes,'independent_verification_report',parent=provider_ids['verification'])
    rows.sort(key=lambda r:r['artifact_id'])
    idx={r['artifact_id']:r for r in rows}
    bindings={}
    for name,role in M.CORE_SINGLETON_ROLE_BINDINGS.items():
       matches=sorted(a for a,r in idx.items() if r['role']==role); assert len(matches)==1,(name,matches); bindings[name]=matches[0]
    for name,roles in M.LIST_ROLE_BINDINGS.items(): bindings[name]=sorted(a for a,r in idx.items() if r['role'] in roles)
    pt,pb=M._validate_packet_provider_bindings(packet_carrier,idx)
    rt,rr,miss,unres=M._validate_packet_role_bindings(bindings,artifacts=idx)
    cov={'artifact_graph_complete':True,'artifacts_total':len(rows),'carrier_binding_complete':True,'coverage_status':'complete','missing_roles':list(miss),'provider_artifacts_bound':pb,'provider_artifacts_total':pt,'role_bindings_complete':not miss and not unres,'role_bindings_resolved':rr,'role_bindings_total':rt,'source_bindings_complete':True,'unresolved_artifact_ids':list(unres)}
    packet={'analysis_boundary':M.EXPECTED_PACKET_ANALYSIS,'artifacts':rows,'authority_boundary':M.EXPECTED_PACKET_AUTHORITY,'authority_sources':M._canonical_packet_authority_sources(authority_sources),'carrier':packet_carrier,'content_boundary':M.EXPECTED_PACKET_CONTENT,'coverage':cov,'errors':[],'ok':True,'packet_identity':{'canonicalization':'json-sort-keys-utf8-newline','carrier_id':carrier_meta['carrier_id'],'packet_created_utc':updated,'packet_id':f'subject-input:{source_id}/{attempt}/v0','packet_scope':'current_run','subject_run_key':source_key},'packet_type':'pulsemech_compute_subject_input_packet','producer':{'ci_workflow_or_job_identity':'Step3F synthetic','producer_id':'pulsemech_compute_subject_input_packet_producer_v0','producer_name':'PULSEmech compute subject-input packet producer','producer_run_key':source_key,'producer_source':paths['subject_input_producer_wrapper'],'producer_source_revision':provider_rev,'producer_source_sha256':comps['subject_input_producer_wrapper']['sha256'],'producer_version':'0.1.0','production_mode':'current_run_export'},'record_status':'observed','role_bindings':bindings,'schema_version':'pulsemech_compute_subject_input_packet_v0','subject':subjdoc}

    files={carrier_name:carrier,'carrier.json':j(carrier_meta),'expectation.json':j(expectation),'subject-input-packet.json':j(packet),'source-run-resolution.json':j(source_resolution),'source-artifact-selection.json':j(source_selection)}
    mf={'authority_boundary':M.EXPECTED_MANIFEST_AUTHORITY,'control_plane_revision':provider_rev,'document_type':'pulsemech_compute_current_run_export_candidate_output_manifest','file_count':6,'files':[{'path':p,'sha256':sha(b),'size_bytes':len(b)} for p,b in sorted(files.items())],'manifest_scope':'all_candidate_files_except_this_manifest','ok':True,'schema_version':'pulsemech_compute_current_run_export_candidate_output_manifest_v0','source_run_attempt':attempt,'source_run_id':source_id,'subject_revision':subject_rev}
    files['candidate-output-manifest.json']=j(mf)
    envelope=z(files)
    envelope_path=workdir/'provider.zip'; envelope_path.write_bytes(envelope); envelope_path.chmod(0o444)
    return locals()


def _provider_namespace(data: Mapping[str, Any], output: Path, envelope_path: Path | None = None) -> argparse.Namespace:
    envelope = Path(envelope_path or data["envelope_path"])
    payload = envelope.read_bytes()
    return argparse.Namespace(
        artifact_envelope=str(envelope),
        repository=data["repository"],
        provider_workflow_name=M.PROVIDER_WORKFLOW_NAME,
        provider_workflow_path=M.PROVIDER_WORKFLOW_PATH,
        provider_workflow_run_id=9001,
        provider_workflow_run_number=90,
        provider_workflow_run_attempt=1,
        provider_workflow_event="workflow_dispatch",
        provider_workflow_head_branch="main",
        provider_workflow_revision=data["provider_rev"],
        provider_workflow_status="completed",
        provider_workflow_conclusion="success",
        provider_workflow_updated_utc="2026-08-20T10:02:00Z",
        provider_artifact_id=999,
        provider_artifact_name=(
            "pulsemech-compute-current-run-export-candidate-"
            f"{data['source_id']}-{data['attempt']}"
        ),
        provider_artifact_created_utc="2026-08-20T10:03:00Z",
        provider_artifact_expires_utc="2026-09-20T10:03:00Z",
        provider_artifact_expired="false",
        provider_artifact_sha256=sha(payload),
        provider_artifact_size_bytes=len(payload),
        producer_run_key="STEP3G_SYNTHETIC=1|ATTEMPT=1",
        ci_workflow_or_job_identity="Step 3G candidate-bundle loader regression",
        control_plane_root=str(ROOT),
        control_plane_revision=data["provider_rev"],
        trusted_git=None,
        output_directory=str(output),
        max_envelope_bytes=10_000_000,
        max_member_bytes=10_000_000,
        max_total_uncompressed_bytes=10_000_000,
    )


def _patch_git_boundaries(monkeypatch: pytest.MonkeyPatch) -> None:
    source_bytes = TOOL.read_bytes()
    binding = M.SourceBinding(
        source_sha256=sha(source_bytes),
        source_bytes=source_bytes,
        source_path=TOOL,
    )
    monkeypatch.setattr(M, "_select_trusted_git", lambda _explicit: Path("/usr/bin/git"))
    monkeypatch.setattr(M, "_require_trusted_git_capability", lambda _path: None)
    monkeypatch.setattr(M, "_verify_git_repository", lambda **_kwargs: None)
    monkeypatch.setattr(M, "_verify_producer_source", lambda **_kwargs: binding)
    monkeypatch.setattr(M, "_reverify_producer_source", lambda **_kwargs: None)


def _write_read_only(path: Path, payload: bytes) -> None:
    path.write_bytes(payload)
    path.chmod(0o444)


def _verify_packet(
    data: Mapping[str, Any],
    tmp_path: Path,
    *,
    packet: dict[str, Any] | None = None,
    expectation: dict[str, Any] | None = None,
    max_total_uncompressed_bytes: int = 10_000_000,
) -> Any:
    stage = tmp_path / ("carrier-stage-" + os.urandom(4).hex())
    stage.mkdir(mode=0o700)
    carrier = stage / data["carrier_name"]
    _write_read_only(carrier, data["carrier"])
    descriptor = os.open(stage, os.O_RDONLY | os.O_DIRECTORY)
    try:
        return M._validate_packet(
            copy.deepcopy(packet if packet is not None else data["packet"]),
            subject=data["subj"],
            carrier_metadata=copy.deepcopy(data["carrier_meta"]),
            expectation=copy.deepcopy(
                expectation if expectation is not None else data["expectation"]
            ),
            provider_revision=data["provider_rev"],
            selection=copy.deepcopy(data["selection"]),
            carrier_directory_descriptor=descriptor,
            carrier_name=data["carrier_name"],
            max_total_uncompressed_bytes=max_total_uncompressed_bytes,
        )
    finally:
        os.close(descriptor)


def _rewrite_envelope(
    data: Mapping[str, Any],
    target: Path,
    *,
    packet: dict[str, Any] | None = None,
) -> Path:
    files = {
        data["carrier_name"]: data["carrier"],
        M.CARRIER_METADATA_NAME: j(data["carrier_meta"]),
        M.EXPECTATION_NAME: j(data["expectation"]),
        M.PACKET_NAME: j(packet if packet is not None else data["packet"]),
        M.SOURCE_RESOLUTION_NAME: j(data["source_resolution"]),
        M.SOURCE_SELECTION_NAME: j(data["source_selection"]),
    }
    manifest = {
        "authority_boundary": M.EXPECTED_MANIFEST_AUTHORITY,
        "control_plane_revision": data["provider_rev"],
        "document_type": (
            "pulsemech_compute_current_run_export_candidate_output_manifest"
        ),
        "file_count": 6,
        "files": [
            {"path": name, "sha256": sha(payload), "size_bytes": len(payload)}
            for name, payload in sorted(files.items())
        ],
        "manifest_scope": "all_candidate_files_except_this_manifest",
        "ok": True,
        "schema_version": (
            "pulsemech_compute_current_run_export_candidate_output_manifest_v0"
        ),
        "source_run_attempt": data["attempt"],
        "source_run_id": data["source_id"],
        "subject_revision": data["subject_rev"],
    }
    files[M.CANDIDATE_MANIFEST_NAME] = j(manifest)
    _write_read_only(target, z(files))
    return target


def _write_staged_file(output: Any, name: str, payload: bytes) -> None:
    descriptor = output.create_file(name)
    try:
        M._write_all(descriptor, payload)
        os.fsync(descriptor)
        os.fchmod(descriptor, 0o444)
    finally:
        os.close(descriptor)


def test_loader_artifact_identity_matches_reviewed_fix() -> None:
    payload = TOOL.read_bytes()
    assert len(payload.splitlines()) == EXPECTED_TOOL_LINES
    assert len(payload) == EXPECTED_TOOL_BYTES
    assert sha(payload) == EXPECTED_TOOL_SHA256
    assert git_blob_sha1(payload) == EXPECTED_TOOL_GIT_BLOB_SHA1
    assert payload.endswith(b"\n")
    assert not payload.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" not in payload
    assert b"\r" not in payload
    assert all(not line.endswith((b" ", b"\t")) for line in payload.splitlines())
    assert M.TOOL_NAME == "load_pulsemech_compute_current_run_export_candidate_bundle_v0"
    assert M.TOOL_VERSION == "0.1.0"
    assert M.PRODUCER_SOURCE_PATH == TOOL.relative_to(ROOT).as_posix()


def test_tools_tests_manifest_registers_loader_regression_exactly_once() -> None:
    entries = manifest_entries()
    assert len(entries) == len(set(entries))
    assert entries.count(TEST_RELATIVE_PATH) == 1
    index = entries.index(TEST_RELATIVE_PATH)
    assert entries[index - 1] == PREVIOUS_COMPUTE_REGRESSION
    assert index < entries.index(FOLLOWING_COMPUTE_ANCHOR)


def test_authoritative_launcher_sanitizes_pytest_environment_and_requires_completed_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inherited = {
        "PYTEST_ADDOPTS": "--help",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "0",
        "PYTEST_PLUGINS": "must_not_import",
    }
    for key, value in inherited.items():
        monkeypatch.setenv(key, value)
    observed: dict[str, Any] = {}

    def successful_main(arguments: list[str], *, plugins: list[Any]) -> int:
        observed["arguments"] = list(arguments)
        observed["environment"] = {
            key: os.environ.get(key)
            for key in _AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS
        }
        contract = plugins[0]
        assert isinstance(contract, _AuthoritativeRegressionContract)
        contract._collection_validated = True
        contract._session_finished = True
        contract._contract_satisfied = True
        return int(pytest.ExitCode.OK)

    assert _run_authoritative_regression(pytest_main=successful_main) == 0
    assert observed["arguments"] == [
        "-o",
        "addopts=",
        "--noconftest",
        str(Path(__file__).resolve()),
    ]
    assert observed["environment"] == {
        "PYTEST_ADDOPTS": None,
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTEST_PLUGINS": None,
    }
    assert {
        key: os.environ.get(key)
        for key in _AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS
    } == inherited


def test_direct_authoritative_launcher_rejects_terminal_pytest_early_exit() -> None:
    if os.environ.get(_AUTHORITATIVE_LAUNCH_PROBE_CHILD) == "1":
        assert "PYTEST_ADDOPTS" not in os.environ
        assert "PYTEST_PLUGINS" not in os.environ
        assert os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") == "1"
        return

    environment = dict(os.environ)
    environment.update(
        {
            _AUTHORITATIVE_LAUNCH_PROBE_CHILD: "1",
            "PYTEST_ADDOPTS": "--help",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "0",
            "PYTEST_PLUGINS": "module_that_must_not_be_imported",
        }
    )
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve())],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=environment,
        timeout=240,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert result.stderr == b""
    expected = str(EXPECTED_COLLECTED_TEST_ITEMS).encode("ascii")
    assert b"collected " + expected + b" items" in result.stdout
    assert expected + b" passed" in result.stdout
    assert b"usage: pytest" not in result.stdout.lower()


def test_direct_nonisolated_execution_fails_before_argument_parsing() -> None:
    result = subprocess.run(
        [sys.executable, str(TOOL), "--help"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    assert result.returncode == 2
    assert result.stdout == b""
    diagnostic = json.loads(result.stderr.decode("utf-8"))
    assert diagnostic["authority_effect"] == "none"
    assert diagnostic["exit_kind"] == "python_runtime_boundary_error"
    assert diagnostic["ok"] is False


def test_isolated_help_exposes_complete_cli_surface() -> None:
    result = subprocess.run(
        [sys.executable, "-I", str(TOOL), "--help"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    help_text = result.stdout.decode("utf-8")
    for option in (
        "--artifact-envelope",
        "--provider-workflow-run-id",
        "--provider-artifact-id",
        "--provider-artifact-sha256",
        "--control-plane-revision",
        "--output-directory",
        "--max-total-uncompressed-bytes",
    ):
        assert option in help_text


def test_failure_diagnostic_and_authority_boundary_are_non_authoritative() -> None:
    diagnostic = M.make_failure_diagnostic(
        error="synthetic_failure",
        exit_kind="synthetic_boundary_error",
    )
    assert diagnostic == {
        "authority_effect": "none",
        "document_type": M.DOCUMENT_TYPE,
        "errors": ["synthetic_failure"],
        "exit_kind": "synthetic_boundary_error",
        "ok": False,
        "tool": M.TOOL_NAME,
        "tool_version": M.TOOL_VERSION,
    }
    assert M.CLOSED_AUTHORITY_BOUNDARY["candidate_only"] is True
    assert M.CLOSED_AUTHORITY_BOUNDARY["non_active"] is True
    assert M.CLOSED_AUTHORITY_BOUNDARY["provider_binding_only"] is True
    assert M.CLOSED_AUTHORITY_BOUNDARY["activates_compute_gate"] is False
    assert M.CLOSED_AUTHORITY_BOUNDARY["changes_release_authority"] is False


def test_provider_artifact_metadata_binding_is_exact(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    args = _provider_namespace(data, tmp_path / "unused")
    provider = M._provider_artifact_from_args(args)
    assert provider.artifact_sha256 == sha(data["envelope"])
    assert provider.artifact_size_bytes == len(data["envelope"])
    assert provider.source_run_id_from_name == data["source_id"]
    assert provider.source_run_attempt_from_name == data["attempt"]
    args.provider_artifact_expired = "true"
    with pytest.raises(M.BundleError, match="provider_artifact_expired_or_unknown"):
        M._provider_artifact_from_args(args)


def test_candidate_manifest_closes_exact_member_surface(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    provider = M._provider_artifact_from_args(
        _provider_namespace(data, tmp_path / "unused")
    )
    declared, carrier_name = M._validate_candidate_manifest(
        copy.deepcopy(data["mf"]),
        provider=provider,
        outer_member_names=set(data["files"]),
    )
    assert carrier_name == data["carrier_name"]
    assert set(declared) == set(data["files"]) - {M.CANDIDATE_MANIFEST_NAME}
    with pytest.raises(M.BundleError, match="provider_envelope_member_set_mismatch"):
        M._validate_candidate_manifest(
            copy.deepcopy(data["mf"]),
            provider=provider,
            outer_member_names=set(data["files"]) | {"unexpected.json"},
        )


def test_outer_archive_rejects_unsafe_flat_members() -> None:
    payload = z({"../escape.json": b"{}\n"})
    with zipfile.ZipFile(io.BytesIO(payload), "r") as archive:
        with pytest.raises(M.BundleError):
            M._zip_info_map(
                archive,
                label="unsafe_outer",
                flat=True,
                max_members=16,
                max_member_bytes=1024,
                max_total_uncompressed_bytes=4096,
            )


def test_packet_artifact_graph_resolves_exact_carrier_bytes(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    verification = _verify_packet(data, tmp_path)
    assert verification.artifacts_total == len(data["packet"]["artifacts"])
    assert verification.provider_artifacts_total == 3
    assert verification.provider_artifacts_bound == 3
    assert verification.role_bindings_total == 18
    assert verification.role_bindings_resolved == 18
    assert verification.missing_roles == ()
    assert verification.unresolved_artifact_ids == ()
    assert verification.archive_members[None]
    assert verification.retained_artifact_bytes[
        verification.role_bindings["package_inventory"]
    ] == data["inventory"]


def test_packet_artifact_digest_forgery_is_rejected(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    packet = copy.deepcopy(data["packet"])
    target = next(
        row for row in packet["artifacts"] if row["role"] == "final_status"
    )
    target["sha256"] = "0" * 64
    with pytest.raises(M.BundleError, match="packet_artifact_identity_mismatch"):
        _verify_packet(data, tmp_path, packet=packet)


def test_packet_unresolved_role_binding_is_rejected(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    packet = copy.deepcopy(data["packet"])
    packet["role_bindings"]["final_status"] = "artifact:missing/status.json"
    with pytest.raises(M.BundleError):
        _verify_packet(data, tmp_path, packet=packet)


def test_packet_semantically_wrong_role_binding_is_rejected(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    packet = copy.deepcopy(data["packet"])
    packet["role_bindings"]["final_status"] = packet["role_bindings"][
        "release_decision"
    ]
    with pytest.raises(M.BundleError, match="packet_role_binding_semantic_mismatch"):
        _verify_packet(data, tmp_path, packet=packet)


def test_packet_forged_coverage_is_rejected(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    packet = copy.deepcopy(data["packet"])
    packet["coverage"]["artifacts_total"] += 1
    with pytest.raises(
        M.BundleError,
        match="packet_coverage_not_derived_from_verified_graph",
    ):
        _verify_packet(data, tmp_path, packet=packet)


def test_packet_provider_binding_drift_is_rejected(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    packet = copy.deepcopy(data["packet"])
    target = next(
        row
        for row in packet["artifacts"]
        if row["provider_binding"] is not None
    )
    target["provider_binding"]["provider_sha256"] = "0" * 64
    with pytest.raises(M.BundleError, match="provider_binding_.*identity_mismatch"):
        _verify_packet(data, tmp_path, packet=packet)


def test_carrier_expectation_and_packet_producer_digests_are_bound(
    tmp_path: Path,
) -> None:
    data = fixture(tmp_path)
    expectation = copy.deepcopy(data["expectation"])
    expectation["trusted_control_plane"]["components"]["carrier_loader"][
        "sha256"
    ] = "0" * 64
    with pytest.raises(M.BundleError, match="carrier_producer_component_digest_mismatch"):
        M._validate_expectation(
            expectation,
            subject=data["subj"],
            carrier_metadata=data["carrier_meta"],
            provider_revision=data["provider_rev"],
            selection=data["selection"],
        )

    packet = copy.deepcopy(data["packet"])
    packet["producer"]["producer_source_sha256"] = "0" * 64
    with pytest.raises(M.BundleError, match="packet_producer_component_digest_mismatch"):
        _verify_packet(data, tmp_path, packet=packet)


def test_preservation_local_verification_is_derived(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    verification = _verify_packet(data, tmp_path)
    assert M._derive_preservation_local_verification(verification) == data[
        "local_ver"
    ]


def test_negative_structural_completeness_is_rejected(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    verification = _verify_packet(data, tmp_path)
    retained = dict(verification.retained_artifact_bytes)
    artifact_id = verification.role_bindings["package_completeness_report"]
    retained[artifact_id] = j(
        {
            "errors": ["synthetic failure"],
            "ok": False,
            "status": "failed",
            "summary": {
                "checks_failed": 1,
                "checks_passed": 2,
                "checks_total": 3,
            },
        }
    )
    mutated = dataclasses.replace(
        verification,
        retained_artifact_bytes=retained,
    )
    with pytest.raises(M.BundleError, match="package_completeness_errors_present"):
        M._derive_preservation_local_verification(mutated)


def test_negative_independent_verification_is_rejected(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    verification = _verify_packet(data, tmp_path)
    retained = dict(verification.retained_artifact_bytes)
    artifact_id = verification.role_bindings["independent_verification_report"]
    retained[artifact_id] = j(
        {
            "errors": ["synthetic verification error"],
            "status": "failed",
            "summary": {
                "checks_failed": 1,
                "checks_passed": 3,
                "checks_total": 4,
            },
            "verified": False,
        }
    )
    mutated = dataclasses.replace(
        verification,
        retained_artifact_bytes=retained,
    )
    with pytest.raises(M.BundleError, match="independent_verification_errors_present"):
        M._derive_preservation_local_verification(mutated)


def test_preservation_local_verification_mismatch_is_rejected(
    tmp_path: Path,
) -> None:
    data = fixture(tmp_path)
    verification = _verify_packet(data, tmp_path)
    manifest = copy.deepcopy(data["preservation"])
    manifest["local_verification"]["structural_completeness_ok"] = False
    with pytest.raises(
        M.BundleError,
        match="preservation_manifest_local_verification_mismatch",
    ):
        M._validate_preservation_manifest(
            manifest,
            subject=data["subj"],
            selection=data["selection"],
            packet_verification=verification,
        )


def test_shared_nested_artifact_budget_fails_closed(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    with pytest.raises(M.BundleError, match="retained_byte_budget_exceeded"):
        _verify_packet(
            data,
            tmp_path,
            max_total_uncompressed_bytes=64,
        )


def test_output_parent_must_be_exclusively_owned(tmp_path: Path) -> None:
    parent = tmp_path / "writable-parent"
    parent.mkdir(mode=0o700)
    parent.chmod(0o770)
    try:
        with pytest.raises(M.BundleError, match="output_parent_not_exclusively_owned"):
            M.StagedOutputDirectory.create(parent / "final")
    finally:
        parent.chmod(0o700)


def test_output_files_are_created_relative_to_directory_descriptor(
    tmp_path: Path,
) -> None:
    tmp_path.chmod(0o700)
    output = M.StagedOutputDirectory.create(tmp_path / "final")
    try:
        payload = b"descriptor-bound\n"
        _write_staged_file(output, "member.txt", payload)
        assert "member.txt" in output.list_names()
        with M.OpenedInput.open_at(
            output.directory_descriptor,
            "member.txt",
            label="descriptor_bound_member",
            max_bytes=len(payload),
            require_read_only=True,
            require_single_link=True,
        ) as opened:
            assert opened.read_bytes(
                label="descriptor_bound_member",
                max_bytes=len(payload),
            ) == payload
    finally:
        output.cleanup()


def test_temporary_directory_path_replacement_cannot_redirect_writes(
    tmp_path: Path,
) -> None:
    tmp_path.chmod(0o700)
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o700)
    output = M.StagedOutputDirectory.create(tmp_path / "final")
    backup_name = output.temporary_name + ".moved"
    symlink_path = tmp_path / output.temporary_name
    backup_path = tmp_path / backup_name
    try:
        os.rename(
            output.temporary_name,
            backup_name,
            src_dir_fd=output.parent_descriptor,
            dst_dir_fd=output.parent_descriptor,
        )
        os.symlink(
            outside,
            output.temporary_name,
            dir_fd=output.parent_descriptor,
        )
        descriptor = output.create_file("member.txt")
        try:
            M._write_all(descriptor, b"descriptor target\n")
            os.fsync(descriptor)
            os.fchmod(descriptor, 0o444)
        finally:
            os.close(descriptor)
        assert not (outside / "member.txt").exists()
        assert (backup_path / "member.txt").read_bytes() == b"descriptor target\n"
        with pytest.raises(M.BundleError, match="output_directory_name_identity_changed"):
            output.publish()
    finally:
        output.cleanup()
        if symlink_path.is_symlink():
            symlink_path.unlink()
        member = backup_path / "member.txt"
        if member.exists():
            member.chmod(0o600)
            member.unlink()
        if backup_path.exists():
            backup_path.rmdir()


def test_materialized_output_rejects_file_identity_replacement(
    tmp_path: Path,
) -> None:
    tmp_path.chmod(0o700)
    output = M.StagedOutputDirectory.create(tmp_path / "final")
    replacement_name = ".replacement"
    try:
        expected = b"expected\n"
        report = j({"ok": True})
        _write_staged_file(output, "member.txt", expected)
        _write_staged_file(output, M.INTAKE_REPORT_NAME, report)
        descriptor = os.open(
            replacement_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=output.directory_descriptor,
        )
        try:
            M._write_all(descriptor, b"attacker\n")
            os.fsync(descriptor)
            os.fchmod(descriptor, 0o444)
        finally:
            os.close(descriptor)
        os.rename(
            replacement_name,
            "member.txt",
            src_dir_fd=output.directory_descriptor,
            dst_dir_fd=output.directory_descriptor,
        )
        with pytest.raises(M.BundleError, match="published_output_identity_mismatch"):
            M._verify_materialized_output(
                output,
                expected_files={"member.txt": (sha(expected), len(expected))},
                report_bytes=report,
            )
    finally:
        output.cleanup()
        final_temp = tmp_path / output.temporary_name
        if final_temp.exists() and final_temp.is_dir():
            for child in final_temp.iterdir():
                child.chmod(0o600)
                child.unlink()
            final_temp.rmdir()


def test_build_success_is_deterministic_and_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path.chmod(0o700)
    data = fixture(tmp_path)
    _patch_git_boundaries(monkeypatch)
    first = tmp_path / "out-first"
    second = tmp_path / "out-second"
    rendered_first = M._build(_provider_namespace(data, first))
    rendered_second = M._build(_provider_namespace(data, second))
    assert rendered_first == rendered_second
    report = json.loads(rendered_first.decode("utf-8"))
    assert report["ok"] is True
    assert report["record_status"] == "observed"
    assert report["authority_boundary"] == M.CLOSED_AUTHORITY_BOUNDARY
    assert report["inner_carrier_verification"][
        "packet_artifact_graph_verified"
    ] is True
    assert report["inner_carrier_verification"][
        "source_package_semantics_verified"
    ] is True
    for directory in (first, second):
        assert directory.is_dir()
        assert stat.S_IMODE(directory.stat().st_mode) == 0o555
        assert len(list(directory.iterdir())) == 8
        for child in directory.iterdir():
            assert child.is_file() and not child.is_symlink()
            assert stat.S_IMODE(child.stat().st_mode) == 0o444


def test_build_failure_leaves_no_partial_or_stale_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path.chmod(0o700)
    data = fixture(tmp_path)
    packet = copy.deepcopy(data["packet"])
    target = next(
        row for row in packet["artifacts"] if row["role"] == "final_status"
    )
    target["sha256"] = "0" * 64
    forged = _rewrite_envelope(data, tmp_path / "forged.zip", packet=packet)
    _patch_git_boundaries(monkeypatch)
    output = tmp_path / "failed-output"
    with pytest.raises(M.BundleError, match="packet_artifact_identity_mismatch"):
        M._build(_provider_namespace(data, output, forged))
    assert not output.exists()
    assert not any(
        path.name.startswith(".failed-output.") for path in tmp_path.iterdir()
    )


def test_postpublication_reverification_failure_removes_owned_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path.chmod(0o700)
    data = fixture(tmp_path)
    _patch_git_boundaries(monkeypatch)
    calls = 0

    def fail_after_publish(**_kwargs: Any) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise M.BundleError(
                "synthetic_postpublication_source_drift",
                exit_kind="trusted_git_error",
            )

    monkeypatch.setattr(M, "_reverify_producer_source", fail_after_publish)
    output = tmp_path / "postpublish-output"
    with pytest.raises(M.BundleError, match="synthetic_postpublication_source_drift"):
        M._build(_provider_namespace(data, output))
    assert calls == 2
    assert not output.exists()


def test_intake_does_not_create_authority_or_transition_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path.chmod(0o700)
    data = fixture(tmp_path)
    _patch_git_boundaries(monkeypatch)
    output = tmp_path / "non-authority-output"
    report = json.loads(M._build(_provider_namespace(data, output)).decode("utf-8"))
    boundary = report["authority_boundary"]
    assert boundary == M.CLOSED_AUTHORITY_BOUNDARY
    assert boundary["materializes_candidate_gate_state"] is False
    assert boundary["produces_transition_relation"] is False
    assert boundary["creates_compute_budget"] is False
    assert boundary["creates_gate_result"] is False
    assert boundary["creates_release_decision"] is False
    assert boundary["changes_release_authority"] is False
    source = TOOL.read_text(encoding="utf-8")
    for forbidden in (
        "check_gates.py",
        "build_pulsemech_compute_planned_observed_relation_v0.py",
        "fold_pulsemech_compute_planned_observed_relation_into_status_v0.py",
    ):
        assert forbidden not in source


if __name__ == "__main__":
    raise SystemExit(_run_authoritative_regression())
