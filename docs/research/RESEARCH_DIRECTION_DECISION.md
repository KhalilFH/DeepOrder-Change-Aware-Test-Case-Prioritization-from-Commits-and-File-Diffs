# Research direction decision

- **Date:** 2026-09-07.
- **Status:** Proposed investment decision; no experiment executed under this document.
- **Purpose:** Choose the next research investment among test-maintenance validation, adaptive CI investigation, and evidence expiration. This is a comparison of three existing proposals, not a search for more visions.
- **Repository baseline:** `d967dbaaec257613c3e1f2440866801c71d0c00e`, `research/revival-2026`.
- **Method:** Single-agent analysis of repository evidence, the two prior design documents, and targeted primary literature. No delegation or additional model review in this pass.
- **Scope of authorization:** Creation of this document only. The sprint below is a proposal, not an instruction to start execution or acquire infrastructure.

## 1. Decision

**Inference — first choice:** Fund **test-maintenance validation**, initially for a maximum 30-day qualification sprint. Its question is whether maintenance that reduces unwanted CI failures also removes useful defect detection, and whether existing validation catches that loss. Fund an assessment study, not a repair generator.

**Inference — second choice:** **Adaptive evidence acquisition / CI investigation**, restricted initially to controlled differential reproducibility. It offers the clearest measurement and fallback experiment, but its smallest version has a weak novelty-to-effort ratio.

**Inference — third choice:** Defer **evidence expiration across software changes**. It has substantial intellectual upside, but the present framing overlaps both dependency-based retesting and property-aware incremental verification. The repository has no established representation of behavioral claims that would distinguish it.

The first choice does not win on data readiness or ground-truth quality. It wins on the value of discovering a consequential gap in an existing engineering decision: accepting a test repair. That judgment is conditional. If independent challenges cannot be constructed, or existing validation already identifies the consequential losses, stop funding a new validator. Do not turn a failed qualification sprint into an indefinite artifact-recovery project.

### Evidence labels and assumptions

- **Repository evidence:** Inspected code, artifacts, history, or documents. A reported experiment without recovered outputs is identified as such.
- **External evidence:** Facts attributed to linked primary sources; the literature check is focused rather than exhaustive.
- **Inference:** Interpretation, comparative judgment, or investment preference.
- **Proposal:** A future procedure, numerical threshold, or criterion not yet validated.
- **Speculation:** Conditional industry or long-term outcomes.

**Proposal assumptions:** One researcher, six months to obtain meaningful evidence, a two-year research horizon, no guaranteed industry partner, and no currently qualified executable artifact pool for these new questions. Existing code can be adapted later, but access to a CSV or Git commit does not imply access to executable counterfactual outcomes. Independent ground truth means independent of the method being assessed; it does not mean asking another language model to endorse its answer.

## 2. Evidence basis and what it changes about the decision

**Repository evidence.** The required [RESEARCH_STATE.md](RESEARCH_STATE.md), [TRAJECTORY.md](TRAJECTORY.md), [EXPERIMENTS.md](EXPERIMENTS.md), and [DECISIONS.md](DECISIONS.md) remain scaffolds. The substantive experimental narrative is [the August findings](change-aware-tcp-findings-2026-08.md), added in `fd36568`; the current pipeline arrived in `820647e`.

**Repository evidence.** The archived Airavata report at `25eb6b7:FINAL6/apache@airavata/step3_report.json` reports a -0.0061 paired APFD difference for HIST+T0 versus HIST on 30 small-failure cycles, with p approximately 0.917. This was checked again in this pass. HBase/Hive persistence-APFD gains remain documented results whose supporting raw outputs were not recovered in the earlier audit. These results motivate questions; they do not establish any of the three new premises.

**Repository evidence from the code audit.** `pipeline/step3_regapfd.py::regression_labels` uses the next execution's failure as a persistence proxy. `pipeline/lrts_adapter.py` constructs histories and identity/change joins, but current duration and result-availability chronology require care. `pipeline/relevance_t0.py` provides inexpensive path/name relevance, with vocabulary fitting requiring a temporal audit. `pipeline/step3_t0.py` supplies prequential comparisons, not an interactive execution system. See the evidence reconstruction in [INDEPENDENT_RESEARCH_VISION.md](INDEPENDENT_RESEARCH_VISION.md), sections 2 and 10.

**Inference.** None of the following follows from the current results: that recurring failures are harmless flakes; that test repairs commonly destroy protection; that different incidents need different next actions; or that prior testing conclusions can be transferred semantically across revisions. Each is a competing hypothesis requiring new evidence.

**Repository evidence.** [ADAPTIVE_CI_RESEARCH_PROGRAM.md](ADAPTIVE_CI_RESEARCH_PROGRAM.md) already defines a two-action pilot, independent assessment observations, budgets, and baselines. [INDEPENDENT_RESEARCH_VISION.md](INDEPENDENT_RESEARCH_VISION.md) proposes a four-cell maintenance comparison and identifies evidence expiration as an alternative. Both are unexecuted designs. Their detail or recency must not be mistaken for empirical support.

