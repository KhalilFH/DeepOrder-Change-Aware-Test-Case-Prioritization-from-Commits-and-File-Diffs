"""The frozen C1 analysis (analysis_plan.md): matched R/L blocks per subject.

Reused from E1 unchanged: `policy.reduce_block` and the prefix helpers, the
`Trace` join of records with annotations, the `S`/`N` indicator rules,
`paired_contrast` (exact paired intervals plus fill-the-unknowns bounds over
all scheduled blocks) and `clopper_pearson`.

New here: the R-vs-L pairing on a shared block index, E/M/W indicators, the
retry-loss interaction with enumerated missingness bounds, per-batch
contrasts, the independent-attempt retry diagnostic, the C2/C3 mechanical gate
flags, and an independent recomputation of the primary numerators.

Unknown is never zero: a missing, invalid or unresolved indicator stays `None`
and widens the bounds instead.
"""

from __future__ import annotations

import csv
import hashlib
import io
import itertools
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

from analysis import Trace, clopper_pearson, join_annotations, n_indicator, paired_contrast, rate, s_indicator
from ledger import read_records, verify_chain
from policy import (
    ACCEPT,
    ACCEPT_WITH_PRIOR_FAILURE,
    BLOCK,
    FOCAL_DEFECT_WITNESS,
    HARNESS_INVALID,
    INDETERMINATE,
    P1,
    P3,
    P3_RETAIN,
    POLICIES,
    UNRESOLVED,
    reduce_block,
)

from c1_harness.budget import GAP_S
from c1_harness.schedule import BATCHES, BLOCKS

ANALYSIS_VERSION = "c1-matched/1"
FOLLOW_UP_MARGIN = 0.20
INVALID_LIMIT = 0.10
FAMILY_ALPHA = 0.05
V_BAD, V_OK = "V_bad", "V_ok"
PROFILE_VCPUS = {"R": 16, "L": 2}


# --- indicators ---------------------------------------------------------------------


def _categories_padded(trace: Trace, n: int) -> list[frozenset[str]]:
    return trace.categories + [frozenset()] * max(0, n - len(trace.categories))


def e_indicator(decision, cats: Sequence[frozenset[str]]) -> int | None:
    """Focal evidence in the defective variant's consumed prefix, whatever the gate did."""
    prefix = [cats[i - 1] for i in decision.consumed_indices if i <= len(cats)]
    if any(FOCAL_DEFECT_WITNESS in c for c in prefix):
        return 1
    if decision.final_status == INDETERMINATE:
        return None
    if any(UNRESOLVED in c for c in prefix):
        return None
    return 0


def m_indicator(decision, cats: Sequence[frozenset[str]]) -> int | None:
    """Accepting defective variant with supported focal evidence in its prefix (masked)."""
    if decision.final_status == INDETERMINATE:
        return None
    if decision.final_status == BLOCK:
        return 0
    failing = [cats[i - 1] for i in decision.prior_failure_indices]
    if any(FOCAL_DEFECT_WITNESS in c for c in failing):
        return 1
    if any(UNRESOLVED in c for c in failing):
        return None
    return 0


def b_indicator(decision) -> int | None:
    return {BLOCK: 1, ACCEPT: 0}.get(decision.final_status)


# --- inputs ---------------------------------------------------------------------------


def load_measured(measured_dir: Path) -> tuple[dict[tuple[str, str], list[dict[str, Any]]], list[dict[str, Any]]]:
    """Records by (subject, profile) from `<subject>__<profile>.jsonl`, chains verified."""
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for path in sorted(measured_dir.glob("*__*.jsonl")):
        subject, profile = path.stem.split("__")
        verify_chain(path)
        rows = read_records(path)
        for r in rows:
            if r["episode"] != subject or r["condition"] != profile:
                raise ValueError(f"{path.name}: record {r['seq']} names {r['episode']}/{r['condition']}")
        by_key[(subject, profile)] = rows
    ids = [(r.get("extra") or {}).get("attempt_id") for rows in by_key.values() for r in rows]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise ValueError(f"duplicate attempt ids across measured ledgers: {sorted(dup)[:5]}")
    all_rows = [r for rows in by_key.values() for r in rows]
    return by_key, all_rows


# --- per subject ----------------------------------------------------------------------


