"""F1 Analysis A: logical bounds on the HIST vs HIST+T0 comparison under
alternative fault mappings, from the committed per-cycle aggregates alone.

Protocol: f1/protocol.md ("Analyses", A). Input: f1/inputs/step3_report_25eb6b7.json
(git blob 6ce7b665... of FINAL6/apache@airavata/step3_report.json at 25eb6b7).

For a cycle with n ranked tests and m failing tests, the reported APFD
(one failed test = one fault, "M1") fixes S = sum of the failing tests' ranks:
    APFD = 1 - S / (n*m) + 1/(2n)
The individual ranks are unknown: any m distinct integers in [1, n] summing to S
are consistent with the record. A mapping partitions the m failing tests into
k faults; each fault is detected at the best rank among its tests:
    APFD_P = 1 - (sum over faults of min rank) / (n*k) + 1/(2n)
The same partition applies to both arms. The bounds below range over every
rank set consistent with each arm's S and every assignment of ranks to tests.
They are logical bounds under these arithmetic constraints, not estimates.

M2 = one fault per cycle (one block). M3 = all set partitions (includes M1, M2).

Run from research_runs/ci_sensitivity_2026_09/f1/:
    python analysis/aggregate_bounds.py
Writes analysis/aggregate_bounds_cycles.csv and analysis/aggregate_bounds_summary.json.
"""
import csv
import itertools
import json

REPORT = "inputs/step3_report_25eb6b7.json"
TOL = 1e-6


def set_partitions(items):
    if not items:
        yield []
        return
    first, rest = items[0], items[1:]
    for part in set_partitions(rest):
        for i in range(len(part)):
            yield part[:i] + [[first] + part[i]] + part[i + 1:]
        yield [[first]] + part


def rank_sum(apfd, n, m):
    s = (1 - apfd + 1 / (2 * n)) * n * m
    if abs(s - round(s)) > TOL:
        raise ValueError(f"non-integer rank sum {s} (n={n}, m={m}, apfd={apfd})")
    return round(s)


def rank_sets(n, m, s):
    return [c for c in itertools.combinations(range(1, n + 1), m) if sum(c) == s]


def apfd_from(block_min_sum, n, k):
    return 1 - block_min_sum / (n * k) + 1 / (2 * n)


def cycle_bounds(c):
    n, m = c["n"], c["m"]
    s_h, s_t = rank_sum(c["apfd_hist"], n, m), rank_sum(c["apfd_t0"], n, m)
    sets_h, sets_t = rank_sets(n, m, s_h), rank_sets(n, m, s_t)
    if not sets_h or not sets_t:
        raise ValueError(f"no consistent rank set for cycle {c['cycle']}")
    m1_diff = c["apfd_t0"] - c["apfd_hist"]
    labels = list(range(m))
    out = {"cycle": c["cycle"], "m": m, "n": n, "rank_sum_hist": s_h, "rank_sum_t0": s_t,
           "n_rank_sets_hist": len(sets_h), "n_rank_sets_t0": len(sets_t), "m1_diff": m1_diff}
    lo3, hi3 = float("inf"), float("-inf")
    for part in set_partitions(labels):
        k = len(part)
        # HIST: labels fixed to sorted ranks (WLOG, since all partitions and all
        # T0 labelings are enumerated); T0: every set and every labeling.
        vals_h = [sum(min(r[i] for i in b) for b in part) for r in sets_h]
        vals_t = [sum(min(p[i] for i in b) for b in part)
                  for r in sets_t for p in itertools.permutations(r)]
        d_lo = (min(vals_h) - max(vals_t)) / (n * k)  # APFD_t0 - APFD_hist
        d_hi = (max(vals_h) - min(vals_t)) / (n * k)
        if k == 1:
            out["m2_diff_min"], out["m2_diff_max"] = d_lo, d_hi
            out["m2_apfd_hist_min"] = apfd_from(max(vals_h), n, 1)
            out["m2_apfd_hist_max"] = apfd_from(min(vals_h), n, 1)
            out["m2_apfd_t0_min"] = apfd_from(max(vals_t), n, 1)
            out["m2_apfd_t0_max"] = apfd_from(min(vals_t), n, 1)
        if k == m:  # singletons: must reproduce the reported M1 difference exactly
            assert abs(d_lo - m1_diff) < TOL and abs(d_hi - m1_diff) < TOL, c["cycle"]
        lo3, hi3 = min(lo3, d_lo), max(hi3, d_hi)
    out["m3_diff_min"], out["m3_diff_max"] = lo3, hi3
    return out


