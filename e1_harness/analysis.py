"""E1 analysis: apply the frozen contrast rules to a ledger and its annotations.

Implements plan 4.5 for the measured blocks of each episode:

- `S(e,p)`: share of `V_bad` blocks whose *blocking* outcome has a focal
  witness in the policy-visible prefix.
- `N(e,p)`: share of `V_ok` blocks blocked solely by verified nuisance.
- `L(e) = S(e,P1) - S(e,P3)` and `R(e) = N(e,P1) - N(e,P3)`, from paired block
  differences in {-1, 0, 1}.

Also: raw blocking on both versions, focal witnesses generated versus retained
versus ignored by the final gate, `ACCEPT_WITH_PRIOR_FAILURE`, prefix attempt
counts, wall time and allocated vCPU-hours.

Rules this script holds, each from the plan:

**Nothing is imputed silently.** A block indicator is `None` when the data do
not determine it: an `INDETERMINATE` decision, or a block whose failing prefix
holds an `UNRESOLVED` attempt that could have gone either way. Contrasts are
reported complete-case *and* with conservative best/worst assignments of every
unknown (plan 4.5, "publish denominators and conservative best/worst
assignments").

**Intervals are exact and paired.** For each contrast, exact Clopper-Pearson
intervals for the positive- and negative-difference probabilities are
subtracted. Bonferroni runs over every interval in the family (two per
contrast), so the contrast intervals have simultaneous coverage under
independent-block sampling. This is the plan's E2 rule applied to whatever
family this run reports; E1 remains descriptive calibration.

**`HARNESS_INVALID` is not an exit status.** Such an attempt enters the reducer
as `None`, as `policy.reduce_block` specifies, so the decision it would have
fed becomes `INDETERMINATE` rather than being read from an invalid run.

**Measured blocks are declared, not discovered.** `--blocks` names the
preassigned range; a declared block with no records is reported missing, not
skipped. Direct-policy checks (`--direct-blocks`) are analysed separately and
never enter `S` or `N`.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from ledger import MAX_ATTEMPTS_PER_BLOCK, V_BAD, V_OK, read_records, verify_chain
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
    RETRY_BUDGET,
    UNRESOLVED,
    VERIFIED_NUISANCE,
    Decision,
    blocked_solely_by_nuisance,
    focal_evidence_in_prefix,
    reduce_block,
)

ANALYSIS_VERSION = "e1-analysis/1"

L_MARGIN = 0.10
R_MARGIN = 0.05

DECISION_RULES = {
    P1: "P1: first attempt only; nonzero blocks, zero accepts",
    P3: f"P3: stop at first zero and accept; block after {RETRY_BUDGET} nonzero",
    P3_RETAIN: "P3-retain: P3's prefix and decision; accept after a failure is flagged",
}


class AnalysisError(ValueError):
    """The inputs do not support an analysis."""


# --- exact binomial intervals -----------------------------------------------


def _binom_cdf(k: int, n: int, p: float) -> float:
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def _bisect(f, target: float, increasing: bool) -> float:
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if (f(mid) < target) == increasing:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def clopper_pearson(x: int, n: int, alpha: float) -> tuple[float, float]:
    """Exact two-sided `1 - alpha` interval for a binomial proportion."""
    if n == 0:
        return (0.0, 1.0)
    if not 0 <= x <= n:
        raise AnalysisError(f"{x} successes out of {n}")
    lower = 0.0 if x == 0 else _bisect(
        lambda p: 1 - _binom_cdf(x - 1, n, p), alpha / 2, increasing=True
    )
    upper = 1.0 if x == n else _bisect(
        lambda p: _binom_cdf(x, n, p), alpha / 2, increasing=False
    )
    return (lower, upper)


# --- inputs -------------------------------------------------------------------


def parse_blocks(spec: str | None) -> list[int]:
    """`"1-20,25"` -> [1, ..., 20, 25]."""
    if not spec:
        return []
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = (int(x) for x in part.split("-", 1))
            if a > b:
                raise AnalysisError(f"block range {part!r} runs backwards")
            out.update(range(a, b + 1))
        elif part:
            out.add(int(part))
    return sorted(out)


def _file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def join_annotations(
    records: Sequence[dict[str, Any]], annotations: Sequence[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Annotation per record sha256. Every record needs exactly one, and vice versa."""
    by_sha: dict[str, dict[str, Any]] = {}
    for a in annotations:
        key = a["record_sha256"]
        if key in by_sha:
            raise AnalysisError(f"record {key[:12]} is annotated twice")
        by_sha[key] = a
    for row in records:
        a = by_sha.get(row["sha256"])
        if a is None:
            raise AnalysisError(
                f"attempt {_ident(row)} has no annotation; classify the whole "
                "ledger before analysing it"
            )
        if _ident(a) != _ident(row):
            raise AnalysisError(f"annotation for {row['sha256'][:12]} names {_ident(a)}")
    extra = set(by_sha) - {r["sha256"] for r in records}
    if extra:
        raise AnalysisError(f"{len(extra)} annotations name records absent from the ledger")
    return by_sha


