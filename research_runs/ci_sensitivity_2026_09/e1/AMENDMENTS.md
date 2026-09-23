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

## 3. 2026-09-23 — direct-check driver recorded (completes section 2.5)

- **Status:** records the driver that section 2.5 requires before any direct check runs. No direct check or control has run.

| File | SHA-256 |
|---|---|
| `e1/run_direct.py` | `59e4f9b4c2d06875ecad2a5d0e751a69414b3e24808b08b5d72b911a98fd93cd` |
| `e1_harness/tests/test_run_direct.py` | `eb31d22ebffc5c3360e5911f5ffd8d7f7637907dceb8a1c70985cafb825d48a3` |
| `e1/direct_checks_plan.json` (unchanged from 2.5) | `5e74dc813f665fb8fa4c6a27e7570d3c55c993a6eb25adbda0fe610db4768883` |

- **Verification:**
  - 22 driver tests pass. The full unit suite is 172 tests, all OK (150 at the E1 freeze plus these 22).
  - Four deliberate breakages were each caught by the suite: disabling the guard, the "continued after exit 0" rule, the leftover-container check and the prefix rule for resuming. The file was restored byte for byte afterwards.
  - A read-only `preflight` against the real Docker host on 2026-09-23 was clean: `docker info` succeeded, all four frozen image IDs were present and `docker ps -a` was empty.
  - The E1 freeze still verifies.
- **What the driver enforces, as implemented:**
  - **Refuses to start** unless the plan and both manifests hash to their frozen values, all four images are present, `docker info` succeeds and `docker ps -a` is empty.
  - **Runs** the 12 checks in plan order through `run_policy_direct` with `reserved_from=101`, applying the section 2.2 guard before each check.
  - **Stops**, never retrying, when `docker info` fails before a check (exit 2); on a guard stop (exit 3); or on a structural mismatch (exit 4).
  - **Structural mismatch** covers the section 2.4 conditions, plus two further ones: a recorded version other than the planned one, and ledger records that disagree with the trace the runner returned.
  - **Resume:** a stopped run resumes only from the next unrecorded check, following `e1_protocol.md`'s rule for stopped runs. It refuses to resume if the recorded checks are not a prefix of the plan order, if any recorded check is structurally unsound, or if a ledger holds a direct-range block that is not in the plan. After a structural mismatch, this refusal means resuming needs a recorded decision here.
  - **Files written** (append mode): `run_logs/direct_start_utc.txt`, one line per start with the preflight result; `run_logs/direct_101-112.log`, a header line, one line per check and the final status; and `run_logs/direct_end_utc.txt`, the end time and exit code, written even after a Python-level error.
- **Not checkable by the driver:** that no other agent background task is running (AMENDMENTS §1). The operator must confirm it and record it in `run_logs/` before starting. No such record exists for batch 2 (`batch2_check.md`).
- **Known disagreement with the frozen `analysis.py`:**
  - Section 2.4 lists no rule for a P3 attempt with no exit status (a timeout or a run that never started). The runner treats it as not a pass and continues, so the driver accepts such a trace as sound. The reducer rates the check `INDETERMINATE`.
  - `analysis.direct_checks` treats any such attempt before the last as inconsistent with P3, so it reports `structural_mismatch`.
  - `analysis.py` is hash-frozen and is not changed. If such a trace occurs, the analysis report will show a mismatch that the driver did not stop on, and the report must cite this entry. It has not occurred: no direct check has run.
- **From here:** direct checks may run under sections 2 and 3, once the pre-start conditions above are met and recorded.

## 4. 2026-09-23 — line endings of the hash-frozen harness files

- **Status:** records a storage fix that the researcher approved on 2026-09-23. No file content, committed blob or recorded hash changes. No E1 experiment was run for this entry.
- **Unchanged:** `e1_protocol.md`, sections 1–3 above, and the content and committed blobs of every `e1_harness/` file.

### 4.1 Finding

