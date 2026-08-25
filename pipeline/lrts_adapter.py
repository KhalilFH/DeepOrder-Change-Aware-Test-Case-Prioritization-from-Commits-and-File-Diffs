#!/usr/bin/env python3
"""
LRTS -> enhanced_tcp_dataset.csv adapter.

Turns one LRTS project's in-memory tables into a CSV byte-compatible with what
pipeline/step2_baseline.py and pipeline/step3_t0.py already consume, plus the
test_name_map.csv that `step3 --name-map` needs -- so step2/step3 run UNCHANGED
on LRTS exactly as they do on airavata. Spec: docs/research/lrts-adapter-spec.md.

The tested core is pure (no git/filesystem): changed files per cycle are INJECTED
(the git-diff reconstruction is a thin adapter at the edge). See CONTEXT.md for the
domain vocabulary (Cycle, Verdict, LastResults, FilesChanged, Test Name).
"""
from __future__ import annotations

import argparse
import glob
import json
import numbers
import os
import re
import subprocess
import sys

import pandas as pd


def _sha_or_blank(v) -> str:
    return "" if (v is None or (isinstance(v, float) and pd.isna(v))) else str(v)


def _ts_to_iso(v) -> str:
    """LRTS build_timestamp -> ISO-8601 UTC. dataset.csv stores epoch SECONDS (float);
    fall back to plain parsing for any ISO-string form."""
    if isinstance(v, numbers.Number) and not isinstance(v, bool):
        return pd.to_datetime(float(v), unit="s", utc=True).isoformat()
    t = pd.to_datetime(v, utc=True, errors="coerce")
    if pd.isna(t):
        raise ValueError(f"unparseable build_timestamp {v!r}")
    return t.isoformat()


def load_lrts_project(builds_csv: str, results_root: str, project: str,
                      *, results_file: str = "test_class.csv.zip") -> tuple:
    """Read one LRTS project's on-disk tree -> (executions_df, build_timestamps, build_shas).

    Layout (confirmed against the processed ~2.8 GB download, 2026-08-25):
      builds_csv   = dataset.csv: project, pr_name, build_id, stage_id, build_timestamp
                     (epoch seconds), trunk_sha, build_head_sha, ...
      per cycle:   {results_root}/{project}/{pr_name}_build{build_id}/stage_{stage_id}/
                   {results_file}  (a zipped CSV: testclass [FQN], duration, outcome [0/1],
                   last_outcome)

    Missing per-cycle results file raises (a build listed but not present is a data
    failure, not something to skip silently).
    """
    bdf = pd.read_csv(builds_csv)
    bdf = bdf[bdf["project"] == project]
    if bdf.empty:
        raise ValueError(f"no builds for project {project!r} in {builds_csv}")

    execs, build_ts, build_shas = [], {}, {}
    for row in bdf.itertuples(index=False):
        key = (row.pr_name, int(row.build_id), str(row.stage_id))
        build_ts[key] = _ts_to_iso(row.build_timestamp)
        build_shas[key] = (_sha_or_blank(row.trunk_sha), _sha_or_blank(row.build_head_sha))
        path = os.path.join(results_root, project,
                            f"{row.pr_name}_build{row.build_id}",
                            f"stage_{row.stage_id}", results_file)
        if not os.path.exists(path):
            raise FileNotFoundError(f"missing test results for cycle {key}: {path}")
        tdf = pd.read_csv(path)
        tdf = tdf.assign(pr_name=row.pr_name, build_id=int(row.build_id),
                         stage_id=str(row.stage_id))
        execs.append(tdf[["pr_name", "build_id", "stage_id", "testclass", "duration", "outcome"]])

    return pd.concat(execs, ignore_index=True), build_ts, build_shas

# Structural path tokens dropped before the overlap gate -- universal Java-layout and
# package-prefix scaffolding that would make every path "overlap" every other. Module
# and class names (which carry the real co-location signal) are deliberately kept.
_STOP_TOKENS = {"src", "test", "tests", "main", "java", "scala", "resources",
                "target", "org", "com", "net", "io"}
_TOKEN_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")