def _ident(row: dict[str, Any]) -> str:
    return f"{row['episode']}/b{row['block']}/{row['version']}/a{row['attempt']}"


# --- one version of one block ---------------------------------------------------


@dataclass
class Trace:
    """One version's recorded attempts in a block, with their annotations."""

    episode: str
    block: int
    version: str
    rows: list[dict[str, Any] | None]
    categories: list[frozenset[str]]

    @classmethod
    def build(
        cls,
        episode: str,
        block: int,
        version: str,
        records: Iterable[dict[str, Any]],
        ann: dict[str, dict[str, Any]],
    ) -> "Trace":
        found = {
            r["attempt"]: r
            for r in records
            if (r["episode"], r["block"], r["version"]) == (episode, block, version)
        }
        width = max(found, default=0)
        rows = [found.get(i) for i in range(1, width + 1)]
        cats = [
            frozenset(ann[r["sha256"]]["categories"]) if r is not None else frozenset()
            for r in rows
        ]
        return cls(episode, block, version, rows, cats)

    @property
    def statuses(self) -> list[int | None]:
        """What the reducer may read: exit statuses, with invalid runs as `None`."""
        return [
            None if (r is None or HARNESS_INVALID in c) else r["exit_status"]
            for r, c in zip(self.rows, self.categories)
        ]

    @property
    def complete(self) -> bool:
        return len(self.rows) == MAX_ATTEMPTS_PER_BLOCK and all(
            r is not None and HARNESS_INVALID not in c
            for r, c in zip(self.rows, self.categories)
        )

    def attempt_ids(self, indices: Iterable[int]) -> list[str]:
        out = []
        for i in indices:
            r = self.rows[i - 1] if i <= len(self.rows) else None
            out.append(f"a{i}:missing" if r is None else f"a{i}:seq{r['seq']}:{r['sha256'][:12]}")
        return out

    def elapsed(self, indices: Iterable[int]) -> float:
        return sum(
            self.rows[i - 1]["elapsed_s"]
            for i in indices
            if i <= len(self.rows) and self.rows[i - 1] is not None
        )

    def started(self) -> str | None:
        present = [r["started_utc"] for r in self.rows if r is not None]
        return min(present) if present else None


def s_indicator(decision: Decision, categories: Sequence[frozenset[str]]) -> int | None:
    """1: block supported by a focal witness in the prefix; 0: not; None: undetermined."""
    if decision.final_status == INDETERMINATE:
        return None
    if focal_evidence_in_prefix(decision, categories):
        return 1
    if decision.final_status == BLOCK and any(
        UNRESOLVED in categories[i - 1] for i in decision.prior_failure_indices
    ):
        return None
    return 0


def n_indicator(decision: Decision, categories: Sequence[frozenset[str]]) -> int | None:
    """1: blocked solely by verified nuisance; 0: not; None: undetermined."""
    if decision.final_status == INDETERMINATE:
        return None
    if blocked_solely_by_nuisance(decision, categories):
        return 1
    if decision.final_status == BLOCK:
        failing = [categories[i - 1] for i in decision.prior_failure_indices]
        could_be = all(c <= {VERIFIED_NUISANCE, UNRESOLVED} for c in failing)
        if could_be and any(UNRESOLVED in c for c in failing):
            return None
    return 0


