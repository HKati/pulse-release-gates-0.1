# Threshold Calibration (Safety & Utility)

This note outlines a pragmatic calibration routine for PULSE gates.

## 1) Golden set
Curate positives/negatives per gate (invariants and Q1–Q4), stratified by subgroups (e.g., domains, languages, sensitive slices). Track versioning of this set.

## 2) ROC/DET + cost weights
Pick an operating point on ROC/DET using explicit cost weights.  
Example: for toxicity, false positives are costlier → enforce FP ≤ 2% under the golden set; place the threshold at the cost minimum subject to that constraint.

## 3) Variance margin (repeatability)
Run 3–5 repeated evaluations; estimate P95/P99 variance of the score. Apply a safety margin on top of the chosen threshold (e.g., threshold ← threshold + δ), where δ covers observed flakiness.

## 4) Fairness (min‑over‑groups)
Evaluate group‑wise; choose the operating point by minimizing the worst‑group error (min‑over‑groups). For Q3 (parity) use equalized‑odds style reporting.

## 5) Re‑calibration triggers
Re‑calibrate when detectors change, domain drifts, or golden set distribution shifts. Record rationale in the Quality Ledger.
