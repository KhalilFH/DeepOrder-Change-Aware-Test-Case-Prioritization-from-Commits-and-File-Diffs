"""E1 oracle classifier: turn one recorded attempt into its evaluator categories.

This is the evaluator step the runner deliberately does not perform (plan 4.2:
"Oracle adjudication uses the obligation and witness, not whether the policy
was green"). It reads the ledger, never writes to it, and knows nothing about
policies: it classifies each attempt on its own raw output, so adjudication
cannot be steered by the policy-comparison summary (plan, Experiment 1,
"Oracle").

Three rules are enforced here rather than left to judgement at run time:

**Signatures are frozen per episode, as code.** Each `OracleCard` transcribes
the pre-declared witness signature from the episode's restoration record, with
a pointer to that record. The file's own hash is written on every annotation,
so any later edit to a signature is visible in the output rather than silent.

**Only a declared signature makes a focal witness.** A timeout, a panic or a
red exit that matches no signature is `UNRESOLVED`. That includes failures
that look like some other defect: `OTHER_DEFECT` and `VERIFIED_NUISANCE` both
assert something about the world (a real second defect; an independently
identified test/harness artifact) that output-matching cannot establish. They
enter only as a researcher's override, with the reason and evidence recorded
beside the mechanical label it replaces (plan 4.1, "Nuisance requires its own
evidence").

**An attempt whose target did not demonstrably run is `HARNESS_INVALID`.**
No exit status (runner ceiling hit, container never started), a Docker-level
failure, a missing `=== RUN` line for the frozen test, or a skipped test. Such
an attempt says nothing about either revision. The reducer already treats
`None` as missing-or-invalid, and the analysis maps this category to `None`.

Stdlib only, like the rest of the harness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from ledger import read_records, verify_chain
from policy import (
    CATEGORIES,
    FOCAL_DEFECT_WITNESS,
    HARNESS_INVALID,
    PASS,
    UNRESOLVED,
)

ORACLE_VERSION = "e1-oracle/1"

MECHANICAL = "mechanical"
OVERRIDE = "override"

DOCKER_HARNESS_EXITS = frozenset({125, 126, 127})
"""`docker run` itself failed, or the command could not be invoked or found."""

DOCKER_ERROR_MARKERS = (
    "docker: Error response from daemon",
    "Cannot connect to the Docker daemon",
    "Unable to find image",
    "OCI runtime create failed",
)


def oracle_sha256() -> str:
    """This file's hash, line endings normalised so a checkout does not change it."""
    raw = Path(__file__).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


class OracleError(ValueError):
    """The classifier's contract was violated."""


# --- Go goroutine dumps -----------------------------------------------------

_GOROUTINE_HEADER = re.compile(r"goroutine (\d+) \[([^\]]+)\]:\s*$")


@dataclass(frozen=True)
class Goroutine:
    """One goroutine of a Go stack dump: its wait state and function frames."""

    gid: int
    state: str
    functions: tuple[str, ...]

    def calls(self, name: str) -> bool:
        """Some frame's function name contains `name` (e.g. `(*Client).Close`)."""
        return any(name in f for f in self.functions)


def parse_goroutines(text: str) -> list[Goroutine]:
    """Every goroutine in `text`, in dump order.

    Tolerates a prefix before the header, as in leakcheck's `Leaked goroutine:
    goroutine 12 [select]:`. Frame lines are the untabbed function lines; the
    tab-indented file:line lines are dropped, because a line number is not
    diagnostic across builds while the call-site identity is. `created by`
    lines are kept as frames.
    """
    out: list[Goroutine] = []
    current: tuple[int, str] | None = None
    frames: list[str] = []

    def close() -> None:
        if current is not None:
            out.append(Goroutine(current[0], current[1], tuple(frames)))

    for line in text.splitlines():
        header = _GOROUTINE_HEADER.search(line)
        if header:
            close()
            current, frames = (int(header.group(1)), header.group(2)), []
            continue
        if current is None:
            continue
        if not line.strip():
            close()
            current, frames = None, []
        elif not line.startswith(("\t", " ")):
            frames.append(_function_name(line))
    close()
    return out


