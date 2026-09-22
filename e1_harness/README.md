# E1 harness

Implementation area for Experiment 1 of the CI policy-sensitivity study
(`docs/research/NEXT_RESEARCH_ACTION_PLAN.md` §6). Deliberately isolated: it
shares no code with `pipeline/`, which stays untouched, and it has **no
third-party dependency**.

The plan authorises exactly four thin pieces here. Status:

| Piece | File | Status |
|---|---|---|
| Explicit policy reducer | `policy.py` | **done**, 34 truth-table tests green |
| Thin isolated command runner | — | not built |
| Append-only attempt logger | — | not built |
| Analysis script (`S`, `N`, `L`, `R`, cost) | — | not built |

## Running the tests

```bash
python -m unittest discover -s e1_harness -t e1_harness -v
```

Stdlib only; pytest also collects them if available.

These are **implementation-validation tests**. Per the plan's Experiment 1
procedure, synthetic truth-table inputs validate the implementation and never
enter empirical results.

## What `policy.py` enforces

Two invariants are enforced in code rather than left to convention, because
both are load-bearing for the experiment's validity:

1. **A policy reads only exit statuses.** Oracle annotations
   (`FOCAL_DEFECT_WITNESS`, `VERIFIED_NUISANCE`, …) are evaluator-only. Passing
   a category where a status belongs raises `PolicyError` rather than silently
   scoring something.
2. **A policy reads only the attempts it would have executed.** Blocks record up
   to three attempts per version even after a pass, so P1 and P3 can be replayed
   from one shared prefix-generating procedure. Everything past the stopping
   point is a *research-only suffix*: recorded and reported, never consulted.
   A pass in the suffix cannot rescue a block.

A block whose recorded attempts cannot determine the decision is
`INDETERMINATE`, never `BLOCK` — treating a truncated block as a block would
invent a decision the data does not support. Missing and `HARNESS_INVALID`
attempts enter as `None` and propagate to `INDETERMINATE` when they fall inside
the consumed prefix.

`focal_evidence_in_prefix` and `blocked_solely_by_nuisance` are the per-block
indicators behind the plan's `S` and `N`. Both require the final outcome to be a
block; `N` additionally requires *every* consumed failing attempt to be
independently verified nuisance, so an `UNRESOLVED` attempt or another real
defect disqualifies it.

## Not in scope here

Reset cleanup, actual early-stopping execution, and the 12 direct-policy checks
belong to the runner, not the reducer; the reducer is pure and executes nothing.
Selection, quarantine and any learned model are outside Experiment 1 entirely.
