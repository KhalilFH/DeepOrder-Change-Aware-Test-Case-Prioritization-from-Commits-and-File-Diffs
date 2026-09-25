"""Projected E2 cost for the three Q0-qualified episodes (feasibility report, section 5).

E2 (plan section 7) runs 100 paired blocks per episode, 3 attempts per version,
and charges every attempt, including research-only suffixes.

- etcd5509, etcd7492: measured E1 blocks 1-20 (120 attempts each), scaled x5.
- grpc2391: no E1 blocks exist, so the per-attempt means come from its 40 Q0
  counted attempts (task5_artifacts/grpc2391/run/results.csv). Those ran under
  the Q0 runner, not the E1 runner; this is disclosed in the report.

Each attempt is charged elapsed_s + 2.04 s, the maximum within-run gap between
attempts used by the E1 cost guard (e1/AMENDMENTS.md section 2.2).

Run from research_runs/ci_sensitivity_2026_09/:
    python feasibility/e2_cost_projection.py
"""
import csv
import json

GAP_S = 2.04
BLOCKS = 100
BASES = (16, 2, 1)  # allocated vCPUs per job: E1 conservative, plan section 11 pin, Q0 convention


def etcd_wall_h(episode):
    with open(f"e1/{episode}/attempts.jsonl", encoding="utf-8") as fh:
        records = [json.loads(line) for line in fh]
    measured = [r for r in records if 1 <= r["block"] <= 20]
    assert len(measured) == 120, (episode, len(measured))
    charged_s = sum(r["elapsed_s"] + GAP_S for r in measured)
    return charged_s * (BLOCKS / 20) / 3600


def grpc2391_wall_h():
    with open("task5_artifacts/grpc2391/run/results.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    mean = {}
    for version in ("V_bad", "V_ok"):
        durations = [float(r["elapsed_s"]) for r in rows if r["version"] == version]
        assert len(durations) == 20, (version, len(durations))
        mean[version] = sum(durations) / len(durations)
    block_s = 3 * (mean["V_bad"] + GAP_S) + 3 * (mean["V_ok"] + GAP_S)
    return block_s * BLOCKS / 3600


def main():
    wall = {
        "etcd5509": etcd_wall_h("etcd5509"),
        "etcd7492": etcd_wall_h("etcd7492"),
        "grpc2391": grpc2391_wall_h(),
    }
    wall["total"] = sum(wall.values())
    print("episode,wall_h," + ",".join(f"vcpu_h_{b}" for b in BASES))
    for name, hours in wall.items():
        print(f"{name},{hours:.3f}," + ",".join(f"{hours * b:.2f}" for b in BASES))


if __name__ == "__main__":
    main()
