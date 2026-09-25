"""EXPLORATORY / POST HOC signal audit s01: independent count verification and
the etcd5509 block-level table.

Read-only over raw ledgers, annotations, schedule and events.
Outputs: out/s01_counts.json, out/s01_etcd5509_blocks.csv, out/s01_etcd5509_blocks.md
"""
from __future__ import annotations

import collections

from audit_common import (STUDY, SUBJECTS, blocks, cells, focal, load_attempts, load_jsonl,
                          p1_prefix, p3_prefix, supported_block, write_csv, write_json, OUT)


def fmt(a, visible: bool) -> str:
    o = "F" if focal(a) else ("P" if a["exit"] == 0 else "X")
    s = f"{o}{'(' + a['signatures'] + ')' if a['signatures'] else ''} {a['elapsed_s']:.1f}s"
    return s if visible else f"[{s}]"


def main():
    att = load_attempts()
    C = cells(att)
    cats = collections.Counter(a["category"] for a in att.values())
    assert set(cats) <= {"PASS", "FOCAL_DEFECT_WITNESS"}, cats
    ok_fail = sum(1 for a in att.values() if a["variant"] == "ok" and a["exit"] != 0)
    ok_focal = sum(1 for a in att.values() if a["variant"] == "ok" and focal(a))
    # Consistency: exit != 0 <=> focal (no other failure kinds recorded).
    mism = [a["attempt_id"] for a in att.values() if (a["exit"] != 0) != focal(a)]

    counts = {}
    for s in SUBJECTS:
        row = {}
        for prof in ("R", "L"):
            trips = [C[(s, b, prof, "bad")] for b in range(1, 11)]
            row[f"{prof}/P1"] = sum(supported_block(p1_prefix(t)) for t in trips)
            row[f"{prof}/P3"] = sum(supported_block(p3_prefix(t)) for t in trips)
            row[f"{prof}/all_attempt_focal"] = sum(focal(a) for t in trips for a in t)
            row[f"{prof}/first_attempt_focal"] = sum(focal(t[0]) for t in trips)
            row[f"{prof}/attempts_2_3_focal"] = sum(focal(a) for t in trips for a in t[1:])
            row[f"{prof}/P3_accept_after_focal"] = sum(
                1 for t in trips if not blocks(p3_prefix(t)) and any(focal(a) for a in p3_prefix(t)))
            okt = [C[(s, b, prof, "ok")] for b in range(1, 11)]
            row[f"{prof}/ok_nonpass"] = sum(a["exit"] != 0 for t in okt for a in t)
        for pol in ("P1", "P3"):
            d = []
            for b in range(1, 11):
                pre = p1_prefix if pol == "P1" else p3_prefix
                d.append(supported_block(pre(C[(s, b, "R", "bad")])) - supported_block(pre(C[(s, b, "L", "bad")])))
            row[f"{pol}/d_plus_minus_zero"] = [d.count(1), d.count(-1), d.count(0)]
            row[f"{pol}/delta"] = sum(d) / 10
            row[f"{pol}/batchA"] = sum(d[:5]) / 5
            row[f"{pol}/batchB"] = sum(d[5:]) / 5
        counts[s] = row

    # Execution context for etcd5509 blocks.
    ev = load_jsonl(STUDY / "events.jsonl")
    block_load = {}
    session_of_block = {}
    for e in ev:
        if e["kind"] == "block_start":
            block_load[e["block"]] = e["host_load"]["host_load_percent"]
            session_of_block[e["block"]] = e["session"]
    by_seq = sorted(att.values(), key=lambda a: a["seq"])
    rows = []
    for b in range(1, 11):
        blk = [a for a in by_seq if a["block"] == b]
        subj_order = []
        for a in blk:
            if a["subject"] not in subj_order:
                subj_order.append(a["subject"])
        pos = subj_order.index("etcd5509") + 1
        prev_subj = subj_order[pos - 2] if pos > 1 else "(block start)"
        mine = [a for a in blk if a["subject"] == "etcd5509"]
        cell_order = []
        for a in mine:
            lab = f"{a['profile']}/{a['variant']}"
            if lab not in cell_order:
                cell_order.append(lab)
        for prof in ("R", "L"):
            for var in ("bad", "ok"):
                t = C[("etcd5509", b, prof, var)]
                p1v = {x["attempt_id"] for x in p1_prefix(t)}
                p3v = {x["attempt_id"] for x in p3_prefix(t)}
                rows.append({
                    "block": b,
                    "batch": t[0]["batch"],
                    "subject_position_in_block": pos,
                    "preceding_subject": prev_subj,
                    "host_load_pct_at_block_start": block_load.get(b),
                    "cell_order": " > ".join(cell_order),
                    "cell_position": cell_order.index(f"{prof}/{var}") + 1,
                    "profile": prof,
                    "variant": var,
                    "first_seq": t[0]["seq"],
                    "a1": f"{'F' if focal(t[0]) else 'P'}{'(' + t[0]['signatures'] + ')' if t[0]['signatures'] else ''}",
                    "a1_s": round(t[0]["elapsed_s"], 3),
                    "a2": f"{'F' if focal(t[1]) else 'P'}{'(' + t[1]['signatures'] + ')' if t[1]['signatures'] else ''}",
                    "a2_s": round(t[1]["elapsed_s"], 3),
                    "a3": f"{'F' if focal(t[2]) else 'P'}{'(' + t[2]['signatures'] + ')' if t[2]['signatures'] else ''}",
                    "a3_s": round(t[2]["elapsed_s"], 3),
                    "P1_visible": "a1",
                    "P1_suffix_research_only": "a2,a3",
                    "P1_gate": "BLOCK" if blocks(p1_prefix(t)) else "ACCEPT",
                    "P3_visible": ",".join(f"a{x['attempt']}" for x in p3_prefix(t)),
                    "P3_suffix_research_only": ",".join(f"a{x['attempt']}" for x in t if x["attempt_id"] not in p3v) or "-",
                    "P3_gate": "BLOCK" if blocks(p3_prefix(t)) else "ACCEPT",
                    "S_P1": supported_block(p1_prefix(t)) if var == "bad" else "",
                    "S_P3": supported_block(p3_prefix(t)) if var == "bad" else "",
                    "started_utc_a1": t[0]["started_utc"],
                    "attempt_ids": " ".join(x["attempt_id"] for x in t),
                })
    write_csv("s01_etcd5509_blocks.csv", rows)

    # Markdown rendering: bad cells (both profiles side-by-side) + ok summary.
    md = ["| Blk | Batch | Pos (prev subject) | Load % | Cell order | R/bad a1 · a2 · a3 | R P1/P3 | L/bad a1 · a2 · a3 | L P1/P3 | d P1 / d P3 |",
          "|---:|---|---|---:|---|---|---|---|---|---|"]
    for b in range(1, 11):
        rr = {(r["profile"], r["variant"]): r for r in rows if r["block"] == b}
        R, L = rr[("R", "bad")], rr[("L", "bad")]

        def trip(r):
            t = C[("etcd5509", b, r["profile"], "bad")]
            p3v = {x["attempt_id"] for x in p3_prefix(t)}
            parts = []
            for x in t:
                s = f"{'F' if focal(x) else 'P'} {x['elapsed_s']:.1f}"
                # visible to P1 = a1 only; visible to P3 = p3 prefix; mark P3-suffix with []
                if x["attempt"] == 1:
                    s = f"**{s}**"
                elif x["attempt_id"] not in p3v:
                    s = f"[{s}]"
                parts.append(s)
            return " · ".join(parts)
        order = R["cell_order"].replace("/bad", "b").replace("/ok", "o")
        md.append(f"| {b} | {R['batch']} | {R['subject_position_in_block']} ({R['preceding_subject']}) | {R['host_load_pct_at_block_start']} | {order} | "
                  f"{trip(R)} | {R['S_P1']}/{R['S_P3']} | {trip(L)} | {L['S_P1']}/{L['S_P3']} | "
                  f"{R['S_P1'] - L['S_P1']:+d} / {R['S_P3'] - L['S_P3']:+d} |")
    okd = collections.defaultdict(list)
    for r in rows:
        if r["variant"] == "ok":
            okd[r["profile"]] += [r["a1_s"], r["a2_s"], r["a3_s"]]
    md.append("")
    md.append("Acceptable variant (V_ok): " + "; ".join(
        f"{p}: 30/30 PASS, elapsed {min(v):.2f}-{max(v):.2f} s (median {sorted(v)[15]:.2f})" for p, v in sorted(okd.items(), reverse=True)))
    (OUT / "s01_etcd5509_blocks.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")

    res = {
        "label": "EXPLORATORY/POST-HOC s01",
        "categories": dict(cats),
        "ok_variant_nonpass": ok_fail,
        "ok_variant_focal": ok_focal,
        "exit_vs_focal_mismatches": mism,
        "counts": counts,
        "claimed_etcd5509": {"R/P1": 7, "L/P1": 10, "R/P3": 5, "L/P3": 7, "R/all": 24, "L/all": 26},
    }
    e = counts["etcd5509"]
    res["claims_verified"] = (e["R/P1"], e["L/P1"], e["R/P3"], e["L/P3"], e["R/all_attempt_focal"], e["L/all_attempt_focal"]) == (7, 10, 5, 7, 24, 26)
    write_json("s01_counts.json", res)
    print("claims_verified", res["claims_verified"], dict(cats), "ok nonpass", ok_fail)
    for s, r in counts.items():
        print(s, {k: v for k, v in r.items()})
    print("\n".join(md))


if __name__ == "__main__":
    main()
