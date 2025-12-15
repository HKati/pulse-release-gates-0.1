"""
PULSE–PD: Paradoxon Diagram tooling (v0).

Core metrics:
- DS: Decision Stability
- MI: Model Inconsistency
- GF: Gate Friction
- PI: Paradox Index
"""

from .pd import compute_ds, compute_mi, compute_gf, compute_pi  # noqa: F401
from .cut_adapter import run_pd_from_cuts  # noqa: F401