## 3. Keep the scientific objects separate

| Direction | Variable being changed | Fixed object for the first study | Target conclusion | Statistical unit |
|---|---|---|---|---|
| **M: Test-maintenance validation** | Test, fixture, or harness maintenance patch | Specified product behavior and controlled implementation/challenge pair | Whether the intervention reduces unwanted failures while retaining sensitivity to specified defects | Maintenance intervention, grouped by shared repair/root cause |
| **A: Adaptive CI investigation** | Which execution action to request next | One index symptom, target test, head/reference pair, and environment protocol | Differential reproducibility and whether another observation is worth its cost | Failure episode, not rerun |
| **E: Evidence expiration** | Product revision or declared environmental assumption | Explicit behavioral obligation and observation procedure | Whether prior support can be reused for the new context, must be renewed, or is insufficient | Obligation–revision transition, grouped by change/project |

**Inference.** A historical fact such as “test T passed at revision R0” does not expire. The *justification for applying that observation to R1* may fail. Without this distinction, E risks becoming a renamed cache-invalidation system or an unjustified claim that passing tests prove behavior.

### M — Test-maintenance validation

**Proposal — core question:** Can an independent assessment identify maintenance changes that reduce unwanted failures by also reducing sensitivity to independently justified defects, beyond what existing repair validation detects?

**Potential contribution:** A credible intervention benchmark and evidence that a bounded assessment catches meaningful losses overlooked by reruns or static preservation checks. A new repair algorithm is unnecessary. A useful negative result would establish that a strong existing validator suffices for a declared repair class.

**Industry problem:** Reviewers need to distinguish a fixture/isolation repair from a change that simply prevents a test encountering the faulty behavior. Removing assertions is an easy case; unchanged assertions with changed inputs, mocks, or schedules are more demanding cases.

**Minimum premise experiment:** Run old and repaired tests against a reference implementation and a justified defective variant under matched conditions. Compare four cells, recording signatures as well as pass/fail. Establish the behavioral obligation independently; not every lost failure or mutant kill is harmful. Include legitimate and harmful controls, but do not use manufactured controls to estimate real-world prevalence.

**Actual transfer:** Recurrence analysis for screening; test/change identity joins; causal evaluation discipline; explicit negative-result handling. The classifiers and APFD reports contribute little directly.

**New requirements:** Authentic maintenance patches, buildable revisions, controlled nuisance conditions, defect challenges, behavioral obligations, and a validation baseline that can actually run. A merged repair is not a sensitivity-preservation label.

### A — Adaptive evidence acquisition / CI investigation

**Proposal — core question:** After a CI failure, does choosing the next head/reference execution from observed outcomes improve controlled reproducibility estimation or supported conclusions at a fixed cost, compared with strong fixed playbooks?

**Potential contribution:** A reproducible account of when outcome-dependent allocation helps and when it does not. A broader investigation contribution would require additional heterogeneous actions and diagnostic outcomes; it cannot be claimed from this initial study.

**Industry problem:** Teams spend time rerunning failures without knowing when a comparison or further rerun is informative. A small tool could standardize that process, even if adaptation proves unnecessary.

**Minimum premise experiment:** Qualify several authentic head/pre-change pairs, collect independent outcome streams, and compare fixed allocations with the simple adaptive selector from the existing program. Score held-out recurrence outcomes and scoped conclusions, with identical tools, parsers, stopping criteria, and budgets. A later passing fix is not the pre-change reference.

**Actual transfer:** Historical identities and causal features can supply optional context; evaluation discipline and the existing written protocol transfer strongly. T0 is not an execution-policy comparator when there is only one fixed test. No current script supplies the action/observation loop.

**New requirements:** Executable references and fresh runs, environments, reliable signature parsing, cost accounting, and independent assessment streams. Historical CSVs do not simulate these actions.

### E — Evidence expiration across changes

**Proposal — core question:** For a declared behavioral obligation, can a method determine when evidence from a prior revision remains applicable more usefully than dependency-based invalidation, without unsupported reuse?

Represent an evidence item minimally as `(obligation, input scope, revision, test/oracle, environment assumptions, observation/proof, provenance)`. A claim about a finite recorded input set is distinct from a claim over all inputs. Start with the former or explicitly formal properties; do not silently move between them.

**Potential contribution:** A scoped account of evidence transfer, with independently verified examples of justified reuse or necessary renewal that existing approaches cannot handle effectively. Simply adding configuration files to dependency tracking is not such a contribution.

**Industry problem:** Teams either rerun too much or reuse stale conclusions when dependencies, configuration, or assumptions change. The useful output is a reasoned renewal requirement or justified reuse, not an opaque expiration score.

