"""Run repeatable comparisons of FCFS, Round Robin, GA, PSO, and hybrid GA-PSO."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import mean, pstdev

from cloud_scheduler import (
    evaluate_schedule, fcfs, genetic_algorithm, hybrid_ga_pso, hybrid_ga_pso_pareto,
    particle_swarm, round_robin,
)
from cloud_scheduler.schedulers import SearchConfig
from cloud_scheduler.workloads import generate_workload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=int, default=30)
    parser.add_argument("--vms", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42, help="Base seed for workload generation and randomized searches")
    parser.add_argument(
        "--workload-seeds", type=int, nargs="+", default=None,
        help="Optional list of workload seeds; every scheduler sees the same workload for each seed",
    )
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--population", type=int, default=30)
    parser.add_argument("--hybrid-interval", type=int, default=10, help="Stagnant iterations before GA variation is injected")
    parser.add_argument(
        "--weights", type=float, nargs=3, default=(0.5, 0.25, 0.25), metavar=("MAKESPAN", "BALANCE", "ENERGY"),
        help="Relative fitness weights; defaults to 0.50 0.25 0.25",
    )
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")

    config = SearchConfig(
        population_size=args.population,
        iterations=args.iterations,
        hybrid_interval=args.hybrid_interval,
        weights=tuple(args.weights),
    )
    workload_seeds = list(dict.fromkeys(args.workload_seeds or [args.seed]))
    algorithm_names = ("FCFS", "Round Robin", "GA", "PSO", "Hybrid GA-PSO")

    args.output.mkdir(parents=True, exist_ok=True)
    detail_rows: list[dict[str, object]] = []
    pareto_rows: list[dict[str, object]] = []
    for workload_seed in workload_seeds:
        tasks, vms = generate_workload(args.tasks, args.vms, workload_seed)
        algorithms = {
            "FCFS": lambda _: fcfs(tasks, vms),
            "Round Robin": lambda _: round_robin(tasks, vms),
            "GA": lambda s: genetic_algorithm(tasks, vms, config, s),
            "PSO": lambda s: particle_swarm(tasks, vms, config, s),
            "Hybrid GA-PSO": lambda s: hybrid_ga_pso(tasks, vms, config, s),
        }
        for algorithm, run in algorithms.items():
            # Deterministic baselines need only one run per workload. The search
            # algorithms retain multiple runs to measure randomness in the search.
            repeat_count = 1 if algorithm in ("FCFS", "Round Robin") else args.repeats
            for repeat in range(repeat_count):
                algorithm_seed = args.seed + workload_seed * 1_000_003 + repeat
                assignment = run(algorithm_seed)
                metrics = evaluate_schedule(tasks, vms, assignment, config.weights)
                detail_rows.append({
                    "workload_seed": workload_seed,
                    "algorithm": algorithm,
                    "repeat": repeat + 1,
                    "makespan_seconds": metrics.makespan_seconds,
                    "load_imbalance_seconds": metrics.load_imbalance_seconds,
                    "energy_proxy_joules": metrics.energy_proxy_joules,
                    "fitness": metrics.fitness,
                    "assignment": " ".join(map(str, assignment)),
                })

        for front_index, assignment in enumerate(
            hybrid_ga_pso_pareto(tasks, vms, config, args.seed + workload_seed * 1_000_003),
            start=1,
        ):
            metrics = evaluate_schedule(tasks, vms, assignment, config.weights)
            pareto_rows.append({
                "workload_seed": workload_seed,
                "front_index": front_index,
                "makespan_seconds": metrics.makespan_seconds,
                "load_imbalance_seconds": metrics.load_imbalance_seconds,
                "energy_proxy_joules": metrics.energy_proxy_joules,
                "fitness": metrics.fitness,
                "assignment": " ".join(map(str, assignment)),
            })

    detail_path = args.output / "runs.csv"
    with detail_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(detail_rows[0]))
        writer.writeheader()
        writer.writerows(detail_rows)

    pareto_path = args.output / "pareto_front.csv"
    with pareto_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(pareto_rows[0]))
        writer.writeheader()
        writer.writerows(pareto_rows)

    metrics_names = ("makespan_seconds", "load_imbalance_seconds", "energy_proxy_joules", "fitness")
    summary: dict[str, dict[str, dict[str, float | int]]] = {}
    for algorithm in algorithm_names:
        rows = [row for row in detail_rows if row["algorithm"] == algorithm]
        summary[algorithm] = {
            metric: {
                "count": len(rows),
                "mean": mean(float(row[metric]) for row in rows),
                "stddev": pstdev(float(row[metric]) for row in rows),
            }
            for metric in metrics_names
        }

    by_workload_seed: dict[str, dict[str, dict[str, dict[str, float]]]] = {}
    for workload_seed in workload_seeds:
        by_workload_seed[str(workload_seed)] = {}
        for algorithm in algorithm_names:
            rows = [
                row for row in detail_rows
                if row["workload_seed"] == workload_seed and row["algorithm"] == algorithm
            ]
            by_workload_seed[str(workload_seed)][algorithm] = {
                metric: {
                    "mean": mean(float(row[metric]) for row in rows),
                    "stddev": pstdev(float(row[metric]) for row in rows),
                }
                for metric in metrics_names
            }

    summary_path = args.output / "summary.json"
    summary_path.write_text(json.dumps({
        "workload": {"tasks": args.tasks, "vms": args.vms, "seeds": workload_seeds},
        "repeats": args.repeats,
        "search": {
            "population": args.population,
            "iterations": args.iterations,
            "hybrid_stagnation_interval": args.hybrid_interval,
            "weights": config.weights,
        },
        "energy_model": "max_power while busy plus idle_power until makespan; illustrative proxy, not measured energy",
        "pareto_front": "pareto_front.csv contains non-dominated hybrid candidates found by separate weighted-objective runs",
        "results": summary,
        "by_workload_seed": by_workload_seed,
    }, indent=2), encoding="utf-8")
    print(f"Wrote {detail_path}, {summary_path}, and {pareto_path}")


if __name__ == "__main__":
    main()
