# Resource ledger — CI policy sensitivity Q0

- Ledger identifier: `ci_policy_sensitivity_resource_ledger_2026-09-17_v1`
- Scope: Q0 metadata/oracle and restoration accounting through the timing amendment
- Accounting rule: model token usage, agent execution time, wall-clock age of the worktree, and file modification times are not human metadata hours unless the approved plan explicitly defines them as equivalent. It does not.
- No subject restoration, candidate execution, qualification attempt, E1, or F1 has occurred in the recorded scope.

## Accounting status

| Item | Evidence basis | Classification | Recorded expenditure |
|---|---|---|---:|
| Task 1 protocol freeze/setup | `protocol.md` records scope and outputs, but no human time ledger | UNKNOWN | `H_T1` human hours; not charged to Q0 metadata without evidence it was metadata/oracle triage |
| Task 2 runtime readiness | `environment_manifest.json` records `observed_at_utc` and commands, not human effort | UNKNOWN | `H_T2` human hours; not charged to Q0 metadata without evidence it was metadata/oracle triage |
| Task 3 baseline/applicability and artifact-entry reconnaissance | `baseline_applicability.md` is explicitly scoped to Task 3; plan cap was at most two hours for Task 3 and the source-order allowance for primary Java defect leads is four metadata hours | UNKNOWN | `H_T3` total human metadata/oracle hours; `H_T3_J` portion chargeable to the primary-Java/JaConTeBe allowance |
| Task 4 six candidate cards | `candidate_cards.md` is explicitly scoped to Task 4; plan allowed at most two hours of Q0 triage allowance | UNKNOWN | `H_T4` human metadata/oracle hours; `H_T4_J` portion chargeable to the primary-Java/JaConTeBe allowance |
| Q0 subject restoration | The supplied records state no subject was restored; no restoration artifact or subject checkout is recorded | EXACT | 0 allocated vCPU-hours; 0 human restoration hours |
| Q0 qualification attempts | No qualification attempts or execution logs exist in the supplied records | EXACT | 0 allocated vCPU-hours; 0 human restoration hours |
| E1/E2/E3/F1 | No execution records exist; these stages were not started | EXACT for recorded scope | 0 recorded expenditure |

`H_T3`, `H_T4`, `H_T3_J`, and `H_T4_J` are not assigned numerical values. The Task 3/Task 4 plan maxima are bounds on allowed work, not observations of time spent. The artifact file modification times are durable timestamps for file writes only; they do not measure human effort and are not used as hour estimates.

## Approved caps and supported remainder

| Allowance | Approved cap | Remainder supported by current evidence |
|---|---:|---:|
| Total Q0 metadata/oracle human hours | 12 human hours | `12h - (H_T3 + H_T4 + other_chargeable_Q0_metadata_hours)`; numeric remainder UNKNOWN |
| Primary Java/JaConTeBe metadata allowance | 4 human hours | `4h - (H_T3_J + H_T4_J + other_chargeable_JaConTeBe_hours)`; numeric remainder UNKNOWN |
| Q0 restoration and qualification compute | 20 allocated vCPU-hours | 20 allocated vCPU-hours remain, conditional on future recorded use; no subject restoration/qualification use is recorded |
| Per-primary-candidate restoration | <=2 human hours and <=4 allocated vCPU-hours | No primary-candidate restoration use recorded; per-candidate cap remains conditional and unchanged |
| Roster | 12 primary + 2 controls maximum | Six cards exist; no roster expansion is authorized by this ledger |
| First-active-ten-day combined ceiling | 40 allocated vCPU-hours | 40 allocated vCPU-hours remain against this ceiling for recorded subject activity; operational day counting has not started under the amendment |

The exact Q0 compute remainder is numeric because the evidence records zero subject restoration/qualification expenditure. Human-hour remainders are not numeric because actual Task 3 and Task 4 effort was not durably measured.

## Planned DBCP-65 metadata subcap

The next planned B pass is limited to:

`min(1 human hour, remaining JaConTeBe allowance, remaining 12-hour Q0 metadata allowance)`

Formally, with unknown actual prior charges:

`B_cap = min(1h, max(0, 4h - H_T3_J - H_T4_J - other_chargeable_JaConTeBe_hours), max(0, 12h - H_T3 - H_T4 - other_chargeable_Q0_metadata_hours))`

If either relevant allowance is exhausted, `B_cap = 0`. Because the prior human-hour values are UNKNOWN, this ledger does not claim a numeric B remainder. B is currently authorized only conditionally within this symbolic cap and only if its start is recorded as the first post-amendment candidate-acquisition action. At that exact start, record the UTC timestamp and charge all unsuccessful B work normally; do not later classify it as setup.

## Timing and chargeability rules

1. The September 10 freeze is historical. The elapsed interval through provenance and tooling work is not itself a Q0 operational-clock trigger.
2. The first post-amendment candidate-acquisition or restoration action starts the operational clock. Its exact timestamp is currently **NOT YET RECORDED** because no such action has occurred.
3. Metadata work before that first action is accounted for as Q0 allowance expenditure when supported, but does not backdate operational day 1.
4. After the operational clock starts, candidate acquisition, restoration, qualification, and rejection consume their ordinary allowances even when unsuccessful.
5. No future record may use model tokens, agent runtime, wall-clock interval, or file mtime as a substitute for human-hour evidence.
6. Record exact command/log elapsed times when they exist. A command runtime is execution/resource evidence, not human metadata effort.

## Next-step decision

B — one bounded DBCP-65 metadata pass — is currently authorized conditionally, not as a numeric-hour claim. It must not be repeated after the single bounded pass. If it fails, preserve DBCP-65 as `UNRESOLVED` and move conditionally to C under the remaining deterministic source order. POOL-162 restoration remains deferred unless separately justified and budgeted as a control.

## Unresolved accounting uncertainty

- Exact human time spent on Task 3 is not recorded.
- Exact human time spent on Task 4 is not recorded.
- The portions of those tasks chargeable specifically to the four-hour JaConTeBe allowance are not separable from the durable records.
- No exact numeric remaining human-hour allowance can therefore be asserted.
- The evidence does support zero Q0 restoration/qualification vCPU expenditure and no started operational Q0 clock.

---

# Addendum v2 — 2026-09-19 (append-only; entries above are historical and unchanged)

- Addendum identifier: `ci_policy_sensitivity_resource_ledger_2026-09-19_v2`
- Scope: accounting for B (DBCP-65 metadata pass), Task C (candidate acquisition), the Task C documentation repair, the roster after the DBCP split, the language/harness selection, and the reserved Task 5 cap.
- Accounting rule unchanged: agent/tool elapsed time, model tokens, wall-clock age and file mtimes are not human hours. Human effort is `UNKNOWN` wherever it was not measured.
- Where the v1 text above says the operational clock is "NOT YET RECORDED", "Six cards exist", or that B is pending, those statements were true when v1 was written (`2026-09-17T23:00:17Z`) and are superseded by this addendum; they are not rewritten.

## A1. Operational Q0 clock