def _path_tokens(path: str) -> set:
    """Repo path -> meaningful lowercase token set (camelCase split, stopwords out)."""
    p = str(path)
    if p.lower().endswith(".java"):
        p = p[:-5]
    toks = {t.lower() for t in _TOKEN_RE.findall(p)}
    return {t for t in toks if len(t) >= 2} - _STOP_TOKENS

# LRTS test outcomes (eval_const.py). REGRESSION = was passing, now failing;
# FIXED = was failing, now passing; SKIPPED = not executed this run.
_FAIL_OUTCOMES = {"FAILED", "REGRESSION"}
_PASS_OUTCOMES = {"PASSED", "FIXED"}
_DROP_OUTCOMES = {"SKIPPED"}


def fold_verdict(outcome: str) -> int | None:
    """LRTS 5-state outcome -> binary Verdict.

    The PROCESSED LRTS `test_class.csv.zip` already stores outcome as numeric 0/1, so
    a number passes through (0/1 kept, NaN -> drop, anything else raises). The 5-state
    string form (from raw reports) is also handled: FAILED/REGRESSION -> 1,
    PASSED/FIXED -> 0, SKIPPED -> None (drop -- a skipped test was not executed). Any
    other value raises: an unrecognized outcome is a data failure, not something to
    silently pass through.
    """
    if isinstance(outcome, numbers.Number) and not isinstance(outcome, bool):
        if pd.isna(outcome):
            return None
        iv = int(outcome)
        if iv in (0, 1):
            return iv
        raise ValueError(f"numeric outcome {outcome!r} is not in {{0, 1}}")
    o = outcome.strip().upper() if isinstance(outcome, str) else outcome
    if o in _FAIL_OUTCOMES:
        return 1
    if o in _PASS_OUTCOMES:
        return 0
    if o in _DROP_OUTCOMES:
        return None
    raise ValueError(f"unknown LRTS outcome {outcome!r} "
                     f"(expected one of {sorted(_FAIL_OUTCOMES | _PASS_OUTCOMES | _DROP_OUTCOMES)})")


def assign_cycles(cycle_timestamps: dict) -> dict:
    """Map each cycle key -> a dense 0-based Cycle int, ORDERED BY build timestamp.

    step2 splits on sorted Cycle and step3 walks a prequential expanding window over
    Cycle, so the integer MUST increase with real build time. Ties on timestamp are
    broken deterministically by the key tuple so the assignment is reproducible.

    cycle_timestamps : {cycle_key -> timestamp string}. A cycle_key is whatever
    identifies one build-stage, e.g. (project, pr_name, build_id, stage_id).
    An unparseable timestamp raises (a build with no usable time can't be ordered).
    """
    items = []
    for key, ts in cycle_timestamps.items():
        t = pd.to_datetime(ts, utc=True, errors="coerce")
        if pd.isna(t):
            raise ValueError(f"cycle {key!r} has unparseable build timestamp {ts!r}")
        items.append((t, key))
    items.sort(key=lambda tk: (tk[0], tk[1]))
    return {key: i for i, (_, key) in enumerate(items)}


