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

## 6. 2026-09-23 — oracle classification and analysis (plan step 5)

- **Status:** the researcher approved step 5 on 2026-09-23. All 40 measured blocks are complete, which is the condition `e1_protocol.md` sets. No container ran, and no vCPU cost was charged.
- **Order, disclosed:**
  - Step 5 ran **before step 4**. Neither control has been designed or run.
  - Oracle classification was finished and reviewed before any analysis output existed (plan §6, "Oracle").
- **Unchanged:** the ledgers, `e1_protocol.md`, all hash-frozen harness files (hashes checked before running) and sections 1–5.

### 6.1 Oracle classification

- **Tool:** `oracle.py` (`e1-oracle/1`, `20a494f0…`), run once per episode ledger. It classified all 254 records: measured blocks 1–20 and direct checks 101–112.
- **Every annotation is mechanical.** No record came out `UNRESOLVED` or `HARNESS_INVALID`, so there was nothing to adjudicate and no override exists.
- **Signatures:** every nonzero exit matched its episode's frozen signature `a`, and every exit 0 is `PASS`.

| Episode | Blocks | `V_bad` | `V_ok` |
|---|---|---|---|
| etcd5509 | measured 1–20 | 47 `FOCAL_DEFECT_WITNESS`, 13 `PASS` | 60 `PASS` |
| etcd5509 | direct 101–106 | 5 `FOCAL_DEFECT_WITNESS` | 3 `PASS` |
| etcd7492 | measured 1–20 | 4 `FOCAL_DEFECT_WITNESS`, 56 `PASS` | 60 `PASS` |
| etcd7492 | direct 107–112 | 3 `PASS` | 3 `PASS` |

### 6.2 Analysis settings

These were fixed before any analysis output existed.

- **Tool:** `analysis.py` (`e1-analysis/1`, `bc27c7de…`), run once per episode ledger with:
  - `--blocks 1-20 --batch 1-10 --batch 11-20` (the batches from `e1_protocol.md`);
  - `--direct-blocks 101-112` (a run skips direct blocks with no records for its episode);
  - `--allocated-vcpus 16` (the conservative basis; the Q0-convention figures are those values divided by 16);
  - the default `--invalid-threshold 0.10` for E1.
- **Family alpha, a choice not fixed by earlier records:** `--family-alpha 0.025` per run.
  - Plan §4's Bonferroni rule covers every contrast across all episodes.
  - `analysis.py` takes one ledger per run and corrects only over the contrasts in that run. At the default 0.05, each episode would be its own two-contrast family (0.05/4 per interval).
  - 0.025 per run gives 0.05/8 per interval, the plan's rule applied to E1's four contrasts (`L` and `R` for two episodes).
  - Each report header says "over 2 contrasts (each side at 0.99375)". The 0.99375 (= 1 − 0.05/8) is the joint setting. The "2 contrasts" is only the per-run count.
- **Section 1 sensitivity run:** etcd5509 again with `--blocks 2-20 --batch 2-10 --batch 11-20`, all other settings the same.
- **Outputs:** `e1/analysis/<run>/report.md`, `summary.json` and `policy_decisions.csv` for the runs `etcd5509`, `etcd7492` and `etcd5509_excl_block1`. A second run of each produced byte-identical files.

### 6.3 Results

- **Observed, both episodes:**
  - 20/20 measured blocks complete; 0 invalid (threshold 0.10); 0 undetermined blocks, so the best and worst assignments equal the complete-case value.
  - No `V_ok` attempt failed, so `N = 0` under every policy and `R = 0`.
  - `P3-retain` equals `P3` on every figure.
  - The direct checks gave 6 traces per episode and 0 structural mismatches, as section 5.2 expected.

