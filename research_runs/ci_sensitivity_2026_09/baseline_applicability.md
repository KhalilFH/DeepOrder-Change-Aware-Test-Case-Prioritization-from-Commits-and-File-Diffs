# Task 3 — baseline and artifact-entry reconnaissance

## Scope and evidence labels

This record covers only Section 13 Task 3 of `docs/research/NEXT_RESEARCH_ACTION_PLAN.md`. No subject was restored or executed, no qualification attempt was made, and no experiment harness or pipeline code was created or changed.

- **Observed**: directly inspected in a cited paper, archive, repository, issue record, or commit.
- **Source claim**: an author's or artifact maintainer's characterization that was not independently reproduced here.
- **Inference**: applicability judgment for Q0/RQ1/RQ2.
- **Missing**: information not established by this reconnaissance.

A fail/pass label, reproducer outcome, flaky-test label, or mutant outcome is not treated as a causal defective/acceptable pair or as product-defect ground truth.

## Executive applicability decision

| Source | What it can support | What it cannot currently support | Task 3 disposition |
|---|---|---|---|
| Zeng et al. YourBase assessment and Zenodo appendix | Methodology reference for comparing an accelerated policy with an unaccelerated reference; warning that nondeterminism can contaminate policy-gap measurements; archived per-mutant outcomes, dependency graphs, selected release commits, test reports, and qualitative labels | Q0 cohort acquisition; real intermittent product-defect episodes; acceptable counterparts; executable YourBase or a complete replication procedure | Retain as the closest assessment-method reference, not as a required executable baseline or cohort source |
| JaConTeBe paper, archived SIR description, third-party mirror, and authoritative upstream projects | Real historical Java concurrency-defect leads, issue-linked behavioral obligations, defect-focused reproducers, old binaries/source archives, and, for several Apache cases, recoverable upstream fix history | Proof that a reproducer is intermittent; proof that a packaged version pair is causal; a ready-made acceptable counterpart; provenance-equivalent substitution of a third-party mirror for the unavailable official SIR distribution | Use upstream Apache issue/history as the first Q0 metadata entry; use JaConTeBe as reproducer and oracle documentation only |

## 1. YourBase mutation/CI assessment

### Source/artifact identity

The paper is Zeng et al., “A Mutation-Guided Assessment of Acceleration Approaches for Continuous Integration: An Empirical Study of YourBase,” MSR 2024.[1] Its published appendix is Zenodo record `10076515`, DOI `10.5281/zenodo.10076515`; the record describes one CC-BY-4.0 archive, `MutationAnonymous.zip`, published 2023-11-06.[2][3]

### Actual method and measurement

**Observed.** The study selected ten GitHub-hosted Python/pytest projects and one release-tagged change set per project. For each project, it first ran the preceding commit so YourBase could construct its dependency graph, then checked out independent accelerated and unaccelerated copies of the release change set. Mutmut generated the same mutation strategies in both settings, and each mutant was independently committed to trigger accelerated selection. The primary comparison was whether a mutant killed by the unaccelerated suite survived under acceleration; these were called “gap mutants.” The paper measured gap rate, mapped gap mutants into YourBase's dependency representation, and manually classified a saturation sample of 200 gap mutants.[1]

**Observed.** This is a mutation-based differential assessment of program-analysis-based test skipping, not an assessment of retries. Its evidence unit is an artificial mutant outcome, not a historical product-defect episode. The paper reports 2,237 gap mutants across the ten projects and a 200-mutant qualitative inspection.[1]

### Nondeterminism/intermittency treatment

**Observed.** Nondeterminism was explicitly considered. The manual priming procedure re-applied a suspect mutation and reran the unaccelerated build to reproduce the failure and reduce flaky-test influence. In the 200 inspected gap mutants, the authors classified 45 (22.5%) as nondeterministic build behavior: 21 flaky-test cases and 24 inconsistent Mutmut labels involving suspicious/timeout/survival outcomes. Identified flaky tests were removed from their trustworthiness analysis, and the paper states that repetition can reduce but cannot guarantee elimination of this noise.[1]

