#!/usr/bin/env python3
"""
Step 3 + Step 4 (airavata) -- add the T0 path-token relevance scalar and test, honestly,
whether it lifts per-cycle APFD over the history-only baseline.

What changes vs Step 2 (exactly one thing)
------------------------------------------
Two model arms are compared. Both are the SAME full history-only model from
`step2_baseline.py` (GradientBoostingClassifier, target=Verdict, identical features,
identical training rows, identical per-cycle tie-breaking):

    HIST   : FEATURES_FULL                       (step2 baseline, the number to beat)
    HIST+T0: FEATURES_FULL + ["T0"]              (baseline + the ONE new feature)

The ONLY difference between the arms is the presence of the T0 column, so any APFD
difference is attributable to T0 and nothing else.

Evaluation -- prequential / rolling (NOT the saturated 70/30 tail)
-----------------------------------------------------------------
The 70/30 tail evaluates only the chronic ~21-test co-failure block, where history
saturates APFD and T0 has no headroom (see RESUME.md). Instead we use an expanding
window: for each *scorable* cycle c (>=2 tests, >=1 failure), train on ALL rows in
cycles < c and predict cycle c. Cycles whose training prefix has <2 Verdict classes
(no failure seen yet) are untrainable and reported, never scored.

Stratification is by fault-set size m (failing tests in the cycle):
    small-fault : m <= 4     <- PRIMARY T0 claim
    chronic     : m >= 21    <- reported separately (saturated regime)
Because airavata's m distribution has a hard gap (m in {1,2,3} then m in {21,32}),
m<=4 is exactly the 31 small-fault cycles. Within the small-fault stratum we ALSO break
down by cycle size n (n<=5 "tiny" vs larger), because T0's behaviour differs sharply by
n and an unstratified mean would hide it.

Step 4 comparison (paired, across cycles, per stratum)
------------------------------------------------------
  * paired Wilcoxon signed-rank on per-cycle APFD (HIST+T0 vs HIST)
  * Vargha-Delaney A12 (stochastic superiority of HIST+T0 over HIST)
  * bootstrap 95% CI of the mean paired APFD difference
  * win/tie/loss counts
No broad try/except: a degenerate run raises; an all-ties stratum is reported explicitly
(a real state), not swallowed.

Usage
  python pipeline/step3_t0.py \
      --dataset FINAL6/apache@airavata/apache@airavata_enhanced_tcp_dataset.csv \
      --name-map <repo-root>/tcpci_slice/TCP-CI-dataset/datasets/apache@airavata/test_name_map.csv
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata, wilcoxon
from sklearn.ensemble import GradientBoostingClassifier

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import step2_baseline as base  # noqa: E402  (reuse feature + APFD machinery)
from relevance_t0 import compute_t0_column  # noqa: E402

RANDOM_STATE = base.RANDOM_STATE
SMALL_FAULT_MAX = 4      # m <= 4  -> small-fault stratum (primary)
CHRONIC_MIN = 21         # m >= 21 -> chronic stratum (reported separately)
TINY_CYCLE_MAX = 5       # n <= 5  -> "tiny" cycle sub-breakdown within small-fault
MIN_TRAIN_ROWS = 50      # a prefix smaller than this is too thin to fit prequentially


# --------------------------------------------------------------------------- #
def build_features(df):
    """Attach the step2 history features + LastRunFeature + Duration (verbatim step2)."""
    feats = df["LastResults"].apply(
        lambda s: base.history_features(base.parse_last_results(s)))
    df = pd.concat([df, pd.DataFrame(list(feats), index=df.index)], axis=1)
    df["Duration"] = pd.to_numeric(df["Duration"], errors="coerce").fillna(0.0)
    bs = pd.to_datetime(df["BuildStartedAt"], errors="coerce", utc=True)
    lr = pd.to_datetime(df["LastRun"], errors="coerce", utc=True)
    gap = (bs - lr).dt.total_seconds() / 86400.0
    df["LastRunFeature"] = gap.fillna(0.0).clip(lower=0.0)
    return df


def apfd_with_fixed_ties(verdicts, scores, ties):
    """APFD ranking by descending score; ties broken by the SAME `ties` vector for both
    arms so a score difference is the only thing that can move the APFD."""
    order = np.lexsort((ties, -np.asarray(scores, dtype=float)))
    return base.apfd_from_order(np.asarray(verdicts)[order])


def fit_predict(train, test, feats):
    clf = GradientBoostingClassifier(random_state=RANDOM_STATE)
    clf.fit(train[feats].to_numpy(float), train["Verdict"].to_numpy(int))
    return clf.predict_proba(test[feats].to_numpy(float))[:, 1]


def vargha_a12(x, y):
    """P(X>Y) + 0.5 P(X=Y) via rank-sum. >0.5 => X (HIST+T0) stochastically larger."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        return None
    r = rankdata(np.concatenate([x, y]))
    r1 = r[:n1].sum()
    return float((r1 / n1 - (n1 + 1) / 2.0) / n2)