| Item | Value | Evidence basis |
|---|---|---|
| Operational clock start (first post-amendment candidate-acquisition action) | `2026-09-17T23:02:26.133312834Z` | `dbcp_65_metadata_pass.md`, "Scope and clock record"; B was the first such action, as the amendment anticipated |
| Operational day 1 | 2026-09-17T23:02:26Z → 2026-09-18T23:02:26Z | derived from the start above |
| Operational day 7 gate (two qualified development episodes) | falls due `2026-09-24T23:02:26Z` | derived |
| Operational day 10 gate (four qualified episodes, ≥2 projects) | falls due `2026-09-27T23:02:26Z` | derived |
| Task C interval | `2026-09-17T23:10:59.517500913Z` → `2026-09-17T23:31:29.047893173Z` (operational day 1) | `task_c_candidate_acquisition.md` |

## A2. Accounting entries added

| Item | Evidence basis | Classification | Recorded expenditure |
|---|---|---|---:|
| B — bounded DBCP-65 metadata pass | `dbcp_65_metadata_pass.md` timestamps | Agent/tool wall clock **EXACT**: `274.903871602 s` (start → verification stop); `190.369393 s` (start → initial artifact write). Human metadata effort **UNKNOWN** | `H_B` human hours (UNKNOWN), chargeable to the Q0 metadata allowance and the JaConTeBe allowance; 0 allocated vCPU-hours; 0 human restoration hours |
| Task C — conditional candidate acquisition (Tiers 2–4) | `task_c_candidate_acquisition.md` timestamps | Agent/tool wall clock **EXACT**: `1229.530393 s`. Human metadata effort **UNKNOWN** | `H_C` human hours (UNKNOWN), chargeable to the Q0 metadata allowance (Tier 2/3/4 allowances not separable); **0 allocated vCPU-hours (EXACT); 0 human restoration hours (EXACT)** |
| Task C documentation repair (2026-09-19) | this addendum; revised `task_c_candidate_acquisition.md` | Provenance/documentation work, not candidate acquisition or restoration. Human effort **UNKNOWN** | Not charged to Q0 metadata triage; 0 compute |
| Q0 subject restoration / qualification through 2026-09-19 | no restoration artifact, checkout, image, or execution log exists | EXACT | 0 allocated vCPU-hours; 0 human restoration hours |

## A3. Caps and supported remainder after this addendum

| Allowance | Approved cap | Remainder supported by current evidence |
|---|---:|---:|
| Total Q0 metadata/oracle human hours | 12 h | `12h - (H_T3 + H_T4 + H_B + H_C + other_chargeable_Q0_metadata_hours)`; numeric remainder **UNKNOWN** |
| Primary Java/JaConTeBe metadata allowance | 4 h | `4h - (H_T3_J + H_T4_J + H_B + …)`; numeric remainder **UNKNOWN**. **Tier 1 was exited by research judgment, not by measured exhaustion** (see Task C, "Tier 1"). |
| Tier 2 (BugSwarm/CI-Bench) and Tier 3 (IDoFT) allowances | 2 h each | Charged symbolically from `H_C`; numeric remainder UNKNOWN; no promotion from either tier |
| Q0 restoration and qualification compute | 20 allocated vCPU-h | **20 remain** (EXACT: zero recorded use) |
| Per-primary-candidate restoration | ≤2 human h and ≤4 allocated vCPU-h | No use recorded; Task 5 reservation below |
| First-active-ten-day combined ceiling | 40 allocated vCPU-h | **40 remain** for the window `2026-09-17T23:02:26Z` → `2026-09-27T23:02:26Z` |
| Roster | 12 primary + 2 nuisance/control | **8 of 12 primary entries used** (after the DBCP-65a / DBCP-65b split recorded in Task C); **0 of 2 nuisance/control slots used**. Convention: cards that entered as primary product-defect candidates count against the primary ceiling even when they later serve only as stable oracle controls (POOL-162, POOL-146); the two nuisance/control slots are reserved for candidates acquired as nuisance or control subjects, so that RQ1's nuisance-blocking measurement remains possible. Per-project primary cap saturated for etcd, commons-pool, commons-dbcp and log4j. |

## A4. Roster after Task C and the DBCP split (8 entries)

| Entry | Label | Tier |
|---|---|---:|
| DBCP-65a (prepareStatement; `ec3988c…` → `4ae5004…`) | `UNRESOLVED` | 1 |
| DBCP-65b / DBCP-270 / DBCP-281 (`AbandonedTrace`; `c8034fa…` → `4bf62b3…`) | `UNRESOLVED` | 1 |
| LOG4J-38137 | `UNRESOLVED` | 1 |
| LOG4J-41214 | `EXCLUDE` | 1 |
| POOL-146 | `STABLE_CONTROL_ONLY` | 1 |
| POOL-162 | `STABLE_CONTROL_ONLY` | 1 |
| etcd-5509 | `Q0_QUALIFIED` (historical pair, blob-equivalence check passed; 16/20 focal-defect-witness, 4/20 pass on `V_bad`, 20/20 pass on `V_ok`) | 4 |
| etcd-7492 | `PRIMARY_METADATA_READY` (controlled historical-fix reversal; declared `const → var` deviation) | 4 |

**One entry is Q0-qualified as of the Task 5 pass recorded above: etcd-5509.** The other seven entries are unchanged (see the Task 5 row above and `task5_etcd5509_restoration.md` for the qualifying evidence). etcd-7492 remains `PRIMARY_METADATA_READY`; its own Task 5 restoration has not been performed.

## A5. Decisions recorded

