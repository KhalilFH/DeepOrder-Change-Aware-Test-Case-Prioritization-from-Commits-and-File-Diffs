# E1 amendments and incidents (append-only)

`e1_protocol.md` stays as frozen (see `FREEZE.sha256`). Later deviations and incidents are recorded here in time order and are never edited afterwards.

## 1. 2026-09-22 — concurrent host load at the start of batch 1

- **Observed:** Batch 1 started at `2026-09-22T21:21:28Z`. A repository-wide `grep -rI` launched earlier in the same agent session was still running in the background: a disk- and CPU-heavy read over the large local dataset directories. It was stopped at about `2026-09-22T21:21:42Z`. That breaks the "one job at a time" rule for the first ~14 s of batch 1.
- **Affected attempts:** `etcd5509` block 1, `V_bad` attempt 1 (started `21:21:29.10Z`, exit 0, 0.91 s), and at least the start of `V_bad` attempt 2. No later attempt overlapped it.
- **Handling:** Nothing was re-run, replaced or removed; the attempts stay in the ledger as recorded. Analysis must also report every `etcd5509` contrast with block 1 excluded, as a sensitivity check. If excluding block 1 changes a conclusion, that conclusion is reported as dependent on this incident.
- **Cause and prevention:** The earlier search was moved to the background and never cleaned up before launch. Before each later batch starts, no other agent background task may be running, and `docker ps` must show no containers.

## 2. 2026-09-23 — direct-policy checks: allocation, cost guard and control reserve

- **Status:** approved by the researcher on 2026-09-23 as drafted. No direct check or control has run.

- **Why:** `run_logs/direct_checks_cost_check.md` (`eff3e79`) found that the 12 direct checks fit the remaining E1 cap on the observed-maximum bound and on expectation, but not on the hard timeout-plus-cleanup bound (10.08 vCPU-hours against 9.39 remaining). No frozen rule decides that case. The allocation of the checks and a reserve for the controls were also undefined. This entry settles all three before any check runs.
- **Unchanged:** `e1_protocol.md`, `manifests.json`, `run_blocks.py`, the harness files and the measured blocks 1–20. Direct checks use the frozen manifests, images, commands, condition, reset and runner (`e1-runner/1`), and `Runner.run_policy_direct` with `reserved_from=101`.

### 2.1 Allocation

- **12 checks, one per block.** etcd5509 uses blocks 101–106 and etcd7492 uses blocks 107–112. Each block holds one version and one policy. Records go to the episode's existing ledger, which stays append-only. `analysis.py --direct-blocks 101-112` keeps them out of `S` and `N`.
- **Balance:** 12 checks cannot fill the 8 episode × version × policy cells evenly, so balance is kept on every pair of factors: 3 checks per episode × version, 3 per episode × policy, and 3 per version × policy. That requires a crossed layout. In one episode, `V_bad` gets 2 P3 + 1 P1 and `V_ok` gets 1 P3 + 2 P1. The other episode gets the reverse.
- **Orientation rule:** let `a` be the first 32 bits of `SHA-256("e1:direct:allocation")`. If `a` is even, etcd5509 `V_bad` gets 2 P3; if odd, etcd7492 `V_bad` gets 2 P3. The rule does not use any E1 outcome.
- **Order rule:** within each episode, the six (version, policy) checks, listed as `V_bad`/P1 first, then `V_bad`/P3, `V_ok`/P1, `V_ok`/P3 with repeats adjacent, are shuffled by `random.Random(s).shuffle`. `s` is the first 32 bits of `SHA-256("e1:direct:order:<episode>")`. The shuffled checks take the episode's blocks in ascending order. Execution order: etcd5509 blocks 101–106, then etcd7492 blocks 107–112.
- **Per-check seed** (recorded on each attempt): first 32 bits of `SHA-256("e1:<episode>:block:<n>")`, the same rule as the measured blocks.
- **Result.** The rules above were written before this was computed. `a = 1185576341` is odd, so etcd7492 `V_bad` gets 2 P3. Order seeds: etcd5509 `3728254925`, etcd7492 `1987856515`.

  | Block | Episode | Version | Policy | Seed |
  |---:|---|---|---|---:|
  | 101 | etcd5509 | `V_ok` | P3 | 3731262331 |
  | 102 | etcd5509 | `V_bad` | P3 | 1021860734 |
  | 103 | etcd5509 | `V_bad` | P1 | 953258952 |
  | 104 | etcd5509 | `V_ok` | P1 | 3833310602 |
  | 105 | etcd5509 | `V_ok` | P3 | 903614685 |
  | 106 | etcd5509 | `V_bad` | P1 | 124962926 |
  | 107 | etcd7492 | `V_ok` | P3 | 2234491992 |
  | 108 | etcd7492 | `V_bad` | P3 | 3789747153 |
  | 109 | etcd7492 | `V_ok` | P1 | 2636512552 |
  | 110 | etcd7492 | `V_ok` | P1 | 87457551 |
  | 111 | etcd7492 | `V_bad` | P1 | 1997272447 |
  | 112 | etcd7492 | `V_bad` | P3 | 2252439627 |

