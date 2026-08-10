# Next steps — kickoff for the machine with the data

This is the execution handoff from the design session. **Read `../CONTEXT.md` and `adr/0001`–`0004` first** — they hold the why. This file holds the *what to do next*, in order. Do it on the machine where the traccar dataset lives.

## Milestone: T0 — prove the mechanism

The single goal of the first work session: **show that one test-specific relevance scalar lifts per-cycle APFD over history-only, on traccar.** Nothing else until this passes or fails cleanly.

### Step 0 — Get REAL data first (PREREQUISITE)
- **This is blocked on real data.** The committed `BugSwarm/BugSwarm@Traccar/traccar_traccar_high_failure_19pct_8735.csv` is **synthetic** (templated names `EdgeTest005…`, trivial `EdgeTest005 → File5.java` mapping — relevance baked into the numbering, so T0 would "succeed" tautologically). Use it ONLY as a **known-answer unit-test fixture**, never for results.
- **✅ RESOLVED (2026-08-08): anchor = airavata (TCP-CI).** The BugSwarm-traccar fail-fast viability check **FAILED** — see the STEP 0 RESULT block at the top of [`HANDOFF-real-bugswarm-harvester.md`](HANDOFF-real-bugswarm-harvester.md). BugSwarm gives only 80 isolated fail↔pass pairs over 11 years (35 with per-test data, 30 of those single-fault, 5.3-yr gaps) — no usable CI timeline. **Do not build the BugSwarm harvester.** Get the **airavata (TCP-CI)** slice instead (real continuous CI timeline, already in the target schema).
  - **How to get airavata without a 17 GB local download:** the TCP-CI dataset (Zenodo record `5532640`) is a **single 16.98 GB `.tar.gz`** — no per-project download, and airavata is **not** at the front of the archive (first subject is `zolyfarkas@spf4j`), so local range/early-stop won't help. Run [`../cloud/fetch_airavata_slice.py`](../cloud/fetch_airavata_slice.py) **on Colab/Kaggle**: it streams the archive once (never stores it whole) and extracts on-the-fly only airavata's members, skipping the multi-GB per-build `analysis/` graphs. Zip the slice and download only that. Local machine pays only for the slim result.
  - **⚠️ It is MORE than "just the data" — you need the git repo too.** `FINAL6/TCP-CI_schema.py` derives the change-aware columns `CommitMsg`/`FilesChanged`/`LocAdded/Deleted` from **local `git show`** against a clone at `datasets/<slug>/<repo>/` (e.g. `datasets/apache@airavata/airavata/`); the upstream `repository_miner.py` mines it with pydriller. So the acquisition must provide, per subject: the `datasets/<slug>/` CSVs (`exe.csv`, `builds.csv`, `id_map.csv`, `entity_change_history.csv`, `contributors.csv`), the `rtp-torrent/<slug>/<slug>-full.csv` (real `testName`) + `-builds.csv`, the `travis-torrent/data/<slug>/data.csv`, **and the airavata git clone**. The fetch script extracts the repo if the archive bundles one; otherwise it prints `git clone --no-single-branch https://github.com/apache/airavata …` (public repo → **no GitHub token needed**; the old BugSwarm token was only for the GitHub-API way of getting changed files, which the local clone replaces).
  - Then convert to the framework schema: `python FINAL6/TCP-CI_schema.py --base-path <slice>/TCP-CI-dataset --project apache@airavata`.
  - **Name-integrity (Step 1) is not just "verify" — FINAL6 has a confirmed bug.** `TCP-CI_schema.py:110-145` assigns `Name` by **sorted position** (`sorted(test_ids)[i] → unique_testNames[i]`), which is the [[name-mapping-unverified]] break. The real join exists: the upstream tool ids each test from its class/package via `IdMapper` (persisted in `id_map.csv`), so `exe.csv.test` → real name should be recovered through `id_map.csv`, **not** by position. Fix this before trusting any name-derived (T0) signal.
- Note: the earlier "traccar has 18.96% failures, best anchor" stat came from the *synthetic* data (harvester targets high failure by construction) — it is not a real property of traccar.

