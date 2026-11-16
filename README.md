# PT171-Meta_heuristic_algorithm_for_task_scheduling_in_cloud_infrastructure

## Live demo

[Open the deployed Cloud Task Scheduler](https://cloud-task-scheduler.vercel.app/)

## Architecture

The diagram below shows the target architecture. The `cloud_scheduler` package holds all the logic, and the CLI, API and tests are thin layers on top of it.

```mermaid
flowchart TD
    UI["public/index.html"] -- "POST /api/simulate" --> API

    subgraph ENTRY["Entry points"]
        CLI["cli/run_experiments.py<br/>argparse thin wrapper"]
        API["api/<br/>main.py (FastAPI routes, thin)<br/>services.py (SimulationService)<br/>schemas.py (Pydantic models)"]
        TESTS["tests/<br/>test_api.py · test_models.py · test_schedulers.py"]
    end

    subgraph PKG["cloud_scheduler/ (installable package)"]
        CFG["config.py<br/>SearchConfig (single source of truth)"]
        WL["workloads.py<br/>WorkloadProtocol<br/>RandomWorkload · UniformWorkload"]
        MD["models.py<br/>Task · VM · ScheduleMetrics<br/>FitnessEvaluator · evaluate_schedule()"]

        subgraph SCH["schedulers/"]
            INIT["__init__.py<br/>Scheduler protocol + registry"]
            BASE["baselines.py<br/>FCFS · RoundRobin"]
            GA["ga.py<br/>GeneticAlgorithm"]
            PSO["pso.py<br/>ParticleSwarm"]
            HYB["hybrid.py<br/>HybridGAPSO · HybridGAPSOPareto"]
        end
    end

    CLI --> PKG
    API --> PKG
    TESTS --> PKG
    CFG --> SCH
    WL --> SCH
    MD --> SCH
```

## Architecture

The `cloud_scheduler` package holds all the scheduling logic. The CLI, the FastAPI backend and the tests are thin layers on top of it.

### Project structure

```text
meta-heuristic-algorithm-for-task-scheduling-in-cloud-infrastructure/
├── api/
│   └── main.py              # FastAPI routes (delegates to core package)
├── cloud_scheduler/
│   ├── __init__.py          # Top-level API exports
│   ├── models.py            # Task, VM, ScheduleMetrics, FitnessEvaluator
│   ├── workloads.py         # WorkloadProtocol + generate_workload()
│   └── schedulers/
│       ├── __init__.py      # Exports SearchConfig & public scheduler functions
│       ├── _operators.py    # Shared GA/PSO operators (crossover, mutate, random candidate)
│       ├── baselines.py     # FCFS and Round Robin
│       ├── ga.py            # Genetic Algorithm
│       ├── pso.py           # Continuous PSO
│       └── hybrid.py        # Discrete GA-PSO and Pareto front search
├── tests/
│   ├── test_models.py       # Metrics, energy bounds, validation
│   ├── test_schedulers.py   # Determinism, convergence, invariants for all 5 algorithms
│   └── test_api.py          # API endpoint and simulation integration tests
├── public/
│   └── index.html           # Frontend web dashboard
├── results/                 # Experiment outputs (.csv, .json)
├── run_experiments.py       # CLI entry point
├── pyproject.toml           # Packaging (pip install -e .)
├── requirements.txt         # Runtime dependencies
├── render.yaml              # Render deployment config
├── vercel.json              # Vercel deployment config
└── README.md
```

### File architecture

```mermaid
flowchart TD
    UI["public/index.html<br/>Web dashboard"] -- "POST /api/simulate" --> API

    subgraph ENTRY["Entry points"]
        CLI["run_experiments.py<br/>CLI entry point"]
        API["api/main.py<br/>FastAPI routes"]
        TESTS["tests/<br/>test_models.py<br/>test_schedulers.py<br/>test_api.py"]
    end

    subgraph PKG["cloud_scheduler/ (installable package)"]
        MD["models.py<br/>Task · VM · ScheduleMetrics<br/>FitnessEvaluator"]
        WL["workloads.py<br/>WorkloadProtocol<br/>generate_workload()"]

        subgraph SCH["schedulers/"]
            SINIT["__init__.py<br/>SearchConfig + public scheduler functions"]
            OPS["_operators.py<br/>crossover · mutate · random candidate"]
            BASE["baselines.py<br/>FCFS · Round Robin"]
            GA["ga.py<br/>Genetic Algorithm"]
            PSO["pso.py<br/>Continuous PSO"]
            HYB["hybrid.py<br/>Discrete GA-PSO · Pareto front search"]
        end
    end

    RES[("results/<br/>.csv · .json")]

    CLI --> PKG
    API --> PKG
    TESTS --> PKG
    CLI --> RES
    MD --> SCH
    WL --> SCH
    OPS --> GA
    OPS --> PSO
    OPS --> HYB
```
