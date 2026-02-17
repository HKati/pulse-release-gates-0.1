#!/usr/bin/env python3
import json
import os
import pathlib
import subprocess
import tempfile
from typing import Any, Optional, Tuple


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "status_to_summary.py"


def _find_key_recursive(obj: Any, key: str) -> Optional[Any]:
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            hit = _find_key_recursive(v, key)
            if hit is not None:
                return hit
    elif isinstance(obj, list):
        for it in obj:
            hit = _find_key_recursive(it, key)
            if hit is not None:
                return hit
    return None


def main() -> int:
    if not SCRIPT.is_file():
        raise SystemExit(f"status_to_summary.py not found at: {SCRIPT}")

    with tempfile.TemporaryDirectory() as td:
        td_path = pathlib.Path(td)
        art = td_path / "artifacts"
        art.mkdir(parents=True, exist_ok=True)

        status_path = art / "status.json"
        status = {
            "version": "1.0.0-core",
            "created_utc": "2026-02-17T00:00:00Z",
            "metrics": {"run_mode": "core"},
            "gates": {
                # IMPORTANT: only gates.*, no top-level mirrors
                "external_all_pass": True,
                "refusal_delta_pass": False,
            },
            "external": {"all_pass": False},
        }
        status_path.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")

        before = {p.name for p in art.glob("*")}

        # Run script
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--status", str(status_path)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )
        if r.returncode != 0:
            print("STDOUT:\n", r.stdout)
            print("STDERR:\n", r.stderr)
            raise SystemExit(f"status_to_summary.py failed with code {r.returncode}")

        after = {p.name for p in art.glob("*")}
        created = sorted(list(after - before))

        # Heuristic: look for a newly created JSON summary file
        candidates = []
        for name in created:
            if "summary" in name.lower() and name.lower().endswith(".json"):
                candidates.append(art / name)

        if not candidates:
            # fallback: any new json file except status.json
            for name in created:
                if name.lower().endswith(".json") and name != "status.json":
                    candidates.append(art / name)

        if not candidates:
            raise SystemExit(f"No summary JSON produced. New files: {created}")

        # Validate content contains the gate flags derived from gates.*
        data = json.loads(candidates[0].read_text(encoding="utf-8"))

        ext_flag = _find_key_recursive(data, "external_all_pass")
        ref_flag = _find_key_recursive(data, "refusal_delta_pass")

        if ext_flag is None or ref_flag is None:
            raise SystemExit(
                f"Summary JSON missing expected keys. "
                f"external_all_pass={ext_flag}, refusal_delta_pass={ref_flag}"
            )

        if ext_flag is not True:
            raise SystemExit(f"Expected external_all_pass=True from gates.*, got {ext_flag}")

        if ref_flag is not False:
            raise SystemExit(f"Expected refusal_delta_pass=False from gates.*, got {ref_flag}")

    print("OK: status_to_summary reads gate flags from gates.* when mirrors are absent")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main())