def analyse_subject(
    subject: str,
    records: dict[str, list[dict[str, Any]]],
    ann: dict[str, dict[str, Any]],
    alpha_each: float,
    questioned: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows_out: list[dict[str, Any]] = []
    vec: dict[str, dict[tuple[str, str], list[int | None]]] = {k: defaultdict(list) for k in ("S", "N", "E", "M", "Bbad", "Bok")}
    warnings: dict[tuple[str, str], list[str]] = defaultdict(list)
    prefix_cost: dict[tuple[str, str, str], list[float]] = defaultdict(lambda: [0, 0.0, 0.0])

    for block in BLOCKS:
        for profile in ("R", "L"):
            recs = records.get(profile, [])
            traces = {v: Trace.build(subject, block, v, recs, ann) for v in (V_BAD, V_OK)}
            for policy in POLICIES:
                for version, trace in traces.items():
                    decision = reduce_block(policy, trace.statuses)
                    cats = _categories_padded(trace, max(decision.attempts_consumed, len(trace.categories)))
                    if version == V_BAD:
                        s = s_indicator(decision, cats)
                        if questioned and s == 1:
                            s = None  # a questioned oracle cannot support a 1 until adjudicated
                        vec["S"][(profile, policy)].append(s)
                        vec["E"][(profile, policy)].append(e_indicator(decision, cats))
                        vec["M"][(profile, policy)].append(m_indicator(decision, cats))
                        vec["Bbad"][(profile, policy)].append(b_indicator(decision))
                    else:
                        vec["N"][(profile, policy)].append(n_indicator(decision, cats))
                        vec["Bok"][(profile, policy)].append(b_indicator(decision))
                    if decision.report_flag == ACCEPT_WITH_PRIOR_FAILURE:
                        warnings[(profile, version)].append(
                            "+".join(sorted(set().union(*(cats[i - 1] for i in decision.prior_failure_indices))))
                        )
                    consumed = decision.consumed_indices
                    job = sum(
                        (trace.rows[i - 1].get("extra") or {}).get("job_elapsed_s", trace.rows[i - 1]["elapsed_s"]) + GAP_S
                        for i in consumed if i <= len(trace.rows) and trace.rows[i - 1] is not None
                    )
                    cost = prefix_cost[(profile, policy, version)]
                    cost[0] += decision.attempts_consumed
                    cost[1] += trace.elapsed(consumed)
                    cost[2] += job * PROFILE_VCPUS[profile] / 3600
                    rows_out.append({
                        "subject": subject, "block": block, "batch": "A" if block in BATCHES["A"] else "B",
                        "matched_block_id": f"c1v1-{subject}-b{block:02d}", "profile": profile,
                        "variant": version, "policy": policy, "final_status": decision.final_status,
                        "warning": decision.report_flag or "",
                        "decision_rule": {P1: "first attempt only", P3: "accept on first zero, block after 3 nonzero",
                                          P3_RETAIN: "P3 decision; flag accept after failure"}[policy],
                        "attempts_consumed": decision.attempts_consumed,
                        "consumed_attempt_ids": " ".join(_ids(trace, consumed)),
                        "research_only_attempt_ids": " ".join(_ids(trace, decision.research_only_indices)),
                        "prefix_categories": " | ".join("+".join(sorted(cats[i - 1])) or "-" for i in consumed),
                        "S": _cell(vec["S"][(profile, policy)][-1]) if version == V_BAD else "",
                        "E": _cell(vec["E"][(profile, policy)][-1]) if version == V_BAD else "",
                        "M": _cell(vec["M"][(profile, policy)][-1]) if version == V_BAD else "",
                        "N": _cell(vec["N"][(profile, policy)][-1]) if version == V_OK else "",
                        "prefix_elapsed_s": round(trace.elapsed(consumed), 3),
                        "prefix_capacity_vcpu_h": round(job * PROFILE_VCPUS[profile] / 3600, 6),
                        "indeterminate_reason": decision.indeterminate_reason or "",
                    })

    primary = {}
    for policy in (P1, P3):
        c = paired_contrast(vec["S"][("R", policy)], vec["S"][("L", policy)], alpha_each)
        c["missing_bounds_all_scheduled"] = c.pop("best_worst")
        c["counts"] = _counts(vec["S"][("R", policy)], vec["S"][("L", policy)])
        c["batches"] = {
            batch: paired_contrast(
                [vec["S"][("R", policy)][b - 1] for b in blocks],
                [vec["S"][("L", policy)][b - 1] for b in blocks],
                alpha_each,
            )
            for batch, blocks in BATCHES.items()
        }
        primary[policy] = c

    retry_loss = {
        profile: paired_contrast(vec["S"][(profile, P1)], vec["S"][(profile, P3)], 0.05 / 2)
        for profile in ("R", "L")
    }
    interaction = _interaction(vec["S"])

    summary = {
        "subject": subject,
        "questioned_oracle": questioned,
        "primary_delta_S": primary,
        "S_rates": {f"{p}/{pol}": rate(vec["S"][(p, pol)]) for p in ("R", "L") for pol in POLICIES},
        "E_rates": {f"{p}/{pol}": rate(vec["E"][(p, pol)]) for p in ("R", "L") for pol in POLICIES},
        "M_rates": {f"{p}/{pol}": rate(vec["M"][(p, pol)]) for p in ("R", "L") for pol in POLICIES},
        "N_rates": {f"{p}/{pol}": rate(vec["N"][(p, pol)]) for p in ("R", "L") for pol in POLICIES},
        "raw_block_bad": {f"{p}/{pol}": rate(vec["Bbad"][(p, pol)]) for p in ("R", "L") for pol in POLICIES},
        "raw_block_ok": {f"{p}/{pol}": rate(vec["Bok"][(p, pol)]) for p in ("R", "L") for pol in POLICIES},
        "raw_discrimination_D": {
            f"{p}/{pol}": _diff(rate(vec["Bbad"][(p, pol)])["rate"], rate(vec["Bok"][(p, pol)])["rate"])
            for p in ("R", "L") for pol in POLICIES
        },
        "retry_loss": retry_loss,
        "interaction_I": interaction,
        "p3_retain_warnings": {f"{p}/{v}": {"count": len(w), "prior_failure_categories": sorted(set(w))}
                               for (p, v), w in sorted(warnings.items())},
        "prefix_cost": {f"{p}/{pol}/{v}": {"attempts": c[0], "elapsed_s": round(c[1], 3), "capacity_vcpu_h": round(c[2], 6),
                                            "measured_cpu": None}
                        for (p, pol, v), c in sorted(prefix_cost.items())},
        "_vectors": {k: {f"{a}/{b}": v for (a, b), v in d.items()} for k, d in vec.items()},
    }
    return summary, rows_out


def _cell(v: int | None) -> str:
    return "" if v is None else str(v)


def _diff(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else a - b


def _ids(trace: Trace, indices: Sequence[int]) -> list[str]:
    out = []
    for i in indices:
        r = trace.rows[i - 1] if i <= len(trace.rows) else None
        out.append(f"a{i}:missing" if r is None else (r.get("extra") or {}).get("attempt_id", f"a{i}:seq{r['seq']}"))
    return out


def _counts(first: Sequence[int | None], second: Sequence[int | None]) -> dict[str, int]:
    d = [a - b for a, b in zip(first, second) if a is not None and b is not None]
    return {"n_plus": d.count(1), "n_minus": d.count(-1), "n_zero": d.count(0),
            "missing": len(first) - len(d), "scheduled": len(first)}


def _interaction(S: dict[tuple[str, str], list[int | None]]) -> dict[str, Any]:
    """I = L(L) - L(R), per block over the same four indicators; enumerated bounds."""
    lows, highs, complete = [], [], []
    for b in range(len(BLOCKS)):
        vals = [S[(p, pol)][b] for p, pol in (("L", P1), ("L", P3), ("R", P1), ("R", P3))]
        options = [[v] if v is not None else [0, 1] for v in vals]
        outcomes = [(a - c) - (e - f) for a, c, e, f in itertools.product(*options)]
        lows.append(min(outcomes))
        highs.append(max(outcomes))
        if all(v is not None for v in vals):
            complete.append(outcomes[0])
    n = len(BLOCKS)
    return {
        "complete_blocks": len(complete),
        "estimate_complete_case": sum(complete) / len(complete) if complete else None,
        "bounds_all_scheduled": [sum(lows) / n, sum(highs) / n],
        "note": "descriptive; built from the same four indicators as the primary contrasts, not independent",
    }


# --- attempt-level views ------------------------------------------------------------


def attempt_index(all_rows: Sequence[dict[str, Any]], ann: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in all_rows:
        a = ann[r["sha256"]]
        x = r.get("extra") or {}
        out.append({
            "attempt_id": x.get("attempt_id"), "matched_block_id": x.get("matched_block_id"),
            "stage": x.get("stage"), "batch": x.get("batch"), "subject": r["episode"], "profile": r["condition"],
            "block": r["block"], "variant": r["version"], "attempt": r["attempt"],
            "scheduled_seq": x.get("scheduled_seq"), "record_seq": r["seq"], "record_sha256": r["sha256"],
            "started_utc": r["started_utc"], "ended_utc": r["ended_utc"], "elapsed_s": r["elapsed_s"],
            "job_elapsed_s": x.get("job_elapsed_s"), "exit_status": r["exit_status"], "timed_out": r["timed_out"],
            "cleanup_ok": (x.get("cleanup") or {}).get("verified_absent"), "profile_verified": x.get("profile_verified"),
            "cpu_quota": (x.get("inspect") or {}).get("cpu_quota"), "cpu_period": (x.get("inspect") or {}).get("cpu_period"),
            "categories": "+".join(a["categories"]), "signatures": "+".join(a["signatures"]),
            "annotation_source": a["source"], "stdout_sha256": x.get("stdout_sha256"), "stderr_sha256": x.get("stderr_sha256"),
        })
    return out


def invalid_fraction(rows: Sequence[dict[str, Any]], ann: dict[str, dict[str, Any]], subject: str, scheduled: int) -> dict[str, Any]:
    mine = [r for r in rows if r["episode"] == subject]
    invalid = sum(1 for r in mine if HARNESS_INVALID in ann[r["sha256"]]["categories"])
    return {"scheduled_attempts": scheduled, "recorded_attempts": len(mine), "harness_invalid": invalid,
            "invalid_fraction_of_scheduled": invalid / scheduled if scheduled else None}


def retry_diagnostic(records: dict[str, list[dict[str, Any]]], ann: dict[str, dict[str, Any]], subject: str) -> dict[str, Any]:
    """Batch-A raw attempt failure rate p; predicted P3 block p^3 vs batch-B observed. Descriptive."""
    out = {}
    for profile in ("R", "L"):
        recs = records.get(profile, [])
        for version in (V_BAD, V_OK):
            a = [r for r in recs if r["version"] == version and r["block"] in BATCHES["A"]
                 and HARNESS_INVALID not in ann[r["sha256"]]["categories"] and r["exit_status"] is not None]
            fails = sum(1 for r in a if r["exit_status"] != 0)
            p = fails / len(a) if a else None
            observed = [
                b_indicator(reduce_block(P3, Trace.build(subject, b, version, recs, ann).statuses))
                for b in BATCHES["B"]
            ]
            known = [x for x in observed if x is not None]
            out[f"{profile}/{version}"] = {
                "batch_a_attempts": len(a), "batch_a_failures": fails, "p": p,
                "p_ci95": list(clopper_pearson(fails, len(a), 0.05)) if a else None,
                "predicted_p3_block_p_cubed": None if p is None else p ** 3,
                "batch_b_observed_p3_blocks": sum(known), "batch_b_known_blocks": len(known),
            }
    return out


# --- independent arithmetic check ----------------------------------------------------


def crosscheck_primary(records: dict[str, list[dict[str, Any]]], ann: dict[str, dict[str, Any]], subject: str) -> dict[str, Any]:
    """Recompute S(P1) and S(P3) numerators without the policy module, from raw attempts."""
    out = {}
    for profile in ("R", "L"):
        by_block: dict[int, dict[int, dict[str, Any]]] = defaultdict(dict)
        for r in records.get(profile, []):
            if r["version"] == V_BAD:
                by_block[r["block"]][r["attempt"]] = r
        for policy, budget in ((P1, 1), (P3, 3)):
            ones = 0
            for block in BLOCKS:
                seen_focal = False
                blocked = False
                for i in range(1, budget + 1):
                    r = by_block[block].get(i)
                    if r is None:
                        break
                    cats = ann[r["sha256"]]["categories"]
                    if HARNESS_INVALID in cats:
                        break
                    if r["exit_status"] == 0:
                        break
                    seen_focal = seen_focal or FOCAL_DEFECT_WITNESS in cats
                    if i == budget:
                        blocked = True
                if blocked and seen_focal:
                    ones += 1
            out[f"{profile}/{policy}"] = ones
    return out


# --- entry point -----------------------------------------------------------------------


def analyse(
    measured_dir: Path,
    annotations_path: Path,
    enrolled: Sequence[str],
    projects: dict[str, str],
    questioned: Sequence[str] = (),
) -> dict[str, Any]:
    by_key, all_rows = load_measured(measured_dir)
    anns = read_records(annotations_path)
    inputs = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(measured_dir.glob("*.jsonl"))}
    ann = join_annotations(all_rows, anns)
    family = 2 * len(enrolled)  # K, frozen before collection; never shrunk
    alpha_each = FAMILY_ALPHA / (2 * family)
    subjects, decisions = [], []
    for sid in enrolled:
        records = {p: by_key.get((sid, p), []) for p in ("R", "L")}
        summary, rows = analyse_subject(sid, records, ann, alpha_each, sid in questioned)
        summary["invalid"] = invalid_fraction(all_rows, ann, sid, scheduled=len(BLOCKS) * 12)
        summary["retry_diagnostic"] = retry_diagnostic(records, ann, sid)
        check = crosscheck_primary(records, ann, sid)
        main = {f"{p}/{pol}": summary["S_rates"][f"{p}/{pol}"]["count"] for p in ("R", "L") for pol in (P1, P3)}
        summary["crosscheck"] = {"independent": check, "main": main, "agree": check == main or questioned}
        focal_on_ok = [r.get("extra", {}).get("attempt_id") for p in ("R", "L") for r in records[p]
                       if r["version"] == V_OK and FOCAL_DEFECT_WITNESS in ann[r["sha256"]]["categories"]]
        summary["acceptable_variant_focal_matches"] = focal_on_ok
        subjects.append(summary)
        decisions.extend(rows)

    analyzable = [s for s in subjects if s["invalid"]["invalid_fraction_of_scheduled"] is not None
                  and s["invalid"]["invalid_fraction_of_scheduled"] <= INVALID_LIMIT
                  and s["primary_delta_S"][P1]["complete_blocks"] > 0 and not s["questioned_oracle"]]
    c2 = {
        "analyzable_subjects": [s["subject"] for s in analyzable],
        "analyzable_projects": sorted({projects[s["subject"]] for s in analyzable}),
        "passed": len(analyzable) >= 4 and len({projects[s["subject"]] for s in analyzable}) >= 2,
    }
    c3 = []
    for s in analyzable:
        for policy in (P1, P3):
            c = s["primary_delta_S"][policy]
            est = c["estimate"]
            a, b = c["batches"]["A"]["estimate"], c["batches"]["B"]["estimate"]
            lo, hi = c["missing_bounds_all_scheduled"]
            sign = 0 if not est else (1 if est > 0 else -1)
            same = sign != 0 and a is not None and b is not None and a * sign > 0 and b * sign > 0
            retain = sign != 0 and lo is not None and ((sign > 0 and lo > 0) or (sign < 0 and hi < 0))
            c3.append({"subject": s["subject"], "policy": policy, "estimate": est, "batch_A": a, "batch_B": b,
                       "bounds": [lo, hi], "abs_ge_margin": est is not None and abs(est) >= FOLLOW_UP_MARGIN,
                       "same_direction_both_batches": same, "bounds_retain_direction": retain,
                       "signal": bool(est is not None and abs(est) >= FOLLOW_UP_MARGIN and same and retain)})
    return {
        "meta": {
            "analysis_version": ANALYSIS_VERSION, "family_K": family, "alpha_each_category_interval": alpha_each,
            "follow_up_margin": FOLLOW_UP_MARGIN, "invalid_limit": INVALID_LIMIT, "enrolled": list(enrolled),
            "questioned_pairs": list(questioned), "scheduled_blocks": len(BLOCKS), "inputs": inputs,
        },
        "subjects": subjects,
        "gates": {"C2": c2, "C3": {"rows": c3, "any_signal": any(r["signal"] for r in c3)}},
        "_decisions": decisions,
        "_attempt_index": attempt_index(all_rows, ann),
    }


def write_outputs(result: dict[str, Any], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    decisions = result.pop("_decisions")
    index = result.pop("_attempt_index")

    def write_csv(name: str, rows: Sequence[dict[str, Any]]) -> None:
        buf = io.StringIO(newline="")
        if rows:
            w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        (out / name).write_text(buf.getvalue(), encoding="utf-8", newline="\n")

    write_csv("attempt_index.csv", index)
    write_csv("policy_decisions.csv", decisions)
    contrasts = []
    for s in result["subjects"]:
        for policy in (P1, P3):
            c = s["primary_delta_S"][policy]
            contrasts.append({
                "subject": s["subject"], "policy": policy, "estimate": c["estimate"],
                "interval_lo": (c["interval"] or [None, None])[0], "interval_hi": (c["interval"] or [None, None])[1],
                "bound_lo": c["missing_bounds_all_scheduled"][0], "bound_hi": c["missing_bounds_all_scheduled"][1],
                **c["counts"], "complete_blocks": c["complete_blocks"],
                "batch_A_estimate": c["batches"]["A"]["estimate"], "batch_B_estimate": c["batches"]["B"]["estimate"],
                "invalid_fraction": s["invalid"]["invalid_fraction_of_scheduled"],
                "questioned_oracle": s["questioned_oracle"],
            })
    write_csv("subject_contrasts.csv", contrasts)
    for s in result["subjects"]:
        s.pop("_vectors", None)
    (out / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (out / "report.md").write_text(render(result), encoding="utf-8", newline="\n")
    (out / "reproduction.md").write_text(reproduction(result, out), encoding="utf-8", newline="\n")


def reproduction(result: dict[str, Any], out: Path) -> str:
    """Literal commands plus digests of every input and output (analysis plan section 5)."""
    import hashlib
    import platform

    from c1_harness import REPO_ROOT

    def digest(p: Path) -> str:
        return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()

    code = {rel: digest(REPO_ROOT / rel) for rel in (
        "c1_harness/matched.py", "c1_harness/cards.py", "e1_harness/analysis.py", "e1_harness/policy.py",
        "e1_harness/oracle.py", "e1_harness/ledger.py")}
    lines = [
        "# C1 analysis reproduction",
        "",
        "Commands (repository root):",
        "",
        "```",
        "python -m c1_harness.cli annotate --stage measured",
        "python -m c1_harness.cli analyze --out analysis",
        "```",
        "",
        f"Analysis version `{result['meta']['analysis_version']}`; Python {platform.python_version()}.",
        "",
        "| Input or code | SHA-256 (inputs raw; code LF-normalized) |",
        "|---|---|",
        *[f"| `{k}` | `{v}` |" for k, v in sorted(result["meta"]["inputs"].items())],
        *[f"| `{k}` | `{v}` |" for k, v in sorted(code.items())],
        "",
        "| Output | SHA-256 (LF-normalized) |",
        "|---|---|",
        *[f"| `{name}` | `{digest(out / name)}` |" for name in
          ("attempt_index.csv", "policy_decisions.csv", "subject_contrasts.csv", "summary.json", "report.md")],
        "",
    ]
    return "\n".join(lines)


def _f(x: float | None) -> str:
    return "n/a" if x is None else f"{x:+.3f}"


def render(result: dict[str, Any]) -> str:
    m = result["meta"]
    lines = [
        "# C1 matched-block analysis (mechanical output)",
        "",
        f"`{m['analysis_version']}`; K = {m['family_K']}; each category interval at "
        f"{1 - m['alpha_each_category_interval']:.5f}. Observations, interpretation and proposals are "
        "written separately by the researcher; this file only renders frozen computations.",
        "",
        "| Subject | Policy | Delta_S = S(R)-S(L) | Simultaneous interval | Bounds over 10 scheduled | +/-/0/missing | Batch A | Batch B |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in result["subjects"]:
        for policy in (P1, P3):
            c = s["primary_delta_S"][policy]
            k = c["counts"]
            iv = c["interval"]
            lines.append(
                f"| {s['subject']} | {policy} | {_f(c['estimate'])} | "
                f"{'n/a' if iv is None else f'[{iv[0]:+.3f}, {iv[1]:+.3f}]'} | "
                f"[{_f(c['missing_bounds_all_scheduled'][0])}, {_f(c['missing_bounds_all_scheduled'][1])}] | "
                f"{k['n_plus']}/{k['n_minus']}/{k['n_zero']}/{k['missing']} | "
                f"{_f(c['batches']['A']['estimate'])} | {_f(c['batches']['B']['estimate'])} |"
            )
    g = result["gates"]
    lines += ["", f"C2 (mechanical): {'pass' if g['C2']['passed'] else 'not met'}; analyzable {g['C2']['analyzable_subjects']}.",
              f"C3 (mechanical): any signal = {g['C3']['any_signal']}.", ""]
    return "\n".join(lines) + "\n"
