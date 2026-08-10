# RESUME — start here (next session)

Single entry point to continue the change-aware TCP work.

## ⏩ CURRENT STATUS (2026-08-10) — Steps 1–4 DONE; T0 is a clean NULL on airavata
- **Step 3 (T0 feature) + Step 4 (paired eval) DONE.** `pipeline/relevance_t0.py`
  (reusable `(test identities, changed files) → per-test scores` module, ADR-0004 shape)
  + `pipeline/step3_t0.py` (adds exactly ONE feature — max path-token TF-IDF cosine of the
  test's **full repo path** vs each changed file — to the SAME step2 full model; prequential
  expanding-window eval; paired Wilcoxon + Vargha-Delaney A12 + bootstrap CI). Report:
  `FINAL6/apache@airavata/step3_report.json`.
- **RESULT — T0 does NOT lift per-cycle APFD, in any stratum (this is a real result, not a
  broken run).** PRIMARY small-fault (m≤4, n=30 cycles): HIST 0.824 vs HIST+T0 0.818,
  mean paired diff **−0.006**, Wilcoxon **p=0.92**, **A12=0.49**, win/tie/loss 4/24/2,
  boot95 [−0.043, +0.023]. Chronic and all-scored strata: same null. **Robust to
  tokenization** — FQN variant also null (−0.015, p=0.46, A12=0.46).
- **WHY (diagnosed, per NEXT-STEPS Step 4 "re-open the diagnosis" — not papered over):**
  the T0 signal is alive (58% nonzero, varies within 163/235 cycles; T0-alone ranker
  0.57 > random 0.50) — but it has **no headroom**. airavata's failures are recurring:
  in the tiny small-fault cycles **100% of failures already failed last run (E1=1)**, so
  the history-only model already ranks them at rank 1 (APFD 0.833 = optimal). Where there
  IS headroom (large small-fault cycles: HIST 0.81 vs optimal 0.97), T0-alone ≈ random
  (0.52 vs 0.50), so it cannot fill it. This is the same chronic-failure pathology Step 2
  flagged, now confirmed to reach into the small-fault stratum. The mechanism isn't
  disproven in principle — airavata just lacks the change-induced (non-recurring) failures
  T0 needs to catch.
