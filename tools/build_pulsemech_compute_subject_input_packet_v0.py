#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import sys
import types
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PRODUCER_CORE = (
    ROOT
    / "tools"
    / "pulsemech_compute_subject_input_packet_producer_core_v0.py"
)
PRODUCER_CORE_MODULE = "pulsemech_compute_subject_input_packet_producer_core_v0"


class CompatibilityWrapperError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_producer_core() -> tuple[Any, str]:
    if not PRODUCER_CORE.is_file():
        raise CompatibilityWrapperError(
            f"producer_core_missing: {PRODUCER_CORE}"
        )
    if PRODUCER_CORE.is_symlink():
        raise CompatibilityWrapperError(
            f"producer_core_symlink_rejected: {PRODUCER_CORE}"
        )

    source = PRODUCER_CORE.read_bytes()
    source_sha256 = sha256_bytes(source)

    try:
        code = compile(
            source,
            str(PRODUCER_CORE),
            "exec",
            dont_inherit=True,
        )
    except Exception as exc:
        raise CompatibilityWrapperError(
            f"producer_core_compile_failed: {PRODUCER_CORE}: {exc}"
        ) from exc

    previous = sys.modules.get(PRODUCER_CORE_MODULE)
    had_previous = PRODUCER_CORE_MODULE in sys.modules

    module = types.ModuleType(PRODUCER_CORE_MODULE)
    module.__file__ = str(PRODUCER_CORE)
    module.__cached__ = None
    module.__loader__ = None
    module.__package__ = ""
    module.__spec__ = None
    module.__pulsemech_source_sha256__ = source_sha256
    sys.modules[PRODUCER_CORE_MODULE] = module

    try:
        exec(code, module.__dict__)
    except Exception as exc:
        if had_previous:
            sys.modules[PRODUCER_CORE_MODULE] = previous
        else:
            sys.modules.pop(PRODUCER_CORE_MODULE, None)
        raise CompatibilityWrapperError(
            f"producer_core_execution_failed: {PRODUCER_CORE}: {exc}"
        ) from exc

    return module, source_sha256


_PRODUCER_CORE, PRODUCER_CORE_SOURCE_SHA256 = _load_producer_core()

# Preserve the established import surface for callers and regressions. Packet
# production remains implemented only in the producer-core module.
for _name, _value in vars(_PRODUCER_CORE).items():
    if _name.startswith("__") or _name in {"main", "executed_producer_source_path"}:
        continue
    globals()[_name] = _value


def executed_producer_source_path(
    repository_root: Path,
    *,
    revision: str,
) -> Path:
    return _PRODUCER_CORE.executed_producer_source_path(
        repository_root,
        revision=revision,
        executed_source_path=Path(__file__).resolve(),
    )


def main() -> int:
    return int(
        _PRODUCER_CORE.main(
            producer_source_path=Path(__file__).resolve(),
            producer_core_source_sha256=PRODUCER_CORE_SOURCE_SHA256,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
