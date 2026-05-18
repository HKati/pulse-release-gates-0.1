from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts" / "check_external_summaries_present.py"


def test_decoy_summary_does_not_count_as_external_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        external_dir = Path(tmpdir)
        (external_dir / "foo_summary.json").write_text(
            json.dumps({"value": 0}),
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "--external_dir",
                str(external_dir),
                "--require_metric_key",
            ],
            text=True,
            capture_output=True,
        )

    assert result.returncode != 0
    assert "No canonical external detector summaries" in result.stderr