**Minimum premise experiment:** Assemble a small set of explicit obligations and revision transitions. Compare an enriched dependency/environment invalidator with a proposed obligation-aware judgment. Check disagreements using independent witnesses or applicable verification tools. Agreement of rerun outcomes on a few inputs cannot prove semantic transfer.

**Actual transfer:** Change extraction and identity mapping assist bookkeeping. Neither T0 nor historical failures provide obligations, proofs, or evidence-validity labels.

**New requirements:** Explicit properties or accepted behavioral contracts, revision-compatible executable systems, dependency instrumentation, and independent transfer witnesses. This is a larger shift toward program analysis and specification than the other options.

## 4. Most dangerous prior-art overlaps

| Direction | External evidence | Consequence for novelty |
|---|---|---|
| M | [Intent-Preserving Test Repair, ICST 2019](https://damorim.github.io/publications/xiangyuETAL-icst2019.pdf) models test intent with dynamic symbolic path conditions. [FlakyDoctor, ISSTA 2024](https://yangc9.github.io/files/ChenETAL24FlakyDcotor.pdf) combines analysis, LLM repair, and execution validation. [FLEX, FSE 2021](https://www.cs.cornell.edu/~saikatd/papers/flex-fse21.pdf) statistically adjusts assertions/reruns for randomized ML tests. | “Preserve intent while fixing flakes” is occupied. The candidate gap is independently measured defect sensitivity under nondeterminism across maintenance interventions. It must survive comparison with these methods where applicable. |
| A | [SEQUOIA](https://ojs.aaai.org/index.php/AAAI/article/view/7844) performs information-guided sequential diagnosis. [Flake Aware Culprit Finding](https://research.google/pubs/flake-aware-culprit-finding/) uses probabilistic reasoning for noisy software failures. | Adaptive diagnosis and Bayesian action selection are occupied. The two-action pilot might support a careful empirical result; “an agent chooses an informative rerun” does not establish novelty. |
| E | [Ekstazi](https://users.ece.utexas.edu/~gligoric/papers/GligoricETAL15EkstaziTool.pdf) tracks dynamic file dependencies, including resources. [Difference Verification with Conditions](https://www.sosy-lab.org/research/difference/) reuses prior verification through change analysis. [Property Differencing](https://ntrs.nasa.gov/citations/20140010016) explicitly considers changes to properties as well as programs. | Neither dependency invalidation nor property-aware renewal is new. The dangerous overlap extends beyond ordinary TCP into incremental verification; adding the word “evidence” is insufficient. |

**Inference.** E currently has the largest unproven gap between an attractive phrase and a distinct contribution. M also has severe overlap, but there is a concrete assessment task on authentic patches that can test whether a gap remains. A has the clearest experiment but the least ambitious immediate contribution.

## 5. Comparative decision matrix

**Inference.** Scores are ordinal judgments about the concrete versions above. For all rows except **novelty risk**, 5 is favorable and 1 unfavorable. For novelty risk, **5 means greatest overlap risk**. Scientific importance refers to the first defensible question; two-year upside includes conditional extensions. There is no claim that intervals between scores are equal.

| Dimension | M: maintenance validation | A: adaptive investigation | E: evidence expiration |
|---|---|---|---|
| Scientific importance | **5** — tests can become quieter while losing their intended discrimination | **3** — the first study concerns allocation for two reproducibility rates | **4** — validity of transferring evidence is fundamental if precisely scoped |
| Novelty potential | **3** — independent cross-intervention sensitivity assessment may add something | **2** — small allocation problem has extensive methodological precedent | **3** — uncertain evidence/assumption transfer may offer a gap, not yet established |
| Novelty risk, high = bad | **4** — intent preservation and repair correctness are close neighbors | **5** — sequential diagnosis and probabilistic culprit finding are direct overlaps | **5** — both test selection and incremental verification occupy the core framing |
| Six-month feasibility | **3** — a useful cohort is plausible; independent challenges may block it | **4** — explicit protocol, simple controller, narrow estimand | **2** — obligation representation and independent transfer judgments must be invented or recovered |
| Executable artifact availability | **3** — repair collections identify candidates, not qualified four-cell subjects | **3** — BugSwarm supplies a starting environment, not authentic parent reruns | **2** — code pairs exist; paired obligations and reusable evidence generally do not |
| Ground-truth quality | **2** — authentic defects and correct obligations are difficult to pair | **4** — fresh held-out runs assess recurrence, conditional on protocol stability | **2** — observed passes are weak evidence of semantic applicability |
| Industry value | **4** — concrete maintenance-review decision; incremental value unmeasured | **3** — standardizes triage, but fixed automation may capture most value | **4** — less redundant checking and stale reuse could matter greatly |
| Repository leverage | **2** — conceptual/methodological transfer outweighs code and data reuse | **3** — protocol and evaluation concepts transfer; runners remain new | **2** — change joins help, semantic evidence machinery is absent |
| Evaluation clarity | **3** — four-cell design is clear; challenge validity is the hard part | **5** — proper scores and charged costs on independent observations are explicit | **2** — “still applicable” needs scoped proof or witness, not another classifier label |
| Two-year upside | **4** — coherent path from assessment benchmark to review validation | **3** — larger action spaces could matter, but need separate premise tests | **5** — potentially substantial evidence-transfer theory and tooling, with high execution risk |

**Uncertainty.** Treat differences of one point as weak preferences. M's ground-truth and feasibility scores could move by two points after artifact qualification. A's artifact score could fall sharply if original parents cannot be built; its clarity score would fall if the target were changed to “root-cause correctness.” E's upside is speculative, not compensation for missing evidence. No score is an estimated publication probability.

**Decision rule.** Do not sum correlated criteria such as ground truth and evaluation clarity. I prioritize (1) a consequential claim beyond existing methods, (2) a bounded way to discover whether its premise exists, then (3) time and reusable assets. Under a different objective—maximize the chance of a clean quantitative result within six months—A would win. Under a formal-methods team's resources and explicit specifications, E could rise. With the stated one-researcher assumptions, M merits one bounded sprint, not unconditional preference.

### Additional dimensions that a score can conceal

| Dimension | M | A | E |
|---|---|---|---|
| Scientific depth versus engineering | Deep only if measurement distinguishes preserved sensitivity from apparent repair; a PR dashboard is engineering | Deep only beyond a standard allocation result or through a consequential empirical boundary; a rerun wrapper is engineering | Deep if scoped semantic transfer is established; manifests and cache invalidation alone are engineering |
| Falsifiability | Can stop if strong validators already catch the independently justified losses in the chosen class | Can stop if fixed playbooks cover the useful cost/accuracy frontier in the qualified setting | Can stop if disagreements reduce to dependency completeness or existing verification decisions |
| Data availability | Public repair leads; no ready independent sensitivity labels | Public CI artifacts; no ready action-outcome bank | Source histories; little obligation-level evidence history |
| Credible publication | Independent repair-assessment benchmark, meaningful validator limitation, or effective assessment method | Reproducible positive/negative allocation study; broader diagnosis claims require more | Scoped transfer method or impossibility/boundary result with sound assumptions |
| Likely research audience | ISSTA/ICST/ASE and empirical software engineering | ISSTA/ICST and industrial CI research | ASE/ICSE; verification audiences only with substantive formal results |

These are possible contributions, not predictions of acceptance. All three remain objectively evaluable only if model-generated explanations are excluded as ground truth.

## 6. Repository leverage, separated rather than inflated

| Kind of reuse | M | A | E |
|---|---|---|---|
| Conceptual | Recurrence and co-failure motivate intervention-level measurement | History and change context motivate uncertainty after failure | Change/test associations motivate evidence scope |
| Code | Adapter identity joins and screening utilities may transfer | History helpers and evaluation utilities may transfer; no runner exists | Changed-file extraction and identity joins only |
| Dataset | Airavata/LRTS identify candidates, not repair effects | Tables supply context, not unobserved actions | Tables supply observations, not validity or obligations |
| Methodological | Causal timing, paired comparisons, negative controls, episode grouping | Same, plus detailed existing action-bank protocol | Same, plus an explicit distinction between observations and proofs |

**Inference.** A is the closest continuation, but “closest” does not mean inexpensive: none has the executable experimental substrate it needs. M is a deliberate research pivot. E is closer to a new program-analysis project than a natural extension of the current classifier.

## 7. Required artifacts: realistic sources and limitations

**Repository evidence / external evidence.** Source existence is distinguished from current executability. Public documentation was inspected; no candidate environment was built or rerun in this pass.

| Source | What it gives; best fit | What it does not give | Reconstruction burden and ground-truth limit |
|---|---|---|---|
| Local Airavata execution tables and archived outputs | Build/test history, durations, changes, and a preserved null result; context for all three | Controlled reruns, sensitivity effects, or evidence-transfer labels | High to obtain historical executable environments. Temporal signatures do not establish flakes or causal defects. |
| HBase/Hive/LRTS | Adapter plus documented experiments; recoverable source dataset can provide large longitudinal histories and compare metadata | Guaranteed local inputs, matched repair/challenge pairs, or counterfactual runs | Recover data, verify stage/revision identities, then reconstruct environments. Persistence and recurring names are weak cause labels. See [LRTS primary study](https://samchengcs.github.io/paper/cheng2024revisiting.pdf). |
| [BugSwarm](https://www.bugswarm.org/docs/introduction/what-is-bugswarm/) | Historical failing/later-passing build pairs and reproduction infrastructure; best initial lead for A | A later passing fix is not A's pre-change reference; not generally a test-maintenance pair or a behavioral obligation | Medium-to-high: qualify target, authentic parent, dependencies, and reset conditions. Reproduction status is not defect causality. |
| [CI-Bench](https://github.com/BugSwarm/CI-Bench) | BugSwarm-based evaluation/runner infrastructure; possible wrapper reuse for A | An independent dataset or a controlled head/base observation bank | Audit actual artifact compatibility; repair success is a different target. Do not count overlapping subjects twice. |
| [IDoFT](https://github.com/TestingResearchIllinois/idoft) | Test identities, detected SHAs, categories, repair/PR links and statuses; best lead for M | Independent labels of sensitivity preservation or guaranteed currently buildable subjects | Medium-to-high: locate exact patches and separate test from production edits. Accepted/DeveloperFixed status is not correctness proof. |
| [FlakyDoctor artifacts](https://github.com/Intelligent-CAT-Lab/FlakyDoctor) | Existing repair subjects and tool outputs; M baseline and candidate pool | An independent challenge oracle or representative population of all maintenance | Reproduce relevant validation, deduplicate with IDoFT, qualify patch/environment pairs. Tool validation cannot be its own final assessment. |
| Historical GitHub CI and issue-linked revisions | Actual patches, rationales, logs where retained; M and E | Complete environments, durable logs, formal specifications, or unbiased repair selection | High and variable; deleted artifacts and co-changing code are serious problems. Issue text can justify scope but remains fallible. |
| Incremental-verification benchmark/artifact collections | Explicit properties and program pairs; E has a better fit here than in TCP tables | Representative noisy integration-test evidence or an automatically novel question | Tool/language adaptation; formal ground truth may be strong inside a narrow model. Existing method superiority is a real possible outcome. |
| Prospective partner CI | Controlled repeats, actual interventions, availability timestamps, and human workflow outcomes if collected | Guaranteed access, rapid incident accumulation, or universal defect truth | High organizational cost. Strongest operational relevance; still needs explicit ground truth and consented collection. Not assumed available. |

**Proposal source priorities:** M starts with IDoFT and existing repair artifacts, not forced Airavata reconstruction. A starts with a bounded BugSwarm qualification roster, retaining its parent-reconstruction risk. E starts with explicit-property revision pairs to test whether a distinct problem exists before collecting informal “evidence” logs. A partner is an optional later asset, not an unstated prerequisite hidden in a six-month estimate.

## 8. Cheapest experiments that could stop each direction

**Proposal.** These are investment kill tests for declared scopes, not proofs that entire research fields are exhausted. Technical inability to qualify artifacts is a feasibility stop. An inconclusive small sample is not empirical equivalence. Do not enlarge a failed scope solely to rescue the preferred story.

### M: Does ordinary validation already suffice?

Qualify up to eight authentic maintenance patches across at least two projects from a predeclared roster. Reproduce the relevant existing validator and add a strong cheap baseline: build/test checks, unchanged-assertion checks, and the appropriate order/condition reruns. Use independent behavioral challenges to inspect decisions those methods accept.

**Observation supporting a stop:** Every independently justified sensitivity loss is already flagged by that baseline or an applicable existing method; alleged additional losses vanish when intended behavior is checked. If this holds on the qualified cohort, do not fund a new validator for it. A simple existing procedure may be the appropriate deployable result.

**Limits:** If there are no harmful authentic cases, discrimination has not been tested. Eight clean patches cannot establish that harm is rare; even under an unrealistic IID model, zero events in eight leaves an approximately 31% one-sided 95% upper prevalence bound. Artificial weakening controls test the evaluator, not prevalence. No credible independent challenge is a separate feasibility stop.

**Planning envelope:** The 30-day sprint below, with an earlier stop after ten working days if fewer than four usable patches can be qualified.

### A: Are fixed diagnostic playbooks enough?

Qualify six incident groups on at least two projects. Collect small fresh head/reference streams and separate assessment runs; reuse the 12-action budget, signature scope, and cost accounting from the existing design. Compare alternating, development-selected fixed quotas, cheapest-first, and the simple adaptive selector on held-out episodes. Keep an explicit no-investigation baseline to distinguish the value of execution from adaptation.

**Observation supporting a stop:** Fixed playbooks resolve essentially the same assessment-supported conclusions at equal or lower cost, and outcome adaptation adds neither a material predictive improvement nor meaningful decision savings. Predeclare practical margins, initially 0.01 absolute mean Brier improvement or 20% cost saving at no loss of supported-conclusion coverage. These are investment thresholds, not universal tolerances.

**Limits:** Six episodes will usually be too few to establish equivalence at those margins. Report uncertainty. A lack of observed benefit means withhold the next major investment, not publish that adaptation never helps. A hindsight best fixed allocation per episode is not an upper bound on all adaptive policies. Uniformly reproducible subjects may kill the chosen artifact strategy rather than the broader premise.

**Planning envelope:** Ten researcher-days or 80 vCPU-hours for qualification and a coarse opportunity probe; stop if reconstruction consumes the allowance. The larger protocol remains available if credible heterogeneity and benefit appear.

### E: Does it collapse into dependency tracking or incremental verification?

Take roughly twelve obligation–revision transitions from two tractable projects or existing verification subjects, chosen by change type before method outcomes. Use known input/assumption scope. Compare ordinary file/dependency invalidation enriched with configuration and environment identity; on compatible formal subjects also compare property-aware incremental verification. Examine every claimed advantage with an independent witness.

**Observation supporting a stop:** All claimed expiration decisions follow from ordinary dependencies/assumption hashes, or established verification already handles the residual property-sensitive cases. If the proposed representation changes no useful decision beyond those methods, stop treating E as a distinct research direction.

**Limits:** A rerun pass does not prove reusable semantic evidence. A newly discovered missing dependency shows an instrumentation defect, not necessarily a new evidence theory. Handcrafted semantic counterexamples demonstrate possibility only. If obligations cannot be stated independently, stop before fitting an expiration classifier.

**Planning envelope:** Five to ten researcher-days for a paper-and-artifact mapping plus a few executable disagreements. No general evidence graph or LLM extraction pipeline.

## 9. Industry trajectories and agentic potential

### Products are contingent on the scientific premise

| Direction | Smallest deployable wedge | Possible two-year system | Conditional five-year capability |
|---|---|---|---|
| M | Advisory review check for a test/fixture patch, returning sensitivity-loss witnesses and unknowns | Supported repair-class validator, benchmark, and measured reviewer benefit | Maintenance planning that pairs noise reduction with replacement checks for lost protection |
| A | Bounded rerun/reference comparison report for one failed test | Several validated diagnostic actions, explicit budgets and escalation/abstention | Evidence-driven incident investigation integrated with team workflows, if it beats fixed playbooks |
| E | Explain why a recorded testing claim needs renewal after a change | Scoped evidence manifests and renewal decisions for supported obligations | Reuse and renewal of heterogeneous assurance evidence across software evolution, within explicit assumptions |

**Speculation.** M's user is the test-infrastructure reviewer; A's is the developer or CI on-call investigator; E's is the platform or verification engineer managing repeated validation. Adoption depends respectively on fewer bad maintenance decisions, lower investigation effort, and less redundant checking without stale reuse. None has adoption evidence in this repository. No five-year capability implies authority to approve releases automatically.

### Agents evaluated by task, not branding

| Direction and role | Open-ended reasoning / dynamic tools / observation-dependent actions? | Deterministic alternative and objective test | Classification |
|---|---|---|---|
| M: execute four-cell comparison, compute uncertainty | No / no / only bounded scheduling | Fixed harness and statistics; assess repeatability and valid measurements | **Unnecessary** |
| M: reconstruct unfamiliar intent or search for a subtle counterexample | Yes / potentially / yes | Retrieval, program analysis, guided search; compare independently validated witnesses and total cost | **Optional** initially; potentially useful after a measured bottleneck |
| A: select head versus reference rerun | No open-ended reasoning / trivial tool choice / yes | Explicit probabilistic policy; compare held-out loss, supported conclusions, cost | **Unnecessary** for v1 |
| A: diagnose an unfamiliar multi-component incident with heterogeneous tools | Yes / yes / yes | Strong playbooks plus specialized diagnostic tools; measure cause/action correctness with independent evidence | **Likely useful**, conditional on a later broader action space; not established here |
| E: invalidate dependencies and assumptions | No / no / bounded | Dependency tracking and incremental verification; measure unjustified reuse and unnecessary renewal | **Unnecessary** |
| E: recover an undocumented obligation from code and issue history | Yes / potentially / yes | Human-authored contracts plus retrieval; compare independently accepted scopes and wrong assumptions | **Optional**, with a particularly weak oracle |

**Inference.** No direction currently requires an agent centrally. A policy responding to observations is not automatically an LLM agent. If any agent is later evaluated, give comparison systems the same tools and budgets, count setup and inference cost, and separate evaluator evidence from information the agent may inspect. Multiple agents are not a benefit in this decision matrix.

## 10. Does a coherent umbrella exist?

**Inference.** Yes, as a research theme: **when can a software observation justify a decision after the context producing or consuming it changes?** The shared object is a scoped claim, its supporting observations, and the assumptions linking them.

- M changes the observer and asks whether its discrimination survives.
- A keeps the observer/context fixed and acquires observations to reduce uncertainty.
- E changes the application context and asks whether support transfers.

This is more precise than “AI reliability engineering,” but it is not a single benchmark, estimator, or system objective. The directions need different interventions and different independent assessments.

**Proposal.** Share only provenance concepts and experimental discipline initially. A could later optimize expensive validation actions for M. E could later express the limits of an M assessment after another code change. These are optional connections, not an obligatory three-stage roadmap. Building all three now would dilute the research and hide failures of individual premises behind a broad platform story.

## 11. Investment rationale and what would change it

**Inference.** I would choose M even if the prior document had favored A. The reason is a specific falsifiable engineering concern, not enthusiasm for the latest framing: a test-maintenance decision can alter future protection, and independent assessment can expose the difference. A's cleaner measurements are valuable, but its current central result may remain an application of standard allocation. E requires too many semantic foundations before a distinctive experiment is available.

**Strongest reason against M:** It may reproduce existing repair-correctness work while relying on weaker ground truth than A. A benchmark of artificial defects chosen because they expose weaknesses in particular repairs would be especially unconvincing. This risk is serious enough to make the sprint a condition of funding.

**Evidence that changes the ranking:** M rises if authentic patches expose independently justified losses that applicable existing methods miss across projects. M falls below A if challenges cannot be qualified or ordinary validation handles the cases. A rises if a ready incident collection shows substantial differences in useful actions and a fixed-playbook limitation. E rises if an existing explicit-obligation corpus exposes an unmet transfer problem beyond dependency and property-aware verification. None of those observations is established today.

**Proposal — preserve:** Airavata's negative result; historical experiment commits; the HBase/Hive claims with their verification status; identity/change extraction; failure-structure analysis as screening; causal evaluation discipline; both previous design documents.

**Proposal — stop allocating primary effort:** APFD optimization, embedding substitutions, classifier tuning, persistence labels as causal regression truth, broad dependency-graph construction without a discriminating experiment, and a general agent platform. Preserve files rather than delete inconvenient work. The adaptive protocol can remain a fallback without receiving concurrent implementation effort.

## 12. Next 30 days: qualification sprint for M only

All quantities here are **Proposal** limits, to freeze before outcomes. The sprint buys a decision about the next six months. It does not aim to deliver a platform or a definitive prevalence estimate.

### Days 1–4: the literature question

Ask: **Which existing test-repair validation methods measure retained defect sensitivity under changed fixtures, isolation, or inputs, rather than only restored execution success or a static intent proxy?** Read the directly relevant validation and evaluation sections of TRIP, FlakyDoctor, FLEX, and their immediate validation antecedents. Record exact overlap, applicability, oracle assumptions, and available artifacts. Stop a proposed novelty claim if an existing method already supplies it; do not broaden into an autonomous literature survey.

**Output:** A short baseline/applicability table and a declared candidate gap. “Not studied in this repository” is not a gap.

### Days 5–10: artifact qualification

Freeze a roster of at most 24 public repair candidates from IDoFT and FlakyDoctor, deduplicating shared patches and subjects. Use a deterministic order based on project, repair type, and revision rather than observed assessment results. Prefer one Java/JUnit ecosystem. Seek eight usable interventions spanning two projects and, if feasible, two maintenance mechanisms. Four may be development cases; keep the remaining cases sealed for the probe's final comparison. Never split tests affected by one shared repair across these sets.

For each, require exact patch/revision hashes, a reproducible command, separate product and test changes, environment/reset manifest, symptom/condition reproduction, and an independently justified behavioral obligation. Record skipped candidates and reasons. Where a real historical defect is unavailable, mark any challenge as synthetic; do not fill the gap with a model-generated “ground truth.”

**Early stop:** Fewer than four usable interventions by day 10, or no independent behavioral obligations, means no-go for the present artifact strategy. Do not silently extend the sprint.

### Days 11–23: one empirical probe

Compare existing validators with independent four-cell assessment:

| | Reference implementation | Justified defective variant |
|---|---|---|
| Original observer | Nuisance failures and signatures | Original defect sensitivity |
| Repaired observer | Nuisance reduction | Retained or lost sensitivity |

Freeze one primary challenge and condition protocol per intervention before comparing validator outputs. Include relevant polluter/victim order or environmental context; isolated test reruns may remove the very phenomenon under study. Additional exploratory challenges must be marked as such, not substituted after the primary challenge fails to support the hypothesis.

**Baselines:** Existing artifact validator, strong build/rerun/static-check playbook, and an applicable intent-preserving method where executable. If a method cannot be applied, report that limitation rather than claiming to beat it. Developer acceptance is context, not the final label.

**Execution budget:** At most 50 fresh attempts per matrix cell, initially 10 per cell to detect qualification problems; up to eight authentic interventions means at most 1,600 matrix attempts. Use a total sprint cap of 160 allocated vCPU-hours including builds, repeats, controls, and failed reconstructions, and at most 20 researcher working days within 30 calendar days. Record actual runtime. Stop at either cap; the counts are ceilings, not promises of statistical precision. Randomize/interleave cell execution with resets so patch version is not confounded with machine drift.

**Assessment:** Record same-signature failures, other failures, pass, invalid runs, cost, timestamps, and available-at times. Compare nuisance reduction and defect-associated discrimination rather than counting all red outcomes as detections. For a stochastic challenge, quantify uncertainty in the four proportions; unresolved comparisons remain unresolved. A pilot-sized effect such as a 0.20 loss of defect-associated discrimination is a coarse screening threshold, not a universal safety margin. Use a fresh confirmatory batch for any selected apparent loss; do not interpret sequentially inspected ordinary intervals as confirmatory coverage.

Add a small number of declared weakening and behavior-preserving controls to check the evaluator, charging their cost. They are not authentic maintenance observations. Require every claimed lost protection to have an independent obligation and executable witness; unchanged assertion text or a lower mutation score alone is insufficient.

**Primary output:** For each authentic intervention, whether the independent assessment identifies an obligation-supported sensitivity loss that the applicable baseline accepted or missed, with uncertainty and provenance. Also report correctly rejected harmful controls, false alarms on supported benign changes, and added assessment effort. Repeats are measurements within interventions, not extra independent examples. No APFD, LLM explanation score, or population-level prevalence claim.

### Days 24–30: decide, do not expand

**Go to a six-month study only if:**

1. At least eight credible interventions can be qualified within budget across at least two projects, with independent obligations and usable baseline comparisons.
2. At least two authentic interventions on different projects, including at least one sealed case, show a confirmed consequential sensitivity loss missed by applicable baseline validation; at least one is supported by a real defect or independently established behavioral violation, not solely generic mutant kills.
3. The assessment also accepts supported beneficial changes rather than flagging everything; its useful distinctions are not limited to assertion deletion or missing execution.
4. The literature comparison identifies a remaining contribution and the measured cost suggests a viable larger assessment study. Predeclare an initial practicality ceiling of four researcher-hours of assessment preparation per qualified patch after shared harness setup, reporting setup separately. Exceeding it triggers a research-only or no-go decision, not an industrial usefulness claim.

These are **investment gates**, not proof of prevalence, broad generalization, or validator accuracy. A small mechanism study can justify a larger study without proving a product market.

**No-go / reframe:** Existing methods catch all independently established losses; alleged losses disappear under correct obligations; all useful examples are manufactured; qualification or costs fail; or too few resolved cases remain. If no harm is found, say “no demonstrated opportunity in this cohort,” not “repairs are safe.” If results are inconclusive, do not award six months by default. Record the uncertainty and stop at day 30.

**Expected durable outputs when execution is later authorized:** Candidate/exclusion manifest, primary-source baseline table, hashed repair and environment recipes, scoped obligations and challenge provenance, four-cell outcome ledger, case-level comparisons, resource accounting, and a go/no-go memo. No new platform, repair generator, deployment integration, or model training is needed. None of these artifacts is created by the present writing pass.

## 13. Final A–I decision summary

**A. Identities:** M assesses whether maintaining tests preserves defect sensitivity. A chooses the next observation after failure to reach a supported conclusion efficiently. E assesses whether prior evidence remains applicable after a context change.

**B. Comparative matrix:** Section 5 records all ten requested scores and their explanations. M leads on the importance of the first research question; A leads on six-month feasibility and evaluation clarity; E has conditional long-term upside but the weakest current definition and artifact fit. Scores do not determine the decision by arithmetic.

**C. Preferred direction:** Test-maintenance validation, funded first as a bounded qualification and counterexample study.

**D. Strongest reason not to choose it:** Existing intent-preserving repair may already address the important cases, while independent defect-sensitivity ground truth may be too expensive or too weak to improve on it.

**E. Best fallback:** The narrow adaptive investigation experiment. Prefer a credible negative result about fixed playbooks over adding actions or agents to rescue an unproductive premise.

**F. Cheapest kill tests:** M—existing validation catches every independently justified loss in the qualified scope. A—fixed playbooks cover the useful cost/conclusion tradeoff with no demonstrated material benefit from adaptation. E—claimed expiration decisions reduce to enriched dependency invalidation or existing property-aware verification. Small unresolved samples stop investment; they do not prove universal sufficiency.

**G. Recommended sprint:** Thirty days on M only: focused validation literature, at most 24 candidate repairs, qualification of eight interventions, one four-cell empirical probe, and a strict go/no-go decision. No parallel exploration of A or E.

**H. Umbrella:** A coherent theme exists around the validity of scoped software evidence, but combining the directions now would dilute the experiments. Shared provenance is useful; a shared platform is premature.

**I. Personal career choice:** I would choose test-maintenance validation because it asks whether we improve the instruments that software teams rely on. I would also enforce its stop conditions. If it cannot produce independently meaningful evidence beyond existing validation, I would change direction rather than spend two years defending the framing.
