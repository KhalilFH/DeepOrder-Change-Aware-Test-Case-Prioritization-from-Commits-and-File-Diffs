# C1 readiness inventory

## Material Passport

- Created: 2026-09-25, by the implementation-handoff agent (single agent, no delegation).
- Stage: **Phase 0, read-only inventory**. No subject, helper or probe container was started, no image was built or pulled, and no host or Docker setting was changed while collecting the facts in sections 1–4.
- Repository: branch `research/revival-2026`, `HEAD = 721d885a315a2c0ef26a82f2613248a4abcc110c`; `git pull` reported up to date; `git status --short` empty.
- Mutable record: later sections are appended with their own dates. Nothing here is a C1 observation of subject behaviour.

## 1. Design-freeze verification

`DESIGN_FREEZE.sha256` lists 8 files. Each digest was recomputed independently three ways on 2026-09-25 (first logged command 11:34Z):

| Check | Result |
|---|---|
| `sha256sum -c DESIGN_FREEZE.sha256` on the checkout | 8/8 OK |
| CR bytes in each listed file | 0 in all 8 (LF bytes, as `.gitattributes` requires) |
| SHA-256 of `git show HEAD:<path>` for each listed path | 8/8 match |
| SHA-256 of `git show 721d885:<path>`; checksum file itself vs. commit | 8/8 match; byte-identical |

Status: **design freeze verified**. No design file was edited.

## 2. Host and runtime (observed)

| Item | Observed | Source |
|---|---|---|
| Host CPU | AMD Ryzen 7 7700, 8 cores / 16 logical | `Win32_Processor` |
| Host OS / RAM | Windows 11 Pro 10.0.26200; 31.1 GB total, 16.1 GB free at inventory | `Win32_OperatingSystem` |
| Host background load | 8% `LoadPercentage` at inventory; interactive applications running (browser, desktop assistants, this agent). Not controlled. | CIM, `Get-Process` |
| WSL config | no `%USERPROFILE%\.wslconfig` (Docker Desktop defaults) | file check |
| Docker client/server | 29.7.2 / Docker Desktop 4.90.0 (238679), API 1.55, context `desktop-linux` | `docker version` |
| Engine VM | kernel 6.6.87.2-microsoft-standard-WSL2, x86_64, **16 CPUs**, 15.17 GiB | `docker info` |
| cgroup | **v2**, driver `cgroupfs`, cgroupns security option | `docker info` |
| Storage / runtime | overlayfs (containerd snapshotter); runc 1.4.3; containerd v2.3.3 | `docker info` |
| Containers at inventory | 0 total, 0 running | `docker ps -a` |
| Python used for C1 code | CPython 3.14.3 (Windows, `C:\Python314\python.exe`) | `python --version` |
| Git line endings | `core.autocrlf=true` in `.git/config` | `git config --show-origin` |

Comparison with the E1-era record (`research_runs/ci_sensitivity_2026_09/environment_manifest.json`, 2026-09-10): same CPU model, same 16-CPU/15.17 GiB Docker Desktop VM, same kernel, engine, cgroup v2 and storage driver. **Difference:** E1 drove Docker from a WSL Ubuntu process; C1 drives the same daemon from the Windows host through the `desktop-linux` context. The container runtime is the same; the client process differs. Recorded, not assumed immaterial.

The protocol's host requirement (same class of Linux Docker VM with 16 visible logical CPUs) is **met on inventory evidence**. Quota enforcement is not yet verified (section 5 item 4).

## 3. Subject images (observed, `docker image inspect`, nothing run)

All twelve images are present locally. IDs are compared with the durable source records.

