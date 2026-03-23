# Separating Generation from Release Authority: PULSE as a Deterministic Control Layer for Probabilistic LLM Workflows

## Abstract

Large language models (LLMs) are powerful generators, but they are weak sole authorities for release-critical decisions. Their outputs remain sensitive to context interpretation, decoding choices, and branch competition; generative systems can become unfaithful to source state; and model-based judging introduces biases of their own. We present **PULSE (Deterministic Release Gates for Safe & Useful AI)** as a deterministic release-control layer that evaluates explicit artifacts under fail-closed policy. Under fixed normative artifacts, schema version, evaluator implementation, and gate policy, PULSE yields reproducible and auditable release outcomes. We formalize a separation between **generation** and **release authority**, define three operational invariants—**reproducibility under fixed artifacts**, **fail-closed gate semantics**, and **diagnostic non-override**—and ground them in the current repository study surface pinned to `schemas/status/status_v1.schema.json`, `pulse_gate_policy_v0.yml` with policy slice `core_required`, `PULSE_safe_pack_v0/tools/check_gates.py`, `PULSE_safe_pack_v0/artifacts/status.json`, and `.github/workflows/pulse_ci.yml`. The contribution is a systems claim rather than a new claim about model behavior: final release authority in LLM-mediated workflows should be externalized to a deterministic evaluator over explicit, versioned artifacts.

## 1. Introduction

Large language models have made open-ended generation practical across text, code, analysis, and workflow support. That capability, however, does not imply that the same model should serve as the final authority in release-critical decisions. Release control is not only a question of whether an output is plausible. It is a question of whether the decision to advance, hold, or reject an artifact can be reproduced, audited, and shown to follow explicit policy.

This distinction matters because many practical workflows blur the boundary between generation and authority. A model is asked not only to draft a patch, summarize a risk, or compare alternatives, but also to implicitly determine whether an artifact is acceptable to ship. That conflation is architecturally unstable. Open-ended generation is probabilistic and context-sensitive by design. Release authority, by contrast, requires explicit state, fixed criteria, and conservative handling of uncertainty.

The motivating observation is often described informally as “hallucination,” but the more relevant systems problem is **authority drift**. The issue is not only that a model may produce a false or weakly grounded statement. The deeper issue is that a probabilistic generator may be allowed to choose outcomes that should instead be selected by explicit policy over persisted state.

We address this problem with **PULSE (Deterministic Release Gates for Safe & Useful AI)**. PULSE externalizes release authority into a deterministic evaluator over versioned artifacts. The model may still generate candidate outputs, summaries, or diagnostics, but final release status is determined only by explicit gate state under fixed schema, evaluator logic, and policy.

This paper makes three contributions. First, it formalizes a separation between probabilistic generation and deterministic release authority. Second, it defines three operational invariants for release control: reproducibility under fixed artifacts, fail-closed gate semantics, and non-override of diagnostics. Third, it grounds those invariants in the current repository study surface rather than in an abstract toy example.

The claim is intentionally narrow. PULSE does not guarantee truth or universal semantic correctness. It guarantees reproducible policy evaluation over explicit, versioned evidence under stated conditions. In release-critical settings, that boundary is the point.

## 2. Authority Drift in LLM-Mediated Workflows

When LLMs are used as release authorities, several familiar generative properties become operationally problematic.

First, models may exhibit **context and state ambiguity**: they may not reliably determine which prior artifact is authoritative, which conversational branch is active, or whether a new instruction has actually changed the task. Second, they face **branch competition**: multiple locally plausible next actions may coexist, such as responding, waiting, inferring intent, or continuing an earlier line of work. Third, they often rely on **pattern-induced action selection**, inferring what is “probably wanted” from prior interaction patterns rather than from explicit policy. Fourth, they are vulnerable to **reconstruction drift**, where state is partially reconstructed from context rather than read from an authoritative object.

None of these behaviors is surprising in a probabilistic generator. They are normal consequences of generative operation. The problem arises only when such behavior is allowed to become final decision authority. In a release pipeline, the question is not whether a model can usually guess the intended next step. The question is whether the system can justify the release decision from explicit evidence.

