"""EXPLORATORY / POST HOC signal audit s02: attempt position, cell order, batch,
timing, host load, within-cell dependence and ordinary-repetition null models
for etcd5509, plus the same position summary for every subject as context.

No outcome is relabelled. Every probability here is a descriptive diagnostic
computed after seeing the data; none is a confirmatory test.
Outputs: out/s02_position_order_time.json
"""
from __future__ import annotations

import collections
import datetime as dt
import itertools
from math import comb

from audit_common import (STUDY, SUBJECTS, blocks, cells, focal, load_attempts, load_jsonl,
                          p1_prefix, p3_prefix, supported_block, write_json)


def ts(s: str) -> dt.datetime:
    s = s.rstrip("Z")
    if "." in s:
        head, frac = s.split(".")
        s = head + "." + frac[:6]
    return dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc)


def binom_pmf(n, p):
    return [comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(n + 1)]


def prob_absdiff_ge(n, p, d):
    pm = binom_pmf(n, p)
    return sum(pm[x] * pm[y] for x in range(n + 1) for y in range(n + 1) if abs(x - y) >= d)


def signflip_p(diffs):
    """Exact two-sided within-block label-swap (sign-flip) p-value for sum(diffs)."""
    obs = abs(sum(diffs))
    nz = [d for d in diffs if d != 0]
    tot = 0
    hit = 0
    for signs in itertools.product((1, -1), repeat=len(nz)):
        tot += 1
        if abs(sum(s * d for s, d in zip(signs, nz))) >= obs - 1e-12:
            hit += 1
    return hit / tot


def rate(xs):
    xs = list(xs)
    return [sum(xs), len(xs)]