1. **Language/harness selection (plan §5, Tier 4 rule).** Go (GoReal) is the selected fallback language/harness for the next restoration and for this month's Q0/E1 work; Java restoration is not pursued this month. Recorded on operational day 1 (within the day-7 limit). POOL-162 and POOL-146 remain deferred stable-control leads pending a separately budgeted decision.
2. **Task 5 target.** Task 5 restoration of **etcd-5509** was performed on 2026-09-19 (operational day 3; start `2026-09-17T23:02:26Z` + ~2 days). Result: Q0-qualified. See `task5_etcd5509_restoration.md`. Day-7 gate (two qualified development episodes) is not yet met: one qualified episode exists; a second (e.g. etcd-7492's own Task 5, or a non-etcd project per G1b) is required before operational day 7 (`2026-09-24T23:02:26Z`).
3. **Acquisition status.** Paused after two `PRIMARY_METADATA_READY` candidates (Task C decision, not a pre-declared gate). Resumption for a non-etcd project is required to satisfy the day-10 gate.

## A6. Reserved Task 5 cap — etcd-5509

| Cap | Reserved | Charged against |
|---|---:|---|
| Human restoration hours | ≤ 2 h | per-primary-candidate cap; measured from the recorded Task 5 start, human effort to be timed and recorded, otherwise `UNKNOWN` and the cap is treated as reached |
| Allocated vCPU-hours (build, image pull, resets, 10+10 qualification attempts per version) | ≤ 4 allocated vCPU-h | per-primary-candidate cap; counted as allocated vCPUs × elapsed runtime, including failed builds |
| Global | — | subject to the 20 allocated vCPU-h Q0 ceiling and the 40 allocated vCPU-h first-active-ten-day ceiling |
| Stop | — | move on when any cap is reached; no unattended retry of a crashed restoration; record every cap-triggered stop |

Task 5 row: `task5_start_utc = 2026-09-19T09:59:44.271208900Z`; `task5_end_utc = 2026-09-19T10:30:02.021891100Z` (last counted attempt); `task5_vcpu_hours ≈ 0.516 h` (EXACT agent/tool wall-clock, one sequential job at a time; full accounting in `task5_etcd5509_restoration.md`); `task5_human_hours = UNKNOWN, to be supplied by the researcher`. **Outcome: etcd-5509 is Q0-qualified** (16 focal-defect-witness / 4 pass on 20 `V_bad` attempts; 20/20 pass on `V_ok`). Full results, the blob-equivalence check, and two disclosed evaluator-signature corrections (one before and one after the first 10 counted attempts) are in `task5_etcd5509_restoration.md`.

**Human-hour accounting note (recorded 2026-09-19, at Task 5 start).** Task 5 is executed by an agent session with no separate human observer timing their own supervision in parallel. Per this table's own rule, an unrecorded human-hour figure would treat the cap as already reached. The researcher directing this session has elected to supply a human-hour figure after the fact rather than block start; until that figure is recorded, the ≤2 human-hour cap is provisional and not verified from durable evidence, consistent with this ledger's convention that agent/tool wall-clock time is never substituted for a human-hour measurement (see "Accounting rule", top of file). The binding, durably-evidenced cap during autonomous execution is the ≤4 allocated vCPU-hour cap and the 20/40 vCPU-hour Q0 ceilings.

## A7. Unresolved accounting uncertainty (carried forward)

- Human time for Tasks 3, 4, B and C is not recorded; no numeric remaining human-hour allowance can be asserted.
- The BugSwarm snapshot identity and IDoFT commit inspected in Task C were not recorded; those screenings are not reproducible from the durable record.
- The evidence supports zero Q0 restoration/qualification vCPU expenditure through 2026-09-19 and a started operational clock at `2026-09-17T23:02:26Z`.

---

# Addendum v3 — 2026-09-19 (append-only; entries above, including Addendum v2, are historical and unchanged)

- Addendum identifier: `ci_policy_sensitivity_resource_ledger_2026-09-19_v3`
- Scope: Task 5 restoration and Q0 qualification of candidate card C-02 (etcd-7492), its resource accounting, an appended roster follow-up for etcd-7492, and the day-7 gate status.
- Accounting rule unchanged: agent/tool elapsed time, model tokens, wall-clock age and file mtimes are not human hours. Human effort is `UNKNOWN` wherever it was not measured.
- Nothing in A1–A7 above (Addendum v2) is rewritten by this addendum; A4's roster table (etcd-7492 row: `PRIMARY_METADATA_READY`) remains as it was written and is superseded for accounting purposes only by A4-addendum-1 below, exactly as Addendum v2 itself did not rewrite v1.

## A8. Task 5 pass — etcd-7492

| Item | Value | Evidence basis |
|---|---|---|
| `task5_start_utc` | `2026-09-19T10:55:26.855778800Z` | recorded at start, not backdated |
| `task5_end_utc` (last counted attempt) | `2026-09-19T11:06:57.445310100Z` | `results.csv`, scratch workspace; `V_ok` attempt 20 |
| Counterpart type | controlled historical-fix reversal on one pinned base (`148c923c72c4aa9207173c03b775e2c0b8754067`) — **not** a historical pair | per the card's pre-declaration, confirmed by the restricted-diff check |
| Restricted-diff Task 5 check | **PASS** — the only difference between `V_bad`'s built `auth/simple_token.go` and the true historical parent's is the declared `const`→`var` move; verified both by local reconstruction and by direct extraction from the built `etcd7492-bug` image | `task5_etcd7492_restoration.md` Step 1 |
| Build deviations disclosed | one: dropped an unused `apt-get install vim python3` step from `fix.Dockerfile` (unreferenced by later steps) | `task5_etcd7492_restoration.md` Step 2 |
| Evaluator-signature correction | **none needed** — the pre-declared signature matched the first observed timeout dump exactly (contrast with etcd-5509, which needed two disclosed corrections) | `task5_etcd7492_restoration.md` Step 3 |
| `V_bad` (`etcd7492-bug`) result | 20 attempts: 18 `PASS`, 2 `FOCAL_DEFECT_WITNESS`, 0 `UNRESOLVED`, 0 `OTHER`/`HARNESS_INVALID` | `task5_etcd7492_restoration.md` Step 4 |
| `V_ok` (`etcd7492-fix`) result | 20 attempts: 20 `PASS`, 0 focal witnesses | `task5_etcd7492_restoration.md` Step 4 |
| Q0 intermittency criterion | **MET, at the minimum margin** (exactly 2 of the required ≥2 focal failures; 18 passes) | `task5_etcd7492_restoration.md`, Q0 verdict |
| Q0 verdict | **Q0_QUALIFIED** (controlled historical-fix reversal; not a historical pair) | `task5_etcd7492_restoration.md`, Q0 verdict |
| Agent/tool wall-clock (restricted-diff check through last counted attempt) | **EXACT**, `690.590 s` ≈ `0.1918` allocated vCPU-h, one sequential job at a time | `task5_etcd7492_restoration.md`, Resource accounting |
| Human restoration hours | **UNKNOWN**, to be supplied by the researcher | same convention as A6 (etcd-5509) |
| Per-candidate cap status | ≤4 allocated vCPU-h cap **not reached** (`≈0.192 h` used of `4 h`); ≤2 human-hour cap **provisional**, pending a supplied figure | `task5_etcd7492_restoration.md`, Resource accounting |
| Cumulative Q0 restoration/qualification vCPU-h (etcd-5509 + etcd-7492) | **≈0.708 h** of the 20 allocated vCPU-h Q0 ceiling and the 40 allocated vCPU-h first-active-ten-day ceiling; neither approached | sum of A6 (`≈0.516 h`) and this table's row above (`≈0.192 h`) |
| No stop triggered | correct — no cap was approached or reached during this pass | `task5_etcd7492_restoration.md`, Resource accounting |

## A4-addendum-1 — roster label update for etcd-7492 (2026-09-19, dated follow-up; A4's table above is not edited in place)

| Entry | Label as of this addendum | Tier | Note |
|---|---|---:|---|
| etcd-7492 | **`Q0_QUALIFIED`** (controlled historical-fix reversal on pinned base `148c923c…`; **not** a historical pair; 2/20 `FOCAL_DEFECT_WITNESS`, 18/20 `PASS` on `V_bad`; 20/20 `PASS` on `V_ok`) | 4 | supersedes the `PRIMARY_METADATA_READY` label recorded for this entry in A4 above and in `task_c_candidate_acquisition.md`'s card C-02; that card's own text is not rewritten, per its own "Post-Task-C addendum" convention |

**Both `PRIMARY_METADATA_READY` entries carded in Task C are now `Q0_QUALIFIED`: etcd-5509 (historical pair) and etcd-7492 (controlled historical-fix reversal). Zero `PRIMARY_METADATA_READY` primary-track entries remain on the roster.** The other six roster entries (DBCP-65a, DBCP-65b/270/281, LOG4J-38137, LOG4J-41214, POOL-146, POOL-162) are unchanged by this addendum.

## A9. Day-7 / day-10 gate status after this addendum

- **Day-7 gate** (two qualified development episodes by `2026-09-24T23:02:26Z`, per A1/A5): **MET**, on operational day 2 (`task5_start_utc` for etcd-7492 falls in the window `2026-09-18T23:02:26Z`–`2026-09-19T23:02:26Z`), five days ahead of the deadline. Two Q0-qualified episodes now exist: etcd-5509 and etcd-7492. Per A5/Task C, E1's stated preference is for two development episodes from different projects; both qualified episodes are etcd, so this preference is **not** met, though the day-7 gate's literal count requirement (two qualified episodes, project-unspecified) is met.
- **Day-10 gate** (four qualified episodes across at least two projects, due `2026-09-27T23:02:26Z`): **not met**. Two qualified episodes exist, both from the same project (etcd), and the per-project primary cap for etcd is saturated (2 of 2, per A3/A4) — no further etcd entry may be enrolled as primary. Reaching this gate requires acquisition to resume for a non-etcd project (G1b, as already flagged in `task_c_candidate_acquisition.md`'s "Scope and stop"), and at least one more Task 5 restoration/qualification after that acquisition.
- No next-step decision is recorded here beyond the gate arithmetic above; resuming acquisition for a non-etcd project is a Task C action, not a Task 5 action, and is out of this addendum's scope.

## A10. Unresolved accounting uncertainty (carried forward, additive to A7)

- Human time for the etcd-7492 Task 5 pass is not recorded; only agent/tool wall-clock (`≈0.1918 h`) is EXACT.
- All A7 items remain unresolved as stated there; this addendum adds no resolution to them.

---

# Addendum v4 — 2026-09-19 (append-only; entries above, including Addenda v2 and v3, are historical and unchanged)

- Addendum identifier: `ci_policy_sensitivity_resource_ledger_2026-09-19_v4`
- Scope: Task C resumption (C2) for a non-etcd primary candidate — metadata acquisition only; its accounting; the roster follow-up for the new card C-03; day-10 gate status. Full record: `task_c2_candidate_acquisition.md` (SHA-256 `c962b47f6e079a3345299c625993b294dc1620c74eb2e8dccd86b09faffcef7c`).
- Accounting rule unchanged: agent/tool elapsed time is not human hours; human effort is `UNKNOWN` wherever unmeasured.
- Nothing in A1–A10 is rewritten. A4-addendum-1 remains the authoritative etcd-7492 row; this addendum adds a row for grpc-go-1859 and per-ID screening dispositions for entries Task C left `NOT RECORDED`.

## A11. Task C2 pass — accounting

| Item | Value | Evidence basis |
|---|---|---|
| `taskc2_start_utc` | `2026-09-19T18:24:10.611376400Z` | recorded at the first acquisition action (pinned GoBench clone into scratch); not backdated |
| `taskc2_end_utc` (screening stop) | `2026-09-19T18:34:12.708308200Z` | recorded when screening stopped at the first defensible non-etcd candidate; record-writing followed and is provenance work |
| Screening wall clock | **EXACT**, `602.097 s` agent/tool elapsed | timestamps above |
| Human metadata effort | **UNKNOWN** | not measured |
| Restoration / qualification (human, vCPU-h) | **EXACT, zero** | nothing built or executed |
| Operational day | 2 (window `2026-09-18T23:02:26Z`–`2026-09-19T23:02:26Z`) | A1 clock start |
| Cumulative Q0 restoration/qualification vCPU-h | unchanged, **≈0.708 h** of 20 / 40 | A8 |
| Stop triggered | none by cap; screening stopped by the researcher's stated per-pass stop rule (first defensible non-etcd `PRIMARY_METADATA_READY`), which is not a pre-registered gate | `task_c2_candidate_acquisition.md`, "Scope and stop" |

## A4-addendum-2 — roster follow-up (2026-09-19; A4 and A4-addendum-1 are not edited in place)

| Entry | Label as of this addendum | Tier | Note |
|---|---|---|---:|
| grpc-go-1859 | **`PRIMARY_METADATA_READY`** (historical pair with identical test backport, pending Task 5 blob check: `V_bad` = `6c48c7f5…` + test addition; `V_ok` = `484b3ebb…`) | 4 | new card C-03; first defensible non-etcd primary candidate in the tier → project → numeric-ID order; carries a pre-declared counterpart-validity caveat (post-merge Travis hang of the fixed test, issue #1850 comment of 2018-02-14) with a binding `V_ok` adjudication rule |

Per-ID screening dispositions recorded (not carded, no roster slot consumed): cockroach_1055, grpc_649, grpc_795, grpc_1275, grpc_1424 → `SCREENED_DETERMINISTIC_LEAD` (stable-control leads by source reasoning); cockroach_1462, 30452, 30479, 36367 → `SCREENED_TEST_ONLY_FIX`; cockroach_17766, 24808, 25456, 35073, 35931 → `SCREENED_RESTORATION_COST` (C-deps build judged outside the ≤4 vCPU-h per-candidate cap — a judgment, not a measurement); etcd_6708, 7443, 10492 → `SCREENED_INELIGIBLE_PROJECT_CAP`; grpc_2391 onward → `NOT_SCREENED`.

Roster after this addendum: **9 of 12 primary entries used (3 remain); 0 of 2 nuisance/control slots used.** Per-project: etcd 2/2, grpc-go 1/2, commons-pool 2/2, commons-dbcp 2/2, log4j 2/2.

## A12. Gate status after this addendum

- **Day-7 gate:** already MET (A9); unchanged.
- **Day-10 gate** (four qualified episodes across ≥2 projects by `2026-09-27T23:02:26Z`): **NOT MET.** Two `Q0_QUALIFIED` (both etcd) + one `PRIMARY_METADATA_READY` (grpc-go). Reaching it now requires a Task 5 restoration/qualification of C-03 that passes **and** one more qualified episode (grpc-go's remaining primary slot or another project), inside the remaining source, candidate, human-hour, compute and operational-day limits.
- No Task 5 is authorized by this addendum. A Task 5 for C-03 is a separate budgeted decision (≤2 human restoration hours, ≤4 allocated vCPU-h, within the 20 / 40 vCPU-h ceilings) and must honour the card's pre-declared blob checks, timing run, signatures and `V_ok` rule.

## A13. Unresolved accounting uncertainty (carried forward, additive to A7 and A10)

- Human time for the C2 pass is not recorded.
- The resolved commits of GoReal's unpinned `go get -d` dependencies for grpc-go-1859 are not yet known; they must be recorded at Task 5 image build or the environment is not reproducible from the durable record.

---

# Addendum v5 — 2026-09-22 (append-only; entries above, including Addenda v2–v4, are historical and unchanged)

- Addendum identifier: `ci_policy_sensitivity_resource_ledger_2026-09-22_v5`
- Scope: Task 5 restoration and Q0 qualification attempt for card C-03 (grpc-go-1859), its accounting, the roster follow-up, and day-10 gate status. Full record: `task5_grpc1859_restoration.md` (SHA-256 `56c3ade0675621605a1f0c9e08f2f2efcbd620cd41d97f770d473d9c92970fa3`).
- Accounting rule unchanged. Nothing in A1–A13 is rewritten.

## A14. Task 5 pass — grpc-go-1859

| Item | Value | Evidence basis |
|---|---|---|
| `task5_start_utc` | `2026-09-22T17:44:33.746614400Z` | recorded at start, not backdated |
| `task5_end_utc` | `2026-09-22T18:00:14.143628200Z` | recorded at end |
| Operational day | 5 | A1 clock start `2026-09-17T23:02:26Z` |
| Counterpart type | **historical pair with identical test backport** — the pre-declared fallback to a controlled reversal was **not** needed | Step 1 blob check |
| Blob-equivalence check | **PASS** — reconstructed `V_bad` equals the historical parent `6c48c7f5…` byte-for-byte on both transport files (`717e4192…`, `5233d6f3…`); test file identical in both images (`6a583182…`); verified again inside both built images | `task5_grpc1859_restoration.md` Step 1 |
| Build deviations disclosed | two: (1) dropped an unused `apt-get install vim python3` step from `fix.Dockerfile`; (2) **forced** replacement of GoReal's unpinned `go get -d` with identical pinned 2018-dated clones in both images (master heads fail on Go 1.13 with `package embed`), plus `golang.org/x/text` added as a required transitive dep | Step 2 |
| Dependency reproducibility | **RESOLVED** — resolved commits recorded inside both images at `/go/dep_versions.txt` and verified identical; closes the A13 gap for this candidate | Step 2 |
| Evaluator-signature correction | **none needed** — all exploratory failures matched pre-declared signature (a) verbatim (contrast: etcd-5509 needed two corrections) | Step 3 |
| Notable environment finding | the subject's committed test certificates are **expired** (`ca.pem` to 2024-11-08, `server1.pem` to 2025-11-01); all four TLS environments block in `Dial`. Identical on both versions; `HARNESS_INVALID`, never a focal witness. The pre-declared stack-level signature correctly refused to score these as defect witnesses | Step 3 |
| Frozen protocol deviation | `-only_env tcp-clear-v1-balancer` (upstream flag, test source unmodified, identical on both versions), chosen as the **first** clear-text entry of the upstream `allEnv` order — **not** the higher-rate `tcp-clear` — to avoid selecting on observed failure rate | Step 4 |
| `V_bad` result | 20 attempts: **19 `PASS`, 1 `FOCAL_DEFECT_WITNESS_A`**, 0 unresolved/other | Step 5 |
| `V_ok` result | 20 attempts: **20 `PASS`**, 0 focal witnesses; the card's counterpart-validity caveat did not reproduce | Step 5 |
| Q0 intermittency criterion | **NOT MET** — 1 focal failure against the required ≥2 (passes were abundant) | Step 5 |
| **Q0 verdict** | **`Q0_NOT_QUALIFIED`** (primary track). A threshold failure, not a demonstration of determinism: the `V_bad` stream is genuinely mixed at an estimated 5–10 % rate | Step 5 |
| Rescue attempts | **none** — no attempts beyond the pre-declared 20, no post-hoc environment switch, no relabelling; enumerated in "What was deliberately not done" | Step 5 |
| Task 5 wall clock | **EXACT**, `940.4 s` ≈ `0.2612` allocated vCPU-h (counted attempts: `60.8 s` ≈ `0.0169` h) | timestamps |
| Human restoration hours | **UNKNOWN**, to be supplied by the researcher | A6/A8 convention |
| Per-candidate cap status | ≤4 allocated vCPU-h **not reached** (6.5 % used); ≤2 human-hour cap **provisional** | above |
| Cumulative Q0 restoration/qualification vCPU-h | **≈0.969 h** of the 20 h Q0 and 40 h first-ten-day ceilings; neither approached | 0.708 (A8) + 0.261 |
| Stop triggered by a cap | none | — |

## A4-addendum-3 — roster follow-up for grpc-go-1859 (2026-09-22; earlier roster tables not edited in place)

| Entry | Label as of this addendum | Tier | Note |
|---|---|---:|---|
| grpc-go-1859 | **`Q0_NOT_QUALIFIED`** (historical pair with identical test backport, blob check passed; 1/20 `FOCAL_DEFECT_WITNESS_A` and 19/20 `PASS` on `V_bad`; 20/20 `PASS` on `V_ok`) | 4 | supersedes the `PRIMARY_METADATA_READY` label recorded in A4-addendum-2 and in card C-03; those records are not rewritten. Retains value as a named non-primary demonstration case (option 3 in the Task 5 record): the mechanism reproduced and the counterpart is the roster's cleanest historical pair |

Roster: **9 of 12 primary entries used (3 remain); 0 of 2 nuisance/control slots used.** Qualified episodes remain **two, both etcd**. Zero `PRIMARY_METADATA_READY` entries remain.

## A15. Gate status after this addendum

- **Day-7 gate:** MET since operational day 2 (A9); unchanged. **E1 remains executable** on etcd-5509 + etcd-7492.
- **Day-10 gate** (four qualified episodes across ≥2 projects by `2026-09-27T23:02:26Z`): **NOT MET, and now materially at risk.** It would require **two** further qualified non-etcd episodes within five days, from a roster with no metadata-ready candidate remaining and a screening prior that most surviving GoReal entries are deterministic.
- **G1b applies if the gate is missed:** "No E2. Finish small feasibility report and trigger F1 where possible." This addendum authorises no cap increase, no broadened defect definition, and no re-run of C-03 under a different environment.
- No Task C resumption and no Task 5 is authorised by this addendum.

## A16. Unresolved accounting uncertainty (carried forward, additive to A7, A10, A13)

- Human time for this pass is not recorded.
- A13's dependency-reproducibility gap is **closed for grpc-go-1859 only**; it remains open for any future GoReal candidate.
- The `V_bad` failure-rate estimate (1/20 counted, 3/20 exploratory across two environments) is imprecise and host-specific; no population rate is claimed.

---

# Addendum v6 — 2026-09-22 (append-only; entries above, including Addenda v2–v5, are historical and unchanged)

- Addendum identifier: `ci_policy_sensitivity_resource_ledger_2026-09-22_v6`
- Scope: durable preservation of the execution artifacts for all three Task 5 passes, and the reproducibility defect that made this necessary. No experiment, restoration, qualification or gate decision is changed by this addendum.

## A17. Task 5 execution artifacts are now in the repository

`research_runs/ci_sensitivity_2026_09/task5_artifacts/` now holds the build recipes, frozen protocol, runner scripts, per-attempt ledgers and raw attempt logs for **etcd-5509, etcd-7492 and grpc-go-1859** (206 files, ≈1.4 MB, listed with sizes and SHA-256 prefixes in `MANIFEST.csv`). See that directory's `README.md`.

**The defect being corrected.** All three Task 5 records state that their results lived in an ephemeral scratch workspace and were "not committed". The durable record therefore carried the summary tables for three qualification verdicts — including the two episodes that satisfy the day-7 gate and are E1's intended subjects — with no preserved evidence an independent reader could check them against. Session-scoped temporary directories are wiped without warning.

This is the same class of defect already recorded in A7 (Task C's BugSwarm snapshot identity and IDoFT commit "not recorded; those screenings are not reproducible from the durable record") and A13 (unpinned dependency versions). Those entries named the problem for *metadata* passes. The identical problem was present for every *execution* pass and was not named until now.

**Recovery was luck, not design.** The two earlier sessions' temporary directories happened to survive. Had they been cleaned, the etcd evidence would have been unrecoverable and both qualified episodes would have rested on their summary tables alone.

**Scope note on `AGENTS.md`.** "Large datasets, generated artifacts, credentials, and local agent/runtime state stay out of Git" correctly excludes the Docker images (1.73 GB each) and the GoBench clones, which are not preserved. It does not cover build recipes, frozen protocols, runner scripts or per-attempt ledgers; treating those as scratch was a misreading.

## A18. Standing rule adopted

Every future execution pass writes its recipes, frozen protocol, runner and per-attempt ledger **into the repository as it runs**, not afterwards from scratch. Raw logs follow when their total stays in the low megabytes. This applies to E1, E2, E3 and F1 as well as to any further Q0 restoration.

## A19. What remains not durably recorded

- The Docker images. Rebuildable from the preserved recipes, but not bit-reproducible: the `golang:1.13` base tag and each subject's `git clone` resolve at build time. For grpc-go-1859 the dependency commits are pinned and were captured inside the images at `/go/dep_versions.txt`; for the two etcd passes the dependency state was whatever their recipes resolved at build time and was never recorded. **A13's dependency gap therefore remains open for etcd-5509 and etcd-7492**, and cannot now be closed retrospectively.
- Human hours for every pass, which remain `UNKNOWN` per this ledger's accounting rule.
- The artifact salvage itself consumed no measured compute and is provenance work; human effort `UNKNOWN`.

---

# Addendum v7 — 2026-09-25 (append-only; entries above, including Addenda v2–v6, are historical and unchanged)

- Addendum identifier: `ci_policy_sensitivity_resource_ledger_2026-09-25_v7`
- Scope: the C3 metadata pass for two further non-etcd primary candidates, the roster follow-up and the day-10 gate status.
- Full record: `task_c3_candidate_acquisition.md` (SHA-256 `a2434a42765e45199c4e55b97f643467025045196b99da14e3bd5b76c8b0607a`).
- The accounting rule is unchanged, and nothing in A1–A19 is rewritten.

## A20. C3 pass

| Item | Value | Evidence basis |
|---|---|---|
| Pass window | `2026-09-25T08:06:08.831Z` → screening stop `08:12:12.479Z`; card checks to `08:13:35.878Z` | recorded at start and stop, not backdated |
| Operational day | 8 | A1 clock start `2026-09-17T23:02:26Z` |
| Screening wall clock | **EXACT**, 363.648 s agent/tool elapsed | timestamps |
| Order traversed | GoReal orders 21–26 (grpc_2391 → istio_17860), continuing C2 | `task_c3_candidate_acquisition.md` |
| Carded | **C-04 grpc-go-2391** and **C-05 istio-17860**, both `PRIMARY_METADATA_READY`, both historical pairs with an identical test backport, blob-checked against their historical parents | same |
| Dispositioned, not carded | grpc_3017 `SCREENED_INELIGIBLE_PROJECT_CAP` (also a deterministic lead); hugo_3251 and hugo_5379 `SCREENED_DETERMINISTIC_LEAD`; istio_16224 `SCREENED_TEST_ONLY_FIX` | same |
| Restoration/qualification vCPU-h | **EXACT, zero** | nothing built or executed |
| Human metadata effort | **UNKNOWN** | accounting rule |

## A4-addendum-4 — roster follow-up (2026-09-25; earlier roster tables not edited in place)

| Entry | Label as of this addendum | Tier | Note |
|---|---|---:|---|
| grpc-go-2391 | **`PRIMARY_METADATA_READY`** (historical pair with identical test backport; `V_bad` = `39444b99…` + test, `V_ok` = `ff2aa059…`) | 4 | card C-04; fills grpc-go's second primary slot |
| istio-17860 | **`PRIMARY_METADATA_READY`** (historical pair with identical test backport; `V_bad` = `7a9a996f…` + upstream test **unchanged**, `V_ok` = `c6e91302…`) | 4 | card C-05; GoReal's `V_bad`-only test instrumentation is **not** adopted |

- **Roster:** **11 of 12 primary entries used (1 remains); 0 of 2 nuisance/control slots used.**
- **Per-project:** etcd 2/2, grpc-go 2/2, istio 1/2, commons-pool 2/2, commons-dbcp 2/2, log4j 2/2.

## A21. Gate status after this addendum

- **Day-7 gate:** MET (A9); unchanged.
- **Day-10 gate** (four qualified episodes across ≥2 projects by `2026-09-27T23:02:26Z`): **NOT MET.**
  - Meeting it now requires Task 5 restoration and qualification of **both** C-04 and C-05 to pass, which would give 4 episodes across 3 projects.
  - Each Task 5 is a separate budgeted decision: ≤2 human restoration hours and ≤4 allocated vCPU-hours per candidate.
  - This addendum authorises no Task 5, no cap increase and no broadened defect definition.
- **Q0 compute so far:** ≈0.969 of 20 allocated vCPU-hours (A14). The first-ten-days ceiling of 40 also carries E1's 12.71 (span basis, E1 AMENDMENTS §8), for a combined total of ≈13.7.

---

# Addendum v8 — 2026-09-25 (append-only; entries above, including Addenda v2–v7, are historical and unchanged)

- Addendum identifier: `ci_policy_sensitivity_resource_ledger_2026-09-25_v8`
- Scope: Task 5 restoration and Q0 qualification of cards C-04 (grpc-go-2391) and C-05 (istio-17860), the C4 metadata pass that carded C-06 (kubernetes-26980), the roster follow-up and the day-10 gate status.
- Full records:
  - `task5_grpc2391_restoration.md` (SHA-256 `4da215184ea376a2bee764e16d29684fd7cf8e1ef710a3d66fe0048aed469ffd`)
  - `task5_istio17860_restoration.md` (SHA-256 `c940f885e7936981d77b95c6d36392f5fcf1c0ba004d2899a001984151898d75`)
  - `task_c4_candidate_acquisition.md` (SHA-256 `0bc78bd5d0786dea117e90867f127fa73a3b641deddf8dec565ccfd5915a66c1`)
- The accounting rule is unchanged, and nothing in A1–A21 is rewritten.

## A22. Task 5 pass — grpc-go-2391 (card C-04)

| Item | Value | Evidence basis |
|---|---|---|
| Authority | researcher's Task 5 authorisation of 2026-09-25, covering C-04 then C-05 | record, "Authority and timing" |
| Task 5 window | `2026-09-25T08:18:58.909Z` → `08:28:59.352Z` | recorded at start and end, not backdated |
| Operational day | 8 | A1 clock start `2026-09-17T23:02:26Z` |
| Counterpart type | historical pair with identical test backport | card C-04 |
| Blob-equivalence check | **PASS** — both images match the card's pre-declared blob IDs | record Step 1 |
| Build deviations disclosed | one: module mode from the revision's own `go.mod` and a shallow fetch of the exact commit, in place of GoReal's unpinned GOPATH `go get -d` and full clone; identical on both images; decided before any run | record Step 2 |
| Dependency reproducibility | **RESOLVED** — 18 modules pinned by the project's `go.mod`, identical in both images (`dep_versions_{bug,fix}.txt`); closes the A13/A19 gap for this candidate | record Step 2 |
| Evaluator-signature correction | **none needed** — exploratory failures matched signature (a) verbatim | record Step 3 |
| `V_bad` result | 20 attempts: **18 `FOCAL_DEFECT_WITNESS_A`, 2 `PASS`**, 0 unresolved/invalid | record Step 5 |
| `V_ok` result | 20 attempts: **20 `PASS`**, 0 focal witnesses | record Step 5 |
| Q0 intermittency criterion | **MET, at the minimum** for passes (2 of the required ≥2) | record, "Result" |
| **Q0 verdict** | **`Q0_QUALIFIED`** | record |
| Rescue attempts | none needed or made | record, "What was deliberately not done" |
| Task 5 wall clock | **EXACT**, `600.4 s` ≈ `0.1668` allocated vCPU-h (counted attempts `369.0 s` ≈ `0.1025` h) | timestamps |
| Human restoration hours | **UNKNOWN** (agent-executed pass) | accounting rule |
| Per-candidate cap status | ≤4 allocated vCPU-h not reached (4.2 % used); ≤2 human-hour cap provisional | above |

## A23. Task 5 pass — istio-17860 (card C-05)

| Item | Value | Evidence basis |
|---|---|---|
| Authority | same authorisation as A22 | record, "Authority and timing" |
| Task 5 window | `2026-09-25T08:29:46.682Z` → `08:37:04.156Z` | recorded at start and end, not backdated |
| Operational day | 8 | A1 clock |
| Counterpart type | historical pair with identical test backport; upstream test **unchanged** (GoReal's `V_bad`-only instrumentation not adopted) | card C-05 |
| Blob-equivalence check | **PASS** | record Step 1 |
| Build deviations disclosed | one environment deviation, pre-declared on the card: GoReal's `replace bitbucket.org/ww/goautoneg => github.com/munnerz/goautoneg …` line, applied to **both** images (GoReal applies it to the bug image only). Build attempt 1 failed on both images with a Bitbucket 404 before the line was added; no test had run | record Step 2 |
| Dependency reproducibility | **RESOLVED** — 493 modules pinned by istio's own `go.sum`, identical in both images; closes the A13/A19 gap for this candidate | record Step 2 |
| Evaluator-signature correction | **none needed** | record Step 3 |
| `V_bad` result | 20 attempts: **20 `FOCAL_DEFECT_WITNESS_A`, 0 `PASS`** | record Step 5 |
| `V_ok` result | 20 attempts: **20 `PASS`** | record Step 5 |
| Q0 intermittency criterion | **NOT MET** — 0 passes against the required ≥2 | record, "Result" |
| **Q0 verdict** | **`Q0_NOT_QUALIFIED`** (primary track); retained as **`STABLE_CONTROL_ONLY`**. Zero passes in 20 is not a proof of determinism | record |
| Rescue attempts | **none** — no extra attempts, no timeout, load, `-test.cpu` or GOMAXPROCS change, no switch to the instrumented test, no relabelling | record, "What was deliberately not done" |
| Task 5 wall clock | **EXACT**, `437.5 s` ≈ `0.1215` allocated vCPU-h, including the failed first build (counted attempts `129.5 s`) | timestamps |
| Human restoration hours | **UNKNOWN** (agent-executed pass) | accounting rule |
| Per-candidate cap status | ≤4 allocated vCPU-h not reached | above |
| Control value | a candidate for the "B2" stable-defect control deferred by E1 AMENDMENTS §7.4. Enrolment is a separate budgeted decision and is **not** made here | record, "Result" |

## A24. C4 pass

| Item | Value | Evidence basis |
|---|---|---|
| Pass window | after `2026-09-25T08:37:04.156Z` (exact start not recorded) → `08:40:22.131Z` | `task_c4_candidate_acquisition.md` |
| Operational day | 8 | A1 clock |
| Screening wall clock | **at most 198 s** agent/tool elapsed (upper bound, because the start was not recorded) | timestamps |
| Order traversed | GoReal orders 27–32 (istio_18454 → kubernetes_26980), continuing C3; orders 33–40 `NOT_SCREENED` | same |
| Carded | **C-06 kubernetes-26980** (`TestPopReleaseLock`), `PRIMARY_METADATA_READY`, historical pair with identical test backport, blob-checked against its historical parent | same |
| Dispositioned, not carded | istio_18454, kubernetes_1321, kubernetes_25331 `SCREENED_DETERMINISTIC_LEAD`; kubernetes_16851 `SCREENED_TEST_ONLY_FIX`; kubernetes_11298 **`SCREENED_NOT_ISOLATABLE`** (new disposition, defined in that record: two defects fixed together; the researcher may overrule) | same |
| Restoration/qualification vCPU-h | **EXACT, zero** | nothing built or executed |
| Human metadata effort | **UNKNOWN** | accounting rule |

## A4-addendum-5 — roster follow-up (2026-09-25; earlier roster tables not edited in place)

| Entry | Label as of this addendum | Tier | Note |
|---|---|---:|---|
| grpc-go-2391 | **`Q0_QUALIFIED`** (18/20 focal, 2/20 pass on `V_bad`; 20/20 pass on `V_ok`) | 4 | supersedes the `PRIMARY_METADATA_READY` label in A4-addendum-4 |
| istio-17860 | **`Q0_NOT_QUALIFIED`**, retained as **`STABLE_CONTROL_ONLY`** (20/20 focal on `V_bad`; 20/20 pass on `V_ok`) | 4 | supersedes the `PRIMARY_METADATA_READY` label in A4-addendum-4 |
| kubernetes-26980 | **`PRIMARY_METADATA_READY`** (historical pair with identical test backport; `V_bad` = `98f0d22b…` + upstream test, `V_ok` = `628af356…`) | 4 | card C-06; intermittency unmeasured |

- **Roster:** **12 of 12 primary entries used (0 remain); 0 of 2 nuisance/control slots used.** No further primary candidate can be carded this month.
- **Per-project:** etcd 2/2, grpc-go 2/2, istio 1/2, kubernetes 1/2, commons-pool 2/2, commons-dbcp 2/2, log4j 2/2.
- **Qualified episodes:** **three across two projects** — etcd-5509, etcd-7492, grpc-go-2391.

## A25. Gate status after this addendum

- **Day-7 gate:** MET (A9); unchanged.
- **Day-10 gate** (four qualified episodes across ≥2 projects by `2026-09-27T23:02:26Z`): **NOT MET; one episode short.** The project-diversity condition is already satisfied.
  - The only remaining route is Task 5 of **C-06 kubernetes-26980**. If it qualifies, the episode condition is met (4 episodes across 3 projects).
  - If it does not qualify, the primary roster is exhausted and **G1b applies**: no E2; finish the small feasibility report and trigger F1 where possible.
  - C-06 Task 5 is a separate budgeted decision (≤2 human restoration hours, ≤4 allocated vCPU-hours) and is **not** authorised by this addendum.
- **G1b's "E2 affordable" condition** is unresolved: it depends on the vCPU basis used for the E2 projection, which is the researcher's decision.
- This addendum authorises no Task 5, no cap increase, no broadened defect definition and no enrolment of istio-17860 as a control.
- **Q0 compute so far:** ≈**1.257** of 20 allocated vCPU-hours (0.969 in A14 + 0.1668 + 0.1215). Including E1's 12.71 (span basis, E1 AMENDMENTS §8), the first-ten-days total is ≈**13.97** of 40.

## A26. Unresolved accounting uncertainty (carried forward, additive to A7, A10, A13, A16, A19)

- Human time for all three passes is not recorded.
- The C4 pass start was not recorded; its 198 s is an upper bound.
- The `V_bad` rates (18/20 for grpc-go-2391, 20/20 for istio-17860) are host-specific and imprecise; no population rate is claimed.
- The Docker images for both Task 5 passes are not preserved; the recipes and per-attempt ledgers are, in `task5_artifacts/grpc2391/` and `task5_artifacts/istio17860/` (ledger A18).

---

# Addendum v9 — 2026-09-25 (append-only; entries above, including Addenda v2–v8, are historical and unchanged)

- Addendum identifier: `ci_policy_sensitivity_resource_ledger_2026-09-25_v9`
- Scope: Task 5 restoration and Q0 qualification of card C-06 (kubernetes-26980), the roster follow-up, and day-10 gate status after the primary roster is exhausted.
- Full record: `task5_k8s26980_restoration.md` (SHA-256 `703ccf0497d216b1295d5e039b09fb101e7b26a18389f6a33ed42c605a63496a`; stored `-text`).
- The accounting rule is unchanged, and nothing in A1–A26 is rewritten.

## A27. Task 5 pass — kubernetes-26980 (card C-06)

| Item | Value | Evidence basis |
|---|---|---|
| Authority | researcher's Task 5 authorisation of 2026-09-25 ("run C-06 Task 5"), given after PR #5 was merged | record, "Authority and timing" |
| Task 5 window | `2026-09-25T09:01:48.403Z` → `09:07:34.530Z` | recorded at start and end, not backdated |
| Operational day | 8 | A1 clock start `2026-09-17T23:02:26Z` |
| Counterpart type | historical pair with identical test backport; upstream test **unchanged** (GoReal's `V_bad`-only `t.Errorf` → `panic` edit not adopted) | card C-06 |
| Blob-equivalence check | **PASS** — `shared_informer.go` `ce9ddf2c…` (`V_bad`, = first parent) / `c557bf97…` (`V_ok`); `processor_listener_test.go` `ffd72d8f…` in both | record Step 1 |
| Build deviations disclosed | one: shallow fetch of the exact merge commit in place of a full clone and reset; GoReal's unused `apt install` steps dropped on both images. Same `golang:1.12` toolchain as GoReal, GOPATH mode | record Step 2 |
| Dependency reproducibility | **NOT APPLICABLE** — dependencies vendored in-tree; `Godeps/Godeps.json` identical in both images (`980fd6ac…`); nothing resolved at build time | record Step 2 |
| Evaluator-signature correction | **none** — no focal failure occurred at any point, so signature (a) stayed exactly as pre-declared | record Step 3 |
| Exploratory runs (uncounted) | `V_ok` 2/2 `PASS`; `V_bad` 5/5 `PASS`. No setting was changed in response | record Step 3 |
| `V_bad` result | 20 attempts: **0 `FOCAL_DEFECT_WITNESS_A`, 20 `PASS`**, 0 unresolved/invalid | record Step 5 |
| `V_ok` result | 20 attempts: **20 `PASS`** | record Step 5 |
| Q0 intermittency criterion | **NOT MET** — 0 focal failures against the required ≥2 | record, "Result" |
| **Q0 verdict** | **`Q0_NOT_QUALIFIED`** (primary track). Zero failures in 20 is not a proof that the failing interleaving is impossible. No secondary (control) role is proposed, because the defect never manifested | record |
| Rescue attempts | **none** — no extra attempts; no `-test.cpu`, GOMAXPROCS, pinning, load or stress; no instrumented test; no relabelling | record, "What was deliberately not done" |
| Task 5 wall clock | **EXACT**, `346.1 s` ≈ `0.0961` allocated vCPU-h (counted attempts: span `30.9 s`, attempt-sum `24.7 s`) | timestamps |
| Human restoration hours | **UNKNOWN** (agent-executed pass) | accounting rule |
| Per-candidate cap status | ≤4 allocated vCPU-h not reached (2.4 % used); ≤2 human-hour cap provisional | above |

## A4-addendum-6 — roster follow-up (2026-09-25; earlier roster tables not edited in place)

| Entry | Label as of this addendum | Tier | Note |
|---|---|---:|---|
| kubernetes-26980 | **`Q0_NOT_QUALIFIED`** (0/20 focal, 20/20 pass on `V_bad`; 20/20 pass on `V_ok`) | 4 | supersedes the `PRIMARY_METADATA_READY` label in A4-addendum-5 |

- **Roster:** **12 of 12 primary entries used (0 remain); 0 of 2 nuisance/control slots used.** No `PRIMARY_METADATA_READY` entry remains.
- **Qualified episodes (final for this roster):** **three across two projects** — etcd-5509, etcd-7492, grpc-go-2391.
- **Primary-track outcomes across the GoReal Task 5 passes:** 1 `Q0_QUALIFIED` (grpc-go-2391) and 3 `Q0_NOT_QUALIFIED` (grpc-go-1859 at 1 focal / 19 pass; istio-17860 at 20 / 0; kubernetes-26980 at 0 / 20). These are meaningful negative results and are preserved as such.

## A28. Gate status after this addendum

- **Day-7 gate:** MET (A9); unchanged.
- **Day-10 gate** (four qualified episodes across ≥2 projects by `2026-09-27T23:02:26Z`): **the episode condition cannot be met under the plan as written.** Three episodes are qualified and no primary roster entry remains to supply a fourth.
  - The gate is formally assessed at its deadline; nothing available under current authorisations can change the outcome before then.
- **G1b therefore applies:** "No E2. Finish small feasibility report and trigger F1 where possible" (`NEXT_RESEARCH_ACTION_PLAN.md`, gate table).
  - The E2 affordability basis (A25) no longer decides G1b, since the episode condition already fails. It stays relevant only as a descriptive figure for the feasibility report.
  - F1 has its own 10 allocated vCPU-hour ceiling (plan compute ceiling; F1 in plan §9). Its start is a separate decision and is **not** authorised here.
- **Guard against post-hoc rescue:** extending the roster, reclassifying a `Q0_NOT_QUALIFIED` entry, broadening the defect definition or re-running any candidate under a different environment would each be decided after seeing these results. Any such step needs an explicit, disclosed amendment by the researcher. This addendum authorises none of them.
- **Q0 compute so far:** ≈**1.353** of 20 allocated vCPU-hours (1.257 in A25 + 0.0961). Including E1's 12.71 (span basis, E1 AMENDMENTS §8), the first-ten-days total is ≈**14.07** of 40.

## A29. Unresolved accounting uncertainty (carried forward, additive to A7, A10, A13, A16, A19, A26)

- Human time for this pass is not recorded.
- The `V_bad` outcome (0/20 counted, 0/5 exploratory) is host-specific. The explanation for the skew (Go's `runnext` hand-off favouring the last-started goroutine) is source reasoning, not measured.
- The Docker images are not preserved; the recipes and per-attempt ledgers are, in `task5_artifacts/k8s26980/` (ledger A18).
- The `--family-alpha 0.025` choice (E1 AMENDMENTS §6.2) still awaits the researcher's acceptance.
