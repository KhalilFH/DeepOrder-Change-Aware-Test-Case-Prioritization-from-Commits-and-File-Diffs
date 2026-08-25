#!/usr/bin/env python3
"""
Fault-structure probe -- instant go/no-go on whether a TCP-CI subject can serve as a
test bed for a change-relevance signal (T0 and friends), BEFORE building the full
Step 1-3 pipeline on it.

Motivation
----------
On apache@airavata the T0 path-token relevance feature was a clean NULL (see
docs/NEXT-STEPS.md "RESULT"). The diagnosis: airavata's failures are *recurring*
(a test that fails today already failed last run), so a history-only model already
ranks them first and a change signal has no headroom. A subject is a useful test bed
only if it has the opposite property: **change-induced, non-recurring failures with a
gap between what history can do and the optimal ordering.**

This probe measures exactly those two things from the cheapest possible inputs
(`exe.csv` + `builds.csv` -- no git, no name join, no schema generation):

  1. RECURRENCE   -- of all failing executions that had a prior run, what fraction
                     failed on that prior run (E1=1). High => history-predictable
                     (airavata-like, bad); low => fresh/change-induced (good).
  2. HEADROOM     -- per scorable cycle, optimal APFD minus the best cheap history
                     heuristic APFD (rank by prior fail-rate / failed-last-run). Large
                     gap => room for a smarter change-aware signal to help; ~0 => the
                     regime is saturated and nothing can help (airavata-like).

Reported per fault-set-size stratum (small-fault m<=4 primary, chronic m>=CHRONIC_MIN
separate), plus the m-distribution and any dominant chronic co-failure block.

No broad try/except: malformed inputs raise. This is a screening tool -- its verdict
is advisory ("GO"/"MARGINAL"/"NO-GO (airavata-like)"); a human reads the numbers.

Usage
  python pipeline/fault_structure_probe.py \
      --data <slice>/TCP-CI-dataset/datasets/<owner>@<repo>
  # or point at the two files directly:
  python pipeline/fault_structure_probe.py --exe .../exe.csv --builds .../builds.csv
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

SMALL_FAULT_MAX = 4
CHRONIC_MIN = 15          # airavata's chronic block is m=21; >=15 catches such blocks
RECURRENCE_GO = 0.60      # recurrence at/above this => history-predictable (bad for T0)
HEADROOM_GO = 0.08        # small-fault optimal-minus-history gap below this => saturated


# --------------------------------------------------------------------------- #
def apfd_from_order(verdicts_in_order):
    """APFD = 1 - (sum ranks of fails)/(n*m) + 1/(2n). None if <2 tests or 0 fails."""
    v = list(verdicts_in_order)
    n = len(v)
    ranks = [i + 1 for i, x in enumerate(v) if x == 1]
    m = len(ranks)
    if n < 2 or m == 0:
        return None
    return 1.0 - (sum(ranks) / (n * m)) + (1.0 / (2 * n))


def apfd_by_score(verdicts, score, ties):
    order = np.lexsort((ties, -np.asarray(score, dtype=float)))
    return apfd_from_order(np.asarray(verdicts)[order])


def load(args):
    if args.data:
        exe_p = os.path.join(args.data, "exe.csv")
        bld_p = os.path.join(args.data, "builds.csv")
    else:
        exe_p, bld_p = args.exe, args.builds
    if not exe_p or not os.path.exists(exe_p):
        raise SystemExit(f"exe.csv not found: {exe_p}")
    if not bld_p or not os.path.exists(bld_p):
        raise SystemExit(f"builds.csv not found: {bld_p}")
    exe = pd.read_csv(exe_p)
    builds = pd.read_csv(bld_p)
    for c in ("test", "build", "verdict"):
        if c not in exe.columns:
            raise SystemExit(f"exe.csv missing column {c!r} (has {list(exe.columns)})")
    bid = "id" if "id" in builds.columns else builds.columns[0]
    tcol = "started_at" if "started_at" in builds.columns else None
    if tcol is None:
        raise SystemExit(f"builds.csv has no started_at (has {list(builds.columns)})")
    return exe, builds, bid, tcol


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None, help="datasets/<owner>@<repo> dir")
    ap.add_argument("--exe", default=None)
    ap.add_argument("--builds", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--label", default=None, help="subject name for the report")
    args = ap.parse_args()

    exe, builds, bid, tcol = load(args)
    label = args.label or (os.path.basename(os.path.normpath(args.data))
                           if args.data else "subject")

    # --- verdict folding: 0=pass, 1/2=fail, 3=unknown(dropped) ---
    v = pd.to_numeric(exe["verdict"], errors="coerce")
    n_unknown = int(((v == 3) | v.isna()).sum())
    exe = exe.loc[v.isin([0, 1, 2])].copy()
    exe["fail"] = exe["verdict"].isin([1, 2]).astype(int)

    # --- temporal order of builds ---
    started = pd.to_datetime(builds[tcol], errors="coerce", utc=True)
    order_of = {b: i for i, b in enumerate(builds[bid].to_numpy()[np.argsort(
        started.fillna(pd.Timestamp.min.tz_localize("UTC")).to_numpy())])}
    exe = exe[exe["build"].isin(order_of)].copy()
    exe["border"] = exe["build"].map(order_of)
    exe = exe.sort_values(["test", "border"], kind="mergesort")

    # --- causal per-test history: previous verdict + prior fail-rate ---
    exe["prev_fail"] = exe.groupby("test")["fail"].shift(1)      # E1 (NaN = first run)
    csum = exe.groupby("test")["fail"].cumsum() - exe["fail"]    # fails strictly before
    cnt = exe.groupby("test").cumcount()                          # runs strictly before
    exe["prior_fail_rate"] = np.where(cnt > 0, csum / cnt.replace(0, np.nan), 0.0)
    exe["prior_fail_rate"] = exe["prior_fail_rate"].fillna(0.0)
    exe["e1"] = exe["prev_fail"].fillna(0.0)

    # --- RECURRENCE: among failing execs with a prior run, how many failed before ---
    fails = exe[exe["fail"] == 1]
    fails_prior = fails[fails["prev_fail"].notna()]
    recurrence = float(fails_prior["prev_fail"].mean()) if len(fails_prior) else None
    nonrecurring = (1.0 - recurrence) if recurrence is not None else None

    # --- per-cycle (=build) fault size m and size n; APFD headroom ---
    rng_seed = 12345
    rows = []
    for b, g in exe.groupby("border", sort=True):
        n = len(g); m = int(g["fail"].sum())
        if n < 2 or m == 0:
            continue
        ties = np.random.default_rng(int(b) + rng_seed).random(n)
        vv = g["fail"].to_numpy(int)
        a_opt = apfd_from_order(sorted(vv.tolist(), reverse=True))
        a_pfr = apfd_by_score(vv, g["prior_fail_rate"].to_numpy(float), ties)
        a_e1 = apfd_by_score(vv, g["e1"].to_numpy(float), ties)
        a_hist = max(a_pfr, a_e1)          # best cheap history heuristic
        rperm = np.random.default_rng(int(b) + 999)
        a_rand = float(np.mean([apfd_from_order(vv[rperm.permutation(n)])
                                for _ in range(30)]))
        rec = g[g["fail"] == 1]["prev_fail"]
        rows.append({"m": m, "n": n, "opt": a_opt, "hist": a_hist,
                     "rand": a_rand, "headroom": a_opt - a_hist,
                     "recur": float(rec.mean()) if rec.notna().any() else None})
    cyc = pd.DataFrame(rows)
    if cyc.empty:
        raise SystemExit("no scorable cycles (>=2 tests & >=1 fail) -- unusable subject.")

    def stratum(df, name):
        if df.empty:
            return {"stratum": name, "n_cycles": 0}
        rr = df["recur"].dropna()
        return {
            "stratum": name, "n_cycles": int(len(df)),
            "apfd_hist_heuristic": round(float(df["hist"].mean()), 4),
            "apfd_optimal": round(float(df["opt"].mean()), 4),
            "apfd_random": round(float(df["rand"].mean()), 4),
            "headroom_opt_minus_hist": round(float(df["headroom"].mean()), 4),
            "recurrence_rate": (round(float(rr.mean()), 4) if len(rr) else None),
        }

    small = cyc[cyc["m"] <= SMALL_FAULT_MAX]
    chronic = cyc[cyc["m"] >= CHRONIC_MIN]
    mdist = {int(k): int(vv) for k, vv in cyc["m"].value_counts().sort_index().items()}
    dom_m, dom_ct = (max(mdist.items(), key=lambda kv: kv[1]) if mdist else (None, 0))

    small_stat = stratum(small, f"small_fault (m<={SMALL_FAULT_MAX})")

    # --- advisory verdict (airavata-like = high recurrence + no small-fault headroom) ---
    sf_rec = small_stat.get("recurrence_rate")
    sf_head = small_stat.get("headroom_opt_minus_hist")
    if small_stat["n_cycles"] < 5:
        verdict = "INSUFFICIENT (too few small-fault cycles to judge)"
    elif (sf_rec is not None and sf_rec >= RECURRENCE_GO
          and sf_head is not None and sf_head < HEADROOM_GO):
        verdict = "NO-GO (airavata-like: recurring failures, no headroom)"
    elif (sf_rec is not None and sf_rec < RECURRENCE_GO
          and sf_head is not None and sf_head >= HEADROOM_GO):
        verdict = "GO (non-recurring failures + headroom -> good T0 test bed)"
    else:
        verdict = "MARGINAL (mixed signals -- inspect the strata)"

    report = {
        "subject": label,
        "n_builds_total": int(len(builds)),
        "n_execs": int(len(exe)),
        "n_verdict_unknown_dropped": n_unknown,
        "overall_fail_rate": round(float(exe["fail"].mean()), 4),
        "n_scorable_cycles": int(len(cyc)),
        "m_distribution": mdist,
        "dominant_m": {"m": (int(dom_m) if dom_m is not None else None),
                       "cycles": int(dom_ct),
                       "share_of_scorable": round(dom_ct / len(cyc), 4)},
        "recurrence_rate_all_fails": (round(recurrence, 4)
                                      if recurrence is not None else None),
        "nonrecurring_frac_all_fails": (round(nonrecurring, 4)
                                        if nonrecurring is not None else None),
        "strata": {
            "small_fault": small_stat,
            "chronic": stratum(chronic, f"chronic (m>={CHRONIC_MIN})"),
            "all_scorable": stratum(cyc, "all_scorable"),
        },
        "thresholds": {"recurrence_go_below": RECURRENCE_GO,
                       "headroom_go_at_or_above": HEADROOM_GO},
        "VERDICT": verdict,
    }

    out = args.out or (args.data or ".")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "fault_structure_probe.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"== fault-structure probe: {label} ==")
    print(f"builds {report['n_builds_total']}  execs {report['n_execs']}  "
          f"fail-rate {report['overall_fail_rate']:.1%}  "
          f"scorable cycles {report['n_scorable_cycles']}  "
          f"(unknown-verdict dropped {n_unknown})")
    print(f"m-distribution (failing cycles): {mdist}")
    print(f"dominant m={report['dominant_m']['m']} in "
          f"{report['dominant_m']['cycles']} cycles "
          f"({report['dominant_m']['share_of_scorable']:.0%} of scorable)")
    print(f"recurrence (all fails w/ prior run): "
          f"{report['recurrence_rate_all_fails']}  "
          f"=> non-recurring {report['nonrecurring_frac_all_fails']}")
    for k in ("small_fault", "chronic", "all_scorable"):
        s = report["strata"][k]
        if s.get("n_cycles"):
            print(f"  [{s['stratum']}] n={s['n_cycles']}  "
                  f"hist {s['apfd_hist_heuristic']}  opt {s['apfd_optimal']}  "
                  f"headroom {s['headroom_opt_minus_hist']}  "
                  f"recurrence {s['recurrence_rate']}")
    print(f"\nVERDICT: {verdict}")
    print(f"wrote: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