**Inference.** This treatment is directly relevant as a contamination warning for our paired, repeated, signature-aware assessment. It does not establish intermittent product defects: the underlying faults are mutants, and the nondeterminism categories concern tests/build labeling rather than independently validated product-defect witnesses.

### What is actually available

**Observed.** The Zenodo archive was downloadable during this reconnaissance. It contains 143 ZIP entries (including macOS metadata/duplicate resource entries) and substantive material for all ten projects: accelerated and unaccelerated mutation reports, gap-mutant lists, dependency-graph JSON files, pytest HTML reports, `Mapping.csv`, `NoMapping.csv`, `Patterns.csv`, `CodeDistribution.csv`, `MutationOperators.csv`, and `SelectedCommits.csv`. `SelectedCommits.csv` gives abbreviated preceding/release commits and release tags for the ten projects.[2][3]

**Observed.** The archive README describes data products only. Inspection found no YourBase implementation, installation package, experiment driver, environment/container definition, dependency-lock file, automated analysis code, or end-to-end reproduction script. The archive therefore preserves useful result-level data and release identifiers but not an executable replication package.[2]

**Missing.** This reconnaissance did not establish public availability of the proprietary YourBase version/plugin used by the study, its exact configuration, immutable dependency/environment versions, or a currently reproducible accelerated run. It also did not establish that the archived reports retain attempt-level timing, exit status, reset state, or policy-visible prefixes in the form required by our protocol.

### Methodological relevance to our RQs

- **RQ1 relevance — moderate, methodology only.** YourBase demonstrates a systematic policy-versus-reference differential assessment and shows that policy gaps can have both deterministic and nondeterministic causes. It does not estimate P1-versus-P3 retry sensitivity or independently verified nuisance reduction.
- **RQ2 relevance — strong prior-art boundary, not an executable required baseline.** It is closer to a mutation-guided fault-injection assessment than to A0/A1/A2. A0 is one paired observation; A1 is repeated paired final-outcome analysis with uncertainty and cost; A2 additionally uses signatures, obligations, earlier attempts, and invalid handling on the same real-defect oracle. YourBase instead uses many synthetic mutants, one accelerated/unaccelerated comparison procedure, dependency mapping, rerun-based priming, and qualitative root-cause classification. It neither replaces A2 nor supplies a new retry assessor.
- **Q0 relevance — low.** Arbitrary mutants cannot enter the real intermittent-defect cohort, and the appendix has no authentic defective/acceptable product-version pairs.

### Provenance quality

**High for the paper-to-archive link and archived result identity:** paper, DOI, archive metadata, release identifiers, and result files agree.[1][2][3]

**Low for executable reproducibility:** the operative accelerator and complete procedure/environment are not in the inspected archive. An unavailable YourBase installation must be reported as “not compared,” consistent with the approved plan, rather than treated as a failed baseline.

### Risks/disqualifiers

1. Mutation faults are synthetic and cannot satisfy Q0's real-product-defect requirement.
2. Gap mutants confound acceleration effects with flaky tests and mutation-tool labeling unless separately adjudicated; the paper itself found this contamination.[1]
3. Archived aggregate/per-mutant outputs cannot answer our counterfactual retry question without new executions.
4. Making a proprietary/absent YourBase installation a dependency would violate the approved bounded source strategy.

## 2. JaConTeBe

### Source/artifact identity and benchmark provenance

The primary paper describes JaConTeBe as 47 confirmed Java concurrency bugs from eight open-source project directories, with a test case and script for each bug, submitted to SIR.[4] The eight directories are DBCP (4), Derby (5), Groovy (6), JDK 6 (14), JDK 7 (6), Log4j (5), Lucene (2), and Commons Pool (5): 27 non-JDK and 20 JDK cases.[4][7]

