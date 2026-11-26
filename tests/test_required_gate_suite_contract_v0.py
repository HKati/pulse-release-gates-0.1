#!/usr/bin/env python3
"""Offline structural suite-contract regressions with explicitly synthetic data.

The two positive selections are frozen by independent constants below. Negative
tests may deliberately re-pin a controlled selection to reach deeper structural
guards; that is a test operation, never a production trust-discovery mechanism.
No subject, operator, model, collector, analyzer or external service is executed.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_REL = 'tests/fixtures/required_gate_suite_contract_v0'
FIXTURES = ROOT / FIXTURE_REL
TOOL_REL = 'tools/check_required_gate_suite_contract_v0.py'
TOOL = ROOT / TOOL_REL
COMPLETE_SELECTION_SHA256 = 'd75577f91cc7c63984a4a9e7ad0cb70c17bc00c094b86483bda016f7eacba9b4'
UNRESOLVED_SELECTION_SHA256 = 'de84befb3090426026b899c28e151b26a40dae4cc6c5d3b0446a15b39c552b9a'
FIXTURE_FILES = {
    'complete.json', 'unresolved.json', 'missing_obligation.json',
    'duplicate_case.json', 'substituted_binding.json',
    'complete_selection.json', 'unresolved_selection.json',
    'synthetic_source.txt', 'synthetic_protocol.json', 'synthetic_operator.txt',
    'synthetic_comparison.txt', 'synthetic_privacy.txt', 'synthetic_reconstruction.txt',
    'baseline_input.json', 'variant_input.json', 'subject_packet.json', 'runtime_packet.json',
}

spec = importlib.util.spec_from_file_location('required_gate_suite_contract_under_test', TOOL)
assert spec is not None and spec.loader is not None
C = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = C
spec.loader.exec_module(C)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode()


def load(path):
    return json.loads(path.read_bytes())


def boundary(report):
    assert report['execution_ready'] is False
    assert report['execution_authorized'] is False
    assert report['semantic_verification'] == 'not_run'
    assert report['packet_semantics_verified'] is False
    assert report['metric_pass'] is None
    assert report['production_gate_eligible'] is False
    assert report['authority_effect'] == 'none'
    assert report['anchor_authentication'] == 'not_established'


class Case:
    """Copy exactly the frozen selection's local inputs into an isolated root."""
    def __init__(self, tmp_path, draft=False):
        self.root = tmp_path / 'selected-root'
        stem = 'unresolved' if draft else 'complete'
        self.selection_rel = FIXTURE_REL + '/' + stem + '_selection.json'
        self.selection_path = self.root / self.selection_rel
        original = (ROOT / self.selection_rel).read_bytes()
        self.pin = UNRESOLVED_SELECTION_SHA256 if draft else COMPLETE_SELECTION_SHA256
        assert digest(original) == self.pin, 'positive selection fixture changed without reviewed pin update'
        self.selection = json.loads(original)
        references = [self.selection['contract'], *self.selection['bindings'].values(), *self.selection['inputs']]
        for ref in references:
            if ref is None:
                continue
            path = self.root / ref['path']
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = (ROOT / ref['path']).read_bytes()
            assert digest(raw) == ref['sha256'] and len(raw) == ref['size_bytes'], ref['path']
            path.write_bytes(raw)
        self.selection_path.parent.mkdir(parents=True, exist_ok=True)
        self.selection_path.write_bytes(original)
        self.contract_path = self.root / self.selection['contract']['path']
        self.contract = load(self.contract_path)

    def select_current_contract(self, raw=None):
        """Test-only re-selection; never used to establish either positive pin."""
        raw = encoded(self.contract) if raw is None else raw
        self.contract_path.write_bytes(raw)
        self.selection['contract'].update(sha256=digest(raw), size_bytes=len(raw))
        return self.select_current_selection()

    def select_current_selection(self, raw=None):
        raw = encoded(self.selection) if raw is None else raw
        self.selection_path.write_bytes(raw)
        self.pin = digest(raw)
        return self.pin

    def file(self, role):
        return self.root / self.selection['bindings'][role]['path']

    def bind_bytes(self, role, raw):
        self.file(role).write_bytes(raw)
        self.selection['bindings'][role].update(sha256=digest(raw), size_bytes=len(raw))
        if role in self.contract['binding_sha256']:
            self.contract['binding_sha256'][role] = digest(raw)
        self.select_current_contract()

    def bind_json(self, role, value):
        self.bind_bytes(role, encoded(value))

    def sync_protocol_rosters(self):
        protocol = load(self.file('protocol'))
        protocol['cases'] = copy.deepcopy(self.contract['cases'])
        protocol['expected_occurrences'] = [
            {k: occurrence[k] for k in ('occurrence_id', 'case_id')}
            for occurrence in self.contract['occurrences']]
        protocol['obligations'] = copy.deepcopy(self.contract['obligations'])
        self.bind_json('protocol', protocol)

    def check(self):
        return C.validate_contract(self.contract_path, self.selection_path, self.pin, self.root)

    def reject(self):
        with pytest.raises(C.ContractError) as caught:
            self.check()
        assert isinstance(caught.value.code, str) and caught.value.code

    def cli(self, *extra, pin=None, timeout=15):
        return subprocess.run([sys.executable, str(TOOL), '--contract', str(self.contract_path),
            '--selection', str(self.selection_path), '--selection-sha256', self.pin if pin is None else pin,
            '--root', str(self.root), *map(str, extra)], capture_output=True, timeout=timeout)


