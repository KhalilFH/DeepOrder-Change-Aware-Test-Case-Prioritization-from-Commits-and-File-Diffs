# W1 amendment A1 — generator model family (v1 → v1.1)

## Material Passport

- Date: 2026-09-26. Authority: researcher instruction in a Claude Code session: "I will use opus 5.5".
- Prepared by a Claude Opus 5.5 coding session. It changed no prompts, packets, thresholds, counts or budgets.
- Measured outcomes observed before amendment: **none**. No W1 implementation, subject calibration, provider call or measured session has occurred. The v1 verifier passed 16/16 on 2026-09-26 immediately before this amendment.

## Change

| Field | v1 (2026-09-25) | v1.1 (2026-09-26) |
|---|---|---|
| `study_config.json` `provider_launch_fields.requested_generator_family` | `GPT-5.6 Sol` | `Claude Opus 5.5` |
| `study_config.json` `design_version` / `design_date` | `1.0` / `2026-09-25` | `1.1` / `2026-09-26`, plus an `amends` pointer |

Consequential text edits only: protocol.md (model-family clause, title, amendment rule), HANDOFF_PROMPT.md and MEASURED_RUN_PROMPT.md (v1.1 paths, model-identity instruction), README.md, DESIGN_FREEZE.md and verify_design.py (version, file list, model-family invariant). All other frozen files are byte-identical to v1.

## Rationale

The researcher chose Claude Opus 5.5 as the capable generator shared by B2, B3 and B4. v1 recorded GPT-5.6 Sol as the requested family, and protocol.md requires an amendment for a model-family change instead of a silent substitution.

## Affected hypotheses and interpretation

- No hypothesis, contrast, arm definition, packet, prompt, count, budget, timeout or endpoint changes. B2, B3 and B4 still share one identical frozen generator configuration, so the B3-versus-B2 and B4-versus-B3 comparisons remain within one model.
- Results describe Claude Opus 5.5 as the generator and do not transfer to GPT-5.6 Sol or other models. Jev's role is unchanged.
- The GPT-5.6 Sol case assessment remains background rationale; it was never a W1 arm.
- The cost ceilings (USD 8 per AI session, USD 300 study, 4M input tokens) were not re-derived for the new model. The launch cost projection must check them against a pricing snapshot for the resolved model. If they cannot be met, that is a NOT_READY gate or a further amendment, not a silent change.

## Launch fields still unresolved

`generator_transport`, `generator_requested_model`, `generator_returned_identity`, `generator_settings` and `pricing_snapshot` remain `null` and belong in launch_config.json. The candidate API model ID `claude-opus-5-5` is a note for the coding agent to confirm against the provider at launch, not a frozen value. As in v1, the coding agent must not use its own conversation as a measured generator session, even if it runs on the same model family.
