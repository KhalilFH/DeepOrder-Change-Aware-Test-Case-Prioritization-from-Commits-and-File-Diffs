"""
Dataset Audit Script
====================
Analyses all 25 TCP-CI projects in datasets/ to understand:
  1. Why the 6 projects were selected (failure rate vs test count balance)
  2. Which features are available / populated per project
  3. Which of the remaining 19 projects are candidates for transfer learning
  4. Coverage data (COV_*) availability — the key signal we want to add
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path

DATASETS_ROOT = Path("/mnt/c/Users/Mega-PC/DeepOrder-Change-Aware-Test-Case-Prioritization-from-Commits-and-File-Diffs/datasets")

# Projects already used in FINAL6
SELECTED_PROJECTS = {
    "apache@airavata",
    "apache@curator",
    "apache@rocketmq",
    "CompEvol@beast2",
    "thinkaurelius@titan",
    # traccar is from BugSwarm, not TCP-CI datasets folder
}

# Key feature groups to audit
FEATURE_GROUPS = {
    "Historical (REC)": [
        "REC_Age", "REC_LastFailureAge", "REC_LastTransitionAge",
        "REC_RecentFailRate", "REC_RecentTransitionRate",
        "REC_TotalFailRate", "REC_TotalTransitionRate",
        "REC_LastVerdict", "REC_LastExeTime",
        "REC_MaxTestFileFailRate", "REC_MaxTestFileTransitionRate",
    ],
    "Change (TES_CHN)": [
        "TES_CHN_LinesAdded", "TES_CHN_LinesDeleted",
        "TES_CHN_AddedChangeScattering", "TES_CHN_DeletedChangeScattering",
        "TES_CHN_DMMSize", "TES_CHN_DMMComplexity", "TES_CHN_DMMInterfacing",
    ],
    "Coverage (COV)": [
        "COV_ChnScoreSum", "COV_ImpScoreSum",
        "COV_ChnCount",    "COV_ImpCount",
    ],
    "Coverage+Code (COD_COV_CHN)": [
        "COD_COV_CHN_C_LinesAdded", "COD_COV_CHN_C_LinesDeleted",
        "DET_COV_C_Faults", "DET_COV_IMP_Faults",
    ],
    "Process (TES_PRO)": [
        "TES_PRO_CommitCount", "TES_PRO_DistinctDevCount",
        "TES_PRO_OwnersExperience", "TES_PRO_AllCommitersExperience",
    ],
}

# Minimum thresholds for a project to be usable
MIN_TOTAL_FAILURES   = 50     # need at least 50 failures to learn from
MIN_BUILDS           = 30     # need enough CI cycles
MIN_FAILURE_RATE     = 0.003  # at least 0.3% failure rate
MIN_TESTS_PER_BUILD  = 5      # at least 5 tests per cycle on average

def check_feature_availability(df: pd.DataFrame, features: list) -> dict:
    """Check what % of rows have real (non -1, non NaN) values for each feature."""
    results = {}
    for feat in features:
        if feat not in df.columns:
            results[feat] = "MISSING"
        else:
            total = len(df)
            # TCP-CI uses -1 as sentinel for "not available"
            valid = df[feat].replace(-1, np.nan).notna().sum()
            pct = valid / total * 100 if total > 0 else 0
            results[feat] = f"{pct:.0f}%"
    return results

def audit_project(project_path: Path) -> dict:
    """Audit a single project's dataset.csv."""
    dataset_file = project_path / "dataset.csv"
    if not dataset_file.exists():
        return None

    try:
        df = pd.read_csv(dataset_file)
    except Exception as e:
        return {"error": str(e)}

    total_rows       = len(df)
    unique_builds    = df["Build"].nunique()   if "Build"   in df.columns else 0
    unique_tests     = df["Test"].nunique()    if "Test"    in df.columns else 0
    total_failures   = int(df["Verdict"].sum()) if "Verdict" in df.columns else 0
    failure_rate     = df["Verdict"].mean()    if "Verdict" in df.columns else 0
    avg_tests_build  = total_rows / unique_builds if unique_builds > 0 else 0
    failures_per_build = total_failures / unique_builds if unique_builds > 0 else 0

    # Feature availability per group
    group_availability = {}
    for group_name, features in FEATURE_GROUPS.items():
        avail = check_feature_availability(df, features)
        # Summarise as % of features with >50% data
        well_populated = sum(
            1 for v in avail.values()
            if v != "MISSING" and v != "0%" and (v == "100%" or int(v.rstrip("%")) > 50)
        )
        group_availability[group_name] = {
            "populated_features": f"{well_populated}/{len(features)}",
            "details": avail,
        }

    # Coverage signal specifically
    cov_available = False
    if "COV_ChnScoreSum" in df.columns:
        valid_cov = (df["COV_ChnScoreSum"].replace(-1, np.nan) > 0).sum()
        cov_pct = valid_cov / total_rows * 100
        cov_available = cov_pct > 10  # at least 10% rows have coverage data
    else:
        cov_pct = 0

    # Selection criteria
    meets_criteria = (
        total_failures   >= MIN_TOTAL_FAILURES  and
        unique_builds    >= MIN_BUILDS          and
        failure_rate     >= MIN_FAILURE_RATE    and
        avg_tests_build  >= MIN_TESTS_PER_BUILD
    )

    return {
        "total_rows":          total_rows,
        "unique_builds":       unique_builds,
        "unique_tests":        unique_tests,
        "total_failures":      total_failures,
        "failure_rate":        failure_rate,
        "avg_tests_per_build": avg_tests_build,
        "failures_per_build":  failures_per_build,
        "cov_data_pct":        cov_pct,
        "cov_available":       cov_available,
        "meets_criteria":      meets_criteria,
        "feature_groups":      group_availability,
    }


