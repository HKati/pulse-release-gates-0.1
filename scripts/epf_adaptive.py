import math, os, json

def _save_status(self):
    tmp = self.status_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(self.status, f, indent=2, ensure_ascii=False)
    os.replace(tmp, self.status_path)  # atomic

# decide() elején:
if not math.isfinite(metric_value):
    metric_value = -float("inf")  # force FAIL

# a jitter bekerül a trace meta-jába:
trace = self._make_trace(..., meta | {
    "adjusted": adjusted, "jitter": jitter, "epf_score": epf_score, "samples": n
}, t0)
