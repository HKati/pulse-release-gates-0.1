#!/usr/bin/env python3
"""WP2H: build a fresh, scope-labelled Anchor diagnostic, never release authority.

Only fixed installed checkers execute. Caller-pinned selection data chooses
one of two fixed pipelines, not code. All evidence stages share one retained
BundleReader. Legacy proxy values never establish coverage or support.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'fresh-anchor-diagnostic-v1'
SCHEMAS = {
    'selection': 'anchor_integrity_diagnostic_selection_v0_1.schema.json',
    'report': 'anchor_integrity_diagnostic_report_v0_1.schema.json',
}
STAGES = ('bindings', 'records', 'record_signatures', 'execution_contract',
          'receipt_signature', 'dependency_cycles')
LOCAL_ROLES = ('input', 'carriers', 'record_set')
RECEIPT_ROLES = (*LOCAL_ROLES, 'signatures', 'trust_policy', 'request', 'receipt',
                 'observer_policy', 'receipt_signature')
MODULES = (
    'check_anchor_integrity_bindings_v0_1.py',
    'anchor_integrity_json_pointer_v0_1.py',
    'check_anchor_integrity_verifier_records_v0_1.py',
    'check_anchor_integrity_dependency_cycles_v0_1.py',
    'check_anchor_integrity_record_signatures_v0_1.py',
    'check_anchor_integrity_execution_contract_v0_1.py',
    'check_anchor_integrity_receipt_signatures_v0_1.py',
)
UNPERFORMED = (
    'claim_set_completeness', 'source_identity_authentication',
    'acquisition_authentication', 'subject_observation_authentication',
    'verifier_execution_attestation', 'observer_execution_attestation',
    'observer_identity_authentication', 'policy_provenance_verification',
    'key_custody_and_independence', 'trusted_clock_verification',
    'request_precommitment_verification', 'challenge_freshness_verification',
    'runtime_closure_and_isolation', 'semantic_support_verification',
    'independent_anchor_admission',
)
STATUSES = {'built': 'LOCAL_DIAGNOSTIC_BUILT', 'invalid': 'LOCAL_DIAGNOSTIC_INVALID',
            'incomplete': 'LOCAL_DIAGNOSTIC_INCOMPLETE'}
MAX_SELECTION_BYTES = 65536


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def report_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                       allow_nan=False) + '\n').encode('utf-8')


def load_installed(filename: str) -> Any:
    """The caller/artifact cannot choose a module outside this fixed allowlist."""
    if filename not in MODULES:
        raise ValueError('module_not_in_fixed_installation')
    path = ROOT / 'tools' / filename
    spec = importlib.util.spec_from_file_location('anchor_wp2h_' + path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError('installed_checker_unavailable')
    module = importlib.util.module_from_spec(spec)
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = old
    return module


def not_run(reason: str) -> dict[str, Any]:
    return {'status': 'not_run', 'result': None, 'reason': reason}


def metric(status: str, reason: str, numerator: int | None = None,
           denominator: int | None = None) -> dict[str, Any]:
    return {'status': status, 'numerator': numerator, 'denominator': denominator,
            'value': numerator / denominator if status == 'completed' else None,
            'reason': None if status == 'completed' else reason}


class DiagnosticSchemas:
    def __init__(self, base: Any) -> None:
        self.base = base
        self.hashes: dict[str, str] = {}
        self.validators: dict[str, Any] = {}
        for role, name in SCHEMAS.items():
            raw = (ROOT / 'schemas' / name).read_bytes()
            schema = base.strict_json(raw)
            base._assert_self_contained(schema)
            jsonschema.Draft202012Validator.check_schema(schema)
            self.validators[role] = jsonschema.Draft202012Validator(schema)
            self.hashes[name] = digest(raw)

    def validate(self, role: str, value: Any) -> None:
        if next(self.validators[role].iter_errors(value), None) is not None:
            raise self.base.BindingError('schema_invalid_diagnostic_' + role)


class DiagnosticReview:
    def __init__(self, base: Any) -> None:
        self.base = base
        self.schemas = DiagnosticSchemas(base)
        self.report: dict[str, Any] = {
            'schema_version': 'anchor_integrity_diagnostic_report_v0_1',
            'work_package': 'WP2H', 'profile': PROFILE,
            'candidate_status': 'diagnostic_only', 'authority_effect': 'none',
            'release_authority_activation': False, 'requested_checks_complete': False,
            'accepted_as_execution_evidence': False, 'accepted_as_semantic_support': False,
            'accepted_as_independent_anchor': False,
            'whole_response_completeness_established': False,
            'whole_response_cycle_freedom_established': False,
            'legacy_v0_replaced': False, 'wp1_output_emitted': False,
            'status': STATUSES['incomplete'], 'pipeline': None,
            'profiles': {'binding': None, 'cycle': None, 'record_signature': None,
                         'execution': None, 'receipt_signature': None},
            'expected_selection_sha256': None, 'observed_selection_sha256': None,
            'selected_bindings': {}, 'subject': None, 'input_requested_checks': None,
            'stage_receipts': {s: {'executed': False, 'outcome': None,
                                   'report_sha256': None} for s in STAGES},
            'inventory': {'claim_set_id': None, 'declared_materialization_status': None,
                          'observed_claim_count': None,
                          'scope': 'explicitly_declared_claim_set_only',
                          'completeness_independently_verified': False},
            'coverage': {
                'anchor_presence_coverage': metric('not_run', 'checked_claim_inventory_unavailable'),
                'verified_binding_coverage': metric('not_run', 'source_identity_authentication_not_implemented'),
                'verified_support_coverage': metric('not_run', 'semantic_support_verification_not_implemented')},
            'legacy_operational_proxy': {
                'semantic_class': 'operational_proxy', 'is_claim_evidence_coverage': False,
                'influences_dispositions': False, 'influences_recommendation': False,
                'status': 'unavailable', 'reported_value': None,
                'path': None, 'sha256': None, 'reason': 'checked_legacy_bytes_unavailable',
                'v0_state_response_gate_action_and_risk_ignored': True},
            'claim_diagnostics': [],
            'cycle_detection': {'status': 'not_run', 'result': None, 'algorithm': None,
                                'reason': 'structural_cycle_stage_not_run'},
            'cycle_scope': 'declared_edges_only', 'cyclic_components': [],
            'cycle_anchor_classification': not_run('independent_anchor_admission_not_implemented'),
            'loop_risk': None,
            'record_signature_authentication': not_run('record_signature_stage_not_run'),
            'execution_contract_check': not_run('execution_contract_stage_not_run'),
            'receipt_statement_authentication': not_run('receipt_signature_stage_not_run'),
            'authenticated_receipt_statement': False, 'receipt_scope': None,
            'response_recommendation': {'mode': 'BOUNDARY', 'authority': 'diagnostic_only',
                                        'enforced': False, 'reason': 'checked_inventory_unavailable'},
            'unperformed_checks': {name: not_run('outside_wp2h_diagnostic_scope') for name in UNPERFORMED},
            'issues': [],
            'implementation': {
                'adapter_sha256': digest(Path(__file__).read_bytes()),
                'module_sha256': {n: digest((ROOT / 'tools' / n).read_bytes()) for n in MODULES},
                'schema_sha256': self.schemas.hashes},
        }

    def issue(self, code: str, severity: str = 'invalid', stage: str = 'adapter') -> None:
        self.report['issues'].append({'code': code, 'severity': severity, 'stage': stage})

    def stage(self, name: str, result: dict[str, Any], *, collect_issues: bool = False) -> None:
        self.report['stage_receipts'][name] = {
            'executed': True, 'outcome': result['status'],
            'report_sha256': digest(report_bytes(result))}
        if collect_issues:
            for issue in result['issues']:
                self.issue(issue['code'], issue['severity'], name)

    def inventory(self, reader: Any, record_review: Any, input_path: str) -> None:
        """Counts only after a fresh consistent binding check, never from labels."""
        result = record_review.binding.report
        self.report['subject'] = result['subject']
        state = result['claim_set_materialization_status']
        inv = self.report['inventory']
        inv['declared_materialization_status'] = state
        inv['observed_claim_count'] = result['counts']['claims']
        if state in ('partial', 'invalid'):
            for name in self.report['coverage']:
                self.report['coverage'][name] = metric('not_applicable', 'claim_set_not_declared_complete')
        if result['status'] != 'LOCAL_BINDINGS_CONSISTENT':
            return
        inp = record_review.cached_json(reader, input_path)
        self.report['input_requested_checks'] = deepcopy(inp['requested_checks'])
        cp = record_review.cached_json(reader, inp['packet_bindings']['claim_packet']['path'])
        rp = record_review.cached_json(reader, inp['packet_bindings']['relation_verification_packet']['path'])
        claims = cp['claim_set']['claims']
        inv['claim_set_id'] = cp['claim_set']['claim_set_id']
        grouped: dict[str, list[dict[str, Any]]] = {c['claim_id']: [] for c in claims}
        for relation in rp['relations']:
            grouped[relation['claim_id']].append(relation)
        for claim in sorted(claims, key=lambda c: c['claim_id']):
            relations = sorted(grouped[claim['claim_id']], key=lambda r: r['binding_id'])
            self.report['claim_diagnostics'].append({
                'claim_id': claim['claim_id'],
                'referenced_evidence_ids': sorted({r['evidence_id'] for r in relations}),
                'recorded_relations': [{
                    'binding_id': r['binding_id'], 'evidence_id': r['evidence_id'],
                    'relation_type': r['relation_type'],
                    'declared_status': r['relation_verification']['status'],
                    'declared_result': r['relation_verification']['result']}
                    for r in relations],
                'disposition': 'unresolved', 'accepted_as_semantic_support': False,
                'reason': 'no_accepted_semantic_verification'})
        n = sum(bool(grouped[c['claim_id']]) for c in claims)
        d = len(claims)
        self.report['coverage']['anchor_presence_coverage'] = (
            metric('completed', '', n, d) if d else metric('not_applicable', 'empty_declared_claim_set'))
        self.legacy(reader, inp['legacy_overlay'])

    def legacy(self, reader: Any, ref: dict[str, Any] | None) -> None:
        out = self.report['legacy_operational_proxy']
        if ref is None:
            out['reason'] = 'legacy_overlay_not_supplied'
            return
        raw = reader.cache[ref['path']]
        if digest(raw) != ref['sha256']:
            raise self.base.BindingError('retained_legacy_digest_mismatch')
        out.update(path=ref['path'], sha256=digest(raw))
        value = self.base.strict_json(raw)
        invariants = value.get('invariants')
        if value.get('schema') != 'anchor_integrity_v0' or not isinstance(invariants, dict):
            out['reason'] = 'legacy_ratio_not_available_in_supported_v0_shape'
            return
        proxy = invariants.get('anchor_coverage')
        if proxy is None:
            out['reason'] = 'legacy_ratio_not_reported'
        elif (isinstance(proxy, bool) or not isinstance(proxy, (int, float)) or
              not 0 <= proxy <= 1 or not math.isfinite(proxy)):
            out.update(status='invalid', reason='invalid_legacy_proxy_value')
            self.issue('invalid_legacy_proxy_value', stage='legacy_proxy')
        else:
            out.update(status='reported', reported_value=proxy, reason=None)

    def collect_records(self, record_review: Any) -> None:
        if record_review.report['base_check']['status'] is not None:
            self.stage('bindings', record_review.binding.report)
        self.stage('records', record_review.report)

    def collect_receipt(self, receipt_review: Any) -> None:
        r = receipt_review.report
        f = receipt_review.previous
        e = f.previous
        c = e.previous
        if e.report['record_check']['status'] is not None:
            self.collect_records(c)
        if f.report['signature_check']['status'] is not None:
            self.stage('record_signatures', e.report)
            self.report['record_signature_authentication'] = deepcopy(e.report['signer_authentication'])
        if r['execution_contract_check']['status'] is not None:
            self.stage('execution_contract', f.report)
            self.report['execution_contract_check'] = deepcopy(f.report['contract_check'])
        self.stage('receipt_signature', r, collect_issues=True)
        self.report['receipt_statement_authentication'] = deepcopy(r['observer_statement_authentication'])
        self.report['authenticated_receipt_statement'] = r['authenticated_receipt_statement']
        self.report['receipt_scope'] = {
            'record_id': r['selected_record_id'], 'execution_id': r['expected_execution_id'],
            'observer_id': r['expected_observer_id'], 'observation_basis': r['observation_basis'],
            'challenge': r['expected_challenge'], 'verification_time_epoch': r['verification_time_epoch'],
            'time_source': 'caller_supplied_not_authenticated',
            'trust_domain': r['trust_domain'], 'covers_all_claims': False}

    def cycles(self, cycle_module: Any, records: Any, record_review: Any,
               reader: Any, selection: dict[str, Any]) -> None:
        if selection['cycle_profile'] == 'not_requested':
            self.report['cycle_detection']['reason'] = 'not_selected_by_pinned_diagnostic_invocation'
            return
        if record_review.report['status'] != 'LOCAL_RECORD_BINDINGS_CONSISTENT':
            self.report['cycle_detection']['reason'] = 'fresh_record_bindings_not_consistent'
            return
        cr = cycle_module.CycleReview(records, record_review.base, selection['binding_profile'])
        # Reuse the already-executed WP2C object and its retained bytes, not a
        # caller-authored report or a separately reopened evidence directory.
        cr.record_review = record_review
        cr.report['expected_digests'] = {k: selection['bindings'][k]['sha256'] for k in LOCAL_ROLES}
        try:
            if cr.capture_records():
                cr.observe(reader, selection['bindings']['input']['path'])
        except record_review.base.BindingError as exc:
            cr.issue(exc.code, 'bundle', exc.severity)
        result = cr.finish()
        self.stage('dependency_cycles', result, collect_issues=True)
        self.report['cycle_detection'] = deepcopy(result['cycle_detection'])
        self.report['cyclic_components'] = deepcopy(result['cyclic_components'])

    def finish(self) -> dict[str, Any]:
        report = self.report
        unique = {(i['stage'], i['severity'], i['code']): i for i in report['issues']}
        report['issues'] = [unique[k] for k in sorted(unique)]
        severity = {i['severity'] for i in report['issues']}
        state = 'invalid' if 'invalid' in severity else 'incomplete' if severity else 'built'
        report['status'] = STATUSES[state]
        presence = report['coverage']['anchor_presence_coverage']
        rec = report['response_recommendation']
        if state != 'built':
            rec['reason'] = 'diagnostic_' + state
        elif presence['status'] == 'completed' and presence['numerator'] == 0:
            rec.update(mode='ASK_FOR_ANCHOR', reason='no_referenced_anchor_in_declared_claim_set')
        else:
            rec['reason'] = 'semantic_support_not_verified'
        self.schemas.validate('report', report)
        validate_arithmetic(report)
        return report


def validate_arithmetic(report: dict[str, Any]) -> None:
    """Reconcile counts and division; a JSON schema alone cannot do this."""
    m = report['coverage']['anchor_presence_coverage']
    if m['status'] == 'completed':
        rows = report['claim_diagnostics']
        ids = [r['claim_id'] for r in rows]
        n = sum(bool(r['referenced_evidence_ids']) for r in rows)
        d = len(rows)
        if (len(set(ids)) != d or d == 0 or m['numerator'] != n or m['denominator'] != d or
                report['inventory']['observed_claim_count'] != d or m['value'] != n / d):
            raise ValueError('diagnostic_coverage_arithmetic_mismatch')
    if report['status'] == STATUSES['built']:
        if report['expected_selection_sha256'] != report['observed_selection_sha256']:
            raise ValueError('diagnostic_selection_pin_mismatch')
    for row in report['claim_diagnostics']:
        if row['referenced_evidence_ids'] != sorted({r['evidence_id'] for r in row['recorded_relations']}):
            raise ValueError('diagnostic_relation_inventory_mismatch')


def disjoint_readers(base: Any, stack: ExitStack, roots: list[Path]) -> list[Any]:
    try:
        resolved = [Path(p).resolve(strict=True) for p in roots]
    except FileNotFoundError as exc:
        raise base.BindingError('required_root_missing', 'incomplete') from exc
    for i, a in enumerate(resolved):
        for b in resolved[:i]:
            if a.is_relative_to(b) or b.is_relative_to(a):
                raise base.BindingError('diagnostic_roots_not_disjoint')
    readers = [stack.enter_context(base.BundleReader(p)) for p in roots]
    inodes = [(os.fstat(r.fd).st_dev, os.fstat(r.fd).st_ino) for r in readers]
    if len(set(inodes)) != len(readers):
        raise base.BindingError('diagnostic_root_inode_alias')
    return readers


def build_diagnostic(bundle_root: Path, *, selection_root: Path, selection_path: str,
                     expected_selection_sha256: str, trust_root: Path | None = None,
                     observer_trust_root: Path | None = None) -> dict[str, Any]:
    records = load_installed('check_anchor_integrity_verifier_records_v0_1.py')
    base = records.load_binding_checker()
    review = DiagnosticReview(base)
    try:
        if not isinstance(expected_selection_sha256, str) or base.HASH_RE.fullmatch(expected_selection_sha256) is None:
            raise base.BindingError('invalid_expected_selection_digest')
        review.report['expected_selection_sha256'] = expected_selection_sha256
        with base.BundleReader(selection_root) as selector:
            raw = selector.read(selection_path, 'wp2h.selection')
        review.report['observed_selection_sha256'] = digest(raw)
        if len(raw) > MAX_SELECTION_BYTES:
            raise base.BindingError('selection_size_limit')
        if digest(raw) != expected_selection_sha256:
            raise base.BindingError('selection_digest_mismatch')
        selection = base.strict_json(raw)
        review.schemas.validate('selection', selection)
        bindings = selection['bindings']
        for ref in bindings.values():
            base.safe_relative(ref['path'])
            if base.HASH_RE.fullmatch(ref['sha256']) is None:
                raise base.BindingError('noncanonical_selected_digest')
        review.report['selected_bindings'] = deepcopy(bindings)
        review.report['pipeline'] = selection['pipeline']
        ctx = selection['receipt_context']
        review.report['profiles'] = {'binding': selection['binding_profile'], 'cycle': selection['cycle_profile'],
            'record_signature': ctx['signature_profile'] if ctx else None,
            'execution': ctx['execution_profile'] if ctx else None,
            'receipt_signature': ctx['receipt_signature_profile'] if ctx else None}
        paths = {k: v['path'] for k, v in bindings.items()}
        pins = {k: v['sha256'] for k, v in bindings.items()}
        with ExitStack() as stack:
            if selection['pipeline'] == 'local-records':
                if trust_root is not None or observer_trust_root is not None:
                    raise base.BindingError('unexpected_policy_root_for_local_pipeline')
                _, reader = disjoint_readers(base, stack, [selection_root, bundle_root])
                child = records.RecordReview(base, selection['binding_profile'])
                child.report['expected_digests'] = pins
                try:
                    record_set = child.bound_set(reader, paths['record_set'], pins['record_set'])
                    child.prepare(reader, record_set, input_path=paths['input'], input_digest=pins['input'],
                                  carriers_path=paths['carriers'], carriers_digest=pins['carriers'])
                    if child.run_base(reader, paths['input'], pins['input'], paths['carriers'], pins['carriers']):
                        child.records(reader, record_set, paths['input'])
                except base.BindingError as exc:
                    child.issue(exc.code, 'bundle', exc.severity)
                result = child.finish()
                review.collect_records(child)
                for item in result['issues']:
                    review.issue(item['code'], item['severity'], 'records')
            else:
                if trust_root is None or observer_trust_root is None:
                    raise base.BindingError('receipt_policy_root_missing', 'incomplete')
                mod = load_installed('check_anchor_integrity_receipt_signatures_v0_1.py')
                execution = mod.load_execution_checker()
                ctx = selection['receipt_context']
                rr = mod.ReceiptReview(execution, selection['binding_profile'], ctx['trust_domain'],
                                       ctx['verification_time_epoch'], ctx['record_id'],
                                       ctx['execution_id'], ctx['challenge'], ctx['observer_id'])
                inner = rr.base
                records = rr.previous.records
                child = rr.previous.previous.previous
                rr.report['expected_digests'] = pins
                reader = None
                try:
                    _, reader, policy_reader, observer_reader = disjoint_readers(
                        inner, stack, [selection_root, bundle_root, trust_root, observer_trust_root])
                    reader.reserve(paths['receipt_signature'], 'wp2g.receipt_signature')
                    policy = rr.policy(observer_reader, paths['observer_policy'])
                    sig = rr.bound_json(reader, paths['receipt_signature'], 'signature', mod.MAX_SIGNATURE_BYTES)
                    previous = rr.run_previous(reader, policy_reader, paths)
                    if previous is not None:
                        rr.authenticate(reader, policy_reader, paths, policy, sig, previous[1])
                except inner.BindingError as exc:
                    rr.issue(exc.code, exc.severity)
                rr.finish()
                review.collect_receipt(rr)
                # A failure before reader creation yields no inventory/graph fallback.
                if reader is None:
                    return review.finish()
            review.inventory(reader, child, paths['input'])
            review.cycles(load_installed('check_anchor_integrity_dependency_cycles_v0_1.py'),
                          records, child, reader, selection)
    except base.BindingError as exc:
        review.issue(exc.code, exc.severity)
    return review.finish()


def render_markdown(report: dict[str, Any]) -> str:
    """A view of this freshly built report; no saved-report ingestion API/CLI."""
    base = load_installed('check_anchor_integrity_bindings_v0_1.py')
    DiagnosticSchemas(base).validate('report', report)
    validate_arithmetic(report)
    def number(value: Any) -> str:
        return 'not measured' if value is None else str(value)
    p = report['legacy_operational_proxy']
    c = report['coverage']['anchor_presence_coverage']
    count = ('not available' if c['value'] is None else
             f"{c['numerator']} / {c['denominator']} ({c['value']:.6f})")
    result = report['cycle_detection']['result'] or 'not measured'
    return '\n'.join([
        '# Anchor Integrity — WP2H diagnostic v0.1', '',
        '**Diagnostic only. No release, execution-evidence or semantic-support authorization.**', '',
        f"Build outcome: `{report['status']}`", '',
        '| Observation | Result |', '|---|---|',
        f"| Legacy gate-signal proxy (NOT claim coverage) | {number(p['reported_value'])} |",
        f'| Referenced-anchor presence in the declared claim set | {count} |',
        '| Verified binding coverage | not measured |',
        '| Verified support coverage | not measured |',
        f'| Structural cycle observation (declared edges only) | {result} |',
        '| Independent-anchor cycle classification | not measured |',
        '| Loop risk | not measured |', '',
        f"Recommendation: `{report['response_recommendation']['mode']}` (diagnostic, not enforced).", '',
        'A valid record or receipt signature does not establish semantic support or actual execution.',
        'The declared claim set and dependency inventory are not independently proven complete.',
        'The legacy v0 adapter and existing publication paths have NOT been replaced.',
        'Inspect the JSON report for exact pins, stage fingerprints, issues and cycle witnesses.', '',
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle-root', type=Path, required=True)
    parser.add_argument('--selection-root', type=Path, required=True)
    parser.add_argument('--selection', required=True)
    parser.add_argument('--expected-selection-sha256', required=True)
    parser.add_argument('--trust-root', type=Path)
    parser.add_argument('--observer-trust-root', type=Path)
    parser.add_argument('--format', choices=('json', 'markdown'), default='json')
    args = parser.parse_args(argv)
    try:
        result = build_diagnostic(args.bundle_root, selection_root=args.selection_root,
                                 selection_path=args.selection,
                                 expected_selection_sha256=args.expected_selection_sha256,
                                 trust_root=args.trust_root, observer_trust_root=args.observer_trust_root)
        output = report_bytes(result) if args.format == 'json' else render_markdown(result).encode('utf-8')
    except Exception as exc:
        print('Anchor diagnostic error: ' + type(exc).__name__, file=sys.stderr)
        return 2
    sys.stdout.buffer.write(output)
    return {STATUSES['built']: 0, STATUSES['invalid']: 1, STATUSES['incomplete']: 2}[result['status']]


if __name__ == '__main__':
    raise SystemExit(main())
