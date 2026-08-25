#!/usr/bin/env python3
"""
Step 1 (airavata) -- real Name join + BLOCKING name-integrity / path-overlap gate.

Runs on the LOCAL slice, CSV-only. The git repo is NOT needed for this step:
changed files per cycle are derived from entity_change_history.csv, not `git show`.

Why this exists
---------------
The Zenodo tar has no rtp-torrent, so FINAL6/TCP-CI_schema.py's positional name
map never fires and its fallback emits useless `test_<id>`. The REAL join is via
`id_map.csv` (path,id): reverse it (value->key) and map `exe.csv.test` /
`dataset.csv.Test` -> real repo-relative test path -> FQN. The change signal per
cycle comes from `entity_change_history.csv` (Commit->EntityId) + `builds.csv`
(build->commits), mapped back through id_map -- so the whole Step-1 gate is
computable from CSVs alone.

What it produces (under --out, default = --data)
  test_name_map.csv       test_id, path, fqn, is_test_class
  step1_gate_report.json  the two gate metrics + samples
and prints a PASS/FAIL summary.

Gate (docs/NEXT-STEPS.md Step 1), no broad try/except -- a degenerate run FAILS:
  exit 0  PASS: all test ids resolve to real paths AND test<->diff overlap is non-trivial
  exit 3  FAIL: some test ids do not resolve via id_map (name join broken)
  exit 4  FAIL: near-zero test<->diff path overlap (mapping/derivation broken -> STOP)

Usage
  python pipeline/step1_name_join.py \
      --data tcpci_slice/TCP-CI-dataset/datasets/apache@airavata
"""
import argparse
import json
import os
import re
import sys

import pandas as pd

# Structural/package tokens that would make everything overlap everything;
# dropped before comparing test paths to changed-file paths. (These are path
# scaffolding and the shared org prefix -- NOT meaningful English words like
# "generic" or "factory", which are kept.)
STOP_TOKENS = {
    "src", "test", "tests", "main", "java", "scala", "resources", "target",
    "org", "apache", "airavata", "com", "net", "io",
}
TEST_SUFFIXES = ("test.java", "tests.java", "testcase.java", "it.java")
# markers that separate the build-path prefix from the package-qualified name
PKG_MARKERS = ("src/test/java/", "src/test/scala/", "src/it/java/",
               "src/main/java/", "src/main/scala/", "src/test/", "src/main/")


def tokenize(path):
    """Path -> set of meaningful lowercase tokens (camelCase split, stopwords out)."""
    if path.lower().endswith(".java"):
        path = path[:-5]
    toks = set()
    for seg in re.split(r"[/._]", path):
        seg = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", seg)  # camelCase -> spaces
        for w in seg.split():
            w = w.lower()
            if len(w) >= 2:
                toks.add(w)
    return toks - STOP_TOKENS


def path_to_fqn(path):
    p = path.replace("\\", "/")
    rel = None
    for marker in PKG_MARKERS:
        i = p.find(marker)
        if i != -1:
            rel = p[i + len(marker):]
            break
    if rel is None:
        rel = p.rsplit("/", 1)[-1]
    if rel.endswith(".java"):
        rel = rel[:-5]
    return rel.replace("/", ".")


def is_test_class(path):
    return path.lower().endswith(TEST_SUFFIXES)


def find_col(df, *names):
    low = {c.lower(): c for c in df.columns}
    for n in names:
        if n in low:
            return low[n]
    raise SystemExit(f"expected one of {names} in columns {list(df.columns)}")


def load_reverse_idmap(id_map_csv):
    """id_map.csv is (key=path, value=id). Return {id: [paths]} (ids can repeat
    across renamed/moved files -- README notes this)."""
    df = pd.read_csv(id_map_csv)
    kcol = find_col(df, "key")
    vcol = find_col(df, "value")
    rev = {}
    for path, eid in zip(df[kcol], df[vcol]):
        rev.setdefault(int(eid), []).append(str(path))
    return rev


