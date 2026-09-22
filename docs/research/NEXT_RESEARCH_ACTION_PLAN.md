# Next research action plan: CI policy sensitivity

## Material Passport

- **Date:** 2026-09-08.
- **Purpose:** Specify the next 30 days of executable research, with a bounded artifact-qualification stage and explicit stopping decisions.
- **Origin:** Academic-research-suite, experiment-agent, inline plan mode; single agent. Its experiment template and statistical guidance informed this plan. The user's request for a decisive design replaces the workflow's default Socratic dialogue. No delegation, secondary model, or review simulation was used.
- **Version:** `ci_policy_sensitivity_plan_v1`.
- **Verification status:** **PLAN ONLY — experiments unexecuted and subjects unqualified.** Repository facts and public artifact descriptions were inspected; no environments were restored in this pass.
- **Repository baseline:** `d967dbaaec257613c3e1f2440866801c71d0c00e`, branch `research/revival-2026`.
- **Write scope of this pass:** This document only. All paths describing future manifests, code, logs and results below are proposed outputs, not files created by this pass. No implementation change, execution, installation or commit is implied by saving the plan.
- **Reading labels:** **Evidence** means inspected source or an explicitly attributed report. **Inference** means interpretation. All designs, budgets, thresholds and schedules are **Proposals**. **Open** means unresolved. Numerical gates are investment criteria, not universal safety tolerances.

## 1. Decision, objective and authority

**Working research question:** Under a fixed, documented execution protocol, does accepting a CI job after a passing retry reduce verified nuisance blocking while materially reducing detection of independently validated intermittent product defects, and do ordinary repeated-run assessments already reveal that trade-off?

**Decision:** Keep the direction “assess whether CI optimization policies preserve sensitivity to real intermittent defects while reducing nuisance failures,” but begin with **one job-retry policy**. Selection interactions are a conditional follow-up. Quarantine is excluded from the first month: trivially suppressing the only detecting test would create an easy result without establishing a useful contribution.

**Exact 30-day objective:** By day 30, either (a) deliver a reproducible case-level assessment of one-attempt versus accept-on-pass, maximum-three-attempt job execution on four independently justified intermittent defect episodes from at least two projects, using fresh outcome blocks, acceptable counterparts, cost accounting and strong assessment baselines; or (b) deliver a documented no-go explaining artifact failure, insufficient measurement precision, or lack of additional value over existing assessment, with the bounded evidence-validity fallback where feasible. No platform or new predictive model is a deliverable.

The four-episode target is a feasibility/measurement cohort. It cannot establish industry prevalence, broad transfer, or a definitive publication-quality effectiveness estimate. “Existing methods suffice for this cohort” is an acceptable outcome. Failure to resolve the question is recorded as inconclusive, not equivalence.

### Chronological reconciliation

| Prior document | What it established or proposed | Authority for this month |
|---|---|---|
| [August findings](change-aware-tcp-findings-2026-08.md), 2026-08-25 | Airavata null and reported HBase/Hive comparisons; strong causal interpretations of temporal signatures | Historical experimental record. Preserve results; do not use persistence as product-defect ground truth |
| [ADAPTIVE_CI_RESEARCH_PROGRAM.md](ADAPTIVE_CI_RESEARCH_PROGRAM.md), 2026-09-05 | A bounded investigation controller and action-bank design | **Superseded for near-term execution.** Retain provenance, availability-time and abstention principles; do not build its controller |
| [INDEPENDENT_RESEARCH_VISION.md](INDEPENDENT_RESEARCH_VISION.md), 2026-09-06 | Favored test-maintenance validation and proposed alternative futures | **Historical alternatives.** No repair-validator implementation this month |
| [RESEARCH_DIRECTION_DECISION.md](RESEARCH_DIRECTION_DECISION.md), 2026-09-07, earlier | Ranked maintenance validation first and prescribed its 30-day sprint | **Superseded for near-term execution, including its source priorities, sample sizes and budget.** Do not combine that sprint with this one |
| [ORIGINALITY_AUDIT_AND_NEW_IDEAS.md](ORIGINALITY_AUDIT_AND_NEW_IDEAS.md), 2026-09-07, later | Identified MeteoR and YourBase overlap; favored intermittent-defect policy sensitivity | Governs the revised novelty boundary. **This plan replaces its Section 6 ten-day experiment and its immediate ordering of work** with qualification, E1, then conditional E2/E3 |
| [INDUSTRY_VALUE_AND_PERSONAL_ASSESSMENT.md](INDUSTRY_VALUE_AND_PERSONAL_ASSESSMENT.md), 2026-09-07, latest | Explains industrial motivation and calls for credible executable evidence | Motivation retained. It supplies no deployment result or qualified cohort |
| [RESEARCH_STATE.md](RESEARCH_STATE.md), [TRAJECTORY.md](TRAJECTORY.md), [EXPERIMENTS.md](EXPERIMENTS.md), [DECISIONS.md](DECISIONS.md) | Routing documents currently largely containing scaffolding | Preserve unchanged. This is the operational plan for this requested sprint, not a silent rewrite of those records |

**Evidence:** The inspected `regression_labels` function in [step3_regapfd.py](../../pipeline/step3_regapfd.py) labels next-execution persistence. Neither that label nor a high lifetime flip count identifies a causal product defect. The raw TCP histories contain observations, not the unobserved interventions required here.

**Inference:** The main contradiction in older recommendations is resolved by the newer originality assessment. No reopening of the overall vision is needed. The near-term uncertainty is executability and added scientific value.

## 2. Questions that need answers

| ID | Falsifiable question / hypothesis | Null or stopping alternative | Experiment |
|---|---|---|---|
| RQ1 | Does accept-on-pass retry produce a material loss of defect-supported blocking, while reducing verified nuisance blocking, on qualified cases? Provisional material sensitivity loss: 0.10 absolute probability | Loss is below that margin, nuisance reduction is absent/unidentifiable, or intervals remain too wide. These are different outcomes | E1 calibration, E2 fresh assessment |
| RQ2 | Does a decision-relevant distinction remain after a strong ordinary assessment using repeated, paired, signature-aware outcomes and the same oracle evidence? | Ordinary assessment identifies all resolved trade-offs; no new assessor is warranted. A one-shot baseline missing a loss is insufficient evidence of novelty | E2 |
| RQ3, conditional | Does a pre-existing change-based selector alter the retry trade-off enough to change a practical assessment conclusion, beyond merely skipping the sole detector? | No eligible selector/context exists, effects are trivial, or the interaction is smaller than 0.10 on the declared probability scale / unresolved | E3 only after its eligibility gate |

