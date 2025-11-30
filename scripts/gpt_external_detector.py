#!/usr/bin/env python
"""
gpt_external_detector.py

Boundary / sentinel for external GPT or vendor LLM usage.

This script does NOT call any external API. It only inspects a JSONL log
of model invocations and produces a diagnostic summary indicating which
records look like external GPT calls vs internal fields (e.g. HPC G-child).

The detector is deliberately conservative:
- explicit "internal" markers always win (e.g. internal_hpc_g_child, g_child)
- everything else is matched against simple vendor/model patterns

Output is a CI-neutral overlay (gpt_external_detection_v0.json) that can be
consumed by the topology / governance layer, but does not change any gates.
"""

import argparse
import datetime as _dt
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# Heuristic lists for detection. These can be extended later or moved to config.
DEFAULT_EXTERNAL_VENDORS = {
    "openai",
    "azure-openai",
    "azure_openai",
    "azure-openai-gpt",
    "anthropic",  # if you want to treat Claude as "external vendor" too
    "vertexai",
    "vertex-ai",
}

# Anything that clearly marks an internal field / HPC / G-child
DEFAULT_INTERNAL_MARKERS = {
    "internal_hpc",
    "g_child",
    "g-child",
    "pulse_internal",
    "pulse_hpc",
}


@dataclass
class DetectionRecord:
    """Single detection decision for one input record."""

    idx: int
    id: Optional[str]
    is_external_gpt: bool
    is_internal: bool
    vendor: Optional[str]
    model: Optional[str]
    reason: str


def _iter_jsonl(path: Path) -> Iterable[Tuple[int, Dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                sys.stderr.write(
                    f"[WARN] Invalid JSON on line {idx} in {path}, skipping.\n"
                )
                continue
            yield idx, obj


def _normalize_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        return s or None
    return str(value).strip() or None


def _detect_vendor_and_model(rec: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    Try to extract vendor/provider and model name from a record.

    We do not enforce any schema; we just look at a few common keys.
    """
    vendor_keys = ("vendor", "provider", "source", "engine", "backend")
    model_keys = ("model", "model_name", "deployment", "deployment_id")

    vendor = None
    model = None

    for k in vendor_keys:
        if k in rec:
            vendor = _normalize_str(rec.get(k))
            if vendor:
                break

    for k in model_keys:
        if k in rec:
            model = _normalize_str(rec.get(k))
            if model:
                break

    return vendor, model


def _looks_internal(rec: Dict[str, Any]) -> bool:
    """
    Decide if the record is clearly internal (HPC / G-child / Pulse-only).

    If any string field contains an internal marker, we treat it as internal,
    even if the model name also contains "gpt".
    """
    for key, value in rec.items():
        if not isinstance(value, (str, int, float)):
            continue
        s = str(value).lower()
        for marker in DEFAULT_INTERNAL_MARKERS:
            if marker in s:
                return True
    return False


def _looks_external_gpt(vendor: Optional[str], model: Optional[str]) -> Tuple[bool, str]:
    """
    Heuristic for "external GPT-like" usage. Returns (flag, reason).
    """
    # Explicit vendor hit
    if vendor:
        v_lower = vendor.lower()
        for known in DEFAULT_EXTERNAL_VENDORS:
            if known in v_lower:
                return True, f"vendor={vendor!r} matched {known!r}"

    # Model-based heuristic
    if model:
        m_lower = model.lower()
        # typical GPT model names start with gpt-
        if m_lower.startswith("gpt-"):
            return True, f"model={model!r} starts with 'gpt-'"
        # or contain gpt4, gpt-4o, etc.
        if re.search(r"\bgpt[-_]?4", m_lower):
            return True, f"model={model!r} contains 'gpt-4'"
        if "gpt" in m_lower:
            return True, f"model={model!r} contains 'gpt'"

    return False, "no external GPT patterns matched"


def _detect_record(idx: int, rec: Dict[str, Any]) -> DetectionRecord:
    rec_id = rec.get("id") or rec.get("request_id") or rec.get("trace_id")

    # Internal markers win outright
    if _looks_internal(rec):
        vendor, model = _detect_vendor_and_model(rec)
        return DetectionRecord(
            idx=idx,
            id=_normalize_str(rec_id),
            is_external_gpt=False,
            is_internal=True,
            vendor=vendor,
            model=model,
            reason="record contains internal marker",
        )

    vendor, model = _detect_vendor_and_model(rec)
    is_ext, reason = _looks_external_gpt(vendor, model)

    return DetectionRecord(
        idx=idx,
        id=_normalize_str(rec_id),
        is_external_gpt=is_ext,
        is_internal=False,
        vendor=vendor,
        model=model,
        reason=reason,
    )


def _build_summary(records: List[DetectionRecord]) -> Dict[str, Any]:
    total = len(records)
    num_external = sum(1 for r in records if r.is_external_gpt)
    num_internal = sum(1 for r in records if r.is_internal)
    num_unknown = total - num_external - num_internal

    vendors: Dict[str, int] = {}
    models: Dict[str, int] = {}

    for r in records:
        if r.vendor:
            v = r.vendor.lower()
            vendors[v] = vendors.get(v, 0) + 1
        if r.model:
            m = r.model.lower()
            models[m] = models.get(m, 0) + 1

    return {
        "total_records": total,
        "num_external_gpt": num_external,
        "num_internal": num_internal,
        "num_unknown": num_unknown,
        "vendors": vendors,
        "models": models,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect external GPT/vendor LLM usage from JSONL logs."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input JSONL file with model invocation records.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for gpt_external_detection_v0.json (or similar).",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.is_file():
        sys.stderr.write(f"[ERROR] Input file not found: {in_path}\n")
        sys.exit(1)

    records: List[DetectionRecord] = []

    for idx, obj in _iter_jsonl(in_path):
        rec = _detect_record(idx, obj)
        records.append(rec)

    created_at = _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    summary = _build_summary(records)

    out_obj = {
        "version": "gpt_external_detection_v0",
        "created_at": created_at,
        "input_file": str(in_path),
        "summary": summary,
        "records": [asdict(r) for r in records],
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out_obj, f, ensure_ascii=False, indent=2)

    sys.stderr.write(
        f"[INFO] Wrote detection overlay for {len(records)} records to {out_path}\n"
    )


if __name__ == "__main__":
    main()
