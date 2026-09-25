# C1 executable launch record v1

## Material Passport

- Study: `c1_ci_configuration_visibility_v1`; design freeze v1 (`DESIGN_FREEZE.sha256`, verified 8/8).
- This record is the **second freeze boundary** of `DESIGN_FREEZE.md`: the executable launch freeze. It is bound, together with the code, manifests, schedule and calibration evidence, by `FREEZE.sha256`. That file is written after this record and excludes itself.
- Frozen: 2026-09-25, by the C1 implementation agent (single agent), under `HANDOFF_PROMPT.md`. The exact freeze time is the `# frozen_utc` header line in `FREEZE.sha256`.
- Authority: the researcher's handoff instruction (2026-09-25) covers preparation, implementation, offline tests, bounded calibration and this freeze. It **does not** authorize measured blocks 1–10. Batch A needs a subsequent explicit launch instruction. Nothing in this record is a C1 measured observation.
- Repository: branch `research/revival-2026`, `HEAD = 721d885a315a2c0ef26a82f2613248a4abcc110c`. The C1 implementation and evidence files are **uncommitted**; their LF-normalized SHA-256 values in `FREEZE.sha256` are the binding identity. Committing them later changes nothing, provided the digests still verify.
- Amendments: **none**. No frozen design clause was changed; implementation choices within the contract are listed in section 9.

## 1. Enrolled and excluded subjects

All six roster subjects are enrolled (`READY_HISTORICAL`); none is excluded. Four projects are represented, which meets C0 (at least four pairs across at least two projects). Full dossiers are in `subject_manifest.json`.

| Subject | Project | Counterpart class | Image ID bad / fix (prefix) | Commit | Test binary SHA-256 bad / fix | Go | Inner / outer s |
|---|---|---|---|---|---|---|---|
| etcd5509 | etcd | historical pair, identical test backport | `399e13203fc4` / `ffc618679d85` | `9ed3b446` | `f334d73560d8` / `68925990e2ee` | go1.10.8 | 45 / 60 |
| etcd7492 | etcd | **controlled historical-fix reversal** on pinned base 148c923c (not a historical pair) | `b51cb62a901b` / `2b66d59152c8` | `148c923c` | `233f3b989b1f` / `f9f2c966b529` | go1.13.15 | 50 / 65 |
| grpc1859 | grpc-go | historical pair, identical test backport | `6b890fa74bed` / `3b72ed206066` | `484b3ebb` | `88e63334adbc` / `a563f1a33e72` | go1.13.15 | 110 / 120 |
| grpc2391 | grpc-go | historical pair, identical test backport | `cc6e5a69cd7a` / `65a2902bbfce` | `ff2aa059` | `a7ab35eaa54a` / `5564bf4d61fe` | go1.13.15 | 60 / 90 |
| istio17860 | istio | historical production pair, identical fix test | `23e14b796ad0` / `7fba6b07fc8d` | `c6e91302` | `f7aa4fff7f72` / `8c7d7829251a` | go1.13.15 | 30 / 60 |
| k8s26980 | kubernetes | historical parent production plus identical fix test | `8a215c592956` / `6c93e46a3848` | `628af356` | `585070ec85ed` / `7a68ca76d2ff` | go1.12.17 | 60 / 90 |

Full 64-hex image IDs, blob IDs, test-file hashes, dependency identities and every equal-treatment check are in `subject_manifest.json` and `prep/image_checks.json`.

**Selection limits** (reported even though C0 passes):

- These are six known, previously restored subjects from one convenience roster, on one host.
- Three were Q0-qualified and three were not; the Q0 labels are unchanged.
- grpc1859's image IDs were never recorded in Q0. Its identity with the Q0 images is inferred from creation times and blob checks, not proven.
- Base-image registry digests are unknown for all images.
- The images exist only in this Docker Desktop VM; no `docker save` archive exists.

## 2. Host and profiles

- Host: AMD Ryzen 7 7700 (8C/16T), Windows 11 Pro 10.0.26200.
  - Docker Desktop 4.90.0, engine 29.7.2, runc 1.4.3, cgroup v2 (`cgroupfs`).
  - VM kernel 6.6.87.2-microsoft-standard-WSL2, **16 CPUs**, 15.17 GiB.
  - The driver is Windows CPython 3.14.3 through the `desktop-linux` context. E1 used a WSL process on the same daemon.
  - Details: `environment_manifest.json`.
- Profiles, as frozen in protocol section 3 and implemented in `c1_harness/profiles.py`:
  - **R**: no CPU-limit argument, `-e GOMAXPROCS=16`.
  - **L**: `--cpu-period=100000 --cpu-quota=200000 -e GOMAXPROCS=16`.
  - Identical memory (no limit), network (default bridge), affinity (none) and workdir/argv/timeouts.
