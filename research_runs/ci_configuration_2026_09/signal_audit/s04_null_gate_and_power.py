"""EXPLORATORY / POST HOC signal audit s04.

(a) Exact probability that the frozen C3 development gate fires when there is
    NO profile effect and attempts are independent Bernoulli trials at each
    subject's pooled (R+L) defective-variant rate ("ordinary repetition").
    C3 (protocol section 7): |Delta| >= 0.20 over 10 blocks and the same nonzero
    direction in batch A (blocks 1-5) and batch B (blocks 6-10). Complete data,
    so missing-label bounds are the point value.
(b) What a fresh etcd5509 confirmation would cost: exact power of a single
    paired contrast analysed with the frozen conservative method (Clopper-
    Pearson on P(d=+1) and P(d=-1), opposing endpoints subtracted) at
    two-sided 0.05 (each category at 1-0.025), for single fresh attempts per
    profile per matched block, under assumed true single-attempt focal rates.
    Costs use the measured per-attempt charges of C1's etcd5509 cells.
Outputs: out/s04_null_gate_and_power.json
"""
from __future__ import annotations

import json
from functools import lru_cache
from math import comb, exp, lgamma, log

from audit_common import STUDY, load_jsonl, write_json


# ---------- (a) C3 under no profile effect ----------
def cell_dist(p):
    """(S_P1, S_P3) for one defective cell of three iid attempts."""
    return {(0, 0): 1 - p, (1, 0): p - p ** 3, (1, 1): p ** 3}


def block_dist(p):
    c = cell_dist(p)
    out = {}
    for (r1, r3), pr in c.items():
        for (l1, l3), pl in c.items():
            k = (r1 - l1, r3 - l3)
            out[k] = out.get(k, 0) + pr * pl
    return out


def conv(a, b):
    out = {}
    for (x1, y1), p in a.items():
        for (x2, y2), q in b.items():
            k = (x1 + x2, y1 + y2)
            out[k] = out.get(k, 0) + p * q
    return out


def batch_dist(p, n=5):
    d = {(0, 0): 1.0}
    b = block_dist(p)
    for _ in range(n):
        d = conv(d, b)
    return d


def c3_probs(p):
    bd = batch_dist(p)
    fire = {"P1": 0.0, "P3": 0.0, "any": 0.0, "P1_negative_direction": 0.0}
    sgn = lambda v: (v > 0) - (v < 0)
    for (a1, a3), pa in bd.items():
        for (b1, b3), pb in bd.items():
            f1 = abs(a1 + b1) >= 2 and sgn(a1) != 0 and sgn(a1) == sgn(b1)
            f3 = abs(a3 + b3) >= 2 and sgn(a3) != 0 and sgn(a3) == sgn(b3)
            w = pa * pb
            fire["P1"] += w * f1
            fire["P3"] += w * f3
            fire["any"] += w * (f1 or f3)
            fire["P1_negative_direction"] += w * (f1 and a1 < 0)
    return fire


# ---------- (b) power of the frozen interval method ----------
def binom_cdf(k, n, p):
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


@lru_cache(maxsize=None)
def cp_bounds(n, a2):
    """Clopper-Pearson (lower, upper) for every k at two-sided level 2*a2 via bisection."""
    lo, up = [], []
    for k in range(n + 1):
        if k == 0:
            lo.append(0.0)
        else:
            a, b = 0.0, 1.0
            for _ in range(50):
                m = (a + b) / 2
                if 1 - binom_cdf(k - 1, n, m) < a2:
                    a = m
                else:
                    b = m
            lo.append((a + b) / 2)
        if k == n:
            up.append(1.0)
        else:
            a, b = 0.0, 1.0
            for _ in range(50):
                m = (a + b) / 2
                if binom_cdf(k, n, m) > a2:
                    a = m
                else:
                    b = m
            up.append((a + b) / 2)
    return tuple(lo), tuple(up)


