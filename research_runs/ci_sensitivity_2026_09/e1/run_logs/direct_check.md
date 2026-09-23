# Direct-policy checks: structural and cost check — 2026-09-23

Run under AMENDMENTS §2 and §3 with `run_direct.py` (`59e4f9b4…`) at HEAD `4517834`. Pre-start conditions are in `direct_prestart_check.md`. The driver's own output is `direct_101-112.log`. This file re-checks the result from the ledgers alone. Exit statuses are not oracle categories: no attempt has been classified, and no measured-block contrast was computed.

## Result

- **Driver outcome:** `DONE`, exit 0. There was no guard stop, no `docker info` stop and no structural mismatch.
- **Window:** `direct_start_utc.txt` 08:12:34Z to `direct_end_utc.txt` 08:16:35Z. First attempt started 08:12:34.79Z; last ended 08:16:35.20Z.
- **After the run,** `docker ps -a` listed no containers.

| Block | Episode | Version | Policy | Executed exit statuses | Reducer decision | Structure |
|---:|---|---|---|---|---|---|
| 101 | etcd5509 | `V_ok` | P3 | `[0]` | ACCEPT | OK |
| 102 | etcd5509 | `V_bad` | P3 | `[2, 2, 2]` | BLOCK | OK |
| 103 | etcd5509 | `V_bad` | P1 | `[2]` | BLOCK | OK |
| 104 | etcd5509 | `V_ok` | P1 | `[0]` | ACCEPT | OK |
| 105 | etcd5509 | `V_ok` | P3 | `[0]` | ACCEPT | OK |
| 106 | etcd5509 | `V_bad` | P1 | `[2]` | BLOCK | OK |
| 107 | etcd7492 | `V_ok` | P3 | `[0]` | ACCEPT | OK |
| 108 | etcd7492 | `V_bad` | P3 | `[0]` | ACCEPT | OK |
| 109 | etcd7492 | `V_ok` | P1 | `[0]` | ACCEPT | OK |
| 110 | etcd7492 | `V_ok` | P1 | `[0]` | ACCEPT | OK |
| 111 | etcd7492 | `V_bad` | P1 | `[0]` | ACCEPT | OK |
| 112 | etcd7492 | `V_bad` | P3 | `[0]` | ACCEPT | OK |

"Structure OK" means all of the following:
- the trace satisfies the planned policy's stopping rule (`stopping_problems`);
- every record carries the planned version, the planned seed and the frozen manifest hash;
- no attempt timed out.

The ledger totals:
- **Records:** 14 attempts. `verify_chain` passes on both ledgers (etcd5509 128 records, etcd7492 126).
- **Measured blocks 1–20:** unchanged, 120 records per episode.
- **Overlap:** no two direct attempts overlap in time.

## What the checks exercised, and what they did not

- **Exercised:**
  - P1 stopping after one attempt, 6 times.
  - P3 stopping at an immediate pass, 5 times.
  - P3 continuing through two failures to its three-attempt limit and blocking, once (block 102).
  - A fresh container per attempt, with none left afterwards.
- **Not exercised:** P3 accepting a pass after an earlier failure, for example `[2, 0]` or `[2, 2, 0]`. That is the stop-after-a-retry path, and the one retry acceptance depends on. The block-102 draw could have produced it but failed three times. In real execution this path is untested; it is covered only by the unit tests (`test_policy.py`, `test_runner.py`, `test_run_direct.py`). The allocation is frozen, so no check is added to cover it.

## Cost

| Basis | Seconds | Conservative vCPU-h (16) | Q0 convention |
|---|---:|---:|---:|
| Span, first start to last end | 240.4 | 1.068 | 0.067 |
| Attempt-sum | 233.2 | 1.037 | 0.065 |
| Guard basis, attempt-sum plus 2.04 s per attempt | — | 1.164 | — |

- **E1 so far on the conservative count:** 10.61 + 1.068 = **11.68 vCPU-hours** on the span basis, or 11.77 on the guard basis.
- **Projection:** the direct checks came in below the observed-maximum projection (2.73) and near the Q0-rate expectation (0.92).
- **Remaining:** the 3.0 vCPU-hour control reserve (17.0–20.0) is untouched. On the guard basis, 5.23 vCPU-hours remain below the 17.0 line.