| Episode | S(P1) | S(P3) | L = S(P1) − S(P3) | Simultaneous interval | Discordant +/− | `ACCEPT_WITH_PRIOR_FAILURE` | Margin 0.10 |
|---|---|---|---|---|---|---|---|
| etcd5509 | 12/20 = 0.600 | 9/20 = 0.450 | 0.150 | [−0.236, +0.468] | 3/0 | 3 | interval contains margin |
| etcd7492 | 2/20 = 0.100 | 0/20 = 0.000 | 0.100 | [−0.246, +0.406] | 2/0 | 2 | interval contains margin |
| etcd5509 without block 1 (§1) | 12/19 = 0.632 | 9/19 = 0.474 | 0.158 | [−0.246, +0.487] | 3/0 | 3 | interval contains margin |

- **`R = N(P1) − N(P3)`:** 0.000 for both episodes, with interval [−0.251, +0.251]. Margin 0.05: the interval contains the margin.
- **Focal witnesses that P3 ignored:**
  - etcd5509: 5 witnesses in 3 blocks, where a prefix failure was followed by an accepting pass.
  - etcd7492: 2 witnesses in 2 blocks.
- **By batch, `S(P1)` / `S(P3)`:**
  - etcd5509: 0.700 / 0.500 in blocks 1–10 and 0.500 / 0.400 in blocks 11–20.
  - etcd7492: 0.100 / 0.000 in both batches.
- **Prefix cost on `V_bad`, measured blocks (conservative):**
  - etcd5509: P1 20 attempts, 527 s, 2.34 vCPU-h. P3 43 attempts, 1399 s, 6.22 vCPU-h.
  - etcd7492: P1 20 attempts, 108 s, 0.48 vCPU-h. P3 22 attempts, 110 s, 0.49 vCPU-h.
- **Hand check:** from the annotations, `S(P1)`, `S(P3)`, the discordant counts and the zero `V_ok` failures were recomputed independently of `analysis.py`. They match for all three runs.
- **Section 1 sensitivity:** excluding block 1 changes etcd5509's `L` from 0.150 to 0.158. Block 1's `V_bad` prefix passed on its first attempt. Nothing changes in the pattern of which intervals contain the margin. So no etcd5509 conclusion depends on the section 1 incident.

### 6.4 Interpretation

This is labelled interpretation, not result.

- **Retry loss.** On both episodes, every discordant block goes the same way: P1 blocked on a focal witness and P3 accepted after a retry. `L` estimates are 0.150 and 0.100. With 20 blocks, both simultaneous intervals include 0 and the 0.10 margin. E1 therefore neither shows nor rules out a material retry loss. This is calibration, as plan §6 intends.
- **Noise reduction is not measured.** No verified nuisance occurred on either `V_ok`, so `N` and `R` are zero by construction. The noise-reduction side of RQ1 is not established for either episode. The report flags this for both.
- **Plan §6 "Continue" criteria, as far as step 5 can check them:**
  - the oracle and the policy interpretation work for both episodes;
  - the invalid fraction is 0, well under 0.10;
  - every outcome and intermediate failure traces to a hashed ledger record.
  - Not assessed here: whether the projected E2 cost fits its cap, and the attribution check that step 4 provides.

### 6.5 Limits

- **Controls:** these results were read before the step 4 controls. If a control later shows an attribution or final-status problem, it must be recorded here, and these results re-read under that entry. The results are not edited.
- **Labels and scope:**
  - All labels are mechanical and there was one researcher (plan §6).
  - Both episodes come from etcd (`e1_protocol.md`).
  - The E1 data are for development only and are not E2 evidence (plan §6, Budget).
- **Coverage assumption:** the intervals assume independent reset blocks, not independent retries.

### 6.6 Hashes

