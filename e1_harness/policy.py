"""E1 policy reducer: turn a block's recorded attempts into a policy decision.

Scope, per the approved plan (`docs/research/NEXT_RESEARCH_ACTION_PLAN.md`,
sections 4.2-4.5 and Experiment 1): this module is the *explicit policy reducer*
only. It executes nothing, reads no files, and has no third-party dependency.
The command runner, the append-only attempt logger and the analysis script are
separate pieces of the E1 harness.

Two invariants are enforced here rather than left to convention, because both
are load-bearing for the experiment's validity:

1.  **A policy sees only exit statuses.** The richer oracle annotations
    (`FOCAL_DEFECT_WITNESS` and friends) are evaluator-only information.
    `reduce_block` therefore accepts integers, and rejects anything else -
    including a category string passed in by mistake.

2.  **A policy sees only the attempts it would actually have executed.** A block
    collects up to three attempts per version even after a pass, so that P1 and
    P3 can be replayed from one shared prefix-generating procedure. Everything
    after the policy's stopping point is a *research-only suffix*: it is
    recorded, it is reported, and it must never influence the decision or the
    evidence that supports it.

A block whose recorded attempts cannot determine the policy's decision is
`INDETERMINATE`. That is deliberately not `BLOCK`: treating a truncated block as
a block would invent a decision the data does not support.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

# --- policies ---------------------------------------------------------------

P1 = "P1"
"""One attempt. Nonzero exit blocks; zero accepts."""

P3 = "P3"
"""Accept-on-pass retry, at most three total attempts."""

P3_RETAIN = "P3-retain"
"""P3's executed prefix and cost, with an accept-after-failure flagged."""

POLICIES = (P1, P3, P3_RETAIN)

RETRY_BUDGET = 3

# --- decision outcomes ------------------------------------------------------

ACCEPT = "ACCEPT"
BLOCK = "BLOCK"
INDETERMINATE = "INDETERMINATE"

ACCEPT_WITH_PRIOR_FAILURE = "ACCEPT_WITH_PRIOR_FAILURE"

# --- attempt categories (evaluator-only; never inputs to a policy) ----------

PASS = "PASS"
FOCAL_DEFECT_WITNESS = "FOCAL_DEFECT_WITNESS"
VERIFIED_NUISANCE = "VERIFIED_NUISANCE"
OTHER_DEFECT = "OTHER_DEFECT"
UNRESOLVED = "UNRESOLVED"
HARNESS_INVALID = "HARNESS_INVALID"

CATEGORIES = frozenset(
    {
        PASS,
        FOCAL_DEFECT_WITNESS,
        VERIFIED_NUISANCE,
        OTHER_DEFECT,
        UNRESOLVED,
        HARNESS_INVALID,
    }
)


class PolicyError(ValueError):
    """A reducer input violated the experiment's contract."""


@dataclass(frozen=True)
class Decision:
    """What a policy decided, and exactly which attempts it was entitled to see.

    `attempts_consumed` is the policy's cost in attempts, and the basis for the
    plan's prefix-cost measurement. `research_only_indices` are the attempts the
    block recorded beyond that point; they are preserved for reporting and are
    invisible to the decision.
    """

    policy: str
    final_status: str
    attempts_consumed: int
    consumed_indices: tuple[int, ...]
    research_only_indices: tuple[int, ...]
    prior_failure_indices: tuple[int, ...] = ()
    report_flag: str | None = None
    indeterminate_reason: str | None = None

    @property
    def is_decided(self) -> bool:
        return self.final_status in (ACCEPT, BLOCK)


def _validate(policy: str, exit_statuses: Sequence[int | None]) -> None:
    if policy not in POLICIES:
        raise PolicyError(
            f"unknown policy {policy!r}; E1 defines exactly {POLICIES}. "
            "Selection and quarantine are out of scope for this experiment."
        )
    for position, status in enumerate(exit_statuses, start=1):
        if status is None:
            continue  # a missing or harness-invalid attempt
        if isinstance(status, bool) or not isinstance(status, int):
            raise PolicyError(
                f"attempt {position}: a policy reads only an integer exit status, "
                f"got {status!r}. Oracle categories are evaluator-only (plan 4.2)."
            )