- **Observed:** The machine has `core.autocrlf=true`, and `e1_harness/` had no `.gitattributes`. So Git stores these files with LF endings (the blob) and checks them out with CRLF endings. `git ls-files --eol` showed `i/lf w/crlf` for all six files in a fresh checkout at `4517834`.
- **The recorded hashes mix both forms.** Every blob is pure LF. The CRLF form is the blob with each LF replaced by CRLF, so the text is identical.

  | File | Recorded in | Recorded hash is | LF form (Git blob) | CRLF form |
  |---|---|---|---|---|
  | `e1_harness/runner.py` | `e1_protocol.md` | **CRLF** | `be3c39d816e609c2ead8108145e8acb026aa91acd78fc28e1c0338e8bbd255aa` | `2b831f91017679bbb913938a05333aa6ecbbda3bbeaecafb26ff3fc6c2ff6be7` |
  | `e1_harness/ledger.py` | `e1_protocol.md` | LF | `9e51b801dba5f034cc1818192d86314e41f93343a4efe6eaa3053cbf8f8a34f3` | `b89123457e8f38e6d41f4d0f834f2d78a296201cda073e095a4c2ab619a685b5` |
  | `e1_harness/policy.py` | `e1_protocol.md` | LF | `b5a2e4ba6638a7a6ae565b0962b47c0af9bf07466bfa0473773b240918ff7da4` | `cb4b31e95b99bc3c5adc4cf3df54b6e2ad9885f011fd69c15df2401bbfa78916` |
  | `e1_harness/oracle.py` | `e1_protocol.md` | LF | `20a494f00b87d52a035b8a1d31b40d31ca46d9037854a5b0caafcf04b20a89a0` | `6f1b5f9bea748613032b285a3960811794305a22e36aff85381299d81418970e` |
  | `e1_harness/analysis.py` | `e1_protocol.md` | LF | `bc27c7de7ebce6bd42c56749c134b76945f13c615bf0f0533336f5528ee1a841` | `4280d660a789feed8bb84bed1e80b58e993fd1f40c6520d31cc2aa9befec23f6` |
  | `e1_harness/tests/test_run_direct.py` | section 3 | LF | `eb31d22ebffc5c3360e5911f5ffd8d7f7637907dceb8a1c70985cafb825d48a3` | `5a45697cd985dd0bd83438e988b52e4136aa8b7538ffa551c2b5cbddeee2fc61` |

- **Observed:** `runner.py`'s blob is the same at the freeze commit `fc3fb2d` and at `4517834` (`be3c39d8…`). In the main checkout, `runner.py` is CRLF and hashes to the recorded `2b831f91…`, while the other five files are LF there and match their recorded hashes. In a fresh checkout on this machine, all six are CRLF, so the five LF hashes failed and only `runner.py` matched. On a checkout without autocrlf (Linux, CI), all six are LF, so `runner.py` fails and the other five match.
- **Inference:** Each recorded hash was taken from whatever the working copy happened to hold at the time, not from a fixed byte form. The content of `runner.py` is what was frozen. Python reads CRLF and LF source identically, so the difference does not change harness behaviour.
- **Nothing in the code checks these hashes.** `run_blocks.py` and `run_direct.py` verify manifest and plan hashes only, so no run was affected.

### 4.2 Fix

- Following commit `636a99e`, a new `e1_harness/.gitattributes` marks exactly these six files `-text`. Git now stores and checks them out byte-for-byte, which is LF, as already committed. No blob was re-added or renormalised.
- `runner.py` stays LF. Storing its CRLF form would change a committed blob. Its recorded hash is therefore defined as the hash of its CRLF form, and it is verified as below.
- **Existing checkouts** keep their old working-copy bytes until the files are checked out again. After this change, a CRLF `runner.py` in such a checkout shows as modified. `git checkout -- e1_harness/runner.py` restores the LF form.

### 4.3 How to verify

Run these from the repository root at this entry's commit or any later one. They behave the same on every platform and with any `core.autocrlf` setting.

- **Five LF hashes** (`ledger.py`, `policy.py`, `oracle.py`, `analysis.py` and `tests/test_run_direct.py`). The working copy and the blob are the same bytes:
  - `sha256sum e1_harness/ledger.py` (the same for the other four), or
  - `git show HEAD:e1_harness/ledger.py | sha256sum`.