def test_fixture_inventory_and_positive_selection_pins_are_closed():
    assert {p.name for p in FIXTURES.iterdir() if p.is_file()} == FIXTURE_FILES
    assert digest((FIXTURES / 'complete_selection.json').read_bytes()) == COMPLETE_SELECTION_SHA256
    assert digest((FIXTURES / 'unresolved_selection.json').read_bytes()) == UNRESOLVED_SELECTION_SHA256
    assert load(FIXTURES / 'complete.json')['selected_gate_ids'] == ['effect_present', 'psf_idempotence_ok']
    assert (FIXTURES / 'baseline_input.json').read_bytes() != (FIXTURES / 'variant_input.json').read_bytes()


def test_complete_shared_observation_declaration_has_no_execution_or_metric_authority(tmp_path):
    case = Case(tmp_path)
    report = case.check()
    assert report['valid'] is True and report['declaration_complete'] is True
    assert report['declaration_state'] == 'complete' and report['origin'] == 'synthetic_fixture'
    assert report['unresolved_decisions'] == []
    assert case.contract['obligations'][0]['occurrence_ids'] == case.contract['obligations'][1]['occurrence_ids']
    boundary(report)
    assert 'gate_results' not in report and 'release_decision' not in report


def test_unresolved_draft_is_valid_as_declaration_and_remains_unready(tmp_path):
    report = Case(tmp_path, draft=True).check()
    assert report['valid'] is True and report['declaration_complete'] is False
    assert report['declaration_state'] == 'draft' and report['origin'] == 'synthetic_fixture'
    assert set(report['unresolved_decisions']) == {'protocol', 'subject', 'operator', 'cases',
        'comparison', 'privacy_retention', 'observation_mapping', 'runtime_evidence'}
    boundary(report)


def test_example_packets_are_schema_valid_without_claiming_full_packet_acceptance():
    for filename, schema_name in [('subject_packet.json', 'pulsemech_compute_subject_input_packet_v0'),
                                  ('runtime_packet.json', 'pulsemech_compute_runtime_observation_packet_v0')]:
        schema = load(ROOT / 'schemas' / (schema_name + '.schema.json'))
        value = load(FIXTURES / filename)
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)
        assert value['record_status'] == 'example' and value['coverage']['coverage_status'] == 'partial'
    assert load(FIXTURES / 'subject_packet.json')['fixture_provenance']['source_data_status'] == 'synthetic'
    runtime = load(FIXTURES / 'runtime_packet.json')
    assert runtime['external_calls'] == runtime['model_inferences'] == []
    assert all(e['result']['lifecycle_status'] == 'unknown' for e in runtime['executions'])


@pytest.mark.parametrize('filename', ['missing_obligation.json', 'duplicate_case.json', 'substituted_binding.json'])
def test_frozen_negative_declarations_are_rejected_against_selected_protocol(tmp_path, filename):
    case = Case(tmp_path)
    case.contract = load(FIXTURES / filename)
    case.select_current_contract()
    case.reject()


@pytest.mark.parametrize('fault', [
    'wrong_version', 'unknown_field', 'raw_payload', 'promoted_authority', 'claimed_ready',
    'claimed_pass', 'invalid_origin', 'invalid_state', 'source_repository', 'source_commit',
    'empty_gates', 'duplicate_gate', 'unknown_gate', 'omitted_gate', 'null_material',
    'changed_material_digest', 'complete_with_unresolved', 'empty_cases', 'empty_occurrences',
    'empty_obligations', 'missing_occurrence', 'duplicate_occurrence', 'reused_execution',
    'unknown_case_reference', 'unknown_state_reference', 'wrong_packet', 'duplicate_obligation',
    'omitted_obligation', 'unknown_obligation_gate', 'unknown_obligation_case',
    'unknown_obligation_occurrence', 'empty_obligation_cases', 'empty_obligation_occurrences'])
