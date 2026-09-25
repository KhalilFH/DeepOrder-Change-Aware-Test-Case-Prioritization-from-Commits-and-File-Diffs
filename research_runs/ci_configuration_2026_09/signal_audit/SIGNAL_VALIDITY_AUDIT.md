# C1 post-collection signal-validity audit: etcd5509

## Material passport

- **Label: EXPLORATORY, POST HOC.** Every analysis here was chosen after the C1 results were seen. None of it is confirmatory, and none of it replaces the frozen primary analysis (`analysis/`) or its simultaneous intervals.
- Date: 2026-09-25. Study: `c1_ci_configuration_visibility_v1`.
- Authority: the researcher asked for an audit of whether the etcd5509 signal justifies a fresh confirmation experiment. The audit was run by one agent, with no delegation.
- **Not done:** no containers, builds, subject executions or new observations. No edits to frozen code, protocols, annotations, raw ledgers, the resource/event ledgers or existing analysis outputs. No label was changed and no oracle was strengthened. Nothing was committed or pushed.
- All new files are in `research_runs/ci_configuration_2026_09/signal_audit/`.
- Each section separates **Observed** results (computed from preserved records) from **Interpretation** (inference) where both appear.

## Question and answer

**Question.** Does the etcd5509 pilot signal justify a fresh confirmation experiment? Or could it reflect attempt placement, execution order, temporal variation, or limitations of the behavioral oracle?

**Answer: STOP.** The signal is what ordinary repeated testing produces with no profile effect.

- **The oracle is not the weak point.** Every positive dump has the structure of the historical leaked-read-lock deadlock. Nothing suggests generic CPU delay.
- **The differences between profiles are small, and chance explains them.**
  - All attempts: 24/30 focal failures under R and 26/30 under L. R's rate equals the historical unrestricted rate.
  - The P3 counts match the arithmetic of retries (p³).
  - The whole P1 gap comes from three R cells. Each passed its first attempt, then failed both research-only attempts.
- **Assume no profile effect at all.** The frozen C3 gate would still fire for etcd5509 about 41% of the time, and for at least one of the six subjects about 72% of the time.
- **Confirmation would be expensive.** A plausible small effect would need several hundred matched blocks to confirm. That is a multiple of C1's entire measured budget, spent on one subject and one host, in a direction that does not address the question C1 was built to ask.

## 1. Integrity verification (before analysis)

Script `s00_verify_integrity.py` is stdlib-only and imports nothing from `c1_harness` or `e1_harness`. Output: `out/integrity.json`. Status: **PASS**.

| Check | Result |
|---|---|
| Design freeze `DESIGN_FREEZE.sha256` (LF-normalized) | 8/8 entries match the working tree. 8/8 also match the **committed bytes at HEAD** `721d885`. File digest `087b338d…bff9fc`. |
| Executable launch freeze `FREEZE.sha256` (frozen_utc 2026-09-25T12:15:02Z) | 71/71 entries match. File digest `45c524f1…70d`. |
| Pre-analysis seal (`analysis_audit/pre_analysis_seal.json`, sealed 16:04:25Z) | 12/12 raw measured ledgers match the sealed raw-byte SHA-256. The seal's recorded freeze digests equal both digests recomputed now. |
| `analysis/summary.json` input digests | 13/13 (12 ledgers and `annotations.jsonl`) match the current files. |
| Hash chains, recomputed independently | 12 measured ledgers (60 rows each), `events.jsonl` (101 rows) and `resource_ledger.jsonl` (1061 rows) are all intact. |
| Annotation linkage | 720 annotations and 720 unique IDs. All 720 `record_sha256` links resolve to the raw record. |

## 2. Task 1: independent count verification

Script `s01_counts_and_blocks.py` re-derives the policy prefixes from exit statuses only (protocol §4). Output: `out/s01_counts.json`.