def derive_history(df: pd.DataFrame) -> pd.DataFrame:
    """Add causal `LastResults` and `LastRun` columns (step2's history inputs).

    For each row, walking that test's own executions in Cycle order:
      LastResults = its Verdicts from STRICTLY earlier cycles, most-recent-first,
                    serialized like ``[1, 0]`` (step2 reads only the 0/1 chars).
      LastRun     = the BuildStartedAt of that test's immediately-previous cycle,
                    or "" on first appearance (step2 coerces "" -> NaT -> gap 0).
    Neither includes the current or any future outcome -> no label leakage.

    Requires columns {Name, Cycle, Verdict, BuildStartedAt}. Raises on a duplicate
    (Name, Cycle) -- that would corrupt the causal walk (a test runs once per cycle).
    """
    need = {"Name", "Cycle", "Verdict", "BuildStartedAt"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"derive_history needs columns {sorted(missing)}")
    dup = df.duplicated(subset=["Name", "Cycle"])
    if dup.any():
        bad = df.loc[dup, ["Name", "Cycle"]].to_dict("records")[:5]
        raise ValueError(f"duplicate (Name, Cycle) rows break causal history: {bad}")

    order = df.sort_values(["Name", "Cycle"], kind="mergesort")
    hist_by_name: dict = {}       # name -> most-recent-first list[int]
    prev_run_by_name: dict = {}   # name -> previous BuildStartedAt
    lr_map, run_map = {}, {}
    for idx, name, verdict, bsa in zip(
        order.index, order["Name"], order["Verdict"], order["BuildStartedAt"]
    ):
        hist = hist_by_name.get(name, [])
        lr_map[idx] = "[" + ", ".join(str(v) for v in hist) + "]"
        run_map[idx] = prev_run_by_name.get(name, "")
        # update AFTER emitting so the current outcome is never in its own history
        hist_by_name[name] = [int(verdict)] + hist
        prev_run_by_name[name] = bsa

    out = df.copy()
    out["LastResults"] = out.index.map(lr_map)
    out["LastRun"] = out.index.map(run_map)
    return out


# markers that separate the build-path prefix from the package-qualified name
# (same convention as pipeline/step1_name_join.py).
_PKG_MARKERS = ("src/test/java/", "src/test/scala/", "src/it/java/",
                "src/main/java/", "src/main/scala/", "src/test/", "src/main/")


def path_to_fqn(path: str) -> str:
    """Repo-relative .java path -> Java FQN (drops the module/build prefix)."""
    p = str(path).replace("\\", "/")
    rel = None
    for marker in _PKG_MARKERS:
        i = p.find(marker)
        if i != -1:
            rel = p[i + len(marker):]
            break
    if rel is None:
        rel = p.rsplit("/", 1)[-1]
    if rel.endswith(".java"):
        rel = rel[:-5]
    return rel.replace("/", ".")


def resolve_identity(testclass: str, repo_index=None) -> tuple[str, str]:
    """LRTS `testclass` -> (fqn, path).

    If `testclass` is already a repo path (`.../Foo.java`), keep it as the path and
    derive the FQN -- T0 tokenizes the FULL path to see module-directory co-location
    (ADR-0004). If it is a bare dotted FQN, resolve it to a file in `repo_index`
    (the repo's list of source paths); no match or an ambiguous match raises, because
    an unresolvable test identity is a name-join failure, not a silent skip.
    """
    tc = str(testclass).replace("\\", "/")
    if "/" in tc and tc.lower().endswith(".java"):
        return path_to_fqn(tc), tc
    if repo_index is None:
        # No repo to resolve against. The processed LRTS data gives test identities as
        # FQNs only, so fall back to the FQN as its own identity -- correct for step3
        # --identity fqn (the FQN's package tokens still overlap changed-file paths;
        # pass --repo-index / a repo clone if you need true file paths for identity=path).
        return tc, tc
    matches = [p for p in repo_index if path_to_fqn(p) == tc]
    if len(matches) == 1:
        return tc, matches[0]
    if not matches:
        raise KeyError(f"no repo file resolves to FQN {testclass!r}")
    raise ValueError(f"FQN {testclass!r} is ambiguous -- {len(matches)} matching "
                     f"files: {matches[:5]}")


# --------------------------------------------------------------------------- #
# The git-diff edge (kept out of build_enhanced_dataset so the core stays pure).
# --------------------------------------------------------------------------- #
def _sha_present(repo: str, sha: str, git: str) -> bool:
    r = subprocess.run([git, "-C", repo, "cat-file", "-e", f"{sha}^{{commit}}"],
                       capture_output=True, text=True)
    return r.returncode == 0


