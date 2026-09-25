"""C1 oracle registry: E1's three frozen cards plus three ported cards.

The three E1 cards (etcd5509, etcd7492, grpc1859) are imported unchanged from
`e1_harness/oracle.py`. The three added here transcribe, without strengthening
or weakening, the pre-declared signatures of cards C-04, C-05 and C-06 and the
shell classifiers that applied them in Q0 (`task5_artifacts/<subject>/run/attempt.sh`).
Where the card text and the shell rule differ, the difference is noted on the
card and the replay report shows whether it ever mattered on real output.

Classification reuses `oracle.classify` unchanged, so every C1 attempt is
judged by the same HARNESS_INVALID / PASS / focal / UNRESOLVED procedure as E1.
Each annotation records the hashes of both files that define the rules.

Source review for generic CPU slowness (protocol 3), recorded here so the rule
and its known limits travel together:

- grpc2391 (a) needs `DeadlineExceeded` on one of the ten `UnaryCall`s. Their
  context is created at test start with 20 s for the whole test (dial, stream,
  GracefulStop, reconnection, ten calls); a passing run takes about 0.01 s. A
  non-defect match would need roughly a 2000x slowdown; the witness itself
  cannot tell such a slowdown from the spin.
- istio17860 (a) needs epoch 1 not started 5 s after epoch 0's exit is sent: a
  handful of goroutine hand-offs, about 0.5 s in a passing run. The separate
  1 s `BeTemporally` assertion is the timing-sensitive one and is non-focal.
- k8s26980 (a) needs the locker goroutine not to acquire an unheld mutex within
  30 s (`wait.ForeverTestTimeout`). No positive log exists; the rule is
  validated by source review only.

Under the 2-CPU quota a throttled cgroup pauses for at most about one 100 ms
period at a time, orders of magnitude below these bounds. That is a source
argument, not a runtime observation; a match on an acceptable variant still
triggers the pair-validity procedure, never automatic attribution.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Iterable, Sequence

import oracle as e1_oracle
from oracle import Evidence, OracleCard, OracleError, Signature, classify

CARDS_VERSION = "c1-cards/1"

_GRPC2391_A = re.compile(
    r"UnaryCall\(_\) = _, rpc error: code = DeadlineExceeded.*; want _, nil"
)


def _grpc2391_spin(ev: Evidence) -> bool:
    return bool(_GRPC2391_A.search(ev.text))


GRPC2391 = OracleCard(
    episode="grpc2391",
    test_name="TestGoAwayThenClose",
    source=(
        "research_runs/ci_sensitivity_2026_09/task_c3_candidate_acquisition.md card C-04 "
        "'Pre-declared evaluator signatures' (a); applied in Q0 by "
        "task5_artifacts/grpc2391/run/attempt.sh; unchanged by exploratory runs "
        "(task5_grpc2391_restoration.md Step 3)"
    ),
    signatures=(
        Signature(
            "a",
            "a `UnaryCall(_) = _, rpc error: code = DeadlineExceeded ...; want _, nil` line: "
            "a call issued after connection 1's closure did not complete within the "
            "test's 20 s context",
            _grpc2391_spin,
        ),
    ),
    notes=(
        "Card text requires one line carrying both the UnaryCall form and "
        "DeadlineExceeded; the Q0 shell rule grepped the two fragments separately. "
        "The line rule is the card's and is the stricter of the two.",
        "Everything else, including a leakcheck report without an (a) line, is not focal.",
    ),
)


def _istio17860_stalled_exit(ev: Evidence) -> bool:
    return bool(
        re.search(r"^\s*--- FAIL: TestExitDuringWaitForLive\b", ev.text, re.M)
        and "timed out waiting for epoch 1 to start" in ev.text
    )


ISTIO17860 = OracleCard(
    episode="istio17860",
    test_name="TestExitDuringWaitForLive",
    source=(
        "research_runs/ci_sensitivity_2026_09/task_c3_candidate_acquisition.md card C-05 "
        "'Pre-declared evaluator signatures' (a); applied in Q0 by "
        "task5_artifacts/istio17860/run/attempt.sh; unchanged by exploratory runs"
    ),
    signatures=(
        Signature(
            "a",
            "`--- FAIL: TestExitDuringWaitForLive` together with "
            "`timed out waiting for epoch 1 to start`",
            _istio17860_stalled_exit,
        ),
    ),
    notes=(
        "A Gomega BeTemporally failure (epoch 1 started, but outside 1 s) is "
        "UNRESOLVED on either version; it matches no signature, so classify() "
        "already returns UNRESOLVED for it.",
    ),
)


def _k8s26980_lock_held(ev: Evidence) -> bool:
    return bool(
        re.search(r"^\s*--- FAIL: TestPopReleaseLock\b", ev.text, re.M)
        and "Timeout after 30s" in ev.text
    )


K8S26980 = OracleCard(
    episode="k8s26980",
    test_name="TestPopReleaseLock",
    source=(
        "research_runs/ci_sensitivity_2026_09/task_c4_candidate_acquisition.md card C-06 "
        "'Pre-declared evaluator signatures' (a); applied in Q0 by "
        "task5_artifacts/k8s26980/run/attempt.sh"
    ),
    signatures=(
        Signature(
            "a",
            "`--- FAIL: TestPopReleaseLock` together with `Timeout after 30s`",
            _k8s26980_lock_held,
        ),
    ),
    notes=(
        "No focal witness has ever been observed (Q0 0/20 + 0/5 exploratory). "
        "The rule is validated on source review and synthetic parsing fixtures only.",
        "A Go test-timeout dump or panic is UNRESOLVED, per the card.",
    ),
)

CARDS: dict[str, OracleCard] = {**e1_oracle.CARDS, **{c.episode: c for c in (GRPC2391, ISTIO17860, K8S26980)}}
"""All six C1 cards. The E1 entries are the same objects E1 used."""


def _normalized_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def rule_hashes() -> dict[str, str]:
    return {
        "e1_oracle_py": e1_oracle.oracle_sha256(),
        "c1_cards_py": _normalized_sha256(Path(__file__)),
    }


def card_for(subject: str) -> OracleCard:
    try:
        return CARDS[subject]
    except KeyError:
        raise OracleError(f"no C1 oracle card for {subject!r}") from None


def annotate(
    records: Iterable[dict[str, Any]],
    overrides: dict[str, dict[str, Any]] | None = None,
    card_subject: Any = None,
) -> list[dict[str, Any]]:
    """One annotation per ledger record, in ledger order (mirrors `oracle.annotate`).

    `card_subject(row)` picks the card; by default the record's `episode`.
    Identity-control attempts carry their real subject in `episode`.
    """
    overrides = dict(overrides or {})
    hashes = rule_hashes()
    out = []
    for row in records:
        subject = card_subject(row) if card_subject else row["episode"]
        card = card_for(subject)
        mech = classify(card, row["exit_status"], row["stdout"], row["stderr"])
        annotation: dict[str, Any] = {
            **{k: row[k] for k in ("episode", "block", "version", "attempt")},
            "attempt_id": (row.get("extra") or {}).get("attempt_id"),
            "record_seq": row["seq"],
            "record_sha256": row["sha256"],
            "categories": sorted(mech.categories),
            "signatures": list(mech.signatures),
            "reason": mech.reason,
            "source": e1_oracle.MECHANICAL,
            "oracle_version": f"{e1_oracle.ORACLE_VERSION}+{CARDS_VERSION}",
            "oracle_sha256": hashes["e1_oracle_py"],
            "cards_sha256": hashes["c1_cards_py"],
        }
        override = overrides.pop(row["sha256"], None)
        if override is not None:
            annotation.update(
                categories=sorted(set(override["categories"])),
                source=e1_oracle.OVERRIDE,
                mechanical=sorted(mech.categories),
                mechanical_reason=mech.reason,
                override={k: override[k] for k in ("adjudicator", "reason", "evidence")},
            )
        out.append(annotation)
    if overrides:
        raise OracleError("overrides name records absent from the ledger: " + ", ".join(k[:12] for k in overrides))
    return out


def classify_text(subject: str, exit_status: int | None, stdout: str, stderr: str = "") -> Sequence[str]:
    """Convenience for replay and live validity alarms: sorted mechanical categories."""
    return sorted(classify(card_for(subject), exit_status, stdout, stderr).categories)