def bootstrap_mean_diff_ci(diffs, rng, B=10000, alpha=0.05):
    d = np.asarray(diffs, float)
    if d.size == 0:
        return None
    idx = rng.integers(0, d.size, size=(B, d.size))
    means = d[idx].mean(axis=1)
    lo, hi = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return [round(float(lo), 4), round(float(hi), 4)]


def diagnostics(rec):
    """Model-free explanation of the model result for a stratum: how each reference
    ranker does, and how recurring (already-failing) the faults are."""
    if not rec:
        return {"n_cycles": 0}
    def mean(k):
        return round(float(np.mean([r[k] for r in rec])), 4)
    return {
        "n_cycles": len(rec),
        "apfd_hist_model": mean("apfd_hist"),
        "apfd_t0_model": mean("apfd_t0"),
        "apfd_t0_alone": mean("apfd_t0_alone"),
        "apfd_random": mean("apfd_random"),
        "apfd_optimal": mean("apfd_optimal"),
        "frac_fail_recurring_E1": mean("frac_fail_recurring_E1"),
    }


def compare_stratum(name, rec, rng):
    """rec: list of dicts with apfd_hist, apfd_t0. Returns the Step-4 comparison block."""
    hist = np.array([r["apfd_hist"] for r in rec], float)
    t0 = np.array([r["apfd_t0"] for r in rec], float)
    diffs = t0 - hist
    n = len(diffs)
    wins = int((diffs > 1e-12).sum())
    losses = int((diffs < -1e-12).sum())
    ties = int((np.abs(diffs) <= 1e-12).sum())

    if n == 0:
        return {"stratum": name, "n_cycles": 0, "note": "no scorable cycles"}
    if ties == n:
        wilcox_p = None
        note = ("T0 produced NO ranking change in any cycle of this stratum "
                "(all diffs == 0); Wilcoxon undefined. This is a reported state, "
                "not a swallowed failure.")
    else:
        # paired signed-rank; default drops zero-diffs (standard Wilcoxon handling)
        stat, wilcox_p = wilcoxon(t0, hist, zero_method="wilcox", alternative="two-sided")
        wilcox_p = float(wilcox_p)
        note = None

    return {
        "stratum": name,
        "n_cycles": n,
        "apfd_hist": base.summ(hist.tolist()),
        "apfd_hist_plus_t0": base.summ(t0.tolist()),
        "mean_paired_diff": round(float(diffs.mean()), 4),
        "median_paired_diff": round(float(np.median(diffs)), 4),
        "bootstrap95_mean_diff": bootstrap_mean_diff_ci(diffs, rng),
        "wilcoxon_p_two_sided": wilcox_p,
        "vargha_a12_t0_over_hist": (round(vargha_a12(t0, hist), 4)
                                    if ties != n else 0.5),
        "win_tie_loss": [wins, ties, losses],
        "note": note,
    }


# --------------------------------------------------------------------------- #
def training_rows(df, c, window_cycles):
    """Rows to train on for cycle c. Default (window_cycles<=0) = the full causal prefix
    (expanding window, unchanged behavior). window_cycles=W = only the most recent W
    cycles before c (a sliding window) -- still causal, but bounds each fit's size so a
    ~1M-row subject is tractable."""
    prior = df["Cycle"] < c
    if window_cycles and window_cycles > 0:
        return df[prior & (df["Cycle"] >= c - window_cycles)]
    return df[prior]