- **`runner.py`, recorded CRLF hash `2b831f91…`.** Convert the blob to CRLF, then hash it:
  - `git show HEAD:e1_harness/runner.py | python -c "import sys,hashlib;print(hashlib.sha256(sys.stdin.buffer.read().replace(b'\n',b'\r\n')).hexdigest())"`
  - The blob contains no `\r`, so this conversion is exact.
- **`runner.py`, LF form `be3c39d8…`** (not a recorded freeze value; it identifies the same content):
  - `sha256sum e1_harness/runner.py`, or
  - `git show HEAD:e1_harness/runner.py | sha256sum`.
- **Check that the fix is in effect:** `git ls-files --eol e1_harness/runner.py` shows `i/lf w/lf attr/-text`.
- **Result on 2026-09-23:** after re-checkout at `4517834` with the new `.gitattributes`, all six files were `i/lf w/lf attr/-text`. All five LF hashes and the `runner.py` CRLF conversion matched their recorded values.

## 5. 2026-09-23 — direct-policy checks run (blocks 101–112)

- **Status:** records the run that sections 2 and 3 authorised. All 12 direct checks ran to completion. No control has run, no attempt has been classified into an oracle category, and no measured-block contrast was computed.
- **Unchanged:** `e1_protocol.md`, the allocation in 2.1 and `direct_checks_plan.json`, and measured blocks 1–20 (120 records per episode, not rewritten).

### 5.1 Run

- **Pre-start:** `run_logs/direct_prestart_check.md` records the conditions at 08:12:07Z. `docker ps -a` was empty, the host was otherwise idle, this operator had no background task running and `FREEZE.sha256` passed at HEAD `4517834`. That file is the operator confirmation that section 3 says the driver cannot make.
- **Code actually executed:** `run_direct.py` at `59e4f9b4…` (section 3) and `runner.py` at `2b831f91…`. That is the CRLF working copy in the checkout where the run happened (section 4). `ledger.py`, `policy.py`, `oracle.py` and `analysis.py` were at their LF hashes from `e1_protocol.md`. None of these files had been modified since before the run started. Records carry runner `e1-runner/1` and the frozen manifest hashes.
- **Window:** 08:12:34Z (`direct_start_utc.txt`, `docker_info=ok containers=0`) to 08:16:35Z (`direct_end_utc.txt`, `exit=0`).
- **Outcome:** driver status `DONE`, exit 0. There was no `docker info` stop, no guard stop and no structural mismatch. After the run, `docker ps -a` listed no containers.

| Block | Episode | Version | Policy | Executed exit statuses | Reducer decision |
|---:|---|---|---|---|---|
| 101 | etcd5509 | `V_ok` | P3 | `[0]` | ACCEPT |
| 102 | etcd5509 | `V_bad` | P3 | `[2, 2, 2]` | BLOCK |
| 103 | etcd5509 | `V_bad` | P1 | `[2]` | BLOCK |
| 104 | etcd5509 | `V_ok` | P1 | `[0]` | ACCEPT |
| 105 | etcd5509 | `V_ok` | P3 | `[0]` | ACCEPT |
| 106 | etcd5509 | `V_bad` | P1 | `[2]` | BLOCK |
| 107 | etcd7492 | `V_ok` | P3 | `[0]` | ACCEPT |
| 108 | etcd7492 | `V_bad` | P3 | `[0]` | ACCEPT |
| 109 | etcd7492 | `V_ok` | P1 | `[0]` | ACCEPT |
| 110 | etcd7492 | `V_ok` | P1 | `[0]` | ACCEPT |
| 111 | etcd7492 | `V_bad` | P1 | `[0]` | ACCEPT |
| 112 | etcd7492 | `V_bad` | P3 | `[0]` | ACCEPT |

Exit statuses and reducer decisions are structural outputs, not oracle categories.

### 5.2 Independent re-check

This check was made on 2026-09-23 from the committed ledgers and `direct_checks_plan.json`, using `ledger.verify_chain` and `ledger.read_records`. It did not use the driver log.