**Source claim.** The paper says the authors searched project issue trackers, removed duplicates, required sufficient reproduction information/resources, excluded low-relevance cases, and created a reproducer for each retained report. It calls the 47 bugs real-world and reports that they span races/atomicity violations, deadlocks, and Java-memory-model defects.[4]

**Observed.** Both the archived biography and the newly located current SIR biography confirm a collection of 47 Java test classes, call each supplied test object a concurrency-error “kernel,” and say shell scripts execute those kernels on the standard JVM.[6][18] This wording matters: the benchmark's test object is a distilled reproducer around a third-party or JDK library, not necessarily an unchanged historical project test or full CI job.

### Current availability and provenance quality

**Observed.** The plan's old SIR URL redirects to `sir-public.github.io/SIRportal/bios/JaConTeBe.php`, which returns HTTP 404. A separate current official SIR site exists at `https://sir-public.github.io/SIR/`; it states that SIR is no longer actively maintained and warns that some external links may be dead.[5][17]

**Observed.** The current JaConTeBe biography is `https://sir-public.github.io/SIR/JaConTeBe.html`. The current download index lists JaConTeBe as SIR version 1.0, updated 2015-01-30, with an all-platform object of 92,797,184 bytes hosted through Google Drive.[18][19] Both the Google Drive view URL and direct-download endpoint returned HTTP 404 during this check, so the official object is listed but not currently retrievable through that link. The public `SIR-public/SIR` repository contains the website and JaConTeBe biography, not the 92.8 MB object archive.[19][20]

**Observed.** A public third-party repository, `ChopinLi-cp/JaConTeBe_TSVD`, contains an apparent copy of the benchmark tree: README/license, descriptions, Java source tests, scripts, compiled classes, old project JARs/source archives, helper code, and SVN administrative metadata.[7] It was created in 2021 as a non-fork GitHub repository and does not document a chain of custody from SIR or the JaConTeBe authors. Treat it as an accessibility lead, not an authoritative replacement for SIR.

**Observed.** The mirror README describes JDK 6/7-era execution and says some project JARs are modified at class load time to control interleavings. The per-project helper script invokes a user-local Maven Java agent path for `asm-simple-project`, but no path matching that agent/source appears in the inspected repository tree. The packaged procedure is therefore not self-contained as observed.[7]

**Provenance assessment.** The paper and archived SIR page provide strong provenance for benchmark identity and issue selection.[4][6]
The current SIR biography and download index add official packaging metadata.[18][19] The newly located site corrects the earlier conclusion that no current official page exists, but it does not make the official object downloadable at present. The third-party mirror provides high-information file-level evidence but weak custody/release provenance. Authoritative upstream project issue records and imported Git/SVN history remain the preferred source for defect/fix identity.

### Candidate inventory actually present

The mirror's overview and project indexes contain these non-JDK issue leads:[7]

| Project | Count | Issue IDs present | Packaged buggy version(s) |
|---|---:|---|---|
| Commons DBCP | 4 | DBCP-65, DBCP-270, DBCP-271, DBCP-369 | 1.2 |
| Derby | 5 | DERBY-764, DERBY-4129, DERBY-5447, DERBY-5560, DERBY-5561 | 10.5.1.1 |
| Groovy | 6 | GROOVY-3495, GROOVY-4292, GROOVY-4736, GROOVY-5198, GROOVY-6068, GROOVY-6456 | 1.7.9 |
| Log4j | 5 | LOG4J-38137, LOG4J-41214, LOG4J-44032, LOG4J-50463, LOG4J-54325 | 1.2.13–1.2.15 |
| Lucene | 2 | LUCENE-1544, LUCENE-2783 | 2.4.0 and 2.9.3 |
| Commons Pool | 5 | POOL-46, POOL-120, POOL-146, POOL-149, POOL-162 | 1.2, 1.4 snapshot, and 1.5 |

