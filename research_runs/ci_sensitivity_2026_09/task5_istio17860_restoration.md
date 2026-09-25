# Task 5 — restoration and Q0 qualification of card C-05 (istio-17860)

## Result

| | `V_bad` (parent `7a9a996f` + unchanged fix test) | `V_ok` (squash-merge `c6e91302`) |
|---|---:|---:|
| Attempts (frozen protocol, counted) | 20 | 20 |
| `FOCAL_DEFECT_WITNESS_A` | **20** | 0 |
| `PASS` | **0** | 20 |
| `UNRESOLVED` / `HARNESS_INVALID` | 0 / 0 | 0 / 0 |

**Disposition: `Q0_NOT_QUALIFIED` on the primary track, retained as `STABLE_CONTROL_ONLY`.**

- **Why not qualified:** Q0 requires ≥2 passes on `V_bad`, and there were none.
- **The mechanism was reproduced on every attempt:** under this protocol, the second `Restart` held the agent mutex through the live-wait before the exit of epoch 0 could be processed.
- **No rescue:** no attempts beyond the 20, no change to the command or environment, and no relabelling.
- **The counterpart is clean:** `V_ok` passed 20/20, with no `BeTemporally` failure.
- **Not a proof of determinism:** zero passes in 20 does not prove the passing interleaving is impossible (Q0 protocol). The card pre-declared that the failure rate "may be high, … even near-deterministic".
- **Value as a control:** a stable, revision-attributable deterministic defect with a clean historical-pair counterpart is the "B2" control that E1 AMENDMENTS §7.4 deferred. Enrolling it as such needs a separate budgeted decision. This record makes no such decision.

## Authority and timing

- **Authority:** card C-05 (`task_c3_candidate_acquisition.md`), authorised by the researcher on 2026-09-25 together with C-04.
- **Task 5 window:** `2026-09-25T08:29:46.682Z` → `08:37:04.156Z`, **437.5 s**.
- **Counted attempts:** `08:36:40.420Z` → `08:37:04.156Z`.
- **Operational day:** 8.

## Step 1 — counterpart verification: PASS

| Image | ID | `pkg/envoy/agent.go` | `pkg/envoy/agent_test.go` | commit |
|---|---|---|---|---|
| `istio17860-bug` | `sha256:23e14b796ad0c487e7536b9213cab2c3a0897548489bb4f0e8a8944182296ba8` | `f6644419ad8c…` (= parent `7a9a996f`) ✅ | `09ea287d1f94…` ✅ | `c6e91302` + agent.go-only patch |
| `istio17860-fix` | `sha256:7fba6b07fc8d68fa362eec12eefb20408dcc2406bdae963414ca75184fd9c679` | `638578e33415…` (= fix) ✅ | `09ea287d1f94…` ✅ | `c6e91302` |

- **GoReal's test edit was not adopted.** GoReal's `V_bad`-only edit swaps `t.Fatalf` for `panic` with a traceback. `recipe/as_built/bug_patch_agent_only.diff` is GoReal's patch truncated before its `agent_test.go` section.
- **Result:** the upstream test is byte-identical on both versions.

## Step 2 — image builds: PASS on the second attempt, one disclosed environment deviation

- **Build attempt 1 failed on both images.** Module mode resolved `bitbucket.org/ww/goautoneg@v0.0.0-20120707110453-75cd24fc2f2c`, and Bitbucket now answers 404. The logs are kept as `build_{fix,bug}_attempt1_goautoneg_404.log`.
- **Build attempt 2:**
  - It added the same `go.mod` line GoReal uses, `replace bitbucket.org/ww/goautoneg => github.com/munnerz/goautoneg v0.0.0-20191010083416-a7dc8b61c822`, to **both** images. GoReal adds it to the bug image only.
  - Both builds exited 0, `08:30:46.814Z` → `08:32:59.866Z`.
  - The card pre-declared this deviation as identical on both versions.
- **Dependencies are reproducible:** `go list -m all` records 493 modules pinned by istio's own `go.sum`, identical in both images (`dep_versions_{bug,fix}.txt`), including the one replacement. Also disclosed: GoReal's `fix.Dockerfile` installs `vim` and `python3`, which this recipe does not, on either image.
- **Toolchain:** `golang:1.13`; istio's `go.mod` declares `go 1.12`.

## Step 3 — uncounted exploratory runs

- **Command:** `-test.run '^TestExitDuringWaitForLive$' -test.timeout 30s` in `/go/src/istio.io/istio/pkg/envoy`, with logs in `timing/`.
- **`V_ok`:** 2/2 `PASS` (test time 0.50 s).
- **`V_bad`:** 5/5 `--- FAIL … agent_test.go:213: timed out waiting for epoch 1 to start` at 5.0 s. That is the card's signature (a), and no correction was needed.
- **What the runs decided:** the timeout, and a check of the classifier on all 7 logs. The 5/5 was not used to decide whether to proceed.

## Step 4 — frozen protocol

`run/frozen_protocol.txt` was frozen before any counted attempt:

- **Images:** pinned by the IDs above, with the identical `replace` on both.
- **Command:** `/go/gobench.test -test.v -test.count 1 -test.run '^TestExitDuringWaitForLive$' -test.timeout 30s`.
- **Limits:** a 60 s outer timeout.
- **Reset and concurrency:** a fresh `docker run --rm` per attempt, one job at a time.
- **Batches:** 10 `V_bad`, 10 `V_ok`, 10 `V_bad`, 10 `V_ok`. `docker ps -a` was empty before and after.
- **Classifier:** `run/attempt.sh` applies only the pre-declared rules.

## Step 5 — counted qualification runs

- **Records:** `run/results.csv` holds all 40 rows, one log per attempt in `run/logs/`.
- **`V_bad`:** 20/20 carry the signature, at 5.29–5.41 s per attempt.
- **`V_ok`:** 20/20 `--- PASS`, at 1.03–1.33 s. No `V_ok` log contains a `FAIL` or `BeTemporally` line.

## Accounting

- **Task 5 wall clock:** **EXACT**, 437.5 s ≈ **0.1215** allocated vCPU-h (Q0 convention, ledger A14). This includes the failed first build.
- **Counted attempts:** 129.5 s.
- **Cap:** ≤4 vCPU-h per candidate, not reached.
- **Human restoration hours:** **UNKNOWN**; this was an agent-executed pass.
- **Artifacts:** `task5_artifacts/istio17860/` (about 355 KB), written into the repository as the pass ran (ledger A18).

## What was deliberately not done

- No further attempts after 0/20 passes.
- No longer `-test.timeout`, added load, `-test.cpu` or GOMAXPROCS change to make passes appear. Each of those would be forcing, or selection on the observed outcome.
- No switch to GoReal's instrumented test.
- No relabelling.
