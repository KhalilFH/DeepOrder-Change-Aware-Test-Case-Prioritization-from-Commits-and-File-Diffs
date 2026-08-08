#!/usr/bin/env python3
"""
STEP 0 — Fail-fast viability check for change-aware TCP on BugSwarm traccar/traccar.
Metadata only (tiny bandwidth). No token, no Docker.

Fetches ALL traccar/traccar BugSwarm artifacts via the public HTTP REST API,
then reports:
  - artifact count
  - time spread (committed_at of the failed job = the buggy commit)
  - distinct trigger_sha / distinct commits
  - failure TYPE breakdown (test vs code vs build) -- crucial: only TEST failures
    give per-test verdicts usable for TCP
  - how many artifacts actually ran tests and how many failed tests
  - a chronological sequence table (the thing TCP history features need)
"""
import json
import time
import urllib.parse
import urllib.request
from collections import Counter

BASE = "http://www.api.bugswarm.org/v1/artifacts"
REPO = "traccar/traccar"


def fetch_all(repo):
    where = urllib.parse.quote(json.dumps({"repo": repo}))
    max_results = 100
    items = []
    page = 1
    while True:
        url = f"{BASE}?where={where}&max_results={max_results}&page={page}"
        req = urllib.request.Request(url, headers={"User-Agent": "step0-viability"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        batch = data.get("_items", [])
        items.extend(batch)
        has_next = bool(data.get("_links", {}).get("next", {}).get("href"))
        if not has_next or not batch:
            break
        page += 1
        time.sleep(0.5)  # stay well under 20 req/min unauthenticated
    return items


def classify(a):
    """Return the failure kind for an artifact from its classification block."""
    c = a.get("classification", {}) or {}
    kinds = [k for k in ("test", "code", "build") if c.get(k) == "Yes"]
    return "+".join(kinds) if kinds else "none"


def main():
    print(f"Fetching all BugSwarm artifacts for {REPO} ...")
    arts = fetch_all(REPO)
    print(f"TOTAL ARTIFACTS: {len(arts)}\n")

    if not arts:
        print("No artifacts. STOP -> pivot to airavata (TCP-CI).")
        return

    rows = []
    for a in arts:
        fj = a.get("failed_job", {}) or {}
        pj = a.get("passed_job", {}) or {}
        rows.append({
            "image_tag": a.get("image_tag", ""),
            "committed_at": fj.get("committed_at", ""),
            "trigger_sha": fj.get("trigger_sha", ""),
            "failed_job_id": fj.get("job_id"),
            "passed_job_id": pj.get("job_id"),
            "num_tests_run": fj.get("num_tests_run", 0),
            "num_tests_failed": fj.get("num_tests_failed", 0),
            "kind": classify(a),
            "build_system": a.get("build_system", ""),
            "ci": a.get("ci_service", ""),
            "message": (fj.get("message", "") or "")[:60],
        })

    rows.sort(key=lambda r: r["committed_at"] or "")

    # --- failure type breakdown ---
    kinds = Counter(r["kind"] for r in rows)
    print("Failure-type breakdown (classification):")
    for k, n in kinds.most_common():
        print(f"  {k:16s}: {n}")
    print()

    # --- test-usability ---
    ran_tests = [r for r in rows if (r["num_tests_run"] or 0) > 0]
    failed_tests = [r for r in rows if (r["num_tests_failed"] or 0) > 0]
    test_kind = [r for r in rows if "test" in r["kind"]]
    print(f"Artifacts whose FAILED job ran >0 tests : {len(ran_tests)}")
    print(f"Artifacts whose FAILED job failed >0 tests: {len(failed_tests)}")
    print(f"Artifacts classified as TEST failure     : {len(test_kind)}")
    print()

    # --- sequence / history viability ---
    distinct_sha = {r["trigger_sha"] for r in rows if r["trigger_sha"]}
    dates = [r["committed_at"] for r in rows if r["committed_at"]]
    print(f"Distinct trigger_sha (commits): {len(distinct_sha)}")
    if dates:
        print(f"Time spread: {min(dates)}  ->  {max(dates)}")
    print()

    # --- chronological table ---
    print("Chronological artifact sequence (buggy-commit date):")
    print(f"{'#':>3} {'committed_at':20} {'kind':12} {'run':>5} {'fail':>5} "
          f"{'sha':10} message")
    print("-" * 100)
    for i, r in enumerate(rows, 1):
        print(f"{i:>3} {r['committed_at'][:19]:20} {r['kind']:12} "
              f"{r['num_tests_run']:>5} {r['num_tests_failed']:>5} "
              f"{(r['trigger_sha'] or '')[:10]:10} {r['message']}")

    # --- save raw metadata for later steps ---
    import os
    out = os.environ.get("STEP0_OUT", "traccar_bugswarm_metadata.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(arts, f, indent=2)
    print(f"\nRaw metadata saved -> {out}")

    # --- decision hint ---
    print("\n" + "=" * 60)
    print("DECISION INPUTS:")
    print(f"  total artifacts        = {len(arts)}")
    print(f"  TEST-failure artifacts = {len(test_kind)}")
    print(f"  with >0 failed tests   = {len(failed_tests)}")
    print(f"  distinct commits       = {len(distinct_sha)}")
    print("Gate: change-aware TCP needs a SEQUENCE of test-failing cycles.")
    print("If TEST-failure artifacts are only a handful & disconnected -> STOP, pivot to airavata.")


if __name__ == "__main__":
    main()
