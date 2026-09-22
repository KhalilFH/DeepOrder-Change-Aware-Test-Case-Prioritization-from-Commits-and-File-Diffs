# Batch 1 structural and cost check — 2026-09-22

Run from the ledgers alone. Outcomes were not tabulated and no policy contrast was computed (e1_protocol.md, Stop rules).

| Episode | Records | `verify_chain` | Blocks 1-10 x 2 versions x 3 attempts | Duplicate IDs | No exit status | Runner timeouts | Manifest hashes | Wall (first start to last end) |
|---|---:|---|---|---:|---:|---:|---|---:|
| etcd5509 | 60 | 60 OK | complete | 0 | 0 | 0 | 1 (frozen) | 1076 s |
| etcd7492 | 60 | 60 OK | complete | 0 | 0 | 0 | 1 (frozen) | 141 s |

- Batch 1 window: 2026-09-22T21:21:28Z to 21:41:47Z. Both driver runs exited 0; `docker ps -a` showed no leftover containers.
- Measured cost: 1217 s of attempt wall time. That is 5.41 allocated vCPU-hours on the conservative count (16 vCPUs) or 0.338 on the Q0 convention (1 vCPU-equivalent).
- Projected cost for all 40 blocks: about 10.8 vCPU-hours (conservative). Allowances: 12 direct checks, at most 1 vCPU-hour of wall time, or up to 16 vCPU-hours on the conservative count at the worst case of 36 x 60 s. In practice fewer than 15 minutes, about 4 vCPU-hours, is expected. Controls: small. The earlier `selftest.py` run was not metered.
- Decision under the batch-1 cost rule: the projected total fits the 20 vCPU-hour E1 cap on the expected estimate, so **batch 2 proceeds**. The worst-case direct-check figure would not fit on the conservative count, so the direct checks get their own cost check before they run.