def test_contract_rejects_substitution_vacuity_and_self_certification(tmp_path, fault):
    case = Case(tmp_path); d = case.contract
    if fault == 'wrong_version': d['record_type'] = 'required_gate_suite_contract_v999'
    elif fault == 'unknown_field': d['unreviewed'] = True
    elif fault == 'raw_payload': d['cases'][0]['raw_prompt'] = 'PRIVATE_B1_SENTINEL'
    elif fault == 'promoted_authority': d['authority_effect'] = 'release'
    elif fault == 'claimed_ready': d['execution_ready'] = True
    elif fault == 'claimed_pass': d['metric_pass'] = True
    elif fault == 'invalid_origin': d['origin'] = 'authenticated_execution'
    elif fault == 'invalid_state': d['declaration_state'] = 'ready'
    elif fault == 'source_repository': d['source']['repository'] = 'other/subject'
    elif fault == 'source_commit': d['source']['commit'] = '2' * 40
    elif fault == 'empty_gates': d['selected_gate_ids'] = []
    elif fault == 'duplicate_gate': d['selected_gate_ids'].append(d['selected_gate_ids'][0])
    elif fault == 'unknown_gate': d['selected_gate_ids'][0] = 'unrecognized_gate'
    elif fault == 'omitted_gate': d['selected_gate_ids'].pop()
    elif fault == 'null_material': d['binding_sha256']['comparison'] = None
    elif fault == 'changed_material_digest': d['binding_sha256']['operator'] = '0' * 64
    elif fault == 'complete_with_unresolved': d['unresolved_decisions'] = ['operator']
    elif fault == 'empty_cases': d['cases'] = []
    elif fault == 'empty_occurrences': d['occurrences'] = []
    elif fault == 'empty_obligations': d['obligations'] = []
    elif fault == 'missing_occurrence': d['occurrences'].pop()
    elif fault == 'duplicate_occurrence': d['occurrences'].append(copy.deepcopy(d['occurrences'][0]))
    elif fault == 'reused_execution': d['occurrences'][1]['execution_id'] = d['occurrences'][0]['execution_id']
    elif fault == 'unknown_case_reference': d['occurrences'][0]['case_id'] = 'absent'
    elif fault == 'unknown_state_reference': d['occurrences'][0]['input_state_ids'] = ['state:absent']
    elif fault == 'wrong_packet': d['occurrences'][0]['packet_id'] = 'runtime-observation:other'
    elif fault == 'duplicate_obligation': d['obligations'].append(copy.deepcopy(d['obligations'][0]))
    elif fault == 'omitted_obligation': d['obligations'].pop()
    elif fault == 'unknown_obligation_gate': d['obligations'][0]['gate_id'] = 'q3_fairness_ok'
    elif fault == 'unknown_obligation_case': d['obligations'][0]['case_ids'] = ['absent']
    elif fault == 'unknown_obligation_occurrence': d['obligations'][0]['occurrence_ids'] = ['absent']
    elif fault == 'empty_obligation_cases': d['obligations'][0]['case_ids'] = []
    else: d['obligations'][0]['occurrence_ids'] = []
    case.select_current_contract()
    case.reject()


@pytest.mark.parametrize('fault', ['self_baseline', 'missing_baseline', 'baseline_is_variant',
    'repeated_baseline_bytes', 'gate_without_obligation', 'unconsumed_case', 'unconsumed_input'])
def test_even_independently_repinned_protocol_cannot_make_invalid_structure_complete(tmp_path, fault):
    case = Case(tmp_path); d = case.contract
    if fault == 'self_baseline': d['cases'][1]['baseline_case_id'] = 'variant'
    elif fault == 'missing_baseline': d['cases'][1]['baseline_case_id'] = 'missing'
    elif fault == 'baseline_is_variant':
        d['cases'][0].update(baseline_case_id='variant', variant_id='second-variant')
    elif fault == 'repeated_baseline_bytes':
        baseline = copy.deepcopy(case.selection['inputs'][0])
        baseline['input_id'] = 'variant-input'
        case.selection['inputs'][1] = baseline
    elif fault == 'gate_without_obligation': d['obligations'].pop()
    elif fault == 'unconsumed_case':
        d['cases'].append({'case_id': 'unused', 'input_id': 'baseline-input', 'baseline_case_id': None, 'variant_id': None})
    else:
        extra = copy.deepcopy(case.selection['inputs'][0]); extra['input_id'] = 'unused-input'
        case.selection['inputs'].append(extra)
    case.sync_protocol_rosters()
    case.reject()


@pytest.mark.parametrize('fault', ['empty_unresolved', 'missing_null_decision', 'promoted_complete',
    'unmapped_occurrence', 'unknown_decision', 'duplicated_decision'])
def test_draft_cannot_hide_unresolved_decisions_or_self_promote(tmp_path, fault):
    case = Case(tmp_path, draft=True); d = case.contract
    if fault == 'empty_unresolved': d['unresolved_decisions'] = []
    elif fault == 'missing_null_decision': d['unresolved_decisions'].remove('operator')
    elif fault == 'promoted_complete': d['declaration_state'] = 'complete'
    elif fault == 'unmapped_occurrence': d['occurrences'] = load(FIXTURES / 'complete.json')['occurrences']
    elif fault == 'unknown_decision': d['unresolved_decisions'].append('auto_authorize')
    else: d['unresolved_decisions'].append('operator')
    case.select_current_contract()
    case.reject()


