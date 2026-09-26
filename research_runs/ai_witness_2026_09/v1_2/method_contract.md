# W1 method and information contract

## Material Passport

- Date: 2026-09-25. Frozen arm definitions; model utility is unestablished.
- Model prompts are templates in prompts.md. Concrete rendering, source limits and tool schemas must be sealed at executable launch.

## Shared source and execution facilities

Materialize one common packet per case: production-only defective→repaired diff; source files enclosing changed functions plus statically referenced local helpers; supplied tests/helpers from the provenance in subject_register.md; build/run instructions; and deterministic T0 retrieval output. T0 ranks supplied tests by normalized changed-symbol/path token overlap, with lexical path/name tie-breaking. It also lists direct syntactic calls and source spans. It does not claim a sound whole-program call graph or supply human-written obligation answers.

The full allowed packet is readable by every arm through the same file tools; model request limits are identical. When context truncation is necessary, use a deterministic source-order/chunk policy frozen before launch, record omitted ranges, and make remaining allowed chunks retrievable within the same budget. Do not give only B3/B4 a better static slice. Bindings required by deterministic templates are shared source-linked metadata, not secret baseline hints. A preparation agent must not tune bindings from outcomes.

Tests may add inputs, calls, test-local synchronization, resource postconditions, or bounded observations, within the existing package and dependencies. Tests may not change production source, weaken/remove existing assertions, expand timeouts, inspect commit hashes/variant labels, read outside the packet, access the network, or fail by construction. A new regression assertion must encode a source-supported behavioral obligation and pass on the repaired variant. Existing assertions remain effective; if a harness extracts one test method it must preserve its semantics and required helpers.

The runner provides `read_source`, `submit_patch`, `build_pair`, `run_pair`, and `submit_final` semantics. Search feedback includes raw build/test output and ordinary stacks, not the independent focal classifier or held-out references. Every provider tool execution and patch is logged. Test edits are validated before subject execution; escaping the sandbox is an integrity stop.

## Arms

| Arm | Algorithm | Provider allowance per session |
|---|---|---|
| B0 | Unchanged supplied test; execute up to the shared paired-run cap; submit unchanged overlay | None |
| B1 | Fixed deterministic template search described below, using common T0 and bindings | None |
| B2 | Strong plain capable model: inspect raw source/static output, propose a small test improvement, use build/run feedback, revise or submit unchanged | At most 4 capable-model calls |
| B3 | Four fixed stages: obligation/prerequisite plan; atomic judgments by the capable model; test generation; optional one repair | At most 4 capable-model calls |
| B4 | Same stages and templates as B3, replacing only the judgment stage with Jev | At most 3 capable-model calls plus up to 8 Jev atomic evaluations |

All arms share 600 seconds, the patch and execution caps, and an equal USD ceiling. B2 can use its four calls flexibly and receives full feedback; it is not restricted to a weak single-shot prompt. B3/B4 have identical planner/generator/repair prompts and generator settings; their realized planner outputs may differ because they are independent sessions. This is an architectural ablation, not paired replay of identical intermediate model outputs. Preserve generated obligations to assess this variation.

Provider call counts are not equal across architectures: B4 may require multiple wire requests for one logical judgment stage. Count each actual request, retry, input token, output token and its cost. All AI arms share a 60,000 input-token and 8,000 output-token session ceiling across **all** provider requests, including duplicated context for atomic judgments. The 4-million-input-token study ceiling includes provider smoke calls. A provider integration that cannot enforce these ceilings is not launch-ready. No hidden agent reasoning calls or extra coordinator models.

### B1 deterministic templates

Freeze a generic template bank and source-bound applicability table before calibration. Each applicable entry must yield a reproducible test overlay without a live model. Implement these entries, in order:

1. Unchanged test reference, always applicable.
2. Repeat the complete existing test workload twice, then four times, with fresh fixture state and all assertions retained. Repetition variants each count as a patch proposal.
3. One resource-lifecycle template where source-bound operations support it: acquire/reserve → invoke an existing error/interruption action → release/cleanup as specified by the API → execute a second operation with a bounded progress/capacity assertion. Applicable operation bindings must be concrete source symbols shared with all arms. Do not insert a case-specific solved regression test and label it generic.

The bank has at most four candidates including unchanged. If the lifecycle entry is inapplicable, record why rather than substituting a bespoke fix. Run candidates in that order with the common pair budget. Remaining pair slots repeat candidates round-robin. Choose the earliest template ID with at least one ordinary bad-fail/ok-pass search pair and no observed ok failure, otherwise unchanged. This selection uses ordinary pass/fail, not the hidden focal oracle. B1 may therefore select a false signal; validation will expose it.

If a compatible controlled scheduler is qualified, use its fixed seed schedule for **all** arms and B0, without adding a sixth arm or an adaptive fuzzer. Report this as template comparison under a shared scheduler, not proof against the scheduler's unrestricted best configuration. If no scheduler is qualified, state the narrower comparator explicitly. A later stronger baseline study may be necessary before a publication claim.

### B3/B4 atomic judgments

The planner returns at most eight source-linked claims spanning input/reachability, ordering, resource/state restoration, and observable postcondition, plus a candidate intervention plan. Each claim asks whether the supplied test establishes one particular prerequisite. The judge emits `supported`, `contradicted`, or `unknown`; optional provider confidence is stored raw and is not treated as a probability of defect detection.

Missing evidence means unknown. `contradicted` requires source evidence of incompatibility; absence of an explicit action is not automatically proof that no helper performs it. Neither judgment authorizes an assertion without executable source support. The generator sees exactly the planner output and the completed judgment table; malformed or missing judgments become unknown and remain charged. One judgment stage only; no outcome-driven rejudging.

Jev supplies typed assessments, not the test patch. API-specific schemas and batch support must be verified using current official documentation/Context7 during implementation. Store actual requested and returned model identities and immutable request/response records. A mutable alias alone cannot substantiate a fixed model version; change detection pauses affected sessions.

## Isolation and prohibited adaptations

The coding agent and oracle author can know the historical mechanisms; measured model calls must operate only on the packet. Do not use the coding agent's ongoing conversation as a B2/B3/B4 experimental session. Use fresh provider contexts with auditable payloads. No manual model-output editing or free human repair during measured sessions.

Freeze template bindings, source packet contents, prompts, model settings, scheduler settings and parser rules before the first measured call. Improvements learned from W1 belong in a separately versioned experiment. Record human preparation time separately from inference and execution cost.
