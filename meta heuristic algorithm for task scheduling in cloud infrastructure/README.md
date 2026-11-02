# Cloud Task Scheduling Simulator

This project compares five schedulers for independent cloud tasks: FCFS, Round Robin, Genetic Algorithm (GA), Particle Swarm Optimization (PSO), and a proposed hybrid GA-PSO.

## Requirements

- Python 3.10 or newer
- No third-party packages are required

## Run an experiment

From this folder, run:

```powershell
python run_experiments.py
```

The default run creates 30 tasks and 5 heterogeneous VMs, repeats each algorithm 10 times, and writes `results/runs.csv` and `results/summary.json`.

Customize the experiment:

```powershell
python run_experiments.py --tasks 100 --vms 10 --repeats 10 --iterations 150 --population 40 --seed 42
```

For a stronger comparison, evaluate several independently generated workloads while keeping every scheduler matched to the same workload within each seed:

```powershell
python run_experiments.py --tasks 100 --vms 10 --repeats 10 --workload-seeds 42 43 44 45 46 47 48 49 --output results/100tasks_10vms_seed_sweep
```

The summary includes pooled statistics and a `by_workload_seed` section. FCFS and Round Robin are run once per workload because their results are deterministic; GA, PSO, and the hybrid are each run `--repeats` times per workload.

The hybrid uses categorical VM assignments directly, starts with FCFS, Min-Min, and Round Robin seeds, and injects GA crossover/mutation after a configurable number of stagnant iterations. A final best-improvement pass tries moving each task to another VM. Tune the objective emphasis with `--weights MAKESPAN BALANCE ENERGY`; weights are normalized by the simulator and default to `0.50 0.25 0.25`. For example, put more emphasis on energy with `--weights 0.4 0.2 0.4`. A weighted score represents a tradeoff and does not guarantee that one schedule is best on every separate metric.

## Deploy the web demo to Render and Vercel

The repository includes a small browser interface in `public/` and a FastAPI endpoint in `api/`. Render runs the scheduling API; Vercel serves the interface. Both services should be connected to the same Git repository.

1. Push this project to a Git provider that both Render and Vercel can access.
2. In Render, create a **Blueprint** from the repository and set the Blueprint file path to `meta heuristic algorithm for task scheduling in cloud infrastructure/render.yaml`. Render creates the `cloud-task-scheduler-api` web service from that config. After it deploys, copy its public URL, such as `https://cloud-task-scheduler-api.onrender.com`.
3. In Vercel, import the same repository. Set the Root Directory to `meta heuristic algorithm for task scheduling in cloud infrastructure` and use the **Other** framework preset. `vercel.json` serves the static files from `public/`; no build command or extra packages are needed.
4. Open the Vercel URL, paste the Render URL into **Render API URL**, and run a comparison. The URL is saved in that browser.

The API is public and has no sign-in. Request limits keep each run bounded (up to 100 tasks, 20 VMs, 150 iterations, and a population of 40). Render's free service may sleep while idle, so its first request after inactivity can take longer. Energy remains the simulator's illustrative proxy, not measured hardware consumption.

The API is also documented at `<render-service-url>/docs`, and its health check is `<render-service-url>/health`.

Each experiment also writes `results/pareto_front.csv`. The hybrid runs with the configured weights and with each individual metric emphasized, then reports the non-dominated schedules found across those runs. This is an empirical Pareto approximation, not a guarantee of the complete Pareto front; compare makespan, balance, and energy in that file to select the tradeoff that fits your deployment.

For a single-seed run, the synthetic workload is generated once and shared by every algorithm. With `--workload-seeds`, each seed generates a separate workload shared by all algorithms. Randomized algorithms receive different seeds across repeats. The baseline schedulers are deterministic, so repeating them on the same workload is unnecessary.

## Model and metrics

- A task has a length in Million Instructions (MI).
- A VM has a speed in Million Instructions Per Second (MIPS).
- Tasks assigned to a VM run sequentially; execution time is `task length / VM speed`.
- Makespan is the maximum total execution time across VMs.
- Load imbalance is the population standard deviation of VM completion times.
- Energy is an illustrative proxy: a VM draws its configured maximum power while busy, then its idle power until the makespan. Values are reported in joules but are not measurements of real hardware consumption.
- Search fitness is a normalized weighted sum with weights 0.50 makespan, 0.25 imbalance, and 0.25 energy. Raw metrics are also written so the tradeoffs remain visible.

The current simulator assumes independent, non-preemptive tasks, known task sizes and VM speeds, and no network transfer delay. Standalone PSO uses continuous particle positions decoded into discrete VM IDs. The hybrid uses a categorical discrete PSO representation, stagnation-triggered GA crossover/mutation, and local improvement. Its Pareto output is generated by separate runs with makespan-only, balance-only, energy-only, and configured weighted objectives.