@pytest.mark.parametrize('fault', ['packet_run', 'source_commit', 'subject_run', 'candidate',
    'run_id', 'attempt', 'execution_run', 'execution_subject_run', 'post_run_binding',
    'incomplete_binding', 'observer_scope', 'observer_role', 'observer_kind',
    'wrong_operator_path', 'wrong_operator_hash', 'wrong_operator_revision',
    'unknown_operator_kind', 'partial_operator_identity', 'missing_execution',
    'duplicate_execution', 'missing_state', 'duplicate_state', 'changed_input_edges',
    'changed_output_edges', 'input_digest', 'input_size', 'input_not_exact',
    'state_run', 'state_candidate', 'wrong_output_producer', 'raw_private_payload'])
def test_runtime_packet_substitutions_and_consumption_changes_reject(tmp_path, fault):
    case = Case(tmp_path); d = load(case.file('runtime_packet'))
    execution = d['executions'][0]; state = d['state_observations'][0]
    if fault == 'packet_run': d['packet_identity']['subject_run_key'] = 'other'
    elif fault == 'source_commit': d['subject']['source_commit'] = '2' * 40
    elif fault == 'subject_run': d['subject']['subject_run_key'] = 'other'
    elif fault == 'candidate': d['subject']['release_candidate_id'] = 'other'
    elif fault == 'run_id': d['subject']['workflow_run_id'] += 1
    elif fault == 'attempt': d['subject']['workflow_run_attempt'] += 1
    elif fault == 'execution_run': execution['run_binding']['execution_run_key'] = 'other'
    elif fault == 'execution_subject_run': execution['run_binding']['subject_run_key'] = 'other'
    elif fault == 'post_run_binding': execution['run_binding']['binding_mode'] = 'post_run_observer'
    elif fault == 'incomplete_binding': execution['run_binding']['binding_complete'] = False
    elif fault == 'observer_scope': execution['execution_scope'] = 'observer'
    elif fault == 'observer_role': execution['declared_role'] = 'observer'
    elif fault == 'observer_kind': execution['execution_kind'] = 'observer_execution'
    elif fault == 'wrong_operator_path': execution['source_identity']['source_path_or_uri'] = 'other.txt'
    elif fault == 'wrong_operator_hash': execution['source_identity']['source_sha256'] = '0' * 64
    elif fault == 'wrong_operator_revision': execution['source_identity']['source_revision'] = '2' * 40
    elif fault == 'unknown_operator_kind': execution['source_identity']['source_kind'] = 'builtin'
    elif fault == 'partial_operator_identity': execution['source_identity']['identity_status'] = 'partial'
    elif fault == 'missing_execution': d['executions'].pop(0)
    elif fault == 'duplicate_execution': d['executions'].append(copy.deepcopy(execution))
    elif fault == 'missing_state': d['state_observations'].pop(0)
    elif fault == 'duplicate_state': d['state_observations'].append(copy.deepcopy(state))
    elif fault == 'changed_input_edges': execution['input_state_ids'] = ['state:b1:variant-input']
    elif fault == 'changed_output_edges': execution['output_state_ids'] = ['state:b1:variant-output']
    elif fault == 'input_digest': state['sha256'] = '0' * 64
    elif fault == 'input_size': state['size_bytes'] += 1
    elif fault == 'input_not_exact': state['content_status'] = 'metadata_only'
    elif fault == 'state_run': state['subject_run_key'] = 'other'
    elif fault == 'state_candidate': state['release_candidate_id'] = 'other'
    elif fault == 'wrong_output_producer': d['state_observations'][1]['producer_execution_id'] = 'execution:b1:variant'
    else: d['privacy_boundary']['raw_prompt_text_included'] = True
    case.bind_json('runtime_packet', d)
    case.reject()


def repeat_baseline_case(case):
    """Select one case with two distinct executions and shared gate obligations."""
    baseline = next(item for item in case.contract['cases'] if item['case_id'] == 'baseline')
    case.contract['cases'] = [baseline]
    case.selection['inputs'] = [item for item in case.selection['inputs']
                                if item['input_id'] == baseline['input_id']]
    for occurrence in case.contract['occurrences']:
        occurrence['case_id'] = baseline['case_id']
    for obligation in case.contract['obligations']:
        obligation['case_ids'] = [baseline['case_id']]


@pytest.mark.parametrize('reverse_occurrences', [False, True])
@pytest.mark.parametrize('fault', ['unrelated_bytes', 'wrong_digest', 'wrong_size', 'non_exact'])
def test_every_repeated_case_occurrence_requires_its_selected_input(tmp_path, fault, reverse_occurrences):
    case = Case(tmp_path)
    repeat_baseline_case(case)
    runtime = load(case.file('runtime_packet'))
    reference = case.selection['inputs'][0]
    state = next(item for item in runtime['state_observations']
                 if item['state_id'] == 'state:b1:variant-input')
    if fault == 'wrong_digest':
        state['size_bytes'] = reference['size_bytes']
    elif fault == 'wrong_size':
        state['sha256'] = reference['sha256']
        state['size_bytes'] = reference['size_bytes'] + 1
    elif fault == 'non_exact':
        state.update(sha256=reference['sha256'], size_bytes=reference['size_bytes'],
                     content_status='metadata_only')
    if reverse_occurrences:
        case.contract['occurrences'].reverse()
    case.bind_json('runtime_packet', runtime)
    case.sync_protocol_rosters()
    with pytest.raises(C.ContractError) as caught:
        case.check()
    assert caught.value.code == 'case_input_digest_mismatch'


