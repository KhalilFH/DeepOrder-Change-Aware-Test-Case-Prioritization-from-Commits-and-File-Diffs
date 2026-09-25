"""EXPLORATORY / POST HOC signal audit s03: etcd5509 oracle evidence.

Descriptive structure of every etcd5509 goroutine dump (C1 R and L, plus the
historical unrestricted Q0 and E1 focal dumps), and test-internal pass
durations. This does NOT relabel any attempt and does NOT define a stronger
oracle: the frozen labels stay as recorded. It only describes what the frozen
positive dumps contain, to judge whether they look like the leaked-RLock
deadlock or like generic CPU delay.
Outputs: out/s03_oracle_dumps.json, out/s03_etcd5509_dumps.csv
"""
from __future__ import annotations

import collections
import csv
import json
import re
from pathlib import Path

from audit_common import STUDY, focal, load_attempts, load_jsonl, write_csv, write_json

REPO = STUDY.parents[1]
HDR = re.compile(r"^goroutine (\d+) \[([^\]]*)\]:\s*$", re.M)


def goroutines(text: str):
    out = []
    ms = list(HDR.finditer(text))
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        body = text[m.end():end]
        body = body.split("\n\n")[0]
        lines = [l for l in body.splitlines() if l.strip()]
        funcs = [l.strip() for l in lines if not l.startswith("\t")]
        files = [l.strip() for l in lines if l.startswith("\t")]
        out.append({"gid": int(m.group(1)), "state": m.group(2), "funcs": funcs, "files": files})
    return out


def site(g, after: str) -> str:
    """Function + file:line of the frame immediately below `after` (the caller)."""
    for i, f in enumerate(g["funcs"]):
        if after in f and i + 1 < len(g["funcs"]):
            fn = re.sub(r"\(0x[^)]*\)|\([^)]*\)$", "", g["funcs"][i + 1]).split("/")[-1]
            fl = g["files"][i + 1].split()[0].split("/")[-1] if i + 1 < len(g["files"]) else "?"
            return f"{fn} @ {fl}"
    return "?"


def describe(text: str) -> dict:
    gs = goroutines(text)
    test = [g for g in gs if any(re.search(r"integration\.TestKVGetErrConnClosed\(", f) for f in g["funcs"])]
    t = test[0] if test else None
    shape = "none"
    if t and any("(*Client).Close" in f for f in t["funcs"]):
        if any("sync.(*RWMutex).Lock" in f for f in t["funcs"]):
            shape = "i: test goroutine in Close's own RWMutex.Lock"
        elif t["state"].startswith("chan receive"):
            shape = "ii: test goroutine in Close chan receive"
    waiters = [g for g in gs if (t is None or g["gid"] != t["gid"])
               and any("sync.(*RWMutex).Lock" in f for f in g["funcs"])]
    waiter_sites = sorted(site(g, "sync.(*RWMutex).Lock") for g in waiters)
    get_g = [g for g in gs if any(("TestKVGetErrConnClosed.func" in f) or ("(*kv).Get" in f) or ("remoteClient" in f) for f in g["funcs"])]
    clientv3_other = set()
    for g in gs:
        if (t is not None and g["gid"] == t["gid"]) or g in waiters:
            continue
        cv = [f for f in g["funcs"] if "coreos/etcd/clientv3." in f]
        if cv:
            top = re.sub(r"\(0x[^)]*\)$|\(\)$", "", cv[0]).split("/")[-1]
            clientv3_other.add(f"{top} [{g['state']}]")
    clientv3_other = sorted(clientv3_other)
    return {
        "timeout_panic": bool(re.search(r"panic: test timed out after 45s", text)),
        "n_goroutines": len(gs),
        "test_state": t["state"] if t else None,
        "shape": shape,
        "rwmutex_lock_waiters_other_than_test": len(waiters),
        "waiter_sites": "; ".join(waiter_sites),
        "get_goroutine_present": bool(get_g),
        "other_clientv3_goroutines": "; ".join(x for x in clientv3_other if x),
        "kv_get_took_too_long": "kv.Get took too long" in text,
    }


def main():
    att = load_attempts(["etcd5509"])
    rows = []
    for a in sorted(att.values(), key=lambda a: a["seq"]):
        if a["variant"] == "bad" and focal(a):
            d = describe(a["stdout"] + "\n" + a["stderr"])
            rows.append({"source": f"C1-{a['profile']}", "attempt_id": a["attempt_id"], "batch": a["batch"], **d})
    # Historical unrestricted focal dumps: E1 ledgers (with frozen annotations) and Q0 logs (with results.csv).
    e1 = STUDY.parent / "ci_sensitivity_2026_09" / "e1" / "etcd5509"
    ann = {n["record_seq"]: n for n in load_jsonl(e1 / "annotations.jsonl")}
    for r in load_jsonl(e1 / "attempts.jsonl"):
        if r["version"] == "V_bad" and "FOCAL_DEFECT_WITNESS" in ann[r["seq"]]["categories"]:
            d = describe(r["stdout"] + "\n" + r["stderr"])
            rows.append({"source": "E1-unrestricted", "attempt_id": f"e1-seq{r['seq']}", "batch": "", **d})
    q0 = STUDY.parent / "ci_sensitivity_2026_09" / "task5_artifacts" / "etcd5509" / "attempts"
    q0_res = {}
    with open(q0 / "results.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            q0_res[r.get("version", "") + "_" + r.get("attempt", "")] = r
    q0_rows_header = list(next(iter(q0_res.values())).keys()) if q0_res else []
    for p in sorted(q0.glob("vbad_attempt_*.log"), key=lambda p: int(re.findall(r"\d+", p.stem)[0])):
        text = p.read_bytes().decode("utf-8", "replace")
        d = describe(text)
        if d["timeout_panic"]:
            rows.append({"source": "Q0-unrestricted", "attempt_id": p.name, "batch": "", **d})
    write_csv("s03_etcd5509_dumps.csv", rows)

    summ = collections.defaultdict(lambda: collections.Counter())
    for r in rows:
        src = r["source"]
        summ[src]["n"] += 1
        summ[src][f"shape={r['shape']}"] += 1
        summ[src][f"waiters={r['waiter_sites']}"] += 1
        summ[src][f"get_goroutine_present={r['get_goroutine_present']}"] += 1
        summ[src][f"timeout_panic={r['timeout_panic']}"] += 1
        summ[src][f"other_clientv3={r['other_clientv3_goroutines']}"] += 1

    # Test-internal durations of passes ("--- PASS: TestKVGetErrConnClosed (0.04s)").
    pat = re.compile(r"--- PASS: TestKVGetErrConnClosed \(([\d.]+)s\)")
    pas = collections.defaultdict(list)
    for a in att.values():
        m = pat.search(a["stdout"])
        if a["exit"] == 0 and m:
            pas[f"{a['profile']}/{a['variant']}"].append(float(m.group(1)))
    passdur = {k: {"n": len(v), "min": min(v), "median": sorted(v)[len(v) // 2], "max": max(v)} for k, v in sorted(pas.items())}

    res = {
        "label": "EXPLORATORY/POST-HOC s03; descriptive dump structure, frozen labels unchanged",
        "q0_results_csv_header": q0_rows_header,
        "dump_summary_by_source": {k: dict(sorted(v.items())) for k, v in summ.items()},
        "test_reported_pass_duration_s": passdur,
        "any_kv_get_took_too_long_anywhere": any(("kv.Get took too long" in (a["stdout"] + a["stderr"])) for a in att.values()),
    }
    write_json("s03_oracle_dumps.json", res)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
