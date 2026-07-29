#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import sys
import types
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ANALYZER_CORE = ROOT / "tools" / "pulsemech_compute_binding_analyzer_core_v0.py"
ANALYZER_CORE_MODULE = "pulsemech_compute_binding_analyzer_core_v0"


class CompatibilityWrapperError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_analyzer_core() -> tuple[Any, str]:
    if not ANALYZER_CORE.is_file():
        raise CompatibilityWrapperError(
            f"analyzer_core_missing: {ANALYZER_CORE}"
        )
    if ANALYZER_CORE.is_symlink():
        raise CompatibilityWrapperError(
            f"analyzer_core_symlink_rejected: {ANALYZER_CORE}"
        )

    source = ANALYZER_CORE.read_bytes()
    source_sha256 = sha256_bytes(source)

    try:
        code = compile(
            source,
            str(ANALYZER_CORE),
            "exec",
            dont_inherit=True,
        )
    except Exception as exc:
        raise CompatibilityWrapperError(
            f"analyzer_core_compile_failed: {ANALYZER_CORE}: {exc}"
        ) from exc

    previous = sys.modules.get(ANALYZER_CORE_MODULE)
    had_previous = ANALYZER_CORE_MODULE in sys.modules

    module = types.ModuleType(ANALYZER_CORE_MODULE)
    module.__file__ = str(ANALYZER_CORE)
    module.__cached__ = None
    module.__loader__ = None
    module.__package__ = ""
    module.__spec__ = None
    module.__pulsemech_source_sha256__ = source_sha256
    sys.modules[ANALYZER_CORE_MODULE] = module

    try:
        exec(code, module.__dict__)
    except Exception as exc:
        if had_previous:
            sys.modules[ANALYZER_CORE_MODULE] = previous
        else:
            sys.modules.pop(ANALYZER_CORE_MODULE, None)
        raise CompatibilityWrapperError(
            f"analyzer_core_execution_failed: {ANALYZER_CORE}: {exc}"
        ) from exc

    return module, source_sha256


_ANALYZER_CORE, ANALYZER_CORE_SOURCE_SHA256 = _load_analyzer_core()

# Preserve the existing import surface for callers and regressions. The
# analysis implementation remains defined only in the analyzer-core module.
for _name, _value in vars(_ANALYZER_CORE).items():
    if _name.startswith("__") or _name == "main":
        continue
    globals()[_name] = _value


def main() -> int:
    return int(
        _ANALYZER_CORE.main(
            producer_source_path=Path(__file__).resolve(),
            analyzer_core_source_sha256=ANALYZER_CORE_SOURCE_SHA256,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