def _function_name(frame_line: str) -> str:
    line = frame_line.strip()
    if line.startswith("created by "):
        return line  # keep the marker; the spawning function follows it
    return line.rsplit("(", 1)[0] if line.endswith(")") else line


# --- the evidence a signature is evaluated against --------------------------


@dataclass(frozen=True)
class Evidence:
    """Everything a signature may read about one attempt."""

    exit_status: int | None
    text: str
    timed_out_in_test: bool
    runtime_panic: bool
    goroutines: tuple[Goroutine, ...]

    @property
    def panicking(self) -> Goroutine | None:
        """The goroutine a non-timeout panic was raised on: first in the dump."""
        return self.goroutines[0] if (self.runtime_panic and self.goroutines) else None


_TEST_TIMEOUT = re.compile(r"^panic: test timed out after ", re.M)
_RUNTIME_PANIC = re.compile(r"^panic: (?!test timed out after )", re.M)


def gather(stdout: str, stderr: str, exit_status: int | None) -> Evidence:
    text = f"{stdout}\n{stderr}"
    return Evidence(
        exit_status=exit_status,
        text=text,
        timed_out_in_test=bool(_TEST_TIMEOUT.search(text)),
        runtime_panic=bool(_RUNTIME_PANIC.search(text)),
        goroutines=tuple(parse_goroutines(text)),
    )


# --- frozen oracle cards ----------------------------------------------------


@dataclass(frozen=True)
class Signature:
    """A pre-declared focal-witness signature. `matches` reads only `Evidence`."""

    sid: str
    summary: str
    matches: Callable[[Evidence], bool]


@dataclass(frozen=True)
class OracleCard:
    episode: str
    test_name: str
    source: str
    signatures: tuple[Signature, ...]
    notes: tuple[str, ...] = field(default=())


def _test_goroutine(ev: Evidence, test_function: str) -> Goroutine | None:
    """The goroutine running the test function itself, not a closure it spawned."""
    for g in ev.goroutines:
        if g.calls("testing.tRunner") and any(
            f.endswith(test_function) for f in g.functions
        ):
            return g
    return None


def _etcd5509_hang(ev: Evidence) -> bool:
    if not ev.timed_out_in_test:
        return False
    test = _test_goroutine(ev, "integration.TestKVGetErrConnClosed")
    if test is None or not test.calls("clientv3.(*Client).Close"):
        return False
    # (i) Close's own second Lock hangs on the test goroutine.
    if test.calls("sync.(*RWMutex).Lock"):
        return True
    # (ii) Close waits on a channel while connMonitor hangs on the same mutex.
    if not test.state.startswith("chan receive"):
        return False
    return any(
        g.gid != test.gid
        and g.calls("sync.(*RWMutex).Lock")
        and g.calls("clientv3.(*Client).connMonitor")
        for g in ev.goroutines
    )


def _etcd5509_panic(ev: Evidence) -> bool:
    g = ev.panicking
    if g is None:
        return False
    on_closed_client = g.calls("clientv3.(*remoteClient).") or g.calls("clientv3.(*kv).Get")
    return on_closed_client and g.calls("TestKVGetErrConnClosed")


