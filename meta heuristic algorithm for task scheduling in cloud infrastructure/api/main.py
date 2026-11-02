"""HTTP API for running cloud task scheduling comparisons."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from cloud_scheduler import (
    evaluate_schedule,
    fcfs,
    genetic_algorithm,
    hybrid_ga_pso,
    particle_swarm,
    round_robin,
)
from cloud_scheduler.schedulers import SearchConfig
from cloud_scheduler.workloads import generate_workload


app = FastAPI(title="Cloud Task Scheduler", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class SimulationRequest(BaseModel):
    tasks: int = Field(default=30, ge=1, le=100)
    vms: int = Field(default=5, ge=1, le=20)
    iterations: int = Field(default=60, ge=1, le=150)
    population: int = Field(default=20, ge=4, le=40)
    seed: int = Field(default=42, ge=0, le=2_147_483_647)


@app.get("/")
def health() -> dict[str, str]:
    return {"service": "cloud-task-scheduler", "status": "ok", "docs": "/docs"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/simulate")
def simulate(request: SimulationRequest) -> dict[str, object]:
    tasks, vms = generate_workload(request.tasks, request.vms, request.seed)
    config = SearchConfig(population_size=request.population, iterations=request.iterations)
    algorithms = {
        "FCFS": fcfs(tasks, vms),
        "Round Robin": round_robin(tasks, vms),
        "Genetic Algorithm": genetic_algorithm(tasks, vms, config, request.seed + 1),
        "Particle Swarm": particle_swarm(tasks, vms, config, request.seed + 2),
        "Hybrid GA-PSO": hybrid_ga_pso(tasks, vms, config, request.seed + 3),
    }

    results = []
    for name, assignment in algorithms.items():
        metrics = evaluate_schedule(tasks, vms, assignment, config.weights)
        results.append({
            "algorithm": name,
            "makespan_seconds": round(metrics.makespan_seconds, 4),
            "load_imbalance_seconds": round(metrics.load_imbalance_seconds, 4),
            "energy_proxy_joules": round(metrics.energy_proxy_joules, 2),
            "fitness": round(metrics.fitness, 6),
            "vm_completion_times": [round(value, 4) for value in metrics.vm_completion_times],
            "assignment": assignment,
        })

    return {
        "seed": request.seed,
        "task_count": len(tasks),
        "vm_count": len(vms),
        "vms": [{"vm_id": vm.vm_id, "mips": vm.mips} for vm in vms],
        "results": results,
        "energy_note": "Energy is an illustrative model estimate, not measured hardware consumption.",
    }