- **Observed:** 540 PASS and 180 FOCAL_DEFECT_WITNESS; there are no other categories. Across all subjects, a nonzero exit coincides exactly with a focal label (0 mismatches). All 360 acceptable-variant attempts passed.
- **Observed, etcd5509:** every stated count is confirmed.

| Quantity | R (unrestricted) | L (2-CPU quota) |
|---|---:|---:|
| P1 supported blocking (blocks) | 7/10 | 10/10 |
| P3 supported blocking (blocks) | 5/10 | 7/10 |
| All recorded defective-variant attempts, focal | 24/30 | 26/30 |
| First attempts (a1), focal | 7/10 | 10/10 |
| Attempts 2–3, focal | 17/20 | 16/20 |
| P3 accepted after a focal witness | 2 | 3 |
| V_ok non-pass | 0/30 | 0/30 |

- **Paired contrasts d = S(R) − S(L):**
  - P1: 0 positive, 3 negative, 7 zero (Δ = −0.30). The batches give −0.40 (A) and −0.20 (B).
  - P3: 2 positive, 4 negative, 4 zero (Δ = −0.20). Both batches give −0.20.
- These match `analysis/summary.json` and `independent_verification.json`. All 50 focal etcd5509 attempts carry signature (a); signature (b) was never observed.

## 3. Task 2: block-level table (etcd5509)

Source: `out/s01_etcd5509_blocks.csv` (40 cell rows, with attempt IDs) and `out/s01_etcd5509_blocks.md`.

How to read the table:

- **F** is a focal witness (signature a, in-test 45 s timeout with the deadlock dump). **P** is a pass. The number is the host-clock attempt time in seconds.
- **Bold** marks a1, the **P1-visible prefix**. For P1, a2 and a3 are always **research-only suffixes**.
- A plain a2/a3 is inside the **P3-visible prefix**, which runs up to the first pass.
- A **[bracketed]** attempt is a research-only suffix for **both** policies.
- Pos (prev subject) is the position of etcd5509 among the six subjects in that block index, and the subject that ran just before it.
- Load % is the single Win32 host-load reading taken at the start of the block index.
- Cell order: R/L are the profiles, b/o are the bad and ok variants.

| Blk | Batch | Pos (prev subject) | Load % | Cell order | R/bad a1 · a2 · a3 | R S P1/P3 | L/bad a1 · a2 · a3 | L S P1/P3 | d P1 / d P3 |
|---:|---|---|---:|---|---|---|---|---|---|
| 1 | A | 5 (istio17860) | 6 | Rb > Ro > Lo > Lb | **P 0.6** · [F 42.2] · [F 42.2] | 0/0 | **F 42.2** · F 42.1 · P 0.5 | 1/0 | −1 / 0 |
| 2 | A | 3 (istio17860) | 21 | Lb > Rb > Lo > Ro | **P 0.5** · [F 42.1] · [F 42.1] | 0/0 | **F 42.1** · F 42.2 · F 42.1 | 1/1 | −1 / −1 |
| 3 | A | 1 (block start) | 13 | Ro > Rb > Lo > Lb | **F 42.1** · F 42.2 · F 42.1 | 1/1 | **F 42.1** · F 42.1 · F 42.1 | 1/1 | 0 / 0 |
| 4 | A | 4 (k8s26980) | 26 | Rb > Lb > Lo > Ro | **F 42.1** · F 42.0 · F 42.1 | 1/1 | **F 42.1** · F 41.9 · P 0.5 | 1/0 | 0 / +1 |
| 5 | A | 5 (k8s26980) | 29 | Lo > Ro > Lb > Rb | **F 42.1** · P 0.4 · [P 0.5] | 1/0 | **F 42.1** · F 42.0 · F 42.0 | 1/1 | 0 / −1 |
| 6 | B | 6 (grpc1859) | 13 | Rb > Lb > Lo > Ro | **P 0.6** · [F 44.1] · [F 44.0] | 0/0 | **F 44.4** · F 44.2 · F 44.8 | 1/1 | −1 / −1 |
| 7 | B | 6 (k8s26980) | 20 | Ro > Lo > Lb > Rb | **F 45.3** · P 0.5 · [F 45.3] | 1/0 | **F 45.3** · F 45.3 · F 45.3 | 1/1 | 0 / −1 |
| 8 | B | 5 (grpc1859) | 16 | Rb > Lb > Lo > Ro | **F 45.5** · F 45.4 · F 45.5 | 1/1 | **F 45.4** · P 0.5 · [P 0.5] | 1/0 | 0 / +1 |
| 9 | B | 3 (grpc2391) | 14 | Lb > Lo > Rb > Ro | **F 45.4** · F 45.4 · F 45.4 | 1/1 | **F 45.4** · F 45.3 · F 45.4 | 1/1 | 0 / 0 |
| 10 | B | 4 (istio17860) | 15 | Lb > Rb > Lo > Ro | **F 45.4** · F 45.4 · F 45.4 | 1/1 | **F 45.5** · F 45.5 · F 45.4 | 1/1 | 0 / 0 |

