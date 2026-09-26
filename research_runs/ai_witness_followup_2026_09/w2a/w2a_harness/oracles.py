"""Frozen per-case focal oracles and primitive-attempt classification.

The validator (never a method process) classifies each primitive attempt as
PASS, FOCAL_FAILURE, NONFOCAL_FAILURE, UNRESOLVED or HARNESS_INVALID
(NOT_RUN is assigned by the scheduler). A FOCAL_FAILURE needs a failing
attempt plus a frozen rule that finds BOTH premise evidence and consequence
evidence, each as locators into the immutable trace (``trace:<sha>:L<a>-L<b>``)
or, for statically established premises of *unchanged* supplied tests, into
frozen source (``source:<path>@<sha>:L<a>-L<b>``). Exit codes, arbitrary
assertion text and elapsed timeouts are never sufficient on their own.

Evidence classes are runtime-produced text the edit contract forbids tests to
imitate: Go goroutine dumps (test-timeout panic, the harness TestMain dump, or
test-printed runtime.Stack), JVM ``-Xlog:exceptions`` records and W1Runner
thread dumps, and production-formatted gRPC status strings.

Rules (specification: private_oracles/<case>/ORACLE.md):

* pool162.R1  InterruptedException thrown in Generic[Keyed]ObjectPool.borrowObject, then
              later in the same failing test NoSuchElementException("Timeout waiting for idle
              object") thrown in borrowObject of the same class.
* pool162.R2  inner timeout inside a selected test after the R1 premise, with the timeout
              thread dump showing a thread waiting (Object.wait) inside borrowObject of that class.
* grpc1859.R1 the UNCHANGED supplied focal test fails with a production-formatted
              DeadlineExceeded status where ResourceExhausted is required; premise is the frozen
              source binding (1 KiB server receive limit, 1 MiB payloads: every call takes the
              oversized-write error path).
* grpc1859.R2 a failing attempt whose goroutine dump shows a writer blocked in
              (*quotaPool).get called from http2Client/http2Server.Write at the transport-quota
              call site, with premise = the unchanged supplied test, or a production-formatted
              ResourceExhausted "message larger than max" status in the trace.
* k8s26980.R1 a failing attempt whose single goroutine dump shows pop blocked at its delivering
              select (premise) and another goroutine in sync.(*Mutex).Lock called from the
              framework package, blocked in semacquire (consequence).
* istio17860.R1 a failing attempt whose single goroutine dump shows (*agent).waitUntilLive
              under Restart (premise) and (*agent).Run blocked in sync.(*Mutex).Lock (consequence).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .casespec import CaseSpec
from .common import sha256_text
from . import static_extract

ORACLE_VERSION = "w1-oracle/1"

PASS = "PASS"
FOCAL = "FOCAL_FAILURE"
NONFOCAL = "NONFOCAL_FAILURE"
UNRESOLVED = "UNRESOLVED"
HARNESS_INVALID = "HARNESS_INVALID"
NOT_RUN = "NOT_RUN"
ATTEMPT_STATUSES = (PASS, FOCAL, NONFOCAL, UNRESOLVED, HARNESS_INVALID, NOT_RUN)


@dataclass
class AttemptClass:
    status: str
    reason: str
    rule_id: str | None = None
    premise_evidence: list[str] = field(default_factory=list)
    consequence_evidence: list[str] = field(default_factory=list)
    test_results: dict[str, str] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "reason": self.reason, "rule_id": self.rule_id,
                "premise_evidence": self.premise_evidence, "consequence_evidence": self.consequence_evidence,
                "test_results": self.test_results, "details": self.details, "oracle_version": ORACLE_VERSION}


# --------------------------------------------------------------------------- parsing

@dataclass
class Goroutine:
    gid: int
    state: str
    start: int  # 1-based line in trace
    end: int
    frames: list[tuple[str, str]]  # (function line, file:line)


def parse_goroutine_dumps(lines: list[str]) -> list[list[Goroutine]]:
    """Group goroutine blocks into dumps (a repeated goroutine id or a gap > 2 lines starts a new dump)."""
    head = re.compile(r"^goroutine (\d+) \[([^\]]+)\]:\s*$")
    dumps: list[list[Goroutine]] = []
    current: list[Goroutine] = []
    i = 0
    while i < len(lines):
        m = head.match(lines[i])
        if not m:
            i += 1
            continue
        start = i
        frames: list[tuple[str, str]] = []
        i += 1
        while i < len(lines) and lines[i].strip() and not head.match(lines[i]):
            fn = lines[i]
            loc = lines[i + 1].strip() if i + 1 < len(lines) and lines[i + 1].startswith("\t") else ""
            if fn.startswith("\t"):
                i += 1
                continue
            frames.append((fn.strip(), loc))
            i += 2 if loc else 1
        g = Goroutine(int(m.group(1)), m.group(2), start + 1, i, frames)
        if current and (any(x.gid == g.gid for x in current) or g.start - current[-1].end > 3):
            dumps.append(current)
            current = []
        current.append(g)
    if current:
        dumps.append(current)
    return dumps


def go_test_results(lines: list[str]) -> tuple[dict[str, str], dict[str, int]]:
    results: dict[str, str] = {}
    where: dict[str, int] = {}
    pat = re.compile(r"^\s*--- (PASS|FAIL|SKIP): (\S+) \(")
    for n, line in enumerate(lines, 1):
        m = pat.match(line)
        if m and "/" not in m.group(2):
            results[m.group(2)] = m.group(1)
            where[m.group(2)] = n
    return results, where


@dataclass
class ExcRecord:
    line: int
    end: int
    exc_type: str
    message: str | None
    method: str | None
    klass: str | None


EXC_HEAD = re.compile(r"^\[[\d.]+s\]\[info\]\[exceptions\] (.*)$")
EXC_BODY = re.compile(
    r"Exception <a '([\w/$]+)'\{0x[0-9a-f]+\}(?:: (.*?))?>.*?thrown in (?:interpreter|compiled) method "
    r"<\{method\} \{0x[0-9a-f]+\} '([\w$<>]+)' '[^']*' in '([\w/$]+)'>", re.S)


def parse_exception_records(lines: list[str]) -> list[ExcRecord]:
    out: list[ExcRecord] = []
    i = 0
    while i < len(lines):
        m = EXC_HEAD.match(lines[i])
        if not m:
            i += 1
            continue
        start = i
        body = [m.group(1)]
        i += 1
        while i < len(lines) and lines[i].startswith(" ") and not EXC_HEAD.match(lines[i]):
            body.append(lines[i])
            i += 1
        text = "\n".join(body)
        bm = EXC_BODY.search(text)
        if bm:
            out.append(ExcRecord(start + 1, i, bm.group(1), bm.group(2), bm.group(3), bm.group(4)))
    return out


def java_windows(lines: list[str]) -> dict[str, dict[str, Any]]:
    """Per selected test: begin/end line and status from W1Runner markers."""
    wins: dict[str, dict[str, Any]] = {}
    for n, line in enumerate(lines, 1):
        if line.startswith("W1-TEST-BEGIN "):
            wins[line.split(" ", 1)[1].strip()] = {"begin": n, "end": None, "status": None}
        elif line.startswith("W1-TEST-END "):
            parts = line.split()
            if len(parts) >= 3 and parts[1] in wins:
                wins[parts[1]].update(end=n, status=parts[2])
    return wins


def java_thread_dumps(lines: list[str]) -> list[dict[str, Any]]:
    dumps = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("W1-THREAD-DUMP-BEGIN"):
            reason = lines[i].split(" ", 1)[1] if " " in lines[i] else ""
            start = i + 1
            threads = []
            j = i + 1
            cur = None
            while j < len(lines) and not lines[j].startswith("W1-THREAD-DUMP-END"):
                if lines[j].startswith('"'):
                    cur = {"header": lines[j], "line": j + 1, "frames": []}
                    threads.append(cur)
                elif lines[j].startswith("\tat ") and cur is not None:
                    cur["frames"].append((lines[j][4:].strip(), j + 1))
                j += 1
            dumps.append({"reason": reason, "start": start, "end": j + 1, "threads": threads})
            i = j + 1
        else:
            i += 1
    return dumps


# --------------------------------------------------------------------------- helpers

def loc(trace_sha: str, a: int, b: int | None = None) -> str:
    return f"trace:{trace_sha}:L{a}-L{b or a}"


def src_loc(path: str, content: str, a: int, b: int) -> str:
    return f"source:{path}@{sha256_text(content)}:L{a}-L{b}"


def _lines_of(content: str, needle: str) -> list[int]:
    return [n for n, l in enumerate(content.split("\n"), 1) if needle in l]


# --------------------------------------------------------------------------- rules

class CaseOracle:
    rule_ids: tuple[str, ...] = ()

    def __init__(self, spec: CaseSpec, packet_files: dict[str, str], originals: dict[str, str]):
        self.spec = spec
        self.files = packet_files
        self.originals = originals

    def focal(self, variant: str, lines: list[str], trace_sha: str, failing: list[str],
              final_sources: dict[str, str]) -> tuple[str, list[str], list[str]] | None:
        raise NotImplementedError

    def supplied_unchanged(self, test: str, final_sources: dict[str, str]) -> tuple[str, str, int, int] | None:
        """If ``test`` is a supplied entry point whose function text is unchanged, return its binding."""
        if test not in self.spec.entry_points:
            return None
        return self.function_unchanged(test.split("#")[-1], final_sources)

    def function_unchanged(self, name: str, final_sources: dict[str, str]) -> tuple[str, str, int, int] | None:
        for path, orig in self.originals.items():
            fs = [f for f in static_extract.functions(path, orig, self.spec.language) if f.name == name]
            if not fs:
                continue
            f = fs[0]
            before = "\n".join(orig.split("\n")[f.start - 1:f.end])
            now = final_sources.get(path, orig)
            gs = [g for g in static_extract.functions(path, now, self.spec.language) if g.name == f.name]
            if gs and "\n".join(now.split("\n")[gs[0].start - 1:gs[0].end]) == before:
                return path, orig, f.start, f.end
        return None


def _first_caller_after(frames: list[tuple[str, str]], fn_regex: str) -> tuple[int, str] | None:
    for k, (fn, _) in enumerate(frames):
        if re.search(fn_regex, fn):
            for fn2, _loc in frames[k + 1:]:
                if not fn2.startswith(("sync.", "runtime.")):
                    return k, fn2
            return k, ""
    return None


class Pool162Oracle(CaseOracle):
    rule_ids = ("pool162.R1", "pool162.R2")
    POOLS = ("org/apache/commons/pool/impl/GenericObjectPool", "org/apache/commons/pool/impl/GenericKeyedObjectPool")

    def focal(self, variant, lines, trace_sha, failing, final_sources):
        recs = parse_exception_records(lines)
        wins = java_windows(lines)
        dumps = java_thread_dumps(lines)
        timed_out = any(l.startswith("W1-INNER-TIMEOUT") for l in lines)
        for spec_name, w in sorted(wins.items(), key=lambda kv: kv[1]["begin"]):
            end = w["end"] or len(lines)
            ended_bad = w["status"] in ("FAIL", "ERROR")
            interrupted = w["end"] is None and timed_out
            if not (ended_bad or interrupted):
                continue
            in_win = [r for r in recs if w["begin"] < r.line < end]
            for pool in self.POOLS:
                prem = [r for r in in_win if r.exc_type == "java/lang/InterruptedException"
                        and r.method == "borrowObject" and r.klass == pool]
                if not prem:
                    continue
                p0 = prem[0]
                if ended_bad:
                    cons = [r for r in in_win if r.line > p0.line and r.exc_type == "java/util/NoSuchElementException"
                            and (r.message or "").strip() == "Timeout waiting for idle object"
                            and r.method == "borrowObject" and r.klass == pool]
                    if cons:
                        c0 = cons[0]
                        return ("pool162.R1", [loc(trace_sha, p0.line, p0.end)],
                                [loc(trace_sha, c0.line, c0.end), loc(trace_sha, w["end"])])
                if interrupted:
                    cls = pool.replace("/", ".")
                    for d in dumps:
                        if d["reason"] != "inner-timeout" or d["start"] < p0.line:
                            continue
                        for t in d["threads"]:
                            names = [f for f, _ in t["frames"]]
                            waits = any(f.startswith("java.lang.Object.wait") for f in names)
                            borrow = [(f, n) for f, n in t["frames"] if f.startswith(cls + ".borrowObject(")]
                            if waits and borrow and "WAITING" in t["header"]:
                                return ("pool162.R2", [loc(trace_sha, p0.line, p0.end)],
                                        [loc(trace_sha, t["line"], borrow[0][1])])
        return None


class Grpc1859Oracle(CaseOracle):
    rule_ids = ("grpc1859.R1", "grpc1859.R2")
    DEADLINE_LINE = re.compile(
        r"TestService/UnaryCall\(_,_\) = _\. rpc error: code = DeadlineExceeded desc = context deadline exceeded, "
        r"want code: ResourceExhausted")
    PREMISE_STATUS = re.compile(r"code = ResourceExhausted desc = grpc: (received|trying to send) message larger than max")

    def __init__(self, spec, packet_files, originals):
        super().__init__(spec, packet_files, originals)
        self.callsites: dict[str, dict[str, set[int]]] = {}
        for variant, prefix in (("V_bad", "defective"), ("V_ok", "repaired")):
            self.callsites[variant] = {
                side: set(_lines_of(packet_files[f"{prefix}/transport/http2_{side}.go"], "t.sendQuotaPool.get("))
                for side in ("client", "server")
            }

    HELPER = "testClientDoesntDeadlockWhileWritingErrornousLargeMessages"

    def _static_premise(self, final_sources) -> list[str] | None:
        """Premise bound to frozen source: entry function AND its per-env helper both unchanged."""
        if not self.supplied_unchanged(self.spec.entry_points[0], final_sources):
            return None
        b = self.function_unchanged(self.HELPER, final_sources)
        if not b:
            return None
        path, content, a, z = b
        spans = [n for n in _lines_of(content, "smallSize := 1024") + _lines_of(content, "te.maxServerReceiveMsgSize = &smallSize")
                 + _lines_of(content, "newPayload(testpb.PayloadType_COMPRESSABLE, 1048576)") if a <= n <= z]
        if len(spans) < 3:
            return None
        return [src_loc(path, content, n, n) for n in sorted(spans)]

    def focal(self, variant, lines, trace_sha, failing, final_sources):
        target = self.spec.entry_points[0]
        static_premise = self._static_premise(final_sources)
        if target in failing and static_premise:
            hits = [n for n, l in enumerate(lines, 1) if self.DEADLINE_LINE.search(l)]
            if hits:
                return ("grpc1859.R1", static_premise, [loc(trace_sha, hits[0])])
        dyn = [n for n, l in enumerate(lines, 1) if self.PREMISE_STATUS.search(l)]
        premise = static_premise if static_premise and target in failing else ([loc(trace_sha, dyn[0])] if dyn else None)
        if not premise:
            return None
        for dump in parse_goroutine_dumps(lines):
            for g in dump:
                for k, (fn, where) in enumerate(g.frames):
                    if not re.search(r"transport\.\(\*quotaPool\)\.get\(", fn) or k + 1 >= len(g.frames):
                        continue
                    caller, cloc = g.frames[k + 1]
                    m = re.search(r"transport\.\(\*http2(Client|Server)\)\.Write\(", caller)
                    lm = re.search(r"/transport/http2_(client|server)\.go:(\d+)", cloc)
                    if m and lm and int(lm.group(2)) in self.callsites[variant][lm.group(1)]:
                        return ("grpc1859.R2", premise, [loc(trace_sha, g.start, g.end)])
        return None


class K8s26980Oracle(CaseOracle):
    rule_ids = ("k8s26980.R1",)

    def __init__(self, spec, packet_files, originals):
        super().__init__(spec, packet_files, originals)
        self.deliver_select: dict[str, set[int]] = {}
        for variant, prefix in (("V_bad", "defective"), ("V_ok", "repaired")):
            text = packet_files[f"{prefix}/pkg/controller/framework/shared_informer.go"].split("\n")
            sends = [n for n, l in enumerate(text, 1) if "case p.nextCh <- notification:" in l]
            sel = set()
            for s in sends:
                for back in range(s - 1, max(0, s - 6), -1):
                    if text[back - 1].strip() == "select {":
                        sel.add(back)
                        break
            self.deliver_select[variant] = sel

    def focal(self, variant, lines, trace_sha, failing, final_sources):
        for dump in parse_goroutine_dumps(lines):
            prem = None
            cons = None
            for g in dump:
                for fn, where in g.frames:
                    lm = re.search(r"/pkg/controller/framework/shared_informer\.go:(\d+)", where)
                    if (re.search(r"framework\.\(\*processorListener\)\.pop\(", fn) and lm
                            and int(lm.group(1)) in self.deliver_select[variant] and g.state.startswith(("select", "chan send"))):
                        prem = prem or g
                if g.state.startswith("semacquire"):
                    hit = _first_caller_after(g.frames, r"^sync\.\(\*Mutex\)\.Lock\(")
                    if hit and hit[1].startswith("k8s.io/kubernetes/pkg/controller/framework."):
                        cons = cons or g
            if prem and cons and prem.gid != cons.gid:
                return ("k8s26980.R1", [loc(trace_sha, prem.start, prem.end)], [loc(trace_sha, cons.start, cons.end)])
        return None


class Istio17860Oracle(CaseOracle):
    rule_ids = ("istio17860.R1",)

    def focal(self, variant, lines, trace_sha, failing, final_sources):
        for dump in parse_goroutine_dumps(lines):
            prem = None
            cons = None
            for g in dump:
                fns = [fn for fn, _ in g.frames]
                if any(re.search(r"pkg/envoy\.\(\*agent\)\.waitUntilLive\(", f) for f in fns) and \
                        any(re.search(r"pkg/envoy\.\(\*agent\)\.Restart\(", f) for f in fns):
                    prem = prem or g
                if g.state.startswith("semacquire"):
                    hit = _first_caller_after(g.frames, r"^sync\.\(\*Mutex\)\.Lock\(")
                    if hit and re.search(r"pkg/envoy\.\(\*agent\)\.Run\(", hit[1]):
                        cons = cons or g
            if prem and cons and prem.gid != cons.gid:
                return ("istio17860.R1", [loc(trace_sha, prem.start, prem.end)], [loc(trace_sha, cons.start, cons.end)])
        return None


ORACLES = {"pool162": Pool162Oracle, "grpc1859": Grpc1859Oracle, "k8s26980": K8s26980Oracle, "istio17860": Istio17860Oracle}


def make_oracle(spec: CaseSpec, packet_files: dict[str, str], originals: dict[str, str]) -> CaseOracle:
    return ORACLES[spec.case](spec, packet_files, originals)


# --------------------------------------------------------------------------- classification

def classify(oracle: CaseOracle, variant: str, *, exit_code: int | None, text: str, outer_timeout: bool,
             cleanup_ok: bool, harness_error: str | None, selection: list[str],
             final_sources: dict[str, str]) -> AttemptClass:
    spec = oracle.spec
    trace_sha = sha256_text(text)
    if harness_error or not cleanup_ok:
        return AttemptClass(HARNESS_INVALID, harness_error or "container cleanup not verified")
    if outer_timeout:
        return AttemptClass(UNRESOLVED, "outer timeout: process killed; outcome not interpretable")
    lines = text.split("\n")
    if spec.language == "go":
        results, _ = go_test_results(lines)
        inner_timeout = any(l.startswith("panic: test timed out after") for l in lines)
    else:
        wins = java_windows(lines)
        results = {k: ("PASS" if v["status"] == "PASS" else "FAIL") for k, v in wins.items() if v["status"]}
        inner_timeout = any(l.startswith("W1-INNER-TIMEOUT") for l in lines)
    selected = {t: results.get(t) for t in selection}
    if any(v == "SKIP" for v in selected.values()):
        return AttemptClass(UNRESOLVED, "a selected test was skipped", test_results=results)
    if exit_code == 0:
        if all(v == "PASS" for v in selected.values()) and not inner_timeout:
            return AttemptClass(PASS, "all selected tests passed", test_results=results)
        return AttemptClass(HARNESS_INVALID, "exit 0 but selected results incomplete or failing", test_results=results)
    if exit_code is None:
        return AttemptClass(UNRESOLVED, "no exit status", test_results=results)
    failing = [t for t, v in selected.items() if v == "FAIL"]
    missing = [t for t, v in selected.items() if v is None]
    if not failing and not missing:
        return AttemptClass(HARNESS_INVALID, f"exit {exit_code} with all selected tests passing", test_results=results)
    if not failing and missing and not inner_timeout and not any(l.startswith("panic:") for l in lines):
        return AttemptClass(UNRESOLVED, "non-zero exit without interpretable test results", test_results=results)
    hit = oracle.focal(variant, lines, trace_sha, failing + (missing if inner_timeout else []), final_sources)
    if hit:
        rule, prem, cons = hit
        return AttemptClass(FOCAL, "frozen rule matched premise and consequence evidence", rule, prem, cons, results,
                            {"failing": failing, "interrupted": missing if inner_timeout else []})
    why = "inner timeout" if inner_timeout and not failing else "test failure"
    return AttemptClass(NONFOCAL, f"{why} without supported focal premise and consequence evidence", test_results=results,
                        details={"failing": failing, "missing": missing, "inner_timeout": inner_timeout})
