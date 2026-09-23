# Controls: pre-start conditions — 2026-09-23

Recorded before `run_controls.py` started, as AMENDMENTS §7.6 requires.

- **Observed at 2026-09-23T09:33:44Z:**
  - Docker engine 29.7.2 with 16 CPUs and 16.29 GB of memory, the same setup as `e1_protocol.md`.
  - `docker ps -a` lists no containers.
- **Agent tasks:**
  - This session has no background task running.
  - The two other Claude sessions on this machine, "Project overview and constraints" and "E1 blocks for etcd5509/etcd7492", were listed as idle.
  - The researcher confirmed that the Docker slot is free: the qualification session has no container running and will start none until `controls_end_utc.txt` is written.
- **Host load:** the busiest process used 0.47 CPU-seconds over a 5-second sample (Claude). `com.docker.backend` used 0.22, and everything else 0.19 or under. No search, build or container job was running.
- **Code state:**
  - The worktree is at HEAD `13a6ef7` with a clean tree. `sha256sum -c FREEZE.sha256` passes.
  - `run_controls.py`, `controls/plan.json`, `controls/manifests.json` and `test_run_controls.py` match their §7.7 hashes.
  - The harness files match their recorded hashes, with `runner.py` checked by its CRLF form (§4).
  - The unit suite passes.
  - The driver's own preflight reported no problems: all six image IDs are present, `docker info` succeeds and there are no containers.
