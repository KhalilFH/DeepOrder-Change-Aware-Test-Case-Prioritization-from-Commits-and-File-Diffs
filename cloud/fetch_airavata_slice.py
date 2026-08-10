#!/usr/bin/env python3
"""
Fetch the airavata slice of the TCP-CI dataset in the cloud (Colab/Kaggle),
INCLUDING everything the schema generator needs -- not just a few CSVs.

Why more than "just the data"
-----------------------------
`FINAL6/TCP-CI_schema.py` builds the change-aware columns (`CommitMsg`,
`FilesChanged`, `LocAdded/Deleted`) by running LOCAL `git show` against a clone
of the project at `datasets/<owner>@<repo>/<repo>/` (see its
get_commit_message_from_git / get_changed_files_from_git). The upstream tool
(Ahmadreza-SY/TCP-CI `repository_miner.py`) likewise mines the repo with
pydriller + `git rev-list --all --remotes`. So the pipeline REQUIRES the git
repository, plus the per-project CI inputs from THREE source trees:

  datasets/<slug>/        exe.csv, builds.csv, id_map.csv,
                          entity_change_history.csv, contributors.csv
  rtp-torrent/<slug>/     <slug>-full.csv  (real testName), <slug>-builds.csv
  travis-torrent/data/<slug>/ data.csv     (build -> git_all_built_commits)

NOTE (airavata / this Zenodo tar): there is NO rtp-torrent tree in the archive,
so the "real testName" source above is absent. That is fine -- real test names
come from id_map.csv instead (path,id -> reverse value->key), which is what
`pipeline/step1_name_join.py` does. Do NOT run the vanilla TCP-CI_schema.py name
path expecting real names: with no rtp-torrent it emits useless `test_<id>`.

No GitHub token is needed: `git show` runs on the local clone. (A token would
only matter if you instead derived FilesChanged via the GitHub REST API.)

What this does
--------------
The dataset is a single 16.98 GB `.tar.gz` (Zenodo 5532640) that cannot be
seeked, and airavata is not at the front. So we STREAM the whole archive once
in the cloud and extract on-the-fly ONLY airavata's members from the three
source trees above **and the bundled git repo if the archive ships one**,
skipping the multi-GB per-build `analysis/` graphs (not needed for T0). Nothing
but the slice is written to disk; you then zip it and download only that home.

If the archive does NOT bundle the repo, the script prints the exact
`git clone` command to place it where the schema generator expects it.

Usage (Colab/Kaggle)
--------------------
    python fetch_airavata_slice.py
    # optional: SUBJECT=apache@commons  INCLUDE_ANALYSIS=1  INCLUDE_LOGS=1

Then download the slim slice home and run Step 1 LOCALLY (CSV-only, no git needed):
    python pipeline/step1_name_join.py \
        --data tcpci_slice/TCP-CI-dataset/datasets/apache@airavata
    # -> test_name_map.csv (real FQNs) + step1_gate_report.json + a PASS/FAIL gate
See docs/RESUME.md and docs/NEXT-STEPS.md Step 1 for the full sequence.
"""
import json
import os
import re
import sys
import tarfile
import time
import urllib.request

URL = "https://zenodo.org/api/records/5532640/files/TCP-CI-dataset.tar.gz/content"
SUBJECT = os.environ.get("SUBJECT", "airavata").lower()   # substring match on member path
OUT = os.environ.get("OUT", "tcpci_slice")
INCLUDE_ANALYSIS = os.environ.get("INCLUDE_ANALYSIS", "") not in ("", "0", "false", "False")
INCLUDE_LOGS = os.environ.get("INCLUDE_LOGS", "") not in ("", "0", "false", "False")

SUBJECT_RE = re.compile(r"([A-Za-z0-9._-]+@[A-Za-z0-9._-]+)")


def want(member):
    """Keep airavata's CI-input CSVs and its bundled git repo; drop the heavy
    per-build analysis graphs and (by default) the raw build_logs tarballs."""
    if not member.isfile():
        return False
    p = member.name.lower()
    if SUBJECT not in p:
        return False
    if "/analysis/" in p and not INCLUDE_ANALYSIS:
        return False          # multi-GB Understand graphs -- not needed for T0
    if "/build_logs/" in p and not INCLUDE_LOGS:
        return False          # ~tens of MB raw logs -- exe.csv already parsed them
    return True               # datasets CSVs, rtp-torrent, travis-torrent, AND the repo