- **NEXT (decision for Khalil):** to test T0's mechanism you need a subject with
  change-induced, non-recurring failures (headroom that history can't already claim).
  Options: (a) find/curate a second TCP-CI subject whose failing cycles are NOT dominated
  by a chronic co-failing block; (b) re-scope the claim to "T0 is redundant with history
  on chronic-failure-dominated CI" (a valid negative result); (c) move to the T1 call-graph
  / T7 coverage signals, which may separate failures history can't. Do NOT chase the number
  by adding try/except or cherry-picking cycles.

## (earlier) STATUS (2026-08-10) — Steps 1 & 2 DONE; PAUSED before Step 3
- **Step 1 gate: PASS.** `pipeline/step1_name_join.py` on the local slice → exit 0
  (55/55 ids resolve, 0 unresolved, all real `…Test` classes; **71.2%** of cycles have
  test↔diff overlap, floor 5%). Outputs `test_name_map.csv` + `step1_gate_report.json`.
- **Name map wired into schema gen.** Added `--name-map` to `FINAL6/TCP-CI_schema.py`
  (new `load_external_name_map`, fails loudly on any missing executed id — no silent
  `test_<id>`). Regenerated `FINAL6/apache@airavata/apache@airavata_enhanced_tcp_dataset.csv`
  (11,429 rows; Name = all 55 real FQNs, FilesChanged 98.6% populated, CommitMsg 100% real).
- **Step 2 baseline: DONE.** `pipeline/step2_baseline.py` (sklearn GradientBoosting,
  history-only; TF has no Python-3.14 wheels so the DeepOrder MLP is deferred). Per-cycle
  APFD on the 70/30 tail: **model 0.787, optimal 0.790, random 0.500 ✓**. See
  `FINAL6/apache@airavata/step2_report.json`.
- **⚠️ PIVOTAL FINDING — the tail is a degenerate regime.** airavata failures are bimodal:
  of 83 failing cycles, **31 are small-fault (m≤4)** vs **~50 are one chronic ~21-test
  co-failure block (m=21)**; ~90% of all failures are that block, and it dominates the
  middle+late timeline. The 70/30 tail evaluates ONLY the chronic regime, where history
  saturates APFD (model≈optimal) and T0 has no headroom — the wrong test bed. Do **not**
  read 0.787 as "the number to beat".
- **DECIDED for Step 3 (Khalil):** eval = **prequential/rolling (train-on-past, test-next),
  stratified by fault-set size**; primary T0 claim on **small-fault cycles (m≤4)**, chronic
  cycles reported separately; paired Wilcoxon + A12. **Khalil PAUSED here** — resume Step 3
  from this agreed regime.
- **Env:** repo `.venv` (Python 3.14 + pandas/numpy/scikit-learn; NO tensorflow). Slice is
  in the MAIN repo root `tcpci_slice/`; pipeline scripts live in the worktree → run with
  absolute cross-paths and `PYTHONUTF8=1` (Windows console chokes on `✓`/`✗` otherwise).

---

_History below is the original acquisition handoff (kept for context)._

As of **2026-08-08**, the data-acquisition prerequisite is **done**.

## TL;DR of where we are
- **Anchor = airavata (TCP-CI).** BugSwarm-traccar **failed** the STEP 0 viability gate
  (80 isolated fail/pass pairs over 11 yrs; 35 with per-test data, 30 single-fault;
  5.3-yr gap → no usable CI timeline). Evidence: `BugSwarm/step0_viability*.{py,txt}`,
  `BugSwarm/traccar_bugswarm_metadata.json`.
- **airavata slice acquired & verified** (real CI timeline: 11,484 execs, **55 test
  classes × 236 builds, ~88% dense**; bundled git repo present). Fetch tool:
  `cloud/fetch_airavata_slice.py` (streams the 16.98 GB Zenodo tar in the cloud,
  extracts only airavata + repo; download only the slim slice).

## 1. Check out the branch
```bash
git fetch origin && git checkout claude/bugswarm-harvester-handoff-578429
```

## 2. Put the data in place (gitignored — never commit it)
The slice was fetched + verified on Kaggle (2026-08-09). Download the two zips the
cloud run produced and extract at the repo root so you have:
```
tcpci_slice/TCP-CI-dataset/
  datasets/apache@airavata/
    exe.csv            # test,build,job,verdict,duration   (verdict 0=pass,1/2=fail,3=unknown; duration ms)
    builds.csv         # id,commits,started_at             (commits carry hashes)
    id_map.csv         # path,id  -> REAL test/file names   (reverse value->key)
    entity_change_history.csv   # Commit,EntityId -> per-cycle changed files (no git needed)
    contributors.csv, dataset.csv (TES_COM_* feature matrix; cross-check only)
    airavata/          # bundled git repo (.git) -> only needed if you later use `git show`
  travis-torrent/data/apache@airavata/data.csv
```
- **`airavata_csvs.zip` (~1.7 MB)** = the pipeline inputs; **this alone unblocks Step 1**.
- **`airavata_slice_full.zip` (~125 MB)** = adds the bundled git repo + everything.
- (No `rtp-torrent/` in the archive — expected; names come from `id_map.csv`.)
- **Verify the download isn't truncated** (must print `exe rows 11484 tests 55 builds 236`):
  ```bash
  python -c "import pandas as pd; d='tcpci_slice/TCP-CI-dataset/datasets/apache@airavata/'; e=pd.read_csv(d+'exe.csv'); print('exe rows',len(e),'tests',e['test'].nunique(),'builds',e['build'].nunique())"
  ```
- If your local tree is nested a level deeper, just use the actual path in `--data` below.
- The fetch tool (`cloud/fetch_airavata_slice.py`) now writes a **full** (untruncated)
  manifest and **fails loudly** if any core CSV is missing — so a partial slice can no
  longer masquerade as complete. If you ever re-fetch, trust `tcpci_slice_manifest.json`.

## 3. Kick off Step 1 — paste this to the new session
> Read `docs/HANDOFF-real-bugswarm-harvester.md` (top STEP 0 block) and
> `docs/NEXT-STEPS.md` Step 1. The airavata TCP-CI slice is at
> `tcpci_slice/TCP-CI-dataset/`. Run `pipeline/step1_name_join.py` and act on its gate.

### What Step 1 is — the module is written; just run and interpret it
**`pipeline/step1_name_join.py` is already implemented** (CSV-only, no git needed). It
does the real name join + the BLOCKING gate:
```bash
python pipeline/step1_name_join.py --data tcpci_slice/TCP-CI-dataset/datasets/apache@airavata
```
It reverses `id_map.csv` (`value→key`), maps `exe.test` → real path → FQN (e.g.
`… → org.apache.airavata.core.gfac.factory.OGCEGenericFactoryTest`), derives per-cycle
changed files from `entity_change_history.csv` (no `git show`), and reports:
- **Name integrity:** unresolved ids (must be 0) and how many resolve to `…Test.java`/`…IT.java`.
- **Path-overlap gate:** fraction of cycles with any nonzero test↔diff token overlap.

Outputs `test_name_map.csv` + `step1_gate_report.json`. Exit codes: **0 PASS**,
**3** name join broken (unresolved ids), **4** near-zero overlap (STOP — mapping broken).

**Then, on PASS:**
1. Feed `test_name_map.csv` as the `Name` source into the schema (do NOT use the vanilla
   `TCP-CI_schema.py` name path — with no rtp-torrent it emits `test_<id>`). Simplest:
   run the generator for `CommitMsg`/`FilesChanged`, then overwrite `Name` by joining on
   the test id via `test_name_map.csv`.
2. Proceed to **Step 2** (history-only per-cycle APFD baseline), then **Step 3** (add the
   T0 path-token relevance scalar). Test paths and changed-file paths share the same
   repo-relative vocabulary → ideal for T0.

**On FAIL (exit 3/4):** do not paper over it — that is a real finding. Re-open the
mapping/derivation (is `id_map` reversed correctly? are `entity_change_history` commits
matching `builds.commits`?) per `docs/NEXT-STEPS.md` Step 1 exit rules.

## Context to read (source of truth)
- `docs/HANDOFF-real-bugswarm-harvester.md` — STEP 0 result + pivot rationale.
- `docs/NEXT-STEPS.md` — Steps 0→4 in order (Step 1 has the id_map join + data shape).
- `CONTEXT.md`, `docs/adr/0001`–`0004` — glossary + decisions (the *why*).

## Caveats
- **Memory is machine-local** (`~/.claude/…`, not in git). Same machine → auto-loads
  the anchor/acquisition facts. Different machine → these repo docs are the truth.
- **The slice/zip are gitignored** (`airavata_slice*.zip`, `tcpci_slice/`). Keep those
  names or widen `.gitignore`. The ignore rules live on this branch; if you work from
  `main`, cherry-pick the `.gitignore` change or just never `git add` the data.
- **Do NOT** re-pull the full 16.98 GB tar or the per-build `analysis/` graphs unless
  you reach the code/coverage-feature work (≈T7); re-run the fetch with
  `INCLUDE_ANALYSIS=1` only then.
