# AI for behavioral-witness adequacy in the repository's actual cases

## Material Passport

- **Origin:** independent GPT-5.6 Sol research assessment requested on 2026-09-25
- **Mode:** deep research plus experiment planning
- **Verification status:** literature claims checked against linked primary or authoritative sources; repository claims checked against the cited local records; proposed experiments are unexecuted
- **Scope:** research assessment and planning only
- **Exclusions:** no subject execution, paid model call, canonical state change, commit, or push

## 1. Decision

**Recommendation:** do not make a direct Jev score, an LLM test generator, or an LLM-guided scheduler the next research contribution. The strongest bounded direction is to test whether AI can identify a *candidate missing behavioral-witness prerequisite* in a change and a frozen universe of existing tests, and whether that advisory diagnosis helps a deterministic execution method produce a valid witness at lower cost.

The proposed intermediate unit is a four-part witness-adequacy record:

1. **State/input reachability:** does the test establish the program state needed to enter the changed or defective path?
2. **Schedule/event reachability:** can the relevant interruption, cancellation, or competing operation occur in the required window?
3. **Oracle adequacy:** does the test distinguish the focal behavioral violation from a timeout, generic failure, or vacuous pass?
4. **Policy visibility:** if the witness occurs, does the CI decision retain it, or can retry/aggregation turn the final result green?

This is a candidate empirical framing, not a novelty claim or a unique causal decomposition. More than one intervention can make a witness valid, and available source may not identify one true missing facet. The first three components substantially overlap Themis's reach-race/trigger-interleaving/manifest-symptom decomposition, controlled concurrency testing, differential test generation, resource-leak analysis, and LLM test-generation work. The fourth component connects the analysis to this repository's measured concern: a witness can occur yet disappear from the final CI decision. A publishable contribution would require evidence that the explicit decomposition improves witness production over strong simple baselines on held-out real repair pairs. If it does not, the right result is that ordinary analysis is sufficient.

Jev may fit as a fast typed judge inside this study. It should not generate code or serve as ground truth. A larger generative model can propose obligation records or test edits; Jev can cheaply score fixed alternatives or screen candidate test-obligation relations; deterministic analysis and paired execution must decide whether a witness is real.

## 2. Evidence from the repository

### 2.1 Current empirical constraints

**Observed.** C1 collected all 720 planned attempts. Every one of the 360 acceptable-variant attempts passed, so no nuisance reduction was observed. Only etcd5509 met the frozen C3 development gate: unrestricted versus limited CPU produced 7/10 versus 10/10 P1 blocks and 5/10 versus 7/10 P3 blocks. Every primary simultaneous interval included zero ([post-collection review](../../research_runs/ci_configuration_2026_09/analysis_audit/POST_COLLECTION_REVIEW.md)).

**Observed.** The post-hoc signal audit found that etcd5509's C3 gate fires with probability about 0.41 under the no-profile-effect iid model and that at least one of the six subjects fires with probability about 0.72. Its 24/30 versus 26/30 all-attempt counts, P3 counts, and three first-attempt discrepancies are adequately explained by ordinary repetition. The audit recommends **STOP**, not confirmation ([signal validity audit](../../research_runs/ci_configuration_2026_09/signal_audit/SIGNAL_VALIDITY_AUDIT.md)).

**Inference.** These data do not support an AI system for choosing CPU configurations. There is no confirmed configuration effect to predict, and the gate's null firing rate makes a model trained to reproduce that gate especially unattractive.

**Observed.** Q0/E1 roster expansion closed at G1b, while F1 found the Airavata HIST-versus-HIST+T0 null stable under every declared fault mapping. The sign changed under one mapping, but the effect remained small; the useful finding was the missing per-test ranking evidence, not a recovered relevance effect ([F1 report](../../research_runs/ci_sensitivity_2026_09/f1/report.md)).

