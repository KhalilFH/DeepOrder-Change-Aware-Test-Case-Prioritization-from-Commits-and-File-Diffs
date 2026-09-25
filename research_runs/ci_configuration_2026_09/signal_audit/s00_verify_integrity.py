"""EXPLORATORY / POST HOC signal-validity audit, step 0: integrity checks.

Independent of c1_harness and e1_harness (stdlib only, no imports from them).
Read-only: verifies
  * the design freeze (DESIGN_FREEZE.sha256, 8 entries, study-relative paths),
    both against the working tree and against the committed bytes at HEAD;
  * the executable launch freeze (FREEZE.sha256, repo-relative paths);
  * the raw measured ledgers against the pre-analysis seal (raw bytes);
  * the hash chains of the 12 measured ledgers, events.jsonl, the resource
    ledger and the annotations' record_sha256 links;
  * that the analysis inputs recorded in analysis/summary.json match.
Writes signal_audit/out/integrity.json.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
REPO = STUDY.parents[1]
OUT = STUDY / "signal_audit" / "out"


def norm_sha(b: bytes) -> str:
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def raw_sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_sums(p: Path):
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            d, _, rel = line.partition("  ")
            rows.append((d.strip(), rel.strip()))
    return rows


def chain_ok(path: Path):
    prev = "0" * 64
    n = 0
    for line in path.read_bytes().decode("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rec = row.pop("sha256")
        if row.get("prev_sha256") != prev:
            return False, n, "prev link broken at row %d" % (n + 1)
        canon = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if hashlib.sha256((prev + canon).encode("utf-8")).hexdigest() != rec:
            return False, n, "digest mismatch at row %d" % (n + 1)
        prev = rec
        n += 1
    return True, n, prev


def main() -> int:
    res: dict = {"label": "EXPLORATORY/POST-HOC signal audit s00 (integrity)"}
    # Design freeze: working tree and committed bytes.
    dfile = STUDY / "DESIGN_FREEZE.sha256"
    d_entries = parse_sums(dfile)
    wt, committed = [], []
    for digest, rel in d_entries:
        p = STUDY / rel
        wt.append((rel, norm_sha(p.read_bytes()) == digest))
        gitpath = f"research_runs/ci_configuration_2026_09/{rel}"
        blob = subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:{gitpath}"],
                              capture_output=True).stdout
        committed.append((rel, norm_sha(blob) == digest))
    res["design_freeze"] = {
        "file_sha256_normalized": norm_sha(dfile.read_bytes()),
        "entries": len(d_entries),
        "working_tree_match": sum(ok for _, ok in wt),
        "committed_HEAD_match": sum(ok for _, ok in committed),
        "mismatches": [r for r, ok in wt if not ok] + [f"HEAD:{r}" for r, ok in committed if not ok],
    }
    # Launch freeze.
    lfile = STUDY / "FREEZE.sha256"
    l_entries = parse_sums(lfile)
    lmis = [rel for digest, rel in l_entries
            if not (REPO / rel).exists() or norm_sha((REPO / rel).read_bytes()) != digest]
    header = [l for l in lfile.read_text(encoding="utf-8").splitlines() if l.startswith("#")]
    res["launch_freeze"] = {
        "file_sha256_normalized": norm_sha(lfile.read_bytes()),
        "header": header,
        "entries": len(l_entries),
        "matched": len(l_entries) - len(lmis),
        "mismatches": lmis,
    }
    # Seal.
    seal = json.loads((STUDY / "analysis_audit" / "pre_analysis_seal.json").read_text(encoding="utf-8"))
    seal_rows = []
    for rel, digest in seal["raw_ledger_sha256"].items():
        p = STUDY / rel.replace("\\", "/")
        seal_rows.append({"file": p.name, "sealed": digest, "now": raw_sha(p), "match": raw_sha(p) == digest})
    res["seal"] = {
        "sealed_utc": seal["sealed_utc"],
        "files": len(seal_rows),
        "matched": sum(r["match"] for r in seal_rows),
        "seal_design_freeze_sha256": seal.get("design_freeze_sha256"),
        "seal_executable_freeze_sha256": seal.get("executable_freeze_sha256"),
        "seal_freeze_digests_match_now": [
            seal.get("design_freeze_sha256") == raw_sha(dfile) or seal.get("design_freeze_sha256") == norm_sha(dfile.read_bytes()),
            seal.get("executable_freeze_sha256") == raw_sha(lfile) or seal.get("executable_freeze_sha256") == norm_sha(lfile.read_bytes()),
        ],
        "rows": seal_rows,
    }
    # summary.json inputs agree with current raw files.
    summ = json.loads((STUDY / "analysis" / "summary.json").read_text(encoding="utf-8"))
    inp = summ["meta"]["inputs"]
    res["summary_inputs_match"] = {k: raw_sha(STUDY / "measured" / k) == v for k, v in inp.items()}
    # Chains.
    chains = {}
    for p in sorted((STUDY / "measured").glob("*__*.jsonl")):
        ok, n, info = chain_ok(p)
        chains[p.name] = {"ok": ok, "rows": n}
    for p in [STUDY / "events.jsonl", STUDY / "resources" / "resource_ledger.jsonl"]:
        ok, n, info = chain_ok(p)
        chains[p.name] = {"ok": ok, "rows": n, "head": info if ok else None}
    res["chains"] = chains
    # Annotation links.
    recs = {}
    for p in sorted((STUDY / "measured").glob("*__*.jsonl")):
        for line in p.read_bytes().decode("utf-8").splitlines():
            r = json.loads(line)
            recs[r["extra"]["attempt_id"]] = r["sha256"]
    ann = [json.loads(l) for l in (STUDY / "measured" / "annotations.jsonl").read_bytes().decode("utf-8").splitlines() if l.strip()]
    res["annotations"] = {
        "rows": len(ann),
        "unique_ids": len({a["attempt_id"] for a in ann}),
        "record_sha_links_ok": sum(recs.get(a["attempt_id"]) == a["record_sha256"] for a in ann),
        "raw_records": len(recs),
    }
    all_ok = (res["design_freeze"]["working_tree_match"] == 8 == res["design_freeze"]["committed_HEAD_match"]
              and not lmis and res["seal"]["matched"] == 12 and all(res["summary_inputs_match"].values())
              and all(c["ok"] for c in chains.values())
              and res["annotations"]["record_sha_links_ok"] == 720 == res["annotations"]["raw_records"])
    res["status"] = "PASS" if all_ok else "FAIL"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "integrity.json").write_text(json.dumps(res, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(res["status"], json.dumps({k: res[k] for k in ("design_freeze", "launch_freeze")}, default=str)[:600])
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