| Subject | bug image ID (prefix) | fix image ID (prefix) | Recorded in | Match | Go (image env) |
|---|---|---|---|---|---|
| etcd5509 | `399e13203fc4` | `ffc618679d85` | `e1/manifests.json` | exact | 1.10.8 |
| etcd7492 | `b51cb62a901b` | `2b66d59152c8` | `e1/manifests.json` | exact | 1.13.15 |
| grpc1859 | `6b890fa74bed` | `3b72ed206066` | **no ID ever recorded** | creation time 17:50:11Z / 17:50:33Z falls inside the Q0 Task 5 window 17:44–18:00Z and matches `build_end.txt` 17:50:35Z; identity inferred, not proven | 1.13.15 |
| grpc2391 | `cc6e5a69cd7a` | `65a2902bbfce` | restoration record + frozen protocol | exact | 1.13.15, `GO111MODULE=on` |
| istio17860 | `23e14b796ad0` | `7fba6b07fc8d` | restoration record + frozen protocol | exact | 1.13.15, `GO111MODULE=on` |
| k8s26980 | `8a215c592956` | `6c93e46a3848` | restoration record + frozen protocol | exact | 1.12.17, `GO111MODULE=off` |

Full IDs are in `environment_manifest.json` and `subject_manifest.json` once written. Other facts:

- `RepoDigests` contain only local self-references; no base-image registry digest is recorded in any image, and no `golang:*` base image is present locally. Base-image digests are therefore **unknown**; layer diff IDs are the available identity.
- Image default working directories differ between bug and fix (bug: the target package; fix: the repository root). C1 always passes `-w` explicitly, so this does not reach the command.
- Images are local only; no archive (`docker save`) exists outside Git. Retention depends on this Docker Desktop VM.

## 4. Source records and harness interfaces (read)

| Subject | Restoration record | Raw attempt logs available for oracle replay | Recorded oracle |
|---|---|---|---|
| etcd5509 | `task5_etcd5509_restoration.md` | Q0 40 + smoke; E1 ledgers (`e1/etcd5509`, controls, direct) | `e1_harness/oracle.py` card |
| etcd7492 | `task5_etcd7492_restoration.md` | Q0 40 + 7 exploratory; E1 ledgers | `e1_harness/oracle.py` card |
| grpc1859 | `task5_grpc1859_restoration.md` | Q0 40 + timing/probe logs incl. expired-certificate timeouts | `e1_harness/oracle.py` card |
| grpc2391 | `task5_grpc2391_restoration.md` | Q0 40 + 7 exploratory | shell rule in `run/attempt.sh`; card C-04 text |
| istio17860 | `task5_istio17860_restoration.md` | Q0 40 + 7 exploratory | shell rule in `run/attempt.sh`; card C-05 text |
| k8s26980 | `task5_k8s26980_restoration.md` | Q0 40 + 7 exploratory; **no positive (focal) log exists** | shell rule in `run/attempt.sh`; card C-06 text |

Harness interfaces read: `e1_harness/{policy,ledger,runner,oracle,analysis}.py`. Findings relevant to C1:

- `policy.reduce_block` and the prefix helpers are reusable unchanged.
- `ledger.Ledger` keys identity as `(episode, block, version, attempt)`; one ledger per subject/profile/stage avoids collisions.
- `runner.Manifest` has no CPU/environment fields and hard-codes `docker run --rm`, so it cannot enforce or evidence a profile; C1 needs its own executor.
- `oracle.card_for` knows only etcd5509, etcd7492 and grpc1859. `oracle.classify` is card-agnostic and reusable.
- `analysis.py` computes within-episode P1/P3 contrasts only; the matched R/L contrast must be new code.
- `task5_artifacts/verify.sh` and `rebuild.sh` cover only etcd5509, etcd7492 and grpc1859.
- E1 offline suite: `python -m unittest discover -s e1_harness` → 193 tests OK (baseline, before any C1 change).

## 5. Unknowns and pending checks at the end of Phase 0

1. In-image blob/test identity for grpc2391, istio17860 and k8s26980 has not been re-run since Q0 (it was checked during Q0; `verify.sh` does not cover them).
2. Dependency state for etcd5509/etcd7492 was never recorded (ledger A13); it can only be enumerated from the surviving images now.
3. Test-binary SHA-256 values are not recorded for any subject.
4. Whether `--cpu-period=100000 --cpu-quota=200000` produces `cpu.max = 200000 100000` and real throttling on this daemon today, and whether `GOMAXPROCS=16` reaches each image's Go runtime, is unverified. (The 2026-09-10 manifest verified `--cpus=2` → `200000 100000` with an alpine helper; that is prior evidence, not a C1 check.)
5. The three missing oracle cards are unwritten; slowness susceptibility of all six oracles under the limited profile is unreviewed.
6. Human hours for all historical preparation remain unknown.

