#!/usr/bin/env python3
"""
Rung 1: does a HIGH-PRECISION name signal beat history where T0's noisy cosine didn't?

Same prequential/paired harness as step3_t0.py (imported verbatim -- no duplicated
stats), but the added arm is `exact_target_hit` and/or `package_hit` (relevance_precise)
instead of T0. Arms differ only by those columns, so any APFD change is attributable to
them. Motivated by the hbase viability gate (T0 fires ~97.5%, true hits 6-31%).

Usage
  python pipeline/step3_precise.py --dataset <enhanced.csv> --out <dir> \
      [--features both|exact|package] [--train-window-cycles N] [--max-eval-cycles N] \
      [--small-fault-max 4] [--chronic-min 21]
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import step2_baseline as base  # noqa: E402
import step3_t0 as s3  # noqa: E402  (reuse build_features, eval helpers, stats, strata)
from relevance_precise import compute_precise_columns  # noqa: E402

FEATURE_CHOICES = {"exact": ["exact_target_hit"],
                   "package": ["package_hit"],
                   "both": ["exact_target_hit", "package_hit"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--features", default="both", choices=list(FEATURE_CHOICES))
    ap.add_argument("--train-window-cycles", type=int, default=0)
    ap.add_argument("--max-eval-cycles", type=int, default=0)
    ap.add_argument("--small-fault-max", type=int, default=s3.SMALL_FAULT_MAX)
    ap.add_argument("--chronic-min", type=int, default=s3.CHRONIC_MIN)
    args = ap.parse_args()
    if args.small_fault_max >= args.chronic_min:
        raise SystemExit("--small-fault-max must be < --chronic-min")

    out = args.out or os.path.dirname(os.path.abspath(args.dataset))
    os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(s3.RANDOM_STATE)

    df = pd.read_csv(args.dataset)
    need = {"Cycle", "Verdict", "LastResults", "Duration", "BuildStartedAt",
            "LastRun", "Name", "FilesChanged"}
    missing = need - set(df.columns)
    if missing:
        raise SystemExit(f"dataset missing required columns: {sorted(missing)}")
    df["Verdict"] = df["Verdict"].astype(int)
    df = s3.build_features(df)

    # --- the added features (label-free, per-test within cycle) ---
    exact, pkg = compute_precise_columns(df)
    df["exact_target_hit"] = exact
    df["package_hit"] = pkg
    added = FEATURE_CHOICES[args.features]
    if all(float(np.std(df[a])) < 1e-12 for a in added):
        raise SystemExit(f"added features {added} are globally constant -- dead signal.")
    fires = {a: round(float((df[a] > 0).mean()), 4) for a in added}

    features_hist = base.FEATURES_FULL
    features_precise = base.FEATURES_FULL + added

    cyc_stats = df.groupby("Cycle")["Verdict"].agg(m="sum", n="count")
    cycles_sorted = np.sort(df["Cycle"].unique())
    scorable = [int(c) for c in cycles_sorted
                if int(cyc_stats.loc[c, "n"]) >= 2 and int(cyc_stats.loc[c, "m"]) >= 1]
    eval_set = set(s3.select_eval_cycles(scorable, args.max_eval_cycles))

    per_cycle, untrainable, unscorable, subsampled_out = [], [], 0, 0
    for c in cycles_sorted:
        g = df[df["Cycle"] == c]
        m, n = int(cyc_stats.loc[c, "m"]), int(cyc_stats.loc[c, "n"])
        if n < 2 or m == 0:
            unscorable += 1
            continue
        if int(c) not in eval_set:
            subsampled_out += 1
            continue
        train = s3.training_rows(df, c, args.train_window_cycles)
        if train["Verdict"].nunique() < 2 or len(train) < s3.MIN_TRAIN_ROWS:
            untrainable.append(int(c))
            continue
        s_hist = s3.fit_predict(train, g, features_hist)
        s_prec = s3.fit_predict(train, g, features_precise)
        v = g["Verdict"].to_numpy(int)
        ties = np.random.default_rng(int(c)).random(len(g))
        per_cycle.append({
            "cycle": int(c), "m": m, "n": n,
            "apfd_hist": s3.apfd_with_fixed_ties(v, s_hist, ties),
            "apfd_t0": s3.apfd_with_fixed_ties(v, s_prec, ties),   # 'apfd_t0' key = precise arm (compare_stratum contract)
        })

    if not per_cycle:
        raise SystemExit("no scorable+trainable cycles -- degenerate run.")

    sfm, cmin = args.small_fault_max, args.chronic_min
    small, chronic, small_tiny, small_large = s3.stratify(per_cycle, sfm, cmin, s3.TINY_CYCLE_MAX)
    report = {
        "dataset": os.path.abspath(args.dataset),
        "rung": "1 (precise name relevance)",
        "added_features": added,
        "feature_fire_rates": fires,
        "arms": {"hist": features_hist, "hist_plus_precise": features_precise},
        "eval": {
            "n_cycles_total": int(len(cycles_sorted)),
            "n_scorable_total": len(scorable),
            "n_subsampled_out": subsampled_out,
            "n_untrainable_prefix": len(untrainable),
            "n_scored": len(per_cycle),
            "train_window_cycles": args.train_window_cycles or "expanding",
            "max_eval_cycles": args.max_eval_cycles or "all",
            "small_fault_definition": f"m <= {sfm}",
        },
        "PRIMARY_small_fault": s3.compare_stratum(f"small_fault (m<={sfm})", small, rng),
        "SECONDARY_chronic": s3.compare_stratum(f"chronic (m>={cmin})", chronic, rng),
        "SECONDARY_all_scored": s3.compare_stratum("all_scored", per_cycle, rng),
        "per_cycle": per_cycle,
    }
    with open(os.path.join(out, "step3_precise_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"== Rung 1: precise name relevance {added} (fires {fires}) -- paired, prequential ==")
    print(f"scored cycles {len(per_cycle)}  (unscorable {unscorable}, "
          f"subsampled-out {subsampled_out}, untrainable {len(untrainable)})")
    for key in ("PRIMARY_small_fault", "SECONDARY_chronic", "SECONDARY_all_scored"):
        b = report[key]
        if b.get("n_cycles", 0) == 0:
            print(f"\n[{key}] no cycles"); continue
        h, t = b["apfd_hist"], b["apfd_hist_plus_t0"]
        print(f"\n[{key}]  n={b['n_cycles']}")
        print(f"  APFD  HIST         {h['mean']:.4f} (median {h['median']})")
        print(f"        HIST+PRECISE {t['mean']:.4f} (median {t['median']})")
        print(f"  mean paired diff {b['mean_paired_diff']:+.4f}  boot95 {b['bootstrap95_mean_diff']}  "
              f"Wilcoxon p {b['wilcoxon_p_two_sided']}  A12 {b['vargha_a12_t0_over_hist']}")
        print(f"  win/tie/loss {b['win_tie_loss']}")
    print(f"\nwrote: {os.path.join(out, 'step3_precise_report.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