- **Enforcement evidence:**
  - Helper probes: L `cpu.max = 200000 100000`, about 2.01–2.03 CPUs, throttled. R `max 100000`, about 3.72 CPUs with 4 busy loops.
  - Both profiles: `cpuset 0-15`, `nproc 16`.
  - Go runtime probes: `GOMAXPROCS = 16` and `NumCPU = 16` in go1.10, go1.12 and go1.13 under both profiles.
  - Every executing session re-probes, and every attempt's created container is inspected before it starts; a mismatch removes it unstarted and stops all collection.
  - L attempts are charged at 2 vCPUs only when both checks hold.
- **Clock-rate finding:** the VM uptime clock runs 5.0% faster than the host monotonic clock, equally for R and L (`calibration/clock_probe.json`). In-test Go timeouts are in VM time; recorded durations are host time.

## 3. Schedule, sample and family

- `schedule.csv` (720 rows) and `schedule.json` (literal hashed strings, order, balance) were generated by `c1_harness/schedule.py` **before any calibration attempt**. They regenerate byte-identically.
- Batch A = blocks 1–5 (360 attempts); batch B = blocks 6–10 (360 attempts). Each matched block has four cells R/bad, R/ok, L/bad, L/ok, with three consecutive attempts each.
- Order balance, as observed: R before L in 31 of 60 subject-blocks for each variant.
- Primary family: K = 2 × 6 = **12**. Each category interval is at 1 − 0.05/24. K does not shrink if a comparison fails.
- Identity: `attempt_id = c1v1-measured-<subject>-bNN-<R|L>-<bad|ok>-a<k>`; `matched_block_id = c1v1-<subject>-bNN`. There is one E1-format ledger per subject/profile under `measured/`.

## 4. Commands (repository root; Python 3.10+ stdlib only)

Validated in this handoff:

- The non-executing commands below were run live.
- The refusal paths were run live.
- The execution path of `run-batch` shares `run_attempt`, the executor, probes and pre-block checks with the calibration stages, which ran live. Its measured-batch orchestration (block admission, full triples, alarms, resume, the gate-B requirement) is covered by offline tests with a scripted executor.
- `run-batch` itself was **not** executed with a valid freeze. Doing so would start measured data.

```
python -m c1_harness.cli verify-design
python -m c1_harness.cli verify-launch
python -m c1_harness.cli preflight --batch A
python -m c1_harness.cli dry-run --batch A
python -m c1_harness.cli run-batch --batch A
python -m c1_harness.cli gate-a --record
python -m c1_harness.cli run-batch --batch B
python -m c1_harness.cli annotate --stage measured
python -m c1_harness.cli analyze --out analysis
```

- `preflight` never starts a container. It verifies both freezes, the schedule regeneration, the ledger chains, the budget, the image IDs, a 16-CPU daemon, no study containers and no running containers.
- `run-batch` repeats those checks and **refuses** (exit 2) without a valid launch freeze or without budget for a matched block. It then starts with pre-block checks and a session profile probe.
- Batch B additionally requires a recorded passing `gate-a`. `gate-a` checks only integrity, validity and cost; it computes no comparative effect.
- Resuming after any interruption requires `--resume-review "<review note>"`. Recorded attempt IDs are never repeated, and a partly collected matched block stays incomplete.

Operational preconditions:

- Docker Desktop is running, and no other container is running (an unrelated running container stops collection).
- The host stays awake.
- No edits are made to frozen files; any edit breaks `verify-launch`, and the run then refuses.
- One batch session at a time.

## 5. Budget

- Adopted caps (allocated vCPU-h): preparation 8, validation 6, measured 24, analysis 2 (total 40). No transfers between stages.
- Spent before launch: **preparation 0.258, validation 1.282, measured 0, analysis 0**. Host reservation: 0.258 and 1.956 h. Measured CPU time is `null` (not instrumented).
- Projection (`cost_projection.json`; Q0 durations, smoke overheads, 2 s gap, frozen basis):
  - **Expected measured cost: 15.6 vCPU-h.** In the live-guard simulation all 60 matched blocks are admitted, with 8.4 remaining.
  - Conservative bound (every defective attempt runs to its timeout on both profiles): 104.6 vCPU-h. The guard would then stop collection after about 13 blocks.
  - Reservation-only bound: 203.1.
  - The projection is not a promise.
- Live guard: before each matched block, reserve `3*(16+2)*2*(outer+32)/3600` (2.76–4.56 vCPU-h); refuse and stop if the measured remainder cannot cover it; release after the block. Research suffixes, cleanup, gaps and probes are all charged.
- Estimated batch-A wall time: about 55 minutes, strictly sequential.

## 6. Oracles