Acceptable variant (V_ok): R 30/30 PASS, 0.46–0.57 s (median 0.51); L 30/30 PASS, 0.41–0.59 s (median 0.51). Every V_ok attempt is inside its P1 and P3 prefix only in the sense that each policy stops after its first pass. All V_ok a2/a3 are research-only.

**Observed:** the three P1-discordant blocks (1, 2, 6) are all R cells whose a1 passed and whose **research-only** a2 and a3 both failed. In those blocks the R cell failed 2 of 3 attempts. The matching L cell failed 2/3, 3/3 and 3/3.

## 4. Task 3: position, order, batch, timing and host load

Script `s02_position_order_time.py`; output `out/s02_position_order_time.json`. Every probability below is a post hoc diagnostic.

### 4.1 Attempt position (observed)

| Position | R focal | L focal | Pooled |
|---|---:|---:|---:|
| a1 | 7/10 | 10/10 | 17/20 (0.85) |
| a2 | 8/10 | 9/10 | |
| a3 | 9/10 | 7/10 | |
| a2–a3 | 17/20 | 16/20 | 33/40 (0.825) |

- The profile ordering reverses with position. L is higher at a1 (10 vs 7), R is higher at a3 (9 vs 7), and a2 is 8 vs 9.
- Pooled across profiles, a1 is not special: 0.85 vs 0.825.
- Context from the four intermittent subjects, pooled:
  - R: a1 22/40, a2–a3 41/80.
  - L: a1 18/40, a2–a3 39/80.
  - No systematic first-attempt effect appears on either profile.

### 4.2 Cell order and preceding work (observed)

- **By cell position within the block, R/bad a1 focal:** position 1 2/4, position 2 2/3, position 3 1/1, position 4 2/2. **L/bad a1** was focal at every position (3/3, 3/3, 2/2, 2/2).
- **By the attempt that ran immediately before, R/bad a1 focal:**
  - after a failed etcd5509 bad attempt: 3/4;
  - after an etcd5509 ok attempt: 2/2;
  - after another subject: 2/4.
- **Order of the two bad cells:** R/bad ran before L/bad in 5 of 10 blocks. The R a1 passes fell in blocks where R ran first (1, 6) and where L ran first (2).
- **Interpretation:** there is no order pattern, but cells of n = 1–4 cannot exclude one.

### 4.3 Batch, time and host load (observed)

