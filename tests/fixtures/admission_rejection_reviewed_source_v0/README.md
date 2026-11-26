# Reviewed admission-rejection source fixtures

These two unchanged source files retain the exact workflow and whole-runtime
checker used by the existing admission-rejection test profile before the
setup-python v7.1.0 refresh. They are test inputs, not evidence of a new native
run, a new admission profile, or release authority.

Both were copied byte-for-byte from repository
`HKati/pulse-release-gates-0.1`, source commit
`a4ef9f9c22faf71f7fd7685219cbfc7e9e3d776e`.

| Fixture | Original path | Bytes | SHA-256 | Git blob SHA-1 |
| --- | --- | ---: | --- | --- |
| `pulse_ci.yml.bin` | `.github/workflows/pulse_ci.yml` | 158466 | `7489fca657c4b2541da4946237b3f864aae7f9247198e5a3c6cbc3429a32db6a` | `9da3eb0a0f8a99071df444f08e9c49f14515ceb1` |
| `check_pulsemech_compute_whole_runtime_observation_v0.py.bin` | `tools/check_pulsemech_compute_whole_runtime_observation_v0.py` | 611462 | `123f5ad80bcb3efa3f057680c083f9102d5b6450f21d5fe8ebf89d97dc995921` | `ebf80fab32f7c33a6432c061d8a94c0077cbfbb4` |

The graph tests validate the fixed workflow bytes with the unchanged production
profile. The semantic adapter tests copy these two files and the other selected
sources into a separate controlled Git repository. They verify its real commit,
source bytes and file modes before exercising the existing content checker.
The controlled commit and fabricated records are test fixtures only; they are
never represented as original execution evidence.

The production admission-rejection schema, builder, checker and semantic adapter
retain their original profile pins. Existing preserved plans and verification
records are unchanged. The active checkout may use the new setup-python pin
without changing these historical test inputs.