- Cards:
  - etcd5509, etcd7492 and grpc1859 are E1's frozen cards, imported unchanged (`e1_harness/oracle.py`).
  - grpc2391, istio17860 and k8s26980 are ported from cards C-04, C-05 and C-06 in `c1_harness/cards.py`, with no strengthening. grpc2391 applies the card's one-line rule, which is stricter than the Q0 two-grep shell rule; replay shows no disagreement.
- Replay agreement:
  - 240/240 Q0 counted attempts;
  - 58/58 uncounted logs, including grpc1859's expired-certificate negatives;
  - 332/332 E1 records.
- **Unresolved oracle risks:**
  1. **k8s26980** has no positive example anywhere. Its rule rests on source review and synthetic fixtures.
  2. For every subject, specificity against generic CPU slowness under L rests on **source review only**: bounds of 5–110 s against about 100 ms throttle pauses. A witness cannot itself distinguish an extreme stall from the defect for grpc1859 (a), grpc2391 (a), istio17860 (a) or k8s26980 (a).
  3. Any mechanical focal match on an acceptable variant pauses that subject (a validity alarm) and triggers pair-validity review; it is never automatic nuisance attribution.
  4. etcd5509 signature (a) was corrected twice in Q0 (disclosed); its signature (b) has never been observed.

## 7. Calibration, controls and direct checks (validation ledgers under `calibration/`)

- **Smoke:** 24/24. Every target executed under both profiles, with profile evidence and verified cleanup on every attempt; 0 HARNESS_INVALID; 0 outer timeouts; no acceptable-variant focal. These are single observations with no frequency criterion.
- **Identity control:** 12/12 (etcd5509 `V_ok` image in both slots), all PASS. It is never revision evidence.
- **Direct policy checks:** 8/8 traces agree structurally with the reducer replay of their own ledger prefix and respect the stopping rules.
  - **Gap:** no live P3 retry-after-failure occurred, because every P3 trace passed on attempt 1. That path is covered offline only.
- **Isolation/timeout helpers:** 4/4 pass.
- Offline: 63 C1 tests and 193 E1 tests pass.
- Details: `calibration/report.json`, `readiness.md` sections 7–8.

## 8. Outputs and byte preservation

- Measured outputs are written only under this directory:
  - `measured/<subject>__<R|L>.jsonl`: E1 hash-chained ledgers with full stdout/stderr, inspect evidence, cleanup and timing.
  - `measured/annotations.jsonl`
  - `events.jsonl`: chained operational events.
  - `resources/resource_ledger.jsonl`: chained charges, reservations and agent time.
  - `analysis/`
- `*.jsonl`, `*.csv` and `*.log` are byte-preserved by the study `.gitattributes` (`-text`).
- JSON and Markdown files are hashed **LF-normalized** (CRLF → LF), because the checkout uses `core.autocrlf=true`; `c1_harness/.gitattributes` also pins LF.
- `FREEZE.sha256` uses the same normalization; `python -m c1_harness.cli verify-launch` recomputes it.
- Images stay outside Git.

## 9. What is frozen, what is not, and implementation choices

- **Frozen (listed in `FREEZE.sha256`):**
  - the 8 design files and `DESIGN_FREEZE.sha256`;
  - this record;
  - `subject_manifest.json`, `environment_manifest.json`, `schedule.csv`, `schedule.json`, `cost_projection.json`, `calibration/plan.json`;
  - `calibration/` ledgers, annotations and report, `calibration/clock_probe.json`;
  - `prep/*.json`;
  - every `c1_harness` source and test file, and `c1_harness/.gitattributes`;
  - the E1 modules C1 imports (`e1_harness/{policy,ledger,oracle,analysis}.py`).
- **Not frozen (mutable, append-only by design):** `readiness.md`, `research_record.md`, `events.jsonl`, `resources/resource_ledger.jsonl`, `measured/`, `analysis/`, `calibration/logs/`.
- **Implementation choices within the contract, not design changes:**
  - An attempt is `docker create` → inspect → `docker start -a` → inspect → `docker rm -f <id>`, which gives evidence before start. E1 used `docker run --rm`.
  - An unrelated running container stops collection.
  - Host load is recorded, not gated; the design gives no threshold.
  - CPU time is not instrumented.
  - The fixed 2 s gap is charged with each attempt.
  - The calibration plan orders cells by `c1-v1:<stage>-order:` hashes.
  - The helper timeout is 10 s.

## 10. Stop rules (live)

- **Stop all collection on:**
  - an unverified or unenforced profile;
  - a cleanup failure;
  - a daemon or create failure;
  - a leftover study container or an unrelated running container;
  - budget exhaustion;
  - a broken ledger or event chain.
- **Pause a subject on** a mechanical focal match on its acceptable variant.
- After batch A, `gate-a --record` stops any subject whose harness-invalid attempts exceed 10% of its scheduled attempts. No significance-based or effect-based stopping.
