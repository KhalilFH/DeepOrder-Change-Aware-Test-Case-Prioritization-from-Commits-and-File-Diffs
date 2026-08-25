#!/usr/bin/env python3
"""
Deflake-then-prioritize evaluation on REGRESSION-APFD (the headline hbase result).

Same prequential gradient-boosted history model as step3_t0.py, but APFD faults =
PERSISTENT regressions per cycle (a failing test whose failure carries into its NEXT
execution, F->F). Transient/flaky failures do NOT count as targets to surface early.
Three arms, differing only by the added feature(s):

  HIST           : FEATURES_FULL
  HIST+T0        : + T0 change-relevance (relevance_t0, --identity)
  HIST+T0+flaky  : + T0 + causal flaky-propensity (flip-rate from prior history)

Paired Wilcoxon vs HIST tells whether relevance beats the real history model at
surfacing genuine regressions early.

NOTE — this is a RESEARCH evaluation, not a deployable metric: the persistent-regression
fault labels use the FUTURE (does the failure persist), which is legitimate ground truth
for measuring a ranker but is not knowable at prioritisation time. All RANKERS use only
causal features. Finding (hbase): feeding flaky-propensity as a MODEL feature hurts (a
Verdict-predicting model uses it to predict flaky failures) -- deflake belongs at ranking
time, not in the model; HIST+T0 is the clean arm.

Usage
  python pipeline/step3_regapfd.py --dataset <enhanced.csv> \
      [--identity fqn] [--train-window-cycles 100] [--max-eval-cycles 0] \
      [--small-fault-max 4] [--out <dir>]
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import step2_baseline as base  # noqa: E402
import step3_t0 as s3  # noqa: E402  (reuse build_features, training_rows, select_eval_cycles, fit_predict)
from relevance_t0 import compute_t0_column  # noqa: E402


def flip_rate(last_results) -> float:
    v = [int(c) for c in str(last_results) if c in "01"]
    return sum(1 for i in range(len(v) - 1) if v[i] != v[i + 1]) / max(len(v) - 1, 1) if len(v) > 1 else 0.0


def regression_labels(df: pd.DataFrame) -> np.ndarray:
    """1 where a failing test's failure PERSISTS into its next execution (F->F)."""
    seqs, idx = {}, {}
    for name, g in df.sort_values("Cycle").groupby("Name"):
        seqs[name] = g["Verdict"].tolist()
        idx[name] = {c: i for i, c in enumerate(g["Cycle"].tolist())}
    out = np.zeros(len(df), dtype=int)
    for pos, (v, n, c) in enumerate(zip(df["Verdict"], df["Name"], df["Cycle"])):
        if v == 1:
            seq = seqs[n]; i = idx[n][c]
            if i < len(seq) - 1 and seq[i + 1] == 1:
                out[pos] = 1
    return out


