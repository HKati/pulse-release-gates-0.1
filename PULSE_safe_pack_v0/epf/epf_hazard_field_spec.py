"""
epf_hazard_field_spec.py

Field specification (coordinate definition) for the EPF Relational Grail overlay.

A FieldSpec is an explicit list of dotted-path numeric feature keys that define
the Grail "field coordinates". This avoids drifting into a classic "log every
metric and threshold later" pipeline. Instead, the field is defined up-front,
and other layers (snapshot logging, feature autowire, coverage diagnostics)
can align to this coordinate system.

Design goals:
  - Deterministic normalization (sorted unique keys, stable serialization).
  - Fail-open loading (invalid/missing files -> None).
  - Additive: defining a FieldSpec does not change gating by itself.

License: Apache-2.0 (same as repository).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json


FIELD_SPEC_SCHEMA_V0 = "epf_hazard_field_spec_v0"

# This module lives in PULSE_safe_pack_v0/epf/, so pack root is parents[1].
PACK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIELD_SPEC_PATH = PACK_ROOT / "artifacts" / "epf_hazard_field_spec_v0.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_dotted_paths(xs: Optional[List[str]]) -> List[str]:
    """
    Normalize dotted-path keys deterministically:
      - cast to str
      - strip whitespace
      - drop empties
      - drop trailing dots
      - sort unique

    Returns an always-defined list (possibly empty).
    """
    if not xs:
        return []
    out: List[str] = []
    for x in xs:
        if x is None:
            continue
        s = str(x).strip()
        if not s:
            continue
        if s.endswith("."):
            s = s[:-1]
        if s:
            out.append(s)
    return sorted(set(out))


@dataclass
class FieldSpecArtifactV0:
    """
    Field specification artifact (v0).

    features:
        Dotted-path keys defining Grail field coordinates, e.g.:
          - "metrics.RDSI"
          - "external.promptfoo.fail_rate"
          - "gates.q1_grounded_ok"

        Keys SHOULD be leaf-like coordinates (exact feature keys), not broad
        prefixes. (Prefix-style "metrics" is allowed but will typically not
        intersect exact scaler keys later, so keep this explicit.)

    deny_keys:
        Optional dotted prefixes to deny (always drop).
        Useful when you want the field explicit but still guard specific subtrees.

    Notes:
        This artifact is intended to be referenced by:
          - snapshot logging policy (allow list)
          - feature-mode autowire allow list
          - coverage diagnostics
    """
    schema: str = FIELD_SPEC_SCHEMA_V0
    created_utc: str = ""
    features: List[str] = None  # type: ignore[assignment]
    deny_keys: List[str] = None  # type: ignore[assignment]
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.created_utc:
            self.created_utc = _utc_now_iso()
        self.features = _normalize_dotted_paths(self.features or [])
        self.deny_keys = _normalize_dotted_paths(self.deny_keys or [])

        # Keep schema stable.
        if not self.schema:
            self.schema = FIELD_SPEC_SCHEMA_V0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FieldSpecArtifactV0":
        if not isinstance(data, dict):
            raise TypeError("FieldSpecArtifactV0.from_dict expects a dict")

        schema = str(data.get("schema", FIELD_SPEC_SCHEMA_V0))
        if schema != FIELD_SPEC_SCHEMA_V0:
            # Strict schema guard: avoid silently misreading other formats.
            raise ValueError(f"unexpected field spec schema: {schema}")

        created_utc = str(data.get("created_utc", "") or "")
        features = data.get("features", [])
        deny_keys = data.get("deny_keys", [])
        notes = str(data.get("notes", "") or "")

        if not isinstance(features, list):
            raise TypeError("field spec 'features' must be a list")
        if not isinstance(deny_keys, list):
            raise TypeError("field spec 'deny_keys' must be a list")

        return cls(
            schema=schema,
            created_utc=created_utc,
            features=[str(x) for x in features],
            deny_keys=[str(x) for x in deny_keys],
            notes=notes,
        )

    def to_dict(self) -> Dict[str, Any]:
        # Stable ordering is guaranteed by normalization.
        payload: Dict[str, Any] = {
            "schema": FIELD_SPEC_SCHEMA_V0,
            "created_utc": self.created_utc,
            "features": list(self.features),
        }
        if self.deny_keys:
            payload["deny_keys"] = list(self.deny_keys)
        if self.notes:
            payload["notes"] = self.notes
        return payload

    def to_snapshot_policy(self) -> Tuple[List[str], List[str]]:
        """
        Interpret FieldSpec as snapshot logging policy.
        - allowed_prefixes := features (exact dotted keys)
        - deny_keys := deny_keys
        """
        return (list(self.features), list(self.deny_keys))

    def to_feature_allowlist(self) -> List[str]:
        """
        Interpret FieldSpec as feature-mode allow list (exact keys).
        """
        return list(self.features)

    def save_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, sort_keys=True)


def maybe_load_field_spec(path: Optional[Path] = None) -> Optional[FieldSpecArtifactV0]:
    """
    Fail-open load:
      - missing file -> None
      - invalid JSON / schema -> None
    """
    p = path or DEFAULT_FIELD_SPEC_PATH
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return FieldSpecArtifactV0.from_dict(data)
    except FileNotFoundError:
        return None
    except Exception:
        return None
