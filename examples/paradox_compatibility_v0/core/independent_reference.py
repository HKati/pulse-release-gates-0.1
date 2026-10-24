"""Bounded PD-SM-01 evaluator. No producer imports, case labels, I/O in assess,
network use, stored verdicts, or mutable proof cache. Not release authority.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

SNAPSHOT = '102145d1f1c321811c52d9d20f92cc7289127b2b'
INPUT_BLOBS = {
    'pulse_gate_drift_v0.csv': 'e1aabd25974f2de48f57954f1c243cb619a59776',
    'pulse_metric_drift_v0.csv': 'e9e92d80240297aab1111b7360ee677ba650d032',
    'pulse_overlay_drift_v0.json': 'c61d6bee0faa9b74ca00bf564900321400b2b21a',
    'pulse_transitions_v0.json': 'cdeb822818b65dba3ca9993176926369aa7a42ad',
}
CONTEXT_KEYS = {
    'pulse_gate_drift_v0.csv': 'transitions_gate_csv_sha1',
    'pulse_metric_drift_v0.csv': 'transitions_metric_csv_sha1',
    'pulse_overlay_drift_v0.json': 'transitions_overlay_json_sha1',
    'pulse_transitions_v0.json': 'transitions_json_sha1',
}
RANK = {'crit': 0, 'warn': 1, 'info': 2}
COUNTS = {'gate_flip': 1, 'metric_delta': 2, 'overlay_change': 2,
          'gate_metric_tension': 2, 'gate_overlay_tension': 2}
RULE = 'gate_flip × metric_delta(warn|crit)'
THRESHOLDS = dict(abs_warn=0.01, abs_crit=0.05, rel_warn=0.01, rel_crit=0.05)


def encoded(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      allow_nan=False, separators=(',', ':')).encode('utf-8')


def digest(value: Any) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def strict_json(raw: str | bytes) -> Any:
    def pairs(items):
        obj = {}
        for k, v in items:
            if k in obj:
                raise ValueError('duplicate JSON member: ' + k)
            obj[k] = v
        return obj
    def reject(v):
        raise ValueError('nonfinite JSON number: ' + v)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)


def differences(a: Any, b: Any, path: str = '') -> list[dict]:
    """Type-sensitive structural diff, never Python's bool == int coercion."""
    if type(a) is not type(b):
        return [{'path': path, 'before': a, 'after': b}]
    if isinstance(a, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            p = path + '/' + k.replace('~', '~0').replace('/', '~1')
            if k not in a or k not in b:
                out.append({'path': p, 'before': a.get(k), 'after': b.get(k),
                            'presence_before': k in a, 'presence_after': k in b})
            else:
                out.extend(differences(a[k], b[k], p))
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [{'path': path, 'before': a, 'after': b}]
        return [d for i, (u, v) in enumerate(zip(a, b))
                for d in differences(u, v, path + '/' + str(i))]
    return [] if a == b else [{'path': path, 'before': a, 'after': b}]


def index_unique(items: Any, key: str) -> dict[str, dict]:
    if not isinstance(items, list) or not items:
        raise ValueError('missing or empty ' + key + ' lookup')
    result = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('non-object record')
        value = item.get(key)
        if not isinstance(value, str) or not value or value.strip() != value:
            raise ValueError('missing/noncanonical ' + key)
        if value in result:
            raise ValueError('ambiguous duplicate ' + key + ': ' + value)
        result[value] = item
    return result


def order_key(item: dict, key: str) -> tuple:
    return RANK[item['severity']], item['type'], item[key]


def semantic_projection(field: dict, edges: list[dict]) -> dict:
    """Phi_sem excludes titles, list order, paths and byte-level serialization.
    It retains full source payloads, aliases, summaries and recorded context.
    """
    root = field['paradox_field_v0']
    atoms = index_unique(root['atoms'], 'atom_id')
    edge_map = index_unique(edges, 'edge_id')
    return {
        'atoms': [{k: v for k, v in atoms[i].items() if k != 'title'} for i in sorted(atoms)],
        'edges': [edge_map[i] for i in sorted(edge_map)],
        'context': root['meta']['run_context'],
        'contract': root['meta']['contract'],
    }


def admitted_sources(evidence: dict) -> tuple[dict[str, bytes], list, list]:
    accepted, missing, invalid = {}, [], []
    if not isinstance(evidence, dict) or set(evidence) - set(INPUT_BLOBS):
        raise ValueError('evidence view contains undeclared sources')
    for name, expected in INPUT_BLOBS.items():
        value = evidence.get(name)
        if value is None:
            missing.append(name)
            continue
        if not isinstance(value, str):
            invalid.append({'source': name, 'reason': 'not UTF-8 source text'})
            continue
        raw = value.encode('utf-8')
        actual = blob(raw)
        if actual != expected:
            invalid.append({'source': name, 'reason': 'pinned source binding mismatch',
                            'expected_git_blob_sha1': expected, 'actual_git_blob_sha1': actual,
                            'actual_sha256': hashlib.sha256(raw).hexdigest()})
        else:
            accepted[name] = raw
    return accepted, missing, invalid


def reconstruct(accepted: dict[str, bytes]) -> tuple[dict, list[dict], dict]:
    """Independent closed-form reconstruction of this four-file fixture only.
    Requires every source premise; never completes a missing source from a
    producer payload, previous certificate or familiar fixture values.
    """
    if set(accepted) != set(INPUT_BLOBS):
        raise ValueError('complete admitted sources required')
    for name, raw in accepted.items():
        if blob(raw) != INPUT_BLOBS[name]:
            raise ValueError('source changed after admission')
    gate_rows = list(csv.DictReader(io.StringIO(accepted['pulse_gate_drift_v0.csv'].decode())))
    metric_rows = list(csv.DictReader(io.StringIO(accepted['pulse_metric_drift_v0.csv'].decode())))
    overlays = strict_json(accepted['pulse_overlay_drift_v0.json'])
    transitions = strict_json(accepted['pulse_transitions_v0.json'])
    if len(gate_rows) != 1 or len(metric_rows) != 2:
        raise ValueError('outside the fixed fixture domain')
    ctx = {CONTEXT_KEYS[n]: hashlib.sha1(raw).hexdigest() for n, raw in accepted.items()}
    ctx['run_pair_id'] = hashlib.sha1('|'.join(k+'='+ctx[k] for k in sorted(ctx)).encode()).hexdigest()[:12]
    a, b = (transitions[k]['status_sha1'] for k in ('run_a', 'run_b'))
    def aid(kind, key, left=a, right=b):
        return hashlib.sha1('|'.join((kind, key, left, right)).encode()).hexdigest()[:12]
    def tension_id(kind, src, dst):
        return hashlib.sha1(':'.join((kind, src, dst)).encode()).hexdigest()[:12]
    def edge_id(kind, src, dst, tid):
        return hashlib.sha1('|'.join((kind, src, dst, tid, ctx['run_pair_id'])).encode()).hexdigest()[:16]
    gate = gate_rows[0]
    if gate['flip'] != '1' or gate['gate_id'] != 'gate_latency_budget':
        raise ValueError('wrong gate subject')
    gate_data = {k: gate[k] for k in ('gate_id', 'group', 'status_a', 'status_b',
                 'value_a', 'value_b', 'threshold', 'notes_a', 'notes_b')}
    gate_data.update(pass_a=gate['pass_a'] == 'true', pass_b=gate['pass_b'] == 'true', flip=1)
    gid = aid('gate_flip', gate['gate_id'])
    atoms = [{'atom_id': gid, 'type': 'gate_flip', 'severity': 'crit',
              'refs': {'gates': [gate['gate_id']], 'metrics': [], 'overlays': []},
              'evidence': {'source': {'gate_drift_csv': 'pulse_gate_drift_v0.csv', 'row_index': 0},
                           'gate': gate_data,
                           'presence': {k: gate[k] for k in ('present_a', 'present_b')}}}]
    edges, subjects = [], {}
    for row_index, row in enumerate(metric_rows):
        name = row['metric']
        metric_data = {'name': name, **{k: float(row[k]) for k in ('a', 'b', 'delta', 'rel_delta')}}
        size = max(abs(Decimal(row['delta'])), abs(Decimal(row['rel_delta'])))
        severity = 'crit' if size >= Decimal('0.05') else 'warn' if size >= Decimal('0.01') else 'info'
        if severity == 'info':
            raise ValueError('ineligible fixed metric')
        mid = aid('metric_delta', name)
        atoms.append({'atom_id': mid, 'type': 'metric_delta', 'severity': severity,
            'refs': {'gates': [], 'metrics': [name], 'overlays': []},
            'evidence': {'source': {'metric_drift_csv': 'pulse_metric_drift_v0.csv', 'row_index': row_index},
                         'metric': metric_data, 'thresholds': THRESHOLDS.copy(),
                         'presence': {k: row[k] for k in ('present_a', 'present_b')}}})
        kind = 'gate_metric_tension'; tid = tension_id(kind, gid, mid); eid = edge_id(kind, gid, mid, tid)
        atoms.append({'atom_id': tid, 'type': kind, 'severity': 'crit',
            'refs': {'gates': [gate['gate_id']], 'metrics': [name], 'overlays': []},
            'evidence': {'gate_atom_id': gid, 'metric_atom_id': mid, 'src_atom_id': gid,
                         'dst_atom_id': mid, 'rule': RULE, 'gate': gate_data, 'metric': metric_data}})
        edges.append({'edge_id': eid, 'type': kind, 'severity': 'crit', 'src_atom_id': gid,
                      'dst_atom_id': mid, 'tension_atom_id': tid, 'rule': RULE, 'run_context': ctx})
        subjects[name] = {'snapshot': SNAPSHOT, 'gate_id': gate['gate_id'], 'metric_name': name,
                          'gate_atom_id': gid, 'metric_atom_id': mid, 'tension_atom_id': tid,
                          'edge_id': eid, 'source_row_index': row_index}
    if set(overlays) != {'g_field_v0', 'paradox_field_v0'}:
        raise ValueError('wrong overlay subjects')
    for name in sorted(overlays):
        row = overlays[name]; diff = row['top_level_diff']
        if not diff['changed_keys']:
            raise ValueError('missing fixed overlay change')
        oid = aid('overlay_change', name, row['sha1_a'], row['sha1_b'])
        overlay_data = {'name': name, **{k: row[k] for k in ('present_a','present_b','path_a','path_b','sha1_a','sha1_b')},
                        'top_level_diff': copy.deepcopy(diff)}
        atoms.append({'atom_id': oid, 'type': 'overlay_change', 'severity': 'info',
            'refs': {'gates': [], 'metrics': [], 'overlays': [name]},
            'evidence': {'source': {'overlay_drift_json': 'pulse_overlay_drift_v0.json', 'overlay_name': name,
                         'json_pointer': '/'+name, 'json_pointer_top_level_diff': '/'+name+'/top_level_diff'},
                         'overlay': overlay_data}})
        kind = 'gate_overlay_tension'; rule = 'gate_flip × overlay_change'
        tid = tension_id(kind, gid, oid)
        atoms.append({'atom_id': tid, 'type': kind, 'severity': 'crit',
            'refs': {'gates': [gate['gate_id']], 'metrics': [], 'overlays': [name]},
            'evidence': {'gate_atom_id': gid, 'overlay_atom_id': oid, 'src_atom_id': gid,
                         'dst_atom_id': oid, 'rule': rule, 'gate': gate_data,
                         'overlay': {'name': name, 'changed_keys_sample': diff['changed_keys'][:12]}}})
        edges.append({'edge_id': edge_id(kind,gid,oid,tid), 'type': kind, 'severity': 'crit',
                      'src_atom_id': gid, 'dst_atom_id': oid, 'tension_atom_id': tid,
                      'rule': rule, 'run_context': ctx})
    index_unique(atoms,'atom_id'); index_unique(edges,'edge_id')
    atoms.sort(key=lambda r: order_key(r,'atom_id')); edges.sort(key=lambda r: order_key(r,'edge_id'))
    contract = {'atoms_sorted_by': ['severity','type','atom_id'], 'severity_order': ['crit','warn','info'],
                'metric_thresholds': THRESHOLDS.copy(),
                'tension_overlays_allowlist': ['g_field_v0','paradox_field_v0']}
    field = {'paradox_field_v0': {'atoms': atoms, 'meta': {'contract': contract, 'run_context': ctx}}}
    return field, edges, subjects


def complete_lookup(field: dict, edges: list[dict]) -> tuple[dict, dict]:
    root = field['paradox_field_v0']; atoms = index_unique(root['atoms'], 'atom_id')
    es = index_unique(edges,'edge_id')
    if len(atoms) != 9 or len(es) != 4:
        raise ValueError('incomplete fixed fixture population')
    counts = {k: sum(a.get('type') == k for a in atoms.values()) for k in COUNTS}
    if counts != COUNTS:
        raise ValueError('incomplete typed Atom population')
    if {k: sum(e.get('type') == k for e in es.values()) for k in ('gate_metric_tension','gate_overlay_tension')} != {'gate_metric_tension': 2,'gate_overlay_tension': 2}:
        raise ValueError('incomplete typed edge population')
    ctx = root['meta']['run_context']
    if not isinstance(ctx,dict) or not set(CONTEXT_KEYS.values()) | {'run_pair_id'} <= set(ctx):
        raise ValueError('incomplete context')
    for e in es.values():
        for k in ('src_atom_id','dst_atom_id','tension_atom_id'):
            if e.get(k) not in atoms:
                raise ValueError('unresolved '+k)
    return atoms, es


def assess(envelope: dict) -> dict:
    """Only these typed inputs are admitted. Scenario IDs are not accepted."""
    allowed = {'field','edges','subject','evidence','presented_certificate'}
    if not isinstance(envelope,dict) or set(envelope) - allowed:
        raise ValueError('unknown inference input; scenario labels are not evidence')
    field, edges, subject = (envelope[k] for k in ('field','edges','subject'))
    evidence = envelope['evidence']; old = envelope.get('presented_certificate')
    out = {'coverage_status': 'INCOMPLETE', 'reference_relation_assessment': 'UNRESOLVED',
           'reference_source_assessment': 'UNRESOLVED', 'proof_applicability_assessment': 'NOT_JUSTIFIED',
           'carrier_assessment': 'UNRESOLVED', 'authority_effect': 'none',
           'certificate': None, 'certificate_reuse': 'NOT_PRESENTED' if old is None else 'NOT_JUSTIFIED',
           'witnesses': [], 'unresolved_obligations': [], 'selected_subject': subject,
           'evidence_view_identity': digest(evidence)}
    try:
        atoms, es = complete_lookup(field,edges)
        e = es[subject['edge_id']]; t = atoms[e['tension_atom_id']]
        g = atoms[e['src_atom_id']]; m = atoms[e['dst_atom_id']]; ev = t['evidence']
        checks = {
            'types': [e['type'],t['type'],g['type'],m['type']] == ['gate_metric_tension','gate_metric_tension','gate_flip','metric_delta'],
            'tension_identity': e['tension_atom_id'] == t['atom_id'],
            'source_binding': e['src_atom_id'] == ev.get('gate_atom_id') == ev.get('src_atom_id') == g['atom_id'],
            'destination_binding': e['dst_atom_id'] == ev.get('metric_atom_id') == ev.get('dst_atom_id') == m['atom_id'],
            'severity_agreement': e['severity'] == t['severity'],
            'rule_agreement': e['rule'] == ev.get('rule'),
        }
        out['coverage_status'] = 'COMPLETE_FOR_DECLARED_CASE'
        out['link_checks'] = checks
        out['reference_relation_assessment'] = 'SATISFIED' if all(checks.values()) else 'VIOLATED'
        out['witnesses'].append({'kind':'joint_binding','edge_id':e['edge_id'],
              'edge_destination':e['dst_atom_id'], 'tension_metric_id':ev.get('metric_atom_id'),
              'tension_alias_destination':ev.get('dst_atom_id'), 'resolved_metric_id':m['atom_id'],
              'resolved_metric_name':m.get('evidence',{}).get('metric',{}).get('name'),
              'selected_metric_name':subject['metric_name']})
        akeys = [order_key(a,'atom_id') for a in field['paradox_field_v0']['atoms']]
        ekeys = [order_key(a,'edge_id') for a in edges]
        out['carrier_assessment'] = ('ENDPOINT_BINDING_INVALID' if not all(checks.values()) else
            'FIELD_ORDER_INVALID' if akeys != sorted(akeys) else
            'EDGE_ORDER_INVALID' if ekeys != sorted(ekeys) else 'CANONICAL')
        projection = semantic_projection(field,edges)
        out['semantic_projection_sha256'] = digest(projection)
        accepted, missing, invalid = admitted_sources(evidence)
        out['accepted_source_sha256'] = {n: hashlib.sha256(b).hexdigest() for n,b in sorted(accepted.items())}
        out['missing_source_premises'] = missing
        if invalid:
            out['reference_source_assessment'] = 'CONTRADICTED'; out['witnesses'].extend(invalid)
        elif missing:
            out['unresolved_obligations'] = ['source premise unavailable: '+n for n in missing]
        else:
            rf, re, rs = reconstruct(accepted)
            delta = differences(semantic_projection(rf,re),projection)
            expected_subject = rs.get(subject['metric_name'])
            if expected_subject is None or encoded(expected_subject) != encoded(subject):
                delta.append({'path':'/selected_subject','before':expected_subject,'after':subject})
            out['source_differences'] = delta
            out['reference_source_assessment'] = 'CONTRADICTED' if delta else 'JUSTIFIED_WITHIN_FIXTURE_BOUNDARY'
            if delta: out['witnesses'].extend(delta)
            elif all(checks.values()):
                cert = {'claim':'source-bound gate-metric relation','snapshot':SNAPSHOT,'subject':subject,
                        'evidence_view_identity':out['evidence_view_identity'],
                        'source_sha256':out['accepted_source_sha256'],
                        'semantic_projection_sha256':out['semantic_projection_sha256'],
                        'derivation_rule':'all four admitted raw sources + independent fixture reconstruction + exact subject and link equalities',
                        'authority_effect':'none'}
                out['certificate'] = cert
                out['proof_applicability_assessment'] = 'JUSTIFIED_FOR_SELECTED_TARGET'
                if old is not None and old.get('subject') != subject:
                    out['proof_applicability_assessment'] = 'NEW_TARGET_PROOF_REQUIRED_AND_SEPARATELY_JUSTIFIED'
        if old is not None:
            if not isinstance(old,dict) or old.get('subject') != subject:
                out['certificate_reuse'] = 'SUBJECT_MISMATCH'
            elif old.get('evidence_view_identity') != out['evidence_view_identity']:
                out['certificate_reuse'] = 'EVIDENCE_VIEW_MISMATCH'
            elif out['certificate'] is None:
                out['certificate_reuse'] = 'NO_CURRENT_GROUNDED_DERIVATION'
            elif encoded(old) == encoded(out['certificate']):
                out['certificate_reuse'] = 'RECHECKED_FOR_SAME_TARGET_AND_EVIDENCE'
            else:
                out['certificate_reuse'] = 'CERTIFICATE_MISMATCH'
    except (KeyError, ValueError, TypeError, IndexError) as exc:
        out['coverage_status'] = 'INCOMPLETE'
        out['reference_relation_assessment'] = 'UNRESOLVED'
        out['reference_source_assessment'] = 'UNRESOLVED'
        out['proof_applicability_assessment'] = 'NOT_JUSTIFIED'
        out['certificate'] = None
        out['unresolved_obligations'].append(type(exc).__name__+': '+str(exc))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('refuse to overwrite an assessment')
    result = assess(strict_json(args.input.read_bytes()))
    args.output.write_bytes(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False).encode()+b'\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
