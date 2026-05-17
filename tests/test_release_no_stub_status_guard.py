from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'ci' / 'check_release_no_stub_status.py'


def _run(payload: dict) -> subprocess.CompletedProcess[str]:
    tmp = ROOT / 'tests' / 'fixtures' / '_tmp_release_no_stub_status.json'
    tmp.write_text(json.dumps(payload), encoding='utf-8')
    try:
        return subprocess.run([sys.executable, str(TOOL), '--status', str(tmp)], text=True, capture_output=True)
    finally:
        tmp.unlink(missing_ok=True)


def test_fails_if_stubbed_or_unmaterialized() -> None:
    payload = {'gates': {'detectors_materialized_ok': False}, 'diagnostics': {'gates_stubbed': True, 'scaffold': False}}
    res = _run(payload)
    assert res.returncode != 0


def test_passes_when_materialized_and_not_stubbed() -> None:
    payload = {'gates': {'detectors_materialized_ok': True}, 'diagnostics': {'gates_stubbed': False, 'scaffold': False}}
    res = _run(payload)
    assert res.returncode == 0
