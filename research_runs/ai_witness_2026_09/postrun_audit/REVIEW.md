# W1 post-collection trace audit and next experiment

## Material Passport

- Date: 2026-09-26. Requested by the researcher after W1 completion.
- Verification status: **ANALYZED**, with artifact integrity and descriptive arithmetic **VERIFIED** by the accompanying offline script. No subject execution, provider call, oracle reclassification, or prospective validation occurred.
- Inputs: W1 v1.2, executable freeze, raw seal, all 60 session/validation records, 119 generator response/request pairs, and the two ledgers. The audit reads public tool calls and metadata, not model thinking text.
- Outputs: [audit.py](audit.py), [audit.json](audit.json), this review, and the separate [W2A proposal](../../ai_witness_followup_2026_09/v0_1/PROPOSAL.md).
- Exposure: all W1 cases and outcomes are known. Findings below are post hoc development evidence.

## What reproduces

All 1,962 raw artifact hashes, 181 executable-freeze hashes, and the 16/17/17 chained design entries match. The event chain has 2,152 intact rows and the resource chain 3,338. All 60 endpoint labels and all 28 complete validation policy summaries reproduce from recorded slot states. This is arithmetic verification of existing classifications, not a fresh check that every focal oracle diagnosis is correct.

Every one of the 119 measured generator responses identifies **`claude-sonnet-5`**. The launch record identifies the transport as OpenCode Zen. The researcher's model correction agrees with the actual run. GPT-5.6 Sol and Claude Opus 5.5 are superseded design choices, not measured generators; their frozen historical mentions should remain.

| Case | Unchanged B0 | Templates B1 | Plain AI B2 | Structured AI B3 | Structured + Jev B4 |
|---|---:|---:|---:|---:|---:|
| pool162 | 0/3 | 3/3 | 0/3 | 0/3 | 0/3 |
| grpc1859 | 2/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| k8s26980 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| istio17860 control | 3/3 | 3/3 | 3/3 unchanged | 0/3 | 0/3 |

The 32 NO_SUBMISSION outcomes remain observed method failures in the denominator. They are not missing observations to exclude. No AI arm sealed a modified candidate. B1's POOL template is a useful positive feasibility example, but it is one template on one known case, not three independent bug discoveries.

## Corrections and additions to the first report

### 1. Six input-admission denials and one output-admission denial

The original report groups all seven BUDGET_DENIED sessions under the input ceiling. The recorded events instead show **six input-token admission denials and one output-token denial**. All seven occurred on pool162.

For `w1.pool162.r3.B3.req03`, the event says `output-token ceiling leaves 880 tokens`. The provider adapter requires at least 1,024 remaining output tokens to admit a call. Separately, four received responses ended with `stop_reason=max_tokens` (two B3 and two B4). Thus output limits also affected execution; the evidence does not support dismissing the launch-time output concern.

Input denial is prospective admission, not proof that exactly 60,000 tokens were consumed. For example, pool162 r1 B2 was denied with 27,913 tokens remaining because the next request's admission estimate was 28,638. We cannot know the actual usage of an unsent request. Counting cache reads is the frozen resource definition; lower cache pricing does not exempt those tokens.

### 2. Most generation stages had almost no interaction budget

| Arm | Total generator requests | Requests in generation stage | Sessions with 0 / 1 / 2 generation requests | Median session seconds | Maximum seconds |
|---|---:|---:|---|---:|---:|
| B2 | 40 | 40 | 0 / 1 / 1; remaining 10 had 3–4 | 35.9 | 52.6 |
| B3 | 44 | 14 | 1 / 8 / 3 | 62.9 | 83.9 |
| B4 | 35 | 17 | 1 / 5 / 6 | 56.4 | 72.2 |

All AI sessions stopped within 84 seconds despite a 600-second wall allowance. Call and token constraints, rather than elapsed wall time, were the recorded bottlenecks. This does not prove a longer interaction budget would produce valid witnesses.

The normal dependent sequence can require source retrieval, proposing, receiving an ID, building, inspecting output, running, inspecting output, and explicitly sealing a final. Some calls can be batched or use `latest`; it is not mathematically impossible in four calls. It is nevertheless a brittle allowance, especially when planning and judgment consume it first. The harness did reach its generation stage in most structured sessions; it did not complete usable test generation.

### 3. Source reads were not simply unnecessary repetition

There were 54 `read_source` tool uses (18 B2, 19 B3, 17 B4). **None of the complete requested ranges was wholly contained in an initial excerpt.** This conservative check does not mean there was no partial overlap or that every read was useful. Eight requested ranges repeated ranges requested in an earlier stage of the same session (six B3, two B4).

