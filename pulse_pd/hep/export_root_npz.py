"""
Backward-compat entrypoint.

Prefer:
  python -m pulse_pd.hep.export_uproot_npz ...

This wrapper forwards execution to the canonical module.
"""
import runpy

if __name__ == "__main__":
    runpy.run_module("pulse_pd.hep.export_uproot_npz", run_name="__main__")