@pytest.mark.parametrize('input_mapping', ['shared_state', 'separate_state', 'additional_input'])
def test_valid_repeated_case_occurrences_keep_distinct_executions(tmp_path, input_mapping):
    case = Case(tmp_path)
    repeat_baseline_case(case)
    runtime = load(case.file('runtime_packet'))
    occurrence = case.contract['occurrences'][1]
    execution = next(item for item in runtime['executions']
                     if item['execution_id'] == occurrence['execution_id'])
    if input_mapping == 'separate_state':
        state = next(item for item in runtime['state_observations']
                     if item['state_id'] == 'state:b1:variant-input')
        reference = case.selection['inputs'][0]
        state.update(sha256=reference['sha256'], size_bytes=reference['size_bytes'])
    else:
        input_ids = ['state:b1:baseline-input']
        if input_mapping == 'additional_input':
            input_ids.insert(0, 'state:b1:variant-input')
        occurrence['input_state_ids'] = input_ids
        execution['input_state_ids'] = list(input_ids)
    case.bind_json('runtime_packet', runtime)
    case.sync_protocol_rosters()
    report = case.check()
    assert report['valid'] is True and report['declaration_complete'] is True
    assert report['counts']['cases'] == report['counts']['inputs'] == 1
    assert report['counts']['occurrences'] == 2
    assert len({item['execution_id'] for item in case.contract['occurrences']}) == 2
    boundary(report)


def test_repeated_case_input_mismatch_cli_is_canonical_and_non_authoritative(tmp_path):
    case = Case(tmp_path)
    repeat_baseline_case(case)
    case.sync_protocol_rosters()
    first = case.cli(); second = case.cli()
    assert first.returncode == second.returncode == 1
    assert first.stdout == second.stdout
    report = json.loads(first.stdout)
    assert first.stdout == C.canonical_bytes(report)
    assert report['valid'] is False and report['declaration_complete'] is False
    assert report['errors'] == ['case_input_digest_mismatch']
    boundary(report)


@pytest.mark.parametrize('fault', ['packet_run', 'repository', 'source_commit', 'subject_run', 'candidate', 'run_id', 'attempt'])
def test_subject_packet_source_and_identity_must_match(tmp_path, fault):
    case = Case(tmp_path); d = load(case.file('subject_packet'))
    if fault == 'packet_run': d['packet_identity']['subject_run_key'] = 'other'
    elif fault == 'repository': d['subject']['repository'] = 'other/repo'
    elif fault == 'source_commit': d['subject']['source_commit'] = '2' * 40
    elif fault == 'subject_run': d['subject']['subject_run_key'] = 'other'
    elif fault == 'candidate': d['subject']['release_candidate_id'] = 'other'
    elif fault == 'run_id': d['subject']['workflow_run_id'] += 1
    else: d['subject']['workflow_run_attempt'] += 1
    case.bind_json('subject_packet', d)
    case.reject()


def test_schema_valid_unsupported_subject_profile_rejects_without_unhandled_key_error(tmp_path):
    case = Case(tmp_path)
    legacy = load(case.file('subject_packet'))
    subject_keys = ('repository', 'workflow_name', 'workflow_run_id', 'workflow_run_number',
        'workflow_run_attempt', 'subject_run_key', 'source_commit', 'release_candidate_id')
    bounded = {
        'schema_version': 'pulsemech_compute_subject_input_packet_v0',
        'packet_type': 'pulsemech_compute_subject_input_packet',
        'input_profile': 'bounded_execution_reference_v0', 'record_status': 'example',
        'packet_identity': {key: legacy['packet_identity'][key] for key in
            ('packet_id', 'packet_created_utc', 'subject_run_key', 'canonicalization')},
        'subject': {**{key: legacy['subject'][key] for key in subject_keys},
            'run_mode': 'bounded_reference', 'active_policy_sets': ['core_required']},
        'acquisition_context': {'record_status': 'example', 'repository': 'HKati/pulse-release-gates-0.1',
            'workflow_name': 'PULSEmech bounded execution reference',
            'workflow_path': '.github/workflows/pulsemech_compute_bounded_execution_reference.yml',
            'run_id': 1, 'run_number': 1, 'run_attempt': 1, 'source_commit': '1' * 40,
            'event_name': 'test', 'acquisition_id': 'synthetic-unsupported-profile'},
        'carrier': {'carrier_kind': 'bounded_execution_archive', 'path_or_uri': 'sha256:' + '0' * 64,
            'sha256': '0' * 64, 'size_bytes': 1, 'immutable': True},
        'capture_binding': {'prelaunch_sha256': '0' * 64, 'capture_manifest_sha256': '0' * 64},
        'construction': {'producer_core_path': 'tools/pulsemech_compute_subject_input_packet_producer_core_v0.py',
            'producer_core_revision': '1' * 40, 'producer_core_sha256': '0' * 64},
        'artifacts': [{'member': name, 'sha256': '0' * 64, 'size_bytes': 1}
            for name in ('prelaunch.json', 'capture.json', 'planner/plan.json')],
        'role_bindings': {'prelaunch': 'prelaunch.json', 'capture': 'capture.json', 'integration_plan': 'planner/plan.json'},
        'coverage': {'artifact_inventory': 'complete', 'observation_claim': 'bounded_reference_only',
            'resource_measurement': 'unavailable'},
        'authority_boundary': {'authority_effect': 'none', 'same_run_release_authority_eligible': False,
            'active_gate_eligible': False, 'packet_is_release_authority': False, 'creates_release_decision': False},
        'errors': [], 'ok': True,
    }
    Draft202012Validator(load(case.file('subject_schema')), format_checker=FormatChecker()).validate(bounded)
    case.bind_json('subject_packet', bounded)
    with pytest.raises(C.ContractError) as caught:
        case.check()
    assert caught.value.code == 'packet_profile_unsupported'