ETCD5509 = OracleCard(
    episode="etcd5509",
    test_name="TestKVGetErrConnClosed",
    source=(
        "research_runs/ci_sensitivity_2026_09/task5_etcd5509_restoration.md, "
        "Step 3b 'Final signature (a)'; signature (b) from "
        "task_c_candidate_acquisition.md card C-01, unchanged by Step 3b"
    ),
    signatures=(
        Signature(
            "a",
            "test timeout; the TestKVGetErrConnClosed goroutine is in "
            "(*Client).Close and either (i) itself blocked in RWMutex.Lock, or "
            "(ii) in a chan receive while a distinct goroutine is blocked in "
            "RWMutex.Lock via (*Client).connMonitor",
            _etcd5509_hang,
        ),
        Signature(
            "b",
            "runtime panic whose panicking goroutine passes through "
            "remoteClient/kv.Get within TestKVGetErrConnClosed",
            _etcd5509_panic,
        ),
    ),
    notes=(
        "Signature (a) was corrected twice during Q0; the second correction "
        "came after 10 counted attempts and is disclosed in the restoration "
        "record. This card is the final text only.",
        "Signature (b) never occurred in Q0, so it is unvalidated on real output.",
    ),
)

_KEEPER_SENDS = (
    "(*simpleTokenTTLKeeper).addSimpleToken",
    "(*simpleTokenTTLKeeper).resetSimpleToken",
    "(*simpleTokenTTLKeeper).deleteSimpleToken",
)
_TOKEN_CALLERS = (
    "(*tokenSimple).assignSimpleTokenToUser",
    "(*tokenSimple).info",
    "(*tokenSimple).invalidateUser",
)
_LOCKS = ("sync.(*Mutex).Lock", "sync.(*RWMutex).Lock", "sync.(*RWMutex).RLock")


def _etcd7492_hang(ev: Evidence) -> bool:
    if not ev.timed_out_in_test:
        return False
    keepers = [
        g
        for g in ev.goroutines
        if g.calls("(*simpleTokenTTLKeeper).run")
        and any(g.calls(lock) for lock in _LOCKS)
        and (g.calls("newDeleterFunc") or g.calls("deleteTokenFunc"))
    ]
    if not keepers:
        return False
    keeper_ids = {g.gid for g in keepers}
    for g in ev.goroutines:
        if g.gid in keeper_ids or not any(g.calls(c) for c in _TOKEN_CALLERS):
            continue
        sending = g.state.startswith("chan send") and any(g.calls(s) for s in _KEEPER_SENDS)
        locking = g.state.startswith("semacquire") and any(g.calls(lock) for lock in _LOCKS)
        if sending or locking:
            return True
    return False


ETCD7492 = OracleCard(
    episode="etcd7492",
    test_name="TestHammerSimpleAuthenticate",
    source=(
        "research_runs/ci_sensitivity_2026_09/task_c_candidate_acquisition.md "
        "card C-02 'Pre-declared evaluator signature'; confirmed without "
        "correction in task5_etcd7492_restoration.md Step 3"
    ),
    signatures=(
        Signature(
            "a",
            "test timeout; a goroutine in tokenSimple.assignSimpleTokenToUser/"
            "info/invalidateUser blocked sending to a TTL-keeper channel (or "
            "acquiring a mutex), and a distinct simpleTokenTTLKeeper.run "
            "goroutine blocked in a mutex Lock via deleteTokenFunc",
            _etcd7492_hang,
        ),
    ),
)

_GRPC_WRITERS = ("transport.(*http2Client).Write", "transport.(*http2Server).Write")
_GRPC_DEADLINE = re.compile(r"code = DeadlineExceeded.*want code: ResourceExhausted")


def _grpc1859_deadline(ev: Evidence) -> bool:
    return bool(_GRPC_DEADLINE.search(ev.text))


def _grpc1859_stack(ev: Evidence) -> bool:
    if not (ev.timed_out_in_test or "Leaked goroutine" in ev.text):
        return False
    return any(
        g.calls("transport.(*quotaPool).get") and any(g.calls(w) for w in _GRPC_WRITERS)
        for g in ev.goroutines
    )