Next: Phase 1 preparation (source/blob/dependency checks inside the existing images, logged against the 8 vCPU-h preparation cap). No rebuild is planned unless a check fails.

## 6. Phase 1 preparation results (appended 2026-09-25)

Authorized preparation (HANDOFF step 2). No image was rebuilt, pulled or modified; every check ran in a fresh helper container (`sh -c`, read-only script) or read files from a never-started container (`docker create` + `docker cp`). No subject test ran in this phase. All containers carried the `c1.study` label and were removed by their own IDs; `docker ps -a --filter label=c1.study` was empty afterwards.

### 6.1 In-image counterpart, test and dependency checks — `prep/image_checks.json`

`python -m c1_harness.cli prepare-checks` → **6/6 PASS**. Expected values come from the restoration records and `task5_artifacts/verify.sh`; they were compared, not copied.

| Subject | Commit (both) | Focal blobs bug / fix | Test files of target package | Tree delta bug vs fix | Dependency identity (equal in both) |
|---|---|---|---|---|---|
| etcd5509 | `9ed3b446` | `b8209b8a` / `b5111630` | 9 identical | `remote_client.go` (+ inert untracked `bug_patch.diff`); `test` script modified identically in both | vendored in-tree (`cmd/vendor`); no non-repo GOPATH source |
| etcd7492 | `148c923c` | `7aa80794` / `ff48c514` | 2 identical | `simple_token.go` (+ inert `bug_patch.diff`); `test` identical | vendored in-tree (`cmd/vendor`); no non-repo GOPATH source |
| grpc1859 | `484b3ebb` | client `717e4192`/`56b434ef`, server `5233d6f3`/`24c2c7e1` | 2 identical | two transport files (+ inert `bug_patch.diff`) | 5 dated dependency repos at the recorded pins; `/go/dep_versions.txt` identical |
| grpc2391 | `ff2aa059` | `e74f8e40` / `d0404313` | 7 identical | `clientconn.go`; `go.mod` modified identically | `go list -m all` identical and byte-equal to `task5_artifacts/grpc2391/dep_versions_*.txt` |
| istio17860 | `c6e91302` | `f6644419` / `638578e3` | 5 identical | `pkg/envoy/agent.go`; `go.mod`/`go.sum` modified identically | `go list -m all` identical and byte-equal to `task5_artifacts/istio17860/dep_versions_*.txt` |
| k8s26980 | `628af356` | `ce9ddf2c` / `c557bf97` | 3 identical | `shared_informer.go` only | vendored in-tree (`vendor/`, `Godeps.json` identical) |

New findings:

- **etcd dependency gap narrowed.** Ledger A13 recorded the etcd dependency state as never recorded. The images show that both etcd revisions vendor their dependencies in-tree under `cmd/vendor`, and GOPATH holds no source outside the repository. The dependency state is therefore fixed by the pinned commit plus the clean tree (only the harness `test` script is modified, identically). The Go toolchain and base image layers are still identified only by image ID.
- Test-binary SHA-256 values are now recorded for all 12 images (`subject_manifest.json`). The binaries differ between variants, as they should.

### 6.2 CPU profile enforcement — `prep/profile_probe_prep1.json` (failed probe), `prep/profile_probe_prep2.json`

- **First probe: FAILED because of a probe bug.** Busybox `date` has no `%N`, so the wall time parsed as 3 ns instead of about 3 s and the L throughput check misfired. The raw counters already showed enforcement: R 11.23 CPU-s and L 6.03 CPU-s in about 3 s, with 30 of 31 L periods throttled. The file is kept. The probe was changed to time with `/proc/uptime` and rerun. No threshold or profile setting changed.
- **Second probe: PASSED.** R: `cpu.max = max 100000`, 3.72 CPUs with 4 busy loops, 0 throttled periods. L: `cpu.max = 200000 100000`, 2.03 CPUs, 31 throttled periods. Both: `cpuset.cpus.effective = 0-15`, `nproc = 16`, `GOMAXPROCS=16`.
- The Go runtime probe used each subject toolchain (go1.10.8, go1.12.17, go1.13.15) under both profiles. It showed `runtime.GOMAXPROCS(0) = 16` and `runtime.NumCPU() = 16` everywhere, with the expected `cpu.max`. These toolchains predate cgroup-aware GOMAXPROCS defaults; the explicit setting is what applies.