def test_synthetic_origin_cannot_be_promoted_by_relabeling_contract_and_selection(tmp_path):
    case = Case(tmp_path)
    case.selection['origin'] = case.contract['origin'] = 'reviewed_declaration'
    protocol = load(case.file('protocol')); protocol['origin'] = 'reviewed_declaration'
    case.bind_json('protocol', protocol)
    case.reject()


def test_draft_cannot_hide_cross_subject_packets_by_omitting_occurrences(tmp_path):
    case = Case(tmp_path)
    case.contract.update(declaration_state='draft', cases=[], occurrences=[], obligations=[], unresolved_decisions=['cases'])
    case.selection['inputs'] = []
    runtime = load(case.file('runtime_packet'))
    runtime['subject']['release_candidate_id'] = 'other-subject'
    case.bind_json('runtime_packet', runtime)
    case.reject()


def test_self_consistent_contract_and_selection_replacement_fails_frozen_caller_pin(tmp_path):
    case = Case(tmp_path); original_pin = case.pin
    case.contract['suite_id'] = 'self-selected-replacement'
    protocol = load(case.file('protocol')); protocol['suite_id'] = case.contract['suite_id']
    case.bind_json('protocol', protocol)
    assert case.pin != original_pin
    with pytest.raises(C.ContractError):
        C.validate_contract(case.contract_path, case.selection_path, original_pin, case.root)


@pytest.mark.parametrize('raw', [b'{} {}', b'[]', b'null', b'1', b'\xff', b'\xef\xbb\xbf{}',
    b'{"record_type":"x","record_type":"y"}',
    b'{"nested":{"same":1,"same":2}}', b'{"number":NaN}', b'{"number":Infinity}',
    b'{"number":-Infinity}', b'{"number":1e999}'])
def test_strict_json_parsing_rejects_malformed_and_nonfinite_contracts(tmp_path, raw):
    case = Case(tmp_path)
    case.select_current_contract(raw)
    case.reject()


@pytest.mark.parametrize('target', ['selection', 'protocol'])
@pytest.mark.parametrize('raw', [b'{"nested":{"id":1,"id":2}}', b'{"number":1e999}'])
def test_other_selected_json_documents_use_the_same_strict_parse_boundary(tmp_path, target, raw):
    case = Case(tmp_path)
    if target == 'selection':
        case.select_current_selection(raw)
    else:
        case.bind_bytes('protocol', raw)
    case.reject()


@pytest.mark.parametrize('fault', ['bool_size', 'fractional_size', 'missing_binding', 'extra_binding',
    'replaced_source_anchor', 'missing_input', 'duplicate_input_id'])
def test_selection_shape_is_closed_and_integer_identities_are_not_coerced(tmp_path, fault):
    case = Case(tmp_path)
    if fault == 'bool_size': case.selection['contract']['size_bytes'] = True
    elif fault == 'fractional_size': case.selection['contract']['size_bytes'] = float(case.selection['contract']['size_bytes'])
    elif fault == 'missing_binding': del case.selection['bindings']['source_anchor']
    elif fault == 'extra_binding': case.selection['bindings']['authorizer'] = case.selection['bindings']['source_anchor']
    elif fault == 'replaced_source_anchor': case.selection['bindings']['source_anchor']['sha256'] = '0' * 64
    elif fault == 'missing_input': case.selection['inputs'].pop()
    else: case.selection['inputs'].append(copy.deepcopy(case.selection['inputs'][0]))
    case.select_current_selection()
    case.reject()