This motivates a simple architectural rule: **generation may remain probabilistic, but release authority should not**.

## 3. Current Study Pin

This paper is tied to a specific repository study surface. It is not a free-floating proposal and it does not redefine shipping semantics.

The current normative boundary is anchored to the following repository artifacts:

- `schemas/status/status_v1.schema.json`
- `pulse_gate_policy_v0.yml`
- policy slice `core_required`
- `PULSE_safe_pack_v0/tools/check_gates.py`
- `PULSE_safe_pack_v0/artifacts/status.json`
- `.github/workflows/pulse_ci.yml`

Within that pinned surface, the active gate set for the study is the `core_required` slice of `pulse_gate_policy_v0.yml`, whose required gates are:

- `pass_controls_refusal`
- `pass_controls_sanit`
- `sanitization_effective`
- `q1_grounded_ok`
- `q4_slo_ok`

The study documentation further separates three roles. `claims_to_checks.md` states the claims and the intended mapping from claims to observable checks. `repro/README.md` specifies the canonical execution order and the observables to record. The release evaluator itself remains the existing deterministic tooling anchored by the status schema, the policy file, and `check_gates.py`.

A conservative point matters here. The policy materialization step from `pulse_gate_policy_v0.yml` to the required gate list is part of the reproduction procedure described in `repro/README.md`. This paper relies on that documented procedure, rather than introducing a new helper path or alternate evaluator.

## 4. PULSE Model

We model LLM output as a probabilistic generative process:

```text
O = f(I, θ, ε)
```

where `I` is input, `θ` model parameters, and `ε` stochastic factors. The output `O` is not assumed to be stable across runs.

We then define an artifact construction step:

```text
A = h(O, E)
```

where `E` denotes external evidence inputs and `A` is the explicit artifact bundle used for evaluation.

For release control, we partition artifact state into:

```text
A = (N, X)
```

where:

- `N` is the **normative gate state**,
- `X` is the set of **non-authoritative diagnostics**, such as summaries, overlays, convenience scores, or explanatory text.

The release decision is computed as:

```text
D = gate(N; σ, ν, π)
```

where `σ` is the schema version, `ν` the evaluator version, and `π` the active gate policy.

In the current study pin, `σ` is the status schema named above, `ν` is the checked-in evaluator implementation in `PULSE_safe_pack_v0/tools/check_gates.py`, and `π` is the `core_required` slice of `pulse_gate_policy_v0.yml`.

Let `R(π)` denote the required gate set under the active policy. Then:

```text
PASS iff every g ∈ R(π) is present in N and N[g] = true
FAIL otherwise
```

This definition is deliberate. Final release authority is a function of the normative gate state `N`, not of all available commentary. PULSE therefore does not infer release validity from loosely weighted signals. It evaluates explicit normative state under explicit policy.

## 5. System Invariants

The authority boundary becomes operational only when stated as invariants.

### 5.1 Invariant I: Reproducibility Under Fixed Artifacts

For fixed normative artifact state `N`, schema version `σ`, evaluator version `ν`, and gate policy `π`, repeated evaluation yields the same decision `D`.

```text
(N, σ, ν, π) fixed  ⇒  D is constant across repeated evaluations
```

This invariant does not claim semantic truth. It claims evaluator stability under fixed authority-bearing inputs.

### 5.2 Invariant II: Fail-Closed Gate Semantics

If any required gate is missing, invalid, or not literal `true`, the release decision must be `FAIL`.

```text
∃ g ∈ R(π) such that N[g] is missing, invalid, or N[g] ≠ true  ⇒  D = FAIL
```

This gives uncertainty a conservative resolution. The system does not interpolate through incomplete authority state.

### 5.3 Invariant III: Diagnostic Non-Override

Changes in non-authoritative diagnostics `X` must not alter the release decision when the normative gate state `N` is unchanged.