- **Ledgers:** both are strict appends to their committed versions at `4517834`. The committed bytes are a byte-identical prefix. etcd5509 gained 8 records (seq 121–128) and etcd7492 gained 6 (seq 121–126). `verify_chain` passes on both. There are no records outside blocks 1–20 and 101–112.
- **Every record matches the plan:** planned episode, version and seed. Attempt numbers start at 1 with no gaps. `timed_out` is false everywhere, and there is one manifest hash per episode.
- **Timing:** there are 14 attempts. None overlap, and each runs to completion before the next starts. The first starts at 08:12:34.79Z and the last ends at 08:16:35.20Z.
- **Cost:** a 240.4 s span is 1.068 vCPU-hours on the conservative 16-vCPU basis. The attempt-sum is 233.2 s, or 1.037 vCPU-hours, and 1.164 on the section 2.2 guard basis. All match `run_logs/direct_check.md`.
- **Stop rules:** none of the section 2.4 rules triggered.
  - The section 3 known disagreement did not arise: every attempt has an exit status and none timed out. `analysis.direct_checks` should therefore report no `structural_mismatch` that the driver did not also report.
  - If it does report one, that is a new discrepancy and must be recorded here.

### 5.3 Incidents and limits

- **Host load:** no incident is recorded.
  - The section 4 session, which the pre-start file mentions, created its worktree at 08:18:03Z, after the run ended, so it could not have overlapped the run.
  - Other activity on the host is evidenced only by the pre-start sample. Nothing was monitored during the run.
- **Not exercised in real execution:** P3 accepting a pass after an earlier failure, for example `[2, 0]` or `[2, 2, 0]`. That is the retry path that acceptance depends on.
  - Block 102, the one P3 check on etcd5509 `V_bad`, failed all three attempts. Section 2.1 had named it as the check most likely to exercise this path.
  - The path is covered only by unit tests. Section 2.1 froze the allocation, so no check is added to cover it.

### 5.4 Cost position

- **E1 conservative total:** 10.61 + 1.068 = **11.68 vCPU-hours** on the span basis, or 11.77 on the guard basis.
- **Headroom:** 5.23 vCPU-hours remain below the 17.0 line on the guard basis.
- **Control reserve:** the 3.0 vCPU-hours (17.0–20.0) from section 2.3 is untouched.

### 5.5 Hashes of the run records

| File | SHA-256 |
|---|---|
| `e1/etcd5509/attempts.jsonl` (chain head seq 128 `f74bfa8a0c9778bcc2eeb39819934ff0f0c19c7492e88b3cfe26c7d25d0de7f6`) | `7b6d771d2c94bb9fe4ce414bdb2d63c251dd0530b3bf45ba9c54accef4d01b30` |
| `e1/etcd7492/attempts.jsonl` (chain head seq 126 `9ab65ad0e083376965c7a8bd0881964914407af6c7d38d0f08360675d78314d6`) | `de92e3b71857e6fdb04dc4a7199c656f7be5c8419a1aa65dcd0fa39fd459e8da` |
| `e1/run_logs/direct_prestart_check.md` | `a96dbf2829fab241bebd42451c8c4fbc710d9f70b8437bd362b87ba054013008` |
| `e1/run_logs/direct_start_utc.txt` | `09a5db3992a737f09b12ad00e6262c611ef1b17f9d35c25aa05c7697f95fdef0` |
| `e1/run_logs/direct_101-112.log` | `1ed77058137e4ccedbb98cbaf3dc27950e95bf259ad7ea022cfaa79047a70e4d` |
| `e1/run_logs/direct_end_utc.txt` | `61fa312fa741059bb03b37df445aa89befd7255bb3c798dd070bac79ce9a69de` |
| `e1/run_logs/direct_check.md` | `5e499d61e4ceb0810e7f371c6dc79176eb5fa7dbe8540da634289ab8f196a53b` |

- All seven files live under `e1/`, whose `.gitattributes` is `* -text`, so each hash verifies from any checkout with `sha256sum`.
- The ledger file hashes are a snapshot at this entry. Later appends change them, but the chain heads above stay in the chain.

- **From here:** the direct checks are complete and are not re-run or extended. Per section 2.3, the identity/no-change control and the deterministic-failure control each need a design, an oracle card and their own cost check against the reserve before they run.