- **By batch:** R all attempts 11/15 (A) and 13/15 (B); L 13/15 and 13/15. R a1 3/5 and 4/5; L a1 5/5 and 5/5.
- **Host load** is a single Win32 LoadPercentage reading per block index (6–29%), taken before all six subjects. It is shared by the R and L cells of a block, so it cannot explain a within-block contrast. The discordant blocks had loads of 6, 21 and 13, within the overall range.
- **Clock non-stationarity.** A focal etcd5509 attempt ends when the Go test timer (the VM clock) reaches 45 s. Its host-clock duration was 41.9–42.2 s in blocks 1–5, 44.0–44.8 s in block 6, and 45.3–45.5 s in blocks 7–10 (`s05_clock_drift.py`).
  - The inferred VM-to-host clock ratio changed from about 1.07 in batch A to about 0.99 in batch B, equally for R and L.
  - etcd7492 shows the same 1.07 ratio in batch A.
  - This goes beyond the 5% rate disclosed at launch (`calibration/clock_probe.json`): the execution environment was **not stationary** across batches.
- **Interpretation:** the clock change is shared by both profiles within every matched block, and etcd5509's rates were stable across it. It therefore does not explain the etcd5509 contrast. It does show that batch-level environmental change occurred and was not otherwise recorded. See §6 for etcd7492.

### 4.4 Within-cell dependence (observed)

- **Transitions inside cells:** R F→F 13, F→P 2, P→F 4, P→P 1. L F→F 16, F→P 3, P→P 1.
- **Cells by number of failures (0/1/2/3):**
  - R observed 0/1/4/5 against 0.1/1.0/3.8/5.1 expected under Binomial(3, 0.80).
  - L observed 0/1/2/7 against 0.0/0.5/3.0/6.5 expected under Binomial(3, 0.867).
- The ANOVA intraclass correlation over the 20 cells is about **0.06**.
- **Interpretation:** retries inside a cell behave roughly like independent draws at a common rate. The data cannot rule out dependence, but they show no clustering.

### 4.5 First-attempt detection versus all-attempt frequency

These are different estimands:

- **P1 supported blocking** is one fresh attempt per cell: 10 observations per profile.
- **The all-attempt focal frequency** (24/30 and 26/30) counts 30 attempts in 10 cells per profile. It includes research-only suffixes, which no policy sees, and retries within a cell that are not independent samples of the matched-block unit.

The effective sample is therefore 10 blocks, not 30 attempts. The frozen analysis treats it that way, and so does this audit.

**Observed:**

- **All-attempt rates:** R 0.80 vs L 0.867 (2 attempts of 30).
- **First-attempt rates:** 0.70 vs 1.00.
- **Where the P1 gap sits:** a1 of three R cells. The research-only attempts in those same cells failed.
- **Historical unrestricted rate:** Q0 16/20 plus E1 52/65, same host class, before C1: **68/85 = 0.80**. That equals R. L is 1.4 attempts above it in expectation.

### 4.6 Ordinary-repetition null models (post hoc, exact)

| Diagnostic (etcd5509) | Value |
|---|---|
| Expected P1 blocks, iid at each profile's own attempt rate | R 8.0, L 8.7 (observed 7, 10) |
| Expected P3 blocks = 10·p³ | R 5.12, L 6.51 (observed **5, 7**) |
| Batch-A rate predicting batch-B P3 blocks (plan §4 diagnostic) | R 1.97 expected vs 3 observed; L 3.25 vs 4 |
| P(\|P1 gap\| ≥ 3 blocks) with one common rate (pooled 0.833 / historical 0.80) | 0.127 / 0.157 |
| P(\|P3 gap\| ≥ 2 blocks) with one common rate | 0.498 / 0.503 |
| P(L a1 = 10/10) at the historical rate 0.80 | 0.107 |
| Exact within-block sign-flip p (P1 S; P3 S; per-cell failure count) | 0.25; 0.69; 0.78 |
| **P(frozen C3 fires for etcd5509 \| no profile effect, iid)** | **0.41** (0.42 at p = 0.80) |
| P(C3 fires for ≥ 1 of the 6 subjects \| no profile effect, iid, each subject at its pooled rate) | **0.72** |

