cat > tests/test_no_legacy_status_schema_refs_smoke.py <<'PY'
#!/usr/bin/env python3
"""
Smoke guard: prevent accidental use of legacy status.schema.json (v0.1)
in CI/tooling.

We allow legacy schema to exist for backward compatibility, but it must not be
referenced by:
- .github/workflows (CI)
- tools/ (repo-level guardrails)
- PULSE_safe_pack_v0/ (pack tools)

This test fails if it finds "status.schema.json" in those areas.
"""

from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
TOOLS_DIR = ROOT / "tools"
PACK_DIR = ROOT / "PULSE_safe_pack_v0"

LEGACY = "status.schema.json"
V1 = "schemas/status/status_v1.schema.json"


def _read_text(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _scan_dir_for_token(base: pathlib.Path, exts: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix and p.suffix not in exts:
            continue
        txt = _read_text(p)
        if LEGACY in txt:
            hits.append(str(p.relative_to(ROOT)))
    return hits


def test_no_legacy_status_schema_refs_smoke() -> None:
    assert WORKFLOWS_DIR.is_dir(), f"Missing workflows dir: {WORKFLOWS_DIR}"
    assert TOOLS_DIR.is_dir(), f"Missing tools dir: {TOOLS_DIR}"
    assert PACK_DIR.is_dir(), f"Missing pack dir: {PACK_DIR}"

    # Positive sanity: ensure CI mentions the v1 schema path somewhere
    pulse_ci = WORKFLOWS_DIR / "pulse_ci.yml"
    assert pulse_ci.is_file(), f"Missing workflow file: {pulse_ci}"
    txt_ci = _read_text(pulse_ci)
    assert V1 in txt_ci, f"Expected pulse_ci.yml to reference status v1 schema path: {V1}"

    # Negative: forbid legacy schema references in CI/tooling
    hits = []
    hits += _scan_dir_for_token(WORKFLOWS_DIR, (".yml", ".yaml"))
    hits += _scan_dir_for_token(TOOLS_DIR, (".py",))
    hits += _scan_dir_for_token(PACK_DIR, (".py",))

    if hits:
        msg = "Legacy schema reference found (forbidden):\n" + "\n".join(f"  - {h}" for h in hits)
        msg += "\n\nFix: update references to use schemas/status/status_v1.schema.json instead."
        raise AssertionError(msg)

    print("OK: no legacy status.schema.json references in CI/tooling")


def main() -> int:
    try:
        test_no_legacy_status_schema_refs_smoke()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1
    print("OK: legacy schema reference guard passed")
    return 0


def test_smoke() -> None:
    # optional pytest entrypoint
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
PY