def select_eval_cycles(scorable_cycles, max_eval):
    """Which scorable cycles to actually evaluate. Default (max_eval<=0) = all. Otherwise
    a deterministic, evenly-spaced subsample of at most max_eval cycles that preserves the
    temporal span (evenly-spaced, not random, so time coverage stays representative)."""
    sc = list(scorable_cycles)
    if not max_eval or max_eval <= 0 or len(sc) <= max_eval:
        return sc
    idx = np.linspace(0, len(sc) - 1, max_eval).round().astype(int)
    return [sc[i] for i in sorted(set(idx.tolist()))]


def stratify(per_cycle, small_fault_max, chronic_min, tiny_cycle_max):
    """Partition scored cycles by fault-set size m, and small-fault cycles by size n.

    Returns (small, chronic, small_tiny, small_large). Thresholds are parameters, not
    constants, because the right cutoffs are subject-specific: airavata's m has a hard
    {1,2,3}->{21,32} gap so 4/21 are natural there, but another CI subject needs its own
    histogram-driven values.
    """
    small = [r for r in per_cycle if r["m"] <= small_fault_max]
    chronic = [r for r in per_cycle if r["m"] >= chronic_min]
    small_tiny = [r for r in small if r["n"] <= tiny_cycle_max]
    small_large = [r for r in small if r["n"] > tiny_cycle_max]
    return small, chronic, small_tiny, small_large


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--name-map", required=True,
                    help="test_name_map.csv (fqn,path) from Step 1")
    ap.add_argument("--identity", default="path", choices=["path", "fqn"],
                    help="test-identity token source (default: full repo path)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--small-fault-max", type=int, default=SMALL_FAULT_MAX,
                    help=f"m <= this => small-fault stratum (PRIMARY T0 claim); "
                         f"default {SMALL_FAULT_MAX} (airavata-tuned -- recalibrate per subject)")
    ap.add_argument("--chronic-min", type=int, default=CHRONIC_MIN,
                    help=f"m >= this => chronic stratum (reported separately); "
                         f"default {CHRONIC_MIN} (airavata-tuned -- recalibrate per subject)")
    ap.add_argument("--train-window-cycles", type=int, default=0,
                    help="0 (default) = expanding window (train on ALL prior cycles). "
                         ">0 = sliding window of the most recent N cycles -- bounds fit "
                         "size so large subjects are tractable.")
    ap.add_argument("--max-eval-cycles", type=int, default=0,
                    help="0 (default) = evaluate every scorable cycle. >0 = evenly-spaced "
                         "deterministic subsample of at most N scorable cycles.")
    args = ap.parse_args()
    if args.small_fault_max >= args.chronic_min:
        raise SystemExit(f"--small-fault-max ({args.small_fault_max}) must be < "
                         f"--chronic-min ({args.chronic_min})")

    out = args.out or os.path.dirname(os.path.abspath(args.dataset))
    os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(RANDOM_STATE)

    df = pd.read_csv(args.dataset)
    need = {"Cycle", "Verdict", "LastResults", "Duration", "BuildStartedAt",
            "LastRun", "Name", "FilesChanged"}
    missing = need - set(df.columns)
    if missing:
        raise SystemExit(f"dataset missing required columns: {sorted(missing)}")
    df["Verdict"] = df["Verdict"].astype(int)
    if not set(df["Verdict"].unique()) <= {0, 1}:
        raise SystemExit(f"Verdict not binary: {sorted(df['Verdict'].unique())}")

    df = build_features(df)

    # --- the ONE new feature ---
    nm = pd.read_csv(args.name_map)
    name_to_path = dict(zip(nm["fqn"].astype(str), nm["path"].astype(str)))
    df["T0"] = compute_t0_column(df, name_to_path, identity=args.identity)

    # T0 sanity gate: a globally constant T0 means the signal is dead -> that is a
    # failed run, not a datum. Raise loudly.
    t0v = df["T0"].to_numpy(float)
    if float(np.nanstd(t0v)) < 1e-12:
        raise SystemExit("T0 is globally constant -- relevance signal is dead. STOP.")
    t0_within = df.groupby("Cycle")["T0"].std().fillna(0.0)
    t0_sanity = {
        "nonzero_frac": round(float((t0v > 0).mean()), 4),
        "mean": round(float(t0v.mean()), 4),
        "median": round(float(np.median(t0v)), 4),
        "max": round(float(t0v.max()), 4),
        "cycles_with_within_variation": int((t0_within > 1e-9).sum()),
        "n_cycles_total": int(df["Cycle"].nunique()),
        "identity": args.identity,
    }

    features_hist = base.FEATURES_FULL
    features_t0 = base.FEATURES_FULL + ["T0"]
    assert set(features_t0) - set(features_hist) == {"T0"}, "arms differ by !=1 feature"

    # --- per-cycle fault size m and cycle size n ---
    cyc_stats = df.groupby("Cycle")["Verdict"].agg(m="sum", n="count")
    cycles_sorted = np.sort(df["Cycle"].unique())

    # --- prequential evaluation (expanding by default; sliding-window + subsample opt-in) ---
    scorable = [int(c) for c in cycles_sorted
                if int(cyc_stats.loc[c, "n"]) >= 2 and int(cyc_stats.loc[c, "m"]) >= 1]
    eval_set = set(select_eval_cycles(scorable, args.max_eval_cycles))
    per_cycle, untrainable, unscorable, subsampled_out = [], [], 0, 0
    for c in cycles_sorted:
        g = df[df["Cycle"] == c]
        m, n = int(cyc_stats.loc[c, "m"]), int(cyc_stats.loc[c, "n"])
        if n < 2 or m == 0:
            unscorable += 1
            continue
        if int(c) not in eval_set:          # scorable but not in the subsample
            subsampled_out += 1
            continue
        train = training_rows(df, c, args.train_window_cycles)
        if train["Verdict"].nunique() < 2 or len(train) < MIN_TRAIN_ROWS:
            untrainable.append(int(c))
            continue
        s_hist = fit_predict(train, g, features_hist)
        s_t0 = fit_predict(train, g, features_t0)
        v = g["Verdict"].to_numpy(int)
        ties = np.random.default_rng(int(c)).random(len(g))  # fixed per-cycle, shared
        # model-free reference rankers (same fixed ties) to explain the model result
        apfd_t0_alone = apfd_with_fixed_ties(v, g["T0"].to_numpy(float), ties)
        apfd_opt = base.apfd_from_order(sorted(v.tolist(), reverse=True))
        rperm = np.random.default_rng(int(c) + 1)
        apfd_rand = float(np.mean([base.apfd_from_order(v[rperm.permutation(len(v))])
                                   for _ in range(50)]))
        fail = g[g["Verdict"] == 1]
        per_cycle.append({
            "cycle": int(c), "m": m, "n": n,
            "t0_within_std": round(float(g["T0"].std(ddof=0)), 4),
            "apfd_hist": apfd_with_fixed_ties(v, s_hist, ties),
            "apfd_t0": apfd_with_fixed_ties(v, s_t0, ties),
            "apfd_t0_alone": apfd_t0_alone,
            "apfd_random": round(apfd_rand, 4),
            "apfd_optimal": apfd_opt,
            # fraction of this cycle's failures that already failed last run (E1=1):
            # a high value => history alone can rank them, leaving T0 no headroom
            "frac_fail_recurring_E1": round(float((fail["E1"] == 1).mean()), 4),
        })

    if not per_cycle:
        raise SystemExit("no scorable+trainable cycles -- degenerate run.")

    # --- strata (thresholds from CLI; see stratify) ---
    sfm, cmin = args.small_fault_max, args.chronic_min
    small, chronic, small_tiny, small_large = stratify(
        per_cycle, sfm, cmin, TINY_CYCLE_MAX)

    report = {
        "dataset": os.path.abspath(args.dataset),
        "name_map": os.path.abspath(args.name_map),
        "model": ("GradientBoostingClassifier, target=Verdict, prequential "
                  "expanding-window (train on all cycles < c, test cycle c)"),
        "arms": {"hist": features_hist, "hist_plus_t0": features_t0,
                 "delta": "T0 (exactly one feature added)"},
        "t0_sanity": t0_sanity,
        "eval": {
            "n_cycles_total": int(len(cycles_sorted)),
            "n_scorable_total": len(scorable),
            "n_unscorable_no_fail_or_singleton": unscorable,
            "n_subsampled_out": subsampled_out,
            "n_untrainable_prefix": len(untrainable),
            "untrainable_cycles": untrainable,
            "n_scored": len(per_cycle),
            "train_window_cycles": (args.train_window_cycles
                                    if args.train_window_cycles > 0 else "expanding"),
            "max_eval_cycles": (args.max_eval_cycles if args.max_eval_cycles > 0 else "all"),
            "small_fault_definition": f"m <= {sfm}",
            "chronic_definition": f"m >= {cmin}",
        },
        "PRIMARY_small_fault": compare_stratum(f"small_fault (m<={sfm})", small, rng),
        "small_fault_tiny_cycles (n<=5)": compare_stratum("small_fault_tiny", small_tiny, rng),
        "small_fault_large_cycles (n>5)": compare_stratum("small_fault_large", small_large, rng),
        "SECONDARY_chronic": compare_stratum(f"chronic (m>={cmin})", chronic, rng),
        "SECONDARY_all_scored": compare_stratum("all_scored", per_cycle, rng),
        "diagnostics_why": {
            "small_fault": diagnostics(small),
            "small_fault_tiny (n<=5)": diagnostics(small_tiny),
            "small_fault_large (n>5)": diagnostics(small_large),
            "chronic": diagnostics(chronic),
            "reading": ("apfd_t0_alone > apfd_random => T0 carries some ordering signal; "
                        "apfd_hist_model ~ apfd_optimal with frac_fail_recurring_E1 ~ 1 "
                        "=> history already ranks the (recurring) faults at the top, so "
                        "T0 has no headroom to add."),
        },
        "per_cycle": per_cycle,
    }
    with open(os.path.join(out, "step3_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # --- console summary ---
    print("== Step 3/4: T0 path-token relevance -- prequential, paired ==")
    print(f"identity={args.identity}  T0 nonzero {t0_sanity['nonzero_frac']:.1%}  "
          f"within-cycle variation in {t0_sanity['cycles_with_within_variation']}"
          f"/{t0_sanity['n_cycles_total']} cycles")
    print(f"scored cycles {len(per_cycle)}  (unscorable {unscorable}, "
          f"untrainable-prefix {len(untrainable)})")
    for key in ("PRIMARY_small_fault", "small_fault_tiny_cycles (n<=5)",
                "small_fault_large_cycles (n>5)", "SECONDARY_chronic",
                "SECONDARY_all_scored"):
        b = report[key]
        if b.get("n_cycles", 0) == 0:
            print(f"\n[{key}] no cycles"); continue
        h, t = b["apfd_hist"], b["apfd_hist_plus_t0"]
        print(f"\n[{key}]  n={b['n_cycles']}")
        print(f"  APFD  HIST   {h['mean']:.4f} (median {h['median']})")
        print(f"        HIST+T0{t['mean']:.4f} (median {t['median']})")
        print(f"  mean paired diff {b['mean_paired_diff']:+.4f}  "
              f"boot95 {b['bootstrap95_mean_diff']}  "
              f"Wilcoxon p {b['wilcoxon_p_two_sided']}  "
              f"A12 {b['vargha_a12_t0_over_hist']}")
        print(f"  win/tie/loss {b['win_tie_loss']}")
        if b.get("note"):
            print(f"  note: {b['note']}")
    print(f"\nwrote: {os.path.join(out, 'step3_report.json')}")
    print(f"\nPRIMARY claim = small_fault (m<={sfm}). "
          f"Chronic (m>={cmin}) reported separately.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
