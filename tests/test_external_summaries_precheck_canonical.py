from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'scripts' / 'check_external_summaries_present.py'


def test_canonical_summary_name_passes_precheck() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / 'llamaguard_summary.json').write_text(json.dumps({'rate': 0.02}), encoding='utf-8')
        res = subprocess.run([sys.executable, str(TOOL), '--external_dir', str(d), '--require_metric_key'], text=True, capture_output=True)
        assert res.returncode == 0