def main():
    att = load_attempts()
    C = cells(att)
    by_seq = sorted(att.values(), key=lambda a: a["seq"])
    prev_of = {a["attempt_id"]: (by_seq[i - 1] if i else None) for i, a in enumerate(by_seq)}
    res: dict = {"label": "EXPLORATORY/POST-HOC s02; descriptive diagnostics, not confirmatory tests"}

    E = "etcd5509"
    bad = [a for a in att.values() if a["subject"] == E and a["variant"] == "bad"]

    # 1. Attempt position x profile.
    pos = {}
    for prof in ("R", "L"):
        for k in (1, 2, 3):
            pos[f"{prof}/a{k}"] = rate(focal(a) for a in bad if a["profile"] == prof and a["attempt"] == k)
    pos["pooled/a1"] = rate(focal(a) for a in bad if a["attempt"] == 1)
    pos["pooled/a2_a3"] = rate(focal(a) for a in bad if a["attempt"] > 1)
    res["etcd5509_position"] = pos

    # 2. Within-cell dependence: transitions and failure-count distribution.
    trans = collections.Counter()
    fc = {"R": collections.Counter(), "L": collections.Counter()}
    for prof in ("R", "L"):
        for b in range(1, 11):
            t = C[(E, b, prof, "bad")]
            fc[prof][sum(focal(a) for a in t)] += 1
            for x, y in zip(t, t[1:]):
                trans[(prof, "F" if focal(x) else "P", "F" if focal(y) else "P")] += 1
    res["etcd5509_transitions"] = {f"{p}:{a}->{b}": n for (p, a, b), n in sorted(trans.items())}
    dist = {}
    for prof in ("R", "L"):
        p = sum(k * n for k, n in fc[prof].items()) / 30
        exp = [10 * q for q in binom_pmf(3, p)]
        dist[prof] = {"observed_cells_by_failures_0_1_2_3": [fc[prof][k] for k in range(4)],
                      "binomial_expected_0_1_2_3": [round(e, 2) for e in exp], "p_hat": round(p, 4)}
    pooled_p = 50 / 60
    allfc = [fc["R"][k] + fc["L"][k] for k in range(4)]
    dist["pooled"] = {"observed": allfc, "binomial_expected": [round(20 * q, 2) for q in binom_pmf(3, pooled_p)], "p_hat": round(pooled_p, 4)}
    # ANOVA-type intraclass correlation over 20 cells of size 3 (binary outcomes).
    ys = [[int(focal(a)) for a in C[(E, b, prof, "bad")]] for prof in ("R", "L") for b in range(1, 11)]
    k, g = 3, len(ys)
    grand = sum(map(sum, ys)) / (k * g)
    msb = k * sum((sum(y) / k - grand) ** 2 for y in ys) / (g - 1)
    msw = sum((v - sum(y) / k) ** 2 for y in ys for v in y) / (g * (k - 1))
    dist["icc_anova_estimate"] = round((msb - msw) / (msb + (k - 1) * msw), 4)
    res["etcd5509_within_cell"] = dist

    # 3. Cell position within block, preceding attempt, batch, block, host load.
    cellpos = collections.defaultdict(list)
    prevctx = collections.defaultdict(list)
    for prof in ("R", "L"):
        for b in range(1, 11):
            t = C[(E, b, prof, "bad")]
            mine = sorted([a for a in att.values() if a["subject"] == E and a["block"] == b], key=lambda a: a["seq"])
            order = []
            for a in mine:
                lab = (a["profile"], a["variant"])
                if lab not in order:
                    order.append(lab)
            cp = order.index((prof, "bad")) + 1
            cellpos[f"{prof}/cellpos{cp}"].append(int(focal(t[0])))
            pa = prev_of[t[0]["attempt_id"]]
            if pa is None:
                key = "none"
            elif pa["subject"] != E:
                key = "other_subject"
            elif pa["variant"] == "bad":
                key = "etcd5509_bad_" + ("F" if focal(pa) else "P")
            else:
                key = "etcd5509_ok"
            prevctx[f"{prof}/{key}"].append(int(focal(t[0])))
    res["etcd5509_a1_by_cell_position"] = {k: rate(v) for k, v in sorted(cellpos.items())}
    res["etcd5509_a1_by_preceding_attempt"] = {k: rate(v) for k, v in sorted(prevctx.items())}
    rb_first = []
    for b in range(1, 11):
        r1 = C[(E, b, "R", "bad")][0]
        l1 = C[(E, b, "L", "bad")][0]
        rb_first.append({"block": b, "R_bad_before_L_bad": r1["seq"] < l1["seq"],
                         "R_a1": "F" if focal(r1) else "P", "L_a1": "F" if focal(l1) else "P"})
    res["etcd5509_R_vs_L_bad_order"] = rb_first
    res["etcd5509_by_batch"] = {
        f"{prof}/{bt}": {"a1": rate(focal(a) for a in bad if a["profile"] == prof and a["batch"] == bt and a["attempt"] == 1),
                         "all": rate(focal(a) for a in bad if a["profile"] == prof and a["batch"] == bt)}
        for prof in ("R", "L") for bt in ("A", "B")}

    ev = load_jsonl(STUDY / "events.jsonl")
    load = {e["block"]: e["host_load"]["host_load_percent"] for e in ev if e["kind"] == "block_start"}
    res["host_load_block_start_pct"] = load
    res["host_load_note"] = ("One Win32_Processor.LoadPercentage snapshot per block index, taken before all six subjects; "
                             "shared by R and L cells of a block, so it cannot vary within a matched block.")
    # 4. Timing: focal durations by batch, VM-vs-host clock drift, pass durations.
    dur = collections.defaultdict(list)
    for a in bad:
        dur[(a["profile"], a["batch"], "F" if focal(a) else "P")].append(a["elapsed_s"])
    res["etcd5509_elapsed_s"] = {f"{p}/{b}/{o}": [len(v), round(min(v), 3), round(sorted(v)[len(v) // 2], 3), round(max(v), 3)]
                                 for (p, b, o), v in sorted(dur.items())}
    # Container runtime in VM clock vs attempt elapsed in host clock, for focal (timed-out-in-test) attempts, all subjects.
    drift = collections.defaultdict(list)
    for a in att.values():
        if focal(a) and a["vm_started"] and a["vm_finished"]:
            vm = (ts(a["vm_finished"]) - ts(a["vm_started"])).total_seconds()
            drift[(a["subject"], a["batch"])].append(round(vm / a["elapsed_s"], 4) if a["elapsed_s"] else None)
    res["focal_vm_runtime_over_host_elapsed"] = {f"{s}/{b}": [len(v), min(v), max(v)] for (s, b), v in sorted(drift.items())}
    # Offsets between VM clock and host clock at container start (VM StartedAt minus host started_utc), per batch.
    off = collections.defaultdict(list)
    for a in att.values():
        off[a["batch"]].append((ts(a["vm_started"]) - ts(a["started_utc"])).total_seconds())
    res["vm_minus_host_start_offset_s"] = {b: [round(min(v), 3), round(sorted(v)[len(v) // 2], 3), round(max(v), 3)] for b, v in off.items()}
    series = []
    for a in sorted(att.values(), key=lambda a: a["seq"]):
        if a["seq"] % 60 == 1:
            series.append({"seq": a["seq"], "batch": a["batch"], "host_start": a["started_utc"],
                           "vm_minus_host_s": round((ts(a["vm_started"]) - ts(a["started_utc"])).total_seconds(), 3)})
    res["vm_minus_host_offset_series"] = series

    # 5. Ordinary-repetition null models (etcd5509).
    pR, pL = 24 / 30, 26 / 30
    hist = 68 / 85  # Q0 16/20 + E1 52/65, unrestricted condition on the same host class, before C1
    res["null_models"] = {
        "historical_unrestricted_rate": {"focal": 68, "n": 85, "p": round(hist, 4), "source": "Q0 16/20 (task5_etcd5509_restoration.md) + E1 52/65 (ci_sensitivity_2026_09/e1/etcd5509)"},
        "iid_expected_P1_blocks": {"R": round(10 * pR, 2), "L": round(10 * pL, 2), "at_hist_p": round(10 * hist, 2)},
        "iid_expected_P3_blocks_p_cubed": {"R": round(10 * pR ** 3, 2), "L": round(10 * pL ** 3, 2), "at_hist_p": round(10 * hist ** 3, 2)},
        "observed": {"R/P1": 7, "L/P1": 10, "R/P3": 5, "L/P3": 7},
        "P_absdiff_P1_ge_3_common_p_pooled": round(prob_absdiff_ge(10, 50 / 60, 3), 4),
        "P_absdiff_P1_ge_3_common_p_hist": round(prob_absdiff_ge(10, hist, 3), 4),
        "P_absdiff_P3_ge_2_common_p_pooled": round(prob_absdiff_ge(10, (50 / 60) ** 3, 2), 4),
        "P_absdiff_P3_ge_2_common_p_hist": round(prob_absdiff_ge(10, hist ** 3, 2), 4),
        "P_L_a1_10_of_10_at_hist_p": round(hist ** 10, 4),
        "P_R_a1_le_7_of_10_at_hist_p": round(sum(binom_pmf(10, hist)[:8]), 4),
        "batchA_rate_predicts_batchB_P3": {},
    }
    for prof in ("R", "L"):
        a_rate = sum(focal(a) for a in bad if a["profile"] == prof and a["batch"] == "A") / 15
        obs_b = sum(supported_block(p3_prefix(C[(E, b, prof, "bad")])) for b in range(6, 11))
        res["null_models"]["batchA_rate_predicts_batchB_P3"][prof] = {"p_A": round(a_rate, 4), "expected_B_blocks": round(5 * a_rate ** 3, 2), "observed_B_blocks": obs_b}
    d1 = [supported_block(p1_prefix(C[(E, b, "R", "bad")])) - supported_block(p1_prefix(C[(E, b, "L", "bad")])) for b in range(1, 11)]
    d3 = [supported_block(p3_prefix(C[(E, b, "R", "bad")])) - supported_block(p3_prefix(C[(E, b, "L", "bad")])) for b in range(1, 11)]
    dn = [sum(focal(a) for a in C[(E, b, "R", "bad")]) - sum(focal(a) for a in C[(E, b, "L", "bad")]) for b in range(1, 11)]
    res["within_block_signflip_exact_p"] = {
        "P1_S": {"diffs": d1, "p": signflip_p(d1)},
        "P3_S": {"diffs": d3, "p": signflip_p(d3)},
        "per_cell_failure_count": {"diffs": dn, "p": signflip_p(dn)},
        "note": "post hoc, unadjusted, conditional on the observed blocks; not a replacement for the frozen simultaneous intervals",
    }

    # 6. Context: position summary for every subject (bad variant).
    ctx = {}
    for s in SUBJECTS:
        bb = [a for a in att.values() if a["subject"] == s and a["variant"] == "bad"]
        ctx[s] = {f"{prof}/{lab}": rate(focal(a) for a in bb if a["profile"] == prof and sel(a["attempt"]))
                  for prof in ("R", "L") for lab, sel in (("a1", lambda k: k == 1), ("a2_a3", lambda k: k > 1))}
    tot = collections.defaultdict(lambda: [0, 0])
    for s, r in ctx.items():
        if s in ("istio17860", "k8s26980"):
            continue  # all-fail / all-pass: no position information
        for k, (x, n) in r.items():
            tot[k][0] += x
            tot[k][1] += n
    res["context_position_by_subject"] = ctx
    res["context_position_pooled_intermittent_4_subjects"] = dict(tot)

    write_json("s02_position_order_time.json", res)
    import json
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