@pytest.mark.parametrize('target', ['contract', 'selection', 'protocol'])
def test_file_limits_reject_oversized_selected_bytes_before_parsing(tmp_path, target):
    case = Case(tmp_path)
    path = {'contract': case.contract_path, 'selection': case.selection_path,
        'protocol': case.file('protocol')}[target]
    path.write_bytes(b' ' * (C.MAX_FILE_BYTES + 1))
    with pytest.raises(C.ContractError) as caught:
        case.check()
    assert caught.value.code == 'file_size_limit'


@pytest.mark.parametrize('kind', ['depth', 'nodes'])
def test_document_complexity_limits_reject_bounded_bytes_with_excessive_structure(tmp_path, kind):
    case = Case(tmp_path)
    raw = (b'[' * (C.MAX_JSON_DEPTH + 1) + b'0' + b']' * (C.MAX_JSON_DEPTH + 1)
        if kind == 'depth' else b'[' + b','.join([b'0'] * (C.MAX_JSON_NODES + 1)) + b']')
    assert len(raw) < C.MAX_FILE_BYTES
    case.select_current_contract(raw)
    with pytest.raises(C.ContractError) as caught:
        case.check()
    assert caught.value.code == 'document_complexity_limit'


@pytest.mark.parametrize('role', ['policy', 'registry'])
def test_selected_yaml_rejects_duplicate_keys_and_nonfinite_values(tmp_path, role):
    case = Case(tmp_path)
    case.bind_bytes(role, b'gates: {}\ngates: {}\n')
    case.reject()
    case.bind_bytes(role, b'gates: {}\ninvalid: .nan\n')
    case.reject()


@pytest.mark.parametrize(('extra', 'error_code'), [
    (b'synthetic_anchor: &b1 [1]\nsynthetic_alias: *b1\n', 'yaml_alias_forbidden'),
    (b'synthetic_recursive: &b1 [*b1]\n', 'yaml_alias_forbidden'),
    (b'synthetic_merge:\n  <<: {fixture: true}\n', 'yaml_merge_forbidden'),
])
def test_selected_yaml_rejects_aliases_and_merge_keys_before_construction(tmp_path, extra, error_code):
    case = Case(tmp_path)
    original = case.file('policy').read_bytes()
    case.bind_bytes('policy', original.rstrip() + b'\n' + extra)
    with pytest.raises(C.ContractError) as caught:
        case.check()
    assert caught.value.code == error_code


@pytest.mark.parametrize('path', ['/absolute.json', '../outside.json', './synthetic_protocol.json',
    'tests/../outside.json', 'tests\\outside.json', 'tests//outside.json'])
def test_selected_paths_cannot_escape_or_change_normalized_identity(tmp_path, path):
    case = Case(tmp_path)
    case.selection['bindings']['protocol']['path'] = path
    case.select_current_selection()
    case.reject()


def test_missing_anchor_and_unselected_contract_path_reject(tmp_path):
    case = Case(tmp_path)
    case.file('protocol').unlink()
    case.reject()
    other = tmp_path / 'unselected.json'; other.write_bytes(case.contract_path.read_bytes())
    with pytest.raises(C.ContractError):
        C.validate_contract(other, case.selection_path, case.pin, case.root)


@pytest.mark.skipif(not hasattr(os, 'symlink'), reason='symlinks unavailable')
def test_identical_bytes_through_input_symlink_are_not_selected_regular_file(tmp_path):
    case = Case(tmp_path)
    path = case.file('operator'); outside = tmp_path / 'other-operator.txt'
    outside.write_bytes(path.read_bytes()); path.unlink(); path.symlink_to(outside)
    case.reject()


@pytest.mark.skipif(not hasattr(os, 'mkfifo'), reason='POSIX FIFO unavailable')
def test_fifo_anchor_rejects_without_blocking_or_reading(tmp_path):
    case = Case(tmp_path); path = case.file('protocol')
    path.unlink(); os.mkfifo(path)
    result = case.cli(timeout=5)
    assert result.returncode != 0


@pytest.mark.parametrize('keyword', ['$ref', '$dynamicRef', '$recursiveRef'])
def test_schema_cannot_resolve_remote_references(tmp_path, keyword):
    case = Case(tmp_path)
    schema = load(case.file('contract_schema'))
    schema[keyword] = 'https://invalid.example/no-network-ever'
    case.bind_json('contract_schema', schema)
    case.reject()


def test_schema_nested_id_cannot_rebase_local_references(tmp_path):
    case = Case(tmp_path)
    schema = load(case.file('contract_schema'))
    schema.setdefault('$defs', {})['rebase'] = {'$id': 'https://invalid.example/rebase', 'type': 'object'}
    case.bind_json('contract_schema', schema)
    case.reject()