### Step 1 — Name-integrity gate (BLOCKING — see ADR 0002 / CONTEXT open risks)
- The `Test Name` → execution-row join provenance is unverified (`FINAL6/TCP-CI_schema.py:126` maps by sorted position, which may be wrong).
- Gate metric: **fraction of cycles that have any nonzero test↔diff path overlap** between derived test paths and `FilesChanged`.
- If near-zero → the mapping or path derivation is broken. **STOP. Fix the join by real test ID before trusting any APFD number.**
- **✅ RESOLVED for airavata (2026-08-08, inspected the fetched slice).** The Zenodo tar has **no `rtp-torrent`** tree, so the positional bug never fires — but the generator's fallback then emits `test_<id>`, also useless. The **correct, unambiguous** join: `id_map.csv` is `path,id`; reverse it (`value→key`) and map `exe.csv.test` / `dataset.csv.Test` → real test path, e.g. `4003 →? gfac-core/src/test/java/org/apache/airavata/.../OGCEGenericFactoryTest.java` → FQN. So Step 1 = (a) build the reverse-id_map name join, (b) confirm all 55 test ids resolve to a `…Test.java`/`…IT.java` path, (c) run the path-overlap gate. Test paths and `git show` changed-file paths share the same repo-relative vocabulary → ideal for T0.
- **🔧 IMPLEMENTED: [`pipeline/step1_name_join.py`](../pipeline/step1_name_join.py)** does exactly this (CSV-only, no git): `python pipeline/step1_name_join.py --data tcpci_slice/TCP-CI-dataset/datasets/apache@airavata`. It derives per-cycle changed files from `entity_change_history.csv` (Commit→EntityId) + `builds.csv`, so the whole gate runs without `git show`. Emits `test_name_map.csv` + `step1_gate_report.json`; exit **0** PASS, **3** unresolved ids (name join broken), **4** near-zero overlap (STOP). See [`RESUME.md`](RESUME.md) for the full run/interpret sequence.
- **Data shape confirmed:** `exe.csv` = 11,484 execs, **55 distinct test classes × 236 builds (~88% density)** → real recurring history (E1/E2/E3, DIST well-defined), unlike BugSwarm. `exe.csv` cols `test,build,job,verdict,duration` (verdict 0=pass,1/2=fail,3=unknown; duration in ms); `builds.csv` cols `id,commits,started_at` (commits carry the hashes for `git show`). `dataset.csv` (`Build,Test,TES_COM_*…`) is the tool's feature matrix — a bonus cross-check, not the label source.

### Step 2 — Honest history-only baseline
- Train the history-only model. Report **per-cycle APFD** (NOT the old global number). Also report global APFD separately.
- This is the number T0 must beat.

### Step 3 — Add the T0 relevance scalar
- Compute **max path-token cosine**: tokenize test identity (`pkg.Class#method`, split on `/`, `.`, camelCase) and each changed path; TF-IDF cosine; take the max over the cycle's changed files. Graded [0,1], varies per test within a cycle.
- Add it as one feature to the SAME model (change one thing only). Keep the binary-Verdict objective (LTR comes later).

### Step 4 — Compare, honestly
- history-only vs history+T0: **per-cycle APFD, paired Wilcoxon across cycles + Vargha-Delaney A12, bootstrap CI.**
- Hard rule: **no broad try/except that swallows failed runs** — a degenerate run is a failure, not a data point.

### Exit
- **T0 lifts per-cycle APFD (significant, positive effect size)** → mechanism proven; proceed to T1 (call-graph) + T7 (coverage oracle), then T6 (mutation). See the roadmap in `CONTEXT.md`.
- **T0 does not lift it** → do not paper over it. That's a real result too; re-open the diagnosis (is the signal actually varying? is the Name mapping still lying?).

## Build constraint (ADR 0004)
Build the relevance computation as a `(repo checkout, commit) → per-test scores` module from the start. The demo and the research call the same module. No hardcoded Kaggle/conda paths, no notebook-only shortcuts in the relevance path.
