from typing import List, Optional


def compute_delta_curvatures(
    instability_series: List[float],
    eps: float = 1e-6,
) -> List[Optional[float]]:
    """
    EPF Δ-hajlás (directional curvature) becslés.

    Diszkrét második derivált, normálva az előző pont abszolút értékére:

        Δ_i = | I_i - 2 * I_{i-1} + I_{i-2} | / (eps + |I_{i-1}|)

    Az első két pontra nincs értelmes második derivált, oda None kerül.
    """
    n = len(instability_series)
    if n < 3:
        return [None] * n

    deltas: List[Optional[float]] = [None, None]
    for i in range(2, n):
        i0 = instability_series[i - 2]
        i1 = instability_series[i - 1]
        i2 = instability_series[i]

        num = abs(i2 - 2.0 * i1 + i0)
        denom = eps + abs(i1)
        deltas.append(num / denom)

    return deltas


def band_delta_curvature(
    value: Optional[float],
    low: float,
    medium: float,
) -> str:
    """
    Egyszerű sávozás Δ-értékekre.

    - None      -> "n/a"
    - [0, low)  -> "low"
    - [low, medium) -> "medium"
    - >= medium -> "high"
    """
    if value is None:
        return "n/a"
    if value < low:
        return "low"
    if value < medium:
        return "medium"
    return "high"
