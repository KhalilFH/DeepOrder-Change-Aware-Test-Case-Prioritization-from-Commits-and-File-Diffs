"""Offline W1 artifact audit; no harness imports, provider calls, or subject runs.

Run from any directory with Python 3.10+. Writes only audit.json beside this file.
This checks recorded evidence, not fresh execution or oracle correctness.
"""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import statistics

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
REPO = STUDY.parent.parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(data):
    return sha256(data).hexdigest()


def manifest(path, base, normalize=False):
    checked, failures = 0, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        expected, rel = line.split(None, 1)
        target = (base / rel).resolve()
        if not target.is_relative_to(STUDY.resolve()):
            raise ValueError(f"Manifest path outside study: {rel}")
        data = target.read_bytes()
        if normalize:
            data = data.replace(b"\r\n", b"\n")
        checked += 1
        if digest(data) != expected:
            failures.append(rel)
    return {"files": checked, "failures": failures, "manifest_sha256": digest(path.read_bytes())}


def chain(path):
    previous, count = "0" * 64, 0
    for count, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        row = json.loads(line)
        stored = row.pop("event_sha256")
        encoded = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
        if row["sequence"] != count or row["previous_event_sha256"] != previous or digest(encoded) != stored:
            raise ValueError(f"Broken chain: {path.name}:{count}")
        previous = stored
    return {"events": count, "tail": previous}