```text
N(A1) = N(A2), σ1 = σ2, ν1 = ν2, π1 = π2  ⇒  D(A1) = D(A2)
```

provided that the differences between `A1` and `A2` are confined to `X`.

This invariant protects the authority boundary. Diagnostics may inform humans or upstream artifact construction, but they do not silently inherit decision rights.

A signal in `X` can become authoritative only through explicit schema evolution, policy revision, and evaluator update. Utility alone does not promote a diagnostic into release authority.

## 6. Repo-Grounded Reproduction Surface

The current study uses the repository’s checked-in fixture surface rather than a synthetic release story. The point is not to claim broad empirical coverage; it is to make the authority-boundary claim inspectable and reproducible within the pinned repository configuration.

### 6.1 Canonical observables

The canonical observables for the study are the ones documented in `repro/README.md`:

- schema validation success or failure,
- the derived required gate list for `core_required`,
- evaluator exit code for schema-valid fixtures,
- validator exit code for the schema-invalid fixture,
- stdout/stderr at the canonical stopping point.

These observables matter because they separate authority-bearing outcomes from narrative interpretation. The study is complete only when the same fixture, run under the same pinned schema, policy slice, and evaluator, yields the same recorded observables.

### 6.2 Fixture set

The current checked-in reproduction surface consists of six fixtures:

- `repro/cases/core_pass.status.json`
- `repro/cases/core_missing_q4.status.json`
- `repro/cases/core_false_q4.status.json`
- `repro/cases/schema_invalid_non_boolean_gate.status.json`
- `repro/cases/core_diag_variant_a.status.json`
- `repro/cases/core_diag_variant_b.status.json`

The intended role of this fixture set is narrow and concrete.

| Fixture | Intended condition | Boundary property exercised |
|---|---|---|
| `core_pass.status.json` | Schema-valid status artifact with all `core_required` gates present and true | Baseline PASS under fixed normative state |
| `core_missing_q4.status.json` | Schema-valid artifact with `q4_slo_ok` absent | Fail-closed behavior on missing required gate |
| `core_false_q4.status.json` | Schema-valid artifact with `q4_slo_ok = false` | Fail-closed behavior on explicitly failing required gate |
| `schema_invalid_non_boolean_gate.status.json` | Schema-invalid artifact in which a gate is not encoded as the required boolean type | Schema boundary before release evaluation |
| `core_diag_variant_a.status.json` | One member of a diagnostic-variation pair | Diagnostic non-override under fixed normative core |
| `core_diag_variant_b.status.json` | Other member of the diagnostic-variation pair | Diagnostic non-override under fixed normative core |

Two points are important. First, the paired diagnostic fixtures are meaningful only if the normative gate state is held fixed while non-authoritative fields vary. That is exactly the kind of separation the study is designed to inspect. Second, the schema-invalid fixture is not an evaluator failure case in the same sense as the missing-gate or false-gate fixtures; it is a precondition failure at the validation boundary.

### 6.3 How the invariants appear in the pinned fixture surface

The fixture surface operationalizes the three invariants without introducing new semantics.

**Reproducibility under fixed artifacts** appears when a given schema-valid fixture is re-run under the same schema, policy slice, and evaluator, and the same derived gate set, exit code, and stopping-point output are observed.

**Fail-closed semantics** appear in `core_missing_q4.status.json` and `core_false_q4.status.json`. Under the current study pin, `q4_slo_ok` is part of the required set. Absence of that gate and explicit falsity of that gate are therefore both sufficient to prevent PASS.

**Diagnostic non-override** appears in the `core_diag_variant_a` / `core_diag_variant_b` pair. The study claim is not that diagnostics are useless; it is that diagnostics do not silently acquire release authority when the normative gate state has not changed.

### 6.4 Scope note

The initial executable boundary-phase surface covers `C1–C5` as mapped in `claims_to_checks.md`. This is the right initial boundary for the study: it is narrow enough to be reproducible and concrete enough to expose the architecture’s authority split.