### 6.3 Oracle cards and replay — `prep/oracle_replay.json`

- Three cards were added in `c1_harness/cards.py`, transcribed from cards C-04, C-05 and C-06 and their Q0 shell rules, each with a source-level slowness review. The three E1 cards are imported unchanged.
- Replay agreement:
  - 240/240 Q0 counted attempts agree with the recorded labels.
  - 58/58 uncounted logs agree, including grpc1859's expired-certificate timeouts, which must not match.
  - 332/332 E1 ledger records reclassify identically.
- Historical focal-positive logs: etcd5509 69, etcd7492 7, grpc1859 4, grpc2391 23, istio17860 25, **k8s26980 0**. k8s26980's rule rests on source review and synthetic fixtures only.

### 6.4 Structural enrollment (gate C0)

All six subjects are `READY_HISTORICAL`: exact surviving images, re-verified counterpart and test equality, pinned dependencies, and ported oracle. Four projects are represented. **C0 passes on structural evidence** (at least four pairs across at least two projects are required). Execution under the limited profile is not yet shown; the smoke calibration checks it. Q0 labels are unchanged.

### 6.5 Schedule and calibration plan (persisted before any calibration attempt)

- `schedule.csv` / `schedule.json`: 720 rows, written 2026-09-25 before the first calibration container. It regenerates byte-identically.
- Order balance, reported and not engineered: R precedes L in 31/60 subject-blocks for each variant. First cells: R/bad 18, R/ok 16, L/bad 16, L/ok 10.
- `calibration/plan.json`: first structurally ready subject = etcd5509. Maximum primitive attempts: smoke 24, identity 12, direct 16, helpers 4 (total 56, within the 64 cap).

## 7. Phase 3 offline checks and fixed calibration (appended 2026-09-25)

### 7.1 Offline checks (no Docker)

- `python -m unittest discover -s c1_harness/tests -t .`: **63 tests, OK**. They cover:
  - an exhaustive P1/P3/P3-retain truth table over every prefix in {0,1,missing}^0..3;
  - profile argument/inspection agreement, including each single-field deviation;
  - executor paths: normal run, unverified profile never started, timeout removing only its own container, cleanup failure, create failure;
  - budget formulas, admission, release, stage isolation and chain tamper detection;
  - schedule hash rule, shape, determinism, byte-equality with the saved schedule, and exclusion invariance;
  - driver behaviour: full triples, schedule order, stop conditions, the acceptable-variant alarm, reviewed resume without repeated IDs, the batch-B gate, budget exhaustion and a dry run that never executes;
  - calibration stages;
  - ported-card fixtures and the replay of historical logs;
  - matched contrasts, bounds, questioned-oracle handling, the independent cross-check and outputs;
  - gate A, including "cannot precede batch A";
  - launch-freeze tamper detection.
- `python -m unittest discover -s e1_harness`: **193 tests, OK**. E1 files are byte-identical to the design-time input hashes.
- Literal `analyze` CLI validated on a synthetic fixture (scratch directory, never in the study tree). All six required outputs, including `reproduction.md`, were written.

### 7.2 Fixed calibration (validation budget; separate ledgers under `calibration/`)

Every executing session began with the same pre-block checks and a helper cgroup probe. All four session probes passed: L 2.01–2.02 CPUs with 30 throttled periods; R 3.72–3.75 CPUs with 4 loops. No stage was repeated, and no parameter was changed after any outcome.