def _indeterminate(policy: str, consumed: list[int], total: int, reason: str) -> Decision:
    return Decision(
        policy=policy,
        final_status=INDETERMINATE,
        attempts_consumed=len(consumed),
        consumed_indices=tuple(consumed),
        research_only_indices=tuple(range(len(consumed) + 1, total + 1)),
        indeterminate_reason=reason,
    )


def reduce_block(policy: str, exit_statuses: Sequence[int | None]) -> Decision:
    """Reduce one version's recorded attempts to `policy`'s decision.

    `exit_statuses` is the block's attempts in execution order: 0 for a pass,
    nonzero for a failure, and `None` for an attempt that is missing or was
    ruled `HARNESS_INVALID`. Attempts beyond the policy's stopping point may be
    present; they are returned as `research_only_indices` and ignored.
    """
    statuses = list(exit_statuses)
    _validate(policy, statuses)
    total = len(statuses)
    budget = 1 if policy == P1 else RETRY_BUDGET

    consumed: list[int] = []
    failures: list[int] = []

    for index in range(1, min(budget, total) + 1):
        status = statuses[index - 1]
        if status is None:
            consumed.append(index)
            return _indeterminate(
                policy,
                consumed,
                total,
                f"attempt {index} is missing or harness-invalid, "
                "so the policy's decision is undetermined",
            )
        consumed.append(index)
        if status == 0:
            return _accept(policy, consumed, failures, total)
        failures.append(index)

    if len(consumed) < budget:
        return _indeterminate(
            policy,
            consumed,
            total,
            f"only {len(consumed)} of {budget} attempts were recorded; "
            "a truncated block is not a block",
        )

    return Decision(
        policy=policy,
        final_status=BLOCK,
        attempts_consumed=len(consumed),
        consumed_indices=tuple(consumed),
        research_only_indices=tuple(range(len(consumed) + 1, total + 1)),
        prior_failure_indices=tuple(failures),
    )


def _accept(
    policy: str, consumed: list[int], failures: list[int], total: int
) -> Decision:
    flag = ACCEPT_WITH_PRIOR_FAILURE if (policy == P3_RETAIN and failures) else None
    return Decision(
        policy=policy,
        final_status=ACCEPT,
        attempts_consumed=len(consumed),
        consumed_indices=tuple(consumed),
        research_only_indices=tuple(range(len(consumed) + 1, total + 1)),
        prior_failure_indices=tuple(failures),
        report_flag=flag,
    )


def _prefix_categories(
    decision: Decision, categories: Sequence[Iterable[str]]
) -> list[frozenset[str]]:
    if len(categories) < decision.attempts_consumed:
        raise PolicyError(
            f"{decision.attempts_consumed} attempts were consumed but only "
            f"{len(categories)} category sets were supplied; the adjudication is "
            "incomplete for this block"
        )
    prefix = []
    for index in decision.consumed_indices:
        annotation = frozenset(categories[index - 1])
        unknown = annotation - CATEGORIES
        if unknown:
            raise PolicyError(f"attempt {index}: unknown categories {sorted(unknown)}")
        prefix.append(annotation)
    return prefix


def focal_evidence_in_prefix(
    decision: Decision, categories: Sequence[Iterable[str]]
) -> bool:
    """Does this block's *blocking* outcome rest on focal-defect evidence?

    This is the per-block indicator behind `S` (plan 4.5): the final outcome must
    be a block, and a focal witness must appear in the attempts the policy
    actually consumed. A witness in the research-only suffix does not count -
    the policy never saw it - and an unrelated red outcome is not focal
    detection.
    """
    if decision.final_status != BLOCK:
        return False
    return any(FOCAL_DEFECT_WITNESS in a for a in _prefix_categories(decision, categories))


def blocked_solely_by_nuisance(
    decision: Decision, categories: Sequence[Iterable[str]]
) -> bool:
    """Is this block's blocking outcome caused *only* by verified nuisance?

    The per-block indicator behind `N` (plan 4.5). An acceptable-version failure
    is not automatically a false alarm: every consumed failing attempt must be
    independently verified nuisance. An `UNRESOLVED` attempt, another real
    defect, or a focal witness anywhere in the prefix disqualifies the block.
    """
    if decision.final_status != BLOCK:
        return False
    prefix = _prefix_categories(decision, categories)
    failing = [prefix[i - 1] for i in decision.prior_failure_indices]
    if not failing:
        return False
    return all(a == {VERIFIED_NUISANCE} for a in failing)
