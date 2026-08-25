#!/usr/bin/env python3
"""
Step 2 (airavata) -- honest history-only per-cycle APFD baseline.

This is the number T0 (Step 3) must beat. It trains a purely history-only model
(NO change/relevance signal -- CommitMsg/FilesChanged are deliberately unused) and
reports **per-cycle APFD** as the primary metric, with global/pooled APFD reported
separately (the "old global number" NEXT-STEPS warns against reading as the result).

Relationship to the original DeepOrder pipeline
-----------------------------------------------
FINAL6/OriginalDeepOrder-featureEngineering.py + FINAL6/*/DeepOrder_on_google_Dataset.py
define the reference features `Duration, E1, E2, E3, LastRunFeature, DIST,
CHANGE_IN_STATUS`. We keep that VOCABULARY for comparability but make three
deliberate departures, each required for a valid T0 experiment:

  1. TARGET = Verdict (did the test actually fail), NOT DeepOrder's PRIORITY_VALUE.
     PRIORITY_VALUE is a formula of history alone (0.7*E1+0.2*E2+0.1*E3 + speed), so
     a model trained to reproduce it CANNOT benefit from a change-relevance feature --
     the target doesn't depend on the change. Whether a test truly fails DOES depend
     on whether the commit touched it, so Verdict is what makes T0 testable at all.
  2. SPLIT = temporal by cycle (train on past, test on future). DeepOrder's random
     80/20 split lets future cycles inform the ranking of past ones -- invalid for TCP.
  3. No global feature normalization. We use gradient-boosted trees (scale-invariant),
     which also sidesteps the train+test global min/max leak in the legacy feature step.
     `LastRunFeature` here is the REAL days-since-last-run from BuildStartedAt - LastRun
     (airavata has real timestamps; the legacy traccar path fabricated dates).

Two baselines are reported from ONE run so you can show your setup matches the paper's
feature set before adding T0:
  * "deeporder_exact" : features Duration,E1,E2,E3,LastRunFeature,DIST,CHANGE_IN_STATUS
                        with DeepOrder's window-3 DIST/CHANGE definitions.
  * "full"            : the above but DIST/CHANGE computed over the FULL history prefix,
                        plus PRIOR_FAIL_RATE and N_HIST (a stronger, harder-to-beat
                        baseline -- the primary number for T0 to beat).

APFD uses failing tests as faults (standard TCP-CI/DeepOrder proxy):
    APFD = 1 - (sum of 1-indexed ranks of failing tests)/(n*m) + 1/(2n)
computed independently within each evaluation cycle. Cycles need >=2 tests and >=1
failure to be scorable; unscorable cycles are reported, never silently averaged in.
No broad try/except: a degenerate run raises. A swallowed failure is not a datum.

Outputs (under --out, default = dataset's dir)
  step2_report.json   metrics + per-cycle APFD for both baselines + reference orderings
and prints a summary. Exit 0 on a clean run.

Usage
  python pipeline/step2_baseline.py \
      --dataset FINAL6/apache@airavata/apache@airavata_enhanced_tcp_dataset.csv
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier

RANDOM_STATE = 42


# --------------------------------------------------------------------------- #
# Causal history features from LastResults (most-recent-first list of 0/1).
# --------------------------------------------------------------------------- #
def parse_last_results(s):
    """'[1,0,1]' (most-recent-first) -> list[int]. Empty/[] -> []."""
    if not isinstance(s, str):
        return []
    return [int(c) for c in s if c in "01"]


def dist_window3(e1, e2, e3):
    """DeepOrder's distance-to-last-failure over the 3-run window (verbatim):
    scan [E3,E2,E1] oldest->newest, return 1-indexed position of first failure, else 0."""
    for i, r in enumerate((e3, e2, e1)):
        if r == 1:
            return i + 1
    return 0


def change_window3(e1, e2, e3):
    """DeepOrder's change-in-status over the 3-run window: pass<->fail flips in [E1,E2,E3]."""
    seq = (e1, e2, e3)
    return sum(1 for i in range(2) if seq[i] != seq[i + 1])


def history_features(results):
    """results = most-recent-first 0/1 verdicts strictly BEFORE this execution.
    1 = fail, 0 = pass (schema gen folded verdict 2 -> 1; LastResults mirrors that)."""
    n = len(results)
    e1 = results[0] if n >= 1 else 0
    e2 = results[1] if n >= 2 else 0
    e3 = results[2] if n >= 3 else 0
    # full-prefix distance to most recent failure (1 = failed last run; 0 = none in prefix)
    dist_full = 0
    for i, r in enumerate(results):
        if r == 1:
            dist_full = i + 1
            break
    change_full = sum(1 for i in range(n - 1) if results[i] != results[i + 1])
    fail_rate = (sum(results) / n) if n else 0.0
    return {
        "E1": e1, "E2": e2, "E3": e3,
        "DIST": dist_full, "CHANGE_IN_STATUS": change_full,   # full-prefix (stronger)
        "DIST_W3": dist_window3(e1, e2, e3),                  # DeepOrder-exact
        "CHANGE_W3": change_window3(e1, e2, e3),              # DeepOrder-exact
        "PRIOR_FAIL_RATE": fail_rate, "N_HIST": n,
    }