**Observed metadata defect.** In the mirror overview, the GROOVY-6068 row links to GROOVY-3495. That row requires upstream correction before use.[7]

**Boundary.** The mirror overview's “succeeded/failed” values are tool-evaluation results (including JPF outcomes), not defective/acceptable version labels. They provide no causal pair.

### Real product defects versus reproducers

**Real historical defect evidence.** The inspected Apache issue records identify POOL-146 and POOL-162 as product bugs with concrete behavioral descriptions and fixed/closed issue metadata.[8][9]
DBCP-65 and DBCP-270 have the same form of upstream product-bug evidence.[10][11]

**Reproducer status.** The JaConTeBe test code is benchmark-authored or adapted test code. It invokes real buggy library binaries but often uses controlled setup:

- POOL-146 uses fixed pool limits, staged thread starts, and a one-second sleep to arrange the blocking condition.[7]
- POOL-162 explicitly interrupts a waiting thread after sleeps and then tests leaked capacity/deadlock behavior; the interrupt is part of the defect-triggering obligation but the schedule is intentionally orchestrated.[7]
- DBCP-65 and DBCP-270 explicitly use Mockito so execution follows the path leading to deadlock.[7]
- LOG4J-38137 starts ten appending threads and repeatedly fills an `AsyncAppender`; the inspected test has no explicit source instrumentation, but its raw intermittency under a frozen environment was not measured here.[7]

These are not synthetic product faults: the fault-bearing production binaries correspond to historical releases. However, the benchmark tests are controlled/forced reproducers, not evidence that the original defect manifests intermittently under ordinary CI conditions.

### What the reproducers say about intermittency

**Source claim.** The paper reports that 36 of 47 test cases reproduced the bug deterministically on every run, including six using mocking and three using instrumentation. Eleven needed several runs; one of those used mocking. Only GROOVY-5198 reportedly needed many more runs. The paper states that instrumentation/mocking cannot strictly guarantee determinism but were used to make reproduction effectively deterministic.[4]

**Inference.** JaConTeBe's default scripts are generally defect-presence controls. They must not be enrolled as primary intermittent episodes merely because the underlying concurrency defect depends on scheduling. A Task 4 card may preserve a less-forced/native protocol as an open possibility, but intermittency remains missing until supported by source documentation and later Q0 qualification under a frozen non-forcing protocol.

### Issue/fix/revision metadata and counterpart recoverability

| Lead | Directly supported metadata | Counterpart assessment before restoration |
|---|---|---|
| POOL-146 | JIRA: major bug; affects Pool 1.5/1.5.1; fixed in 1.5.2. Upstream imported history exposes fix commit `1b80d343ca28618318e7c13760913ad91dca78c5` with parent `51ae45b7462481c08fb53feaffc4d18ad4772074`; an upstream test was added separately before the fix.[8][12] | **Promising historical pair**, but Task 4 must trace the test-add/update/fix sequence and ensure one identical target can be used on both sides. JaConTeBe's sleep-orchestrated kernel is not intermittency evidence. |
| POOL-162 | JIRA: major bug affecting 1.5–1.5.4 and fixed in 1.5.5; issue discussion names SVN revision `924479`. Imported Git commit `674a6ba9877d2de7224306c83e7871e1eddeab93` has parent `280c60ac3e918eb7fe8fb542847913bb5317cbc6` and adds a test and one-line production fix.[9][13] | **Best pair-provenance lead.** A controlled historical test backport may be possible under the protocol, but the supplied interrupt-driven reproducer is likely a deterministic control rather than a primary intermittent case. |
| DBCP-65 | JIRA: major deadlock report, nominally fixed in 1.2.2 by removing synchronization in imported Git commit `4ae50045738561c1c48c31bbad2ece90eaebffb8`. Later issue comments report the deadlock persisted in 1.2.2 under rare use and high load.[10][14] | **Strong intermittency lead but ambiguous focal fix.** The later contradiction means the nominal fix cannot yet define `V_ok`; Task 4 must identify the final obligation-satisfying change or mark counterpart unresolved. |
| DBCP-270 | JIRA: critical deadlock in 1.2.2, fixed for 1.3, with an attached patch. Imported Git commit `4bf62b339ef3a30dac10160da76905222063485b` has parent `c8034fa0290b3690e31e933402ee049af9aa39d0` and narrows `AbandonedTrace` synchronization.[11][15] | **Promising historical pair and clear obligation**, but the JaConTeBe test uses mocks to drive the deadlock path; unforced intermittency evidence remains missing. |
| LOG4J-38137 | JaConTeBe identifies Log4j 1.2.13 and a wait/notify deadlock; an Apache Log4j 1 source repository remains public but archived/EOL.[4][7][16] | **Lower-priority lead.** The upstream Bugzilla record currently requires authentication, and this reconnaissance did not establish an exact fix commit or acceptable counterpart. Do not infer one from a later release alone. |