def main():
    os.makedirs(OUT, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "tcpci-slice"})
    t0 = time.time()
    n_seen = 0
    logical_bytes = 0
    extracted = []
    subjects = set()
    repo_dirname = None  # e.g. "airavata" (from slug apache@airavata)

    print(f"Streaming {URL}", flush=True)
    print(f"SUBJECT={SUBJECT!r}  INCLUDE_ANALYSIS={INCLUDE_ANALYSIS}  "
          f"INCLUDE_LOGS={INCLUDE_LOGS}  OUT={OUT}\n", flush=True)

    with urllib.request.urlopen(req) as resp:
        # r|gz = streaming read over gzip; members MUST be handled in order and
        # extractfile() only works on the current member.
        with tarfile.open(fileobj=resp, mode="r|gz") as tar:
            for m in tar:
                n_seen += 1
                logical_bytes += m.size or 0
                mobj = SUBJECT_RE.search(m.name)
                if mobj:
                    slug = mobj.group(1)
                    subjects.add(slug)
                    if repo_dirname is None and SUBJECT in slug.lower():
                        # <owner>@<repo> -> repo dir the schema generator expects
                        repo_dirname = slug.split("@")[-1]
                if want(m):
                    dest = os.path.join(OUT, m.name)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    src = tar.extractfile(m)
                    if src is not None:
                        with open(dest, "wb") as f:
                            while True:
                                chunk = src.read(1 << 20)
                                if not chunk:
                                    break
                                f.write(chunk)
                        extracted.append({"name": m.name, "size": m.size})
                        # keep the log readable: only echo the CI-input CSVs
                        if m.name.lower().endswith(".csv"):
                            print(f"  + {m.size:>12,}  {m.name}", flush=True)
                if n_seen % 20000 == 0:
                    dt = time.time() - t0
                    print(f"  ... scanned {n_seen:,} members, "
                          f"{logical_bytes/1e9:.1f} GB logical, {dt:.0f}s, "
                          f"{len(extracted)} kept", flush=True)

    # Did we get an actual git repo (a .git dir) for the subject?
    bundled_git = any("/.git/" in e["name"] or e["name"].rstrip("/").endswith("/.git")
                      for e in extracted)

    # Core CI inputs the pipeline needs; their absence == an unusable slice.
    REQUIRED_CSVS = {"exe.csv", "builds.csv", "id_map.csv", "entity_change_history.csv"}
    basenames = {os.path.basename(e["name"]) for e in extracted}
    required_missing = sorted(REQUIRED_CSVS - basenames)

    manifest = {
        "source": URL,
        "subject_filter": SUBJECT,
        "repo_dirname_expected": repo_dirname,
        "bundled_git_found": bundled_git,
        "required_csvs_present": sorted(REQUIRED_CSVS & basenames),
        "required_csvs_missing": required_missing,
        "include_analysis": INCLUDE_ANALYSIS,
        "include_logs": INCLUDE_LOGS,
        "members_scanned": n_seen,
        "extracted_count": len(extracted),
        # Full inventory (NOT truncated): this file IS the ground truth of what
        # hit disk. A file's absence here means it was never extracted.
        "extracted": extracted,
        "all_subjects_seen": sorted(subjects),
        "elapsed_sec": round(time.time() - t0, 1),
    }
    with open("tcpci_slice_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 64)
    print(f"Extracted {len(extracted)} files to ./{OUT}/")
    print(f"Subjects present in archive ({len(subjects)}):")
    for s in sorted(subjects):
        print(f"   {s}{'   <-- MATCH' if SUBJECT in s.lower() else ''}")

    if not extracted:
        print(f"\n!! No files matched SUBJECT={SUBJECT!r}. Pick one of the "
              f"subjects above and re-run with SUBJECT=<owner@repo>.")
        return 1

    if required_missing:
        print(f"\n!! INCOMPLETE SLICE -- required core CSVs missing from the "
              f"extraction: {required_missing}. The stream likely dropped "
              f"mid-run. Re-run; do NOT trust a partial slice.")
        return 2

    base = os.path.join(OUT, "TCP-CI-dataset")
    slug = next((s for s in subjects if SUBJECT in s.lower()), f"?@{SUBJECT}")
    repo = repo_dirname or SUBJECT
    if not bundled_git:
        print("\n!! No bundled git repo found in the archive for this subject.")
        print("   The schema generator needs it. Clone it into place:")
        print(f"     git clone --no-single-branch "
              f"https://github.com/{slug.replace('@','/')} "
              f"{base}/datasets/{slug}/{repo}")
        print("   (public repo -> no GitHub token needed; use --no-single-branch "
              "so historical build commits are reachable for FilesChanged.)")
    else:
        print("\nBundled git repo found -- FilesChanged/CommitMsg can use it "
              "directly (best commit reachability).")

    print(f"\nNext:")
    print(f"  python <repo>/FINAL6/TCP-CI_schema.py --base-path {base} "
          f"--project {slug} --output-dir {base}/out")
    print(f"  zip -r airavata_slice.zip {OUT} tcpci_slice_manifest.json  # download this")
    print("Manifest -> tcpci_slice_manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