# Feature sets share DeepOrder's vocabulary; "full" adds the broader history signals.
FEATURES_DEEPORDER = ["Duration", "E1", "E2", "E3", "LastRunFeature",
                      "DIST_W3", "CHANGE_W3"]
FEATURES_FULL = ["Duration", "E1", "E2", "E3", "LastRunFeature",
                 "DIST", "CHANGE_IN_STATUS", "PRIOR_FAIL_RATE", "N_HIST"]


# --------------------------------------------------------------------------- #
# APFD (failing tests as faults), evaluated per cycle.
# --------------------------------------------------------------------------- #
def apfd_from_order(verdicts_in_order):
    """verdicts_in_order: 0/1 in PRIORITIZED order (rank 1 first).
    APFD = 1 - (sum of ranks of failing tests)/(n*m) + 1/(2n). None if unscorable."""
    v = list(verdicts_in_order)
    n = len(v)
    fail_ranks = [i + 1 for i, x in enumerate(v) if x == 1]
    m = len(fail_ranks)
    if n < 2 or m == 0:
        return None
    return 1.0 - (sum(fail_ranks) / (n * m)) + (1.0 / (2 * n))


def order_by_score(group, score, rng, descending=True):
    """Verdicts ordered by `score`. Ties broken RANDOMLY so constant/steppy model
    scores cannot inherit a spurious APFD from stable input order."""
    tie = rng.random(len(group))
    key = np.asarray(score, dtype=float)
    sign = -1.0 if descending else 1.0
    order = np.lexsort((tie, sign * key))
    return group["Verdict"].to_numpy()[order]


def per_cycle_apfd(df, score, rng):
    """Returns (list_of_apfd, n_scorable, n_unscorable)."""
    s = pd.Series(np.asarray(score, dtype=float), index=df.index)
    vals, unscorable = [], 0
    for _, g in df.groupby("Cycle", sort=True):
        a = apfd_from_order(order_by_score(g, s.loc[g.index], rng, descending=True))
        if a is None:
            unscorable += 1
        else:
            vals.append(a)
    return vals, len(vals), unscorable


def optimal_apfd(df):
    vals = []
    for _, g in df.groupby("Cycle", sort=True):
        a = apfd_from_order(sorted(g["Verdict"].tolist(), reverse=True))
        if a is not None:
            vals.append(a)
    return vals


def random_apfd(df, rng, repeats=20):
    per_cycle = {}
    for _ in range(repeats):
        for cyc, g in df.groupby("Cycle", sort=True):
            v = g["Verdict"].to_numpy()
            a = apfd_from_order(v[rng.permutation(len(v))])
            if a is not None:
                per_cycle.setdefault(cyc, []).append(a)
    return [float(np.mean(v)) for v in per_cycle.values()]


def summ(vals):
    if not vals:
        return {"n": 0, "mean": None, "median": None, "std": None,
                "p25": None, "p75": None}
    a = np.asarray(vals, dtype=float)
    return {"n": int(a.size), "mean": round(float(a.mean()), 4),
            "median": round(float(np.median(a)), 4), "std": round(float(a.std(ddof=0)), 4),
            "p25": round(float(np.percentile(a, 25)), 4),
            "p75": round(float(np.percentile(a, 75)), 4)}


