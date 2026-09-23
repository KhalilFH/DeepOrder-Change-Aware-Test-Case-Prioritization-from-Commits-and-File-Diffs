# Direct checks: pre-start conditions — 2026-09-23

Recorded before `run_direct.py` started, as AMENDMENTS §1 and §3 require.

- **Observed at 2026-09-23T08:12:07Z:**
  - Docker engine 29.7.2 with 16 CPUs and 16.29 GB of memory, the same setup as `e1_protocol.md`.
  - `docker ps -a` lists no containers.
- **Agent tasks:** this session has no background task running. One other Claude session on this machine, "E1 blocks for etcd5509/etcd7492", was listed as idle. The separate task suggested for harness line endings had not been started as a session.
- **Host load:** the busiest process used 0.61 CPU-seconds over a 5-second sample (Chrome), followed by Claude processes at 0.55 and under. No search, build or container job was running.
- **Code state:** HEAD is `4517834`. `sha256sum -c FREEZE.sha256` passes. The plan, driver and test hashes match AMENDMENTS §2.5 and §3.