- **Consequence of the draw.** Only one check (block 102) runs P3 on etcd5509 `V_bad`, the version that fails often in Q0 (16/20). It is the check most likely to exercise P3's "fail, then retry, then stop at a pass" path. The two P3 checks on etcd7492 `V_bad` (2/20 in Q0) will probably pass on attempt 1. Any change to the rule after seeing this draw must be recorded as having been made after the draw.
- **Plan file:** the resulting 12 rows (block, episode, version, policy, seed) are written to `e1/direct_checks_plan.json` before any check runs and hashed below. The ledger has no policy field, so this file is the authoritative record of which policy each block executed. Seeds and rows are not re-drawn.

### 2.2 Cost guard

- **Accounting:** conservative basis, 16 vCPUs. The E1 cost so far is fixed at **10.61 vCPU-hours** (measured blocks, span basis, `batch2_check.md`). Each direct-check attempt is charged `16 × (elapsed_s + 2.04 s) / 3600`. The 2.04 s is the maximum within-run gap between attempts.
- **Guard, applied before each check** (never inside one, so no policy execution is cut short): let `W` be the check's hard bound, `n × (timeout_s + 30 + 2.04)` s × 16 / 3600, with `n = 1` for P1 and `n = 3` for P3. That is 0.41 / 1.23 vCPU-hours for etcd5509 P1/P3 and 0.43 / 1.29 for etcd7492. If the cost so far plus `W` exceeds the **line of 17.0 vCPU-hours**, the check does not start.
- **A guard stop is a resource stop.** It is recorded here, the remaining checks are not run, and the allocation is not rebalanced. Direct checks already run are kept and analysed.
- **Projected cost for this allocation:** 2.73 vCPU-hours on the observed-maximum bound (the cost check file's worst balanced placement was 3.92), 0.92 expected at Q0 rates, and 10.08 at the hard bound. The guard binds only if attempts start running to the runner timeout, which none of the 240 measured attempts did. If every attempt did hit the hard bound, the first 7 checks would start (cumulative 16.81) and the guard would stop before block 108.

### 2.3 Control reserve

- **Reserve: 3.0 vCPU-hours**, from 17.0 to 20.0. It covers the identity/no-change control, the deterministic-failure control and metered implementation verification (for example `selftest.py` and the new driver's checks).
- The direct checks may not use it. Neither control has a design or an oracle card yet. Each gets its own cost check against this reserve when it is designed.
- Reserve left unused at the end of E1 is not spent on extra sampling.

### 2.4 Execution and stop rules

- **Before starting:** `docker info` succeeds, `docker ps -a` lists no containers, and no other agent background task is running (AMENDMENTS §1). The result and a UTC timestamp are written to `run_logs/direct_start_utc.txt`.
- **Driver:** a new script `e1/run_direct.py`, hashed below. `run_blocks.py` stays frozen. The driver reads `direct_checks_plan.json`, applies the guard, calls `run_policy_direct` and writes `run_logs/direct_101-112.log`. The log lists, per check, the intended policy, executed exit statuses, reducer decision and cumulative cost.
- **Stop at the first structural mismatch**, without retrying:
  - an executed prefix that is inconsistent with the intended policy's stopping rule (P1 ran more than one attempt; P3 continued after exit 0, or stopped before 3 attempts without exit 0);
  - a container from the check still present in `docker ps -a` afterwards;
  - `verify_chain` failing on the episode ledger.

  A stop is recorded here. Nothing is re-run or replaced.
- **Printed output** is exit statuses and structure only. The direct checks are not compared with the measured-block contrasts while they run.
- **After the run:** `run_logs/direct_check.md` gives the structural and cost results in the same format as the batch checks.

### 2.5 Hashes at approval

| File | SHA-256 |
|---|---|
| `e1/direct_checks_plan.json` | `5e74dc813f665fb8fa4c6a27e7570d3c55c993a6eb25adbda0fe610db4768883` |

- `direct_checks_plan.json` was generated from the rules in 2.1 and checked against the table there before hashing.
- `run_direct.py` does not exist yet. Its hash and its test results will be recorded in a later entry here before any direct check runs. It must refuse to start unless `direct_checks_plan.json` hashes to the value above. No direct check may run under this entry alone.