No counterpart above is qualified. Recoverability means only that issue/release/history evidence appears sufficient to inspect a candidate pair in Task 4; it does not prove the fix is isolated, the test is unchanged across versions, or `V_ok` satisfies the focal obligation.

### Methodological relevance to our RQs

- **Q0 — high as a lead index, conditional as an artifact.** It supplies real historical defect reports, focused witnesses, and old binaries/source. It does not itself supply authenticated defective/acceptable pairs or measured intermittency.
- **RQ1 — potential subject source only after Q0.** A forced deterministic kernel can validate an oracle but cannot estimate retry sensitivity for intermittent defects. A native or minimally controlled protocol would have to retain the focal obligation while producing both passes and focal failures naturally.
- **RQ2 — limited.** JaConTeBe is a defect-reproduction benchmark, not a CI policy assessor. Its value is external oracle support, not an A0/A1/A2 replacement.

### Missing information

1. A retrievable current author/SIR-hosted official distribution or release checksum for JaConTeBe; the current SIR index's Google Drive object link returns 404.[19]
2. A documented custody relationship between the third-party mirror and the original SIR artifact.
3. Exact per-case classification of the paper's 36 deterministic versus 11 several-run tests; the paper gives aggregate counts but not a complete inspected mapping in the sources reviewed here.
4. For each lead, an identical target/harness validated on both the defective and acceptable revisions.
5. For POOL-146/162 and DBCP-270, evidence of an unforced intermittent manifestation suitable for the primary cohort.
6. For DBCP-65, an unambiguous final fix and acceptable counterpart for the same obligation.
7. For LOG4J-38137, inspectable upstream issue/fix metadata without authenticated Bugzilla access.
8. A self-contained modern build/environment recipe; the mirror is JDK 6/7-era and references an external user-local Java agent.

### Risks/disqualifiers

- Forced scheduling, sleeps, interruption, instrumentation, or mocks can turn a concurrency defect into a deterministic benchmark control and erase the policy-sensitivity phenomenon of interest.
- Benchmark-authored kernels are not necessarily historical CI tests; any identical backport must be disclosed as a reconstructed test of a historical defect.
- Old JARs plus a passing later JAR do not prove an isolated causal defect pair.
- The mirror's provenance gap, missing agent dependency, ancient JDK assumptions, and metadata typo create restoration and traceability risk.
- Deadlock monitors/timeouts establish a hang only when tied to the documented obligation; an administrative timeout alone is insufficient.
- JaConTeBe's JPF “success/failure” fields must not be interpreted as product-version outcomes.

## Explicit Task 4 recommendation

**First artifact source to inspect:** authoritative Apache Commons Pool upstream issue/history, beginning with **POOL-162**, and using JaConTeBe only for reproducer/oracle documentation. POOL-162 has the clearest currently observed issue → affected/fix versions → exact fix commit/parent → added regression-test chain.[9][13]

