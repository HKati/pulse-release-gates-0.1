# EPF hazard log plotting

The EPF hazard probe writes a line-oriented JSON log to:

```text
PULSE_safe_pack_v0/artifacts/epf_hazard_log.jsonl

In addition to the CLI inspector, the safe pack includes a small plotting
helper:

PULSE_safe_pack_v0/tools/epf_hazard_plot.py

This script provides a quick visual view of how the EPF hazard signal
evolves over time for a given gate or EPF field.

1. Basic usage

First, run the safe pack to generate / extend the hazard log:

python PULSE_safe_pack_v0/tools/run_all.py

Then plot the hazard time series:

python PULSE_safe_pack_v0/tools/epf_hazard_plot.py

By default, the script:

reads the log from:

PULSE_safe_pack_v0/artifacts/epf_hazard_log.jsonl

PULSE_safe_pack_v0/artifacts/epf_hazard_log.jsonl

selects the first gate_id found in the log,

plots four time series (E, T, S, D) over the log index.

Note: matplotlib is required to run this script.
Install it with:

pip install matplotlib

2. Selecting a log and gate

You can override the log path with --log:

python PULSE_safe_pack_v0/tools/epf_hazard_plot.py \
  --log /path/to/epf_hazard_log.jsonl

You can also specify which gate_id to plot:

python PULSE_safe_pack_v0/tools/epf_hazard_plot.py \
  --gate EPF_demo_RDSI

Both options can be combined:

python PULSE_safe_pack_v0/tools/epf_hazard_plot.py \
  --log /path/to/archive/epf_hazard_log.jsonl \
  --gate EPF_demo_RDSI


3. What the plot shows

The script extracts the following series from the hazard field:

E(t) – early-warning index

T(t) – distance between current and baseline snapshot

S(t) – stability index (clipped to [0, 1])

D(t) – short-horizon drift

It then plots four stacked time series:

E(t)

T(t)

S(t)

D(t)

all against a simple log index (0, 1, 2, ...), which corresponds to the
order of hazard events for the chosen gate.

This is sufficient to see:

whether E(t) is trending up or down,

how T(t) and S(t) move before and after a regime change,

whether D(t) is signalling increased drift in the field.

4. Relationship to the inspector and other artefacts

The plotting helper is complementary to:

epf_hazard_inspect.py

prints per-gate statistics (entry count, last zone/E, min/max/mean E),

status.json and report_card.html

show the current hazard state for a run.

The plotting tool focuses on time series:

how T, S, D, E evolve over the entries in epf_hazard_log.jsonl,

on a per-gate basis.

A typical workflow is:

Run the safe pack (one or more times) to generate hazard log entries.

Use epf_hazard_inspect.py to check overall statistics.

Use epf_hazard_plot.py to visually inspect the hazard dynamics for
a specific gate or EPF field.








