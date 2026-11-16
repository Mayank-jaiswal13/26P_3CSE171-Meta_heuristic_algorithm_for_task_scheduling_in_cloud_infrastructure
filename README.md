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