def main():
    print("=" * 90)
    print("TCP-CI DATASET AUDIT — All Projects")
    print("=" * 90)

    project_dirs = sorted([p for p in DATASETS_ROOT.iterdir() if p.is_dir()])
    results = {}

    for proj_dir in project_dirs:
        proj_name = proj_dir.name
        print(f"  Reading {proj_name}...", end=" ", flush=True)
        result = audit_project(proj_dir)
        if result and "error" not in result:
            results[proj_name] = result
            print("done")
        else:
            print(f"skipped ({result.get('error','no dataset.csv') if result else 'no dataset.csv'})")

    # -----------------------------------------------------------------------
    # TABLE 1 — Summary of all projects
    # -----------------------------------------------------------------------
    print("\n" + "=" * 90)
    print("TABLE 1 — ALL PROJECTS OVERVIEW")
    print("=" * 90)
    header = f"{'Project':<35} {'Builds':>7} {'Tests':>7} {'Rows':>8} {'Failures':>9} {'Fail%':>7} {'Avg T/B':>8} {'F/B':>6} {'COV%':>6} {'OK?':>5}"
    print(header)
    print("-" * 90)

    selected_summary   = []
    candidate_summary  = []
    rejected_summary   = []

    for proj_name, r in results.items():
        is_selected = proj_name in SELECTED_PROJECTS
        tag = " ★" if is_selected else ("  ✓" if r["meets_criteria"] else "  ✗")

        line = (
            f"{proj_name:<35} "
            f"{r['unique_builds']:>7} "
            f"{r['unique_tests']:>7} "
            f"{r['total_rows']:>8} "
            f"{r['total_failures']:>9} "
            f"{r['failure_rate']*100:>6.2f}% "
            f"{r['avg_tests_per_build']:>8.1f} "
            f"{r['failures_per_build']:>6.2f} "
            f"{r['cov_data_pct']:>5.0f}% "
            f"{tag}"
        )
        print(line)

        if is_selected:
            selected_summary.append((proj_name, r))
        elif r["meets_criteria"]:
            candidate_summary.append((proj_name, r))
        else:
            rejected_summary.append((proj_name, r))

    print("-" * 90)
    print("★ = already selected   ✓ = meets criteria (transfer learning candidate)   ✗ = insufficient data")

    # -----------------------------------------------------------------------
    # TABLE 2 — Why the 6 were selected (failure rate vs test count)
    # -----------------------------------------------------------------------
    print("\n" + "=" * 90)
    print("TABLE 2 — SELECTED PROJECTS: WHY THEY WERE CHOSEN")
    print("=" * 90)
    print(f"Selection logic: need ≥{MIN_TOTAL_FAILURES} failures, ≥{MIN_BUILDS} builds, "
          f"≥{MIN_FAILURE_RATE*100:.1f}% failure rate, ≥{MIN_TESTS_PER_BUILD} avg tests/build")
    print()

    for proj_name, r in selected_summary:
        print(f"  {proj_name}")
        print(f"    Builds: {r['unique_builds']}  |  Tests: {r['unique_tests']}  |  "
              f"Failures: {r['total_failures']} ({r['failure_rate']*100:.2f}%)")
        print(f"    Avg tests/build: {r['avg_tests_per_build']:.1f}  |  "
              f"Failures/build: {r['failures_per_build']:.2f}")
        print(f"    Coverage data available: {'YES' if r['cov_available'] else 'NO'} "
              f"({r['cov_data_pct']:.0f}% rows populated)")
        print()

    # -----------------------------------------------------------------------
    # TABLE 3 — Transfer learning candidates
    # -----------------------------------------------------------------------
    print("=" * 90)
    print("TABLE 3 — TRANSFER LEARNING CANDIDATES (meet criteria, not yet used)")
    print("=" * 90)

    if candidate_summary:
        for proj_name, r in candidate_summary:
            print(f"  {proj_name}")
            print(f"    Builds: {r['unique_builds']}  |  Tests: {r['unique_tests']}  |  "
                  f"Failures: {r['total_failures']} ({r['failure_rate']*100:.2f}%)")
            print(f"    Coverage data: {'YES' if r['cov_available'] else 'NO'} "
                  f"({r['cov_data_pct']:.0f}% rows populated)")
            print()
    else:
        print("  None found with current thresholds.")

    # -----------------------------------------------------------------------
    # TABLE 4 — Feature group availability across selected projects
    # -----------------------------------------------------------------------
    print("=" * 90)
    print("TABLE 4 — FEATURE GROUP AVAILABILITY IN SELECTED PROJECTS")
    print("=" * 90)
    print(f"{'Project':<35}", end="")
    for g in FEATURE_GROUPS:
        short = g.split("(")[0].strip()[:12]
        print(f"  {short:>14}", end="")
    print()
    print("-" * 90)

    for proj_name, r in selected_summary:
        print(f"{proj_name:<35}", end="")
        for group_name in FEATURE_GROUPS:
            val = r["feature_groups"][group_name]["populated_features"]
            print(f"  {val:>14}", end="")
        print()

    # -----------------------------------------------------------------------
    # TABLE 5 — COV_* detail for selected projects
    # -----------------------------------------------------------------------
    print("\n" + "=" * 90)
    print("TABLE 5 — COVERAGE SIGNAL DETAIL (COV_* columns) — SELECTED PROJECTS")
    print("=" * 90)
    print("These are the test-covers-changed-code features. Critical for enhanced TCP.")
    print()

    for proj_name, r in selected_summary:
        cov_details = r["feature_groups"]["Coverage (COV)"]["details"]
        print(f"  {proj_name}:")
        for feat, pct in cov_details.items():
            bar_len = int(pct.rstrip("%")) // 5 if pct not in ("MISSING", "0%") else 0
            bar = "█" * bar_len
            print(f"    {feat:<25} {pct:>5}  {bar}")
        print()

    # -----------------------------------------------------------------------
    # RECOMMENDATION
    # -----------------------------------------------------------------------
    print("=" * 90)
    print("RECOMMENDATION")
    print("=" * 90)

    total_selected   = len(selected_summary)
    total_candidates = len(candidate_summary)
    total_rejected   = len(rejected_summary)

    print(f"  Projects already selected:              {total_selected}")
    print(f"  New transfer learning candidates:       {total_candidates}")
    print(f"  Rejected (insufficient data):           {total_rejected}")
    print()

    cov_projects = [n for n, r in selected_summary if r["cov_available"]]
    no_cov_projects = [n for n, r in selected_summary if not r["cov_available"]]

    if cov_projects:
        print(f"  Coverage data available for:  {cov_projects}")
        print(f"  → COV_ChnScoreSum can be used as a feature for these projects")
    if no_cov_projects:
        print(f"  No coverage data for:         {no_cov_projects}")
        print(f"  → Fall back to embedding-based test-file overlap for these")

    print()
    print("  FEATURE ENRICHMENT STRATEGY (revised after audit):")
    print("  ┌─ All projects: add REC_RecentFailRate, REC_LastFailureAge,")
    print("  │                    REC_RecentTransitionRate, TES_CHN_LinesAdded/Deleted")
    print("  ├─ Projects with COV: add COV_ChnScoreSum, COV_ImpScoreSum directly")
    print("  └─ Projects without COV: use embedding test-file overlap as proxy")
    print()
    print("  Run this script again after adding more projects to see updated counts.")
    print("=" * 90)


if __name__ == "__main__":
    main()