def test_repeated_actual_cli_reports_are_canonical_identical_and_non_authoritative(tmp_path):
    case = Case(tmp_path)
    before = {p.relative_to(case.root).as_posix(): p.read_bytes() for p in case.root.rglob('*') if p.is_file()}
    first = case.cli(); second = case.cli()
    assert first.returncode == second.returncode == 0, (first.stderr, second.stderr)
    assert first.stdout == second.stdout
    report = json.loads(first.stdout)
    assert first.stdout == C.canonical_bytes(report)
    boundary(report)
    assert str(case.root).encode() not in first.stdout and b'finite-pair-v0' not in first.stdout
    after = {p.relative_to(case.root).as_posix(): p.read_bytes() for p in case.root.rglob('*') if p.is_file()}
    assert after == before


def test_fresh_output_matches_stdout_and_second_write_preserves_original_bytes(tmp_path):
    case = Case(tmp_path); output = tmp_path / 'report.json'
    first = case.cli('--out', output)
    assert first.returncode == 0 and output.read_bytes() == first.stdout
    original = output.read_bytes()
    second = case.cli('--out', output)
    assert second.returncode == 2 and output.read_bytes() == original


@pytest.mark.parametrize('name', ['status.json', 'release_decision_v0.json', 'release_authority_v0.json',
    'STATUS.JSON', 'Release_Decision_v0.json', 'Release_Authority_v0.JSON'])
def test_authority_output_basenames_are_refused(tmp_path, name):
    case = Case(tmp_path); output = tmp_path / name
    result = case.cli('--out', output)
    assert result.returncode == 2 and not output.exists()


@pytest.mark.parametrize('target', ['contract', 'selection', 'schema', 'tool', 'hardlink', 'symlink', 'symlink_parent'])
def test_outputs_cannot_alias_inputs_sources_or_traverse_symlinks(tmp_path, target):
    case = Case(tmp_path)
    if target == 'contract': output = case.contract_path
    elif target == 'selection': output = case.selection_path
    elif target == 'schema': output = case.file('contract_schema')
    elif target == 'tool': output = case.file('checker_source')
    elif target == 'hardlink':
        output = tmp_path / 'hardlink-report.json'; os.link(case.contract_path, output)
    elif target == 'symlink':
        output = tmp_path / 'symlink-report.json'; output.symlink_to(case.contract_path)
    else:
        actual = tmp_path / 'real-reports'; actual.mkdir()
        link = tmp_path / 'linked-reports'; link.symlink_to(actual, target_is_directory=True)
        output = link / 'report.json'
    before = case.contract_path.read_bytes()
    existed = output.exists()
    previous = output.read_bytes() if existed else None
    result = case.cli('--out', output)
    assert result.returncode == 2
    assert case.contract_path.read_bytes() == before
    if existed:
        assert output.read_bytes() == previous
    else:
        assert not output.exists()


def test_cli_missing_selection_pin_refuses_to_derive_trust(tmp_path):
    case = Case(tmp_path)
    result = subprocess.run([sys.executable, str(TOOL), '--contract', str(case.contract_path),
        '--selection', str(case.selection_path), '--root', str(case.root)], capture_output=True, timeout=15)
    assert result.returncode == 2


def test_cli_error_report_does_not_echo_rejected_private_content(tmp_path):
    case = Case(tmp_path)
    case.contract['raw_prompt'] = 'PRIVATE_B1_SENTINEL_DO_NOT_ECHO'
    case.select_current_contract()
    result = case.cli()
    assert result.returncode == 1
    assert b'PRIVATE_B1_SENTINEL' not in result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report['valid'] is False and report['declaration_complete'] is False
    boundary(report)


def test_selected_operator_and_decision_text_are_bound_without_execution_or_interpretation(tmp_path):
    case = Case(tmp_path)
    case.bind_bytes('operator', b'raise RuntimeError("SYNTHETIC OPERATOR MUST NEVER EXECUTE")\n')
    runtime = load(case.file('runtime_packet'))
    for execution in runtime['executions']:
        execution['source_identity']['source_sha256'] = case.selection['bindings']['operator']['sha256']
    case.bind_json('runtime_packet', runtime)
    case.bind_bytes('comparison', b'SYNTHETIC declaration: deliberately not a mathematical predicate.\n')
    report = case.check()
    assert report['valid'] is True and report['declaration_complete'] is True
    boundary(report)


@pytest.mark.parametrize('missing_flag', ['O_NOFOLLOW', 'O_DIRECTORY'])
def test_unavailable_required_descriptor_safety_fails_closed_before_file_access(tmp_path, monkeypatch, missing_flag):
    case = Case(tmp_path)
    monkeypatch.delattr(C.os, missing_flag)
    with pytest.raises(C.ContractError) as caught:
        case.check()
    assert caught.value.code == 'platform_not_supported'


def test_suite_contract_test_is_registered_once_without_targeted_pytest_duplication():
    name = 'tests/test_required_gate_suite_contract_v0.py'
    def entries(path):
        return [line.split('#', 1)[0].strip() for line in path.read_text().splitlines()
                if line.split('#', 1)[0].strip()]
    assert entries(ROOT / 'ci/tools-tests.list').count(name) == 1
    assert name not in entries(ROOT / 'ci/pytest-tests.list')


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__]))
