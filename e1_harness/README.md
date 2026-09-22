# E1 harness

Implementation area for Experiment 1 of the CI policy-sensitivity study
(`docs/research/NEXT_RESEARCH_ACTION_PLAN.md` §6). Deliberately isolated: it
shares no code with `pipeline/`, which stays untouched, and it has **no
third-party dependency**.

The plan authorises exactly four thin pieces here. Status:

| Piece | File | Tests | Status |
|---|---|---|---|
| Explicit policy reducer | `policy.py` | `tests/test_policy.py` | **done** |
| Append-only attempt logger | `ledger.py` | `tests/test_ledger.py` | **done** |
| Thin isolated command runner | `runner.py` | `tests/test_runner.py` | **done** |
| Analysis script (`S`, `N`, `L`, `R`, cost) | — | — | not built |

76 unit tests green, stdlib only.

## Running the tests

```bash
python -m unittest discover -s e1_harness/tests -t e1_harness -v   # no Docker needed
python e1_harness/selftest.py                                      # needs a built image
```

Tests live in `e1_harness/tests/`. `-t e1_harness` sets the top-level directory,
which is what puts `policy`, `ledger` and `runner` on the import path; running
discovery without it will fail to import them.

The unit suite injects a fake executor, so it proves the orchestration but
nothing about real containers. `selftest.py` covers the two properties that
cannot be faked — reset isolation and direct-execution-versus-replay agreement.
Last run 2026-09-22 against `grpc1859-bug`: all passed.

Both are **implementation-validation** only. Per the plan's Experiment 1
procedure, synthetic truth-table inputs validate the implementation and never
enter empirical results.

## The contracts these modules enforce

Each of these is enforced in code rather than left to discipline, because each
is load-bearing for the experiment's validity.

**A policy reads only exit statuses** (`policy.py`). Oracle annotations are
evaluator-only. Passing a category where a status belongs raises `PolicyError`.

**A policy reads only the attempts it would have executed** (`policy.py`).
Everything past the stopping point is a research-only suffix: recorded,
reported, never consulted. A pass in the suffix cannot rescue a block.

**A truncated block is `INDETERMINATE`, never `BLOCK`** (`policy.py`). Treating
it as a block would invent a decision the data does not support. Missing and
`HARNESS_INVALID` attempts enter as `None` and propagate.

**The ledger is append-only** (`ledger.py`). There is no update, delete or
truncate verb; re-recording an attempt identity is refused. Plan §4.3 requires
earlier failures to stay in the ledger even when a policy accepts, so nothing
may remove them.

**The ledger is tamper-evident** (`ledger.py`). Records are SHA-256 chained, so
`verify_chain` detects any later edit, reorder or deletion. Not security against
an adversary — the point is that a result turning on a handful of attempts
should not rest on a file that could have been quietly corrected.

**The runner classifies nothing** (`runner.py`). It records observations;
assigning categories is a separate evaluator step. A runner that classified at
capture time would be adjudicating on the same pass that observes.

**Reset is a fresh container per attempt** (`runner.py`). Verified empirically
by `selftest.py`, not assumed from `--rm`.

**A measured block always collects the full suffix** (`runner.py`).
`run_block` runs three attempts per version whatever the outcomes, so P1 and P3
replay from one shared prefix-generating procedure (plan §4.4). Conditioning
collection on the first outcome would distort unconditional blocking rates.

**Direct execution and replay must agree** (`runner.py`).
`run_policy_direct` stops early for real, for the plan's 12 direct-policy
checks, and its decision comes from the same reducer that scores replayed
blocks — so a disagreement is a structural mismatch, not a difference of
opinion. `reserved_from` keeps those checks out of the measured block range.

## Sketch

```python
from ledger import Ledger, V_BAD, V_OK, exit_statuses_for, read_records
from policy import P1, P3, reduce_block
from runner import Manifest, Runner

manifest = Manifest(
    episode="etcd5509",
    images={V_BAD: "etcd5509-bug", V_OK: "etcd5509-fix"},
    workdir="/go/src/github.com/coreos/etcd/clientv3/integration",
    argv=["/go/gobench.test", "-test.count", "1", "-test.run", "^TestKVGetErrConnClosed$"],
    timeout_s=45,
    condition="default",
)
with Ledger("runs/etcd5509/attempts.jsonl") as led:
    Runner(manifest).run_block(led, block=1, seed=1)

rows = read_records("runs/etcd5509/attempts.jsonl")
statuses = exit_statuses_for(rows, "etcd5509", 1, V_BAD)
reduce_block(P1, statuses), reduce_block(P3, statuses)
```

`Manifest.sha256` is recorded on every attempt, so a ledger states which frozen
subject definition produced it. The manifest refuses a timeout above the plan's
120-second attempt ceiling.

## Not in scope here

The oracle classifier (raw output → attempt categories) and the analysis script
are not built. Selection, quarantine and any learned model are outside
Experiment 1 entirely.
