# TCP-CI dataset subjects — fetch-prioritization for a change-relevance test bed

**Summary:** The TCP-CI dataset has **25 open-source Java subjects** (21.5k builds, 3.6k failed builds). We want the *opposite* of `apache/airavata` (S2): a subject with change-induced, non-recurring failures and a large test suite, so there is headroom between a history-only ordering and the optimal ordering. Ranking below is a **fetch-prioritization heuristic** derived from the paper's Table 2 / Table 3; exact recurrence and history-vs-optimal headroom can only be confirmed by fetching the subject and running `pipeline/fault_structure_probe.py` (reads `exe.csv` + `builds.csv`).

**Date:** 2026-08-10

**Primary sources consulted:**
- Paper (arXiv preprint of the TSE 2022 article), Yaraghi, Bagherzadeh, Kahani, Briand, "Scalable and Accurate Test Case Prioritization in Continuous Integration Contexts." Full-text PDF: https://orbilu.uni.lu/bitstream/10993/53817/1/2109.13168.pdf ; abstract: https://arxiv.org/abs/2109.13168 ; DOI 10.1109/TSE.2022.3184842
- Zenodo record 5532640 (dataset): https://zenodo.org/record/5532640 (DOI 10.5281/zenodo.5532640). Single file `TCP-CI-dataset.tar.gz` (~17 GB); description: "a benchmark of 25 open-source subjects with 21.5k builds and 3.6k failed builds."
- Upstream replication package / tool repo: https://github.com/Ahmadreza-SY/TCP-CI (README documents the dataset CSV layout: `exe.csv`, `builds.csv`, `dataset.csv`, `entity_change_history.csv`, `id_map.csv`; subject naming convention `login@repository`, e.g. `apache@airavata`).