Q0 separately answers a feasibility question: can sufficiently trustworthy artifacts be qualified within a fixed recovery budget? It is not an effectiveness experiment.

## 3. Why the earlier ten-day factorial study is not Experiment 1

The originality audit proposed eight episodes, eight selection/retry/quarantine configurations, two versions and 20 condition blocks: 2,560 policy runs before counting individual attempts and restoration work.

**Decision: do not execute that design as E1.**

1. There is no qualified eight-episode cohort. The cited YourBase artifact is an assessment lead, not a demonstrated source of acceptable/intermittently defective pairs.
2. Selection needs eligible-test and change metadata. Quarantine needs an authentic prior policy/history. Neither follows from having a reproducer.
3. Selection changes execution context; eight policy cells cannot safely be populated by rearranging static CSV outcomes.
4. Twenty blocks per cell give weak precision, particularly at low nuisance rates. More cells would spread the same budget over more unresolved estimates.
5. One-run assessment is a weak sole comparator. Ordinary repeated, signature-aware analysis may already answer the question.
6. Mixing controls, artifact development and final measurement would make the effective independent sample unclear.
7. Fewer blocks may result from more false negatives; fewer red builds is not a sufficient benefit measure.

**Replacement:** Q0 qualifies artifacts. E1 measures two retry policies on two development episodes and checks the evidence pipeline. E2 collects independent, fresh measurements on four episodes. E3 tests one interaction only if its additional factual inputs already exist. A negative gate stops expansion.

## 4. Common scientific contract

### 4.1 Subjects and independent oracle

An **episode** is one underlying product defect and its repair, including all associated tests, builds, extracted examples and issue duplicates. These observations stay together. Multiple manifestations or retry streams are not extra episodes.

For each episode, record:

- `V_bad`: an authentic historical defective revision, or an explicitly identified reconstruction obtained by reverting the documented focal production fix.
- `V_ok`: an acceptable counterpart for the **focal behavioral obligation**, not an assertion that the whole project is bug-free.
- The same target test/component command, test source and dependency/environment recipe on both versions, except the justified product change.
- A human-authored issue/fix or equivalent independently inspectable evidence of the product defect; exact hashes and a behavioral obligation stated before policy measurements.
- An observable witness of that obligation, such as an incorrect result, violated invariant, or diagnosed deadlock. A timeout or matching stack trace alone is insufficient unless its relation to the obligation is established.

Two counterpart types are allowed and reported separately: **historical pair** with an isolatable focal change; **controlled historical-fix reversal** on one pinned base. An arbitrary mutant or an agent-written repair is not a real-defect counterpart. If test code was added with the repair, a documented identical backport to both variants is permitted, but label the experiment a reconstructed test of a historical defect, not replay of the original CI test.

This is a retrospective policy experiment. A later verified fix can supply `V_ok`; it is **not** a pre-change reference and provides no deployment-time knowledge. The older adaptive-investigation protocol's authentic-parent requirement does not apply to E1/E2. E3 separately requires authentic pre-decision change context.

**Nuisance requires its own evidence.** An acceptable-version failure is not automatically a false alarm. Identify a test/harness artifact that does not violate the focal contract or another known required behavior. Other real defects, uncertain timeouts and unresolved failures get separate labels. If no real nuisance occurs, report sensitivity only and state that the noise-reduction part of RQ1 was not established. Do not inject random verdict noise to fill that gap.

### 4.2 Observations, state and availability

Retain raw exit codes, full stdout/stderr, test reports, per-attempt signatures, duration, actual test execution identity, skipped status, environment/seed/condition identity, and final policy output. Oracle adjudication uses the obligation and witness, not whether the policy was green.

Attempt categories are `PASS`, `FOCAL_DEFECT_WITNESS`, `VERIFIED_NUISANCE`, `OTHER_DEFECT`, `UNRESOLVED`, and `HARNESS_INVALID`. Record sets of categories if one component invocation exposes multiple outcomes. Do not flatten two simultaneous causes into a flake/regression class.

The operational policy consumes only the exit status of attempts available so far. The richer oracle annotations are evaluator-only information. No policy sees the acceptable-counterpart outcomes, later fix, final aggregate counts or future attempts.

### 4.3 Precisely defined policies

| Policy | Execution and final decision | Role |
|---|---|---|
| P1: one attempt | Execute the fixed command once. Nonzero exit blocks; zero accepts | Primary deterministic reference |
| P3: accept-on-pass retry | Execute the same job command, with prescribed reset, up to three total attempts. Stop at first zero exit; accept. Block only if all three attempts are nonzero | Primary retry intervention |
| P3-retain: evidence-retaining report | Same executed prefix and cost as P3. If P3 accepts after an earlier failure, emit `ACCEPT_WITH_PRIOR_FAILURE` with links; otherwise retain P3's result | Secondary reporting control, **not** an automatic block or a proven human escalation |

The first scope is **job retries using fresh test processes and the same predeclared reset recipe**. It does not claim equivalence to in-process framework retries or retries that retain mutated fixtures. Include any required polluter/setup sequence inside the fixed job command; isolated victim reruns can erase the phenomenon.

Keep earlier failures in the research ledger even when P3 accepts. Whether the original CI UI also shows them is a separately recorded fact; a green final exit is not proof the evidence is invisible to humans.

### 4.4 Paired blocks and restricted replay

One block contains up to three attempts on each version. Randomize whether `V_bad` or `V_ok` runs first in the block. Use the same declared condition family, with independently reset state; equal seeds do not imply equal concurrent schedules. Fix the condition distribution before measurement, preferably the reproducer's documented default without added schedule forcing. Begin blocks regardless of whether the first attempt passes: conditioning collection on initial failure would distort unconditional blocking rates.

