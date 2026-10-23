"""Exercise the actual embedded repo-hygiene version guard on bounded fixtures.

Uses PyYAML already installed by repo_hygiene.yml; it is not an E0 dependency.
The synthetic workflows exercise validation, not hosted interpreter execution.
"""
from __future__ import annotations
import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MATRIX_PATH = '.github/workflows/paradox_compatibility_v0.yml'
HYGIENE_PATH = '.github/workflows/repo_hygiene.yml'
Q2_JOBS = {
    '.github/workflows/q2_reference_acquisition_v0.yml': ['acquire'],
    '.github/workflows/pulse_ci.yml': ['pulse', 'tools-tests'],
    '.github/workflows/q2_release_capsule_publication_v0.yml': ['build', 'verify_download'],
    '.github/workflows/q2_release_host_tokenizer_verification_v0.yml': ['verify_host'],
    '.github/workflows/q2_release_host_worker_verification_v0.yml': ['verify_host'],
}


def get_guard():
    doc = yaml.load((ROOT / HYGIENE_PATH).read_text(), Loader=yaml.BaseLoader)
    steps = doc['jobs']['hygiene_guardrails']['steps']
    step = next(x for x in steps if x.get('name', '').startswith('Repo hygiene: enforce Python version sync'))
    body = step['run'].split("python3 - <<'PY'\n", 1)[1]
    return body.rsplit('\nPY', 1)[0] + '\n'


def minimal_workflow(jobs, version='3.11.16'):
    return {'name': 'synthetic guard fixture', 'on': {'workflow_dispatch': {}},
            'jobs': {name: {'runs-on': 'ubuntu-24.04', 'steps': [
                {'uses': 'actions/setup-python@' + '1' * 40, 'with': {'python-version': version}}]}
                     for name in jobs}}


def check_variant(mutation):
    doc = yaml.load((ROOT / MATRIX_PATH).read_text(), Loader=yaml.BaseLoader)
    with tempfile.TemporaryDirectory(prefix='pd-matrix-guard-') as td:
        root = Path(td); (root / '.github/workflows').mkdir(parents=True)
        (root / 'environment.yml').write_text('dependencies:\n  - python=3.11\n')
        for name, jobs in Q2_JOBS.items():
            (root / name).write_text(yaml.safe_dump(minimal_workflow(jobs), sort_keys=False))
        (root / '.github/workflows/ordinary.yml').write_text(yaml.safe_dump(minimal_workflow(['plain'], '3.11'), sort_keys=False))
        steps = doc['jobs']['compatibility']['steps']
        setups = [x for x in steps if x.get('uses', '').startswith('actions/setup-python@')]
        if mutation == 'version': setups[0]['with']['python-version'] = '3.11.15'
        elif mutation == 'missing': steps.remove(setups[0])
        elif mutation == 'duplicate': steps.append(copy.deepcopy(setups[0]))
        elif mutation == 'step-id': setups[0]['id'] = 'other'
        elif mutation == 'extra-job': doc['jobs']['other'] = copy.deepcopy(doc['jobs']['compatibility'])
        elif mutation == 'automatic-trigger': doc['on']['push'] = {}
        elif mutation == 'dynamic-version': setups[0]['with']['python-version'] = '${{ inputs.version }}'
        elif mutation == 'extra-declaration': steps.append({'run': 'true', 'with': {'python-version': '3.11'}})
        elif mutation == 'wrong-job': doc['jobs']['renamed'] = doc['jobs'].pop('compatibility')
        target = root / MATRIX_PATH
        target.write_text(yaml.safe_dump(doc, sort_keys=False))
        if mutation == 'rename': target.rename(target.with_name('other_compatibility.yml'))
        elif mutation == 'symlink':
            stored = root / 'saved-workflow'; target.rename(stored); target.symlink_to(stored)
        elif mutation == 'absent-optional-matrix': target.unlink()
        elif mutation == 'ordinary-drift':
            p = root / '.github/workflows/ordinary.yml';p.write_text(p.read_text().replace('3.11', '3.13.5'))
        elif mutation == 'q2-drift':
            p = root / '.github/workflows/q2_reference_acquisition_v0.yml';p.write_text(p.read_text().replace('3.11.16', '3.11.15'))
        elif mutation == 'missing-q2': (root / '.github/workflows/q2_reference_acquisition_v0.yml').unlink()
        elif mutation == 'bad-yaml': target.write_text('on: [invalid\njobs: !\n')
        proc = subprocess.run([sys.executable, '-B', '-c', get_guard()], cwd=root,
                              stdin=subprocess.DEVNULL, capture_output=True, text=True,
                              timeout=10, env={'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'LANG': 'C.UTF-8'})
        return proc


class WorkflowGuardControls(unittest.TestCase):
    def accept(self, variant):
        result = check_variant(variant)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def reject(self, variant):
        result = check_variant(variant)
        self.assertNotEqual(result.returncode, 0, 'unexpected acceptance: ' + variant)
        self.assertIn('::error', result.stdout, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stderr, result.stderr)

    def test_01_exact_matrix_accepted(self): self.accept('valid')
    def test_02_changed_patch_rejected(self): self.reject('version')
    def test_03_missing_setup_rejected(self): self.reject('missing')
    def test_04_duplicate_setup_rejected(self): self.reject('duplicate')
    def test_05_changed_step_id_rejected(self): self.reject('step-id')
    def test_06_extra_job_rejected(self): self.reject('extra-job')
    def test_07_automatic_trigger_rejected(self): self.reject('automatic-trigger')
    def test_08_dynamic_version_rejected(self): self.reject('dynamic-version')
    def test_09_extra_declaration_rejected(self): self.reject('extra-declaration')
    def test_10_changed_job_id_rejected(self): self.reject('wrong-job')
    def test_11_renamed_workflow_gets_no_exception(self): self.reject('rename')
    def test_12_symlink_does_not_get_exception(self): self.reject('symlink')
    def test_13_ordinary_pin_still_enforced(self): self.reject('ordinary-drift')
    def test_14_q2_pin_still_enforced(self): self.reject('q2-drift')
    def test_15_missing_q2_still_rejected(self): self.reject('missing-q2')
    def test_16_malformed_workflow_rejected(self): self.reject('bad-yaml')
    def test_17_optional_matrix_does_not_change_existing_fixture_contracts(self): self.accept('absent-optional-matrix')


if __name__ == '__main__':
    unittest.main(verbosity=2)
