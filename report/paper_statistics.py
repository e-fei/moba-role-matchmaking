#!/usr/bin/env python3
"""Summarize recorded matchmaking runs without inventing player-level data.

Usage: python3 report/paper_statistics.py
Only Python's standard library is required. The input is never modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
PRIMARY_METRICS = (
    "mean_matched_wait_seconds",
    "mean_team_pairwise_gap",
    "observed_mean_queue_time_seconds",
)
RUN_METRICS = PRIMARY_METRICS + (
    "match_rate",
    "matched_players",
    "teams",
    "pending_players",
    "p95_matched_wait_seconds",
)
PENDING_AGE_METRICS = (
    "mean_pending_age_seconds",
    "oldest_pending_age_seconds",
)
PAIRED_METRICS = PRIMARY_METRICS + ("match_rate", "pending_players")


def summary(values):
    """Equal-weight run summary; SD has n - 1 in its denominator."""
    values = list(values)
    if not values:
        return {"n": 0, "mean": None, "sample_sd": None, "min": None, "max": None}
    return {
        "n": len(values),
        "mean": statistics.mean(values),
        "sample_sd": statistics.stdev(values) if len(values) > 1 else None,
        "min": min(values),
        "max": max(values),
    }


def check_close(recorded, recomputed, description):
    # Input mean metrics are serialized to six decimal places.
    if not math.isclose(recorded, recomputed, rel_tol=0.0, abs_tol=1.1e-6):
        raise ValueError(f"Inconsistent {description}: {recorded} != {recomputed}")


def validate_result(result, seeds):
    runs = result["per_seed"]
    if sorted(row["seed"] for row in runs) != sorted(seeds):
        raise ValueError(f"Unexpected seed list for {result['policy']}")
    for row in runs:
        m = row["metrics"]
        label = f"{result['policy']}, seed {row['seed']}"
        if m["matched_players"] != 5 * m["teams"]:
            raise ValueError(f"Team size mismatch: {label}")
        if m["arrivals"] != m["matched_players"] + m["pending_players"]:
            raise ValueError(f"Player accounting mismatch: {label}")
        if sum(m["pending_by_role"].values()) != m["pending_players"]:
            raise ValueError(f"Pending role accounting mismatch: {label}")
        check_close(m["match_rate"], m["matched_players"] / m["arrivals"], label)
        check_close(
            m["mean_matched_wait_seconds"],
            m["matched_wait_sum_seconds"] / m["matched_players"],
            label,
        )
        check_close(
            m["observed_mean_queue_time_seconds"],
            (m["matched_wait_sum_seconds"] + m["pending_age_sum_seconds"])
            / m["arrivals"],
            label,
        )
        if m["pending_players"]:
            check_close(
                m["mean_pending_age_seconds"],
                m["pending_age_sum_seconds"] / m["pending_players"],
                label,
            )
    pooled = result["pooled"]
    for name in (
        "arrivals", "teams", "matched_players", "pending_players",
        "matched_wait_sum_seconds", "pending_age_sum_seconds",
    ):
        if pooled[name] != sum(row["metrics"][name] for row in runs):
            raise ValueError(f"Pooled {name} mismatch for {result['policy']}")
    for name, weight in (
        ("mean_matched_wait_seconds", "matched_players"),
        ("mean_team_pairwise_gap", "teams"),
        ("observed_mean_queue_time_seconds", "arrivals"),
    ):
        weighted = sum(row["metrics"][name] * row["metrics"][weight] for row in runs)
        denominator = sum(row["metrics"][weight] for row in runs)
        check_close(pooled[name], weighted / denominator, f"pooled {name}")


def build_statistics(source_bytes):
    source = json.loads(source_bytes)
    seeds = source["workload"]["seeds"]
    if len(seeds) != 5 or len(set(seeds)) != 5:
        raise ValueError("This figure specification expects five distinct seeds")
    output = {
        "schema_version": 1,
        "source": {
            "file": "experiment_results.json",
            "sha256": hashlib.sha256(source_bytes).hexdigest(),
            "experiment": source["experiment"],
        },
        "conventions": {
            "unit_of_replication": "One scenario-policy run with one seed; n = 5.",
            "run_summary": "Arithmetic mean and sample SD (denominator n - 1) of the five run metrics; each run has equal weight.",
            "uncertainty": "SD describes variation across these seeds. It is not a confidence interval, standard error, or significance test.",
            "pairing": "Within a scenario, policies share seed and arrival workload. Delta is policy minus role_fifo for the same seed.",
            "gap_delta": "A negative gap delta means smaller score differences.",
            "wait_delta": "A negative matched-wait delta can reflect selection of who completes. Interpret with match rate, observed queue residence, and pending ages.",
            "pending_age_summary": "Mean and oldest pending ages are summarized only over runs with pending players. No-pending runs have undefined pending age, although the source records mean pending age as zero.",
            "pooled": "Preserved separately from the source. Pooled means weight waits by matched-player count and gaps by team count. A mean of five run p95 values is not the pooled p95.",
            "precision": "Computed from recorded per-run summaries; source means are rounded to six decimal places. No unrecorded player-level observations are reconstructed.",
            "observed_queue_time": source["metric_definitions"]["observed_mean_queue_time"],
            "claims": "Descriptive synthetic experiment; no statistical-significance or population-generalization claims.",
        },
        "workload": source["workload"],
        "policy_parameters": source["policies"],
        "scenarios": [],
    }
    for scenario in source["scenarios"]:
        results = scenario["results"]
        by_policy = {result["policy"]: result for result in results}
        for result in results:
            validate_result(result, seeds)
        baseline = {r["seed"]: r["metrics"] for r in by_policy["role_fifo"]["per_seed"]}
        scenario_output = {"name": scenario["name"], "policies": [], "paired_deltas_vs_fifo": []}
        for result in results:
            runs = sorted(result["per_seed"], key=lambda row: row["seed"])
            run_summary = {
                metric: summary(row["metrics"][metric] for row in runs)
                for metric in RUN_METRICS
            }
            run_summary.update({
                metric: summary(
                    row["metrics"][metric]
                    for row in runs if row["metrics"]["pending_players"] > 0
                )
                for metric in PENDING_AGE_METRICS
            })
            scenario_output["policies"].append({
                "policy": result["policy"],
                "raw_points": runs,
                "across_run_summary": run_summary,
                "pooled_metrics": result["pooled"],
            })
            if result["policy"] in ("adaptive_10", "adaptive_30"):
                paired_points = [
                    {
                        "seed": row["seed"],
                        "deltas": {
                            metric: row["metrics"][metric] - baseline[row["seed"]][metric]
                            for metric in PAIRED_METRICS
                        },
                    }
                    for row in runs
                ]
                scenario_output["paired_deltas_vs_fifo"].append({
                    "policy": result["policy"],
                    "baseline": "role_fifo",
                    "raw_points": paired_points,
                    "across_run_summary": {
                        metric: summary(row["deltas"][metric] for row in paired_points)
                        for metric in PAIRED_METRICS
                    },
                })
        output["scenarios"].append(scenario_output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "experiment_results.json")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "paper_statistics.json")
    args = parser.parse_args()
    output = build_statistics(args.input.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    for scenario in output["scenarios"]:
        print(f"\n{scenario['name']} (run mean +/- sample SD; n = 5)")
        for policy in scenario["policies"]:
            stats = policy["across_run_summary"]
            fields = [
                f"{metric}: {stats[metric]['mean']:.3f} +/- {stats[metric]['sample_sd']:.3f}"
                for metric in PRIMARY_METRICS
            ]
            print(f"  {policy['policy']}: " + "; ".join(fields))


if __name__ == "__main__":
    main()
