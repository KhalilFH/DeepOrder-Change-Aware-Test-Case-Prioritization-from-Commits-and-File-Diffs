"""F1: R2 equality test, then (only if it passes) Analysis B.

Protocol: f1/protocol.md, rule R2 and "Analyses" B.

R2 test: every one of the 30 PRIMARY_small_fault cycles in the committed report
(inputs/step3_report_25eb6b7.json) must be reproduced by the re-run in cycle id,
m, n, apfd_hist and apfd_t0, within 1e-9. All 82 scored cycles are also compared
and reported. The rankings must also reproduce their own cycle APFD under M1.

Analysis B: exact APFD per cycle and arm under M1 (singletons), M2 (one block)
and M3 (every set partition of the cycle's failing tests), the same partition on
both arms. Mean-difference range under M3 takes each cycle's partition choice
independently (cycles have different failing tests).

    python analysis/r2_check_and_analysis_b.py <rerun_report.json> <rankings.csv>
Run from f1/. Writes analysis/r2_check.json and, if R2 passes,
analysis/analysis_b_cycles.csv and analysis/analysis_b_summary.json.
"""
import csv
import json
import sys
from collections import defaultdict

TOL = 1e-9
COMMITTED = "inputs/step3_report_25eb6b7.json"


def set_partitions(items):
    if not items:
        yield []
        return
    first, rest = items[0], items[1:]
    for part in set_partitions(rest):
        for i in range(len(part)):
            yield part[:i] + [[first] + part[i]] + part[i + 1:]
        yield [[first]] + part


def apfd(rank_of, part, n):
    k = len(part)
    return 1 - sum(min(rank_of[t] for t in block) for block in part) / (n * k) + 1 / (2 * n)


def wtl(diffs):
    return [sum(d > TOL for d in diffs), sum(abs(d) <= TOL for d in diffs), sum(d < -TOL for d in diffs)]


def r2_check(rerun_path, rankings):
    with open(COMMITTED, encoding="utf-8") as fh:
        old = {c["cycle"]: c for c in json.load(fh)["per_cycle"]}
    with open(rerun_path, encoding="utf-8") as fh:
        new = {c["cycle"]: c for c in json.load(fh)["per_cycle"]}
    fields = ("m", "n", "apfd_hist", "apfd_t0")
    mism = []
    for cyc in sorted(set(old) | set(new)):
        if cyc not in old or cyc not in new:
            mism.append({"cycle": cyc, "issue": "missing in " + ("rerun" if cyc not in new else "committed")})
            continue
        for f in fields:
            if abs(old[cyc][f] - new[cyc][f]) > TOL:
                mism.append({"cycle": cyc, "field": f, "committed": old[cyc][f], "rerun": new[cyc][f]})
    cohort = sorted(c for c in old if old[c]["m"] <= 4)
    cohort_mism = [x for x in mism if x["cycle"] in cohort]
    # rankings reproduce their own M1 APFD
    self_mism = []
    for (cyc, arm), rs in rankings.items():
        if arm not in ("hist", "t0"):
            continue
        n = len(rs)
        fails = {r["name"]: r["rank"] for r in rs if r["verdict"] == 1}
        m1 = apfd(fails, [[t] for t in fails], n)
        if abs(m1 - float(rs[0]["cycle_apfd"])) > TOL or abs(m1 - new[cyc]["apfd_" + arm]) > TOL:
            self_mism.append({"cycle": cyc, "arm": arm})
    return {
        "committed_report": COMMITTED,
        "rerun_report": rerun_path,
        "fields_compared": list(fields),
        "tolerance": TOL,
        "n_cycles_committed": len(old),
        "n_cycles_rerun": len(new),
        "cohort_cycles": len(cohort),
        "cohort_mismatches": cohort_mism,
        "all_cycle_mismatches": mism,
        "ranking_self_consistency_mismatches": self_mism,
        "R2_PASS": not cohort_mism and not self_mism and len(cohort) == 30,
    }, cohort, new


