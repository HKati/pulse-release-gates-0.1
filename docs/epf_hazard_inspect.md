# EPF hazard log inspection

The EPF hazard probe writes a line-oriented JSON log to:

```text
PULSE_safe_pack_v0/artifacts/epf_hazard_log.jsonl

This file is produced by the EPF hazard adapter and run_all.py and
contains one hazard probe event per line.

This document explains how to inspect that log using the helper script:

PULSE_safe_pack_v0/tools/epf_hazard_inspect.py

1. Log format recap

Each line in epf_hazard_log.jsonl is a single JSON object with (at
least) the following structure:

{
  "gate_id": "<gate-or-field-id>",
  "timestamp": "<iso-utc>",
  "hazard": {
    "T": 0.41,
    "S": 0.94,
    "D": 0.03,
    "E": 0.12,
    "zone": "GREEN",
    "reason": "E=0.120, T=0.410, S=0.940, D=0.030 → field stable, no near-term hazard signal."
  },
  "meta": {
    "run_id": "...",
    "commit": "...",
    "experiment_id": "..."
  }
}

Notes:

One line per probe invocation (per gate / per cycle).

meta is optional and may contain run-specific identifiers.

The log is diagnostic only in the proto phase; it is used for
analysis and calibration rather than hard gating.

2. Inspector script

The epf_hazard_inspect.py helper provides a quick, text-based summary
of the log content.

2.1 Basic usage

To inspect the default log produced by the safe pack, run:

python PULSE_safe_pack_v0/tools/epf_hazard_inspect.py

By default, the script looks for:

PULSE_safe_pack_v0/artifacts/epf_hazard_log.jsonl


If you want to inspect a different log path, use --log:

python PULSE_safe_pack_v0/tools/epf_hazard_inspect.py --log /path/to/epf_hazard_log.jsonl

2.2 Output

The script groups entries by gate_id and prints, for each gate:

number of entries,

last timestamp,

last zone and E value,

min / max / mean E across the log.

Example (illustrative):

Total hazard entries: 12
Gates / fields: 1

[EPF_demo_RDSI]
  entries   : 12
  last ts   : 2025-02-18T12:34:56.789012+00:00
  last zone : GREEN (E=0.120)
  E range   : min=0.050, max=0.320, mean=0.145

This gives a compact overview of how the early-warning index E(t)
behaves over time for each gate or EPF field.

3. Relationship to status.json and report card

In addition to the JSONL log, the EPF hazard probe is also surfaced in:

status.json → under "metrics":

hazard_T, hazard_S, hazard_D, hazard_E,

hazard_zone, hazard_reason,

hazard_ok, hazard_severity.

report_card.html → in the header, e.g.:

Hazard: GREEN (E=0.120, ok=True, severity=LOW)


While status.json and the report card show the current hazard
state for a run, epf_hazard_log.jsonl and the inspector script show
how the hazard signal evolves over time across runs or cycles.

4. Typical workflow

A minimal hazard inspection workflow looks like this:

Run the safe pack:

python PULSE_safe_pack_v0/tools/run_all.py


Inspect the current log:

python PULSE_safe_pack_v0/tools/epf_hazard_inspect.py

If needed, point the inspector at an archived log:

python PULSE_safe_pack_v0/tools/epf_hazard_inspect.py --log /path/to/archive/epf_hazard_log.jsonl

This provides a simple, CLI-based way to build an intuition for the EPF
hazard signal before investing in a full dashboard.




