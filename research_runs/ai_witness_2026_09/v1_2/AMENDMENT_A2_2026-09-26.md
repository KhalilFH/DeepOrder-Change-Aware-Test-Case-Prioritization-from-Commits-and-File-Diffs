# W1 amendment A2 — generator model family (v1.1 → v1.2)

## Material Passport

- Date: 2026-09-26. Authority: researcher instruction in a Claude Code session, choosing "(B) Sonnet 5 with caching: amendment v1.2" after a cost comparison, with an OpenCode Zen API key as the intended access.
- Prepared by a Claude Opus 5.5 coding session. It changed no prompts, packets, thresholds, counts, budgets, timeouts or endpoints.
- Observed before amendment: the fixed unchanged-test calibration (16 attempts: istio17860 V_bad focal 2/2, all other attempts PASS) and offline fake dry runs. Calibration involves no model, so it cannot favour either generator. **No provider call, model output or measured session had occurred.** The v1.1 verifier passed 17/17 immediately before this amendment.

## Change

| Field | v1.1 | v1.2 |
|---|---|---|
| `study_config.json` `provider_launch_fields.requested_generator_family` | `Claude Opus 5.5` | `Claude Sonnet 5` |
| `study_config.json` `design_version` / `amends` | `1.1` / v1.0 via A1 | `1.2` / v1.1 via this file |

Consequential text edits only: protocol.md (title, passport, model-family clause), README.md, DESIGN_FREEZE.md, HANDOFF_PROMPT.md, MEASURED_RUN_PROMPT.md and verify_design.py (version, paths, file list, model-family invariant, chained verification of v1.1). All other frozen files are byte-identical to v1.1. The v1.1 folder and the v1 files are preserved byte-identical.

## Rationale

The researcher preferred lower provider spend. Claude Sonnet 5 costs half as much per token as Claude Opus 5.5 ($2 / $10 against $4 / $20 per million input/output tokens). It is still a strong coding and agentic model. At the frozen session ceilings (60k input, 8k output tokens) the timeout-bound provider cost of the 36 AI sessions falls from USD 14.40 to USD 7.20.

Prompt caching was chosen at the same time. It is a launch setting, identical across arms, and changes price and latency, not model inputs. The token ceilings still count cached input tokens.

## Affected hypotheses and interpretation

- No hypothesis, contrast, arm, packet, prompt, count, budget, timeout or endpoint changes. B2, B3 and B4 still share one identical frozen generator configuration, so the B3-versus-B2 and B4-versus-B3 comparisons remain within one model.
- Results describe Claude Sonnet 5 as the generator. They do not transfer to Claude Opus 5.5, GPT-5.6 Sol or other models.
- A weaker generator could lower AI-arm yield. The design's interpretation limits already cover this: a null result is a protocol outcome for this model, not evidence that structured analysis cannot help.
- The cost ceilings (USD 8 per AI session, USD 300 study, 4M input tokens) are unchanged. They were checked against a pricing snapshot for the new model and remain comfortably met.
- Sonnet 5 always runs adaptive thinking unless it is disabled, and thinking counts as output. The frozen 8k output-token session ceiling therefore remains the main feasibility risk, as it was under v1.1.

## Launch fields still unresolved

These remain `null` in study_config.json and belong in launch_config.json: `generator_transport`, `generator_requested_model` (candidate `claude-sonnet-5`), `generator_returned_identity`, `generator_settings` and `pricing_snapshot`.

Intended transport: OpenCode Zen's Anthropic-Messages-compatible endpoint (`https://opencode.ai/zen/v1/messages`, Bearer auth; OpenCode docs, fetched 2026-09-26). Zen documents no routing or substitution policy. The returned identity must therefore be confirmed by the authorized smoke request, and any returned model other than the frozen one pauses sessions. The coding agent must not use its own conversation as a measured generator session.