def pick_test_path(paths):
    for p in paths:                      # prefer an actual test class
        if is_test_class(p):
            return p
    for p in paths:                      # else anything under src/test/
        if "src/test/" in p.replace("\\", "/"):
            return p
    return paths[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True,
                    help="path to datasets/<slug> dir (has exe.csv, id_map.csv, "
                         "builds.csv, entity_change_history.csv)")
    ap.add_argument("--out", default=None, help="output dir (default: --data)")
    ap.add_argument("--min-overlap-frac", type=float, default=0.05,
                    help="gate floor for fraction of cycles with any overlap")
    args = ap.parse_args()
    data, out = args.data, (args.out or args.data)
    os.makedirs(out, exist_ok=True)

    exe = pd.read_csv(os.path.join(data, "exe.csv"))
    builds = pd.read_csv(os.path.join(data, "builds.csv"))
    rev = load_reverse_idmap(os.path.join(data, "id_map.csv"))
    ech = pd.read_csv(os.path.join(data, "entity_change_history.csv"))

    # --- A. name join: exe.test -> real path -> FQN ---
    test_ids = sorted(int(t) for t in exe["test"].unique())
    rows, unresolved = [], []
    for tid in test_ids:
        paths = rev.get(tid)
        if not paths:
            unresolved.append(tid)
            rows.append({"test_id": tid, "path": "", "fqn": f"test_{tid}",
                         "is_test_class": False})
            continue
        p = pick_test_path(paths)
        rows.append({"test_id": tid, "path": p, "fqn": path_to_fqn(p),
                     "is_test_class": is_test_class(p)})
    name_map = pd.DataFrame(rows)
    name_map.to_csv(os.path.join(out, "test_name_map.csv"), index=False)
    n = len(test_ids)
    n_unres = len(unresolved)
    n_testcls = int(name_map["is_test_class"].sum())

    # --- B. per-build changed paths from entity_change_history + builds ---
    commit_col = find_col(ech, "commit")
    entity_col = find_col(ech, "entityid", "entity_id")
    changed_by_commit = {}
    for commit, eid in zip(ech[commit_col], ech[entity_col]):
        changed_by_commit.setdefault(str(commit), set()).add(int(eid))

    bid_col = find_col(builds, "id")
    commits_col = find_col(builds, "commits")
    build_commits = dict(zip(builds[bid_col], builds[commits_col]))

    def build_changed_paths(commits_field):
        paths = set()
        if pd.isna(commits_field):
            return paths
        for h in str(commits_field).split("#"):
            h = h.strip()
            for eid in changed_by_commit.get(h, ()):
                paths.update(rev.get(eid, ()))
        return paths

    # --- C. path-overlap gate ---
    tid_tokens = {r["test_id"]: tokenize(r["path"])
                  for _, r in name_map.iterrows() if r["path"]}
    cycles_eval = cycles_overlap = 0
    fail_execs = fail_execs_overlap = 0
    for bid, grp in exe.groupby("build"):
        changed = build_changed_paths(build_commits.get(bid))
        if not changed:
            continue
        changed_tokens = set().union(*(tokenize(p) for p in changed))
        if not changed_tokens:
            continue
        cycles_eval += 1
        any_overlap = False
        for _, e in grp.iterrows():
            ov = bool(tid_tokens.get(int(e["test"]), set()) & changed_tokens)
            any_overlap = any_overlap or ov
            if int(e["verdict"]) != 0:
                fail_execs += 1
                fail_execs_overlap += int(ov)
        cycles_overlap += int(any_overlap)

    frac_cycles = cycles_overlap / cycles_eval if cycles_eval else 0.0
    frac_fail = fail_execs_overlap / fail_execs if fail_execs else 0.0

    report = {
        "data": os.path.abspath(data),
        "n_tests": n, "n_unresolved": n_unres, "unresolved_ids": unresolved,
        "n_test_class_paths": n_testcls,
        "n_builds_exe": int(exe["build"].nunique()),
        "cycles_evaluated": cycles_eval, "cycles_with_overlap": cycles_overlap,
        "frac_cycles_with_overlap": round(frac_cycles, 4),
        "failing_execs": fail_execs, "failing_execs_with_overlap": fail_execs_overlap,
        "frac_failing_execs_with_overlap": round(frac_fail, 4),
        "sample_names": name_map.head(12).to_dict("records"),
    }
    with open(os.path.join(out, "step1_gate_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("== Step 1: name join + gate ==")
    print(f"tests: {n}   unresolved: {n_unres}   test-class paths: {n_testcls}/{n}")
    for r in rows[:8]:
        print(f"  {r['test_id']:>6} -> {r['fqn']}")
    print(f"cycles evaluated (changed files & tests present): {cycles_eval}")
    print(f"cycles with >=1 test<->diff overlap: {cycles_overlap} ({frac_cycles:.1%})")
    print(f"failing execs with overlap: {fail_execs_overlap}/{fail_execs} ({frac_fail:.1%})")
    print(f"wrote: {os.path.join(out, 'test_name_map.csv')} , step1_gate_report.json")

    rc = 0
    if n_unres > 0:
        print(f"\nFAIL: {n_unres} test ids did not resolve via id_map -> name join broken.")
        rc = 3
    elif n_testcls < 0.5 * n:
        print(f"\nWARN: only {n_testcls}/{n} resolved paths look like test classes -- "
              f"inspect test_name_map.csv before trusting names.")
    if cycles_eval == 0:
        print("\nFAIL: no cycles had derivable changed files -- cannot run the gate.")
        rc = rc or 4
    elif frac_cycles < args.min_overlap_frac:
        print(f"\nFAIL: near-zero test<->diff overlap ({frac_cycles:.1%} < "
              f"{args.min_overlap_frac:.0%}) -- mapping or path derivation is broken. "
              f"STOP (NEXT-STEPS Step 1).")
        rc = rc or 4
    if rc == 0:
        print("\nPASS: names resolve and test<->diff overlap is non-trivial. "
              "Proceed to Step 2 (history-only per-cycle APFD baseline).")
    return rc


if __name__ == "__main__":
    sys.exit(main())