# --- contrasts ------------------------------------------------------------------


def paired_contrast(
    first: Sequence[int | None], second: Sequence[int | None], alpha_each: float
) -> dict[str, Any]:
    """`first - second` over paired blocks, complete-case plus best/worst bounds."""
    if len(first) != len(second):
        raise AnalysisError("paired vectors differ in length")
    pairs = [(a, b) for a, b in zip(first, second) if a is not None and b is not None]
    n = len(pairs)
    pos = sum(1 for a, b in pairs if a - b == 1)
    neg = sum(1 for a, b in pairs if a - b == -1)
    pos_ci = clopper_pearson(pos, n, alpha_each)
    neg_ci = clopper_pearson(neg, n, alpha_each)

    def filled(hi_first: bool) -> float | None:
        if not first:
            return None
        a = [x if x is not None else int(hi_first) for x in first]
        b = [x if x is not None else int(not hi_first) for x in second]
        return sum(x - y for x, y in zip(a, b)) / len(a)

    return {
        "blocks": len(first),
        "complete_blocks": n,
        "undetermined_blocks": len(first) - n,
        "positive": pos,
        "negative": neg,
        "estimate": (pos - neg) / n if n else None,
        "interval": [pos_ci[0] - neg_ci[1], pos_ci[1] - neg_ci[0]] if n else None,
        "interval_confidence_each_side": 1 - alpha_each,
        "best_worst": [filled(hi_first=False), filled(hi_first=True)],
    }


def margin_position(interval: Sequence[float] | None, margin: float) -> str:
    if interval is None:
        return "no complete blocks"
    if interval[1] < margin:
        return "upper bound below margin"
    if interval[0] > margin:
        return "lower bound above margin"
    return "interval contains margin"


def rate(values: Sequence[int | None]) -> dict[str, Any]:
    known = [v for v in values if v is not None]
    x, n = sum(known), len(known)
    lo, hi = clopper_pearson(x, n, 0.05)
    return {
        "count": x,
        "denominator": n,
        "undetermined": len(values) - n,
        "rate": x / n if n else None,
        "ci95": [lo, hi] if n else None,
    }


# --- per-episode analysis -----------------------------------------------------