For efficient measurement, collect three attempts even after a pass, clearly separating the **research-only suffix** from the prefix P3 would execute. P1 reads the first attempt; P3 reads only through the first pass or third failure. This replay is allowed only because the policies share the exact same prefix-generating procedure, and reset isolation prevents research-only suffixes from affecting later blocks. No IID assumption is needed among the three retries.

E1 must verify prefix/reset mechanics against direct execution. If a job's behavior depends on the policy label, early stopping changes subsequent blocks, or external state cannot be reset, do not use shared traces: either qualify a directly randomized live comparison before E2 or exclude this subject from the restricted replay cohort. Do not silently spend the budget on a different design.

### 4.5 Primary measurements and analysis

For episode `e` and policy `p`, over its preassigned valid blocks:

- `S(e,p)`: fraction of defective-version blocks where the **final blocking outcome has supporting focal-defect evidence in the policy-visible prefix**. Unrelated red outcomes do not count as focal detection.
- `N(e,p)`: fraction of acceptable-version blocks blocked solely by independently verified nuisance behavior. Other defects are not nuisance.
- `L(e) = S(e,P1) - S(e,P3)`: sensitivity loss. Primary material margin `0.10`.
- `R(e) = N(e,P1) - N(e,P3)`: nuisance-block reduction. Provisional practical margin `0.05`; report smaller effects without calling them materially useful.

Also report raw final blocking rates on both versions, focal witnesses generated versus retained versus ignored by the final gate, `ACCEPT_WITH_PRIOR_FAILURE`, allocated vCPU-hours, measured CPU where available, wall time and policy-prefix attempt count. Give the operational cost difference honestly: P1 and P3 do not have equal execution cost. P3 and P3-retain do. Do not claim a compute saving from retries merely because nuisance blocks decrease.

`S-N` can be a descriptive secondary contrast, but it is not substituted for reporting both components. No APFD, model accuracy, explanation score or estimated production incidents prevented is a primary metric. No developer-time benefit is measured without an actual workflow study.

**Uncertainty plan:** E1 is descriptive calibration. E2 has 100 fixed blocks per episode, in five time batches of 20, never stopped early because a result looks promising. For each contrast, form paired block differences in `{-1,0,1}`. Use conservative paired intervals by obtaining exact binomial intervals for the positive- and negative-difference probabilities and subtracting their bounds. For the eight E2 contrasts (four `L`, four `R`), use Bonferroni over the 16 category-probability intervals: each interval has confidence `1 - 0.05/16`; the resulting contrast intervals have at least 95% simultaneous coverage under independent-block sampling. This works at zero-discordance boundaries, where an ordinary bootstrap can give misleadingly zero width.

Report ordinary per-case rate intervals descriptively as well. These calculations assume independent reset blocks, not independent retries or representative defect sampling. Inspect time-batch drift and state dependence. If independence is not defensible, report batch-specific estimates and dependency sensitivity; do not retain the nominal exact-interval coverage claim. No pooled project-generalizing p-value is planned.

For unresolved/invalid outcomes, publish denominators and conservative best/worst assignments for the relevant block differences. Complete-case estimates are secondary when missingness could change a conclusion. No invisible replacement attempts. More than 10% invalid blocks in E1 or 5% in E2 triggers an unresolved quality gate. A missing suffix is irrelevant to a policy already stopped, but may affect other planned summaries.

A 100-block pilot is not guaranteed to resolve a 0.10 margin. In an ordinary binomial sample, observing zero events still permits a nonzero rate; simultaneous intervals are wider. Narrow intervals entirely below the material-loss margin support “no material loss detected within this scoped protocol.” A wide interval crossing it supports “inconclusive.” Failure to reject a null is not preservation.

## 5. Artifact sources, order and qualification — Q0

### Source order

**Evidence checked on 2026-09-08:** Source descriptions below were inspected, not executed. Docker, WSL, Python and Git executable paths are visible on this host; daemon readiness, Linux images and subject compatibility were not established.

