"""Standard-library controls for the isolated PD-SM-01-E0 experiment.
These are harness checks, not changes to the existing project checkers.
"""
from __future__ import annotations

import ast
import copy
import io
import json
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import independent_reference as ref
import run_cases as run


class Controls(unittest.TestCase):
    context={}
    details={}

    def envelope(self, metric='p99_latency', restricted=False, certificate=None):
        c=self.context; ev=copy.deepcopy(c['evidence'])
        if restricted: del ev['pulse_metric_drift_v0.csv']
        return run.make_envelope(copy.deepcopy(c['baseline']),copy.deepcopy(c['edges']),
                                 copy.deepcopy(c['subjects'][metric]),ev,certificate)

    def observe(self, label, envelope):
        c=self.context;d=c['runner'].work/'controls'/label;d.mkdir(parents=True)
        inp=d/'input.json';out=d/'output.json';run.write_json(inp,envelope)
        proc=c['runner'].run('controls/'+label,[c['python'],'-I','-B',HERE/'independent_reference.py',
                              '--input',inp,'--output',out],[inp])
        self.assertEqual(proc['returncode'],0)
        value=ref.strict_json(out.read_bytes())
        return value,{'input':run.file_record(inp),'output':run.file_record(out),'process':proc}

    def test_G01_lookup_coverage(self):
        outcomes=[]
        for label in ('missing','empty','ambiguous','missing_metric'):
            env=self.envelope()
            atoms=env['field']['paradox_field_v0']['atoms']
            if label=='missing': del env['field']['paradox_field_v0']['atoms']
            elif label=='empty': atoms.clear()
            elif label=='ambiguous': atoms.append(copy.deepcopy(atoms[0]))
            else:
                mid=env['subject']['metric_atom_id']
                env['field']['paradox_field_v0']['atoms']=[a for a in atoms if a['atom_id']!=mid]
            value,evidence=self.observe('G01_'+label,env)
            self.assertEqual(value['coverage_status'],'INCOMPLETE')
            self.assertIsNone(value['certificate']);outcomes.append(evidence)
        c=self.context;env=self.envelope();env['field']['paradox_field_v0']['atoms']=[]
        p=c['runner'].work/'controls/G01_empty_probe';p.mkdir()
        fp=p/'field.json';ep=p/'edges.jsonl';run.write_json(fp,env['field']);ep.write_bytes(run.dump_edges(env['edges']))
        obs=c['runner'].run('controls/G01_empty_checker_probe',c['cmd']('edge_checker',['--in',ep,'--atoms',fp]),[ep,fp])
        # Preserve the known limitation, never count this as link coverage.
        self.assertEqual(obs['returncode'],0)
        self.details['G01']={'reference_controls':outcomes,'empty_lookup_checker_observation':obs,
                             'interpretation':'legacy checker exit 0 does not establish coverage'}

    def test_G02_source_binding(self):
        env=self.envelope();name='pulse_metric_drift_v0.csv';old=env['evidence'][name]
        self.assertEqual(old.count(',0.080,'),1)
        env['evidence'][name]=old.replace(',0.080,',',0.081,',1)
        value,evidence=self.observe('G02_changed_source',env)
        self.assertEqual(value['reference_relation_assessment'],'SATISFIED')
        self.assertEqual(value['reference_source_assessment'],'CONTRADICTED')
        self.assertIsNone(value['certificate'])
        self.details['G02']={'observation':evidence,'mutation':{'field':'latency delta',
                            'from':'0.080','to':'0.081','binding_retained':ref.INPUT_BLOBS[name]},
                            'witnesses':value['witnesses']}

    def test_G03_rejection_specificity(self):
        c=self.context;expected=next(x for x in c['expectations']['scenarios'] if x['scenario_id']=='E20')['expected']['existing_programs']['edge_checker']
        stimuli=[('wrong_diagnostic','raise SystemExit("unrelated control failure")',30,'MISMATCH'),
                 ('signal','import os,signal; os.kill(os.getpid(),signal.SIGTERM)',30,'INCOMPLETE'),
                 ('timeout','import time; time.sleep(2)',0.05,'INCOMPLETE')]
        observations=[]
        for label,code,timeout,want in stimuli:
            obs=c['runner'].run('controls/G03_'+label,[c['python'],'-I','-B','-c',code],timeout=timeout)
            actual=run.compare_program(expected,obs,True)
            self.assertEqual(actual,want);observations.append({'observation':obs,'comparison':actual})
        self.details['G03']={'controls':observations,'production_checkers_modified':False}

    def test_G04_stale_evidence(self):
        old=copy.deepcopy(self.context['certificate'])
        full=self.envelope();restricted=self.envelope(restricted=True,certificate=old)
        self.assertNotIn('pulse_metric_drift_v0.csv',restricted['evidence'])
        value,evidence=self.observe('G04_restricted_with_old_certificate',restricted)
        self.assertEqual(value['reference_relation_assessment'],'SATISFIED')
        self.assertEqual(value['reference_source_assessment'],'UNRESOLVED')
        self.assertEqual(value['proof_applicability_assessment'],'NOT_JUSTIFIED')
        self.assertEqual(value['certificate_reuse'],'EVIDENCE_VIEW_MISMATCH')
        self.assertIsNone(value['certificate'])
        # A reused Python process must also be free of accepted-evidence caches.
        self.assertIsNotNone(ref.assess(full)['certificate'])
        self.assertIsNone(ref.assess(restricted)['certificate'])
        self.assertIsNotNone(ref.assess(full)['certificate'])
        self.details['G04']={'fresh_subprocess':evidence,'same_process_full_restricted_full':'correctly separated',
                            'missing_premises':value['missing_source_premises']}

    def test_G05_wrong_target_proof(self):
        old=copy.deepcopy(self.context['certificate']);retained=ref.digest(old)
        value,evidence=self.observe('G05_cpu_with_latency_certificate',self.envelope('cpu_util',certificate=old))
        self.assertEqual(value['certificate_reuse'],'SUBJECT_MISMATCH')
        self.assertEqual(value['proof_applicability_assessment'],'NEW_TARGET_PROOF_REQUIRED_AND_SEPARATELY_JUSTIFIED')
        self.assertEqual(value['certificate']['subject']['metric_name'],'cpu_util')
        self.assertNotEqual(value['certificate']['subject'],old['subject'])
        self.assertEqual(ref.digest(old),retained)
        restricted,ev2=self.observe('G05_cpu_without_source',self.envelope('cpu_util',True,old))
        self.assertEqual(restricted['proof_applicability_assessment'],'NOT_JUSTIFIED')
        self.details['G05']={'new_target_observation':evidence,'missing_source_control':ev2,
                            'old_certificate_sha256':retained,'old_certificate_unchanged':True}

    def test_G06_result_completeness(self):
        c=self.context;spec=c['expectations']['scenarios'][0]['expected'];original=c['cases']['E00']
        cases=[]
        missing=copy.deepcopy(original);del missing['program_observations']['edge_checker']
        outcome,why=run.compare_case(spec,missing);self.assertEqual(outcome,'INCOMPLETE')
        cases.append({'missing':'stage','outcome':outcome,'details':why})
        missing=copy.deepcopy(original);missing['program_observations']['edge_checker']['stderr']['path']+='-absent'
        outcome,why=run.compare_case(spec,missing);self.assertEqual(outcome,'INCOMPLETE')
        cases.append({'missing':'log','outcome':outcome,'details':why})
        missing=copy.deepcopy(original);missing['reference_result_file']['path']+='-absent'
        outcome,why=run.compare_case(spec,missing);self.assertEqual(outcome,'INCOMPLETE')
        cases.append({'missing':'reference output','outcome':outcome,'details':why})
        reduced=copy.deepcopy(c['cases']);del reduced['E40']
        self.assertEqual(run.complete_summary(c['expectations'],reduced,{}),'INCOMPLETE')
        cases.append({'missing':'scenario','outcome':'INCOMPLETE'})
        self.details['G06']={'negative_completeness_assessments':cases,'original_logs_deleted':False}


