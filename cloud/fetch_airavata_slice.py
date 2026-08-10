#!/usr/bin/env python3
"""
Fetch ONE subject's slim slice of the TCP-CI dataset (Zenodo 5532640) in the
cloud (Colab/Kaggle) -- everything the pipeline needs for that subject, not the
whole 16.98 GB archive.

(Historically named for airavata; now works for ANY TCP-CI subject via --subject.)

Why more than "just the data"
-----------------------------
`FINAL6/TCP-CI_schema.py` builds the change-aware columns (`CommitMsg`,
`FilesChanged`, `LocAdded/Deleted`) via LOCAL `git show` against a clone of the
project at `datasets/<owner>@<repo>/<repo>/`; the upstream tool
(Ahmadreza-SY/TCP-CI `repository_miner.py`) mines it with pydriller. So the
pipeline needs the git repo PLUS the per-subject CI inputs from up to three
source trees:

  datasets/<slug>/            exe.csv, builds.csv, id_map.csv,
                              entity_change_history.csv, contributors.csv
  rtp-torrent/<slug>/         <slug>-full.csv (real testName), <slug>-builds.csv
  travis-torrent/data/<slug>/ data.csv (build -> git_all_built_commits)

NOTE: some subjects (e.g. airavata) have NO rtp-torrent tree in the archive.
That's fine -- real test names come from id_map.csv (path,id -> reverse
value->key), which `pipeline/step1_name_join.py` does. Do NOT expect the vanilla
TCP-CI_schema.py name path to produce real names without rtp-torrent (it emits
useless `test_<id>`).

No GitHub token is needed: `git show` runs on the local clone.

What this does
--------------
The dataset is a single 16.98 GB `.tar.gz` that cannot be seeked and whose
subjects are not ordered. So we STREAM the whole archive once in the cloud and
extract on-the-fly ONLY the chosen subject's members (CI CSVs + bundled git repo
if present), skipping the multi-GB per-build `analysis/` graphs and raw
`build_logs`. Only the slim slice is written to disk; zip it and download that.

If the archive does NOT bundle the repo, the script prints the exact `git clone`
to place it where the schema generator expects it.

Usage (Colab/Kaggle)
--------------------
    python fetch_airavata_slice.py --subject SonarSource@sonarqube
    python fetch_airavata_slice.py --subject airavata            # default
    # flags: --include-analysis  --include-logs  --out DIR
    # (env vars SUBJECT / OUT / INCLUDE_ANALYSIS / INCLUDE_LOGS also work)

Then download the slim slice and run Step 1 LOCALLY (CSV-only, no git):
    python pipeline/step1_name_join.py \
        --data tcpci_slice/TCP-CI-dataset/datasets/<owner>@<repo>
See docs/RESUME.md and docs/NEXT-STEPS.md Step 1 for the full sequence.
"""
import argparse
import json
import os
import re
import sys
import tarfile
import time
import urllib.request

URL = "https://zenodo.org/api/records/5532640/files/TCP-CI-dataset.tar.gz/content"
SUBJECT_RE = re.compile(r"([A-Za-z0-9._-]+@[A-Za-z0-9._-]+)")


def _env_flag(name):
    return os.environ.get(name, "") not in ("", "0", "false", "False")


def parse_args():
    ap = argparse.ArgumentParser(
        description="Fetch one subject's slim TCP-CI slice from Zenodo (streamed).")
    ap.add_argument("--subject", default=os.environ.get("SUBJECT", "airavata"),
                    help="subject slug 'owner@repo' (e.g. SonarSource@sonarqube) "
                         "or a unique substring of it. Default: airavata.")
    ap.add_argument("--out", default=os.environ.get("OUT", "tcpci_slice"),
                    help="output directory (default: tcpci_slice)")
    ap.add_argument("--include-analysis", action="store_true",
                    default=_env_flag("INCLUDE_ANALYSIS"),
                    help="also extract the multi-GB per-build Understand analysis/ graphs")
    ap.add_argument("--include-logs", action="store_true",
                    default=_env_flag("INCLUDE_LOGS"),
                    help="also extract the raw travis build_logs tarballs")
    return ap.parse_args()


