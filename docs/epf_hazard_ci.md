# EPF hazard gate · CI integration

The EPF hazard pipeline can be used as a **soft gate** in CI by
configuring the `EPF_HAZARD_ENFORCE` environment variable.

By default, the hazard gate is in **shadow mode**:

- `status["metrics"]["hazard_ok"]` always reflects the policy decision,
- `status["gates"]["epf_hazard_ok"]` is always `true` (so CI behaviour
  does not change).

When `EPF_HAZARD_ENFORCE=1` is set, the gate becomes **enforced**:

- `status["gates"]["epf_hazard_ok"] == status["metrics"]["hazard_ok"]`,
- a `RED` hazard zone (or any policy-defined non-OK state) can cause
  the overall check to fail, depending on how `status["gates"]` is
  consumed.

---

## 1. Local runs

To experiment locally with an enforced hazard gate, run:

```bash
EPF_HAZARD_ENFORCE=1 python PULSE_safe_pack_v0/tools/run_all.py

After the run:

PULSE_safe_pack_v0/artifacts/status.json will contain:

"gates": {
  "...": true,
  "epf_hazard_ok": false
},
"metrics": {
  "...": 0.0,
  "hazard_ok": false,
  "hazard_severity": "HIGH",
  "hazard_zone": "RED",
  "hazard_reason": "..."
}

if the hazard policy determines that the field is not OK.

report_card.html will show the hazard state in the header, including
ok and severity.

If EPF_HAZARD_ENFORCE is not set (or set to "0"), then:

gates["epf_hazard_ok"] is forced to true (shadow gate),

metrics["hazard_ok"] still reflects the policy decision.

2. GitHub Actions example

A typical GitHub Actions job that runs the safe pack might look like:

jobs:
  pulse-safe-pack:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run PULSE safe pack (EPF hazard in shadow mode)
        run: |
          python PULSE_safe_pack_v0/tools/run_all.py

In this configuration:

the hazard probe runs,

status.json and epf_hazard_log.jsonl are produced,

epf_hazard_ok is present in status["gates"] but always true.

To enforce the hazard gate in CI, add EPF_HAZARD_ENFORCE=1:

      - name: Run PULSE safe pack (EPF hazard enforced)
        env:
          EPF_HAZARD_ENFORCE: "1"
        run: |
          python PULSE_safe_pack_v0/tools/run_all.py

With this setting:

epf_hazard_ok will follow metrics["hazard_ok"],

a non-OK hazard decision (e.g. zone="RED") can propagate as a failed
gate, depending on how status["gates"] is interpreted by downstream
tooling.

3. Recommended rollout strategy

To reduce risk, consider the following rollout steps:

Shadow mode only

Run the safe pack without EPF_HAZARD_ENFORCE.

Monitor hazard_E, hazard_zone, hazard_ok, hazard_severity
in status.json and in the report card.

Enforced in non-critical workflows

Enable EPF_HAZARD_ENFORCE=1 in:

a dedicated experimental workflow, or

a non-production branch.

Observe how often epf_hazard_ok becomes false.

Gradual expansion

Once calibrated, enable enforcement in more workflows or for more
gates/EPF fields as needed.

Throughout this process, the JSONL log
(PULSE_safe_pack_v0/artifacts/epf_hazard_log.jsonl) and the associated
tools (epf_hazard_inspect.py, epf_hazard_plot.py) can be used to
analyse and tune the hazard thresholds and policy.

