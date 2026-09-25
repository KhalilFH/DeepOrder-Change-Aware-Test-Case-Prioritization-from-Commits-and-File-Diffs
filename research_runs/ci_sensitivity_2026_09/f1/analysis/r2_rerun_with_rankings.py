"""F1 R2: re-run pipeline/step3_t0.py exactly as at 25eb6b7 and record the per-test
rankings it scores, without changing its code.

The unchanged step3_t0.main() runs as-is. The only intervention is observational:
its module-level `apfd_with_fixed_ties` is wrapped so that each call's ordering
(the same np.lexsort the original computes) is written out together with the
cycle, the arm and the test names, and the original function's return value is
passed through unchanged. The arm is identified by object identity against the
caller's `s_hist` / `s_t0` locals; the model-free `apfd_t0_alone` call is recorded
as arm "t0_alone" and not used by F1.

    python r2_rerun_with_rankings.py <code_dir> <rankings_out.csv> -- <step3_t0 args...>

<code_dir> holds pipeline/step3_t0.py, step2_baseline.py and relevance_t0.py
exported verbatim from 25eb6b7.
"""
import csv
import os
import sys


def main():
    code_dir, rankings_out = sys.argv[1], sys.argv[2]
    step3_args = sys.argv[sys.argv.index("--") + 1:]
    sys.path.insert(0, os.path.join(code_dir, "pipeline"))
    import numpy as np
    import step3_t0

    original = step3_t0.apfd_with_fixed_ties
    rows = []

    def recording(verdicts, scores, ties):
        result = original(verdicts, scores, ties)
        caller = sys._getframe(1).f_locals
        if scores is caller.get("s_hist"):
            arm = "hist"
        elif scores is caller.get("s_t0"):
            arm = "t0"
        else:
            arm = "t0_alone"
        g = caller["g"]
        order = np.lexsort((ties, -np.asarray(scores, dtype=float)))  # identical to original
        names = g["Name"].to_numpy()
        v = np.asarray(verdicts)
        s = np.asarray(scores, dtype=float)
        for rank, idx in enumerate(order, start=1):
            rows.append({"cycle": int(caller["c"]), "arm": arm, "rank": rank,
                         "name": str(names[idx]), "verdict": int(v[idx]),
                         "score": repr(float(s[idx])), "tie": repr(float(ties[idx])),
                         "cycle_apfd": repr(float(result))})
        return result

    step3_t0.apfd_with_fixed_ties = recording
    sys.argv = ["step3_t0.py"] + step3_args
    step3_t0.main()

    with open(rankings_out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"recorded {len(rows)} ranked rows -> {rankings_out}")


if __name__ == "__main__":
    main()
