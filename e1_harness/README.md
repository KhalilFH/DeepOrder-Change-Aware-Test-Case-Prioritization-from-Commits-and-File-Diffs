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
| Analysis script (`S`, `N`, `L`, `R`, cost) | `analysis.py` | `tests/test_analysis.py` | **done** |

Plus the evaluator step the runner deliberately leaves out:

| Piece | File | Tests | Status |
|---|---|---|---|
| Oracle classifier (raw output → attempt categories) | `oracle.py` | `tests/test_oracle.py` | **done** |

Unit tests are stdlib only. The oracle tests include a replay of all
120 preserved Q0 qualification logs (`research_runs/.../task5_artifacts/`):
the frozen cards reproduce every recorded label, and removing a witness's key
goroutine from a real dump turns it `UNRESOLVED`.

## Running the tests

```bash
python -m unittest discover -s e1_harness/tests -t e1_harness -v   # no Docker needed
python e1_harness/selftest.py                                      # needs a built image
```

Tests live in `e1_harness/tests/`. `-t e1_harness` sets the top-level directory,
which is what puts `policy`, `ledger` and `runner` on the import path; running
discovery without it will fail to import them.

The unit suite injects a fake executor, so it proves the orchestration but
nothing about real containers. `selftest.py` covers the three properties that
cannot be faked — reset isolation, direct-execution-versus-replay agreement, and
no container outliving a timed-out attempt. Last run 2026-09-22 against
`grpc1859-bug`: all passed (the timed-out container was still running when the
CLI was killed, so the cleanup is needed, not precautionary).

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
by `selftest.py`, not assumed from `--rm`. Each container is named
`e1-<episode>-b<block>-<version>-a<attempt>-<nonce>` (recorded as
`extra.container`). A timeout kills only the local `docker` CLI, so
`DockerExecutor` then runs `docker rm -f <name>` and records the outcome in
`extra.cleanup`. Without that, a hung container would keep consuming CPU during
later attempts.

**A measured block always collects the full suffix** (`runner.py`).
`run_block` runs three attempts per version whatever the outcomes, so P1 and P3
replay from one shared prefix-generating procedure (plan §4.4). Conditioning
collection on the first outcome would distort unconditional blocking rates.

**Only a frozen signature makes a focal witness** (`oracle.py`). Each episode's
pre-declared signature is transcribed as an `OracleCard` citing its source
record; the file's hash is written on every annotation. A failure matching no
signature is `UNRESOLVED`. The classifier never emits `OTHER_DEFECT` or
`VERIFIED_NUISANCE`: both are claims about the world that output-matching
cannot establish, so they enter only as researcher overrides carrying an
adjudicator, reason and evidence, with the mechanical label kept beside them.

**Unestablished target execution is `HARNESS_INVALID`** (`oracle.py`). No exit
status, a Docker-level failure, a skipped test, or no `=== RUN <test>` line.
The analysis feeds such attempts to the reducer as `None`.

**Nothing is imputed silently** (`analysis.py`). A block whose decision is
`INDETERMINATE`, or whose failing prefix holds an `UNRESOLVED` attempt, has an
undetermined `S`/`N` indicator. Contrasts are reported complete-case with
exact paired intervals (Clopper-Pearson on each discordance direction,
Bonferroni over every contrast in the run) and with conservative best/worst
fills. Measured blocks are declared with `--blocks`; a declared block without
records is reported missing.

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
    # The frozen Q0 command. -test.v gives the oracle the target's execution
    # identity; -test.timeout must fire *below* timeout_s, or a hang is killed
    # by the runner before Go prints the goroutine dump the witness needs.
    argv=["/go/gobench.test", "-test.v", "-test.count", "1",
          "-test.run", "TestKVGetErrConnClosed", "-test.timeout", "45s"],
    timeout_s=60,
    condition="default",
)
with Ledger("runs/etcd5509/attempts.jsonl") as led:
    Runner(manifest).run_block(led, block=1, seed=1)

rows = read_records("runs/etcd5509/attempts.jsonl")
statuses = exit_statuses_for(rows, "etcd5509", 1, V_BAD)
reduce_block(P1, statuses), reduce_block(P3, statuses)
```

Then classify and analyse, in that order, without editing either output by hand:

```bash
python e1_harness/oracle.py --ledger runs/attempts.jsonl --out runs/annotations.jsonl \
    [--overrides runs/adjudications.jsonl]
python e1_harness/analysis.py --ledger runs/attempts.jsonl --annotations runs/annotations.jsonl \
    --blocks 1-20 --direct-blocks 101-112 --batch 1-10 --batch 11-20 \
    --allocated-vcpus 2 --out runs/analysis
```

`analysis.py` writes `policy_decisions.csv` (every decision with the attempt
IDs it consumed and its rule), `summary.json` and `report.md`.
`--allocated-vcpus` is required because the runner does not pin CPUs: state
the allocation used for accounting rather than let a default imply one.

`Manifest.sha256` is recorded on every attempt, so a ledger states which frozen
subject definition produced it. The manifest refuses a timeout above the plan's
120-second attempt ceiling.

## Not in scope here

Oracle cards exist for etcd-5509 and etcd-7492 (E1's subjects) and for
grpc-go-1859 (`Q0_NOT_QUALIFIED`; kept to validate a non-hang witness). The
identity/no-change and deterministic-failure controls have no card yet; the
oracle refuses an episode without one. Signature (b) of etcd-5509 and both
grpc-go-1859 stack forms never fired in Q0 and are validated only on
constructed dumps. Selection, quarantine and any learned model are outside
Experiment 1 entirely.
