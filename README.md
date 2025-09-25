<!-- HERO (dark default) -->
<img alt="Run PULSE before you ship." src="hero_dark_4k.png" width="100%">

<p align="center">
  <em>Prefer a light version?</em>
</p>

<details>
  <summary><strong>Show light hero</strong></summary>

  <img alt="Run PULSE before you ship. (light)" src="hero_light_4k.png" width="100%">
</details>

[![PULSE](badges/pulse_status.svg)](PULSE_safe_pack_v0/artifacts/report_card.html)
[![RDSI](badges/rdsi.svg)](PULSE_safe_pack_v0/artifacts/status.json)
[![Q‑Ledger](badges/q_ledger.svg)](PULSE_safe_pack_v0/artifacts/report_card.html#quality-ledger)


# PULSE — Release Gates for Safe & Useful AI

From **findings** to **fuses**. Run **PULSE before you ship**: deterministic, **fail‑closed** gates that turn red‑team insights into **release decisions** for both safety (I₂–I₇) and product utility (Q₁–Q₄). Offline, CI‑enforced, audit‑ready.

<p>
  <img src="badges/pulse_status.svg" height="20" alt="PULSE status">
  <img src="badges/rdsi.svg" height="20" alt="RDSI">
  <img src="badges/q_ledger.svg" height="20" alt="Q‑Ledger">
</p>

> **TL;DR**: Drop the pack → run → enforce → ship.  
> PULSE gives PASS/FAIL release gates, a human‑readable **Quality Ledger**, and a stability signal (**RDSI**).

---

## Quickstart

**One‑liner (local):**
```bash
pip install -r requirements.txt && make all