def want(member, subject, include_analysis, include_logs):
    """Keep the subject's CI-input CSVs and its bundled git repo; drop the heavy
    per-build analysis graphs and (by default) the raw build_logs tarballs."""
    if not member.isfile():
        return False
    p = member.name.lower()
    if subject not in p:
        return False
    if "/analysis/" in p and not include_analysis:
        return False          # multi-GB Understand graphs -- not needed for T0
    if "/build_logs/" in p and not include_logs:
        return False          # raw logs -- exe.csv already parsed them
    return True               # datasets CSVs, rtp-torrent, travis-torrent, AND the repo


def main():
    args = parse_args()
    subject = args.subject.lower()
    out = args.out
    os.makedirs(out, exist_ok=True)

    req = urllib.request.Request(URL, headers={"User-Agent": "tcpci-slice"})
    t0 = time.time()
    n_seen = 0
    logical_bytes = 0
    extracted = []
    subjects = set()
    repo_dirname = None  # e.g. "sonarqube" (from slug SonarSource@sonarqube)

    print(f"Streaming {URL}", flush=True)
    print(f"subject={subject!r}  include_analysis={args.include_analysis}  "
          f"include_logs={args.include_logs}  out={out}\n", flush=True)

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
                    if repo_dirname is None and subject in slug.lower():
                        # <owner>@<repo> -> repo dir the schema generator expects
                        repo_dirname = slug.split("@")[-1]
                if want(m, subject, args.include_analysis, args.include_logs):
                    dest = os.path.join(out, m.name)
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
        "subject_filter": subject,
        "repo_dirname_expected": repo_dirname,
        "bundled_git_found": bundled_git,
        "required_csvs_present": sorted(REQUIRED_CSVS & basenames),
        "required_csvs_missing": required_missing,
        "include_analysis": args.include_analysis,
        "include_logs": args.include_logs,
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
    print(f"Extracted {len(extracted)} files to ./{out}/")
    print(f"Subjects present in archive ({len(subjects)}):")
    for s in sorted(subjects):
        print(f"   {s}{'   <-- MATCH' if subject in s.lower() else ''}")

    if not extracted:
        print(f"\n!! No files matched --subject {subject!r}. Pick one of the "
              f"subjects above and re-run with --subject <owner@repo>.")
        return 1

    matched = sorted(s for s in subjects if subject in s.lower())
    if len(matched) > 1:
        print(f"\n!! --subject {subject!r} matched MULTIPLE subjects: {matched}. "
              f"Files for ALL of them were extracted. Re-run with a full "
              f"'owner@repo' slug if you wanted exactly one.")

    if required_missing:
        print(f"\n!! INCOMPLETE SLICE -- required core CSVs missing from the "
              f"extraction: {required_missing}. The stream likely dropped "
              f"mid-run. Re-run; do NOT trust a partial slice.")
        return 2

    base = os.path.join(out, "TCP-CI-dataset")
    slug = matched[0] if matched else f"?@{subject}"
    repo = repo_dirname or subject
    safe = slug.replace("@", "_")
    if not bundled_git:
        print("\n!! No bundled git repo found for this subject. The schema "
              "generator needs it -- clone it into place:")
        print(f"     git clone --no-single-branch "
              f"https://github.com/{slug.replace('@', '/')} "
              f"{base}/datasets/{slug}/{repo}")
        print("   (public repo -> no GitHub token needed; --no-single-branch so "
              "historical build commits are reachable for FilesChanged.)")
    else:
        print("\nBundled git repo found -- FilesChanged/CommitMsg can use it "
              "directly (best commit reachability).")

    print("\nNext (local):")
    print(f"  python pipeline/step1_name_join.py --data {base}/datasets/{slug}")
    print(f"  zip -rq {safe}_slice.zip {out} tcpci_slice_manifest.json   # download this")
    print("Manifest -> tcpci_slice_manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