def main():
    integrity = {"raw": manifest(STUDY / "raw_seal.sha256", STUDY),
                 "executable": manifest(STUDY / "FREEZE.sha256", REPO, True)}
    for version in (".", "v1_1", "v1_2"):
        base = STUDY / version
        integrity[version] = manifest(base / "DESIGN_FREEZE.sha256", base, True)
    for name in ("events.jsonl", "resources/resource_ledger.jsonl"):
        integrity[name] = chain(STUDY / name)
    if any(v.get("failures") for v in integrity.values()):
        raise ValueError(f"Manifest mismatch: {integrity}")

    events = [json.loads(x) for x in (STUDY / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    denials = [{"id": e["entity_id"], **e["payload"]} for e in events if e["event_type"] == "budget_denied"]
    table = defaultdict(Counter)
    labels, models, ai = Counter(), Counter(), []
    label_checks, policy_checks = 0, 0
    for directory in sorted((STUDY / "measured").glob("w1.*")):
        s = read(directory / "session.json")
        o = read(directory / "validation/outcome.json")
        final = read(directory / "final.json") if (directory / "final.json").exists() else None
        # This closed dataset has no integrity stops or invalid sealed candidates.
        # Fail visibly if that premise changes; do not silently classify new cases.
        if final is None:
            label = "NO_SUBMISSION"
            assert all(x["status"] == "NOT_RUN" for x in o["slots"])
        else:
            assert final["legal"] and not final["malformed"]
            bad = [x for x in o["slots"] if x["variant"] == "V_bad"]
            ok = [x for x in o["slots"] if x["variant"] == "V_ok"]
            assert len(bad) == len(ok) == 15
            assert all(x["status"] == "PASS" for x in ok)
            assert all(x["status"] in ("PASS", "FOCAL_FAILURE", "NONFOCAL_FAILURE") for x in bad)
            focal = [x for x in bad if x["status"] == "FOCAL_FAILURE"]
            success = len(focal) >= 2 and len({x["triplet"] for x in focal}) >= 2 and all(x["status"] != "NONFOCAL_FAILURE" for x in bad)
            label = "VALIDATED_WITNESS" if success else "NO_WITNESS_WITHIN_BUDGET"
            triples = [[x["status"] == "FOCAL_FAILURE" for x in sorted(bad, key=lambda x: x["position"]) if x["triplet"] == t] for t in range(1, 6)]
            for key, value in {"P1": sum(t[0] for t in triples), "P3": sum(all(t) for t in triples), "P3_retain": sum(any(t) for t in triples), "focal_attempts": len(focal)}.items():
                assert o["policy"][key] == [value, value], (s["id"], key)
            policy_checks += 1
        assert label == o["outcome"], s["id"]
        label_checks += 1
        labels[label] += 1
        table[s["case"]][s["arm"]] += int(label == "VALIDATED_WITNESS")
        if s["arm"] not in ("B2", "B3", "B4"):
            continue
        calls, tool_counts, stops, errors = [], Counter(), Counter(), {}
        previous_reads = []
        for response_path in sorted((directory / "requests").glob("*.req*.response.json")):
            response = read(response_path)
            request = read(response_path.with_name(response_path.name.replace(".response.", ".request.")))
            names = {t["name"] for t in request["tools"]}
            stage = "planner" if "submit_plan" in names else "judge" if "submit_judgments" in names else "b2" if s["arm"] == "B2" else "generator"
            uses = [c for c in response.get("content", []) if c.get("type") == "tool_use"]
            tool_counts.update(c["name"] for c in uses)
            models[response["model"]] += 1
            stops[response["stop_reason"]] += 1
            # Count repeated reads only if the entire requested range was in initial excerpts.
            initial = request["messages"][0]["content"][0]["text"]
            spans = [(f, int(a), int(b)) for f, a, b in re.findall(r"### `([^`]+)` lines (\d+)-(\d+)", initial)]
            read_uses = [c["input"] for c in uses if c["name"] == "read_source"]
            redundant = sum(any(r.get("file_id") == f and a <= r.get("start_line", 0) and r.get("end_line", 10**9) <= b for f, a, b in spans) for r in read_uses)
            repeated_across_stages = sum(any(old["file_id"] == r.get("file_id") and old["start_line"] <= r.get("start_line", 0) and r.get("end_line", 10**9) <= old["end_line"] and old["stage"] != stage for old in previous_reads) for r in read_uses)
            previous_reads.extend({**r, "stage": stage} for r in read_uses)
            for message in request["messages"]:
                for content in message.get("content", []) if isinstance(message.get("content"), list) else []:
                    if content.get("type") == "tool_result":
                        value = content.get("content", "")
                        if isinstance(value, str) and ('"error"' in value or value.startswith("ERROR:")):
                            errors[content["tool_use_id"]] = value
            calls.append({"file": response_path.relative_to(STUDY).as_posix(), "stage": stage,
                          "messages": len(request["messages"]), "tools": [c["name"] for c in uses],
                          "stop_reason": response["stop_reason"], "usage": response.get("usage"),
                          "reads_fully_in_initial_excerpts": redundant,
                          "reads_repeating_prior_stage_range": repeated_across_stages,
                          "empty_plan_submissions": sum(c["name"] == "submit_plan" and not c.get("input") for c in uses),
                          "empty_judgment_submissions": sum(c["name"] == "submit_judgments" and not c.get("input", {}).get("judgments") for c in uses)})
        plan_path, judge_path = directory / "stages/plan.json", directory / "stages/judgments.json"
        plan = read(plan_path) if plan_path.exists() else None
        judgments = read(judge_path) if judge_path.exists() else {}
        proposals = [{"file": p.relative_to(STUDY).as_posix(), "error": read(p).get("error")} for p in sorted((directory / "proposals").glob("*.json"))]
        ai.append({"id": s["id"], "case": s["case"], "arm": s["arm"], "outcome": label,
                   "final_unchanged": final.get("unchanged") if final else None,
                   "seconds": s["elapsed_search_seconds"], "details": s["details"], "reasons": s["reason_codes"],
                   "calls": calls, "tools": dict(tool_counts), "stop_reasons": dict(stops),
                   "tool_errors_returned_to_model": errors, "proposals": proposals,
                   "plan_claims": len(plan["claims"]) if plan else None,
                   "judgments": dict(Counter(x["judgment"] for x in judgments.values())),
                   "judgment_sources": dict(Counter(x["source"] for x in judgments.values()))})
    summaries = {}
    for arm in ("B2", "B3", "B4"):
        rows = [x for x in ai if x["arm"] == arm]
        calls = [c for x in rows for c in x["calls"]]
        tools = Counter()
        stops = Counter()
        for x in rows:
            tools.update(x["tools"])
            stops.update(x["stop_reasons"])
        summaries[arm] = {"sessions": len(rows), "calls": len(calls), "tools": dict(tools), "stops": dict(stops),
                          "median_seconds": statistics.median(x["seconds"] for x in rows),
                          "max_seconds": max(x["seconds"] for x in rows),
                          "initial_only_requests": sum(c["messages"] == 1 for c in calls),
                          "reads_fully_in_initial_excerpts": sum(c["reads_fully_in_initial_excerpts"] for c in calls),
                          "reads_repeating_prior_stage_range": sum(c["reads_repeating_prior_stage_range"] for c in calls),
                          "empty_plan_submissions": sum(c["empty_plan_submissions"] for c in calls),
                          "empty_judgment_submissions": sum(c["empty_judgment_submissions"] for c in calls),
                          "plans_with_claims": sum(bool(x["plan_claims"]) for x in rows),
                          "generator_calls_per_session": dict(Counter(sum(c["stage"] in ("b2", "generator") for c in x["calls"]) for x in rows)),
                          "generator_calls": sum(c["stage"] in ("b2", "generator") for c in calls),
                          "usd": round(sum(x["details"]["usd"] for x in rows), 6)}
    result = {"scope": "Offline rehash, label/policy arithmetic, and provider trace audit; no execution or oracle reclassification.",
              "integrity": integrity, "labels_checked": label_checks, "complete_policies_checked": policy_checks,
              "labels": dict(labels), "table": dict(table), "returned_models": dict(models),
              "denials": denials, "arms": summaries, "ai_sessions": ai}
    (HERE / "audit.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "ai_sessions"}, indent=2))


if __name__ == "__main__":
    main()