def changed_files_from_git(repo: str, trunk_sha: str, head_sha: str,
                           *, git: str = "git") -> list[str]:
    """Repo-relative paths a PR changed, via **three-dot** ``trunk...head`` (the diff
    since the merge-base) -- matching LRTS's GitHub ``trunk...prhead`` compare, so a
    later trunk-only commit does NOT leak in.

    Returns [] when either SHA is blank or not present in the repo (a cycle with no
    usable diff data -> T0 = 0 for it, counted honestly upstream). A genuine `git diff`
    failure on two present commits raises -- that is a broken repo, not missing data.
    """
    if not trunk_sha or not head_sha:
        return []
    if not (_sha_present(repo, trunk_sha, git) and _sha_present(repo, head_sha, git)):
        return []
    r = subprocess.run(
        [git, "-C", repo, "diff", "--name-only", f"{trunk_sha}...{head_sha}"],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git diff {trunk_sha}...{head_sha} failed: {r.stderr.strip()}")
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]


def changed_files_from_compare_json(compare_dir: str) -> list[str]:
    """Changed repo-relative paths from LRTS's shipped GitHub-compare JSON(s).

    Each `{trunk}_{head}_pageN.json` in `compare_dir` is a GitHub compare response
    (base...head = three-dot) with a `files` array; we union `files[].filename` across
    pages. Missing dir / no json / no files -> [] (a cycle with no usable change data).
    This is the primary change source for the processed dataset -- no git clone needed.
    """
    files: set = set()
    for jp in sorted(glob.glob(os.path.join(compare_dir, "*.json"))):
        with open(jp, encoding="utf-8") as f:
            doc = json.load(f)
        for entry in doc.get("files", []):
            fn = entry.get("filename")
            if fn:
                files.add(fn)
    return sorted(files)


def build_changed_files_map_from_shadata(cycle_keys, shadata_root: str,
                                         project: str) -> dict:
    """{cycle_key -> [changed paths]} from shadata/<project>/compare_commits/<pr>_build<id>/.

    Change data is per (pr, build) (stage-independent), so results are cached by
    (pr, build) and broadcast to every stage of that build. Cycles with no compare
    dir map to [].
    """
    cache: dict = {}
    out: dict = {}
    for key in cycle_keys:
        pr, build, _stage = key
        pb = (pr, build)
        if pb not in cache:
            cdir = os.path.join(shadata_root, project, "compare_commits", f"{pr}_build{build}")
            cache[pb] = changed_files_from_compare_json(cdir)
        out[key] = cache[pb]
    return out


def build_changed_files_map(build_shas: dict, repo: str, *, git: str = "git") -> dict:
    """{cycle_key -> (trunk_sha, head_sha)} -> {cycle_key -> [changed paths]}.

    Caches by (trunk, head) so cycles sharing a diff cost one `git diff`. Cycles with
    no usable diff data map to []. This is the thin edge that feeds
    build_enhanced_dataset's injected `changed_files_by_cycle`.
    """
    cache: dict = {}
    out: dict = {}
    for key, (trunk, head) in build_shas.items():
        ck = (trunk, head)
        if ck not in cache:
            cache[ck] = changed_files_from_git(repo, trunk, head, git=git)
        out[key] = cache[ck]
    return out


_TEST_SUFFIXES = ("test.java", "tests.java", "testcase.java", "it.java")
_KEY_COLS = ["pr_name", "build_id", "stage_id"]
# Final column order = the step2/step3 contract (+ CommitMsg when provided).
_CONTRACT_COLS = ["Cycle", "Name", "Verdict", "Duration",
                  "LastResults", "BuildStartedAt", "LastRun", "FilesChanged"]