class ReferenceRegressions(Controls):
    """Additional unit checks are selected by name, not inherited G controls."""
    def test_R01_no_case_labels(self):
        env=self.envelope();env['scenario_id']='E00'
        with self.assertRaisesRegex(ValueError,'unknown inference input'): ref.assess(env)

    def test_R02_label_independence(self):
        env=self.envelope();results=[]
        for label in ('arbitrary_A','arbitrary_B'):
            value,_=self.observe('R02_'+label,copy.deepcopy(env));results.append(value)
        self.assertEqual(results[0],results[1])

    def test_R03_duplicate_json_members(self):
        with self.assertRaisesRegex(ValueError,'duplicate'): ref.strict_json('{"x":1,"x":2}')

    def test_R04_nonfinite_json(self):
        for number in ('NaN','Infinity','-Infinity'):
            with self.assertRaises(ValueError): ref.strict_json('{"x":'+number+'}')

    def test_R05_typed_difference(self):
        self.assertNotEqual(ref.differences({'v':True},{'v':1}),[])

    def test_R06_summary_not_id(self):
        env=self.envelope();tid=env['subject']['tension_atom_id']
        t=next(a for a in env['field']['paradox_field_v0']['atoms'] if a['atom_id']==tid)
        t['evidence']['metric']['delta']=42.0
        result=ref.assess(env)
        self.assertEqual(result['reference_relation_assessment'],'SATISFIED')
        self.assertEqual(result['reference_source_assessment'],'CONTRADICTED')
        self.assertIsNone(result['certificate'])

    def test_R07_alias_binding(self):
        env=self.envelope();tid=env['subject']['tension_atom_id']
        t=next(a for a in env['field']['paradox_field_v0']['atoms'] if a['atom_id']==tid)
        t['evidence']['dst_atom_id']=self.context['subjects']['cpu_util']['metric_atom_id']
        self.assertEqual(ref.assess(env)['reference_relation_assessment'],'VIOLATED')

    def test_R08_consistent_rule_rewrite(self):
        env=self.envelope();tid=env['subject']['tension_atom_id'];eid=env['subject']['edge_id']
        next(a for a in env['field']['paradox_field_v0']['atoms'] if a['atom_id']==tid)['evidence']['rule']='invented'
        next(e for e in env['edges'] if e['edge_id']==eid)['rule']='invented'
        result=ref.assess(env)
        self.assertEqual(result['reference_relation_assessment'],'SATISFIED')
        self.assertEqual(result['reference_source_assessment'],'CONTRADICTED')

    def test_R09_context_not_self_authenticating(self):
        env=self.envelope();root=env['field']['paradox_field_v0']
        root['meta']['run_context']['transitions_metric_csv_sha1']='0'*40
        for e in env['edges']: e['run_context']['transitions_metric_csv_sha1']='0'*40
        self.assertEqual(ref.assess(env)['reference_source_assessment'],'CONTRADICTED')

    def test_R10_duplicate_collection_preserved(self):
        env=self.envelope();env['edges'].append(copy.deepcopy(env['edges'][0]))
        with self.assertRaisesRegex(ValueError,'ambiguous'): ref.semantic_projection(env['field'],env['edges'])
        self.assertEqual(ref.assess(env)['coverage_status'],'INCOMPLETE')

    def test_R11_reference_import_boundary(self):
        tree=ast.parse((HERE/'independent_reference.py').read_text())
        modules=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Import): modules.update(x.name.split('.')[0] for x in node.names)
            elif isinstance(node,ast.ImportFrom): modules.add((node.module or '').split('.')[0])
        self.assertTrue(modules <= {'__future__','argparse','copy','csv','hashlib','io','json','decimal','pathlib','typing'})
        self.assertNotIn('run_cases',modules)

    def test_R12_certificate_recheck(self):
        env=self.envelope(certificate=copy.deepcopy(self.context['certificate']))
        value=ref.assess(env)
        self.assertEqual(value['certificate_reuse'],'RECHECKED_FOR_SAME_TARGET_AND_EVIDENCE')
        env['presented_certificate']['derivation_rule']='unverified claim'
        self.assertEqual(ref.assess(env)['certificate_reuse'],'CERTIFICATE_MISMATCH')


class RecordedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.records=[]
    def addSuccess(self,test):
        super().addSuccess(test);self.records.append({'test':test.id(),'result':'MATCH'})
    def addFailure(self,test,err):
        super().addFailure(test,err);self.records.append({'test':test.id(),'result':'MISMATCH','detail':self._exc_info_to_string(err,test)})
    def addError(self,test,err):
        super().addError(test,err);self.records.append({'test':test.id(),'result':'INCOMPLETE','detail':self._exc_info_to_string(err,test)})


def run_controls(context):
    Controls.context=context;Controls.details={};ReferenceRegressions.context=context
    suite=unittest.TestSuite()
    for name in sorted(n for n in dir(Controls) if n.startswith('test_G')): suite.addTest(Controls(name))
    for name in sorted(n for n in dir(ReferenceRegressions) if n.startswith('test_R')): suite.addTest(ReferenceRegressions(name))
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=RecordedResult).run(suite)
    root=context['output']/'controls';root.mkdir()
    (root/'unittest.log').write_text(stream.getvalue())
    controls={}
    for gid in run.CONTROLS:
        records=[r for r in result.records if '.test_'+gid+'_' in r['test']]
        status=records[0]['result'] if len(records)==1 else 'INCOMPLETE'
        detail=Controls.details.get(gid,{})
        if not detail: status='INCOMPLETE'
        path=root/(gid+'.json');run.write_json(path,{'control_id':gid,'result':status,'assertions':records,'observations':detail})
        controls[gid]={'execution':'COMPLETED','result':status,'evidence':run.file_record(path)}
    summary={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
             'successful':result.wasSuccessful(),'records':result.records,'log':run.file_record(root/'unittest.log')}
    run.write_json(root/'summary.json',summary)
    return controls,summary


if __name__=='__main__':
    raise SystemExit('Run via run_cases.py so the controls share one bound, preserved experiment context.')
