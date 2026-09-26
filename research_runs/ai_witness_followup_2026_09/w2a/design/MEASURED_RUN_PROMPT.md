# W2A launch instruction — for the researcher to issue when ready

## Material Passport

- Prepared 2026-09-26 with design v1.0. This is a conditional follow-on prompt; it is not evidence that launch prerequisites exist.
- Issuing it authorizes exactly:
  - one synthetic smoke request, plus one recorded retry only after a failure that returned no identity;
  - the eight frozen measured sessions;
  - their independent validations;
  - within USD 8.10 total provider charge and the other study caps.
- It does not authorize purchases, a different model, extra sessions, design changes or follow-up studies.

---

Launch W2A v1.0 in this repository using the frozen package under `research_runs/ai_witness_followup_2026_09/w2a/`. Work as one agent. Read `AGENTS.md`, `w2a/README.md`, `design/PROTOCOL.md`, `design/EXECUTION_PLAN.md` and `readiness.md`. I have set `W2A_GENERATOR_API_KEY` in the environment to my existing OpenCode Zen key.

1. Verify the design and package freezes, run `w2a.py preflight`, and inspect the resource ledger. If any offline gate fails, stop and report.
2. Run the single synthetic smoke with authorization text "W2A smoke authorized by the researcher on <date>". Continue only if the smoke returns `claude-sonnet-5` and the `report_ready` tool call. A request-shape rejection stops the launch.
3. Confirm the current Claude Sonnet 5 price list from the OpenCode Zen documentation and record it with `confirm-pricing`. Stop if the prices differ from the frozen snapshot.
4. Write the launch freeze. Then run `w2a.py run --authorize "W2A v1.0 measured run authorized by the researcher on <date>"`.
5. Execute the immutable schedule serially. Do not rerun, extend, adapt prompts or budgets, or skip sessions. On a pause, preserve everything and report INCOMPLETE with the precise cause.
6. After collection, write the raw seal, run the frozen analysis, and independently re-derive the feasibility table, attrition, gate result and costs from the session and validation records.
7. Update `readiness.md`, the W2A results report and the research records. Separate observed results from interpretation. Apply only the frozen Gate 2 rule. Make no effectiveness, population, discovery or TCP claims.

Do not commit or push.
