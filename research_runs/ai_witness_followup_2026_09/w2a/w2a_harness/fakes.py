"""Scripted fake provider and subject behaviour for offline tests and ``dry-run``.

No credentials, provider calls or containers. Each of the eight sessions follows a scripted
scenario chosen to exercise a different path (discretionary seal, reserved final call, W1 failure
replays, stage failure, final without submit_final, build-before-run error, illegal placeholder
patch, truncation). Outcomes are synthetic and carry no experimental meaning.

W1 replays read recorded W1 response files read-only (``W1_REPLAYS``).
"""

from __future__ import annotations

import json
import re
from typing import Any

from . import W1_STUDY_DIR
from .casespec import CaseSpec, spec as case_spec
from .oracle_fixtures import POOL_INT, POOL_NSEE

FAKE_TEST = "TestProbeFake"
W1_MEASURED = W1_STUDY_DIR / "measured"
W1_REPLAYS = {
    # max_tokens planner response with an empty submit_plan object (W1 audit finding 4)
    "empty_plan_truncated": "w1.pool162.r1.B3/requests/w1.pool162.r1.B3.req01.response.json",
    # max_tokens planner response with a partial, non-empty plan object
    "partial_plan_truncated": "w1.pool162.r2.B4/requests/w1.pool162.r2.B4.req02.response.json",
    # complete response submitting an empty judgment list
    "empty_judgments": "w1.istio17860.r1.B3/requests/w1.istio17860.r1.B3.req03.response.json",
}


def w1_replay(name: str) -> dict[str, Any]:
    return json.loads((W1_MEASURED / W1_REPLAYS[name]).read_text(encoding="utf-8"))


def probe_proposal(sp: CaseSpec) -> dict[str, Any]:
    if sp.language == "go":
        return {"edits": [], "new_files": [{"path": f"{sp.test_dir}/w1_probe_test.go",
                                            "content": f"package {sp.package_name}\n\nimport \"testing\"\n\nfunc {FAKE_TEST}(t *testing.T) {{}}\n"}]}
    anchor = "public class TestGenericObjectPool extends TestBaseObjectPool {"
    return {"edits": [{"path": "src/test/org/apache/commons/pool/impl/TestGenericObjectPool.java", "old": anchor,
                       "new": anchor + "\n    public void testProbeFake() throws Exception {\n    }\n"}], "new_files": []}


PLACEHOLDER = {"edits": [{"path": "placeholder", "old": "", "new": ""}], "new_files": []}


def tu(name: str, inp: dict[str, Any], n: int) -> dict[str, Any]:
    return {"type": "tool_use", "id": f"toolu_fake_{name}_{n}", "name": name, "input": inp}


def _case(body: dict[str, Any]) -> str:
    m = re.search(r"# Build and run interface \((\w+)\)", json.dumps(body["messages"][0]))
    return m.group(1) if m else "k8s26980"


def _stage(body: dict[str, Any]) -> str:
    names = {t["name"] for t in body.get("tools", [])}
    if "submit_plan" in names:
        return "planner"
    if "submit_judgments" in names:
        return "judge"
    first = json.dumps(body["messages"][0])
    return "generator" if "## Validated plan" in first else "agent"


def _is_final(body: dict[str, Any]) -> bool:
    return "reserved final model call" in json.dumps(body["messages"][-1])


def _claims(body: dict[str, Any]) -> list[str]:
    text = body["messages"][0]["content"][0]["text"]
    m = re.search(r"## Claims to judge\n```json\n(.*?)\n```", text, re.S)
    return [c["id"] for c in json.loads(m.group(1))] if m else []


def good_plan(case: str) -> dict[str, Any]:
    sp = case_spec(case)
    entry = "shared/" + sp.editable_files[0]
    return {"obligation": "fake obligation", "intervention": "fake intervention", "uncertainties": ["fake"],
            "claims": [{"id": "c1", "category": "ordering", "proposition": "fake proposition 1", "source_spans": [f"{entry}:1-5"]},
                       {"id": "c2", "category": "observable_consequence", "proposition": "fake proposition 2",
                        "source_spans": [f"{entry}:2-3"]}]}