GRPC1859 = OracleCard(
    episode="grpc1859",
    test_name="TestClientDoesntDeadlockWhileWritingErrornousLargeMessages",
    source=(
        "research_runs/ci_sensitivity_2026_09/task_c2_candidate_acquisition.md "
        "card C-03 'Pre-declared evaluator signatures'; frozen_protocol.txt"
    ),
    signatures=(
        Signature(
            "a",
            "a DeadlineExceeded line with 'want code: ResourceExhausted'",
            _grpc1859_deadline,
        ),
        Signature(
            "b",
            "test timeout or leakcheck report with a goroutine in "
            "quotaPool.get called from http2Client/http2Server.Write",
            _grpc1859_stack,
        ),
    ),
    notes=(
        "Q0_NOT_QUALIFIED: a named non-primary case, not an E1 subject. The "
        "card is kept so the classifier is validated on a non-hang witness.",
    ),
)

CARDS: dict[str, OracleCard] = {c.episode: c for c in (ETCD5509, ETCD7492, GRPC1859)}


def card_for(episode: str) -> OracleCard:
    try:
        return CARDS[episode]
    except KeyError:
        raise OracleError(
            f"no frozen oracle card for episode {episode!r}; an attempt is never "
            "classified without its episode's pre-declared signatures"
        ) from None


# --- classification ---------------------------------------------------------


@dataclass(frozen=True)
class Adjudication:
    categories: frozenset[str]
    signatures: tuple[str, ...]
    reason: str


def _one(category: str, reason: str, signatures: Sequence[str] = ()) -> Adjudication:
    return Adjudication(frozenset({category}), tuple(signatures), reason)


def classify(
    card: OracleCard, exit_status: int | None, stdout: str, stderr: str
) -> Adjudication:
    """Classify one attempt's raw output against `card`'s frozen signatures."""
    if exit_status is None:
        return _one(
            HARNESS_INVALID,
            "no exit status: the runner's ceiling fired or the attempt never ran, "
            "so no in-test evidence (such as a goroutine dump) was produced",
        )

    ev = gather(stdout, stderr, exit_status)
    test = re.escape(card.test_name)

    if exit_status in DOCKER_HARNESS_EXITS or any(m in ev.text for m in DOCKER_ERROR_MARKERS):
        return _one(HARNESS_INVALID, f"container or command failure (exit {exit_status})")
    if not re.search(rf"^=== RUN\s+{test}\s*$", ev.text, re.M):
        return _one(
            HARNESS_INVALID,
            f"no '=== RUN {card.test_name}' line: the frozen target's execution "
            "is not established (is -test.v in the frozen argv?)",
        )
    if re.search(rf"^\s*--- SKIP: {test}\b", ev.text, re.M):
        return _one(HARNESS_INVALID, "the frozen target was skipped")

    reported_pass = bool(re.search(rf"^\s*--- PASS: {test}\b", ev.text, re.M))
    reported_fail = bool(re.search(rf"^\s*--- FAIL: {test}\b", ev.text, re.M))
    abnormal = ev.timed_out_in_test or ev.runtime_panic

    if exit_status == 0:
        if reported_pass and not reported_fail and not abnormal:
            return _one(PASS, "exit 0 and the target reported PASS")
        return _one(UNRESOLVED, "exit 0 but the output does not show a clean PASS")

    matched = [s.sid for s in card.signatures if s.matches(ev)]
    if matched:
        return _one(
            FOCAL_DEFECT_WITNESS,
            "matched frozen signature " + ", ".join(matched),
            matched,
        )
    if ev.timed_out_in_test:
        mode = "test timeout whose goroutine dump matches no frozen signature"
    elif ev.runtime_panic:
        mode = "runtime panic matching no frozen signature"
    elif reported_fail:
        mode = "target reported FAIL matching no frozen signature"
    elif reported_pass:
        mode = "nonzero exit although the target reported PASS"
    else:
        mode = "nonzero exit with no recognised failure form"
    return _one(UNRESOLVED, f"{mode} (exit {exit_status})")


# --- annotations and researcher overrides -----------------------------------


