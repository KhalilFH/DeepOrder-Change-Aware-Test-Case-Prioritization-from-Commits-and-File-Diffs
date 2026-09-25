"""EXPLORATORY / POST HOC signal audit s05: host-clock duration of in-test
timeouts by subject, profile and batch.

A focal timeout ends when the Go test timer (VM monotonic clock) reaches the
frozen -test.timeout. Its host-clock elapsed time therefore tracks the VM/host
clock-rate relationship. Descriptive only.
Outputs: out/s05_clock_drift.json
"""
from __future__ import annotations

import collections
import json
import re

from audit_common import focal, load_attempts, write_json

INNER = {"etcd5509": 45, "etcd7492": 50, "grpc1859": 110, "grpc2391": 60, "istio17860": 30, "k8s26980": 60}


def main():
    att = load_attempts()
    g = collections.defaultdict(list)
    for a in att.values():
        if focal(a) and re.search(r"panic: test timed out after", a["stdout"] + a["stderr"]):
            g[(a["subject"], a["batch"], a["profile"])].append(a["elapsed_s"])
    out = {}
    for (s, b, p), v in sorted(g.items()):
        v.sort()
        med = v[len(v) // 2]
        out[f"{s}/{b}/{p}"] = {"n": len(v), "min": round(v[0], 2), "median": round(med, 2), "max": round(v[-1], 2),
                               "inner_timeout_s": INNER[s], "inner_over_median_host": round(INNER[s] / med, 4)}
    by_block = collections.defaultdict(list)
    for a in att.values():
        if a["subject"] == "etcd5509" and focal(a):
            by_block[a["block"]].append(a["elapsed_s"])
    res = {"label": "EXPLORATORY/POST-HOC s05", "timeout_elapsed_by_subject_batch_profile": out,
           "etcd5509_focal_elapsed_by_block": {b: [round(min(v), 2), round(max(v), 2)] for b, v in sorted(by_block.items())}}
    write_json("s05_clock_drift.json", res)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