def analysis_b(cohort, rankings, new):
    rows, per = [], []
    for cyc in cohort:
        rh, rt = rankings[(cyc, "hist")], rankings[(cyc, "t0")]
        n = len(rh)
        fh = {r["name"]: r["rank"] for r in rh if r["verdict"] == 1}
        ft = {r["name"]: r["rank"] for r in rt if r["verdict"] == 1}
        assert set(fh) == set(ft) and len(fh) == new[cyc]["m"], cyc
        tests = sorted(fh)
        parts = list(set_partitions(tests))
        diffs = {}
        for p in parts:
            key = " | ".join(",".join(sorted(b)) for b in sorted(p, key=lambda b: sorted(b)))
            diffs[key] = (apfd(fh, p, n), apfd(ft, p, n))
        m1 = [[t] for t in tests]
        m2 = [tests]
        a1h, a1t = apfd(fh, m1, n), apfd(ft, m1, n)
        a2h, a2t = apfd(fh, m2, n), apfd(ft, m2, n)
        d3 = [t - h for h, t in diffs.values()]
        per.append({"cycle": cyc, "m": len(tests), "n": n,
                    "hist_fail_ranks": sorted(fh.values()), "t0_fail_ranks": sorted(ft.values()),
                    "m1_hist": a1h, "m1_t0": a1t, "m1_diff": a1t - a1h,
                    "m2_hist": a2h, "m2_t0": a2t, "m2_diff": a2t - a2h,
                    "m3_diff_min": min(d3), "m3_diff_max": max(d3), "n_partitions": len(parts)})
        for key, (h, t) in diffs.items():
            rows.append({"cycle": cyc, "partition": key, "k": key.count("|") + 1,
                         "apfd_hist": h, "apfd_t0": t, "diff": t - h})
    N = len(per)
    summary = {
        "cohort": "PRIMARY_small_fault (m<=4), 30 cycles",
        "M1_mean_diff": sum(p["m1_diff"] for p in per) / N,
        "M1_win_tie_loss": wtl([p["m1_diff"] for p in per]),
        "M2_mean_diff": sum(p["m2_diff"] for p in per) / N,
        "M2_win_tie_loss": wtl([p["m2_diff"] for p in per]),
        "M2_mean_hist": sum(p["m2_hist"] for p in per) / N,
        "M2_mean_t0": sum(p["m2_t0"] for p in per) / N,
        "M3_mean_diff_range": [sum(p["m3_diff_min"] for p in per) / N, sum(p["m3_diff_max"] for p in per) / N],
        "cycles_where_mapping_changes_diff": sum(1 for p in per if p["m3_diff_max"] - p["m3_diff_min"] > TOL),
        "cycles_whose_sign_differs_M1_vs_M2": sum(
            1 for p in per if (p["m1_diff"] > TOL) - (p["m1_diff"] < -TOL) != (p["m2_diff"] > TOL) - (p["m2_diff"] < -TOL)),
        "note": "exact values from recovered rankings; mapping ranges are assumptions, not sampling intervals; cycles are correlated",
    }
    m1s = (summary["M1_mean_diff"] > TOL) - (summary["M1_mean_diff"] < -TOL)
    m2s = (summary["M2_mean_diff"] > TOL) - (summary["M2_mean_diff"] < -TOL)
    lo, hi = summary["M3_mean_diff_range"]
    summary["M2_mean_sign_reversal_vs_M1"] = m1s != 0 and m2s == -m1s
    summary["M3_mean_sign_reversal_possible"] = (m1s < 0 and hi > TOL) or (m1s > 0 and lo < -TOL)
    return per, rows, summary


def main():
    rerun_path, rankings_path = sys.argv[1], sys.argv[2]
    rankings = defaultdict(list)
    with open(rankings_path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            r["rank"], r["verdict"], r["cycle"] = int(r["rank"]), int(r["verdict"]), int(r["cycle"])
            rankings[(r["cycle"], r["arm"])].append(r)
    check, cohort, new = r2_check(rerun_path, rankings)
    with open("analysis/r2_check.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(check, fh, indent=2)
        fh.write("\n")
    print(json.dumps({k: (v if not isinstance(v, list) or len(v) < 6 else f"{len(v)} items") for k, v in check.items()}, indent=2))
    if not check["R2_PASS"]:
        print("R2 FAILED: ranking part stops (protocol). Analysis B not run.")
        return 1
    per, rows, summary = analysis_b(cohort, rankings, new)
    fmt = lambda d: {k: (f"{v:.6f}" if isinstance(v, float) else v) for k, v in d.items()}
    with open("analysis/analysis_b_cycles.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(per[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(fmt(p) for p in per)
    with open("analysis/analysis_b_partitions.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(fmt(r) for r in rows)
    with open("analysis/analysis_b_summary.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, indent=2)
        fh.write("\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
