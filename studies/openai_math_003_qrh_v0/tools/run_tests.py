"""Run real unittest cases and preserve per-case outcomes as structured data."""
from __future__ import annotations
import argparse
import datetime as dt
import io
from pathlib import Path
import sys
import time
import traceback
import unittest

try:
    from .common import canonical_bytes, write_json
except ImportError:
    from common import canonical_bytes, write_json

ROOT = Path(__file__).absolute().parents[1]


class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []
        self.start_times = {}

    def startTest(self, test):
        self.start_times[test.id()] = time.monotonic()
        super().startTest(test)

    def record(self, test, outcome, detail=''):
        self.records.append({'id': test.id(), 'outcome': outcome, 'detail': detail,
            'elapsed_seconds': round(time.monotonic() - self.start_times.get(test.id(), time.monotonic()), 6),
            'trust_domain': 'TEST', 'fixture_evidence_is_production': False})

    def addSuccess(self, test):
        super().addSuccess(test)
        self.record(test, 'PASS')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.record(test, 'FAIL', self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self.record(test, 'ERROR', self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.record(test, 'SKIP', reason)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.record(test, 'EXPECTED_FAILURE', self._exc_info_to_string(err, test))

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.record(test, 'UNEXPECTED_SUCCESS')


def run(output, pattern='test_*.py'):
    stream = io.StringIO()
    started = dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern=pattern)
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result).run(suite)
    report = {'schema_version': 'qrh003_test_execution_v1', 'started_utc': started,
              'return_code': 0 if result.wasSuccessful() else 1, 'timed_out': False,
              'tests_run': result.testsRun, 'tests': result.records,
              'runner_text': stream.getvalue(), 'execution_is_actual': True,
              'synthetic_inputs_remain_test_evidence': True,
              'mathematical_claim_tested': False}
    write_json(output, report)
    sys.stdout.write(stream.getvalue())
    return report['return_code']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pattern', default='test_*.py')
    args = parser.parse_args(argv)
    return run(args.output, args.pattern)


if __name__ == '__main__':
    raise SystemExit(main())