| File | SHA-256 |
|---|---|
| `e1/etcd5509/annotations.jsonl` | `304b110f208b22c59965c9e200acf5ba729a52de174c8fbd427282b802d9a5b9` |
| `e1/etcd7492/annotations.jsonl` | `e9a625d48a7076be621b56f52bbaa0c4001efc33865e33bf48b039d86ed40aac` |
| `e1/analysis/etcd5509/report.md` | `77736a921e2e7ecbf4766ac9205a8e128825629b9e8c5037c8d912d849999b10` |
| `e1/analysis/etcd5509/summary.json` | `9685c45045a2d6c6ad74c128f2be94a87a4de55015be3df47ae52ff0a0baa070` |
| `e1/analysis/etcd5509/policy_decisions.csv` | `1cc756f8f1030a6a096c8eb94acf4894d867115563955ebc0722a285b23c15b4` |
| `e1/analysis/etcd7492/report.md` | `c86c7110333cd71b62efecf0a67fcdb520fdc87d57e8997665cdb5513c789fa6` |
| `e1/analysis/etcd7492/summary.json` | `b79bb87da9ae9d37cda012eee548f5fc33dafc93b89d9ab1bd834b10aa4d6feb` |
| `e1/analysis/etcd7492/policy_decisions.csv` | `f5f4cdde098b4b605e40f752978c9e8236a886bcc6d36f4568f91ea376d46f01` |
| `e1/analysis/etcd5509_excl_block1/report.md` | `c7c1a53a8d4f6e163579ce842bb23c1d57fb2556f328800e6231c337e7426fb5` |
| `e1/analysis/etcd5509_excl_block1/summary.json` | `740d6600cbe4eb4862248df7c46f7004e9746a182e6c308733cd76878b56fef8` |
| `e1/analysis/etcd5509_excl_block1/policy_decisions.csv` | `20fb562c062ab88dfb84c75f17c41e935c386181e79b087c9aead3bf18418ee8` |

- **Byte-for-byte storage:** everything is under `e1/`, whose `.gitattributes` is `* -text`. The CSVs keep the `\r\n` row endings that Python's `csv` module writes.
- **To reproduce,** run from the repository root. `oracle.py` refuses to overwrite a differing file, and each command should reproduce the hashes above:
  - `python e1_harness/oracle.py --ledger research_runs/ci_sensitivity_2026_09/e1/<episode>/attempts.jsonl --out <path>`
  - `python e1_harness/analysis.py --ledger …/<episode>/attempts.jsonl --annotations …/<episode>/annotations.jsonl --blocks 1-20 --batch 1-10 --batch 11-20 --direct-blocks 101-112 --allocated-vcpus 16 --family-alpha 0.025 --out <dir>`
- **From here:** step 4, the controls, is the remaining E1 work. Each control needs a design, an oracle card and a cost check against the 3.0 vCPU-hour reserve (section 2.3). After that comes the E1 "Continue" decision, including the projected E2 cost.

## 7. 2026-09-23 — step-4 controls: design, driver and freeze

- **Status:** the researcher approved the design on 2026-09-23 as drafted. B2 (see 7.4) is deferred.
  - No control attempt has run.
  - The controls may run only once the section 7.6 pre-start conditions are met and recorded.
  - A qualification session may be using Docker on this host at the same time. Its runs and the control run must not overlap (section 1).
- **Unchanged:**
  - `e1_protocol.md`, every hash-frozen harness file and every E1 ledger;
  - `run_blocks.py`, `run_direct.py`, and the section 6 results;
  - `oracle.py`. No oracle card was added; each control reuses an existing card, so its hash is unchanged.
- **Ordering, already disclosed in section 6:** the controls run after the E1 analysis. If a control shows an attribution or final-status problem, it is recorded here and section 6 is re-read under that entry, not edited.

### 7.1 What the frozen records fix

- **The controls themselves:** plan §6 step 4 and `protocol.md` call for "a small identity/no-change and deterministic-failure control set to verify attribution and final status". Costs are charged, the controls add no episodes, and stable or synthetic controls are labelled separately.
- **Budget:** section 2.3's 3.0 vCPU-hour reserve (17.0–20.0) covers the controls and metered implementation verification. Unused reserve is not spent on extra sampling.

### 7.2 How the controls are kept apart from E1