| Stage | Plan | Recorded | Integrity | What it establishes |
|---|---|---|---|---|
| Smoke | 24 (6 × R/L × bad/ok) | 24 | 24/24 profile-verified (quota in inspect matches), GOMAXPROCS=16, cleanup verified; 0 outer timeouts; 0 HARNESS_INVALID; 0 acceptable-variant focal | every subject's target executes and is captured under both profiles |
| Identity control (etcd5509 `V_ok` image in both slots) | 12 | 12 | same checks all pass; all 12 PASS; no focal in either slot | reset/identity path works; never revision evidence |
| Direct policy checks (etcd5509) | 8 traces, ≤16 attempts | 8 traces, 8 attempts | 8/8 direct decision = reducer replay of the trace's own ledger prefix; 8/8 stopping rule respected | structural agreement only |
| Isolation/timeout helpers | 4 | 4 | marker absent in the fresh container on both profiles; the 10 s helper timeout fired (10.09 s), partial output captured, the container removed by ID | reset isolation and timeout cleanup |

Mechanical categories (single observations; **no frequency or effect is read from them**):
- Smoke: focal on etcd5509 L/bad, etcd7492 R/bad, grpc2391 R/bad, istio17860 R/bad and L/bad. Every other cell PASS.
- Direct: P1 BLOCK on both bad traces, with a focal witness in each; every other trace accepted on attempt 1.

**Limitations, disclosed:**

- **The P3 retry path was not exercised live.** All four live P3 direct traces passed on attempt 1, so a live retry after failure never occurred. That path is covered only by the offline tests. It was not re-run to obtain a failure; the protocol forbids demanding outcomes.
- **VM clock rate.** Two failing smoke attempts ended about 3 s before their Go test timeouts in host time, although their dumps report "timed out after 45s/50s". A helper clock probe (`calibration/clock_probe.json`) measured the VM uptime clock running **5.0% faster** than the host monotonic clock (host/VM = 0.952), identically on R and L. The VM wall clock is stepped by time sync. Consequences:
  - in-test bounds are in VM time;
  - C1 attempt durations are host time, and Q0/E1 durations (driven from WSL) were VM time;
  - the effect is the same for both profiles, so it is not an R/L confound.

  It is disclosed for duration comparisons and projections.

### 7.3 Stage counts and spend

- Primitive calibration/control/helper attempts: 24 + 12 + 8 + 4 = **48 of the 64 maximum**.
- Helper probes: 8 session-probe containers and 2 clock probes.
- Validation spend: **1.282 of 6 allocated vCPU-h**; host reservation 1.956 h.
- Preparation spend: **0.258 of 8**.
- Measured: **0**.

## 8. Readiness gates and cost projection (appended 2026-09-25)

| Gate / item | Result | Evidence |
|---|---|---|
| Design freeze | verified 8/8 (checkout, HEAD, `721d885`) | §1; `verify-design` |
| Host (16-CPU Linux Docker VM, same class as E1) | met; same VM as E1, driven from the Windows host | §2, `environment_manifest.json` |
| C0 structural readiness | **pass**: 6 pairs, 4 projects, all `READY_HISTORICAL` | §6, `subject_manifest.json` |
| CPU enforcement | **pass**: probes plus per-attempt inspect before start; L charged at 2 only when both hold | §6.2, §7.2 |
| Identity / reset | **pass** | §7.2 |
| Policy prefix | **pass** (offline exhaustive; live structural 8/8), with the live retry-path coverage gap disclosed | §7.1–7.2 |
| Oracle | **pass with limits**: 630/630 replay agreement; smoke classified without HARNESS_INVALID; no acceptable-variant focal. k8s26980 has no positive example; slowness specificity rests on source review for all six. | §6.3, `c1_harness/cards.py`, `subject_manifest.json` |
| Schedule | frozen before calibration; regenerates identically | §6.5 |
| Budget | expected measured cost **15.6 vCPU-h** (all 60 matched blocks admitted, 8.4 left under the live guard). The conservative bound (every defective attempt times out on both profiles) is 104.6 vCPU-h; the guard would then stop after about 13 blocks. | `cost_projection.json` |
| Refusal paths (live) | `run-batch --batch A/B` refused without a launch freeze (exit 2). `dry-run --batch B` refused without gate A. `gate-a` refuses before batch A. No container started. | this section |

Estimated batch-A wall time from historical durations: about 55 minutes of strictly sequential jobs.
