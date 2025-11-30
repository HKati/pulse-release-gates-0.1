# Competitor Radar (2025)

**Position.** PULSE = pre‑release, deterministic, fail‑closed *release governance* layer. It consolidates Safety (I‑gates), Utility (Q‑gates) and SLO (p95 + cost) into PASS/FAIL with an audit‑ready ledger.

## Landscape

- Runtime guardrails: AWS Bedrock Guardrails, Azure Risk & Safety, Vertex/Gemini Safety, NVIDIA NeMo Guardrails.
- Eval frameworks: Promptfoo, DeepEval, TruLens, RAGAS, OpenAI Evals.
- Observability: LangSmith, Langfuse, Phoenix, Evidently, WhyLabs, Giskard.
- Red‑teaming/benchmarks: Meta Purple Llama (Llama Guard/Prompt Guard/LlamaFirewall), Garak, PyRIT, Azure Safety Evaluations.

## Differentiators

- Pre‑release PASS/FAIL across explicit invariants (mono/comm/idemp/path/PII), Q‑gates (grounded/consistency/fairness) and SLO.
- Deterministic CI: `status.json`, Quality Ledger, SVG badges committed.
- Detector‑agnostic ingestion (simple JSON/JSONL adapters).
- Agentic framing risk captured via refusal‑delta gate.

## Compact comparison

| Tool/family | Pre‑release PF | Runtime | I‑gates | Q‑gates | SLO | Audit |
|---|---|---|---|---|---|---|
| **PULSE** | ✔ | – | ✔ explicit | ✔ | ✔ | ✔ |
| Promptfoo/DeepEval/TruLens/RAGAS | ◐ | – | ◐ | ✔ | ◐ | ◐ |
| LangSmith/Langfuse/Phoenix/Evidently/Giskard | ◐ | – | ◐ | ✔ | ◐ | ◐ |
| Bedrock/Azure/Vertex/NeMo | – | ✔ | – | ◐ | – | – |
| Purple Llama/Garak/PyRIT | ◐ | ◐ | – | ◐ | – | ◐ |

*Legend:* ✔ full; ◐ partial; – not focus.

## Takeaway

PULSE sits above evals/guardrails as a release decision layer: deterministic **GO/NO‑GO**, audit trail, vendor‑neutral adapters.