def wtl(diffs):
    return [sum(d > TOL for d in diffs), sum(abs(d) <= TOL for d in diffs), sum(d < -TOL for d in diffs)]


def main():
    with open(REPORT, encoding="utf-8") as fh:
        report = json.load(fh)
    cohort = [c for c in report["per_cycle"] if c["m"] <= 4]
    prim = report["PRIMARY_small_fault"]

    # Verification before analysis (protocol): the aggregates reproduce the report.
    mh = sum(c["apfd_hist"] for c in cohort) / len(cohort)
    mt = sum(c["apfd_t0"] for c in cohort) / len(cohort)
    assert len(cohort) == prim["n_cycles"] == 30
    assert round(mh, 4) == prim["apfd_hist"]["mean"] and round(mt, 4) == prim["apfd_hist_plus_t0"]["mean"]
    assert round(mt - mh, 4) == prim["mean_paired_diff"]
    assert wtl([c["apfd_t0"] - c["apfd_hist"] for c in cohort]) == prim["win_tie_loss"]

    rows = [cycle_bounds(c) for c in cohort]
    cols = list(rows[-1].keys())
    with open("analysis/aggregate_bounds_cycles.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            if r["m"] == 1:  # every mapping is M1
                for key in ("m2_diff_min", "m2_diff_max", "m3_diff_min", "m3_diff_max"):
                    r.setdefault(key, r["m1_diff"])
            w.writerow({k: (f"{v:.6f}" if isinstance(v, float) else v) for k, v in r.items()})

    n = len(rows)
    sensitive = [r for r in rows if r["m"] >= 2]
    summary = {
        "input": REPORT,
        "cohort": "PRIMARY_small_fault (m<=4)",
        "n_cycles": n,
        "n_cycles_mapping_sensitive_m_ge_2": len(sensitive),
        "verification": "cohort means, mean paired diff and win/tie/loss reproduce the report",
        "M1_mean_diff": sum(r["m1_diff"] for r in rows) / n,
        "M1_win_tie_loss": wtl([r["m1_diff"] for r in rows]),
        "M2_mean_diff_range": [sum(r["m2_diff_min"] for r in rows) / n, sum(r["m2_diff_max"] for r in rows) / n],
        "M3_mean_diff_range": [sum(r["m3_diff_min"] for r in rows) / n, sum(r["m3_diff_max"] for r in rows) / n],
        "M2_cycles_whose_diff_sign_can_differ_from_M1": sum(
            1 for r in sensitive
            if (r["m1_diff"] > TOL and r["m2_diff_min"] < -TOL) or (r["m1_diff"] < -TOL and r["m2_diff_max"] > TOL)
            or (abs(r["m1_diff"]) <= TOL and (r["m2_diff_min"] < -TOL or r["m2_diff_max"] > TOL))),
        "M1_tied_cycles_that_can_be_untied_under_M2": sum(
            1 for r in sensitive if abs(r["m1_diff"]) <= TOL and (r["m2_diff_min"] < -TOL or r["m2_diff_max"] > TOL)),
        "note": "logical bounds from aggregates; not sampling intervals; cycles are correlated",
    }
    summary["M2_mean_diff_sign_reversal_logically_possible"] = summary["M2_mean_diff_range"][1] > TOL
    summary["M3_mean_diff_sign_reversal_logically_possible"] = summary["M3_mean_diff_range"][1] > TOL
    with open("analysis/aggregate_bounds_summary.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, indent=2)
        fh.write("\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