- **Cards:** oracle cards live in the frozen `oracle.py`, and it refuses an episode without one. Each control therefore runs the target test of an existing frozen card, under that card's episode key (`etcd5509`, `etcd7492`, `grpc1859`).
- **Separation:**
  - own ledgers at `e1/controls/<control>/attempts.jsonl`;
  - blocks 201–213, outside 1–20 and 101–112;
  - a distinct `manifest_sha256` on every record.

  Control records never enter the E1 ledgers or the section 6 analysis.
- **Driver:** `e1/run_controls.py` is new. It calls the frozen `Runner.run_block` (three attempts on each version role, role order from the seed) and imports, without changing, `run_direct.py`'s Docker preflight and cost functions.

### 7.3 The two controls

**A — identity/no-change** (`identity_etcd5509`, `identity_etcd7492`; blocks 201–205 each; 60 attempts)

- **Manifest:** each episode's frozen manifest with **both** version roles on its frozen `V_ok` image. The argv, workdir, runner timeout and condition are unchanged. The driver re-derives this from `manifests.json` and refuses anything else.
- **Pre-declared expectation:** every attempt `PASS`; P1, P3 and P3-retain ACCEPT on both roles; `S = N = 0`; no focal witness on either role.
- **What it checks:** with no revision change, nothing in the pipeline (role labels, randomised order, manifest handling, oracle) creates a difference or an attribution. Any failure is recorded and adjudicated as a finding.
- **Label:** stable control, not synthetic.

**B — deterministic failure** (`detfail_grpc1859`; blocks 211–213; 18 attempts)

- **Source:** `task5_grpc1859_restoration.md` Step 3. The subject's committed test certificates expired in 2024–2025. In every TLS environment, the test therefore blocks in `grpc.Dial` until the test timeout, identically on both versions. The failure is real, not forced, but it is caused by the environment, not a revision.
- **Manifest:** the Q0 grpc1859 command (`task5_artifacts/grpc1859/run/attempt.sh`) with two declared changes:
  - `-only_env tcp-tls-v1-balancer`, the first TLS entry in upstream `allEnv` order. This was read from `end2end_test.go` inside the image (line 404: `tcpClearEnv, tcpTLSEnv, …`) and was not chosen by any observed outcome;
  - `-test.timeout 10s` with a 25 s runner timeout, to bound cost.
- **Images, pinned by ID:** the Q0 record gave tags only.
  - `grpc1859-bug` = `sha256:6b890fa74bedace16bf8049b8a1968f7928a596312210bc17a9ba86b96e03a03` (created 2026-09-22T17:50:11Z)
  - `grpc1859-fix` = `sha256:3b72ed206066bb8ea69f5dfbf0271c753f25e832797069d6abc560ec6c4e9034` (created 17:50:33Z)
  - **Observed:** both were created inside the Task 5 window (17:44:33–18:00:14Z). The `end2end_test.go` copied from each has Git blob `6a583182170323ec5b23d760d926c92d3816be18`, the test blob recorded by Task 5.
  - **Inference:** these are the Q0 images.
- **Pre-declared expectations:**
  - **Final status:** every attempt exits nonzero. P1 BLOCKs, and P3 BLOCKs after three attempts, on both versions.
  - **Mechanical oracle:** the frozen `grpc1859` card labels every attempt `UNRESOLVED` (a test timeout matching no signature), never `FOCAL_DEFECT_WITNESS`.
  - **Analysis:** no block counts toward `S`. Blocks are undetermined or invalid, not focal-supported.
- **Pre-declared adjudication,** fixed here before any control attempt:
  - An attempt is overridden to `HARNESS_INVALID` if and only if its goroutine dump shows the test goroutine blocked under `grpc.Dial` → `WaitForStateChange` with no `quotaPool.get` frame.
  - Evidence: the expired-certificate finding above.
  - Any other outcome stays as the oracle labelled it and is reported.
- **What it checks:** a deterministic failure is blocked and cannot be hidden by retry, and a failure identical on both versions is not attributed to the revision.
- **Label:** environment-caused deterministic failure. It is not a revision-attributable defect.

### 7.4 Deferred and rejected

