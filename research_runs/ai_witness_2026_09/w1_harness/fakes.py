"""Scripted fake provider and subject behaviour for offline tests and ``dry-run``.

No credentials, provider calls or containers. The scripts exercise every arm end to end
(tool loops, stage pipelines, malformed Jev output, sealing, validation, analysis); the
outcomes they produce are synthetic and carry no experimental meaning.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .casespec import CaseSpec, spec as case_spec
from .oracle_fixtures import POOL_INT, POOL_NSEE

FAKE_TEST = "TestProbeFake"


def _probe_proposal(sp: CaseSpec) -> dict[str, Any]:
    if sp.language == "go":
        return {"edits": [], "new_files": [{"path": f"{sp.test_dir}/w1_probe_test.go",
                                            "content": f"package {sp.package_name}\n\nimport \"testing\"\n\nfunc {FAKE_TEST}(t *testing.T) {{}}\n"}]}
    anchor = "public class TestGenericObjectPool extends TestBaseObjectPool {"
    return {"edits": [{"path": "src/test/org/apache/commons/pool/impl/TestGenericObjectPool.java", "old": anchor,
                       "new": anchor + "\n    public void testProbeFake() throws Exception {\n    }\n"}], "new_files": []}


def _case_from_body(body: dict[str, Any]) -> str:
    text = json.dumps(body["messages"][0])
    m = re.search(r"# Build and run interface \((\w+)\)", text)
    return m.group(1) if m else "k8s26980"


def generator_script(body: dict[str, Any]) -> dict[str, Any]:
    tools = {t["name"] for t in body.get("tools", [])}
    n_assist = sum(1 for m in body["messages"] if m["role"] == "assistant")
    sp = case_spec(_case_from_body(body))
    if "submit_plan" in tools:
        return {"content": [{"type": "tool_use", "id": "tu_plan", "name": "submit_plan", "input": {
            "obligation": "fake obligation", "intervention": "fake intervention", "uncertainties": ["fake"],
            "claims": [{"id": "c1", "category": "ordering", "proposition": "fake proposition 1", "source_spans": []},
                       {"id": "c2", "category": "observable_consequence", "proposition": "fake proposition 2", "source_spans": []}]}}]}
    if "submit_judgments" in tools:
        return {"content": [{"type": "tool_use", "id": "tu_j", "name": "submit_judgments", "input": {"judgments": [
            {"claim_id": "c1", "judgment": "unknown", "source_spans": [], "reason": "fake"},
            {"claim_id": "c2", "judgment": "supported", "source_spans": [], "reason": "fake"}]}}]}
    if n_assist == 0:
        return {"content": [
            {"type": "thinking", "thinking": "", "signature": "fake-signature"},
            {"type": "tool_use", "id": "tu_r", "name": "read_source",
             "input": {"file_id": next(iter(sorted(["shared/" + sp.editable_files[0]]))), "start_line": 1, "end_line": 5}},
            {"type": "tool_use", "id": "tu_p", "name": "submit_patch",
             "input": {**_probe_proposal(sp), "rationale": "fake", "source_spans": []}},
            {"type": "tool_use", "id": "tu_b", "name": "build_pair", "input": {"proposal_id": "latest"}},
            {"type": "tool_use", "id": "tu_x", "name": "run_pair", "input": {"proposal_id": "latest"}}]}
    return {"content": [{"type": "tool_use", "id": "tu_f", "name": "submit_final", "input": {
        "proposal_id": "latest", "rationale": "fake", "source_spans": [], "obligation": "fake", "uncertainties": []}}]}


def jev_choice(body: dict[str, Any]) -> Any:
    """Alternate valid and malformed answers so the parser's unknown path is exercised."""
    if "fake proposition 2" in body["state"]:
        return b'{"model": "jev-fake-1.0", "answers": {"judgment": {"type": "choice", "choice": "maybe"}}, "usage": {"input_tokens": 10, "output_tokens": 1}}'
    return "supported"


def subject_outcome(sp: CaseSpec, variant: str, overlay_sha: str, selection: list[str], seed: Any, aid: str):
    """Synthetic traces: V_ok always passes; V_bad fails focally for pool162 probe overlays, else passes."""
    if sp.language == "java":
        lines = []
        for t in selection:
            lines.append(f"W1-TEST-BEGIN {t}")
            if variant == "V_bad" and t.endswith("#testProbeFake"):
                lines += [POOL_INT.rstrip("\n"), POOL_NSEE.rstrip("\n"), f"W1-TEST-FAILURE {t}", f"W1-TEST-END {t} FAIL"]
            else:
                lines.append(f"W1-TEST-END {t} PASS")
        failed = sum(1 for l in lines if l.endswith(" FAIL"))
        lines.append(f"W1-RUN-COMPLETE passed={len(selection) - failed} failed={failed}")
        return (1 if failed else 0), "\n".join(lines) + "\n", False
    return 0, "".join(f"=== RUN   {t}\n--- PASS: {t} (0.01s)\n" for t in selection) + "PASS\n", False