class ScenarioScript:
    """Per-(case, stage) call counters drive the scripted scenario of each session."""

    def __init__(self) -> None:
        self.calls: dict[tuple[str, str], int] = {}

    def __call__(self, body: dict[str, Any]) -> dict[str, Any]:
        case, stage = _case(body), _stage(body)
        arm = "F2" if stage == "agent" else "F3"
        key = (case, stage)
        n = self.calls[key] = self.calls.get(key, 0) + 1
        sp = case_spec(case)
        entry = "shared/" + sp.editable_files[0]
        if _is_final(body):
            return self.final(case, arm)
        if stage == "planner":
            return self.planner(case, n, entry)
        if stage == "judge":
            return self.judge(case, n, body)
        return self.work(case, arm, n, sp, entry)

    # -- scenarios -------------------------------------------------------------
    def planner(self, case: str, n: int, entry: str) -> dict[str, Any]:
        if case == "k8s26980":  # stage failure: two invalid plans
            return {"content": [tu("submit_plan", {"obligation": "", "claims": [], "intervention": "", "uncertainties": []}, n)]}
        if case == "pool162" and n == 1:  # W1 replay: truncated empty submit_plan
            return {"raw": w1_replay("empty_plan_truncated")}
        if case == "grpc1859" and n == 1:  # read the helper, then plan
            return {"content": [tu("read_source", {"file_id": "shared/test/end2end_test.go", "start_line": 5990, "end_line": 6042}, n)]}
        return {"content": [tu("submit_plan", good_plan(case), n)]}

    def judge(self, case: str, n: int, body: dict[str, Any]) -> dict[str, Any]:
        ids = _claims(body) or ["c1", "c2"]
        if case == "pool162" and n == 1:  # W1 replay: complete response with an empty judgment list
            return {"raw": w1_replay("empty_judgments")}
        return {"content": [tu("submit_judgments", {"judgments": [
            {"claim_id": i, "judgment": "unknown" if k else "supported",
             "source_spans": [] if k else ["shared/" + case_spec(case).editable_files[0] + ":1-2"], "reason": "fake"}
            for k, i in enumerate(ids)]}, n)]}

    def work(self, case: str, arm: str, n: int, sp: CaseSpec, entry: str) -> dict[str, Any]:
        probe = {**probe_proposal(sp), "rationale": "fake", "source_spans": []}
        if (case, arm) == ("pool162", "F2"):
            steps = [[tu("read_source", {"file_id": entry, "start_line": 1, "end_line": 5}, n)],
                     [tu("submit_patch", probe, n), tu("build_pair", {"proposal_id": "latest"}, n + 100)],
                     [tu("run_pair", {"proposal_id": "p1"}, n)],
                     [tu("submit_final", {"proposal_id": "p1", "rationale": "fake", "source_spans": [], "obligation": "fake", "uncertainties": []}, n)]]
            return {"content": steps[min(n, len(steps)) - 1]}
        if (case, arm) == ("pool162", "F3"):  # patch/build/run, then keep reading until only the reserve is left
            steps = [[tu("submit_patch", probe, n)], [tu("build_pair", {"proposal_id": "p1"}, n)], [tu("run_pair", {"proposal_id": "p1"}, n)]]
            if n <= len(steps):
                return {"content": steps[n - 1]}
            return {"content": [tu("read_source", {"file_id": entry, "start_line": n, "end_line": n + 3}, n)]}
        if (case, arm) == ("grpc1859", "F2"):  # W1 pattern: run before build; a no-tool response; then work
            steps = [[tu("submit_patch", probe, n), tu("run_pair", {"proposal_id": "latest"}, n + 100)],
                     [{"type": "text", "text": "thinking aloud without a tool call"}],
                     [tu("build_pair", {"proposal_id": "p1"}, n)], [tu("run_pair", {"proposal_id": "p1"}, n)],
                     [tu("submit_final", {"proposal_id": "latest", "rationale": "fake", "source_spans": [], "obligation": "fake", "uncertainties": []}, n)]]
            return {"content": steps[min(n, len(steps)) - 1]}
        if (case, arm) == ("grpc1859", "F3"):
            return {"content": [tu("submit_final", {"proposal_id": "unchanged", "rationale": "fake", "source_spans": [], "obligation": "fake", "uncertainties": []}, n)]}
        if (case, arm) == ("k8s26980", "F2"):  # W1 placeholder patch, a truncated response, then a legal patch
            steps = [[tu("submit_patch", {**PLACEHOLDER, "rationale": "fake", "source_spans": []}, n)],
                     "TRUNCATE", [tu("submit_patch", probe, n)], [tu("build_pair", {"proposal_id": "p2"}, n)],
                     [tu("run_pair", {"proposal_id": "p2"}, n)]]
            if n <= len(steps):
                st = steps[n - 1]
                if st == "TRUNCATE":
                    return {"content": [tu("submit_patch", {}, n)], "stop_reason": "max_tokens", "output_tokens": 4000}
                return {"content": st}
            return {"content": [tu("read_source", {"file_id": entry, "start_line": 1, "end_line": 2}, n)]}
        if (case, arm) == ("istio17860", "F2"):  # never seals; final call answers without submit_final
            return {"content": [tu("read_source", {"file_id": entry, "start_line": 1, "end_line": 2}, n)]}
        return {"content": [tu("submit_final", {"proposal_id": "unchanged", "rationale": "fake", "source_spans": [], "obligation": "fake", "uncertainties": []}, n)]}

    def final(self, case: str, arm: str) -> dict[str, Any]:
        if (case, arm) == ("istio17860", "F2"):
            return {"content": [{"type": "text", "text": "no tool in the final call"}]}
        if (case, arm) == ("k8s26980", "F2"):  # final call also tries other tools; only submit_final runs
            return {"content": [tu("read_source", {"file_id": "x", "start_line": 1, "end_line": 1}, 900),
                                tu("submit_final", {"proposal_id": "p2", "rationale": "fake", "source_spans": [], "obligation": "fake", "uncertainties": []}, 901)]}
        return {"content": [tu("submit_final", {"proposal_id": "latest", "rationale": "fake", "source_spans": [], "obligation": "fake", "uncertainties": []}, 902)]}


def subject_outcome(sp: CaseSpec, variant: str, overlay_sha: str, selection: list[str], seed: Any, aid: str):
    """Synthetic traces: V_ok always passes; for pool162 the probe fails focally on V_bad; Go passes."""
    if sp.language == "java":
        lines = []
        for t in selection:
            lines.append(f"W1-TEST-BEGIN {t}")
            if variant == "V_bad" and t.endswith("#testProbeFake"):
                lines += [POOL_INT.rstrip("\n"), POOL_NSEE.rstrip("\n"), f"W1-TEST-FAILURE {t}", f"W1-TEST-END {t} FAIL"]
            else:
                lines.append(f"W1-TEST-END {t} PASS")
        failed = sum(1 for x in lines if x.endswith(" FAIL"))
        lines.append(f"W1-RUN-COMPLETE passed={len(selection) - failed} failed={failed}")
        return (1 if failed else 0), "\n".join(lines) + "\n", False
    return 0, "".join(f"=== RUN   {t}\n--- PASS: {t} (0.01s)\n" for t in selection) + "PASS\n", False