Sources: `s02` and `s04_null_gate_and_power.py`. C3 was evaluated exactly: |Δ| ≥ 0.20 over 10 blocks, the same nonzero sign in both batches, for P1 or P3.

## 5. Task 4: the etcd5509 oracle and specificity against CPU delay

### 5.1 Source and patch evidence

Inputs: the patch `ci_sensitivity_2026_09/task5_artifacts/etcd5509/recipe/as_built/bug_patch.diff`, the oracle card in `e1_harness/oracle.py`, and card C-01 in `task_c_candidate_acquisition.md`.

**The defect.** The bug patch reverses the fix in `remoteClient.acquire`. In the defective version, the closed-client path returns `ErrConnClosed` **while still holding `r.client.mu.RLock()`**. After that, every write `Lock()` on the same mutex blocks forever. That includes Close's second `Lock()`, and `connMonitor`'s lock sites.

**The test** is the post-fix `TestKVGetErrConnClosed`, backported identically to both variants. It races a goroutine's `Get(context.TODO())` against `Close()`, with no ordering gate. The deadlock happens only when Get's `acquire` runs after the client's cancel state is cleared. **Manifestation is therefore a scheduling race.** Once the race is triggered, the hang is permanent.

### 5.2 What the frozen positives contain

Script `s03_oracle_dumps.py` describes the dumps and relabels nothing. Outputs: `out/s03_oracle_dumps.json` and `out/s03_etcd5509_dumps.csv`.

| Source | n focal dumps | Timeout panic at 45 s | Get goroutine still alive | Other live clientv3 goroutines | Test goroutine in Close's own Lock (i) | Close chan-receive + connMonitor Lock (ii): sites 358 / 344 / 286 |
|---|---:|---:|---:|---:|---:|---|
| C1 R | 24 | 24 | 0 | 0 | 5 | 7 / 5 / 7 |
| C1 L | 26 | 26 | 0 | 0 | 5 | 10 / 1 / 11 |
| E1 (unrestricted) | 52 | 52 | 0 | 0 | 6 | 15 / 14 / 18 |
| Q0 (unrestricted) | 16 | 16 | 0 | 0 | 1 | 4 / 5 / 6 |

Sites: `client.go:358` is `connMonitor`'s body, `:344` is its deferred closure, and `:286` is `retryConnection`. One C1-L dump has both shape (i) and a connMonitor waiter.

**Observed:**

1. In all 118 positive dumps (50 C1, 68 historical), the Get goroutine had **already exited**. No other goroutine was executing clientv3 code. The only clientv3 goroutines were the test goroutine (in `Close`) and write-`Lock` waiters. A read lock held by a goroutine that no longer exists is exactly the leaked-RLock mechanism. An in-flight or slow holder would be visible in the dump, and none is.
2. **Pass durations reported by the test itself** (`--- PASS (…s)`): R/ok and L/ok 0.04–0.06 s (median 0.05), R/bad 0.04–0.06 s, L/bad 0.04–0.05 s. The quota produced **no measurable slowdown** of this test. The 45 s timeout is about 900 times the pass duration.
3. V_ok passed 30/30 under L and 30/30 under R, with no timeouts. The one-sided 95% upper bound on the V_ok L failure rate is about 0.095.
4. There was no `kv.Get took too long` (the 3 s non-focal bound) and no panic (signature b), on any variant or profile.

**Interpretation:** the frozen signature (a) positives under L are, structurally, the same deadlock as the historical unrestricted positives. The data give no sign that generic CPU delay produced any of them. Detection given a trigger is effectively certain under both profiles: the hang is permanent, the 45 s dump was captured 50/50 times, and there was no outer timeout. So the oracle **cannot** create an R–L difference through differential sensitivity. Any real difference would have to be in how often the race is triggered.

### 5.3 Unresolved ambiguity (stated, not resolved)

