### Paradox edges case study — <rövid cím>

**Context**
- transitions-dir: `<...>`
- Goal: <mit vizsgáltatok?>

**Evidence (atoms)**
- gate_flip atom_id: `<...>`
  - gate_id: `<...>`, status: `<...→...>`
- metric_delta atom_id: `<...>`
  - metric: `<...>`, delta: `<...>`, rel_delta: `<...>`, severity: `<warn|crit>`

**Evidence (edges)**
- edge_id: `<...>`
  - type: `gate_metric_tension`
  - src_atom_id: `<gate_flip atom_id>`
  - dst_atom_id: `<metric_delta atom_id>`

**Why it helped**
- <1–3 bullet: gyorsabb triage? audit trail? regresszió “fingerprint”?>

**Follow-up**
- <ha kell: új acceptance fixture? küszöb finomítás? csak megjegyzés>
