"""Exact UTF-8 byte binding, independent of the semantic interpretation."""

from __future__ import annotations

from pathlib import Path

from .io import InputError, MAX_SOURCE_BYTES, safe_read, sha256


def bind_sources(document: dict, package_root: Path) -> tuple[dict, dict]:
    """Return source texts and per-role checks; retain a failed binding as fail."""
    texts: dict[str, str] = {}
    failures: dict[str, list[str]] = {side: [] for side in ("before", "after", "context")}
    evidence: dict[str, list[str]] = {side: [] for side in failures}
    sources = {row["source_id"]: row for row in document["sources"]}
    raw_sources: dict[str, bytes] = {}
    total = 0
    for source_id, source in sources.items():
        side = source["role"]
        carrier = source["content"]
        if carrier["kind"] == "inline_utf8":
            raw = carrier["text"].encode("utf-8")
            if len(raw) > MAX_SOURCE_BYTES:
                raise InputError("source byte limit exceeded")
        else:
            raw = safe_read(package_root, carrier["path"], limit=MAX_SOURCE_BYTES)
        total += len(raw)
        if total > 4 * MAX_SOURCE_BYTES:
            raise InputError("total source byte limit exceeded")
        raw_sources[source_id] = raw
        evidence[side].append(source_id)
        if len(raw) != source["byte_length"]:
            failures[side].append(f"{source_id}: byte_length mismatch")
        if sha256(raw) != source["content_sha256"]:
            failures[side].append(f"{source_id}: whole-source digest mismatch")
        try:
            texts[source_id] = raw.decode("utf-8")
        except UnicodeError:
            failures[side].append(f"{source_id}: invalid UTF-8 source")

    for anchor in document["source_anchors"]:
        source_id = anchor["source_id"]
        raw = raw_sources[source_id]
        side = sources[source_id]["role"]
        name = anchor["anchor_id"]
        evidence[side].append(name)
        start, end = anchor["start_byte"], anchor["end_byte"]
        if not 0 <= start < end <= len(raw):
            failures[side].append(f"{name}: invalid half-open byte interval")
            continue
        # Whole-source decoding and both prefix decodings establish UTF-8
        # boundaries. A coincidentally matching sliced digest is insufficient.
        try:
            raw[:start].decode("utf-8")
            raw[:end].decode("utf-8")
            raw[start:end].decode("utf-8")
        except UnicodeError:
            failures[side].append(f"{name}: anchor splits invalid UTF-8")
        if sha256(raw[start:end]) != anchor["content_sha256"]:
            failures[side].append(f"{name}: selected-span digest mismatch")

    checks = {}
    for side in failures:
        if side == "context" and not evidence[side]:
            continue
        checks[side] = {
            "result": "fail" if failures[side] else "pass",
            "reason": "; ".join(failures[side][:20]) or None,
            "evidence_refs": sorted(evidence[side]),
        }
    return texts, checks
