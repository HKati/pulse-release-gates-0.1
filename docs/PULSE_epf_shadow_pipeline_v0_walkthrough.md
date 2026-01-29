# PULSE EPF shadow pipeline v0 – walkthrough

Status: **v0, shadow-only**  
Scope: Stability Map v0 + Decision Engine v0 + paradox / EPF field

Ez a doksi azt írja le, hogyan kapcsolódik be az EPF jel
a PULSE Topology v0 → Stability Map v0 → Decision Engine v0 → summary / history
láncba **anélkül**, hogy a gate logikát megváltoztatnánk.

A pipeline 3 lépésből áll:

1. Stability Map dúsítása paradox / EPF mezővel  
2. Decision Engine v0 shadow-output építése  
3. Summary / history nézetek építése

---

## 1. Előfeltételek

A PULSE topology pipeline már létezik, és előállítja:

- `status.json` (és opcionálisan `status_epf.json`)
- `stability_map.json` a `PULSE_safe_pack_v0/tools/build_stability_map_v0.py` futásából

A Stability Map sémája ki lett bővítve:

- `schemas/PULSE_stability_map_v0.schema.json` támogatja:
  - `ReleaseState.paradox_field_v0`
  - `ReleaseState.epf_field_v0`

A régi mezők (`rdsi`, `epf`, `instability`, `paradox`, …) jelentése változatlan.

---

## 2. Step 1 – Stability Map dúsítása paradox / EPF mezővel

**Tool:**

```text
PULSE_safe_pack_v0/tools/build_paradox_epf_fields_v0.py