All per-subject numbers below are transcribed from **Table 2** ("The statistics of the 25 carefully selected subjects") and **Table 3** ("frequent-failing (FF) test cases … before (B) and after (A) removing the FF test cases") of the paper PDF (pages 9–11 of https://orbilu.uni.lu/bitstream/10993/53817/1/2109.13168.pdf). All subjects are **Java** (selection step 1 restricted to Java projects; source: PDF §4.2).

---

## Table 2 — all 25 subjects (transcribed faithfully)

Columns: SID · Subject (owner/repo) · SLOC · Java SLOC · #Commits · Time period (months) · #Builds · #Failed Builds · Failure Rate (%) · Avg #TC/Build · Avg Test Time (min). Source: PDF Table 2, p.10 (https://orbilu.uni.lu/bitstream/10993/53817/1/2109.13168.pdf).

| SID | Subject | SLOC | Java SLOC | #Commits | Months | #Builds | #Failed | Fail % | Avg TC/Build | Avg Test min |
|-----|---------|------|-----------|----------|--------|---------|---------|--------|--------------|--------------|
| S1  | JMRI/JMRI | 4.56M | 1.05M | 69.3k | 5 | 1,481 | 65 | 4 | 4364 | 25 |
| S2  | **apache/airavata** (known unsuitable) | 1.46M | 731k | 10.0k | 15 | 236 | 83 | 35 | 49 | 6 |
| S3  | SonarSource/sonarqube | 899k | 398k | 31.8k | 18 | 4,286 | 230 | 5 | 1309 | 6 |
| S4  | apache/sling | 695k | 388k | 47.4k | 7 | 1,403 | 343 | 24 | 189 | 6 |
| S5  | camunda/camunda-bpm-platform | 653k | 395k | 20.6k | 34 | 822 | 125 | 15 | 569 | 23 |
| S6  | facebook/buck | 586k | 384k | 26.3k | 10 | 846 | 130 | 15 | 663 | 26 |
| S7  | apache/shardingsphere | 422k | 165k | 29.6k | 7 | 1,049 | 123 | 11 | 789 | 17 |
| S8  | b2ihealthcare/snow-owl | 373k | 212k | 13.4k | 2 | 277 | 21 | 7 | 46 | 10 |
| S9  | Angel-ML/angel | 336k | 204k | 3.0k | 23 | 308 | 124 | 40 | 33 | 20 |
| S10 | apache/logging-log4j2 | 313k | 166k | 12.7k | 13 | 441 | 122 | 27 | 544 | 8 |
| S11 | eclipse/jetty.project | 282k | 199k | 25.0k | 2 | 192 | 89 | 46 | 137 | 6 |
| S12 | optimatika/ojAlgo | 246k | 84k | 1.6k | 22 | 254 | 72 | 28 | 136 | 9 |
| S13 | yamcs/Yamcs | 229k | 123k | 5.6k | 24 | 504 | 61 | 12 | 114 | 6 |
| S14 | eclipse/steady | 221k | 98k | 2.0k | 13 | 675 | 51 | 7 | 81 | 7 |
| S15 | Graylog2/graylog2-server | 182k | 85k | 22.3k | 53 | 3,668 | 124 | 3 | 110 | 20 |
| S16 | CompEvol/beast2 | 159k | 83k | 3.0k | 85 | 415 | 115 | 27 | 65 | 6 |
| S17 | EMResearch/EvoMaster | 158k | 25k | 4.1k | 7 | 583 | 109 | 18 | 100 | 12 |
| S18 | apache/rocketmq | 135k | 100k | 2.0k | 16 | 536 | 56 | 10 | 182 | 17 |
| S19 | zolyfarkas/spf4j | 125k | 79k | 32.6k | 37 | 587 | 180 | 30 | 116 | 7 |
| S20 | spring-cloud/spring-cloud-dataflow | 104k | 54k | 3.5k | 9 | 408 | 19 | 4 | 115 | 17 |
| S21 | cantaloupe-project/cantaloupe | 98k | 77k | 4.5k | 29 | 450 | 65 | 14 | 148 | 11 |
| S22 | thinkaurelius/titan | 85k | 40k | 5.1k | 25 | 384 | 41 | 10 | 45 | 48 |
| S23 | apache/curator | 84k | 58k | 3.1k | 21 | 517 | 65 | 12 | 115 | 67 |
| S24 | jcabi/jcabi-github | 61k | 32k | 2.8k | 29 | 788 | 6 | < 0.01 | 176 | 14 |
| S25 | eclipse/paho.mqtt.java | 61k | 34k | 1.0k | 16 | 378 | 77 | 20 | 37 | 15 |

Notes from surrounding text (PDF p.10–11): SLOC ranges 61k–4.56M (median 229k). #Failed builds ranges 6–343 (median 83). Avg TC/build ranges 33–4368 (median 117). Avg regression test time 6–67 min (median 12). "Failed builds are … builds with at least one failed test case."

## Table 3 — frequent-failing (FF) test-case removal (chronic-block indicator)

The paper removed **frequent-failing (FF)** test cases — "also referred to as known breakages … they tend to fail most of the time for the same reason, independently of changes" — using a three-sigma failure-frequency outlier rule. Columns show statistics **B**efore vs **A**fter removing FF test cases. Only subjects that had ≥1 FF test case appear; four subjects (shown bold) drop below the 50-failed-build selection floor after removal. Source: PDF Table 3, p.9 (https://orbilu.uni.lu/bitstream/10993/53817/1/2109.13168.pdf).

| SID | Subject | #FF TCs | #Failed B→A | Fail% B→A | Avg TC/Build B→A |
|-----|---------|---------|-------------|-----------|------------------|
| S5  | camunda-bpm-platform | 8 | 174 → 125 | 21 → 15 | 575 → 569 |
| S3  | sonarqube | 7 | 299 → 230 | 6 → 5 | 1315 → 1309 |
| S7  | shardingsphere | 6 | 151 → 123 | 14 → 11 | 795 → 789 |
| S1  | JMRI | 5 | 94 → 65 | 6 → 4 | 4368 → 4364 |
| S17 | EvoMaster | 2 | 143 → 109 | 24 → 18 | 101 → 100 |
| S21 | cantaloupe | 2 | 70 → 65 | 15 → 14 | 149 → 148 |
| **S22** | **titan** | 2 | 60 → **41** | 15 → 10 | 45 → 45 |
| **S24** | **jcabi-github** | 2 | 76 → **6** | 9 → <0.01 | 174 → 176 |
| S4  | sling | 1 | 697 → 343 | 49 → 24 | 189 → 189 |
| **S8**  | **snow-owl** | 1 | 58 → **21** | 20 → 7 | 47 → 46 |
| S10 | logging-log4j2 | 1 | 231 → 122 | 52 → 27 | 545 → 544 |
| S11 | jetty.project | 1 | 150 → 89 | 78 → 46 | 138 → 137 |
| S13 | Yamcs | 1 | 72 → 61 | 14 → 12 | 115 → 114 |
| S19 | spf4j | 1 | 277 → 180 | 47 → 30 | 117 → 116 |
| **S20** | **spring-cloud-dataflow** | 1 | 88 → **19** | 21 → 4 | 115 → 115 |
| S23 | curator | 1 | 103 → 65 | 19 → 12 | 115 → 115 |

Subjects **not in Table 3** (no FF test cases removed by the three-sigma rule): S2 airavata, S6 buck, S9 angel, S12 ojAlgo, S14 steady, S15 graylog2-server, S16 beast2, S18 rocketmq, S25 paho.mqtt.java.

### Stated failure characteristics (paper §4.2)
- The FF / "known breakages" investigation sampled **S24, S20, S8, S7** and found test cases "that failed in more than 65% of the failed builds due to the same reason" — external exceptions unrelated to the SUT (HTTP/auth errors, invalid args), or Java runtime errors (`ClassNotFoundException`, `FileNotFoundException`). These are chronic, change-independent — the airavata failure mode we want to avoid.
- The Table 2/Table 3 numbers used in the rest of the paper are **after** FF removal. The paper does not report per-subject recurrence or history-vs-optimal APFD gaps — those are exactly what our probe measures and are **not reported in primary sources**.

---

## Ranking heuristic (fetch-prioritization, NOT a final verdict)

We want the opposite of airavata (S2): **low failure recurrence + headroom between history-only and optimal ordering.** From primary data we can only see *proxies* for those properties, so we score each non-airavata subject on:

1. **Test-suite size (Avg TC/Build)** — larger suite ⇒ more positions to order ⇒ more potential headroom. Tiny suites (≈33–49) give a change signal almost nowhere to move a failure. *Higher is better.*
2. **Failed-build density (#Failed, post-FF where known)** — more failed builds ⇒ more scorable cycles and statistical power. Need ≥50; more is better.
3. **Failure rate** — a *moderate/low* rate (failures sporadic, spread across time) is more consistent with change-induced, non-recurring failures; a very high rate (≥~30–46%) co-occurs with chronic/known-breakage regimes (angel 40%, jetty 46%, spf4j 30%). *Lower-but-not-trivial is better; extreme-high is a red flag.*
4. **Chronic-block signal (Table 3)** — subjects whose failed-build count **collapses** after removing one FF test (sling 697→343, log4j2 231→122, jetty 150→89, spf4j 277→180) had a single test dominating failures — an airavata-like symptom. Subjects where FF removal barely moved the count (sonarqube 299→230, JMRI 94→65, cantaloupe 70→65) are cleaner. *Small B→A drop is better.*
5. **Activity/scale** — more commits, longer time period, larger SLOC ⇒ more diverse changes touching more code ⇒ more genuine change-relevance to exploit.

**Important caveat (why this is only a heuristic):** airavata (S2) itself has **no FF test cases removed** in Table 3, yet our own probe found it has a chronic ~21-test co-failing block with ~78% recurrence. The paper's three-sigma FF rule is a *per-test-case* failure-frequency outlier test; a **co-failing block** where each member fails in a moderate fraction survives it. So "not in Table 3" does **not** guarantee non-recurring failures. Recurrence and headroom must be confirmed empirically per subject with `pipeline/fault_structure_probe.py --data <slice>/TCP-CI-dataset/datasets/<owner>@<repo>` (reads `exe.csv` + `builds.csv`; verdict GO / MARGINAL / NO-GO).

### Deprioritized / avoid (do not fetch as a first test bed)
- **Too sparse after FF removal:** S24 jcabi-github (6 failed), S20 spring-cloud-dataflow (19), S8 snow-owl (21), S22 titan (41) — below or near the 50-failed floor; the paper flags these four (bold) as FF-dominated.
- **Tiny test suites (little headroom):** S9 angel (33), S25 paho (37), S8 snow-owl (46), S22 titan (45), S2 airavata (49), S16 beast2 (65).
- **Extreme failure rate ⇒ likely chronic regime:** S11 jetty.project (46%), S9 angel (40%), S2 airavata (35%), S19 spf4j (30% and collapses 277→180 after 1 FF), S10 log4j2 (52%→27% via 1 FF).

---

## RECOMMENDED FETCH ORDER (top 3)

### 1. `SonarSource/sonarqube` (S3) — strongest opposite-of-airavata
- **Large suite (1309 avg TC/build)** ⇒ lots of ordering headroom; **230 failed builds** (excellent density, second only to sling); **5% failure rate** (failures sporadic across 4,286 builds ⇒ consistent with change-induced, not chronic). 31.8k commits, 18-month window ⇒ highly active, diverse changes.
- **Clean chronic signal:** Table 3 shows only 7 FF test cases removed, and failed builds barely moved (299→230). Failures are *not* dominated by one block — the exact opposite of airavata's 21-test cluster.
- Best combination of headroom (big suite) × density (many failed builds) × low sporadic failure rate.

### 2. `JMRI/JMRI` (S1) — maximum headroom
- **Largest test suite in the dataset by far (4364 avg TC/build)** ⇒ a history-only ordering has enormous room to be beaten by the optimal ordering; a change-relevance signal has the most positions to exploit. **4% failure rate** (very sporadic). Only 5 FF test cases removed (94→65), so failures aren't chronic-block-driven.
- Caveat: **65 failed builds** is modest (just above the 50 floor) ⇒ fewer scorable cycles, so effect estimates will be noisier. Fetch second because the suite-size upside is unique, but confirm density is workable with the probe.

### 3. `facebook/buck` (S6) — large suite + good density, second-tier confirmation
- **663 avg TC/build** (large suite ⇒ headroom), **130 failed builds** (good density), 26.3k commits. **Not in Table 3** (no FF removed) — treat with the airavata caveat, but combined with a large suite and 15% (moderate) failure rate it is a solid diverse test bed.
- **Alternative to consider in this slot:** `Graylog2/graylog2-server` (S15) — **3% failure rate (lowest meaningful in the dataset)**, 124 failed builds, 3,668 builds over a 53-month active history — the most "sporadic, spread-out" failure profile of any subject; its only weakness is a modest suite (110 avg TC), which caps headroom. Prefer buck if suite-size headroom matters most; prefer graylog2-server if a low, spread-out failure rate is the priority.

**Next action:** fetch S3 `SonarSource/sonarqube` first, then run `python pipeline/fault_structure_probe.py --data <slice>/TCP-CI-dataset/datasets/SonarSource@sonarqube` and read the recurrence + headroom numbers before committing to the full Step 1–3 pipeline. A GO/MARGINAL verdict there confirms (or refutes) this heuristic ranking empirically.
