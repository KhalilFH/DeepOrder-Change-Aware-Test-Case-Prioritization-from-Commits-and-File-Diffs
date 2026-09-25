"""Post-collection arithmetic audit; no imports from the C1/E1 scorer.

Run from repository root with Python -B. Reads sealed measured records and
frozen-analysis outputs, writes only independent_verification.json beside this
file. This checks arithmetic/provenance, not the causal truth of oracle labels.
"""
import collections
import csv
import hashlib
import json
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
AUDIT = Path(__file__).resolve().parent


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def main():
    seal = json.loads((AUDIT / "pre_analysis_seal.json").read_text(encoding="utf-8"))
    rows = []
    for name, expected in seal["raw_ledger_sha256"].items():
        path = STUDY / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
        rows.extend(read_jsonl(path))
    annotations = read_jsonl(STUDY / "measured/annotations.jsonl")
    ann = {a["record_sha256"]: a for a in annotations}
    assert len(rows) == len(annotations) == len(ann) == 720
    assert {r["sha256"] for r in rows} == set(ann)
    scheduled = list(csv.DictReader((STUDY / "schedule.csv").open(encoding="utf-8")))
    actual = sorted(rows, key=lambda r: r["extra"]["job_started_utc"])
    assert [r["extra"]["attempt_id"] for r in actual] == [r["attempt_id"] for r in scheduled]
    groups = collections.defaultdict(list)
    labels = collections.Counter()
    for r in rows:
        x = r["extra"]
        assert x["stage"] == "measured" and x["profile_verified"] and x["session_probe_passed"]
        assert not x["profile_problems"] and x["cleanup"]["verified_absent"]
        assert x["cleanup"]["returncode"] == 0
        cfg = x["inspect"]
        assert cfg["gomaxprocs_env"] == ["GOMAXPROCS=16"]
        if x["profile"] == "L":
            assert (cfg["cpu_period"], cfg["cpu_quota"]) == (100000, 200000)
        else:
            assert cfg["cpu_quota"] in (0, -1) and cfg["nano_cpus"] == 0
        a = ann[r["sha256"]]
        assert a["attempt_id"] == x["attempt_id"]
        assert a["categories"] in (["PASS"], ["FOCAL_DEFECT_WITNESS"])
        assert (r["exit_status"] == 0) == (a["categories"] == ["PASS"])
        if r["version"] == "V_ok":
            assert a["categories"] == ["PASS"]
        labels.update(a["categories"])
        groups[r["episode"], x["profile"], r["version"], r["block"]].append(r)
    summary = json.loads((STUDY / "analysis/summary.json").read_text(encoding="utf-8"))
    assert summary["meta"]["family_K"] == 12
    checks = []
    for subject in summary["subjects"]:
        sid = subject["subject"]
        vectors, masked = {}, {}
        for profile in ("R", "L"):
            first, triple, masked_blocks = [], [], 0
            for block in range(1, 11):
                rs = sorted(groups[sid, profile, "V_bad", block], key=lambda r: r["attempt"])
                assert [r["attempt"] for r in rs] == [1, 2, 3]
                failed = [r["exit_status"] != 0 for r in rs]
                # Every observed nonzero is a focal match in these data.
                first.append(int(failed[0]))
                triple.append(int(all(failed)))
                masked_blocks += int(failed[0] and not all(failed))
            vectors[profile, "P1"] = first
            vectors[profile, "P3"] = triple
            masked[profile] = masked_blocks
            for policy in ("P1", "P3"):
                assert sum(vectors[profile, policy]) == subject["S_rates"][f"{profile}/{policy}"]["count"]
        contrasts = {}
        for policy in ("P1", "P3"):
            diff = [a - b for a, b in zip(vectors["R", policy], vectors["L", policy])]
            estimate = sum(diff) / 10
            batch_a, batch_b = sum(diff[:5]) / 5, sum(diff[5:]) / 5
            c = subject["primary_delta_S"][policy]
            assert c["complete_blocks"] == 10 and abs(c["estimate"] - estimate) < 1e-12
            assert c["batches"]["A"]["estimate"] == batch_a
            assert c["batches"]["B"]["estimate"] == batch_b
            signal = abs(estimate) >= 0.20 and batch_a * estimate > 0 and batch_b * estimate > 0
            gate = next(g for g in summary["gates"]["C3"]["rows"] if g["subject"] == sid and g["policy"] == policy)
            assert gate["signal"] == signal
            contrasts[policy] = {"delta": estimate, "batch_A": batch_a, "batch_B": batch_b, "C3_signal": signal}
        checks.append({"subject": sid, "counts": {f"{p}/{q}": sum(v) for (p, q), v in vectors.items()},
                       "masked_P3_blocks": masked, "contrasts": contrasts})
    report = {"status": "PASS", "scope": "All primary numerators, contrasts, batch directions and C3 flags independently recomputed; raw bytes, order and recorded profile evidence verified. Causal oracle validity and confidence-interval numerical implementation are not independently re-established here.",
              "raw_attempts": 720, "categories": dict(labels), "subjects": checks,
              "source_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (AUDIT / "independent_verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