def fit_score(train, test, feats):
    """Fit a history-only GB classifier on `feats`, return P(fail) for test rows."""
    clf = GradientBoostingClassifier(random_state=RANDOM_STATE)
    clf.fit(train[feats].to_numpy(float), train["Verdict"].to_numpy(int))
    return clf.predict_proba(test[feats].to_numpy(float))[:, 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True,
                    help="path to *_enhanced_tcp_dataset.csv from TCP-CI_schema.py")
    ap.add_argument("--out", default=None, help="output dir (default: dataset's dir)")
    ap.add_argument("--train-frac", type=float, default=0.7,
                    help="fraction of (temporally sorted) cycles used for training")
    args = ap.parse_args()

    out = args.out or os.path.dirname(os.path.abspath(args.dataset))
    os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(RANDOM_STATE)

    df = pd.read_csv(args.dataset)
    need = {"Cycle", "Verdict", "LastResults", "Duration", "BuildStartedAt", "LastRun"}
    missing = need - set(df.columns)
    if missing:
        raise SystemExit(f"dataset missing required columns: {sorted(missing)}")

    df["Verdict"] = df["Verdict"].astype(int)
    if not set(df["Verdict"].unique()) <= {0, 1}:
        raise SystemExit(f"Verdict not binary: {sorted(df['Verdict'].unique())}")

    # --- causal history features ---
    feats = df["LastResults"].apply(lambda s: history_features(parse_last_results(s)))
    df = pd.concat([df, pd.DataFrame(list(feats), index=df.index)], axis=1)
    df["Duration"] = pd.to_numeric(df["Duration"], errors="coerce").fillna(0.0)

    # --- REAL recency: days between this build and the test's previous run ---
    # Both timestamps are known before the tests run -> causal, no leakage. Kept raw
    # (trees are scale-invariant; DeepOrder's 0-5 global normalization would leak).
    bs = pd.to_datetime(df["BuildStartedAt"], errors="coerce", utc=True)
    lr = pd.to_datetime(df["LastRun"], errors="coerce", utc=True)
    gap = (bs - lr).dt.total_seconds() / 86400.0
    n_bad = int(gap.isna().sum())
    n_neg = int((gap < 0).sum())
    df["LastRunFeature"] = gap.fillna(0.0).clip(lower=0.0)

    # --- temporal split by cycle ---
    cycles = np.sort(df["Cycle"].unique())
    cut = int(len(cycles) * args.train_frac)
    if cut < 1 or cut >= len(cycles):
        raise SystemExit(f"bad split: {len(cycles)} cycles, train cut at {cut}")
    train = df[df["Cycle"].isin(set(cycles[:cut].tolist()))].copy()
    test = df[df["Cycle"].isin(set(cycles[cut:].tolist()))].copy()
    if train["Verdict"].nunique() < 2:
        raise SystemExit("training split has a single Verdict class -- cannot fit.")

    # --- fit both history-only baselines (same target, same split) ---
    score_full = fit_score(train, test, FEATURES_FULL)
    score_do = fit_score(train, test, FEATURES_DEEPORDER)

    apfd_full, n_scor, n_unscor = per_cycle_apfd(test, score_full, rng)
    apfd_do, _, _ = per_cycle_apfd(test, score_do, rng)
    apfd_heur, _, _ = per_cycle_apfd(test, test["PRIOR_FAIL_RATE"].to_numpy(float), rng)
    apfd_rand = random_apfd(test, rng)
    apfd_opt = optimal_apfd(test)

    pooled = test.assign(_s=score_full).sort_values("_s", ascending=False, kind="mergesort")
    global_full = apfd_from_order(pooled["Verdict"].tolist())

    report = {
        "dataset": os.path.abspath(args.dataset),
        "model": "GradientBoostingClassifier(history-only), target=Verdict, split=temporal",
        "features_full": FEATURES_FULL,
        "features_deeporder_exact": FEATURES_DEEPORDER,
        "lastrunfeature": {"source": "BuildStartedAt - LastRun (days, raw)",
                           "n_unparseable": n_bad, "n_negative_clipped": n_neg},
        "n_rows": int(len(df)), "n_cycles_total": int(len(cycles)),
        "train_frac": args.train_frac,
        "train_cycles": [int(cycles[0]), int(cycles[cut - 1])],
        "test_cycles": [int(cycles[cut]), int(cycles[-1])],
        "n_train_rows": int(len(train)), "n_test_rows": int(len(test)),
        "test_fail_rate": round(float(test["Verdict"].mean()), 4),
        "per_cycle_apfd": {
            "full_model": summ(apfd_full),
            "deeporder_exact_model": summ(apfd_do),
            "heuristic_prior_fail_rate": summ(apfd_heur),
            "random": summ(apfd_rand),
            "optimal": summ(apfd_opt),
        },
        "cycles_scorable": n_scor,
        "cycles_unscorable_no_fail_or_singleton": n_unscor,
        "global_pooled_apfd_full_model": (round(global_full, 4)
                                          if global_full is not None else None),
        "full_model_apfd_values": [round(x, 4) for x in apfd_full],
    }
    with open(os.path.join(out, "step2_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    m = report["per_cycle_apfd"]
    print("== Step 2: history-only per-cycle APFD baseline (target=Verdict, temporal) ==")
    print(f"rows {len(df)}  cycles {len(cycles)}  "
          f"train cycles {report['train_cycles']}  test cycles {report['test_cycles']}")
    print(f"test rows {len(test)}  test fail-rate {report['test_fail_rate']:.1%}  "
          f"scorable cycles {n_scor} (unscorable {n_unscor})")
    print(f"LastRunFeature: real days since last run "
          f"(unparseable {n_bad}, neg-clipped {n_neg})")
    print("\nper-cycle APFD (mean +/- std, median):")
    for name in ("full_model", "deeporder_exact_model", "heuristic_prior_fail_rate",
                 "random", "optimal"):
        s = m[name]
        if s["n"]:
            print(f"  {name:26s} {s['mean']:.4f} +/- {s['std']:.4f}   "
                  f"median {s['median']:.4f}  (n={s['n']})")
    print(f"\nglobal/pooled APFD (full model, secondary): "
          f"{report['global_pooled_apfd_full_model']}")
    print(f"\nwrote: {os.path.join(out, 'step2_report.json')}")
    print("\nPRIMARY BASELINE = per-cycle APFD 'full_model'. "
          "'deeporder_exact_model' is the paper-feature cross-check. "
          "T0 (Step 3) must beat the primary on a paired per-cycle test.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
