# RESUME — start here (next session)

Single entry point to continue the change-aware TCP work. As of **2026-08-08**, the
data-acquisition prerequisite is **done**; the next milestone is **Step 1**.

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