Task 4 should first inspect the full `674a6ba9877d2de7224306c83e7871e1eddeab93` diff and its parent, determine whether the production fix is isolated, identify the exact upstream test and whether it can be held identical on both versions, and classify the supplied interrupt-driven reproducer as forced/deterministic unless an authoritative native non-forcing procedure is found.[9][13]
If no defensible intermittent protocol is documented, retain POOL-162 only as a stable oracle/control lead and move next to **DBCP-65** for its source-reported probabilistic manifestation, while treating its acceptable counterpart as unresolved until the final focal fix is traced.[10][14]

Strongest subsequent candidate leads are **POOL-146** (clear issue and fix history) and **DBCP-270** (critical deadlock, patch, exact fix commit/parent).[8][11][12]
LOG4J-38137 should not lead Task 4 because its issue/fix chain is presently less accessible and no exact acceptable counterpart was established.[16]

## Task 3 verdict

**TASK 3 VERDICT: PASS WITH ISSUES**

The best artifact entry is established. A current official SIR biography and download listing now exist, but the listed Google Drive object returns 404; the accessible mirror still has weak custody/self-containment, and none of the inspected reproducers establishes the intermittency required for a primary Q0 episode.[18][19]

## Sources

[1] https://rebels.cs.uwaterloo.ca/papers/msr2024_zeng.pdf — Zeng et al. MSR 2024 YourBase assessment
[2] https://doi.org/10.5281/zenodo.10076515 — YourBase study online appendix (Zenodo)
[3] https://zenodo.org/api/records/10076515 — Zenodo record metadata API
[4] https://mir.cs.illinois.edu/marinov/publications/LinETAL15JaConTeBe.pdf — Lin et al. JaConTeBe paper
[5] https://sir.csc.ncsu.edu/portal/bios/JaConTeBe.php — SIR JaConTeBe catalog page
[6] https://web.archive.org/web/20221008001508id_/https://sir.csc.ncsu.edu/portal/bios/JaConTeBe.php — Archived SIR JaConTeBe object biography
[7] https://github.com/ChopinLi-cp/JaConTeBe_TSVD — Third-party JaConTeBe_TSVD mirror
[8] https://issues.apache.org/jira/si/jira.issueviews:issue-xml/POOL-146/POOL-146.xml — ASF JIRA POOL-146 XML
[9] https://issues.apache.org/jira/si/jira.issueviews:issue-xml/POOL-162/POOL-162.xml — ASF JIRA POOL-162 XML
[10] https://issues.apache.org/jira/si/jira.issueviews:issue-xml/DBCP-65/DBCP-65.xml — ASF JIRA DBCP-65 XML
[11] https://issues.apache.org/jira/si/jira.issueviews:issue-xml/DBCP-270/DBCP-270.xml — ASF JIRA DBCP-270 XML
[12] https://github.com/apache/commons-pool/commit/1b80d343ca28618318e7c13760913ad91dca78c5 — Commons Pool POOL-146 fix commit
[13] https://github.com/apache/commons-pool/commit/674a6ba9877d2de7224306c83e7871e1eddeab93 — Commons Pool POOL-162 test and fix commit
[14] https://github.com/apache/commons-dbcp/commit/4ae50045738561c1c48c31bbad2ece90eaebffb8 — Commons DBCP DBCP-65 fix commit
[15] https://github.com/apache/commons-dbcp/commit/4bf62b339ef3a30dac10160da76905222063485b — Commons DBCP DBCP-270 fix commit
[16] https://github.com/apache/logging-log4j1 — Apache Log4j 1 source repository
[17] https://sir-public.github.io/SIR — Current SIR site
[18] https://sir-public.github.io/SIR/JaConTeBe.html — Current SIR JaConTeBe object biography
[19] https://sir-public.github.io/SIR/showfiles.html — Current SIR object download index
[20] https://github.com/SIR-public/SIR — Current SIR site repository
