I think a lightweight machine-readable evidence contract could reduce reviewer load without making the challenge heavier for newcomers.

Concretely, an optional `evidence.json` per submission could record:
- artifact accounting (code bytes, compressed model bytes, total bytes, optional tokenizer-bytes advisory),
- evaluation mode metadata (`standard` / `sliding_window` / `ttt_lora` / `other`, sequence length, stride if relevant),
- final reported metrics and wallclock,
- the set of logs used for any statistical claim.

A small shadow verifier could then validate presence/shape of this evidence while staying non-blocking at first.

This seems aligned with the desire for more scientific rigor and a clearer burden of proof, without forcing a big framework into the counted submission path.
