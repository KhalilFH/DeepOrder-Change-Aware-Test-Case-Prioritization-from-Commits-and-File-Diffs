# C1 analysis and interpretation plan

## Material Passport

- Date: 2026-09-25; status: design frozen v1 before any C1 observation.
- Unit: one complete matched block within a defect subject; projects/defects, not attempts, define external replication.
- No APFD, predictive model or trained assessor is part of this analysis.

## 1. Scoring contract

Use only each policy's consumed prefix. Research-only suffixes are excluded from policy decisions, evidence and policy costs, but included in total research spending. Report all three policies even though P3-retain has identical blocking and execution cost to P3.

For subject `s`, profile `c`, policy `p`, block `b`:

- `S`: 1 if the defective variant blocks and its consumed prefix contains independently supported focal evidence; 0 if it accepts, or blocks for established non-focal reasons only. A potentially focal unresolved blocking prefix is unknown; harness-invalid observations may make the policy decision unknown. A known focal match under a questioned oracle cannot become a supported 1 until adjudicated.
- `B_bad`, `B_ok`: raw final blocking on each variant, independent of causal annotation. Invalid prefix decisions remain unknown.
- `N`: acceptable-variant blocking caused solely by independently verified nuisance; unknown if the necessary attribution is unresolved. An acceptable variant is not automatically a nuisance generator.
- `E`: focal evidence occurs in the defective variant's consumed prefix, whether or not the gate ultimately blocks. Unknown if needed evidence is unresolved. This distinguishes observation from enforcement.
- `M`: accepting defective variant with supported focal evidence in its consumed prefix. Count both masked blocks and witnesses; do not confuse them.
- `W`: P3-retain warning. Count warnings on both variants and report their adjudicated categories. A warning's usefulness and developer burden are unmeasured.
- Costs: prefix attempts and elapsed time, capacity-hours under the verified profile, separately measured CPU time where available. Missing CPU instrumentation means unknown, not zero.

Always output the consumed attempt IDs, ignored suffix IDs and decision rule. A signature on the acceptable variant triggers the validity procedure in the protocol, not a false-positive number silently absorbed into a successful comparison.

## 2. Primary and secondary contrasts

**Primary:** per subject and policy P1/P3, `Delta_S(p) = mean_b[S(R,p,b) - S(L,p,b)]`.

Positive means limiting CPU bandwidth reduces supported blocking; negative means it increases supported blocking. The design does not assume that fewer CPUs will make tests greener. There are at most 12 primary contrasts for six subjects. No pooled headline effect or project-population estimate.

**Secondary/descriptive:**

- Within-profile retry loss `L(c) = mean[S(c,P1) - S(c,P3)]`.
- Interaction `I = L(L) - L(R)`: positive means the limited profile loses more supported blocking to retries. Do not assume the general oracle-aware contrast is mathematically nonnegative; early non-focal failures followed by focal failures can change attribution.
- Raw block-rate changes on both variants. `D(c,p) = B_bad(c,p) - B_ok(c,p)` is raw revision discrimination, not independently proven defect specificity.
- Nuisance-block reduction, only with verified nuisance; evidence retention, masked witnesses, costs and two batch summaries.
- Raw attempt rates including suffixes are descriptive execution measurements. They are not the probability that a stopping policy encounters a failure.

A lower raw failure rate plus lower supported blocking on a known defective revision is evidence of reduced visibility in this setup. It is not evidence of fewer defects, a production incident rate, or a safety guarantee. A higher failure rate with generic timeouts may instead reveal a broken oracle or unsupported execution contract.

## 3. Uncertainty and missingness

Ten blocks are a feasibility sample. No equivalence test, significant/insignificant headline, power claim or population prevalence estimate is planned. Zero out of ten does not mean impossible. The pilot follow-up margin 0.20 is two blocks, chosen for development triage; it is not a minimal industrially important loss estimate.