- **U1.** A goroutine dump does not record lock owners. The leaked-RLock attribution is an inference from three things:
  - no live holder is visible;
  - the source and patch;
  - V_ok's 0/60.

  It is strong, but it is not a direct observation.
- **U2.** A dump is a snapshot at 45 s. It shows that the waiters were blocked at that moment, not for how long. Permanence is inferred from the mechanism and from the roughly 900-fold gap to normal duration.
- **U3.** The textual final signature (restoration Step 3b) lists two connMonitor sites: the deferred closure and `retryConnection`. The frozen code rule accepts **any** connMonitor frame. The dumps also show a third site, `client.go:358`, in 4 of the 16 Q0 positives, 15 of the 52 E1 positives and 17 of the 50 C1 positives. Q0 attempt 7 is described in the record as a deferred-closure shape, but its dump shows site 358. Replay agreement (40/40 Q0, 158/158 E1) shows that the Q0 human labels also counted these dumps. It is the same mutex and the same root cause, so it is a **documentation imprecision, not a label change**. It is recorded here only.
- **U4.** The mix of shapes differs descriptively. The deferred-closure site is 1/26 under L, 5/24 under R and 19/68 historically. This is one post hoc comparison among several categories. It is compatible with the quota altering interleavings, and it is also compatible with chance. **It is not evidence of a causal effect.**
- **U5.** Signature (a) was corrected twice during Q0, once after 10 counted attempts (disclosed). C1 used the final frozen text, with 100% replay agreement. That history remains a limit on independent oracle validation.
- **U6.** Signature (b) has never been observed in any dataset. Its validity is untested, but it did not affect any C1 count.
- **U7.** The oracle cannot say *why* the race was won or lost. It cannot separate a quota effect from other correlates of the L condition, such as CFS throttling pauses or a different container start profile.

## 6. Task 5: other subjects (context only; no replacement winner and no redefined endpoint)

| Subject | R P1 / L P1 | R P3 / L P3 | All-attempt focal R / L | Note |
|---|---|---|---|---|
| etcd5509 | 7 / 10 | 5 / 7 | 24 / 26 of 30 | the C3 signal |
| etcd7492 | 4 / 0 | 0 / 0 | 7 / 3 of 30 | **all 10 focal failures (7 R, 3 L) occurred in batch A**, during the clock-ratio-1.07 era; zero in batch B on either profile |
| grpc1859 | 2 / 0 | 0 / 0 | 4 / 1 | tiny counts |
| grpc2391 | 9 / 8 | 8 / 7 | 28 / 27 | near-identical |
| istio17860 | 10 / 10 | 10 / 10 | 30 / 30 | saturated; carries no profile information |
| k8s26980 | 0 / 0 | 0 / 0 | 0 / 0 | never manifests; carries no profile information |

**Observed:**

- The direction of the P1 contrast is not coherent across subjects. L is higher for etcd5509, R is higher for etcd7492 and grpc1859, and grpc2391 is flat.
- etcd7492's large batch-A P1 contrast (+0.8), and its disappearance in batch B, coincide with an environmental change. Whatever the cause, it shows that sizeable single-batch contrasts arise here without replicating.
- Under no profile effect, some subject would pass C3 about 72% of the time.

**Interpretation:** the cross-subject picture is what chance produces on intermittent subjects, and it gives no support to a general CPU-quota effect.

## 7. Task 6: what ordinary repeated testing explains, and what remains uncertain

### Explained by ordinary repetition (descriptive)

- **P3 counts.** P3 blocking is p³ arithmetic from the attempt rates: expected 5.12 and 6.51, observed 5 and 7. Retry loss behaves as the plan's independent-attempt approximation predicts. As the plan anticipated, "an interaction generated merely by a changed failure rate and ordinary retry arithmetic" is not evidence of a new mechanism.
- **The P1 gap** falls within common-rate sampling variation (about 13–16%). It comes from three R first attempts whose own research-only suffixes failed.
- **The C3 firing** is expected with probability about 0.41 for this subject, with no profile effect.
- **The all-attempt rates** (0.80, 0.867) bracket the historical rate of 0.80. R equals it.
- **Retries within a cell** show no clustering (ICC about 0.06).

