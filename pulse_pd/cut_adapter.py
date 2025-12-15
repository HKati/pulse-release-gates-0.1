"""
Cut-based adapter for PULSE–PD (Paradoxon Diagram) v0.

Purpose
-------
Provide a model-free way to measure PD metrics at the *decision moment* (theta),
using a classic selection-cuts style pipeline.

We define:
- decision_cut(X, theta): hard pass/fail (0/1)
- prob_cut(X, theta): a smooth probability proxy derived from "margin-to-fail"
- eps_sampler_cut(theta, rng): perturb thresholds for DS
- make_cut_prob_ensemble(theta, ...): create a set of equally-valid "models" by jittering theta
- run_pd_from_cuts(X, theta, ...): convenience wrapper to compute DS/MI/GF/PI

theta format (v0)
-----------------
theta = {
  "cuts": [
    {"feat": 0, "op": ">",  "thr": 0.10, "sigma": 0.02, "scale": 1.0},
    {"feat": 1, "op": "<=", "thr": 1.20, "sigma": 0.03}
  ],
  "k": 8.0,      # steepness for sigmoid(margin*k)
  "sigma": 0.02  # default sigma for thresholds if a cut does not define one
}

Notes:
- "feat" can be an int index, or a string name if you provide
  theta["feature_names"] as a list or mapping.
- "scale" (optional) rescales margin per-cut so different units don't dominate.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Union

import numpy as np

from pulse_pd.pd import compute_ds, compute_gf, compute_mi, compute_pi

ArrayLike = Union[np.ndarray, Sequence[float], Sequence[Sequence[float]]]


def _as_2d_float(X: ArrayLike) -> np.ndarray:
    x = np.asarray(X, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    if x.ndim != 2:
        raise ValueError(f"X must be 1D or 2D; got shape {x.shape}")
    return x


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-z))


def _resolve_feat_index(theta: Dict[str, Any], feat: Any) -> int:
    """
    Resolve a cut feature selector into an integer column index.

    Supports:
    - int: used directly
    - str: looked up via theta["feature_names"] (list or dict)
    """
    if isinstance(feat, (int, np.integer)):
        return int(feat)

    if isinstance(feat, str):
        names = theta.get("feature_names", None)
        if names is None:
            raise ValueError(
                f"Cut feat='{feat}' is a string but theta has no 'feature_names'."
            )
        if isinstance(names, Mapping):
            if feat not in names:
                raise ValueError(f"Feature name '{feat}' not found in feature_names mapping.")
            return int(names[feat])
        if isinstance(names, (list, tuple)):
            try:
                return int(names.index(feat))
            except ValueError as e:
                raise ValueError(f"Feature name '{feat}' not found in feature_names list.") from e

        raise ValueError("theta['feature_names'] must be a list/tuple or mapping.")

    raise ValueError(f"Unsupported feat selector type: {type(feat)}")


def decision_cut(X: ArrayLike, theta: Dict[str, Any]) -> np.ndarray:
    """
    Hard cut-based decision: pass if all cuts are satisfied.

    Returns 0/1 array of shape (n_samples,).
    """
    x = _as_2d_float(X)
    n, d = x.shape

    cuts = theta.get("cuts", None)
    if not cuts:
        raise ValueError("theta must contain a non-empty 'cuts' list")

    mask = np.ones(n, dtype=bool)
    for cut in cuts:
        feat = cut.get("feat", None)
        op = str(cut.get("op", ">")).strip()
        thr = float(cut.get("thr", 0.0))

        j = _resolve_feat_index(theta, feat)
        if j < 0 or j >= d:
            raise ValueError(f"Cut feature index out of bounds: {j} for X with d={d}")

        col = x[:, j]
        if op in (">", ">="):
            cond = col >= thr if op == ">=" else col > thr
        elif op in ("<", "<="):
            cond = col <= thr if op == "<=" else col < thr
        else:
            raise ValueError(f"Unsupported cut op '{op}'. Use >, >=, <, <=")

        mask &= cond

    return mask.astype(int)


def _min_margin_to_fail(X: np.ndarray, theta: Dict[str, Any]) -> np.ndarray:
    """
    Compute a per-sample "margin" to the nearest failing cut.
    Positive margin => safely passing; negative => failing.

    For each cut:
      if op is > or >=: margin = (x - thr)
      if op is < or <=: margin = (thr - x)

    Then take min over cuts (closest to failing dominates).
    """
    cuts = theta.get("cuts", None)
    if not cuts:
        raise ValueError("theta must contain a non-empty 'cuts' list")

    n, d = X.shape
    margins = np.full((len(cuts), n), np.inf, dtype=float)

    for i, cut in enumerate(cuts):
        feat = cut.get("feat", None)
        op = str(cut.get("op", ">")).strip()
        thr = float(cut.get("thr", 0.0))
        scale = float(cut.get("scale", 1.0))
        if scale <= 0:
            scale = 1.0

        j = _resolve_feat_index(theta, feat)
        col = X[:, j]

        if op in (">", ">="):
            m = (col - thr) / scale
        elif op in ("<", "<="):
            m = (thr - col) / scale
        else:
            raise ValueError(f"Unsupported cut op '{op}'. Use >, >=, <, <=")

        margins[i, :] = m

    return np.min(margins, axis=0)


def prob_cut(X: ArrayLike, theta: Dict[str, Any]) -> np.ndarray:
    """
    Smooth probability proxy from cut margins.

    p = sigmoid(k * min_margin)

    k controls how sharp the boundary is (higher k => sharper).
    """
    x = _as_2d_float(X)
    k = float(theta.get("k", 8.0))
    margin = _min_margin_to_fail(x, theta)
    return _sigmoid(k * margin)


def perturb_theta_thresholds(
    theta: Dict[str, Any],
    rng: np.random.Generator,
    sigma: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Return a perturbed theta by jittering cut thresholds.

    Per-cut sigma:
      cut["sigma"] if present else (sigma argument) else theta["sigma"] else 0.02
    """
    cuts = theta.get("cuts", None)
    if not cuts:
        raise ValueError("theta must contain a non-empty 'cuts' list")

    sigma_global = float(theta.get("sigma", 0.02))
    if sigma is None:
        sigma = sigma_global

    new_cuts: List[Dict[str, Any]] = []
    for cut in cuts:
        thr = float(cut.get("thr", 0.0))
        sigma_cut = float(cut.get("sigma", sigma))
        thr_p = thr + float(rng.normal(0.0, sigma_cut))
        new_cut = dict(cut)
        new_cut["thr"] = thr_p
        new_cuts.append(new_cut)

    new_theta = dict(theta)
    new_theta["cuts"] = new_cuts
    return new_theta