`C6` remains outside the initial executable fixture set. It should be treated as a future extension of the study surface, not as hidden missing proof inside this paper. That boundary is intentional. The present paper argues for the architecture and grounds it in the current repository pin; it does not claim that every possible authority-boundary extension has already been fixture-backed.

For exact mapping details and execution notes, the paper should be read together with `claims_to_checks.md` and `repro/README.md`.

## 7. Related Work and Positioning

Prior work on neural text generation shows strong sensitivity to decoding strategy [1], while the hallucination literature documents that generative systems can produce outputs that are plausible yet unfaithful to source state [2]. These results support a key distinction used in this paper: generation quality and release authority are different properties.

A second line of work studies **LLM-as-a-judge** evaluation. Strong LLM judges can approximate human preferences on open-ended tasks, but documented limitations include position bias, verbosity bias, self-enhancement bias, and restricted reasoning reliability [3]. PULSE does not reject model-based evaluation altogether; it rejects assigning final release authority to the same kind of generative mechanism.

A third line of work improves model behavior from within the model itself, for example through Constitutional AI [4]. Such approaches are valuable and complementary, but they remain model-mediated. PULSE addresses a different layer of the problem by externalizing final release authority into a deterministic evaluator over explicit artifacts.

Conceptually, PULSE is closest to runtime assurance and Simplex-style external control [5,6]. In those architectures, high-capability components may propose actions, but a separate assurance layer determines whether those actions are allowed to govern the system. The novelty claim here is correspondingly narrow: not the discovery that LLMs are probabilistic, but the claim that **release authority in LLM-mediated workflows should be externalized and attached only to invariant-bearing artifact state**.

## 8. Conclusion

The central issue in release-critical LLM workflows is not merely that a model may hallucinate. The deeper issue is that probabilistic generation may be allowed to cross an authority boundary it should not hold. PULSE addresses this by separating generation from release decision.

Under PULSE, models may generate, summarize, classify, and assist. Release status, however, is determined only by explicit normative artifacts under fixed schema, evaluator logic, and gate policy. The resulting guarantee is not truth in the broad sense. It is reproducible policy evaluation under stated conditions.

Within the current repository study pin, that claim is inspectable. The schema, policy slice, evaluator, workflow entrypoint, fixture cases, and expected observables are all named explicitly. That is the right level of ambition for this phase. A release decision that cannot be reproduced from versioned artifacts and a fixed evaluator should not be considered valid.

## References

[1] Ari Holtzman, Jan Buys, Li Du, Maxwell Forbes, Yejin Choi. **The Curious Case of Neural Text Degeneration.** arXiv:1904.09751.

[2] Ziwei Ji, Nayeon Lee, Rita Frieske, Tiezheng Yu, Dan Su, Yan Xu, Etsuko Ishii, Yejin Bang, Delong Chen, Wenliang Dai, Ho Shu Chan, Andrea Madotto, Pascale Fung. **Survey of Hallucination in Natural Language Generation.** arXiv:2202.03629.

[3] Lianmin Zheng, Wei-Lin Chiang, Ying Sheng, Siyuan Zhuang, Zhanghao Wu, Yonghao Zhuang, Zi Lin, Zhuohan Li, Dacheng Li, Eric P. Xing, Hao Zhang, Joseph E. Gonzalez, Ion Stoica. **Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena.** arXiv:2306.05685.

[4] Yuntao Bai et al. **Constitutional AI: Harmlessness from AI Feedback.** arXiv:2212.08073.

[5] Darren Cofer, Isaac Amundson, Ramachandra Sattigeri, Arjun Passi, Christopher Boggs, Eric Smith, Limei Gilham, Taejoon Byun, Sanjai Rayadurgam. **Run-Time Assurance for Learning-Enabled Systems.** NASA Formal Methods Symposium, 2020.

[6] Usama Mehmood, Sanaz Sheikhi, Stanley Bak, Scott A. Smolka, Scott D. Stoller. **The Black-Box Simplex Architecture for Runtime Assurance of Autonomous CPS.** arXiv:2102.12981.
