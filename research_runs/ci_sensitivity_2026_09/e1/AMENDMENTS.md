# E1 amendments and incidents (append-only)

`e1_protocol.md` stays as frozen (see `FREEZE.sha256`). Later deviations and incidents are recorded here in time order and are never edited afterwards.

## 1. 2026-09-22 — concurrent host load at the start of batch 1

- **Observed:** Batch 1 started at `2026-09-22T21:21:28Z`. A repository-wide `grep -rI` launched earlier in the same agent session was still running in the background: a disk- and CPU-heavy read over the large local dataset directories. It was stopped at about `2026-09-22T21:21:42Z`. That breaks the "one job at a time" rule for the first ~14 s of batch 1.
- **Affected attempts:** `etcd5509` block 1, `V_bad` attempt 1 (started `21:21:29.10Z`, exit 0, 0.91 s), and at least the start of `V_bad` attempt 2. No later attempt overlapped it.
- **Handling:** Nothing was re-run, replaced or removed; the attempts stay in the ledger as recorded. Analysis must also report every `etcd5509` contrast with block 1 excluded, as a sensitivity check. If excluding block 1 changes a conclusion, that conclusion is reported as dependent on this incident.
- **Cause and prevention:** The earlier search was moved to the background and never cleaned up before launch. Before each later batch starts, no other agent background task may be running, and `docker ps` must show no containers.