- **B2 is deferred:** a revision-attributable deterministic defect from a GoReal `SCREENED_DETERMINISTIC_LEAD` (grpc_649/795/1275/1424, cockroach_1055).
  - It would give the stronger check: `S(P1) = S(P3) = 1`, so `L = 0`.
  - It needs a restoration, a control roster slot, Docker time and human hours before the day-10 gate.
  - It is pursued only if the qualification work turns one up. If so, it gets its own entry.
- **Rejected:** a synthetic harness failure, such as a bad flag. It produces no `=== RUN` line, so it is only `HARNESS_INVALID`, and it would check exit propagation only.

### 7.5 Cost and guard

- **Accounting:** as in section 2.2, 16 vCPUs and `elapsed_s + 2.04 s` per attempt. The cost before the controls is 11.77 vCPU-hours on that basis, computed at run time from the E1 ledgers.
- **Projection:**
  - A: about 0.72 vCPU-hours at measured `V_ok` durations (0.75 at their maximum).
  - B: about 1.00.
  - Total: about 1.72, bringing E1 to about 13.49.
- **Guard, applied before each block** (never inside one):
  - a block does not start if the cost so far plus its hard bound exceeds **20.0**;
  - the hard bound is 6 × (runner timeout + 30 + 2.04) s × 16 / 3600: 2.45 vCPU-hours for identity_etcd5509 blocks, 2.59 for identity_etcd7492 and 1.52 for detfail_grpc1859;
  - a guard stop is final and is recorded here.
- **Implementation verification so far:**
  - The unit tests use a fake Docker and cost nothing.
  - Pinning the images and reading `allEnv` used `docker image inspect` plus `docker create`, `docker cp` and `docker rm`. No container was started, so no metered job ran.

### 7.6 Execution and stop rules

These carry over from sections 1 and 2.4.

- **Before starting**, recorded in `run_logs/controls_prestart_check.md`:
  - no other agent Docker task is running, including the qualification session;
  - `docker ps -a` is empty;
  - `sha256sum -c FREEZE.sha256` passes, and the hashes below match.

  The driver checks the rest itself: the plan, control and E1 manifest hashes, the identity derivation, all image IDs present, and `docker info`.
- **Order:** identity_etcd5509 201–205, then identity_etcd7492 201–205, then detfail_grpc1859 211–213. Seeds follow the measured-block rule, SHA-256(`e1:<episode>:block:<n>`).
- **Stops, with no retry:**
  - on `docker info` failure (exit 2);
  - on a guard stop (exit 3);
  - at the first structural mismatch (exit 4): a version role without exactly three recorded attempts, a record with another manifest or episode, a ledger that disagrees with the executed statuses or fails `verify_chain`, or a container still present.
- **Resume:** a stopped run resumes only from the next unrecorded block. An incomplete recorded block needs a decision recorded here.
- **Output:** while running, exit statuses only, in `run_logs/controls_201-213.log`, plus the start and end UTC files.
- **After the run:**
  - oracle on each control ledger, then the 7.3 pre-declared override, then per-control analysis;
  - all in a later entry here.

### 7.7 Verification and hashes

- **Tests:**
  - The unit suite runs 193 tests, all OK: the 172 from section 3 plus 21 for the control driver.
  - Four deliberate breakages were each caught: disabling the guard, the leftover-container check, the block-completeness check and the identity-derivation check. `run_controls.py` was restored byte for byte afterwards.
- **Byte-for-byte storage:** `e1_harness/.gitattributes` now also marks `tests/test_run_controls.py` `-text`. Everything else below is under `e1/` (`* -text`).

| File | SHA-256 |
|---|---|
| `e1/run_controls.py` | `4feed4f0a83c8cc03839cd7e363b20d11b2464d360a5de092dfbe7901e4092f3` |
| `e1/controls/plan.json` | `c67830841a540cf68f509115d0a4627f3890b7ae31f2de8a2b217c7f8f9f6cd7` |
| `e1/controls/manifests.json` | `575244b1b663ce149cea5176fbed0ba960261db17e58550c29f04bf195ab556d` |
| `e1_harness/tests/test_run_controls.py` | `537b452a39dac425c3eda311c3137a86c51ebee224285a6da3e8cf7757503d98` |