def eps_sampler_cut(theta: Dict[str, Any], rng: np.random.Generator) -> Dict[str, Any]:
    """Default eps_sampler for DS: jitter cut thresholds."""
    return perturb_theta_thresholds(theta, rng, sigma=None)


def make_cut_prob_ensemble(
    theta: Dict[str, Any],
    n_models: int = 7,
    *,
    seed: int = 0,
    sigma: Optional[float] = None,
) -> List[Callable[[np.ndarray, Any], np.ndarray]]:
    """
    Create a list of probability functions representing equally-valid selectors.

    We sample n_models perturbed thetas, and return prob_fns that close over each theta_i.
    """
    if n_models <= 0:
        raise ValueError("n_models must be >= 1")

    rng = np.random.default_rng(seed)
    prob_fns: List[Callable[[np.ndarray, Any], np.ndarray]] = []

    for _ in range(n_models):
        theta_i = perturb_theta_thresholds(theta, rng, sigma=sigma)

        def _fn(X: np.ndarray, _unused: Any = None, _theta=theta_i) -> np.ndarray:
            return prob_cut(X, _theta)

        prob_fns.append(_fn)

    return prob_fns


def run_pd_from_cuts(
    X: ArrayLike,
    theta: Dict[str, Any],
    *,
    feature_names: Optional[Union[List[str], Dict[str, int]]] = None,
    ds_M: int = 24,
    mi_models: int = 7,
    mi_sigma: Optional[float] = None,
    gf_method: str = "spsa",
    gf_K: int = 8,
    gf_delta: float = 0.05,
    seed: int = 0,
    normalize_pi: bool = True,
) -> Dict[str, np.ndarray]:
    """
    Compute DS/MI/GF/PI from a cut-based theta.

    New: if feature_names is provided, it is injected into theta (without mutating
    the original dict), so cuts can use string feature names in `feat`.
    """
    x = _as_2d_float(X)
    rng = np.random.default_rng(seed)

    # Inject feature_names into theta for name-based feat resolution
    theta_eff = theta
    if feature_names is not None:
        theta_eff = dict(theta)
        theta_eff["feature_names"] = feature_names

    ds = compute_ds(
        decision_fn=lambda X_, th: decision_cut(X_, th),
        X=x,
        theta=theta_eff,
        eps_sampler=lambda th: eps_sampler_cut(th, rng=rng),
        M=int(ds_M),
    )

    sigma_used = float(theta_eff.get("sigma", 0.02)) if mi_sigma is None else float(mi_sigma)
    prob_fns = make_cut_prob_ensemble(theta_eff, models=int(mi_models), sigma=sigma_used, rng=rng)
    mi = compute_mi(prob_fn_list=prob_fns, X=x, theta=None)

    gf = compute_gf(
        prob_fn=lambda X_, th: prob_cut(X_, th),
        X=x,
        theta=theta_eff,
        method=str(gf_method),
        K=int(gf_K),
        delta=float(gf_delta),
        rng=rng,
    )

    pi = compute_pi(ds=ds, mi=mi, gf=gf, normalize=bool(normalize_pi))
    return {"ds": ds, "mi": mi, "gf": gf, "pi": pi}

