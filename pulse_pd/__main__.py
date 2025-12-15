"""
Entry-point helper for running PULSE–PD modules.

Usage examples:
  python -m pulse_pd.demo_toy --out pulse_pd/artifacts --n 5000 --seed 0

  python -m pulse_pd.examples.make_toy_X --out pulse_pd/examples/X_toy.npz --n 5000 --seed 0

  python -m pulse_pd.run_cut_pd \
    --x pulse_pd/examples/X_toy.npz \
    --theta pulse_pd/examples/theta_cuts_example.json \
    --dims 0 1 \
    --out pulse_pd/artifacts_run
"""

def main() -> int:
    print(__doc__.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