| Control manifest | `Manifest.sha256` |
|---|---|
| `identity_etcd5509` | `973488c9d0d7a89b4259a5ff8f3e0f4371f7814652d28be84687a7fab4d681c1` |
| `identity_etcd7492` | `362fa13a502e3eb1eb93ed18d3cacc57eeb550909562ca32df5f4d189e598358` |
| `detfail_grpc1859` | `87d94b32c105903e2f59c7badba44d0716452f44a1c4fc36d4cd06ea3169d2f6` |

- **From here:** the controls may run under this entry once the 7.6 pre-start conditions are met and recorded, and the Docker slot has been agreed with the qualification session.

## 8. 2026-09-23 — step-4 controls run: results

- **Status:** records the run that section 7 authorised. All 13 control blocks ran to completion, and both controls met every expectation that section 7.3 pre-declared. E1 step 4 is complete.
- **Unchanged:** `e1_protocol.md`, sections 1–7, every hash-frozen file, the E1 ledgers (still 254 records) and the section 6 results.

### 8.1 Run

- **Pre-start:** `run_logs/controls_prestart_check.md` records the conditions at 09:33:44Z.
  - `docker ps -a` was empty and the host was idle.
  - Both other sessions were idle, and the researcher confirmed the Docker slot was free.
  - All frozen and section 7.7 hashes matched, and the driver's preflight was clean.
- **Code executed:** `run_controls.py` at `4feed4f0…` from HEAD `13a6ef7`, with the harness at its recorded hashes.
- **Window:** 09:34:09Z (`controls_start_utc.txt`) to 09:38:01Z (`controls_end_utc.txt`, `exit=0`).
- **Outcome:** driver status `DONE`. There was no `docker info` stop, no guard stop and no structural mismatch. After the run, `docker ps -a` listed no containers.
- **Independent re-check,** from the control ledgers and not the driver log:
  - `verify_chain` passes on all three ledgers (30, 30 and 18 records).
  - Every block is complete: three attempts per role, the planned seed, and the control's manifest hash and episode.
  - `timed_out` is false everywhere, and the 78 attempts do not overlap.
  - The identity attempts ran only each episode's frozen `V_ok` image. The grpc attempts ran both pinned images.
  - The E1 ledgers are byte-unchanged.

### 8.2 Results against the pre-declared expectations

| Control | Exit statuses | Oracle | Executed decisions (frozen reducer on raw statuses) | Analysis | Expectation met |
|---|---|---|---|---|---|
| `identity_etcd5509` (201–205) | 30 × 0 (0.54–0.68 s) | 30 `PASS`, 0 focal | P1, P3, P3-retain: ACCEPT on both roles, every block | `S = N = 0`, 0 invalid, 0 focal witnesses | yes |
| `identity_etcd7492` (201–205) | 30 × 0 (0.51–0.61 s) | 30 `PASS`, 0 focal | P1, P3, P3-retain: ACCEPT on both roles, every block | `S = N = 0`, 0 invalid, 0 focal witnesses | yes |
| `detfail_grpc1859` (211–213) | 18 × 2 (10.33–10.59 s) | mechanical: 18 `UNRESOLVED`, 0 focal; after the 7.3 rule: 18 `HARNESS_INVALID` | P1: BLOCK. P3 and P3-retain: BLOCK after three failures. Both versions, every block | no block counts toward `S`; every decision `INDETERMINATE`; invalid fraction 1.00, which the report flags against the 0.10 gate | yes |

- **The pre-declared override (7.3):**
  - It was applied mechanically to all 18 grpc attempts and held for every one. Each dump has 7 goroutines. The test goroutine is blocked in `(*ClientConn).WaitForStateChange` ← `DialContext` ← `Dial` ← `(*test).clientConn`, and no `quotaPool` frame appears.
  - Each attempt's `=== RUN` line is present, followed by `panic: test timed out after 10s`.
  - This matches the Task 5 expired-certificate finding. No other override exists.
