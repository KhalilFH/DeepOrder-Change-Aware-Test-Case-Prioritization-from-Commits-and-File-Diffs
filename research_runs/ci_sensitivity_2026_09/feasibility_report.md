# Feasibility report — CI policy sensitivity, Q0 and E1 (gate G1b)

## Material passport

- **Date:** 2026-09-25 (operational day 8 of the Q0 clock that started `2026-09-17T23:02:26Z`).
- **Status:** **DRAFT for researcher review.** Started on the researcher's instruction of 2026-09-25. It makes no new measurement.
- **Why this report exists:** plan gate G1b (`docs/research/NEXT_RESEARCH_ACTION_PLAN.md` §12): "No E2. Finish small feasibility report and trigger F1 where possible." Ledger Addendum v9 (A28) records that G1b applies.
- **Repository state:** written on `research/revival-2026` at `c157b54` (PR #6 merged).
- **Reading labels**, as in the plan:
  - **Observed** means read from a committed record.
  - **Result** means a pre-declared computation on those records.
  - **Interpretation** is labelled where it appears.
  - **Proposal** means a next step that nobody has authorised.
- **Sources:** `resource_ledger.md` (Addenda v1–v9), the Task C/C2/C3/C4 acquisition records, the six `task5_*_restoration.md` records, `e1/AMENDMENTS.md` §1–§9 and `e1/analysis/`. Nothing here overrides them. Where this report and a record disagree, the record wins.

## 1. Bottom line

1. **Q0's question:** "Can four usable episodes on two projects be qualified economically?"
   - **Answer: no, not within this roster.**
   - **Three** episodes qualified across **two** projects: etcd-5509, etcd-7492 and grpc-go-2391.
   - All 12 primary roster slots are used, so no fourth candidate can be carded.
   - Compute was **not** the limit: Q0 used ≈1.35 of its 20 allocated vCPU-hours. The limits were the roster and the qualification criterion.
2. **E1's question:** "Can the paired protocol measure P1/P3 … without conflating noise, faulty behaviour and harness errors?"
   - **Answer: yes, within its two episodes**, on every E1 criterion that could be checked (section 4).
   - It neither shows nor rules out a material retry loss.
   - It could not measure nuisance reduction, because no nuisance occurred.
3. **Gate G1b is not met.** Of its three conditions:
   - four episodes: failed;
   - E1 measurement valid: met;
   - E2 affordable: depends on the vCPU basis (section 5).

   **Consequence: no E2.** This report and a possible F1 audit follow.
4. **This is a feasibility no-go for E2, not a finding about retry policies.** It does not show that accept-on-pass retry is safe or unsafe (plan §7, "No-go / inconclusive").

## 2. What was planned

| Stage | Question (plan) | Stop rule (plan) |
|---|---|---|
| Q0 (§5) | Can four usable episodes on two projects be qualified economically? | Fewer than two by day 7 stops E1; fewer than four across two projects by day 10 stops E2 |
| E1 (§6) | Can the paired protocol measure P1/P3 on two real intermittent episodes, with traceable evidence? | Contradictory counterparts, forced intermittency, result-determining missing evidence, or unaffordable execution |
| G1b (§12) | Four episodes across two projects, E1 measurement valid, E2 affordable | "No E2. Finish small feasibility report and trigger F1 where possible" |

**Q0's qualification criterion (§5):** at least 2 focal failures **and** at least 2 passes on `V_bad` over 20 attempts at a frozen protocol, with a clean `V_ok`. It "deliberately selects measurable intermittency; absence of the pattern does not prove a test deterministic."

## 3. Q0 — what happened to each candidate

### 3.1 The 12 primary roster entries (observed)

| # | Entry | Source tier | Final label | Why | Record |
|---:|---|---:|---|---|---|
| 1 | DBCP-65a | 1 (JaConTeBe) | `UNRESOLVED` | historical pair, but only a forced (Mockito-controlled) kernel reproducer | `task_c_candidate_acquisition.md`, `dbcp_65_metadata_pass.md` |
| 2 | DBCP-65b / 270 / 281 | 1 | `UNRESOLVED` | historical pair, but no non-forcing protocol | same |
| 3 | LOG4J-38137 | 1 | `UNRESOLVED` | authoritative issue inaccessible; exact fix and counterpart unresolved | `candidate_cards.md`, `task_c_candidate_acquisition.md` |
| 4 | LOG4J-41214 | 1 | `EXCLUDE` | no acceptable counterpart; upstream lists it among outstanding Log4j 1 bugs | same |
| 5 | POOL-146 | 1 | `STABLE_CONTROL_ONLY` | reproducer is forced (sleep/staged threads), so a stable control only | same |
| 6 | POOL-162 | 1 | `STABLE_CONTROL_ONLY` | reproducer is forced (controlled interrupt/sleep sequence), so a stable control only | same |
| 7 | etcd-5509 | 4 (GoReal) | **`Q0_QUALIFIED`** | `V_bad` 16 focal / 4 pass; `V_ok` 20/20 | `task5_etcd5509_restoration.md` |
| 8 | etcd-7492 | 4 | **`Q0_QUALIFIED`** | `V_bad` 2 / 18 (at the minimum); `V_ok` 20/20 | `task5_etcd7492_restoration.md` |
| 9 | grpc-go-1859 | 4 | `Q0_NOT_QUALIFIED` | `V_bad` 1 / 19 | `task5_grpc1859_restoration.md` |
| 10 | grpc-go-2391 | 4 | **`Q0_QUALIFIED`** | `V_bad` 18 / 2 (at the minimum); `V_ok` 20/20 | `task5_grpc2391_restoration.md` |
| 11 | istio-17860 | 4 | `Q0_NOT_QUALIFIED`, kept as `STABLE_CONTROL_ONLY` | `V_bad` 20 / 0 | `task5_istio17860_restoration.md` |
| 12 | kubernetes-26980 | 4 | `Q0_NOT_QUALIFIED` | `V_bad` 0 / 20 | `task5_k8s26980_restoration.md` |

- **Java (tier 1) was left by decision, not exhausted.** Ledger A5 selected Go (GoReal) as this month's language on operational day 1, and no Java subject was restored. A3 records that tier 1 "was exited by research judgment, not by measured exhaustion".
- **Six Task 5 restorations ran,** all on GoReal subjects. Every one passed its counterpart check: blob equivalence, or the restricted-diff check for etcd-7492. None was abandoned for build, dependency or oracle reasons. istio-17860 needed a second build attempt, and grpc-go-1859 needed pinned dependency clones; both were disclosed and applied to both versions.

### 3.2 GoReal entries screened but not carded (observed)

The C2, C3 and C4 passes read GoReal in its fixed order and gave these entries a disposition without a roster slot (ledger A4-addendum-2, A20, A24):

| Disposition | Count | Entries |
|---|---:|---|
| `SCREENED_DETERMINISTIC_LEAD` (source reasoning: fails every time) | 10 | cockroach_1055, grpc_649, grpc_795, grpc_1275, grpc_1424, hugo_3251, hugo_5379, istio_18454, kubernetes_1321, kubernetes_25331 |
| `SCREENED_TEST_ONLY_FIX` | 6 | cockroach_1462, 30452, 30479, 36367; istio_16224; kubernetes_16851 |
| `SCREENED_RESTORATION_COST` (judged, not measured) | 5 | cockroach_17766, 24808, 25456, 35073, 35931 |
| `SCREENED_INELIGIBLE_PROJECT_CAP` | 4 | etcd_6708, 7443, 10492; grpc_3017 (also a deterministic lead) |
| `SCREENED_NOT_ISOLATABLE` (new, researcher may overrule) | 1 | kubernetes_11298 |
| `NOT_SCREENED` (after the last stop) | 8 | kubernetes_30872, 38669, 70277, moby_29733, 30408, serving_2137, syncthing_4829, 5795 |

### 3.3 The shape of the qualification results (result, then interpretation)

**Result.** Focal failures on `V_bad`, out of 20 counted attempts, across the six restorations:

| Subject | Focal failures | Passes | Inside Q0's [2, 18] window? |
|---|---:|---:|---|
| kubernetes-26980 | 0 | 20 | no |
| grpc-go-1859 | 1 | 19 | no |
| etcd-7492 | 2 | 18 | yes, at the edge |
| etcd-5509 | 16 | 4 | yes |
| grpc-go-2391 | 18 | 2 | yes, at the edge |
| istio-17860 | 20 | 0 | no |

**Interpretation.**
- The outcomes pile up at the two ends. Three of six fall outside the window, and two of the three that qualified sit exactly on its edge. With 20 attempts, a subject whose true failure rate is 10% (or 90%) lands inside the window only about 61% of the time; a rate between roughly 20% and 80% gives about 93% or better (binomial, 20 independent attempts). Most of these real concurrency bugs, under their default schedule on this host, fire either almost always or almost never.
- Screening points the same way: 10 GoReal entries were set aside by source reasoning as deterministic before any build.
- **This is not an estimate of any population rate.** The roster is a convenience sample (plan §5, "do not estimate population qualification rates from this convenience roster").

**Interpretation, what did not limit Q0:**
- no build or dependency problem stopped a restoration;
- no oracle needed a post-hoc correction except etcd-5509's two disclosed signature fixes;
- no per-candidate cap was approached (largest: etcd-5509, ≈0.52 of 4 vCPU-h).

## 4. E1 — calibration on etcd-5509 and etcd-7492

### 4.1 Results (from `e1/AMENDMENTS.md` §6.3 and §8.2, unchanged)

| Episode | S(P1) | S(P3) | L = S(P1) − S(P3) | Simultaneous interval | Contains margin 0.10? | `ACCEPT_WITH_PRIOR_FAILURE` |
|---|---|---|---|---|---|---:|
| etcd-5509 | 12/20 | 9/20 | 0.150 | [−0.236, +0.468] | yes | 3 |
| etcd-7492 | 2/20 | 0/20 | 0.100 | [−0.246, +0.406] | yes | 2 |

- **`R` = 0 for both episodes**, with interval [−0.251, +0.251]. No `V_ok` attempt failed, so nuisance was never observed.
- **Direction:** every discordant block went the same way. P1 blocked on a focal witness and P3 accepted after a retry.
- **Quality:** 0 invalid blocks and 0 undetermined blocks. The 12 direct-policy checks showed 0 structural mismatches.
- **Controls:**
  - identity/no-change: 60 attempts, all `PASS`, no attribution;
  - environment-caused deterministic failure: 18 attempts, all blocked by every policy, none attributed to the revision.
- **Family alpha:** `0.025` per run, accepted by the researcher on 2026-09-25 (`e1/AMENDMENTS.md` §9). This changes no result.

### 4.2 Plan §6 "Continue" criteria (result)

| Criterion | Status |
|---|---|
| Both episodes have working oracles, reset and policy interpretation | **met** (§6.4, direct checks §5, controls §8) |
| Invalid fraction ≤ 10% | **met** (0%) |
| Outcomes and intermediate failures traceable | **met** (SHA-256-chained ledgers, hashed annotations and outputs) |
| Projected E2 cost fits its cap | **depends on the vCPU basis**; see section 5 |

### 4.3 What E1 does not show (interpretation)

- **Loss:** with 20 blocks, both intervals include 0 and the 0.10 margin. E1 neither shows nor rules out a material retry loss, as plan §6 intends for a calibration.
- **Noise:** the noise-reduction side of RQ1 is not established, because no verified nuisance occurred.
- **Project:** both episodes are etcd, so the plan's preference for two projects was not met.
- **Data status:** the E1 data are development-only and are not E2 evidence.

## 5. Cost

### 5.1 Spent (observed, allocated vCPU-hours)

| Item | Spent | Cap | Basis |
|---|---:|---:|---|
| Q0 restoration and qualification (6 Task 5 passes) | ≈1.353 | 20 | Q0 convention, 1 vCPU per sequential job (ledger A14) |
| E1 (blocks, direct checks, controls) | 12.71 | 20 | conservative 16 vCPU, span basis (AMENDMENTS §8.4) |
| First ten operational days, combined | ≈14.07 | 40 | sum of the two rows above |
| Human hours, every pass | **UNKNOWN** | 12 (metadata), 2 per candidate | never measured (ledger accounting rule) |

**Observed:** the two stages use different vCPU conventions, so their sum mixes bases. On E1's 16-vCPU basis, Q0's figure would be ≈21.6, over its own 20 cap. The ledger has always stated Q0 on the 1-vCPU convention (A14).

### 5.2 Projected E2 cost (result)

E2 would run 100 paired blocks per episode and charge every attempt (plan §7). Script `feasibility/e2_cost_projection.py` computes the projection from:
- measured E1 durations, for etcd;
- Q0 counted-attempt durations, for grpc-go-2391, which has no E1 blocks;
- plus E1's 2.04 s per-attempt gap.

| Episode | Wall-clock h | 16 vCPU | 2 vCPU | 1 vCPU |
|---|---:|---:|---:|---:|
| etcd-5509 | 3.246 | 51.94 | 6.49 | 3.25 |
| etcd-7492 | 0.712 | 11.39 | 1.42 | 0.71 |
| grpc-go-2391 | 1.877 | 30.04 | 3.75 | 1.88 |
| **Three episodes** | **5.835** | **93.37** | **11.67** | **5.84** |

- **E2 cap:** 80 allocated vCPU-hours.
- **On the 16-vCPU basis**, three episodes already exceed it; a fourth would only add.
- **On the 2-vCPU basis**, which matches plan §11's instruction to "pin at most two allocated vCPUs per job initially", E2 would use about 15% of its cap.
- **Why 16:** E1 charged 16 because it did not pin CPUs, not because the tests used them.
- **The basis choice no longer decides G1b,** since the episode condition fails either way (ledger A28). It is reported so that any future design can budget honestly.
- **Limit:** grpc-go-2391's row uses Q0-runner durations, not E1-runner durations. The difference is not measured.

## 6. Decision under G1b

- **No E2.** Neither E2 nor E3 runs this month, and E3 needs a completed E2 anyway.
- **Not done, and not proposed:**
  - no roster extension;
  - no relabelling of a `Q0_NOT_QUALIFIED` entry;
  - no environment change to push kubernetes-26980 or grpc-go-1859 into the window;
  - no controls substituted for episodes.

  Each would be a choice made after seeing the results (plan §5 "No-go", §7 "Do not increase sample size or change defect definitions to preserve the story"; ledger A28).
- **What remains valid and preserved:**
  - three qualified episodes with their recipes, frozen protocols and per-attempt logs;
  - E1's calibrated, hash-chained measurement pipeline and its controls;
  - one stable-defect control candidate (istio-17860) for the deferred B2 check;
  - three meaningful negative qualification results.

## 7. Limits of this report

- **Human hours:** unknown for every pass, so the 12-hour metadata cap and the 2-hour per-candidate caps cannot be checked.
- **Reproducibility gaps:**
  - The etcd images are linked to their Q0 records by timestamps, not recorded image hashes.
  - etcd dependency versions were never recorded (ledger A13, A19); this cannot be fixed retrospectively.
  - None of the Docker images is preserved; the recipes and per-attempt logs are.
- **Host-specific rates:** every failure rate comes from one host (16 CPUs visible to Docker). Other hardware could move a subject into or out of the window.
- **Sample:** a convenience roster from one benchmark (GoReal) for everything that was restored, so no generalisation is claimed.
- **Single researcher:** all oracle labels are mechanical and applied by one researcher (plan §6).

## 8. F1 readiness (observed; F1 is not started)

The plan's F1 audit (§9) starts from "Airavata's preserved small-failure comparison and raw execution/identity tables", reading `25eb6b7`'s outputs. A read-only check on 2026-09-25 found:

- **Present:** commit `25eb6b7` holds `FINAL6/apache@airavata/step3_report.json`, with an 82-entry `per_cycle` list of APFD summaries (`m`, `n`, `apfd_hist`, `apfd_t0`, …) and the arm definitions (HIST vs HIST+T0). The file is not in the current tree.
- **Not found in the repository:**
  - the per-test rankings F1 needs to vary fault mappings;
  - the input dataset (`apache@airavata_enhanced_tcp_dataset.csv`);
  - the test-name map (`tcpci_slice/…/test_name_map.csv`).

  The report records their paths on another machine.
- **What the plan says to do:** "If per-test rankings cannot be recovered within one day, stop the ranking part and issue a traceability/label-validity audit instead", and "Do not fit a new model to fabricate the missing historical outputs."
- **F1 budget:** three researcher-days and 10 allocated vCPU-hours. Starting it is the researcher's decision.

## 9. Open decisions for the researcher (proposals, none authorised)

1. **Start F1**, beginning with a bounded search for the missing Airavata inputs (section 8), or close the month with this report.
2. **Close or keep the E2-affordability basis question.** It no longer affects G1b; it matters only for a future design.
3. **B2 control:** whether to enrol istio-17860 as the deferred revision-attributable deterministic-defect control. Without E2 its main use would be to strengthen the E1 calibration record.
4. **Routing documents:** `docs/research/RESEARCH_STATE.md` and its siblings are still scaffolds naming the older TCP question, although `AGENTS.md` calls `RESEARCH_STATE.md` authoritative. The plan says to preserve them unchanged; whether to update them now is a separate decision.
5. **Deferred Jev ideas:** an agreement check against E1's frozen oracle, qualification triage, and the original TCP shortlist use. None changes any result here.

## 10. Reproducing the figures

From `research_runs/ci_sensitivity_2026_09/`:

- **E2 projection (section 5.2):**
  - Command: `python feasibility/e2_cost_projection.py`.
  - Expected output: `feasibility/e2_cost_projection.csv` (SHA-256 `cb4f0245e5599c8ba75d9d83a231724d392e0066b301d88d479da7631b440dc3`).
  - Script SHA-256: `346848dd586398fc80a9003a73851b028fa170d5d29d3b4aca54bd4f5a257c0e`.
- **E1 results (section 4):** the commands in `e1/AMENDMENTS.md` §6.6 and §8.5.
- **Q0 results (section 3):** each `task5_artifacts/<id>/run/results.csv`, hashed through the restoration records listed in ledger A14, A22, A23 and A27.
