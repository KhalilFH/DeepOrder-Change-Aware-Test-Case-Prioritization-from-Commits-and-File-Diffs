# E1 measured-block protocol — frozen 2026-09-22

- Status: frozen before the first measured attempt. Covers the 20 paired blocks per episode (plan §6, execution step 2) only.
- Authority: `docs/research/NEXT_RESEARCH_ACTION_PLAN.md` §4 and §6; locked E1 design in `../protocol.md`; resource ledger A9 (day-7 gate met by etcd-5509 + etcd-7492) and A18 (records are written into the repository as the run proceeds).
- Starting commit: `c706fb03738edcbc8f90856fc8e6126e45948313` on `research/revival-2026`, clean working tree. E1 unit suite: 150 tests OK at freeze.
- Not covered here, and not yet run: the 12 direct-policy checks (step 3), the identity/no-change and deterministic-failure controls (step 4), oracle classification and analysis (step 5). Oracle classification and analysis wait until all 40 blocks are complete or a documented stop occurs (step 5).

## Subjects

The first two Q0-qualified episodes in roster order, fixed by the day-7 gate (A9). They were not chosen by any observed policy loss.

| Episode | Q0 verdict | Counterpart type | Target |
|---|---|---|---|
| `etcd5509` | `Q0_QUALIFIED`, 16 focal / 4 pass on `V_bad`, 20/20 pass on `V_ok` | see `../task5_etcd5509_restoration.md` | `TestKVGetErrConnClosed` |
| `etcd7492` | `Q0_QUALIFIED`, 2 focal / 18 pass on `V_bad`, 20/20 pass on `V_ok` | see `../task5_etcd7492_restoration.md` | `TestHammerSimpleAuthenticate` |

Both are from the etcd project. The plan prefers different projects but does not require them. This limitation stays in force for every E1 claim.

## Frozen subject manifests

`manifests.json` holds the exact manifests. `run_blocks.py` refuses to start unless each manifest hashes to its value below. `Manifest.sha256` is recorded on every attempt.

| Episode | `Manifest.sha256` | Command (inside `-w <workdir>`) | Runner timeout |
|---|---|---|---|
| `etcd5509` | `a88cc638f51ebab31580aaf25948e9ce5968ab0fe23c29b50246ec60d66f5791` | `/go/gobench.test -test.v -test.count 1 -test.run TestKVGetErrConnClosed -test.timeout 45s` in `/go/src/github.com/coreos/etcd/clientv3/integration` | 60 s |
| `etcd7492` | `860cb23ef6abd35f6273e21f40557ecba481a167ee5ea4ad629577c9480d4620` | `/go/gobench.test -test.v -test.count 1 -test.run TestHammerSimpleAuthenticate -test.timeout 50s` in `/go/src/github.com/coreos/etcd/auth` | 65 s |

The commands match the Q0 frozen commands byte for byte (`../task5_artifacts/etcd5509/run_attempts.sh`, `../task5_artifacts/etcd7492/build/run_batch.sh`). Q0 imposed no outer timeout. Here the runner timeout sits above Go's `-test.timeout`, so a hang produces Go's goroutine dump, which the witness needs, before the runner kills anything.

**Images are pinned by ID, not by tag.** Tags can be re-pointed by a rebuild; an ID cannot.

| Image | ID | Created (UTC) |
|---|---|---|
| `etcd5509-bug` (`V_bad`) | `sha256:399e13203fc432de8a91473df1e91a64ea2ab1afecdb906166033d86f51589c6` | 2026-09-19T10:04:23Z |
| `etcd5509-fix` (`V_ok`) | `sha256:ffc618679d85e331c3b957c1af0ad561118bf488460dd5f80baeb10187800b26` | 2026-09-19T10:04:28Z |
| `etcd7492-bug` (`V_bad`) | `sha256:b51cb62a901bbf0d386b3ae2197d3a67b5e587b587a3ba035cc2a6212bb0164f` | 2026-09-19T11:00:39Z |
| `etcd7492-fix` (`V_ok`) | `sha256:2b66d59152c86f601c5f85bdffe6b919f98197cf9dc5c0a66409c54756cd047c` | 2026-09-19T11:01:43Z |

**Observed:** each image was created before its episode's first Q0 counted attempt (etcd-5509 at 2026-09-19T10:12:19Z; etcd-7492 at 11:04:27Z), and no later image carries these tags. **Inference:** these are the images Q0 qualified. Q0 did not record image IDs, so that link rests on timestamps and not on a recorded hash. The A13/A19 gap in etcd dependency versions remains open.

## Condition and reset