**Inference.** A more semantic ranker might still retrieve useful tests, but the current repository has neither a demonstrated ranking opportunity nor a causal failure label that would justify treating Jev as a probability-of-failure feature. A direct `history + T0 + Jev` TCP study remains low priority.

### 2.2 Actual cases expose different witness deficits

| Case | Repository observation | Witness-adequacy diagnosis to test | Suitable intervention class |
|---|---|---|---|
| **POOL-162** | The historical obligation is that interrupting a waiting borrower must not leak pool capacity. The pre-fix parent contains three inspected candidate tests. In the exploratory Jev probe, two scored 1/2 because they used the changed implementation but did not interrupt a waiting borrower; the third scored 0.01/2. None exercised the obligation. The regression test added with the fix is withheld as a future artifact ([research state](RESEARCH_STATE.md); [candidate card](../../research_runs/ci_sensitivity_2026_09/candidate_cards.md)). | Existing-test retrieval can look plausible while the critical event sequence is absent. The missing item is primarily state/event reachability, followed by a liveness oracle. | Derive the missing interrupt-after-wait sequence; validate with the held-out upstream test or an independently written equivalent. Fray is a strong scheduler baseline after the test establishes the right state. |
| **grpc1859** | The focal change returns connection-level send quota when acquiring local send quota fails. Its test repeatedly sends oversized requests and expects `ResourceExhausted`; without release, later writes can block ([candidate acquisition record](../../research_runs/ci_sensitivity_2026_09/task_c2_candidate_acquisition.md)). | Exceptional-path conservation: acquire outer quota, fail/cancel during inner acquisition, release outer quota, retain later progress. | Repeated-call input sequence plus a progress/error oracle. Schedule search is secondary to constructing the path and repeated-use check. |
| **etcd5509** | The failure path returned while holding `RLock`; a concurrent `Close` then waited forever for the write lock. C1's positive dumps consistently matched this mechanism, but CPU quota did not measurably slow passing executions and did not establish a causal rate change ([signal validity audit](../../research_runs/ci_configuration_2026_09/signal_audit/SIGNAL_VALIDITY_AUDIT.md); [upstream PR](https://github.com/etcd-io/etcd/pull/5509)). | The obligation is release-on-failure; the witness also needs a Get/Close ordering and a specific leaked-lock oracle. The missing research problem is not another resource profile. | Use a schedule or handshake intervention that targets the critical window, then apply the existing structural dump oracle. Compare against ordinary repeated execution. |
| **k8s26980** | The frozen test adds an item, starts `pop(stopCh)`, then starts a locker goroutine and treats acquiring the lock as success. No handshake proves that `pop` reached its blocked `nextCh` send before the competing lock acquisition. In C1 the defective variant produced 0/60 focal witnesses. | Possible vacuous pass: the test may satisfy its assertion without reaching the intended blocked-send state. This is a schedule-precondition deficit, not evidence that the scheduler caused the observed zero. | Static/event-sequence check first; then a deterministic handshake or scheduler control. Reject generic timeout-only witnesses. |
| **istio17860** | The defective variant produced a focal witness in all 60 C1 attempts (30/30 per profile), while the acceptable variant passed ([post-collection review](../../research_runs/ci_configuration_2026_09/analysis_audit/POST_COLLECTION_REVIEW.md)). | A negative control for over-intervention: the existing witness is already adequate under the tested conditions. | The system should say "no intervention needed". An AI workflow that rewrites or schedules this case incurs cost without adding evidence. |