def power(n, pR, pL, a2=0.0125):
    """P(interval for mean(d) excludes 0 in the L>R direction). d = S(R)-S(L)."""
    pp = pR * (1 - pL)
    pm = (1 - pR) * pL
    p0 = 1 - pp - pm
    lo, up = cp_bounds(n, a2)
    lp, lpm, lp0 = log(pp) if pp > 0 else None, log(pm), log(p0)
    tot = 0.0
    for kp in range(n + 1):
        if pp == 0 and kp > 0:
            break
        for km in range(n - kp + 1):
            k0 = n - kp - km
            if up[kp] < lo[km]:  # upper(mean d) < 0: limited CPU increases supported blocking
                lg = lgamma(n + 1) - lgamma(kp + 1) - lgamma(km + 1) - lgamma(k0 + 1)
                lg += (kp * lp if kp else 0) + km * lpm + k0 * lp0
                tot += exp(lg)
    return tot


def main():
    rates = {"etcd5509": 50 / 60, "etcd7492": 10 / 60, "grpc1859": 5 / 60, "grpc2391": 55 / 60,
             "istio17860": 60 / 60, "k8s26980": 0 / 60}
    res = {"label": "EXPLORATORY/POST-HOC s04", "c3_under_no_profile_effect": {}}
    none_fire = 1.0
    for s, p in rates.items():
        f = c3_probs(p)
        res["c3_under_no_profile_effect"][s] = {"p_pooled": round(p, 4), **{k: round(v, 4) for k, v in f.items()}}
        none_fire *= 1 - f["any"]
    res["c3_under_no_profile_effect"]["P_at_least_one_subject_fires"] = round(1 - none_fire, 4)
    res["c3_under_no_profile_effect"]["etcd5509_at_historical_p_0.80"] = {k: round(v, 4) for k, v in c3_probs(0.8).items()}
    res["c3_under_no_profile_effect"]["note"] = ("iid attempts, common rate for R and L; exact enumeration; "
                                                 "the observed within-cell ICC estimate (~0.06, s02) is consistent with near-independence")

    # Per-attempt measured charges for etcd5509 cells (resource ledger, read-only).
    R = load_jsonl(STUDY / "resources" / "resource_ledger.jsonl")
    cost = {}
    for r in R:
        if r["kind"] == "charge" and r["stage"] == "measured" and "-etcd5509-" in r["job_id"]:
            parts = r["job_id"].split("-")
            k = f"{parts[4]}/{parts[5]}"
            c = cost.setdefault(k, [0, 0.0, 0.0])
            c[0] += 1
            c[1] += r["charged_vcpu_h"]
            c[2] += r["host_reservation_h"]
    per = {k: {"attempts": v[0], "alloc_vcpu_h_per_attempt": round(v[1] / v[0], 5), "host_reservation_h_per_attempt": round(v[2] / v[0], 5)} for k, v in cost.items()}
    res["etcd5509_measured_cost_per_attempt"] = per
    pair_alloc = sum(per[k]["alloc_vcpu_h_per_attempt"] for k in ("R/bad", "L/bad", "R/ok", "L/ok"))
    pair_host = sum(per[k]["host_reservation_h_per_attempt"] for k in ("R/bad", "L/bad", "R/ok", "L/ok"))
    res["cost_per_confirmation_block_single_attempt_4_cells"] = {"alloc_vcpu_h": round(pair_alloc, 4), "host_reservation_vcpu_h": round(pair_host, 4),
                                                                 "wall_h_approx": round(pair_host / 16, 4)}

    scen = {
        "pilot_attempt_rates_0.80_vs_0.867": (0.80, 26 / 30),
        "historical_R_0.80_vs_L_0.90": (0.80, 0.90),
        "R_0.80_vs_L_0.95": (0.80, 0.95),
        "pilot_first_attempt_point_0.70_vs_1.00": (0.70, 0.9999),
    }
    grid = [50, 100, 150, 200, 300, 400, 500, 600]
    pw = {}
    for name, (pR, pL) in scen.items():
        pw[name] = {}
        for n in grid:
            pw[name][n] = round(power(n, pR, pL), 3)
    res["power_single_contrast_two_sided_0.05"] = pw
    res["power_note"] = ("One primary contrast (not a 12-contrast family); single fresh attempt per profile per block; "
                         "within-block independence assumed; power = P(interval excludes 0 in the L-higher direction).")
    write_json("s04_null_gate_and_power.json", res)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