| Order | Exact source | Use and boundary | Stop rule |
|---|---|---|---|
| 0: baseline reconnaissance, not cohort acquisition | [Zeng et al., YourBase assessment](https://rebels.cs.uwaterloo.ca/papers/msr2024_zeng.pdf), artifact DOI [10.5281/zenodo.10076515](https://doi.org/10.5281/zenodo.10076515) | Establish existing assessment and available metadata. The study already addresses mutation-based CI trustworthiness and discusses nondeterminism; it is not absent prior art. The archive could not be inspected through the browser in this pass | Two researcher-hours. Do not make recovering a proprietary accelerator a dependency |
| 1: primary Java defect leads | [JaConTeBe primary paper](https://mir.cs.illinois.edu/marinov/publications/LinETAL15JaConTeBe.pdf), [SIR catalog](https://sir.csc.ncsu.edu/portal/bios/JaConTeBe.php) | Real historical concurrency defects with reproducers and issue references. Start with non-JDK library cases in Commons Pool/DBCP/Log4j; verify bug/fix metadata and test conditions. POOL-146, POOL-162 and LOG4J-38137 are bibliographic seed IDs, **not qualified intermittent subjects** | Four metadata hours; initial restoration candidates must fit the common caps below. Catalog access was unsuccessful in this pass; inspect authoritative upstream/mirror provenance before using a copy |
| 2: matching archived Java CI | [BugSwarm](https://www.bugswarm.org/docs/introduction/what-is-bugswarm/) and its [experiment instructions](https://www.bugswarm.org/docs/tutorials/setting-up-an-experiment/); inspect [CI-Bench](https://github.com/BugSwarm/CI-Bench) only for minimal runner reuse | Inspect fail/pass patches and issue evidence for product defects. A passing partner is not automatically acceptable or causal. Keep scripts/dependencies equal where scientifically justified. CI-Bench shares BugSwarm subjects and does not supply new ground truth | Two metadata hours. No installation of CI-Bench's LLM stack; no all-artifact harvester |
| 3: nuisance/issue leads | [IDoFT](https://github.com/TestingResearchIllinois/idoft), especially its test/PR records | Look for independently documented nuisance cases or links to genuine product fixes. A flaky-test label, accepted test repair, or `DeveloperFixed` status does not establish product-defect truth | Two metadata hours. Pure test repairs cannot fill the primary product-defect cohort |
| 4: one ecosystem fallback, only if Java qualification fails early | [GoBench repository](https://github.com/timmyyuan/gobench), [primary paper](https://lujie.ac.cn/files/papers/GoBench.pdf), **GoReal** rather than GoKer | A source of historical Go concurrency bugs and execution tooling. GoKer kernels are extracted subjects and remain controls; GoReal still needs counterpart and oracle qualification. A data-race report alone is insufficient for the chosen behavioral obligation | Use only remaining Q0 allowance. Select Java or Go by day 7; do not build two new language harnesses in parallel |
| No restoration this month | Local Airavata/TCP-CI and reported HBase/Hive/LRTS | Existing histories support fallback audit, not counterfactual job attempts. LRTS provenance lead: [original study](https://samchengcs.github.io/paper/cheng2024revisiting.pdf) | No large data download or legacy environment resurrection for E1 |

The JaConTeBe paper reports that many reproducers use mocking/instrumentation to make failures repeatable. A forced deterministic reproducer is a control, not evidence of intermittency. This source addition is an artifact-feasibility refinement, not a new research direction. Restricting to recoverable library cases creates selection bias and limits claims.

### Q0 protocol

- **Question / null:** Can four usable episodes on two projects be qualified economically? Null: fewer than the required cases, no independent oracle, or unacceptable restoration cost.
- **Why necessary:** Every effectiveness result depends on artifact and oracle validity; existing tables cannot substitute for this stage.
- **Roster:** At most 12 primary defect candidates plus two nuisance/control candidates. Deduplicate by upstream issue/fix before execution. Order by source tier, project and issue ID; break ties by revision hash. Enrol at most two primary episodes per project so the first four eligible cases cover at least two projects. Keep the whole roster and exclusions. Do not rank by newly measured policy losses.
- **Inclusion:** An authentic product-defect link; inspectable fix/obligation; same target/harness across counterparts; pinned execution command and environment; legitimate reset/condition protocol; independently interpretable outcome; economical execution.
- **Exclusion from primary cohort:** Compilation/dependency-only failure; purely test-maintenance intervention; arbitrary mutation; unverifiable counterpart; discarded polluter/setup; forced fault outcome; cloud/hardware dependencies outside the available scope; changing production behavior merely to make a benchmark run.
- **Qualification executions:** After source inspection, run ten fresh single attempts per version. If build/reset/oracle checks pass, run ten more per version, regardless of whether early outcomes look favorable. Qualification intermittency requires at least two focal failures and two passes on `V_bad` over these 20 attempts at the frozen protocol. This deliberately selects measurable intermittency; absence of the pattern does not prove a test deterministic. Retain stable defects as named controls if inexpensive, not as substitutes for primary episodes.
- **Acceptable counterpart:** Independent obligation/fix reasoning plus successful witness checks. Zero focal failures in 20 runs is supportive reproduction evidence, not proof of zero defect probability. Any contradictory focal witness makes the pair unresolved until a documented explanation exists.
- **Controls/variables/baseline:** Vary revision only; hold tests, image, inputs and reset constant. Begin with native author/benchmark reproduction commands. Evaluate the oracle against documented positive and acceptable executions before evaluating retry behavior.
- **Metrics/unit/analysis:** Qualified episodes/projects, per-candidate failure reason, witness counts, invalid fraction, engineering and compute cost. Unit is candidate episode. Report counts and exclusions descriptively; do not estimate population qualification rates from this convenience roster.
- **Preserve:** Candidate manifest, upstream URLs and hashes, patches, oracle card, exact commands, image/dependency hashes, qualification logs, time/cost ledger, schema and all rejected candidates.
- **Continue:** At least two qualified development episodes by day 7 for E1; at least four across two projects by day 10 for E2. At least two future E2 cases remain free of policy-outcome inspection until the E1 protocol freezes. Qualification outcomes can be inspected for all cases; do not describe those cases as wholly blinded.
- **No-go:** Fewer than two by day 7 stops E1; fewer than four/two projects by day 10 stops E2. Failure to observe verified nuisance limits the scope to sensitivity and withholds a full trade-off claim. Move to fallback rather than widening the definition of a real defect.
- **Caps:** 12 human hours total for metadata/oracle triage, including the source allowances above; 20 allocated vCPU-hours for restoration and qualification; at most two human restoration hours and four allocated vCPU-hours per primary candidate, all counted against the totals. Move on when any cap is reached.
- **Main threats:** Convenience selection, ancient toolchains, reconstruction changing scheduling, insufficient rare-event sampling, bug kernels masquerading as full-system CI, and fix/test co-evolution.

## 6. Experiment 1 — minimal paired retry measurement

**Research question:** Can the paired protocol measure P1/P3's factual decisions and attributable outcomes on two real intermittent defect episodes without conflating noise, faulty behavior and harness errors?

**Hypothesis / null:** The procedure produces trustworthy, costed measurements with preserved intermediate evidence. Null: oracle/reset failure, mostly unresolved outcomes, or unreliable policy replay. This is calibration and a mechanism probe, not a significance contest.

**Why necessary:** It tests the research instrument and scope before a larger cohort. It replaces the ten-day factorial proposal rather than beginning it with fewer subjects.

**Subjects / inclusion / exclusion:** First two Q0-qualified episodes in the fixed roster order, preferably different projects; all common criteria apply. Stable/synthetic controls are separately labeled. Do not choose the two largest observed losses.

**Oracle:** Frozen Q0 obligation, counterpart and witness rules. Adjudicate raw attempts without looking at the policy-comparison summary. One researcher performs this; independent ground truth means external evidence plus an independent behavioral criterion, not a claim of independent reviewers.

**Policies / baselines:** P1, P3, secondary P3-retain. No selector, quarantine or learned model. Native job status is the execution baseline; a hand-checked reconstruction of each policy prefix is the reporting reference.

**Variables / controls:** Revision and retry decision vary; target, conditions, image/reset recipe remain fixed. Block version order is randomized with stored seeds. Log available-at times and all failure categories. Begin from both first-pass and first-fail blocks.

**Implementation phase, after Q0:** Create only a thin isolated command runner, append-only attempt logger, explicit policy reducer and analysis script in a new experiment area. Keep existing pipeline code untouched. Test reducer truth tables such as pass, fail/pass and fail/fail/fail, plus missing-attempt handling and reset cleanup. Synthetic truth-table inputs validate implementation only; they never enter empirical results.

**Execution procedure:**

1. Freeze the two subject manifests, test/reset commands, policies, condition distribution and oracle rules.
2. Run 20 paired blocks per episode, three attempts per version: `2 episodes × 20 blocks × 2 versions × 3 attempts = 240` primitive attempts, plus the separately budgeted checks below. Use at least two time batches.
3. Perform 12 direct-policy checks total, balanced over episodes, versions and P1/P3, using the same runner with actual early stopping. Check selected attempt prefixes, reset behavior and final status against the reducer for those actual traces. Different fresh stochastic runs need not have matching outcomes. Stop on structural mismatch; do not demand arbitrary percentage agreement between fresh executions.
4. Use a small identity/no-change and deterministic-failure control set to verify attribution and final status. Charge all costs; controls do not increase episode count.
5. Analyze only after the fixed E1 blocks complete or a documented resource/data-quality stop occurs. Preserve partial results and reasons.

**Metrics / unit / uncertainty:** Common `S`, `N`, `L`, `R`, raw blocking, prior-evidence retention and prefix cost; episode is the unit, block is the repeated measure. Show all counts and descriptive intervals. At 20 blocks, no equivalence claim and no project-level generalization.

**Preserve:** E1 protocol version/hash, runner version, command and reset manifests, unit-check output, direct-policy checks, complete attempt ledger, failure annotations, per-case tables and cost accounting.

**Continue:** Both episodes have working oracles/reset/policy interpretation; invalid fraction at most 10%; outcomes and intermediate failures remain traceable; measured projected E2 cost fits its cap. E1 need not show a large loss. An operationally sound null proceeds to the predeclared E2 measurement when Q0's cohort gate passes.

**No-go:** Contradictory counterpart behavior, forced/synthetic intermittency, missing evidence that determines the result, or unaffordable execution. Stop the policy study and preserve a qualification/calibration failure report. Do not rescue it by changing assertions or relabeling failures.

**Major threats:** Development-case overfitting, reset changing the phenomenon, assuming conditional retries are IID, conflating warnings with blocked releases, and sharing suffix executions across inadequately isolated blocks.

**Budget:** At most 20 allocated vCPU-hours, including direct checks, controls and implementation verification. Protocol choices may be amended during E1, but amendments must be frozen before E2, and E1 data remain development-only.

## 7. Experiment 2 — fresh trade-off assessment and baseline sufficiency

**Research questions:** RQ1 and RQ2.

**Hypotheses / nulls:** A material retry sensitivity loss is supported on multiple independently qualified episodes; verified nuisance reduction is measured where present. A separate hypothesis is that additional assessment beyond ordinary repeated, signature-aware analysis is useful. The latter can fail even when retry loss is real.

**Why necessary:** E1 could be an anecdote or a measurement bug. E2 separates development from fresh measurement and prevents claiming novelty solely because a one-shot comparator performs poorly.

**Subjects / criteria / oracle:** Four Q0-qualified episodes across at least two projects, at most two per project, including the two E1 development cases and two cases without prior policy-outcome inspection. All receive fresh E2 observations. Whole issues stay together. The frozen Q0 oracle is external to each policy and independent of E2 verdict summaries. If four cases cannot qualify, do not substitute controls or advertise a completed E2.

**Policies / variables / controls:** Same P1/P3/P3-retain and common controls as E1, with no post-E1 policy tuning. Record whether the job-retry rule is documented in the subject's historical CI or introduced as an explicit experimental intervention. The latter is a policy experiment on a historical defect, not evidence of an actual historical escape.

**Assessment baselines, all specified before E2:**

| ID | Assessment | Interpretation |
|---|---|---|
| A0 | Compare first-block paired final outcomes only; disagreeing outcomes flag a possible policy effect | Cheap descriptive baseline. Agreement is “no difference in this observation,” never a justified safety certificate |
| A1 | Ordinary repeated paired analysis of final blocking rates, with counts, uncertainty and cost | Stronger baseline; use the complete fixed E2 observation budget |
| A2 | A1 plus ordinary signature/obligation stratification, invalid handling and inspection of earlier attempts | **Strong primary assessment baseline.** Same logs, oracle cards, time allowance and execution budget as the full study analysis |
| Reference analysis | Full common-contract case table, witness provenance and conservative unresolved bounds | A transparent measurement reference, **not a newly invented algorithm** |

Do not withhold the fixed revision, logs or oracle from A2 to manufacture an advantage. Give it up to one researcher-hour per case, the same case-inspection allowance as the reference analysis. Its reporting rules are applied mechanically, with the same single researcher; there is no simulated independent reviewer. If A2 and the reference agree, the conclusion is that ordinary assessment suffices here. An unavailable YourBase installation or MeteoR run is “not compared,” not a defeated baseline. Neither is required for this different retry intervention.

**Execution procedure:** Freeze the E2 plan and select cases by roster order before viewing E2 outcomes. Run 100 new paired blocks per episode in five batches of 20; charge all three attempts per version even though some are research-only suffixes. Total ceiling: `4 × 100 × 2 × 3 = 2,400` primitive attempts. Run cases in interleaved time batches with version order randomized. No optional extension based on a borderline result. Analyze after the fixed collection or an explicit budget stop. Record A0/A1/A2 outputs and reference classifications using their frozen rules.

**Metrics / statistical unit:** Common `L` and `R` primary contrasts and operating costs, plus assessment classifications: supported loss, bounded-below-margin loss, or inconclusive. Record A0 misses as descriptive single-observation instability; count A2 disagreement only when an independent witness and interval support a changed conclusion. Unit is episode; attempts are measurements. Report development versus previously uninspected cases separately.

**Uncertainty:** Use Section 4.5's paired simultaneous intervals and unresolved bounds. Do not equate the reference estimate to perfect diagnostic truth: a case whose interval cannot resolve the margin remains unresolved for all assessor-accuracy summaries. Present time-batch drift and invalid patterns. Do not pool thousands of attempts as independent defects or make a population generalization from two projects.

**Success / continue:** A scoped empirical follow-up is justified if at least two episodes from different projects, including one not inspected under E1 policies, have `L >= 0.10` with simultaneous lower bound above zero and independently supported witnesses. A full “noise reduction versus sensitivity” claim additionally needs at least one qualified case with real nuisance observations and supported `R >= 0.05`, lower bound above zero; ideally that same episode shows both effects. Otherwise retain only the narrower supported statement.

**Separate method gate:** Fund a new assessor only if at least one reproducible, nontrivial resolved assessment distinction remains beyond A2 and the closest applicable prior work. If all resolved cases are captured by A2, stop the new-assessor claim; an empirical replication or practical guide may still be useful. If the only result is the elementary fact that retrying can suppress an intermittent failure, document it without calling it a strong new method.

**No-go / inconclusive:** Material loss bounded out on all evaluable cases, no independently supported differences, too few qualified cases, or uncertainty/missingness dominating the conclusions. “No-go for expanded investment” does not imply all retry policies are safe. Do not increase sample size or change defect definitions to preserve the story.

**Preserve:** E2 protocol/hash, disjoint data identifiers, full attempt ledger and annotations, all assessor outputs, analysis command/package versions, interval computation checks, per-episode/batch plots and tables, missingness bounds, cost ledger, and a decision memo separating scientific opportunity from method novelty.

**Main threats:** Selection for measurable intermittency, scarce nuisance events, oracle ambiguity, case inspection hindsight, dependence across runs, introduced policy rather than authentic deployment, and the small project/episode count.

**Budget:** 80 allocated vCPU-hours. Q0/E1 must project completion from measured invocation costs, including resets. The number of blocks is a ceiling, not permission to exceed the cap. An incomplete E2 remains incomplete.

## 8. Experiment 3 — optional selector × retry interaction

**Eligibility gate:** Begin only if E2 is complete and at least two qualified episodes already have a full eligible component suite, an authentic introducing change/context, stable test identities, and an executable **pre-existing native dependency selector**. Freeze the exact selector command before its outcomes. No new T0 model or dependency engine is built to make this experiment possible. Cases using only minimal reproducers will usually be ineligible.

**RQ / hypothesis / null:** RQ3. Retry sensitivity loss differs materially between full-suite and selected-suite execution. Null: negligible/unresolved difference, no eligible artifacts, or only the obvious removal of the sole detecting test.

**Why necessary if eligible:** A general claim about interacting optimization policies needs actual interaction evidence. E1/E2 alone support a claim about the scoped retry rule.

**Subjects / inclusion / exclusion / oracle:** First two eligible episodes in roster order, preferably on different projects; all common oracle rules apply. Retain selector omissions in descriptive results, but do not count “selector omitted every detector” as a nontrivial interaction success. No retrospective fix-derived change signal may masquerade as an authentic pre-decision selector input.

**Systems / variables / baselines / controls:** Four cells: full/P1, full/P3, selected/P1, selected/P3. Full/P1 is the reference. Hold oracle, version pair, inputs and reset protocol fixed. Run selected and full suites separately with randomized order; selection can change state/order/duration and cannot be simulated by deleting rows from full-suite logs.

**Procedure:** Twenty new blocks per version and suite per episode, three attempts each: `2 × 20 × 2 versions × 2 suites × 3 = 480` primitive invocations. Derive retry decisions only within a validated same-suite prefix. Freeze the selected set per supplied change; preserve every selected/omitted identity and reason.

**Metrics / unit / analysis:** Per-episode interaction `I = L(selected) - L(full)`, nuisance counterpart, selected-test cost, and whether interpretation changes. A provisional material interaction is `abs(I) >= 0.10`. Use paired block-level contrasts with uncertainty and dependence checks; with only 20 blocks, treat this as exploratory and do not use an uncorrected p-value to override E2. Multiplicative probabilities alone do not establish an interaction on every scale.

**Preserve:** Selector version/commands/input snapshot, full/selected test lists, actual separate executions, four-cell tables, omission explanations, interval/sensitivity analysis and costs.

**Continue:** A nontrivial, independently supported interaction warrants a separately preregistered larger replication. **No-go:** No eligibility, only sole-detector omission, small/unresolved effects, or ordinary A2 analysis already handles everything relevant. Mark not attempted or inconclusive honestly; do not add quarantine to create more cells.

**Threats:** Selector provenance, ordering effects, different full/selected costs, tiny sample, conditional choice of cases, and scale-dependent interaction definitions.

**Budget:** 20 allocated vCPU-hours, unavailable until E2 completion. If ineligible, use the period for analysis and the decision memo; unused compute is not automatically reassigned.

## 9. Fallback F1 — fault-mapping and evidence-validity audit

**Trigger:** Q0/E1 failure, or E2 supplies no reason to expand the policy-sensitivity research. This replaces further implementation, not a parallel project. Cap at three researcher-days and ten allocated vCPU-hours.

**RQ / hypothesis / null:** Does an existing TCP comparison's conclusion depend on an unsupported one-failed-test/one-fault assumption or an unjustified persistence label? Null: recoverable comparisons are stable under the declared alternative mappings; or inputs are insufficient to test stability.

**Why necessary:** It can produce a traceable finding from existing evidence without inventing unobserved CI actions.

**Subjects / artifacts / inclusion:** Start with Airavata's preserved small-failure comparison and raw execution/identity tables. Read `25eb6b7`'s outputs and the August reproduction references. Include only cycles whose paired per-test rankings and executed test sets can be recovered exactly. Published aggregate APFD alone cannot reconstruct a fault mapping. Prefer the reported small-failure stratum, where partition enumeration is tractable. HBase/Hive are excluded unless the precise inputs/rankings are already recoverable without a new acquisition project.

**Oracle / controls / comparisons:** There is no new fault oracle. Compare HIST and HIST+T0 using the **same** mapping and cycle/test cohort for both. Evaluate one-failed-test/one-fault, one-fault-per-cycle, and all partitions of failing tests where tractable. Treat unconstrained partitions as logical sensitivity bounds, not equally probable causal explanations. Add constraints only from independently inspected logs/issues; co-failure alone is not a cause label.

**Procedure:** Recover immutable ranking artifacts into a separate audit workspace; verify original per-cycle metrics. Hold rankings fixed; vary mapping/label interpretation. Report within-cycle and mean-difference ranges, any sign reversal under a common mapping, and successor censoring for persistence labels. If per-test rankings cannot be recovered within one day, stop the ranking part and issue a traceability/label-validity audit instead. Do not fit a new model to fabricate the missing historical outputs.

**Metrics / unit / uncertainty:** Cycle-level paired difference ranges, robust/reversible/unidentified comparison, reconstructed-versus-reported discrepancies, missing artifact counts and label-category counts. The ranges reflect modeling assumptions, not sampling confidence intervals. Cycles in one failure episode are correlated; no naive significance test over all rows.

**Preserve:** Exact source commit/path/hash, cohort and ranking manifest, verified original metrics, mapping definitions, bounds and examples, missing-input report and scoped interpretation.

**Continue:** A reproducible material claim reversal or demonstrated evidence gap supports a methods/replication write-up. **No-go:** No recoverable rankings and no additional evidence beyond already documented limitations; archive the audit and stop. Stability is a meaningful negative finding, not a reason to search unlimited mappings until a reversal appears.

**Threats:** Unjustified mapping constraints, conflating hypothetical bounds with real fault counts, correlated cycles, and expanding a post-hoc audit into a new benchmark without disclosure.

## 10. Implementation boundary, outputs and reuse

### Separate the stages

| Stage | Allowed work when execution is subsequently requested | Exit artifact |
|---|---|---|
| Qualification | Read artifact metadata, restore pinned external subjects in an isolated area, run existing native commands, document obligations | Candidate manifest, oracle cards, environment/command recipes and Q0 decision |
| Experiment implementation | Add only the runner/logger/reducer/analysis necessary for E1; preserve existing experimental pipeline | Tested small harness, protocol hash and execution manifest |
| Actual execution | Run only the frozen cases, conditions and budgets; record every attempt and stop | Immutable observation ledger and resource log |
| Analysis | Apply frozen outcome/contrast rules; preserve ambiguous cases and planned missingness bounds | Case tables, intervals, figures and assessor comparisons |
| Interpretation | Separate operational trade-off, added assessment value and generalization limits | GO / NO-GO / INCONCLUSIVE memo and next scoped decision |

Suggested future root: `research_runs/ci_sensitivity_2026_09/`. Use `protocol.md`, `candidate_manifest.csv`, `environment_manifest.json`, `subjects/<episode_id>/oracle.md`, `subjects/<episode_id>/commands.json`, `attempts.jsonl`, `policy_decisions.csv`, `costs.csv`, `analysis/`, and `decision.md`. These are planned paths, not existing artifacts. Keep large external checkouts/images/raw logs outside tracked research documents; do not stage them automatically.

Minimum attempt record: episode/project, source cohort, revision role and hash, test/harness hash and identity, environment digest, reset/condition/seed, phase, batch/block/attempt ID, actual command, start/end/available-at UTC, exit/status/signature, raw-log URI/hash, allocated CPU/wall cost and evaluator annotation with provenance. Policy records must list exactly which attempt IDs they consumed and which decision rule produced the final status. Subject cards record intended scope, source fix, oracle limitations and reconstruction type.

### Repository reuse decisions

| Component | Decision | Concrete use / limit |
|---|---|---|
| Raw dataset/history utilities | **KEEP / VALIDATE** | Reuse parsers and factual history inspection for F1 and source screening. No counterfactual outcomes or CI policy truth inferred from CSVs |
| `pipeline/lrts_adapter.py::derive_history` | **ADAPT later; FREEZE for E1/E2** | Preserve emit-before-update and duplicate checks; later require availability times. Earlier build start is not necessarily earlier observation availability |
| Identity/change joins, including `step1_name_join.py` and adapter identity helpers | **KEEP / VALIDATE** | Reuse identity conventions; check exact target source on each revision and preserve missing joins. E3 needs authentic pre-change context |
| `pipeline/relevance_t0.py` | **FREEZE** | Retain as future cheap baseline. Whole-dataframe IDF fitting needs causal correction before future learning claims. E1/E2 do not need relevance |
| Temporal/prequential evaluation in `step2_baseline.py` / `step3_t0.py` | **KEEP principle / VALIDATE before reuse** | Preserve temporal separation; do not use current-run duration or unavailable earlier outcomes as decision inputs. No training in this month |
| `pipeline/fault_structure_probe.py` | **ADAPT for F1 only** | Describe co-failure/concentration; do not turn its strata into causal labels |
| `BugSwarm/BugSwarm_harvester.py` | **VALIDATE / FREEZE broad harvesting** | Metadata/schema reference only until side effects are audited. Its all-artifact/high-failure project ranking is unsuitable for the small unbiased qualification queue |
| `step3_regapfd.py` persistence label | **RETIRE as ground truth; KEEP historical analysis** | Use only as an explicitly retrospective persistence proxy in F1 |
| Airavata null and precise/import-reach negatives | **KEEP** | Preserve scope and reported results. They rule out neither all relevance nor all structural analysis |
| HBase/Hive reports | **VALIDATE; FREEZE extension** | Do not turn reported persistence-APFD lifts into confirmed real-defect evidence |
| Legacy embedding/classifier sweeps and generated reports | **FREEZE** | No additional sweeps; outputs are artifact leads, not independent replications |

### Do not build yet

No agents, multi-agent coordination, LLM investigator, repair generator, learned action selector, bandit/RL controller, embedding sweep, broad dependency graph, general CI platform, dashboard product, deployment integration, live release gate, GPU test fleet, new model-evaluation framework or mass artifact harvester. Do not modify existing implementation code to fit a preferred narrative. Only a small isolated experiment harness is justified after Q0; if native scripts suffice, use them.

## 11. Practical 30-day schedule and budget

The window is 2026-09-08 through 2026-10-07 inclusive if started today. Day numbers below are elapsed calendar days; allocate at most 20 researcher working days inside that window. No running experiment is started by this document.

| Period | Work | Tangible exit |
|---|---|---|
| **Days 1–3** | Snapshot protocol and source state; verify runtime readiness; do bounded baseline reconnaissance; freeze candidate queue; inspect first oracle cards and native commands | Baseline/applicability table, runtime manifest, ordered candidate roster; stop early if no defensible source |
| **Days 4–7** | Complete Q0 for first two episodes; qualify reset/conditions and counterparts; begin minimal E1 harness only after Q0 passes | Two qualified development cases and tested measurement path, or qualification NO-GO |
| **Days 8–10** | Execute E1 fixed blocks; finish the four-episode/two-project qualification gate; freeze E2 design and remaining case order | E1 calibration report, measured E2 cost projection, and explicit E2 GO / NO-GO |
| **Days 11–14 — transition** | Resolve only declared E1 implementation defects; freeze final hashes; begin E2's preassigned batches. Do not tune on E2 summaries | Locked protocol/runner and immutable first E2 batches; fallback F1 instead if earlier gates failed |
| **Week 3, days 15–21** | Complete E2 fixed collection, quality checks and case-level analysis; apply assessor rules; evaluate E3 eligibility | E2 evidence table and baseline-sufficiency decision; locked optional E3 protocol or NOT ELIGIBLE |
| **Week 4, days 22–28** | Execute E3 only if eligible and within cap; otherwise finalize evidence/analysis or complete triggered F1 | Interaction probe or fallback audit; reproducibility package and draft decision |
| **Days 29–30** | Audit claims against logs, costs and missingness; decide and archive all negative/inconclusive outcomes | Final GO / NO-GO / INCONCLUSIVE memo identifying one next investment or a stop |

**Compute ceiling:** 160 allocated vCPU-hours total: Q0 20, E1 20, E2 80, optional E3 20, fallback F1 10, environment/analysis reserve 10. First ten days are capped at 40 allocated vCPU-hours including their setup. These are ceilings, not amounts to spend; unused conditional allocations do not automatically authorize extra sampling. Count allocated vCPUs times elapsed runtime, including failed builds, resets, controls and research-only suffixes; distinguish this from measured CPU utilization.

Use one experiment job at a time; native subject threads are part of the subject, not parallel research workers. No new paid/cloud/GPU resources are assumed. Pin at most two allocated vCPUs per job initially and record memory limits. Initial build timeout is 30 minutes; attempt timeout is declared per subject from its documented contract, with a 120-second execution ceiling for this cohort. A deadlock requires its independent witness; an administrative timeout is not automatically a defect. If legitimate behavior exceeds these caps, reject for feasibility instead of redefining correct behavior. Record monitor/process exit and all cap-triggered stops. No unattended retry of a crashed research run; P3's prescribed test retries are different from silently retrying an experiment failure.

## 12. Gates and what happens when they fail

| Gate | GO condition | If it fails |
|---|---|---|
| G0: source/oracle readiness | Independently justified product-defect and acceptable counterpart; existing executable commands and viable runtime | Continue only within Q0 caps; otherwise F1. Do not manufacture mutants or flake labels as replacements |
| G1a, day 7 | Two qualified development episodes | Stop E1 and record artifact-strategy failure |
| G1b, day 10 | Four episodes across two projects, E1 measurement valid and E2 affordable | No E2. Finish small feasibility report and trigger F1 where possible |
| G2: empirical opportunity | E2's multi-episode sensitivity criterion is met; verified nuisance evidence separately supports any claimed noise trade-off | If bounded below margin: scoped negative result. If unresolved: no expansion by default. If nuisance absent: narrower sensitivity-only report |
| G3: additional assessment value | Nontrivial, resolved distinction beyond strong A2 and applicable prior art | Adopt ordinary assessment; stop inventing a new validator. Empirical replication remains possible |
| G4: interaction eligibility/value | Required existing selector/context and nontrivial E3 effect | Mark ineligible, null or inconclusive. Stop generalizing from retry to arbitrary composed policies |
| G5, day 30 | Reproducible evidence, honest scope, costs and a specific unanswered follow-up | Freeze the policy-investigation investment; preserve the result and fallback audit |

It is acceptable that ordinary methods suffice, real intermittent pairs are too hard to recover, interactions do not matter, or the most useful contribution is an evidence-validity audit. No gate authorizes broadening the vision or launching a platform to compensate for weak evidence.

## 13. Exact first five tasks for the next execution turn

These are sequential, bounded tasks. They are not executed in this planning pass and do not require another research-vision discussion.

1. **Freeze the starting record — 20 minutes.** Record `git rev-parse HEAD`, `git status --short` and SHA-256 hashes of this plan, the six preceding research proposals/assessments and relevant pipeline files. Create the future run root and `protocol.md` containing the locked RQs, Q0/E1 gates and resource caps. Preserve all pre-existing untracked files; stage nothing.
2. **Check execution readiness — 30 minutes.** Inspect `docker version`, `docker info`, `wsl --status`, `git --version` and available disk/memory, retaining failure output. Record Linux-container capability and allocated-resource settings in `environment_manifest.json`. Do not install software or start services silently. If no usable local runtime exists, record the blocker and continue metadata/oracle tasks without claiming execution readiness.
3. **Resolve the baseline and first artifact entry point — at most two hours.** Read YourBase's method/nondeterminism sections and inspect its published archive metadata if accessible; inspect JaConTeBe's subject/reproduction documentation. Write `baseline_applicability.md` distinguishing A0/A1/A2 from published methods and record exact accessible archive/upstream URLs. Stop archive chasing at the limit.
4. **Create the first six candidate cards — at most two hours of the Q0 triage allowance.** Use the source order and deterministic project/issue ordering above. Record at most six initial candidates, with source ID, exact known revisions or explicit missing fields, product-vs-test fix classification, oracle obligation, expected native command, condition manipulation and exclusion reason. Start from the Commons Pool/DBCP/Log4j leads; do not fabricate missing hashes or call these qualified cases. Select the first two source-eligible cases, not the most dramatic ones.
5. **Qualify the first candidate using its existing commands — maximum two human restoration hours/four allocated vCPU-hours.** Restore it in an isolated external-subject area, record hashes and dependencies, confirm the same target on both versions, and run Q0's ten-per-version initial batch. If structural checks pass, execute the predeclared second ten-per-version batch. Save all logs, oracle annotations and the qualify/exclude decision. Stop at its cap. Do not write the policy harness or edit this repository's implementation during this task.

**Recommended immediate action:** Task 1. **Recommended first effectiveness-related execution after qualification:** E1's paired one-attempt versus accept-on-pass retry probe. No additional vision document is needed before starting.
