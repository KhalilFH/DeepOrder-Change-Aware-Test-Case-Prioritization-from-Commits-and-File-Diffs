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
Drop `airavata_slice.zip` in the repo root and extract so you have:
```
tcpci_slice/TCP-CI-dataset/
  datasets/apache@airavata/
    exe.csv            # test,build,job,verdict,duration   (verdict 0=pass,1/2=fail,3=unknown; duration ms)
    builds.csv         # id,commits,started_at             (commits carry hashes for `git show`)
    id_map.csv         # path,id  -> REAL test/file names   (reverse value->key)
    entity_change_history.csv, contributors.csv, dataset.csv (TES_COM_* feature matrix; cross-check only)
    airavata/          # bundled git repo (.git) -> FilesChanged / CommitMsg / LOC via `git show`
  travis-torrent/data/apache@airavata/data.csv
```
(No `rtp-torrent/` in the archive — that's expected; see Step 1.)

## 3. Kick off Step 1 — paste this to the new session
> Read `docs/HANDOFF-real-bugswarm-harvester.md` (top STEP 0 block) and
> `docs/NEXT-STEPS.md` Step 1. The airavata TCP-CI slice is extracted at
> `tcpci_slice/TCP-CI-dataset/`. Start Step 1.

### What Step 1 is (the name-integrity gate, now concrete)
1. **Real `Name` join (not positional).** The tar has no `rtp-torrent`, so
   `FINAL6/TCP-CI_schema.py`'s positional name map (`sorted(test_ids)[i] →
   unique_testNames[i]`, lines 110–145) never fires — and its fallback emits
   useless `test_<id>`. Correct source: reverse `id_map.csv` (`value→key`) and map
   `exe.csv.test` / `dataset.csv.Test` → real test path, e.g.
   `… → gfac-core/src/test/java/org/apache/airavata/.../OGCEGenericFactoryTest.java`
   → FQN. **Assert all 55 test ids resolve to a `…Test.java`/`…IT.java` path.**
2. **Generate the schema** with the bundled repo for `CommitMsg`/`FilesChanged`:
   `python FINAL6/TCP-CI_schema.py --base-path tcpci_slice/TCP-CI-dataset --project apache@airavata --output-dir tcpci_slice/TCP-CI-dataset/out`
   …but inject the corrected `Name` (the generator won't do it for this layout).
3. **Path-overlap gate:** fraction of cycles with any nonzero overlap between a
   test's path tokens and `FilesChanged`. Near-zero ⇒ STOP (mapping/derivation
   broken). Otherwise proceed to Step 2 (history-only per-cycle APFD baseline),
   then Step 3 (add the T0 path-token relevance scalar). Test paths and `git show`
   changed-file paths share the same repo-relative vocabulary → ideal for T0.

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
