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
