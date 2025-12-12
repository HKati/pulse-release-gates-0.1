"""
EPF Hazard / Relational Grail — feature primitives for PULSE safe-pack.

This module provides deterministic, side-effect-free utilities for:
- feature extraction from metric snapshots (FeatureSpec)
- robust scaling via median/MAD (RobustScaler)
- per-feature contribution bookkeeping for explainability (FeatureContribution)
- stable top-contributor selection and weighted L2 distance building blocks

Design goals:
- No IO, no randomness, no third-party deps.
- Deterministic ordering and stable outputs (audit-friendly).
- Safe handling of missing/non-numeric values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
import statistics
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


FEATURE_SCALERS_SCHEMA_V0 = "epf_hazard_feature_scalers_v0"
DEFAULT_SCALER_EPS = 1e-9


class Transform(str, Enum):
    """Supported deterministic transforms for feature values."""
    IDENTITY = "identity"
    LOG1P = "log1p"


class MissingPolicy(str, Enum):
    """What to do when a feature is missing / unusable in a snapshot."""
    SKIP = "skip"       # drop the feature from computations
    DEFAULT = "default" # use FeatureSpec.default


@dataclass(frozen=True)
class FeatureSpec:
    """
    Declarative spec describing how to extract and transform a numeric feature.

    Notes:
    - key supports dotted-path access (e.g. "metrics.rdsi") for nested dict snapshots.
    - missing policy controls behavior when a value is absent / non-numeric / non-finite.
    - clip is applied AFTER transform to keep outputs bounded deterministically.
    """
    key: str
    transform: Transform = Transform.IDENTITY
    clip: Optional[Tuple[float, float]] = None
    weight: float = 1.0
    missing: MissingPolicy = MissingPolicy.SKIP
    default: float = 0.0
    description: str = ""

    def validate(self) -> None:
        if not self.key or not isinstance(self.key, str):
            raise ValueError("FeatureSpec.key must be a non-empty string")
        if self.weight < 0:
            raise ValueError(f"FeatureSpec.weight must be >= 0, got {self.weight}")
        if self.clip is not None:
            lo, hi = self.clip
            if lo > hi:
                raise ValueError(f"FeatureSpec.clip must be (lo<=hi), got {self.clip}")

    def extract(self, snapshot: Mapping[str, Any]) -> Optional[float]:
        """
        Extract a transformed, clipped numeric value from a snapshot.

        Returns:
            float if usable, otherwise None (unless missing policy is DEFAULT).
        """
        raw = _get_by_dotted_path(snapshot, self.key)
        x = _to_float(raw)

        if x is None:
            if self.missing == MissingPolicy.DEFAULT:
                x = float(self.default)
            else:
                return None

        x = _apply_transform(x, self.transform)
        if x is None:
            if self.missing == MissingPolicy.DEFAULT:
                x = float(self.default)
            else:
                return None

        if self.clip is not None:
            x = _clip(x, self.clip[0], self.clip[1])

        # Final sanity check: must be finite
        if not math.isfinite(x):
            if self.missing == MissingPolicy.DEFAULT:
                return float(self.default)
            return None

        return float(x)


@dataclass(frozen=True)
class RobustScaler:
    """
    Robust scaler using median and MAD (median absolute deviation).

    z(x) = (x - median) / max(mad, eps)

    MAD is not scaled by 1.4826 by default on purpose:
    - deterministic and simpler
    - works well as a relative robust scale proxy for distance building
    """
    median: float
    mad: float
    eps: float = DEFAULT_SCALER_EPS

    def z(self, x: float) -> float:
        denom = self.mad if abs(self.mad) > self.eps else self.eps
        return (x - self.median) / denom

    @staticmethod
    def fit(values: Sequence[float], *, eps: float = DEFAULT_SCALER_EPS) -> "RobustScaler":
        """
        Fit a RobustScaler from finite numeric samples.

        Raises:
            ValueError if values has no usable finite samples.
        """
        finite = [float(v) for v in values if isinstance(v, (int, float)) and math.isfinite(float(v))]
        if not finite:
            raise ValueError("RobustScaler.fit requires at least 1 finite sample")

        med = float(statistics.median(finite))
        abs_dev = [abs(v - med) for v in finite]
        mad = float(statistics.median(abs_dev))
        return RobustScaler(median=med, mad=mad, eps=eps)

    def to_dict(self) -> Dict[str, float]:
        return {"median": float(self.median), "mad": float(self.mad)}

    @staticmethod
    def from_dict(d: Mapping[str, Any], *, eps: float = DEFAULT_SCALER_EPS) -> "RobustScaler":
        med = _to_float(d.get("median"))
        mad = _to_float(d.get("mad"))
        if med is None or mad is None:
            raise ValueError("RobustScaler.from_dict requires 'median' and 'mad' numeric fields")
        return RobustScaler(median=float(med), mad=float(mad), eps=eps)


@dataclass(frozen=True)
class FeatureContribution:
    """
    Per-feature bookkeeping for explainability and stable top-contributor reporting.
    """
    key: str
    current: float
    reference: float
    delta: float
    z_current: float
    z_reference: float
    delta_z: float
    weight: float
    weighted_delta_z: float
    contrib: float
    scaled: bool

    def to_compact_dict(self) -> Dict[str, Any]:
        """
        Compact dict suitable for status.json / logs (keeps only high-signal fields).
        """
        return {
            "key": self.key,
            "delta_z": float(self.delta_z),
            "weight": float(self.weight),
            "contrib": float(self.contrib),
            "scaled": bool(self.scaled),
        }


@dataclass(frozen=True)
class FeatureScalersArtifactV0:
    """
    Container for feature scalers stored in threshold/calibration artifacts.

    Intended JSON shape:
    {
      "schema": "epf_hazard_feature_scalers_v0",
      "stats": {"count": 123, "missing": {"rdsi": 2}},
      "features": {"rdsi": {"median": 0.91, "mad": 0.03}, ...}
    }
    """
    schema: str = FEATURE_SCALERS_SCHEMA_V0
    count: int = 0
    missing: Dict[str, int] = field(default_factory=dict)
    features: Dict[str, RobustScaler] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "stats": {"count": int(self.count), "missing": dict(self.missing)},
            "features": {k: s.to_dict() for k, s in sorted(self.features.items(), key=lambda kv: kv[0])},
        }

    @staticmethod
    def from_dict(d: Mapping[str, Any], *, eps: float = DEFAULT_SCALER_EPS) -> "FeatureScalersArtifactV0":
        schema = str(d.get("schema", ""))
        if schema and schema != FEATURE_SCALERS_SCHEMA_V0:
            raise ValueError(f"Unsupported feature scalers schema: {schema}")

        stats = d.get("stats", {}) if isinstance(d.get("stats", {}), Mapping) else {}
        count_raw = stats.get("count", 0)
        count = int(count_raw) if isinstance(count_raw, (int, float)) else 0

        missing_raw = stats.get("missing", {})
        missing: Dict[str, int] = {}
        if isinstance(missing_raw, Mapping):
            for k, v in missing_raw.items():
                try:
                    missing[str(k)] = int(v)
                except Exception:
                    continue

        feats_raw = d.get("features", {})
        features: Dict[str, RobustScaler] = {}
        if isinstance(feats_raw, Mapping):
            for k, v in feats_raw.items():
                if not isinstance(v, Mapping):
                    continue
                features[str(k)] = RobustScaler.from_dict(v, eps=eps)

        return FeatureScalersArtifactV0(
            schema=FEATURE_SCALERS_SCHEMA_V0,
            count=count,
            missing=missing,
            features=features,
        )


def compute_feature_contributions(
    current_snapshot: Mapping[str, Any],
    reference_snapshot: Mapping[str, Any],
    feature_specs: Sequence[FeatureSpec],
    *,
    scalers: Optional[Mapping[str, RobustScaler]] = None,
) -> List[FeatureContribution]:
    """
    Compute per-feature contributions between current and reference snapshots.

    - Uses FeatureSpec extraction (transform + clip + missing policy).
    - If a scaler is provided for the feature key, uses robust z-space deltas.
      Otherwise falls back to raw deltas (scaled=False).

    Determinism:
    - Output order follows feature_specs order, with skipped features removed.
    """
    out: List[FeatureContribution] = []
    scalers_map = scalers or {}

    for spec in feature_specs:
        # Avoid surprises from invalid specs while keeping this function pure.
        # Call spec.validate() in tests / at config load time.
        cur = spec.extract(current_snapshot)
        ref = spec.extract(reference_snapshot)

        if cur is None or ref is None:
            # If one side is missing, treat as missing entirely (skip/default already applied in extract()).
            continue

        delta = float(cur - ref)

        scaler = scalers_map.get(spec.key)
        if scaler is not None:
            z_cur = float(scaler.z(cur))
            z_ref = float(scaler.z(ref))
            scaled = True
        else:
            z_cur = float(cur)
            z_ref = float(ref)
            scaled = False

        delta_z = float(z_cur - z_ref)
        weighted_delta_z = float(spec.weight * delta_z)
        contrib = float(abs(weighted_delta_z))

        out.append(
            FeatureContribution(
                key=spec.key,
                current=float(cur),
                reference=float(ref),
                delta=delta,
                z_current=z_cur,
                z_reference=z_ref,
                delta_z=delta_z,
                weight=float(spec.weight),
                weighted_delta_z=weighted_delta_z,
                contrib=contrib,
                scaled=scaled,
            )
        )

    return out


def weighted_l2_distance(contribs: Sequence[FeatureContribution]) -> float:
    """
    Compute L2 norm of weighted delta_z across contributions.

    Returns 0.0 if no contributions.
    """
    if not contribs:
        return 0.0
    s = math.fsum((c.weighted_delta_z * c.weighted_delta_z) for c in contribs)
    return float(math.sqrt(s))


def top_contributors(
    contribs: Sequence[FeatureContribution],
    *,
    k: int = 3,
    min_contrib: float = 0.0,
) -> List[FeatureContribution]:
    """
    Deterministically select top-k contributors by contrib magnitude.

    Stable ordering:
    - primary: contrib desc
    - tie-breaker: key asc
    """
    if k <= 0:
        return []

    filtered = [c for c in contribs if c.contrib > min_contrib]
    filtered.sort(key=lambda c: (-c.contrib, c.key))
    return filtered[:k]


def format_top_contributors_reason(
    contribs: Sequence[FeatureContribution],
    *,
    k: int = 3,
) -> str:
    """
    Format a compact deterministic reason suffix:
    "top: key1(1.23), key2(0.77), key3(0.51)"

    Uses contrib values (already abs(weighted_delta_z)).
    """
    top = top_contributors(contribs, k=k, min_contrib=0.0)
    if not top:
        return "top: none"

    parts = [f"{c.key}({c.contrib:.2f})" for c in top]
    return "top: " + ", ".join(parts)


def _get_by_dotted_path(snapshot: Mapping[str, Any], key: str) -> Any:
    """
    Support nested dict snapshots using dotted keys: "a.b.c".
    If any level is missing or non-mapping, returns None.
    """
    if "." not in key:
        return snapshot.get(key)

    cur: Any = snapshot
    for part in key.split("."):
        if not isinstance(cur, Mapping):
            return None
        cur = cur.get(part)
        if cur is None:
            return None
    return cur


def _to_float(value: Any) -> Optional[float]:
    """
    Best-effort conversion to finite float.
    Returns None for non-numeric, NaN, or +/-inf.
    """
    if value is None:
        return None

    # Treat booleans explicitly (avoid surprise because bool is subclass of int).
    if isinstance(value, bool):
        return 1.0 if value else 0.0

    if isinstance(value, (int, float)):
        x = float(value)
        return x if math.isfinite(x) else None

    if isinstance(value, str):
        try:
            x = float(value.strip())
            return x if math.isfinite(x) else None
        except Exception:
            return None

    return None


def _clip(x: float, lo: float, hi: float) -> float:
    if x < lo:
        return float(lo)
    if x > hi:
        return float(hi)
    return float(x)


def _apply_transform(x: float, t: Transform) -> Optional[float]:
    """
    Apply a deterministic transform. Returns None if transform cannot be applied.
    """
    if not math.isfinite(x):
        return None

    if t == Transform.IDENTITY:
        return float(x)

    if t == Transform.LOG1P:
        # log1p is only defined for x > -1. Use a strict guard for safety.
        if x <= -1.0:
            return None
        return float(math.log1p(x))

    # Defensive default: unknown transform => unusable
    return None
