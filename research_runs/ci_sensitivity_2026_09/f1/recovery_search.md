# F1 recovery search — per-test rankings for the Airavata HIST vs HIST+T0 comparison

- **Protocol:** `f1/protocol.md` (SHA-256 `038ff07713cb07eb425d111e8092911d5cdd44b896aca772621112a3ffc56800`), frozen and committed (`65d43ff`) before this search.
- **Search window so far:** `2026-09-25T09:50:16.856Z` (F1 start) to about `09:58Z`. This is agent/tool elapsed time; human hours are `UNKNOWN`.
- **Compute so far:** read-only Git and filesystem queries, and Analysis A (well under a second). No build, container, download or install.
- **Status:** **R1 FAILED; R2 NOT ATTEMPTED — it needs researcher decisions** (see "What R2 would need").

## L1 — Git objects (all refs, after `git fetch --all`)

- **Refs searched:** 16 refs and 64 commits, including `origin/claude/t0-path-token-relevance-f13581` and `claude/hive-change-relevance-replication-fa18d1`.
- **Found:**
  - `FINAL6/apache@airavata/step3_report.json` at `25eb6b7` (blob `6ce7b6659366d783abfe97b9212f5b74a77fabf8`). It holds aggregates only: `per_cycle` gives `cycle`, `m`, `n` and the APFD of each arm and reference ranker for 82 scored cycles. There are **no per-test rankings**.
  - The pipeline that produced it, at `25eb6b7`:
    - `pipeline/step3_t0.py`: `GradientBoostingClassifier(random_state=RANDOM_STATE)`, with ties broken by a seeded generator, so the run is deterministic given identical inputs and library versions;
    - `pipeline/step1_name_join.py`, `FINAL6/TCP-CI_schema.py` (with `--name-map`) and `cloud/fetch_airavata_slice.py`.
  - `step3_t0.py` writes only the JSON report (`json.dump`). It has no option to write rankings.
  - Unrelated rankings: `FINAL6/<subject>/{codebert,unixcoder}/…/practical_rankings/*.txt` belong to the older DeepOrder/CodeBERT experiments, not the HIST vs HIST+T0 comparison. They are out of scope under the protocol and are not used.
- **Not found:**
  - any per-cycle ranking for either arm;
  - `apache@airavata_enhanced_tcp_dataset.csv` (the T0 branch's `.gitignore` excluded the local slice, per commit `00386ca`);
  - `test_name_map.csv`.

## L2 — this host's filesystem

- **Recorded absolute paths absent:**
  - the report's `dataset` path under `C:\Users\kfhassen\…` (no such user on this host);
  - its `name_map` path under `…\tcpci_slice\…` (no `tcpci_slice` directory);
  - the August findings' `C:\h`, `C:\hb` and `C:\long_running_test_suites`.
- **No `t0-path-token-relevance*` worktree exists.** The worktrees present are `happy-wing`, `nervous-albattani-e2e50a` and `nifty-mendeleev-2baf6c`.
- **Bounded filename search** of `C:\Users\Mega-PC` (depth 7, excluding temp). It found:
  - `…\DeepOrder…\TCP-CI_DATASET\` (gitignored): older DeepOrder-line outputs (`apache@airavata_deeporder_fixed_processed.csv`, summary results). **Not** the enhanced dataset, and no rankings.
  - `Downloads\wetransfer_apache-airavata_2025-12-27_1212.zip` (2.91 GB), listed without extraction: 630 members, the same DeepOrder/CodeBERT/UniXcoder output tree as the committed `FINAL6/`. No slice and no HIST/T0 rankings.
  - `Downloads\TCP-CI-dataset.tar.gz`: **16,978,768,994 bytes**, matching the fetch script's description of Zenodo record 5532640 ("a single 16.98 GB `.tar.gz`"). This is the public raw input (L3), already on disk. It was **not opened**.
  - `Downloads\TCP-CI_DATASET.rar` (147 MB): not opened.
- **Environment:** no repository `.venv`. The system Python has no scikit-learn. The version that produced the report was never recorded; `requirements.txt` at `25eb6b7` says only `scikit-learn>=1.3`, and `docs/RESUME.md` says Python 3.14.

## L3 — public TCP-CI inputs

Present locally (L2), so no download is needed for the archive itself. Not opened pending the decisions below.

## R1 verdict

**FAILED.** No stored per-cycle ranking exists for either arm in any searched location.

## What R2 would need (for the researcher)

The chain is recorded at `25eb6b7`. Each step's cost is an estimate, not a measurement.

1. **Stream the local 16.98 GB archive once** and extract only the Airavata members (`datasets/`, `travis-torrent/`, and a bundled git repository if the archive ships one), about 10–30 minutes of one CPU.
2. **If the archive does not bundle Airavata's git repository:** `git clone https://github.com/apache/airavata`, a download from GitHub of unmeasured size. `TCP-CI_schema.py` needs it for `git show` of each build's commits.
3. **Install** pandas, numpy, scipy and **scikit-learn** into an isolated environment. The original version is unknown, and a different version can change GradientBoosting results.
4. **Run** `step1_name_join.py`, then `TCP-CI_schema.py --name-map`, then `step3_t0.py`, all exactly as at `25eb6b7`.
5. **Apply R2's test:** all 30 cohort cycles must reproduce the report's `apfd_hist` and `apfd_t0` within 1e-9. On failure, the ranking part stops (no retuning).

The protocol already flags whether R2 counts as recovery at all as the researcher's decision.