### Not explained, or uncertain

- **A small real L effect cannot be excluded in either direction.** The frozen simultaneous intervals are [−0.794, +0.475] for P1 and [−0.853, +0.667] for P3.
- **A mechanism exists by which a quota could raise the race rate:** throttling pauses landing in Close's lock window. It is a hypothesis only (U4, U7).
- **The environment was non-stationary**, as the clock-ratio shift shows. Other host factors went unmeasured, and host load is a single coarse snapshot per block index.
- **The design has limits:** one host, independence between blocks assumed, ten blocks.

### Descriptive versus causal

- **Descriptive:** L had 10/10 first-attempt failures against 7/10 for R, and 26/30 against 24/30 across all attempts. The positive dumps are structurally the historical deadlock. There was no V_ok failure and no pass slowdown.
- **Causal:** "a 2-CPU quota increases the deadlock trigger probability" is **not established** by these data. The pattern is adequately explained without it.

## 8. Recommendation: **STOP**

Current evidence does not justify further execution on this signal.

**Strongest evidence:**

- With no profile effect and independent attempts at a common rate, the frozen C3 gate fires for etcd5509 about 41% of the time, and for at least one of the six subjects about 72%.
- The observed counts are ordinary:
  - all-attempt focal failures differ by 2 of 30 (24 vs 26), and R equals the historical 0.80 rate;
  - the P3 counts equal p³ arithmetic (5.12 and 6.51 expected; 5 and 7 observed);
  - the whole P1 gap is three R first-attempt passes whose research-only retries then failed.
- The oracle's positives are specific to the historical deadlock and show no generic-delay signature. The signal's weakness is statistical, not diagnostic.

**Main uncertainty:** a small true L effect (about +0.05 to +0.10 per attempt) is neither excluded nor affordable to detect. `s04` computes exact power for a single fresh paired contrast using the frozen conservative Clopper–Pearson method (two-sided 0.05). The cost per matched block of single R/L attempts on both variants is 0.206 allocated vCPU-h, or 0.375 host-reservation vCPU-h, at C1's measured per-attempt charges.