- **Two views of B, both as intended:**
  - **Executed view:** what a CI job would see from exit statuses alone. Every policy BLOCKs, so retry cannot hide the deterministic failure.
  - **Analysis view:** after adjudication, the failure is identified as an environment artifact present on both versions. `analysis.py` turns `HARNESS_INVALID` into a missing result by design, so it rates each decision `INDETERMINATE`, attributes nothing to the revision and flags the invalid fraction.
  - The difference between the two views is the attribution check itself, not a discrepancy.
- **Analysis settings:** `analysis.py` ran once per control ledger with `--blocks 201-205` or `--blocks 211-213` and `--allocated-vcpus 16`, and the tool's default `--family-alpha` and `--invalid-threshold`. The controls are not in the section 6 contrast family, and their intervals are not interpreted. A second run of each reproduced all nine output files byte for byte.

### 8.3 Interpretation

This is labelled interpretation.

- **Attribution:** with no revision change, the whole pipeline produced no difference, no failure and no attribution on either episode. A failure identical on both versions and caused by the environment was never scored as a defect witness. It was isolated as invalid, not counted in `S`.
- **Final status:** a deterministic failure BLOCKs under P1, P3 and P3-retain. P3 spends its full three attempts and cannot accept.
- **Scope, section 7.4 still applies:** B's failure comes from the environment. The stronger check, a revision-attributable deterministic defect giving `L = 0`, remains deferred as B2.
- **Plan §6 "Continue":** within E1's two episodes, the controls add evidence that attribution and final status work. The projected E2 cost and the day-10 gate are not assessed here.

### 8.4 Cost

- **This run:** span 231.0 s, which is **1.027 vCPU-hours** conservative. The attempt-sum is 0.991, and the guard basis is 1.698.
- **E1 total:**
  - 11.68 + 1.027 = **12.71 vCPU-hours** on the span basis.
  - 13.47 on the guard basis, the figure the driver's guard used.
  - About 6.5 vCPU-hours below the 20.0 cap on either basis.
- **Reserve used:** the section 2.3 reserve paid for this run. The unused remainder is not spent on extra sampling.

### 8.5 Hashes