**Cross-case hypothesis.** POOL-162, grpc1859, and etcd5509 can all be described as a conserved capability acquired before an exceptional path and not released on that path: allocation latch/capacity, send quota, and read lock. That analogy is useful for a controlled experiment, but it is not itself novel. Resource acquisition/release specification mining is established, and InferROI already combines LLM intention inference with static checking for resource leaks ([RRFinder](https://doi.org/10.1109/ASE.2011.6100058); [InferROI](https://arxiv.org/abs/2311.04448)). Locks, quota tokens, and pool latches also differ semantically; forcing them into one abstraction may erase the conditions that make their witnesses valid.

## 3. Prior art and novelty pressure

This is a targeted primary-source scan, not an exhaustive systematic review or a claim of absence.

### Direct threats

- **Themis, NSDI 2026** combines static race analysis, LLM test generation, directed input fuzzing, and interleaving exploration. Its authors explicitly organize detection around reaching racy statements, triggering the buggy interleaving, and satisfying failure conditions; they also report that LLM-produced tests rarely reach the target or manifest the symptom without the later stages. This is direct overlap with any generic "LLM understands a concurrency change and generates a witness" claim ([paper](https://www.usenix.org/conference/nsdi26/presentation/cao)).
- **Fray, OOPSLA 2025** provides controlled concurrency testing for JVM programs and evaluates on SCTBench and JaConTeBe, finding substantially more known bugs than JPF and RR chaos mode while also applying to thousands of mature-project tests. Because POOL-162 is a JaConTeBe case, "apply a modern scheduler to a JaConTeBe test" is a baseline or replication, not a contribution ([paper and artifact](https://github.com/cmu-pasta/fray)).
- **DeltaScout, TU Delft 2026 thesis** uses an AI coding agent to choose interesting events for a sampling-based concurrency scheduler. On JaConTeBe, its pure agent condition found 14/25 versus 15/25 for the random-delta baseline; the hybrid tied the baseline. It found some complementary bugs but did not substantially improve aggregate counts. This is a close warning against assuming LLM schedule guidance will dominate simple random exploration ([repository record](https://repository.tudelft.nl/record/uuid%3Aafc56588-8e7a-464d-bbec-82a343f53371)).
- **DiffTGen** and **DiffGen/EvoSuiteR** already generate tests that expose semantic differences between program versions. DiffTGen reported identifying 39 of 79 likely overfitting patches in its study. A paired repair version and a generated differential test are established ingredients ([DiffTGen paper](https://cs.brown.edu/people/qxin/papers/testgen_issta17.pdf); [EvoSuiteR documentation](https://www.evosuite.org/evosuiter/)).
- **Mokav** explicitly claims execution-driven, LLM-based difference-exposing test generation. This further occupies a generic "LLM + old/new versions -> regression witness" contribution ([publisher record](https://doi.org/10.1016/j.jss.2025.112571)).
- **CodaMOSA** uses LLM-generated tests to seed search-based testing when coverage stalls. The general architecture "LLM proposes semantic seeds, conventional search validates/refines them" is established ([ICSE 2023 paper](https://www.microsoft.com/en-us/research/publication/codamosa-escaping-coverage-plateaus-in-test-generation-with-pre-trained-large-language-models/)).
- **IntUT** uses explicit test intentions to guide LLM unit-test generation. Therefore, extracting an intention and putting it in a prompt is not a defensible novelty claim ([ICSE 2025 record](https://conf.researchr.org/details/icse-2025/icse-2025-research-track/242/Test-Intention-Guided-LLM-based-Unit-Test-Generation)).
- A 2026 replication of HITS, SymPrompt, TestSpark, and CoverUp reports that a plain modern LLM outperformed the elaborate techniques on its coverage and mutation metrics at comparable query cost. Whatever its later peer-review status, it creates a necessary baseline: every proposed cascade must beat a plain, current-model prompt rather than old weak models ([preprint](https://arxiv.org/abs/2601.09695)).
- Oracle generation remains an independent bottleneck. A post-cutoff Java study found LLM oracles with average mutation score near human-designed oracles, but also emphasizes limits for complex oracles and uses explicit contamination controls. A generated test that compiles and covers code is not yet a valid behavioral witness ([ASE 2025 paper](https://homes.cs.washington.edu/~mernst/pubs/neurosymbolic-oracles-ase2025-abstract.html)).

### What may remain worth testing

**Candidate gap, not established novelty.** The repository can join four evidence layers on authentic repair pairs: (a) a source-grounded behavioral obligation, (b) adequacy of tests available at a declared historical time, (c) an executable focal witness distinguished from nuisance or generic timeout, and (d) the final decision after retry or aggregation. Themis covers a close three-stage bug-exposure problem but does not make CI-policy evidence retention the evaluation target. The repository has already measured the fourth layer, including 13 defective-version blocks in which P3 accepted after a focal witness. Whether the four-layer decomposition improves AI-guided testing is unanswered here.

The cautious contribution shape is therefore:

> On retrospective real repair pairs, does an explicit witness-adequacy decomposition help an AI-assisted method choose the right intervention and produce more independently validated, policy-visible witnesses than simple retrieval, static analysis, a plain modern LLM, and scheduler/search baselines at equal budget?

This would be an empirical contribution even if the answer is negative. It is not a claim that the individual components are new.

## 4. Three candidate directions

### Direction A — Jev as a direct semantic feature for TCP

**Mechanism.** For each change/test pair, ask Jev for a bounded relevance score and combine it with history and current T0 relevance.

**Strengths.** The API returns typed scores/choices with probabilities and confidence rather than source code; the vendor positions it for narrow, high-throughput judgments. The local POOL-162 probe showed that a rubric can distinguish two tests that use the changed implementation from an unrelated test ([official API description](https://api.typesafe.ai/docs); [launch description](https://typesafe.ai/blog/introducing-system-one-models-and-jev)).

**Critical weaknesses.** The probe also exposes the ceiling: both top candidates were only level 1 and neither exercised interruption. Ranking inadequate tests earlier does not create a witness. Change-aware semantic ranking is already crowded, while Airavata T0 is null and F1 preserved that null. Jev's confidence is model confidence, not a probability of focal defect detection. The vendor's calibration and speed claims are vendor evidence, not validation on this task.

**Verdict:** reject as the next main direction. Retain Jev only as one component/baseline in Direction B.

### Direction B — typed obligation-gap detection plus deterministic witness routing

**Mechanism.** A generative model extracts a source-anchored obligation and maps each existing candidate test to the four adequacy facets. Jev independently scores the fixed facet questions or candidate-obligation pairs. Code combines the answers and routes only the unresolved facet:

- state/input deficit -> search, fuzzing, or parameter generation;
- schedule deficit -> handshake, systematic scheduler, or stress schedule;
- oracle deficit -> deterministic assertion/signature construction and review;
- policy deficit -> retain first-failure evidence or evaluate the frozen policy reducer.

Every proposed witness is executed on `V_bad` and `V_ok`; model agreement never substitutes for this check.

**Strengths.** It matches the repository's actual variation: POOL-162 lacks the interrupt sequence, k8s26980 may lack a schedule handshake, etcd5509 has a strong oracle but probabilistic trigger, and istio17860 needs no intervention. Jev's typed outputs are a natural fit for the fixed facets, while generative reasoning is limited to evidence extraction and candidate construction.

**Critical weaknesses.** Themis already has a very similar first-three-factor decomposition. InferROI already uses LLM-inferred acquire/release intentions with static validation. The routing code may be engineering rather than research. Public historical cases are likely training-contaminated. False obligations can make an executable but scientifically invalid test.

**Verdict:** recommended, conditionally. Its value must come from a preregistered comparison showing improved intervention choice or witness yield, especially at the policy-visibility boundary. A rubric or architecture diagram alone is insufficient.

### Direction C — LLM-generated concurrency witnesses guided by Fray or another scheduler

**Mechanism.** Ask an LLM to adapt an existing test or create a new one, then use Fray for JVM cases or an appropriate language-specific scheduler/stress harness to explore interleavings. Feed counterexamples back for bounded repair.

**Strengths.** It can turn POOL-162's controlled witness into an executable starting point and directly addresses cases such as k8s26980 where repeated natural execution produced no witness. The output is objectively checkable on a repair pair.

**Critical weaknesses.** Themis, CodaMOSA, Fray, and DeltaScout occupy most of the method combination. A scheduler cannot repair a missing call sequence or oracle; Themis reports this exact failure mode. Fray already includes JaConTeBe. A cross-language system would multiply harness effort before the basic hypothesis is known. The 2026 replication makes a plain current-model generator mandatory as a baseline.

**Verdict:** use as a second-stage execution arm inside Direction B, not as the headline direction. Begin with one JVM case only after restoration and baseline gates pass.

## 5. Proposed experiments

No experiment below is authorized for execution by this document.

### Experiment A — Can AI identify the missing witness prerequisite?

#### Question and hypotheses

- **RQ-A1:** Given only causally available repair-review inputs and the tests available at that time, can a method correctly decide whether an adequate focal witness already exists?
- **RQ-A2:** When it does not, can the method correctly identify the missing facet(s): state/input, schedule/event, oracle, or policy visibility?
- **Null:** the best AI method does not materially improve episode-level exact diagnosis over the strongest simple baseline at equal evidence and budget.

#### Dataset

Use a development set and a sealed confirmation set.

- **Development-only cases:** POOL-162, grpc1859, etcd5509, k8s26980, and istio17860. These cases define failure modes and test the harness. They are public and have already been inspected; they cannot support a clean model-generalization claim.
- **Provisional confirmation acquisition target:** at least 36 independently adjudicated repair episodes from at least six projects, with at least 12 cases where an adequate pre-existing witness is present in the frozen candidate universe, 12 where one is not found in that universe, and 12 unresolved/partial cases. This is a planning target, not a powered sample-size result. Balance is for diagnostic evaluation, not a prevalence estimate.
- Keep all manifestations of one root defect in one episode. Split by project and defect family, never by individual test.

For each episode freeze a T0 bundle:

1. parent revision and tests available at T0;
2. production change available at review time, if the task is repair-review assessment;
3. issue/discussion text whose timestamp is no later than T0;
4. no added regression test, later review comment, future execution result, or acceptable-version outcome.

The future regression test and paired outcomes are evaluation oracles only. A human panel must independently state the focal obligation and the set of defensible adequacy interpretations before model scoring. Human adjudication remains necessary and visible, but it does not manufacture a unique causal ground truth when several interventions could work. The post-fix test is an assessment-only human reference, not automatic truth. A label that no adequate witness is present means only that none was established in the frozen candidate universe and evidence; it is not proof that no test, input, or schedule exists.

#### Compared methods

1. **Random/name-only retrieval.** Random candidate and test-name token overlap.
2. **Repository cheap baseline.** Frozen T0/BM25-style diff-to-test relevance plus file/path overlap.
3. **Static baseline.** Changed-method call reachability, exception/cancellation edges, and simple acquire/release/post-dominance rules where applicable.
4. **Plain modern LLM.** One prompt with the same evidence bundle and a fixed structured output; no tools or self-repair.
5. **Jev-only judge.** Fixed typed facet questions over the same evidence. It may abstain but cannot invent tests.
6. **Proposed cascade.** Generative obligation extraction, retrieval/static evidence, Jev facet scoring, and deterministic rule combination.

The same candidate-test set and token-visible source are supplied to every eligible method. Tool-derived context counts against the method's time and compute budget.

#### Outcomes

- **Intermediate diagnostic outcome:** episode-level exact match on `(witness_present_in_frozen_universe, missing_facets)` where the panel supports a determinate label. Where several facet descriptions or interventions are valid, score against the frozen admissible set and report partial agreement rather than forcing one answer. Executable witness yield in Experiment B remains the main outcome for the research direction.
- **Safety-primary:** recall for true witness gaps and false "adequate" rate on gap episodes.
- **Secondary:** macro-F1 per facet, Brier score for probabilistic outputs, selective accuracy versus abstention, evidence-anchor precision, candidate recall@k, latency, token count, dollar cost, and human adjudication minutes.
- Repeated model calls characterize instability but do not increase the statistical sample size. The episode is the unit; use paired episode-level permutation or exact tests and project-clustered bootstrap intervals.

#### Success and stop rules

- Before scoring methods, stop and repair the dataset if independent adjudicators cannot reach at least 0.70 Krippendorff's alpha on the four facets after reconciliation training. Report both pre-reconciliation reliability and the adjudicated record; consensus after discussion does not erase initial ambiguity.
- Promote the cascade only if its confirmation-set exact diagnosis improves by at least 10 percentage points over the strongest non-AI baseline **and** the lower bound of the project-clustered 95% interval on the paired improvement is above zero.
- Reject it if a plain modern LLM is within five percentage points at lower total cost, if the static baseline is within five points with fewer harmful false-adequate decisions, or if the observed confident false-adequate fraction exceeds the predeclared practical limit. Any 5% limit is an investment rule, not a certified error-rate bound: 36 total episodes, and especially 12 gap episodes with zero misses, cannot establish a population false-adequate rate below 5%. A confirmatory rate claim needs a separate sample-size calculation and substantially more independent gap episodes.
- Treat abstention as acceptable only when coverage is reported. Do not convert abstentions into correct answers.

### Experiment B — Does the diagnosis produce an executable, focal witness?

#### Question and design

Select the first 12 Experiment-A gap episodes that pass restoration and oracle gates, without choosing by method performance. Start with one language; JVM is attractive because Fray and JaConTeBe provide strong baselines, but only if the historical build can be restored within a predeclared cap.

For each episode compare, with equal wall-clock and execution budgets:

1. nearest existing test plus a human-written deterministic template edit;
2. EvoSuiteR/DiffTGen-style differential generation where applicable;
3. Fray/random schedule exploration from the best existing test for JVM concurrency cases;
4. plain modern LLM test generation;
5. plain LLM plus compile/test repair feedback;
6. Direction-B diagnosis followed by the routed intervention; and
7. an ablation without Jev to test whether Jev adds value beyond the generative model and deterministic rules.

Each condition receives a fresh isolated workspace. Cap repair loops and executions in advance. Preserve every failed candidate; selecting only the best-looking generation is part of the treatment and must consume budget.

#### Valid witness contract

A candidate succeeds only if all are true:

- it compiles and runs in the frozen environment;
- it produces the predeclared focal signature on `V_bad` within the fixed schedule/execution budget;
- it does not produce that signature on `V_ok` under the same protocol;
- its oracle refers to the behavioral obligation, not merely process exit or a broad timeout;
- it does not read the withheld future test or future outcomes; and
- its result remains visible under the named CI policy, or the loss of visibility is explicitly recorded.

For intermittent witnesses, report block-level detection probability and uncertainty, not a binary success after unlimited reruns. For controlled schedules, report them separately from natural manifestation; deterministic exposure is not evidence of natural intermittency.

#### Outcomes and stop rules

- **Primary:** number of episodes with at least one valid witness under equal budget.
- **Secondary:** time to first witness, compile success, focal specificity, `V_ok` false positives, attempts, vCPU-hours, human minutes, model calls, and policy-visible detection under P1/P3/P3-retain.
- Stop an episode when its build/restoration cap is reached; do not substitute a simplified synthetic subject while retaining the real-defect claim.
- Stop the AI execution line if it yields fewer valid witnesses than the strongest conventional baseline after six episodes, or if its only gains are generic timeouts or future-test reconstructions.
- Continue to a larger confirmation only if it adds at least two valid episode-level witnesses over the strongest baseline in the 12-episode feasibility set and neither added witness depends on contaminated future evidence.

### Experiment C — Does the acquire/exception/release analogy transfer?

#### Question

Can an obligation representation learned or prompted from one resource family help diagnose a different family without leaking the target's known fix/test?

Use leave-one-family-out evaluation over capacity latches, quota tokens, locks, and at least two additional independently acquired families. Compare:

1. lexical `acquire/release` rules;
2. static exceptional-path/post-dominance analysis;
3. a plain LLM with no demonstrations;
4. demonstrations from the same family;
5. demonstrations only from other families; and
6. the typed cross-family representation.

The primary outcome is exact missing-facet diagnosis, followed by valid-witness yield if Experiment B continues. A transfer claim requires improvement in the other-family condition, not merely better performance with target-family examples.

**Stop rule:** abandon the cross-family abstraction if static analysis matches it within five points, if errors cluster by resource semantics, or if gains disappear after identifiers and issue IDs are removed. In that case, retain separate domain-specific obligations.

## 6. Temporal validity, contamination, and independence

### Temporal protocol

- Define the decision time before building each episode bundle. Every source fragment, test, issue comment, and tool output needs an `available_at` timestamp or an explicit `unknown` status.
- A repair-pair experiment is retrospective. `V_ok` may validate the evaluator but is not knowledge available to a pre-fix or review-time method.
- For repair-review assessment, the production diff may be available while a regression test added later in the same series is withheld. Record this choice explicitly; do not switch between bug discovery and patch assessment in the interpretation.
- Historical execution features must be limited to completed, available observations, not merely earlier build start times.

### Foundation-model contamination

POOL-162, etcd5509, grpc1859, JaConTeBe, and other public historical artifacts may be in foundation-model training data. Renaming identifiers or omitting issue numbers is only a memorization sensitivity check; it cannot prove absence of contamination.

Accordingly:

- use the named repository cases only for mechanism development and qualitative case analysis;
- reserve the main capability estimate for post-model-cutoff or access-controlled episodes whose contents were not public before the frozen model snapshot;
- record provider, exact model ID, date, parameters, prompt hash, source bundle hash, and full response;
- do not silently accept a provider alias that changes weights during the experiment;
- report public, post-cutoff, and access-controlled strata separately;
- include identifier-scrubbed and semantically equivalent reorderings as diagnostics, not proof of cleanliness; and
- never allow a model that saw confirmation labels or withheld tests to be scored on that set.

The unbiased-oracle study's use of tests created after model cutoffs is a useful precedent, but closed providers may not disclose adequate cutoffs. If a clean stratum cannot be built, restrict the conclusion to tool behavior on known historical cases.

### Oracle and assessor independence

- Human gold obligations must cite issue/fix/source evidence and be fixed before method outputs are revealed.
- Method outputs are anonymized for adjudication.
- The model that proposes a witness does not judge its correctness.
- A generated witness is checked by paired execution, the frozen focal signature, and manual source review where the signature is not mechanically sufficient.
- Multiple model samples are dependent outputs, not independent replications.

## 7. Budget and cost accounting

Use staged ceilings. Effort is not the limiting concern, but unlimited search destroys interpretability.

| Stage | Ceiling | Required accounting | Exit |
|---|---:|---|---|
| A0: five-case harness | 40 generative calls, 100 Jev judgments, 1 million input tokens, 16 allocated vCPU-h, 20 researcher-hours, at most USD 100 in external-model charges | calls, tokens, provider charge, wall time, adjudication time, artifact hashes | schemas and baselines run end to end; no effectiveness claim |
| A1: 36-episode confirmation | 720 generative calls, 2,000 Jev judgments, 12 million input tokens, 120 allocated vCPU-h, 120 researcher-hours, at most USD 1,000 in external-model charges | cost per episode and per correct diagnosis; abstentions and failed calls retained | Direction-B retain/reject decision |
| B: 12 restored episodes | 240 generation/repair calls, 300 scheduler/search runs per episode maximum, 300 allocated vCPU-h, 160 researcher-hours, at most USD 1,000 in external-model charges | build/restoration failures, execution attempts, scheduler decisions, human edits, cost per valid witness | witness-generation retain/reject decision |
| C: transfer | reuse A1 episodes; no new subjects until A1 passes | same metrics plus family-stratified results | cross-family abstraction retain/reject decision |

The money ceiling should be computed from provider prices on the freeze date and written as both currency and token/call caps. Token/call caps govern if prices change. Jev's advertised low price does not excuse unlimited queries, and paid calls require separate authorization. Human review time, compilation attempts, and vCPU-hours belong in the same cost table; model API price alone is not efficiency.

## 8. Minimal artifact schema

Each method should emit a closed, reviewable record rather than prose alone:

```json
{
  "episode_id": "...",
  "decision_time": "...",
  "obligation": {
    "acquire_or_precondition": [{"claim": "...", "source_anchor": "..."}],
    "exception_or_competing_event": [{"claim": "...", "source_anchor": "..."}],
    "required_release_or_progress": [{"claim": "...", "source_anchor": "..."}],
    "observable_violation": [{"claim": "...", "source_anchor": "..."}]
  },
  "adequacy": {
    "state_input": {"status": "met|missing|unknown", "evidence": []},
    "schedule_event": {"status": "met|missing|unknown", "evidence": []},
    "oracle": {"status": "met|missing|unknown", "evidence": []},
    "policy_visibility": {"status": "met|missing|unknown", "evidence": []}
  },
  "recommended_intervention": "none|input_search|schedule_control|oracle_work|policy_retention|unknown",
  "confidence": null,
  "abstained": false
}
```

Schema validity establishes only that the output is well formed. It does not make Jev's probabilities calibrated for this task or make the obligation true.

## 9. Practical sequence

1. Freeze the five repository cases as development examples and write their source-anchored gold records. Include istio17860 as the "do nothing" control and k8s26980 as the possible vacuous-pass case.
2. Implement only the artifact schema, evidence-bundle builder, and scoring harness. Do not integrate any model into the production TCP pipeline.
3. Run the non-AI baselines first. If static reachability plus simple exceptional-path rules resolve the cases, preserve that result.
4. If external calls are later authorized, run plain modern LLM and Jev baselines before building a cascade. Cache exact requests/responses and pin model IDs.
5. Acquire and adjudicate a sealed confirmation set. Public old cases remain development examples.
6. Begin executable witness generation only if Experiment A shows incremental diagnostic value. Restore one language and one case family first.
7. Evaluate CI-policy visibility using the existing deterministic reducers. Do not collect another C1 CPU-profile cohort; the signal audit's STOP recommendation stands unless a new mechanism-derived protocol is separately approved.

## 10. Final critical assessment

The parent's suggested idea—semantic analysis of missing behavioral obligations followed by executable witnesses—is better aligned with the repository than another ranking model, but its broad form is not novel. Themis, InferROI, IntUT, DiffTGen/Mokav, CodaMOSA, Fray, and DeltaScout collectively occupy semantic extraction, LLM test generation, differential testing, resource-intention inference, and scheduler guidance.

The narrower question worth owning is empirical: can a typed adequacy diagnosis keep an AI system from applying the wrong intervention, and can that improve *focal, paired, policy-visible* witness production on real repair episodes? POOL-162 shows why relevance is insufficient; k8s26980 shows why a passing test may be vacuous; etcd5509 shows why a valid oracle does not make an environmental contrast causal; istio17860 shows why the system must sometimes decline to act; and C1 shows why policy decisions must retain evidence rather than summarize only final green/red status.

If simple static rules, a plain modern LLM, or a scheduler baseline match the cascade, stop at the simpler method. If clean held-out episodes cannot be obtained, publish only a case study or benchmark construction result. If the cascade improves only on public historical cases, treat contamination as the leading explanation. The research becomes credible when every claimed gain ends in an independently validated witness and every negative result remains visible.

## AI-assistance disclosure

This assessment was drafted with AI assistance. Literature claims were checked against the linked primary or authoritative sources, and repository claims were tied to local evidence. No model output in this document is an empirical result, an executable witness, or a novelty determination.