def _record_identity(row: dict[str, Any]) -> dict[str, Any]:
    return {k: row[k] for k in ("episode", "block", "version", "attempt")}


def load_overrides(path: str | Path | None) -> dict[str, dict[str, Any]]:
    """Researcher adjudications, keyed by the ledger record's sha256.

    Each JSONL row: `record_sha256`, `categories`, `adjudicator`, `reason`,
    `evidence`. Reason and evidence are mandatory: an override is a claim
    about the world and must say what supports it.
    """
    if path is None:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in read_records(path):
        key = row.get("record_sha256")
        cats = row.get("categories")
        if not key or not isinstance(cats, list) or not cats:
            raise OracleError(f"override {row!r} needs record_sha256 and categories")
        unknown = set(cats) - CATEGORIES
        if unknown:
            raise OracleError(f"override for {key[:12]}: unknown categories {sorted(unknown)}")
        for required in ("adjudicator", "reason", "evidence"):
            if not str(row.get(required, "")).strip():
                raise OracleError(f"override for {key[:12]} has no {required}")
        if key in out:
            raise OracleError(f"two overrides for record {key[:12]}")
        out[key] = row
    return out


def annotate(
    records: Iterable[dict[str, Any]],
    overrides: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """One annotation per ledger record, in ledger order.

    Every override must name a record in this ledger; an unused override is an
    error, because it means the adjudication and the observations disagree
    about which attempts exist.
    """
    overrides = dict(overrides or {})
    digest = oracle_sha256()
    out = []
    for row in records:
        card = card_for(row["episode"])
        mech = classify(card, row["exit_status"], row["stdout"], row["stderr"])
        annotation: dict[str, Any] = {
            **_record_identity(row),
            "record_seq": row["seq"],
            "record_sha256": row["sha256"],
            "categories": sorted(mech.categories),
            "signatures": list(mech.signatures),
            "reason": mech.reason,
            "source": MECHANICAL,
            "oracle_version": ORACLE_VERSION,
            "oracle_sha256": digest,
        }
        override = overrides.pop(row["sha256"], None)
        if override is not None:
            annotation.update(
                categories=sorted(set(override["categories"])),
                source=OVERRIDE,
                mechanical=sorted(mech.categories),
                mechanical_reason=mech.reason,
                override={
                    k: override[k] for k in ("adjudicator", "reason", "evidence")
                },
            )
        out.append(annotation)
    if overrides:
        missing = ", ".join(k[:12] for k in overrides)
        raise OracleError(f"overrides name records absent from the ledger: {missing}")
    return out


def write_annotations(path: str | Path, annotations: Sequence[dict[str, Any]], replace: bool) -> None:
    p = Path(path)
    body = "".join(
        json.dumps(a, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        for a in annotations
    )
    if p.exists() and not replace and p.read_text(encoding="utf-8") != body:
        raise OracleError(
            f"{p} exists with different content; pass --replace to regenerate it"
        )
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8", newline="\n")


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ledger", required=True, help="attempts.jsonl written by the runner")
    ap.add_argument("--out", required=True, help="annotations.jsonl to write")
    ap.add_argument("--overrides", help="researcher adjudications (JSONL)")
    ap.add_argument("--replace", action="store_true", help="regenerate an existing output")
    args = ap.parse_args(argv)

    verify_chain(args.ledger)
    annotations = annotate(read_records(args.ledger), load_overrides(args.overrides))
    write_annotations(args.out, annotations, args.replace)

    counts: dict[tuple[str, str, str], int] = {}
    for a in annotations:
        key = (a["episode"], a["version"], "+".join(a["categories"]))
        counts[key] = counts.get(key, 0) + 1
    for (episode, version, cats), n in sorted(counts.items()):
        print(f"{episode:10} {version:6} {cats:28} {n}")
    print(f"{len(annotations)} attempts annotated -> {args.out} ({ORACLE_VERSION})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