- Condition label `q0-default-unpinned`: the reproducer's native default, with no schedule forcing, as in Q0.
- Reset: a fresh `docker run --rm` container for every attempt, with a unique name. A timed-out container is removed by name (`runner.py`, verified by `selftest.py`).
- **Deviation from plan §11, disclosed:** the plan says to pin at most two allocated vCPUs per job, but Q0 ran with no CPU pinning, and `runner.py`'s manifest has no CPU field. Pinning now would change the scheduling condition under which both episodes qualified. For these subjects, a race window's rate is exactly the kind of property a CPU limit can shift. E1 therefore keeps the Q0 condition: unpinned, on a Docker Desktop VM with 16 CPUs and 16.29 GB of memory (engine 29.7.2), with no per-container memory limit. Cost is reported two ways (see Cost).
- One job at a time, run strictly in sequence: no attempt overlaps another.

## Blocks, seeds and order

- Measured blocks: 1–20 per episode, each with three attempts on each version. `Runner.run_block` collects all three attempts whatever the outcomes, so the research-only suffix is always present.
- Version order per block is `random.Random(seed).shuffle(["V_bad", "V_ok"])`, where `seed` is the first 32 bits of `SHA-256("e1:<episode>:block:<n>")`. The rule was fixed before any seed was computed, and seeds were not re-drawn for balance. Resulting first versions (computed at freeze):
  - `etcd5509` `V_bad` first in blocks 1, 2, 3, 8, 10, 12, 13, 16, 17, 18, 19 (11/20).
  - `etcd7492` `V_bad` first in blocks 4, 5, 8, 9, 10, 11, 13, 15, 17, 18, 20 (11/20).
- Time batches (analysis `--batch`): batch 1 = blocks 1–10, batch 2 = blocks 11–20.
- Execution order: `etcd5509` 1–10, `etcd7492` 1–10, `etcd5509` 11–20, `etcd7492` 11–20.
- Direct-policy check blocks are reserved as 101–112 (`reserved_from=101`). They stay out of the measured range and are not run under this record.

## Records

- Ledgers: `etcd5509/attempts.jsonl` and `etcd7492/attempts.jsonl`. Both are append-only and SHA-256 chained, and they carry full stdout and stderr. They are stored byte for byte (`.gitattributes`).
- Driver output: `run_logs/<episode>_b<range>.log`.
- Every attempt that runs is kept. No attempt is replaced, re-run or edited. Invalid or unresolved attempts enter the analysis as such.

## Stop rules

- `run_blocks.py` stops before a block if `docker info` fails, and on any Python-level error. It never retries automatically. A stopped run is resumed only from the next unrecorded block, and the stop is recorded here as an amendment.
- Cost check after batch 1: if the projected E1 total, including 12 direct checks and the controls, exceeds 20 allocated vCPU-hours under the conservative accounting, batch 2 does not start and a resource stop is recorded.
- Per-block outcomes printed by the driver are exit statuses only. They are not inspected for policy loss while collection is in progress, and they do not change the design.

## Cost accounting

Allocated vCPU-hours = allocated vCPUs × elapsed wall time, including suffixes. Two figures are reported:

- **Conservative:** 16 vCPUs, the whole VM. Unpinned containers could use all of it.
- **Q0 convention:** one vCPU-equivalent per sequential job, as `task5_etcd5509_restoration.md` and `task5_etcd7492_restoration.md` computed their figures.

**Pre-run estimate** (from Q0 rates; not a measurement): about 45 minutes of wall time for all 240 attempts. That is about 12 vCPU-hours under the conservative figure, or about 0.8 under the Q0 convention.

## Hashes at freeze

| File | SHA-256 |
|---|---|
| `e1_harness/runner.py` | `2b831f91017679bbb913938a05333aa6ecbbda3bbeaecafb26ff3fc6c2ff6be7` |
| `e1_harness/ledger.py` | `9e51b801dba5f034cc1818192d86314e41f93343a4efe6eaa3053cbf8f8a34f3` |
| `e1_harness/policy.py` | `b5a2e4ba6638a7a6ae565b0962b47c0af9bf07466bfa0473773b240918ff7da4` |
| `e1_harness/oracle.py` | `20a494f00b87d52a035b8a1d31b40d31ca46d9037854a5b0caafcf04b20a89a0` |
| `e1_harness/analysis.py` | `bc27c7de7ebce6bd42c56749c134b76945f13c615bf0f0533336f5528ee1a841` |
| `docs/research/NEXT_RESEARCH_ACTION_PLAN.md` | `84f1c189c1ce2d360f8e5d49d449797fda4bfc5e7096184ad998ff55fe7ed871` |
| `research_runs/ci_sensitivity_2026_09/protocol.md` | `67f2ea2913ee5566731d4f6e5f0c45a1c821d8a5058a23b0d5c8ae72341fdf45` |

`FREEZE.sha256` hashes this file, `manifests.json` and `run_blocks.py`. Check it with `sha256sum -c FREEZE.sha256` from this directory.