For each primary paired contrast, score complete blocks as `d` in {-1,0,+1}. Estimate `mean(d)`. Preserve counts `n_plus`, `n_minus`, `n_zero`, and missing. Report a conservative interval by estimating `P(d=+1)` and `P(d=-1)` with exact binomial Clopper-Pearson intervals, then subtracting their opposing endpoints.

Freeze the family size at `K = 2 * number_of_enrolled_subjects` before collection; do not shrink it because a comparison fails. Use each of the `2*K` category intervals at confidence `1 - 0.05/(2*K)`. This supplies a conservative simultaneous primary family under independent matched blocks. Per-profile marginal 95% intervals are descriptive and not simultaneous. Do not mislabel either family as the E1 alpha setting.

Within-triplet independence is not assumed. Fresh containers do not prove independence across blocks: shared host load, clock and warm caches remain threats. Show both batches, ordering and timing; if strong batch drift or shared disruptions exist, retain intervals as assumption-dependent descriptive results and avoid generalization. The effective cross-defect sample remains at most six.

For every missing/invalid/unresolved primary block, bound the unknown indicators in [0,1] consistent with known observations. Compute the lowest and highest possible contrast over **all ten scheduled blocks**, not just complete cases. Missing cells can contribute [-1,+1]; a known side can narrow that. Show complete-case estimates beside these bounds. Never replace or silently drop attempts. Secondary interaction bounds follow from the same four indicators; do not treat four estimates as independent.

If more than 10% of a subject's attempts are harness-invalid, or unresolved evidence can change the claimed direction, that subject cannot support a directional follow-up claim. Report it nonetheless. No winsorizing durations; report timeouts and censoring explicitly.

## 4. Baselines that prevent unnecessary complexity

1. **Single-attempt raw status:** P1 and the raw R/L block rates. Useful as a deliberately limited view, never ground truth.
2. **Ordinary repeated assessment:** per-profile repetition counts, paired uncertainty and all raw outputs. No learned model.
3. **Signature-aware paired assessment:** the same repetitions plus frozen behavioral oracles and counterpart comparison. This is the strong baseline and the planned analysis itself; there is no competing novel assessor yet.
4. **Independent-attempt retry approximation:** descriptively compare observed raw P3 blocking with `p^3`, where `p` is the profile's raw attempt failure rate. Use batch A to estimate `p` and batch B for the displayed predictive check; also show sample sizes and broad binomial uncertainty. This is a secondary diagnostic, not a test of independence or a guaranteed model. Unresolved/invalid traces are not coerced into valid IID trials.
5. **P3-retain reporting control:** establishes whether evidence is preserved at identical execution cost. It does not demonstrate that humans act on it or that a new release policy is superior.

If counts and ordinary signature-aware comparisons explain the results, that is a sufficient outcome. An interaction generated merely by a changed failure rate and ordinary retry arithmetic is not evidence that adaptive reasoning is required.

## 5. Required outputs

Future outputs under this study only:

- `analysis/attempt_index.csv`: provenance join and every oracle category, including validation stage.
- `analysis/policy_decisions.csv`: every measured subject/block/profile/variant/policy, prefix and suffix IDs, gate, warning and costs.
- `analysis/subject_contrasts.csv`: all frozen primary contrasts, counts, intervals, missingness bounds, batches and inclusion status.
- `analysis/summary.json`: exact numerators/denominators, family size, thresholds, excluded comparisons and cost totals.
- `analysis/report.md`: design deviations, results, threats and gate decision, explicitly separating observations, interpretation and proposals.
- `analysis/reproduction.md`: literal commands, environment, hashes, code revision, input manifests and output digests.

Before interpretation, independently recompute sampled prefix decisions and all primary numerators from raw attempt IDs. Prefer a small independent arithmetic check over trusting a second rendering of the same summary. If confirmation is warranted, define a fresh study with a justified sample size and predeclared subjects; do not append blocks until a pilot interval excludes zero.