Concrete example: grpc1859's initial test excerpt covers lines 6000–6008, the wrapper that calls `testClientDoesntDeadlockWhileWritingErrornousLargeMessages`. The implementation helper at lines 6009–6042 is not in that excerpt. In r1 B3 the planner reads it, the judge reads it, and the generator reads it again. The judge and generator each start a new one-message conversation; prior tool results are not transferred. The repeated retrieval has an identifiable context-transfer cause.

Therefore the first report's wording about rereading already supplied ranges is too broad. A better response is to include deterministically selected helper bodies and transfer source evidence, not prohibit necessary source reads.

### 4. Stage completion was accepted without sufficient content validation

- B3 produced plans with claims in 10/12 sessions; B4 in 11/12.
- Two `max_tokens` responses contain `submit_plan` with an empty input object: pool162 r1 B3 and istio17860 r2 B4. `_tool_loop` captures the tool name as stage completion. `_plan_claims` then returns no claims; the workflow proceeds.
- istio17860 r1 B3 submits an empty judgment list against seven claims. All seven retain the default `unknown`. This differs from seven explicit, reasoned unknown judgments and needs a separate completeness flag.
- The sole AI patch, pool162 r1 B3, targets a file literally named `placeholder`; the edit contract rejects it. It is a patch attempt, not a legal synthesized test. The absence of INVALID_CANDIDATE final labels does not imply absence of invalid intermediate proposals.
- Several B2 requests try `run_pair` before building. Returned errors consume additional interaction turns. Final-call tool results cannot be assumed to have reached the model: the audit only counts errors visible in subsequent saved requests.

These are observed execution/interface failures. Their individual causal contributions are not isolated by W1. Provider `strict` tool declarations did not remove the need for local semantic validation.

## Interpretation and proposed next investment

W1 supports **no method advancement under D005**, and it does not establish that Sonnet, structured analysis, or Jev cannot strengthen tests. The strongest next step is a small **W2A execution-feasibility pilot** on these already exposed development cases, with a new implementation and protocol identity. Its immediate question is whether plain and structured agents can finish the workflow and submit legal modified tests at bounded cost.

Keep the same generator family so a model change does not obscure the harness investigation. First fix context transfer, stage completeness, tool-state feedback and finalization budget; then measure completion. Jev's 71 evaluations did not yield a sealed synthesized candidate, so adding more Jev calls before this gate would not resolve the immediate uncertainty. If feasibility succeeds, a later effectiveness design should restore B0/B1 and explicitly compare plain, structured and structured-plus-Jev methods under matched resources.

POOL is the demonstrated test-strengthening feasibility case. Kubernetes is the unresolved ordering/observation challenge. gRPC is a rare-signal case where a replacement can lose an existing witness. Istio is a control where retaining the unchanged test is appropriate. The proposed pilot keeps all four visible to avoid selecting only the easiest success.

## Statistical interpretation check: 11/11 considered

| Check | Assessment |
|---|---|
| Simpson's paradox | Keep case-level results and control separate; pooled yield is misleading here. |
| Ecological fallacy | No inference from four selected cases to repositories or bugs generally. |
| Berkson/selection bias | Familiar, restored cases are a selected development sample. |
| Collider bias | Do not condition method comparisons on successful submission. |
| Base-rate neglect | Known defective/repaired pairs do not estimate real-world diagnostic prevalence or precision. |
| Regression to mean | Future improvements on prior low-yield cases require concurrent controls. |
| Survivorship | All 60 scheduled rows retained, including 32 NO_SUBMISSION outcomes. |
| Look-elsewhere | No best-arm significance claim or new success threshold applied to W1. |
| Forking paths | This audit and W2A are explicitly post hoc; no retrospective preregistration. |
| Correlation/causation | Failure traces motivate changes but do not isolate which change will help. |
| Reverse causality | No reverse-direction claim; budgets preceded outcomes, but this is not an identified component-effect experiment. |

No p-values, population confidence intervals or equivalence claims are warranted. Fifteen validation attempts and three search replicates are not independent sampled defects.

## Reproduce

From the repository root:

```text
python research_runs/ai_witness_2026_09/postrun_audit/audit.py
```

The script writes only `postrun_audit/audit.json`. It does not import or modify the frozen harness, append to W1 ledgers, send requests, or start containers. Manifest and chain failures stop it. Arithmetic checks assume this closed dataset's recorded absence of invalid sealed candidates and acceptable-variant failures and fail if those premises change. Original frozen analysis and raw records remain unchanged.