def build_enhanced_dataset(executions: pd.DataFrame, build_timestamps: dict,
                           changed_files_by_cycle: dict, repo_index=None,
                           commit_msgs: dict | None = None,
                           overlap_floor: float = 0.05):
    """Assemble one LRTS subject into the (dataframe, name_map) step2/step3 consume.

    executions            : rows with {pr_name, build_id, stage_id, testclass, duration, outcome}
    build_timestamps      : {(pr_name, build_id, stage_id) -> ISO timestamp}
    changed_files_by_cycle: {(pr_name, build_id, stage_id) -> [changed repo paths]} (injected)
    repo_index            : optional repo source paths, to resolve FQN testclasses to paths
    commit_msgs           : optional {(cycle key) -> message}; adds a CommitMsg column
    overlap_floor         : min fraction of cycles with test<->diff path-token overlap

    Returns (df with `_CONTRACT_COLS` [+ CommitMsg], name_map DataFrame [fqn, path,
    is_test_class]). The change-file git-diff reconstruction is deliberately NOT here --
    callers inject `changed_files_by_cycle`, keeping this core pure and testable.
    """
    df = executions.copy()

    # 1. fold outcome -> Verdict; drop SKIPPED; unknown outcome raises inside fold_verdict.
    verd = df["outcome"].map(fold_verdict)
    df = df.assign(Verdict=verd)
    df = df[df["Verdict"].notna()].copy()
    df["Verdict"] = df["Verdict"].astype(int)

    # 2. cycle key -> temporal dense Cycle int + BuildStartedAt.
    df["_key"] = list(zip(df["pr_name"], df["build_id"], df["stage_id"]))
    cyc_of = assign_cycles(build_timestamps)
    _require_keys_covered(set(df["_key"]), set(cyc_of), "build_timestamps")
    df["Cycle"] = df["_key"].map(cyc_of).astype(int)
    df["BuildStartedAt"] = df["_key"].map(build_timestamps)

    # 3. test identity -> Name (FQN) + name_map (fqn -> path).
    idmap = {tc: resolve_identity(tc, repo_index) for tc in df["testclass"].unique()}
    df["Name"] = df["testclass"].map(lambda t: idmap[t][0])
    name_map = pd.DataFrame(
        [{"fqn": f, "path": p, "is_test_class": p.lower().endswith(_TEST_SUFFIXES)}
         for f, p in sorted(set(idmap.values()))]
    )

    # 4. FilesChanged: the cycle's changed set, stringified, broadcast to every row.
    _require_keys_covered(set(df["_key"]), set(changed_files_by_cycle), "changed_files_by_cycle")
    df["FilesChanged"] = df["_key"].map(lambda k: repr(list(changed_files_by_cycle[k])))

    # 5. causal history (LastResults, LastRun) + numeric Duration.
    df["Duration"] = pd.to_numeric(df["duration"], errors="coerce").fillna(0.0)
    df = derive_history(df)

    # 6. path-overlap gate: near-zero test<->diff token overlap means the identity or
    # change-file derivation is broken (T0 would be all zeros) -- stop, don't mislead.
    _check_path_overlap(df, idmap, changed_files_by_cycle, overlap_floor)

    cols = list(_CONTRACT_COLS)
    if commit_msgs is not None:
        df["CommitMsg"] = df["_key"].map(lambda k: commit_msgs.get(k, ""))
        cols.append("CommitMsg")

    return df[cols].reset_index(drop=True), name_map