def reg_apfd(fault_mask: np.ndarray, scores, ties) -> float | None:
    n, mf = len(fault_mask), int(fault_mask.sum())
    if n < 2 or mf == 0:
        return None
    order = np.lexsort((ties, -np.asarray(scores, float)))
    ranks = np.where(fault_mask[order] == 1)[0] + 1
    return 1.0 - ranks.sum() / (n * mf) + 1.0 / (2 * n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--identity", default="fqn", choices=["path", "fqn"])
    ap.add_argument("--train-window-cycles", type=int, default=100)
    ap.add_argument("--max-eval-cycles", type=int, default=0)
    ap.add_argument("--small-fault-max", type=int, default=s3.SMALL_FAULT_MAX)
    args = ap.parse_args()

    out = args.out or os.path.dirname(os.path.abspath(args.dataset))
    os.makedirs(out, exist_ok=True)

    # FilesChanged is the commit's change-set string, identical for every row in a
    # cycle -> reading it as a categorical collapses ~14GB of duplicated text to one
    # value per cycle. Results-neutral: it is only consumed via .unique()/parse per
    # cycle group in compute_t0_column. (Needed for LRTS subjects like hive whose CSV
    # is ~15GB and would otherwise exhaust RAM.)
    df = pd.read_csv(args.dataset, dtype={"FilesChanged": "category"})
    need = {"Cycle", "Verdict", "LastResults", "Duration", "BuildStartedAt",
            "LastRun", "Name", "FilesChanged"}
    missing = need - set(df.columns)
    if missing:
        raise SystemExit(f"dataset missing required columns: {sorted(missing)}")
    df["Verdict"] = df["Verdict"].astype(int)
    df = s3.build_features(df)
    df["T0"] = compute_t0_column(df, {n: n for n in df["Name"].unique()}, identity=args.identity)
    df["flaky_prop"] = df["LastResults"].apply(flip_rate)
    df["is_reg"] = regression_labels(df)

    FH = base.FEATURES_FULL
    arms = {"HIST": FH, "HIST+T0": FH + ["T0"], "HIST+T0+flaky": FH + ["T0", "flaky_prop"]}

    m = df.groupby("Cycle")["Verdict"].sum()
    small = set(m[(m >= 1) & (m <= args.small_fault_max)].index)
    reg_per_cycle = df.groupby("Cycle")["is_reg"].sum()
    cand = [int(c) for c in np.sort(df["Cycle"].unique())
            if c in small and reg_per_cycle.loc[c] >= 1 and int((df["Cycle"] == c).sum()) >= 2]
    eval_set = set(s3.select_eval_cycles(cand, args.max_eval_cycles))

    per = {k: [] for k in arms}
    scored, untrainable = 0, 0
    for c in np.sort(df["Cycle"].unique()):
        if int(c) not in eval_set:
            continue
        g = df[df["Cycle"] == c]
        train = s3.training_rows(df, c, args.train_window_cycles)
        if train["Verdict"].nunique() < 2 or len(train) < s3.MIN_TRAIN_ROWS:
            untrainable += 1
            continue
        fault = g["is_reg"].to_numpy(int)
        ties = np.random.default_rng(int(c)).random(len(g))
        row, ok = {}, True
        for name, feats in arms.items():
            a = reg_apfd(fault, s3.fit_predict(train, g, feats), ties)
            if a is None:
                ok = False
                break
            row[name] = a
        if ok:
            scored += 1
            for k in arms:
                per[k].append(row[k])

    if scored == 0:
        raise SystemExit("no scorable regression cycles -- degenerate run.")

    base_a = np.array(per["HIST"])
    report = {"dataset": os.path.abspath(args.dataset), "metric": "regression-APFD (faults=persistent F->F)",
              "identity": args.identity, "train_window_cycles": args.train_window_cycles,
              "n_scored_cycles": scored, "n_untrainable": untrainable, "arms": {}}
    print(f"regression-APFD, full GB model, identity={args.identity}, "
          f"window={args.train_window_cycles}, scored {scored} cycles\n")
    for k in arms:
        a = np.array(per[k])
        report["arms"][k] = {"mean": round(float(a.mean()), 4), "median": round(float(np.median(a)), 4)}
        print(f"  {k:14s} mean {a.mean():.4f}  median {np.median(a):.4f}")
    print("\npaired Wilcoxon vs HIST:")
    for k in ("HIST+T0", "HIST+T0+flaky"):
        a = np.array(per[k]); d = a - base_a
        p = float(wilcoxon(a, base_a)[1]) if np.any(d != 0) else float("nan")
        wins, losses = int((d > 1e-9).sum()), int((d < -1e-9).sum())
        report["arms"][k].update({"mean_diff": round(float(d.mean()), 4),
                                  "wilcoxon_p": p, "win": wins, "loss": losses})
        print(f"  {k:14s} mean diff {d.mean():+.4f}  Wilcoxon p {p:.3e}  win/loss {wins}/{losses}")

    with open(os.path.join(out, "step3_regapfd_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nwrote: {os.path.join(out, 'step3_regapfd_report.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
