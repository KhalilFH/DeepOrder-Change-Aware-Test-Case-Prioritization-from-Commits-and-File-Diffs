# Batch 2 structural and cost check — 2026-09-23

Run from the ledgers alone, after collection ended. Outcomes were not tabulated and no policy contrast was computed (e1_protocol.md, Stop rules).

| Episode | Records | `verify_chain` | Blocks 11-20 x 2 versions x 3 attempts | Duplicate IDs | No exit status | Runner timeouts | Manifest hashes | Wall (first start to last end) |
|---|---:|---|---|---:|---:|---:|---|---:|
| etcd5509 | 60 | 120 OK (whole ledger) | complete | 0 | 0 | 0 | 1 (frozen) | 1030 s |
| etcd7492 | 60 | 120 OK (whole ledger) | complete | 0 | 0 | 0 | 1 (frozen) | 140 s |

- Batch 2 window: 2026-09-22T21:42:40Z to 22:02:12Z. Both driver logs end in `DONE`. Across both episodes, no two batch 2 attempts overlap in time, and every container name is unique.
- The batch 1 records are unchanged: the batch 2 diff to each ledger adds 60 lines and removes none.
- Container check: done late, at 2026-09-23T07:55:52Z, not at the end of the batch. Docker Desktop was not running when batch 2 was committed (`9d99786`). `docker ps -a` then listed no containers at all, and none named `e1-*`. This shows nothing is left now. It does not show the state at 22:02Z. The four image tags still resolve to the frozen IDs in `e1_protocol.md`.
- No record in `run_logs/` shows the pre-batch check that AMENDMENTS.md §1 requires (no other agent background task, and `docker ps` empty). The timestamps above show that no two E1 attempts overlapped. They cannot show whether other host load was present.

## Cost

Batch 1's check used the first-start-to-last-end span, so the span figures below are the comparable ones. Summed per-attempt `elapsed_s` is given too.

| Basis | Batch 1 | Batch 2 | E1 measured blocks |
|---|---:|---:|---:|
| Span (s) | 1216.9 | 1170.4 | 2387.3 |
| Span, vCPU-h conservative / Q0 convention | 5.41 / 0.338 | 5.20 / 0.325 | **10.61 / 0.663** |
| Attempt-sum (s) | 1202.6 | 1157.5 | 2360.1 |
| Attempt-sum, vCPU-h conservative / Q0 convention | 5.35 / 0.334 | 5.15 / 0.322 | 10.49 / 0.656 |

- Correction: the `9d99786` commit message gives an E1 total of 2374.6 s (10.55 vCPU-h). That figure adds batch 1's span to batch 2's attempt-sum, which mixes the two bases. Use 10.61 (span) or 10.49 (attempt-sum). The commit is not rewritten.
- All 240 measured attempts are collected. Remaining E1 cap on the conservative count: about 9.4 vCPU-hours for the 12 direct checks, the controls and implementation verification. As batch 1's check noted, the direct checks' worst case (36 x 60 s) is up to 16 vCPU-hours and would not fit. They need their own cost check before they run.