| File | SHA-256 |
|---|---|
| `e1/controls/identity_etcd5509/attempts.jsonl` (chain head seq 30 `8226f44728830761b094342f5b6e1d2d4ddcdf2e3571cc9b5979ae166b85c093`) | `202fdcaec9a3a4e6c61f69e600a4047dc1d4b1bf475d7f60e1ad4769adc8188d` |
| `e1/controls/identity_etcd7492/attempts.jsonl` (chain head seq 30 `3876e00393be1883dbee10354d4fec98c8018b98c5baa73e33178acef9654f52`) | `e6e7aefc7a1b783a2ad91864857249ea35a62adaa2ee9721bd46316eabfd6848` |
| `e1/controls/detfail_grpc1859/attempts.jsonl` (chain head seq 18 `267938dc26114fbb20acf8774c18513ada87e3b35dcd067e3aee0ea8965ce990`) | `0e77915a05cf3660801c6d81f27291189f29d0b3a9a0ae572e71481e9d1cd5db` |
| `e1/controls/identity_etcd5509/annotations.jsonl` | `a2caa557e2d84f8a8f2d7beaf9a0386ac64a49523e608aa1457fb9f54dd7812d` |
| `e1/controls/identity_etcd7492/annotations.jsonl` | `e5efeb1d09c14c666bb1c5d920ae2679153a8e33044cf455277f81ae38947897` |
| `e1/controls/detfail_grpc1859/overrides.jsonl` | `c101993c346f7fc007d18d67abd496519652126c6d6c5b8a851fb07a3cb803e6` |
| `e1/controls/detfail_grpc1859/annotations.jsonl` (with overrides) | `758a6bc4991ac1fd79fb417314a557db1c805318e24ac9d71f98b8ee27f27dc1` |
| `e1/controls/identity_etcd5509/analysis/report.md` | `0a8fed6d37fa85ecfd8084fff679c83b542c9e2925cd28ae5e2534f95059135e` |
| `e1/controls/identity_etcd5509/analysis/summary.json` | `a2e7ade412d85cea0b8d3817e03ac64ea60c1adde59af5201ab3abadd22bdc0e` |
| `e1/controls/identity_etcd5509/analysis/policy_decisions.csv` | `e85a19b684105efb08a635b86f86596aacf6992b236f5903d571f18acb9fb9e3` |
| `e1/controls/identity_etcd7492/analysis/report.md` | `d7cf3882ce7970342e5e7d0ee693b3c2a3c5f9d6d709366fbe92e962d7b0bd27` |
| `e1/controls/identity_etcd7492/analysis/summary.json` | `3973b436fdc91389d9c8ff38d28c590b70d681741c2e5e872e0475cd1f806453` |
| `e1/controls/identity_etcd7492/analysis/policy_decisions.csv` | `1a97202f2cdb7496f7fc609de353fd042f8bf9c0291ce52b1e0a32a8895bbccb` |
| `e1/controls/detfail_grpc1859/analysis/report.md` | `19307c3568d411dec3dfce584cb8f627e22734ed711da58bb6a6ea940c0858ac` |
| `e1/controls/detfail_grpc1859/analysis/summary.json` | `534e9d2421f89672106f7fa10db985420016ca45193e6c604d74c4d5e02bfa5d` |
| `e1/controls/detfail_grpc1859/analysis/policy_decisions.csv` | `516f16a5ea69eb341d67ccc5db62737b41450c33deea31def61638bdc64bacc6` |
| `e1/run_logs/controls_prestart_check.md` | `a2881c3f8ec3370aa6c4751d5bc6328432ae3ec5488d9962343b9c4f691412b3` |
| `e1/run_logs/controls_start_utc.txt` | `c2f3a4c13502e897f01202b4557c9cde684206976adf8bc32e6848e3f3d6c1e1` |
| `e1/run_logs/controls_201-213.log` | `c59cc58b00f7282fdc2f73fb6f4668644c08eac69439b44933c42ce9cc56c41f` |
| `e1/run_logs/controls_end_utc.txt` | `5a48bbc520cd3d1dd98578184dbdd95c8ffab96deb20297689ac4a9d7b1fd3f9` |

- All files are under `e1/` (`* -text`), so each hash verifies from any checkout with `sha256sum`.
- **To reproduce** from the repository root: `oracle.py --ledger …/controls/<control>/attempts.jsonl` (plus `--overrides …/detfail_grpc1859/overrides.jsonl` for B), then `analysis.py` with the settings in 8.2.
- **From here:** E1 steps 1–5 are complete. Remaining before E2 are the E1 "Continue" decision (plan §6), including the projected E2 cost, and the day-10 gate (four qualified episodes across two projects by 2026-09-27T23:02:26Z). Both are the researcher's decisions.

## 9. 2026-09-25 — researcher accepts `--family-alpha 0.025`

- **Status:** on 2026-09-25 the researcher accepted the setting that section 6.2 recorded as "a choice not fixed by earlier records": `--family-alpha 0.025` per `analysis.py` run.
- **What it means:** E1's four contrasts (`L` and `R` for etcd5509 and etcd7492) form one Bonferroni family, as plan §4.5 requires. Each category-probability interval is at confidence 1 − 0.05/8 = 0.99375.
- **Effect on results: none.** Section 6 already used this setting. No output is re-run or edited, and the hashes in section 6.6 still apply.
- **Unchanged:**
  - the section 1 sensitivity run, which used the same setting;
  - the section 8 controls, which used the tool's default and are outside the family (section 8.2).
- **Scope:** this acceptance covers E1 only. Plan rule G1b means E2 will not run (ledger Addendum v9, A28), so no E2 family is defined here.
