#!/usr/bin/env python3
"""
Fixtures for build_gravity_record_protocol_inputs_v0_1.py (JSONL rawlog -> inputs bundle).

We enforce:
- demo rawlog builds a contract-valid inputs bundle
- common failure modes return non-zero and still write an output for triage
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Tuple


PY = sys.executable
BUILDER = ["scripts/build_gravity_record_protocol_inputs_v0_1.py"]
CHECKER = ["scripts/check_gravity_record_protocol_inputs_v0_1_contract.py"]

RAWLOG_DEMO = Path("PULSE_safe_pack_v0/fixtures/gravity_record_protocol_v0_1.rawlog.demo.jsonl")


def _read_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def _run(cmd: list[str]) -> Tuple[int, str, str]:
    proc = subprocess.run([PY, *cmd], text=True, capture_output=True)
    return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()


def main() -> int:
    fails = []

    # 1) PASS: demo rawlog -> bundle -> contract PASS
    with tempfile.TemporaryDirectory() as td:
        outp = Path(td) / "inputs.json"
        rc, out, err = _run([*BUILDER, "--rawlog", str(RAWLOG_DEMO), "--out", str(outp), "--source-kind", "demo"])
        if rc != 0:
            fails.append(f"[FAIL] demo build rc={rc}\nstdout:\n{out}\nstderr:\n{err}")
        else:
            rc2, out2, err2 = _run([*CHECKER, "--in", str(outp)])
            if rc2 != 0:
                fails.append(f"[FAIL] demo contract rc={rc2}\nstdout:\n{out2}\nstderr:\n{err2}")
            else:
                obj = _read_json(outp)
                if obj.get("raw_errors"):
                    fails.append(f"[FAIL] demo output contains raw_errors: {obj.get('raw_errors')}")

    # 2) PASS: only lambda points -> required kappa emitted as status=MISSING
    with tempfile.TemporaryDirectory() as td:
        rawlog = Path(td) / "only_lambda.jsonl"
        rawlog.write_text(
            "\n".join(
                [
                    '{"type":"meta","source_kind":"demo","provenance":{"generated_at_utc":"2026-02-15T00:00:00Z","generator":"fixture"}}',
                    '{"type":"station","case_id":"c","station_id":"A"}',
                    '{"type":"station","case_id":"c","station_id":"B"}',
                    '{"type":"point","case_id":"c","profile":"lambda","r":0,"value":1.0}',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        outp = Path(td) / "out.json"
        rc, out, err = _run([*BUILDER, "--rawlog", str(rawlog), "--out", str(outp), "--source-kind", "demo"])
        if rc != 0:
            fails.append(f"[FAIL] only-lambda build expected rc=0, got rc={rc}\nstdout:\n{out}\nstderr:\n{err}")
        else:
            rc2, out2, err2 = _run([*CHECKER, "--in", str(outp)])
            if rc2 != 0:
                fails.append(
                    f"[FAIL] only-lambda contract expected PASS rc=0, got rc={rc2}\nstdout:\n{out2}\nstderr:\n{err2}"
                )
            else:
                obj = _read_json(outp)
                profiles = obj.get("cases", [{}])[0].get("profiles", {})
                if "kappa" not in profiles:
                    fails.append("[FAIL] expected profiles.kappa to be emitted")
                elif profiles["kappa"].get("status") != "MISSING":
                    fails.append(
                        f"[FAIL] expected profiles.kappa.status == MISSING, got {profiles['kappa'].get('status')}"
                    )

    # 3) FAIL: duplicate station_id should yield rc=2 (but still write output)
    with tempfile.TemporaryDirectory() as td:
        rawlog = Path(td) / "dup.jsonl"
        rawlog.write_text(
            "\n".join(
                [
                    '{"type":"meta","source_kind":"demo","provenance":{"generated_at_utc":"2026-02-15T00:00:00Z","generator":"fixture"}}',
                    '{"type":"station","case_id":"c","station_id":"A"}',
                    '{"type":"station","case_id":"c","station_id":"A"}',
                    '{"type":"point","case_id":"c","profile":"lambda","r":0,"value":1.0}',
                    '{"type":"point","case_id":"c","profile":"kappa","r":0,"value":1.0}',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        outp = Path(td) / "out.json"
        rc, out, err = _run([*BUILDER, "--rawlog", str(rawlog), "--out", str(outp), "--source-kind", "demo"])
        if rc == 0:
            fails.append("[FAIL] duplicate station_id expected non-zero rc, got 0")
        if not outp.exists():
            fails.append("[FAIL] duplicate station_id case did not write output file")

    if fails:
        print("\n\n".join(fails), file=sys.stderr)
        print("[fixtures:gravity_record_protocol_inputs_v0_1_builder] FAIL", file=sys.stderr)
        return 1

    print("[fixtures:gravity_record_protocol_inputs_v0_1_builder] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