def analyse_episode(
    episode: str,
    blocks: Sequence[int],
    records: Sequence[dict[str, Any]],
    ann: dict[str, dict[str, Any]],
    vcpus: float,
    batches: Sequence[Sequence[int]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows_out: list[dict[str, Any]] = []
    s: dict[str, list[int | None]] = {p: [] for p in POLICIES}
    n: dict[str, list[int | None]] = {p: [] for p in POLICIES}
    raw: dict[tuple[str, str], list[str]] = {}
    witness = {p: {"generated": 0, "in_prefix": 0, "ignored_by_gate": 0, "research_only": 0} for p in POLICIES}
    retain_flags = 0
    prefix_cost = {(p, v): [0, 0.0] for p in POLICIES for v in (V_BAD, V_OK)}
    invalid_blocks: list[int] = []
    missing_blocks: list[int] = []
    counterpart_witnesses: list[str] = []
    first_versions: dict[int, str | None] = {}

    for block in blocks:
        traces = {v: Trace.build(episode, block, v, records, ann) for v in (V_BAD, V_OK)}
        if not any(t.rows for t in traces.values()):
            missing_blocks.append(block)
        if not all(t.complete for t in traces.values()):
            invalid_blocks.append(block)
        seqs = {v: min((r["seq"] for r in t.rows if r), default=None) for v, t in traces.items()}
        ordered = sorted((q, v) for v, q in seqs.items() if q is not None)
        first_versions[block] = ordered[0][1] if ordered else None

        ok = traces[V_OK]
        for i, c in enumerate(ok.categories, start=1):
            if FOCAL_DEFECT_WITNESS in c:
                counterpart_witnesses.append(ok.attempt_ids([i])[0])

        for version, trace in traces.items():
            for policy in POLICIES:
                decision = reduce_block(policy, trace.statuses)
                consumed = decision.consumed_indices
                cats = trace.categories + [frozenset()] * (decision.attempts_consumed - len(trace.categories))
                indicator = (s_indicator if version == V_BAD else n_indicator)(decision, cats)
                (s if version == V_BAD else n)[policy].append(indicator)
                raw.setdefault((policy, version), []).append(decision.final_status)
                cost = prefix_cost[(policy, version)]
                cost[0] += decision.attempts_consumed
                cost[1] += trace.elapsed(consumed)

                if version == V_BAD:
                    focal = [i for i, c in enumerate(trace.categories, 1) if FOCAL_DEFECT_WITNESS in c]
                    w = witness[policy]
                    w["generated"] += len(focal)
                    w["in_prefix"] += sum(1 for i in focal if i in consumed)
                    w["research_only"] += sum(1 for i in focal if i not in consumed)
                    if decision.final_status == ACCEPT:
                        w["ignored_by_gate"] += sum(1 for i in focal if i in consumed)
                if decision.report_flag == ACCEPT_WITH_PRIOR_FAILURE:
                    retain_flags += 1

                rows_out.append(
                    {
                        "episode": episode,
                        "block": block,
                        "version": version,
                        "first_version_in_block": first_versions[block],
                        "block_started_utc": trace.started(),
                        "policy": policy,
                        "final_status": decision.final_status,
                        "report_flag": decision.report_flag or "",
                        "decision_rule": DECISION_RULES[policy],
                        "attempts_consumed": decision.attempts_consumed,
                        "consumed_attempt_ids": " ".join(trace.attempt_ids(consumed)),
                        "research_only_attempt_ids": " ".join(
                            trace.attempt_ids(decision.research_only_indices)
                        ),
                        "prefix_categories": " | ".join(
                            "+".join(sorted(cats[i - 1])) or "-" for i in consumed
                        ),
                        "indicator": "S" if version == V_BAD else "N",
                        "indicator_value": "" if indicator is None else indicator,
                        "prefix_elapsed_s": round(trace.elapsed(consumed), 3),
                        "indeterminate_reason": decision.indeterminate_reason or "",
                    }
                )

    all_attempts = [r for r in records if r["episode"] == episode]
    measured = [r for r in all_attempts if r["block"] in set(blocks)]
    summary = {
        "episode": episode,
        "measured_blocks": len(blocks),
        "missing_blocks": missing_blocks,
        "invalid_blocks": invalid_blocks,
        "invalid_fraction": len(invalid_blocks) / len(blocks) if blocks else None,
        "block_order_first_version": {
            V_BAD: sum(1 for v in first_versions.values() if v == V_BAD),
            V_OK: sum(1 for v in first_versions.values() if v == V_OK),
        },
        "counterpart_focal_witnesses": counterpart_witnesses,
        "S": {p: rate(s[p]) for p in POLICIES},
        "N": {p: rate(n[p]) for p in POLICIES},
        "raw_blocking": {
            f"{p}/{v}": {
                "blocks": statuses.count(BLOCK),
                "accepts": statuses.count(ACCEPT),
                "indeterminate": statuses.count(INDETERMINATE),
            }
            for (p, v), statuses in sorted(raw.items())
        },
        "focal_witnesses_V_bad": witness,
        "accept_with_prior_failure": retain_flags,
        "prefix_cost": {
            f"{p}/{v}": {
                "attempts": c[0],
                "wall_s": round(c[1], 3),
                "allocated_vcpu_h": round(c[1] * vcpus / 3600, 6),
            }
            for (p, v), c in prefix_cost.items()
        },
        "research_spend": {
            "measured_block_attempts": len(measured),
            "measured_block_wall_s": round(sum(r["elapsed_s"] for r in measured), 3),
            "measured_block_allocated_vcpu_h": round(
                sum(r["elapsed_s"] for r in measured) * vcpus / 3600, 6
            ),
            "ledger_attempts_all_blocks": len(all_attempts),
            "ledger_wall_s_all_blocks": round(sum(r["elapsed_s"] for r in all_attempts), 3),
            "measured_cpu": "not measured by runner e1-runner/1",
        },
        "_vectors": {"S": s, "N": n},
    }
    if batches:
        summary["batches"] = [
            {
                "blocks": f"{b[0]}-{b[-1]}" if b else "",
                "S": {p: rate([s[p][blocks.index(x)] for x in b if x in blocks]) for p in (P1, P3)},
                "N": {p: rate([n[p][blocks.index(x)] for x in b if x in blocks]) for p in (P1, P3)},
            }
            for b in batches
        ]
    return summary, rows_out


def direct_checks(
    episode: str, blocks: Sequence[int], records: Sequence[dict[str, Any]], ann: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Structural check of each direct-policy trace (plan, E1 step 3).

    The ledger does not record which policy a direct check executed, so each
    trace is tested for which policies' stopping rule it is consistent with. A
    trace consistent with neither is a structural mismatch: the runner did not
    stop where the reducer says the policy stops.
    """
    out = []
    for block in blocks:
        for version in (V_BAD, V_OK):
            t = Trace.build(episode, block, version, records, ann)
            if not t.rows:
                continue
            st = t.statuses
            gapless = all(r is not None for r in t.rows)
            earlier_failed = all(x not in (0, None) for x in st[:-1])
            consistent = []
            if len(st) == 1:
                consistent.append(P1)
            if gapless and earlier_failed and len(st) <= RETRY_BUDGET and (st[-1] == 0 or len(st) == RETRY_BUDGET):
                consistent.append(P3)
            out.append(
                {
                    "episode": episode,
                    "block": block,
                    "version": version,
                    "executed": st,
                    "consistent_with": consistent,
                    "structural_mismatch": not consistent,
                    "decisions": {p: reduce_block(p, st).final_status for p in consistent},
                }
            )
    return out


# --- report -------------------------------------------------------------------


def _fmt(x: float | None, digits: int = 3) -> str:
    return "n/a" if x is None else f"{x:.{digits}f}"


def _interval(iv: Sequence[float] | None) -> str:
    return "n/a" if iv is None else f"[{iv[0]:+.3f}, {iv[1]:+.3f}]"


def _rate(r: dict[str, Any]) -> str:
    text = f"{r['count']}/{r['denominator']} = {_fmt(r['rate'])}"
    if r["undetermined"]:
        text += f" (+{r['undetermined']} undetermined)"
    return text


def render_report(result: dict[str, Any]) -> str:
    meta = result["meta"]
    lines = [
        "# E1 analysis report",
        "",
        f"Generated by `{meta['analysis_version']}` from ledger `{meta['ledger_sha256'][:16]}...` "
        f"and annotations `{meta['annotations_sha256'][:16]}...` "
        f"(oracle {', '.join(sorted(meta['oracle_versions']))}).",
        "",
        "E1 is descriptive calibration (plan section 6): no equivalence claim and no "
        "project-level generalisation at E1's 20 blocks. Contrast intervals are "
        f"Bonferroni-simultaneous over {meta['contrast_family']} contrasts "
        f"(each side at {1 - meta['alpha_each']:.5f}); they assume independent "
        "reset blocks, not independent retries.",
        "",
    ]
    for ep in result["episodes"]:
        name = ep["episode"]
        lines += [f"## {name}", ""]
        flags = []
        if ep["missing_blocks"]:
            flags.append(f"declared blocks with no records: {ep['missing_blocks']}")
        if ep["invalid_fraction"] is not None and ep["invalid_fraction"] > meta["invalid_threshold"]:
            flags.append(
                f"invalid-block fraction {ep['invalid_fraction']:.2f} exceeds the "
                f"{meta['invalid_threshold']:.2f} quality gate"
            )
        if ep["counterpart_focal_witnesses"]:
            flags.append(
                "focal witness on V_ok (pair UNRESOLVED until explained): "
                + ", ".join(ep["counterpart_focal_witnesses"])
            )
        if not ep["N"][P1]["count"] and not ep["N"][P3]["count"]:
            flags.append(
                "no verified nuisance observed: sensitivity only; the noise-reduction "
                "part of RQ1 is not established for this episode"
            )
        for f in flags:
            lines.append(f"- **{f}**")
        if flags:
            lines.append("")
        lines += [
            f"Measured blocks: {ep['measured_blocks']}; invalid: {len(ep['invalid_blocks'])} "
            f"({_fmt(ep['invalid_fraction'], 2)}); V_bad first in "
            f"{ep['block_order_first_version'][V_BAD]} blocks.",
            "",
            "| Policy | S (focal-supported blocks on V_bad) | 95% CI | N (nuisance-only blocks on V_ok) | 95% CI |",
            "|---|---|---|---|---|",
        ]
        for p in POLICIES:
            sr, nr = ep["S"][p], ep["N"][p]
            lines.append(
                f"| {p} | {_rate(sr)} | {_interval(sr['ci95'])} "
                f"| {_rate(nr)} | {_interval(nr['ci95'])} |"
            )
        lines += ["", "| Contrast | Estimate | Simultaneous interval | Best/worst | Discordant +/- | Margin |", "|---|---|---|---|---|---|"]
        for key, margin in (("L", L_MARGIN), ("R", R_MARGIN)):
            c = ep[key]
            lines.append(
                f"| {key} = {'S' if key == 'L' else 'N'}(P1) - {'S' if key == 'L' else 'N'}(P3) "
                f"| {_fmt(c['estimate'])} | {_interval(c['interval'])} "
                f"| {_fmt(c['best_worst'][0])} ... {_fmt(c['best_worst'][1])} "
                f"| {c['positive']}/{c['negative']} of {c['complete_blocks']} "
                f"| {margin:.2f}: {c['margin_position']} |"
            )
        lines += ["", "| Policy/version | Blocks | Accepts | Indeterminate | Prefix attempts | Prefix wall s | Allocated vCPU-h |", "|---|---|---|---|---|---|---|"]
        for key, rb in ep["raw_blocking"].items():
            pc = ep["prefix_cost"][key]
            lines.append(
                f"| {key} | {rb['blocks']} | {rb['accepts']} | {rb['indeterminate']} "
                f"| {pc['attempts']} | {pc['wall_s']} | {pc['allocated_vcpu_h']} |"
            )
        w = ep["focal_witnesses_V_bad"]
        lines += [
            "",
            f"Focal witnesses on V_bad: {w[P1]['generated']} generated. "
            + "; ".join(
                f"{p}: {w[p]['in_prefix']} in prefix, {w[p]['ignored_by_gate']} ignored by an accepting gate, "
                f"{w[p]['research_only']} research-only"
                for p in (P1, P3)
            )
            + f". `ACCEPT_WITH_PRIOR_FAILURE`: {ep['accept_with_prior_failure']}.",
            "",
            f"Research spend on measured blocks: {ep['research_spend']['measured_block_attempts']} attempts, "
            f"{ep['research_spend']['measured_block_wall_s']} s, "
            f"{ep['research_spend']['measured_block_allocated_vcpu_h']} allocated vCPU-h "
            f"at {meta['allocated_vcpus']} vCPU per job. Measured CPU: not recorded.",
            "",
        ]
        for b in ep.get("batches", []):
            lines.append(
                f"- Batch {b['blocks']}: S(P1) {_fmt(b['S'][P1]['rate'])}, S(P3) {_fmt(b['S'][P3]['rate'])}, "
                f"N(P1) {_fmt(b['N'][P1]['rate'])}, N(P3) {_fmt(b['N'][P3]['rate'])}"
            )
        if ep.get("batches"):
            lines.append("")
        if ep["direct_checks"]:
            mismatches = [d for d in ep["direct_checks"] if d["structural_mismatch"]]
            lines.append(
                f"Direct-policy checks: {len(ep['direct_checks'])} traces, "
                f"{len(mismatches)} structural mismatches"
                + (": " + ", ".join(f"b{d['block']}/{d['version']}" for d in mismatches) if mismatches else ".")
            )
            lines.append("")
    return "\n".join(lines)


# --- entry point --------------------------------------------------------------


def analyse(
    ledger: str | Path,
    annotations: str | Path,
    blocks: Sequence[int],
    vcpus: float,
    direct: Sequence[int] = (),
    batches: Sequence[Sequence[int]] = (),
    episodes: Sequence[str] | None = None,
    family_alpha: float = 0.05,
    invalid_threshold: float = 0.10,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not blocks:
        raise AnalysisError("declare the measured blocks (--blocks); they are never inferred")
    if set(blocks) & set(direct):
        raise AnalysisError("a block cannot be both measured and a direct-policy check")
    if vcpus <= 0:
        raise AnalysisError("allocated vCPUs per job must be positive")

    verify_chain(ledger)
    records = read_records(ledger)
    anns = read_records(annotations)
    ann = join_annotations(records, anns)

    present = sorted({r["episode"] for r in records})
    chosen = list(episodes) if episodes else present
    absent = set(chosen) - set(present)
    if absent:
        raise AnalysisError(f"episodes with no records in the ledger: {sorted(absent)}")

    family = 2 * len(chosen)
    alpha_each = family_alpha / (2 * family)

    results, decision_rows = [], []
    for episode in chosen:
        summary, rows = analyse_episode(episode, blocks, records, ann, vcpus, batches)
        vec = summary.pop("_vectors")
        for key, source, margin in (("L", vec["S"], L_MARGIN), ("R", vec["N"], R_MARGIN)):
            c = paired_contrast(source[P1], source[P3], alpha_each)
            c["margin_position"] = margin_position(c["interval"], margin)
            summary[key] = c
        summary["direct_checks"] = direct_checks(episode, direct, records, ann)
        results.append(summary)
        decision_rows.extend(rows)

    meta = {
        "analysis_version": ANALYSIS_VERSION,
        "ledger": str(ledger),
        "ledger_sha256": _file_sha256(ledger),
        "annotations": str(annotations),
        "annotations_sha256": _file_sha256(annotations),
        "oracle_versions": sorted({f"{a['oracle_version']}@{a['oracle_sha256'][:12]}" for a in anns}),
        "annotation_sources": {
            s: sum(1 for a in anns if a["source"] == s) for s in sorted({a["source"] for a in anns})
        },
        "measured_blocks": list(blocks),
        "direct_blocks": list(direct),
        "allocated_vcpus": vcpus,
        "family_alpha": family_alpha,
        "contrast_family": family,
        "alpha_each": alpha_each,
        "invalid_threshold": invalid_threshold,
        "margins": {"L": L_MARGIN, "R": R_MARGIN},
    }
    return {"meta": meta, "episodes": results}, decision_rows


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--annotations", required=True, help="output of oracle.py")
    ap.add_argument("--blocks", required=True, help="preassigned measured blocks, e.g. 1-20")
    ap.add_argument("--allocated-vcpus", type=float, required=True, help="vCPUs allocated per job")
    ap.add_argument("--direct-blocks", help="blocks holding direct-policy checks")
    ap.add_argument("--batch", action="append", default=[], help="a time batch, e.g. 1-10 (repeatable)")
    ap.add_argument("--episode", action="append", help="restrict to these episodes (repeatable)")
    ap.add_argument("--family-alpha", type=float, default=0.05)
    ap.add_argument("--invalid-threshold", type=float, default=0.10, help="0.10 for E1, 0.05 for E2")
    ap.add_argument("--out", required=True, help="output directory")
    args = ap.parse_args(argv)

    result, rows = analyse(
        args.ledger,
        args.annotations,
        parse_blocks(args.blocks),
        args.allocated_vcpus,
        direct=parse_blocks(args.direct_blocks),
        batches=[parse_blocks(b) for b in args.batch],
        episodes=args.episode,
        family_alpha=args.family_alpha,
        invalid_threshold=args.invalid_threshold,
    )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "policy_decisions.csv", "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ["episode"])
        writer.writeheader()
        writer.writerows(rows)
    (out / "summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    report = render_report(result)
    (out / "report.md").write_text(report + "\n", encoding="utf-8", newline="\n")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
