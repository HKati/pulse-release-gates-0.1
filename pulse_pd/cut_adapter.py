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

    If feature_names is provided, it is injected into theta (without mutating
    the original dict) so cuts can use string feature names in `feat`.

    IMPORTANT: do not overwrite explicit theta["feature_names"] if present.
    """
    x = _as_2d_float(X)
    rng = np.random.default_rng(seed)

    # Inject feature_names into theta for name-based feat resolution.
    # Preserve explicit theta["feature_names"] if provided.
    theta_eff: Dict[str, Any] = theta
    if feature_names is not None:
        existing = theta.get("feature_names", None)

        # Treat empty containers as missing.
        missing = existing is None
        if isinstance(existing, (list, tuple, dict)) and len(existing) == 0:
            missing = True

        if missing:
            theta_eff = dict(theta)
            theta_eff["feature_names"] = feature_names

        elif isinstance(existing, dict) and isinstance(feature_names, (list, tuple)):
            # Merge: keep explicit mapping, add any missing names from dataset list
            merged = dict(existing)
            for idx, name in enumerate(feature_names):
                key = str(name)
                if key not in merged:
                    merged[key] = idx
            theta_eff = dict(theta)
            theta_eff["feature_names"] = merged

        else:
            # theta already has explicit list or mapping -> do not override
            theta_eff = theta

    ds = compute_ds(
        decision_fn=lambda X_, th: decision_cut(X_, th),
        X=x,
        theta=theta_eff,
        eps_sampler=lambda th: eps_sampler_cut(th, rng=rng),
        M=int(ds_M),
    )

    sigma_used = float(theta_eff.get("sigma", 0.02)) if mi_sigma is None else float(mi_sigma)

    # NOTE: make_cut_prob_ensemble signature in this file is:
    #   (theta, n_models=..., *, seed=..., sigma=...)
    prob_fns = make_cut_prob_ensemble(
        theta_eff,
        n_models=int(mi_models),
        seed=int(seed) + 1,
        sigma=sigma_used,
    )
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