def run_adapter(builds_csv: str, results_root: str, project: str, out_dir: str, *,
                shadata_root: str | None = None, repo: str | None = None,
                repo_index=None, overlap_floor: float = 0.05, git: str = "git") -> dict:
    """Full pipeline for one project: read the LRTS tree, get changed files per cycle,
    assemble the enhanced dataset, and write the three artifacts. Returns the report dict.

    Changed-file source (pick one): `shadata_root` uses LRTS's shipped GitHub-compare
    JSONs (preferred -- no clone needed); `repo` reconstructs via three-dot `git diff`
    on a clone. The CLI (`main`) is a thin wrapper over this.
    """
    execs, build_ts, build_shas = load_lrts_project(builds_csv, results_root, project)
    if shadata_root:
        changed = build_changed_files_map_from_shadata(list(build_ts), shadata_root, project)
    elif repo:
        changed = build_changed_files_map(build_shas, repo, git=git)
    else:
        raise ValueError("provide either shadata_root (compare JSONs) or repo (git clone)")
    df, name_map = build_enhanced_dataset(execs, build_ts, changed,
                                          repo_index=repo_index, overlap_floor=overlap_floor)

    os.makedirs(out_dir, exist_ok=True)
    ds_path = os.path.join(out_dir, f"lrts@{project}_enhanced_tcp_dataset.csv")
    nm_path = os.path.join(out_dir, "test_name_map.csv")
    rep_path = os.path.join(out_dir, "lrts_adapter_report.json")
    df.to_csv(ds_path, index=False)
    name_map.to_csv(nm_path, index=False)

    report = {
        "project": project,
        "n_rows": int(len(df)),
        "n_cycles": int(df["Cycle"].nunique()),
        "n_test_classes": int(df["Name"].nunique()),
        "fail_rate": round(float(df["Verdict"].mean()), 4),
        "cycles_without_diff_data": int(sum(1 for v in changed.values() if not v)),
        "dataset": os.path.abspath(ds_path),
        "name_map": os.path.abspath(nm_path),
    }
    with open(rep_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Adapt one LRTS project into an enhanced_tcp_dataset.csv that "
                    "step2_baseline.py and step3_t0.py consume unchanged.")
    ap.add_argument("--builds", required=True,
                    help="CSV of build metadata (project, pr_name, build_id, stage_id, "
                         "build_timestamp, trunk_sha, build_head_sha)")
    ap.add_argument("--results-root", required=True,
                    help="root of the per-cycle test_class.csv tree")
    ap.add_argument("--project", required=True, help="LRTS project to adapt (e.g. activemq)")
    ap.add_argument("--shadata-root", default=None,
                    help="LRTS shadata/ dir -- changed files come from its compare JSONs "
                         "(preferred; no git needed)")
    ap.add_argument("--repo", default=None,
                    help="alternative to --shadata-root: a git clone for the three-dot diff")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--repo-index", default=None,
                    help="optional newline-delimited list of repo source paths, to "
                         "resolve FQN testclasses to file paths")
    ap.add_argument("--overlap-floor", type=float, default=0.05,
                    help="min fraction of cycles with test<->diff path overlap (gate)")
    ap.add_argument("--git", default="git", help="git executable")
    args = ap.parse_args(argv)

    repo_index = None
    if args.repo_index:
        with open(args.repo_index, encoding="utf-8") as f:
            repo_index = [ln.strip() for ln in f if ln.strip()]

    report = run_adapter(args.builds, args.results_root, args.project, args.out,
                         shadata_root=args.shadata_root, repo=args.repo,
                         repo_index=repo_index, overlap_floor=args.overlap_floor,
                         git=args.git)

    print(f"== LRTS adapter: {report['project']} ==")
    print(f"rows {report['n_rows']}  cycles {report['n_cycles']}  "
          f"test classes {report['n_test_classes']}  fail-rate {report['fail_rate']:.1%}")
    print(f"cycles without diff data: {report['cycles_without_diff_data']}")
    print(f"wrote:\n  {report['dataset']}\n  {report['name_map']}")
    print("\nNext (unchanged): step2_baseline.py --dataset <above>; "
          "step3_t0.py --dataset <above> --name-map <test_name_map.csv>")
    return 0


def _require_keys_covered(used: set, provided: set, what: str) -> None:
    missing = used - provided
    if missing:
        raise ValueError(f"{len(missing)} cycle key(s) missing from {what}: "
                         f"{sorted(missing)[:5]}")


def _check_path_overlap(df: pd.DataFrame, idmap: dict, changed_files_by_cycle: dict,
                        floor: float) -> None:
    """Raise if fewer than `floor` of cycles have ANY test-path token shared with ANY
    changed-file token. Mirrors step1_name_join's blocking overlap gate."""
    n_cycles = 0
    n_overlap = 0
    for key, g in df.groupby("_key", sort=False):
        n_cycles += 1
        diff_tokens = set()
        for f in changed_files_by_cycle[key]:
            diff_tokens |= _path_tokens(f)
        hit = any(_path_tokens(idmap[tc][1]) & diff_tokens
                  for tc in g["testclass"].unique())
        if hit:
            n_overlap += 1
    frac = (n_overlap / n_cycles) if n_cycles else 0.0
    if frac < floor:
        raise ValueError(
            f"test<->diff path-token overlap {frac:.1%} < floor {floor:.0%} "
            f"({n_overlap}/{n_cycles} cycles) -- identity/change-file derivation looks "
            f"broken; refusing to emit a dataset T0 cannot use.")


if __name__ == "__main__":
    sys.exit(main())