- For 0.80 → 0.867 (the pilot's attempt rates), 600 blocks give only 53% power. That is about 124 allocated vCPU-h.
- For 0.80 → 0.90, about 400 blocks are needed for 83% power. That is about 82 allocated or 150 host-reservation vCPU-h, 3–6 times C1's 24 vCPU-h measured cap.
- Only an effect as large as the pilot's first-attempt point estimate (0.70 → 1.00) would confirm cheaply, and §4–§7 give no reason to believe that estimate over the attempt-level rates.

**What would change this conclusion:**

- Independent pre-existing evidence of a **large** quota effect (≥ 0.15 per attempt) on this or a closely analogous race.
- A pre-specified, mechanism-derived prediction that allows a cheap and sharp test. That would be a new, separately designed question, not a C1 confirmation.
- An external decision in which a change of a few percentage points in the manifestation probability of a known race has material consequences. Estimation, not confirmation, would then be the appropriate question.

C1 should stand as a completed pilot. Its answer to RQ3 (ordinary paired repetition with signatures is sufficient) is reinforced by this audit.

## 9. Reproduction, costs and hashes

### Commands (repository root; Python 3.14.3; stdlib only; no containers)

```text
python -B research_runs/ci_configuration_2026_09/signal_audit/run_timed.py s00_verify_integrity.py
python -B research_runs/ci_configuration_2026_09/signal_audit/run_timed.py s01_counts_and_blocks.py
python -B research_runs/ci_configuration_2026_09/signal_audit/run_timed.py s02_position_order_time.py
python -B research_runs/ci_configuration_2026_09/signal_audit/run_timed.py s03_oracle_dumps.py
python -B research_runs/ci_configuration_2026_09/signal_audit/run_timed.py s04_null_gate_and_power.py
python -B research_runs/ci_configuration_2026_09/signal_audit/run_timed.py s05_clock_drift.py
python -B research_runs/ci_configuration_2026_09/signal_audit/run_timed.py s06_manifest.py
```

`run_timed.py` captures each script's stdout and stderr to `out/<script>.stdout.txt` and `.stderr.txt`, and appends one row to `cost_log.jsonl`. All scripts are deterministic; none uses randomness. `s03` failed once with a SyntaxError (rc = 1) and was fixed and rerun. The failed run is kept in the cost log.

### Timed computation cost

The basis is conservative: 16 allocated vCPUs × wall time, as in the prior post-collection pass.

| Item | vCPU-h |
|---|---:|
| Analysis cap (C1 stage) | 2.000000 |
| Spent before this audit (annotate, analyze, independent verification) | 0.002832 |
| This audit: first 9 logged runs, s00–s06 plus one manifest rerun (129.9 s wall, of which `s04` exact power enumeration took 129.1 s) | 0.577207 |
| This audit: the last manifest run that hashes this final report version (logged in `cost_log.jsonl`) | ≈ 0.0003 |
| **Remaining (approx.)** | **≈ 1.4197** |

These charges are recorded in `signal_audit/cost_log.jsonl` only. **They were not appended to the chained `resources/resource_ledger.jsonl`**, which this audit left untouched. Until the researcher reconciles them, that ledger overstates the analysis-stage remainder by about 0.578 vCPU-h. Agent reasoning time is not included.

### Inputs and outputs

`out/MANIFEST.json` lists raw and LF-normalized SHA-256 digests for 47 input files, all audit scripts, all outputs and this report. That covers the 13 measured JSONL files, the schedule, the events and resource ledgers, both freeze files, the seal, the summary and report, the E1 and Q0 etcd5509 records and logs, the patch, and `e1_harness/oracle.py`. Key input digests (raw bytes):

- Raw ledgers: as sealed in `analysis_audit/pre_analysis_seal.json`, for example etcd5509 L `a8fbab63…125d` and R `a24d4807…3050`.
- `measured/annotations.jsonl`: `ca0030b5…124df`.
- Design freeze `087b338d…bff9fc`; launch freeze `45c524f1…70d` (LF-normalized).

| File (under `signal_audit/`) | Content |
|---|---|
| `s00_verify_integrity.py` → `out/integrity.json` | freezes, seal, chains, links |
| `s01_counts_and_blocks.py` → `out/s01_counts.json`, `out/s01_etcd5509_blocks.csv`, `.md` | Tasks 1–2 |
| `s02_position_order_time.py` → `out/s02_position_order_time.json` | Task 3 and null models |
| `s03_oracle_dumps.py` → `out/s03_oracle_dumps.json`, `out/s03_etcd5509_dumps.csv` | Task 4 |
| `s04_null_gate_and_power.py` → `out/s04_null_gate_and_power.json` | C3 under the null; power and cost |
| `s05_clock_drift.py` → `out/s05_clock_drift.json` | clock non-stationarity |
| `s06_manifest.py` → `out/MANIFEST.json` | hashes and cost totals |
| `audit_common.py`, `run_timed.py`, `cost_log.jsonl` | shared loaders, timing wrapper, cost log |

### Limits of this audit

- It is post hoc, with many diagnostics and no multiplicity control. The probabilities are descriptive.
- The null models assume independent attempts at a common rate. The ICC estimate supports this but has little power.
- The dump parser is a descriptive heuristic. It does not validate the frozen oracle.
- Historical rates come from the same host class but from earlier sessions and conditions (Q0, and E1 `q0-default-unpinned`).
- Power assumes single attempts with within-block independence, and it evaluates only the L-higher direction.
