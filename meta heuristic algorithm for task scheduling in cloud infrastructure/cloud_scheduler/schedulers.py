"""Baseline and meta-heuristic schedulers."""

from __future__ import annotations

import random
import math
from dataclasses import dataclass, replace
from typing import Callable, Sequence

from .models import ScheduleMetrics, Task, VM, evaluate_schedule

Assignment = list[int]


@dataclass(frozen=True)
class SearchConfig:
    population_size: int = 30
    iterations: int = 100
    crossover_rate: float = 0.8
    mutation_rate: float = 0.08
    inertia: float = 0.7
    cognitive: float = 1.4
    social: float = 1.4
    hybrid_interval: int = 10
    weights: tuple[float, float, float] = (0.5, 0.25, 0.25)

    def __post_init__(self) -> None:
        if self.population_size < 4 or self.iterations < 1:
            raise ValueError("population_size must be >= 4 and iterations must be >= 1")
        if not 0 <= self.crossover_rate <= 1 or not 0 <= self.mutation_rate <= 1:
            raise ValueError("crossover_rate and mutation_rate must be between 0 and 1")
        if self.hybrid_interval < 1:
            raise ValueError("hybrid_interval must be >= 1")
        if len(self.weights) != 3 or any(weight < 0 for weight in self.weights) or sum(self.weights) <= 0:
            raise ValueError("weights must contain three non-negative values with a positive sum")
        if self.inertia < 0 or self.cognitive < 0 or self.social < 0:
            raise ValueError("PSO inertia and acceleration coefficients must be non-negative")


def _score(tasks: Sequence[Task], vms: Sequence[VM], candidate: Sequence[int], weights: tuple[float, float, float]) -> ScheduleMetrics:
    return evaluate_schedule(tasks, vms, candidate, weights)


def fcfs(tasks: Sequence[Task], vms: Sequence[VM]) -> Assignment:
    """Schedule in input order onto the VM with the earliest projected finish."""
    loads = [0.0] * len(vms)
    assignment: Assignment = []
    for task in tasks:
        vm_index = min(range(len(vms)), key=lambda i: (loads[i], i))
        assignment.append(vm_index)
        loads[vm_index] += task.length_mi / vms[vm_index].mips
    return assignment


def round_robin(tasks: Sequence[Task], vms: Sequence[VM]) -> Assignment:
    """Assign tasks cyclically, ignoring VM speed and current load."""
    return [i % len(vms) for i in range(len(tasks))]


def _random_candidate(task_count: int, vm_count: int, rng: random.Random) -> Assignment:
    return [rng.randrange(vm_count) for _ in range(task_count)]


def _tournament(population: list[Assignment], scores: list[float], rng: random.Random, size: int = 3) -> Assignment:
    contestants = rng.sample(range(len(population)), min(size, len(population)))
    return population[min(contestants, key=lambda i: scores[i])][:]


def _crossover(a: Assignment, b: Assignment, rng: random.Random) -> tuple[Assignment, Assignment]:
    if len(a) < 2:
        return a[:], b[:]
    cut = rng.randrange(1, len(a))
    return a[:cut] + b[cut:], b[:cut] + a[cut:]


def _mutate(candidate: Assignment, vm_count: int, rate: float, rng: random.Random) -> None:
    for i in range(len(candidate)):
        if rng.random() < rate:
            candidate[i] = rng.randrange(vm_count)


def genetic_algorithm(
    tasks: Sequence[Task], vms: Sequence[VM], config: SearchConfig = SearchConfig(), seed: int = 0
) -> Assignment:
    rng = random.Random(seed)
    population = [_random_candidate(len(tasks), len(vms), rng) for _ in range(config.population_size)]
    population[0] = fcfs(tasks, vms)
    best = min(population, key=lambda c: _score(tasks, vms, c, config.weights).fitness)[:]

    for _ in range(config.iterations):
        scores = [_score(tasks, vms, c, config.weights).fitness for c in population]
        ranked = sorted(range(len(population)), key=lambda i: scores[i])
        next_population = [population[i][:] for i in ranked[:2]]  # elitism
        while len(next_population) < config.population_size:
            parent1 = _tournament(population, scores, rng)
            parent2 = _tournament(population, scores, rng)
            if rng.random() < config.crossover_rate:
                child1, child2 = _crossover(parent1, parent2, rng)
            else:
                child1, child2 = parent1, parent2
            _mutate(child1, len(vms), config.mutation_rate, rng)
            _mutate(child2, len(vms), config.mutation_rate, rng)
            next_population.extend((child1, child2))
        population = next_population[:config.population_size]
        candidate = min(population, key=lambda c: _score(tasks, vms, c, config.weights).fitness)
        if _score(tasks, vms, candidate, config.weights).fitness < _score(tasks, vms, best, config.weights).fitness:
            best = candidate[:]
    return best


def _decode(position: Sequence[float], vm_count: int) -> Assignment:
    return [min(vm_count - 1, max(0, int(value * vm_count))) for value in position]


def _pso_search(tasks: Sequence[Task], vms: Sequence[VM], config: SearchConfig, seed: int) -> Assignment:
    rng = random.Random(seed)
    count, dimensions = config.population_size, len(tasks)
    positions = [[rng.random() for _ in range(dimensions)] for _ in range(count)]
    velocities = [[rng.uniform(-0.2, 0.2) for _ in range(dimensions)] for _ in range(count)]
    positions[0] = [(i + 0.5) / len(vms) for i in fcfs(tasks, vms)]
    personal_best = [p[:] for p in positions]
    fitness: Callable[[Sequence[float]], float] = lambda p: _score(tasks, vms, _decode(p, len(vms)), config.weights).fitness
    personal_scores = [fitness(p) for p in personal_best]
    global_best = personal_best[min(range(count), key=lambda i: personal_scores[i])][:]
    global_score = fitness(global_best)

    for _ in range(config.iterations):
        for particle in range(count):
            for dimension in range(dimensions):
                r1, r2 = rng.random(), rng.random()
                velocities[particle][dimension] = (
                    config.inertia * velocities[particle][dimension]
                    + config.cognitive * r1 * (personal_best[particle][dimension] - positions[particle][dimension])
                    + config.social * r2 * (global_best[dimension] - positions[particle][dimension])
                )
                positions[particle][dimension] = min(0.999999, max(0.0, positions[particle][dimension] + velocities[particle][dimension]))

            current_score = fitness(positions[particle])
            if current_score < personal_scores[particle]:
                personal_best[particle] = positions[particle][:]
                personal_scores[particle] = current_score
                if current_score < global_score:
                    global_best, global_score = positions[particle][:], current_score

    return _decode(global_best, len(vms))


def _min_min(tasks: Sequence[Task], vms: Sequence[VM]) -> Assignment:
    """Construct a heterogeneous-workload seed using the classic Min-Min rule."""
    loads = [0.0] * len(vms)
    assignment = [-1] * len(tasks)
    remaining = set(range(len(tasks)))
    while remaining:
        best_task = -1
        best_vm = -1
        best_finish = float("inf")
        for task_index in remaining:
            task = tasks[task_index]
            for vm_index, vm in enumerate(vms):
                finish = loads[vm_index] + task.length_mi / vm.mips
                if finish < best_finish:
                    best_task, best_vm, best_finish = task_index, vm_index, finish
        assignment[best_task] = best_vm
        loads[best_vm] = best_finish
        remaining.remove(best_task)
    return assignment


def _local_improve(
    tasks: Sequence[Task], vms: Sequence[VM], candidate: Assignment,
    weights: tuple[float, float, float],
) -> Assignment:
    """Apply deterministic best-improvement VM moves until a full pass stalls."""
    best = candidate[:]
    best_score = _score(tasks, vms, best, weights).fitness
    improved = True
    while improved:
        improved = False
        for task_index in range(len(tasks)):
            original_vm = best[task_index]
            task_best_vm = original_vm
            task_best_score = best_score
            for vm_index in range(len(vms)):
                if vm_index == original_vm:
                    continue
                trial = best[:]
                trial[task_index] = vm_index
                trial_score = _score(tasks, vms, trial, weights).fitness
                if trial_score + 1e-12 < task_best_score:
                    task_best_vm, task_best_score = vm_index, trial_score
            if task_best_vm != original_vm:
                best[task_index] = task_best_vm
                best_score = task_best_score
                improved = True
    return best


def _categorical_sample(logits: Sequence[float], rng: random.Random, temperature: float = 1.0) -> int:
    """Sample a VM category from numerically stable softmax probabilities."""
    peak = max(logits)
    weights = [math.exp(max(-60.0, (value - peak) / temperature)) for value in logits]
    return rng.choices(range(len(weights)), weights=weights, k=1)[0]


def _hybrid_discrete_search(
    tasks: Sequence[Task], vms: Sequence[VM], config: SearchConfig, seed: int
) -> Assignment:
    """Discrete categorical PSO with stagnation-triggered GA and local refinement."""
    rng = random.Random(seed)
    particle_count, task_count, vm_count = config.population_size, len(tasks), len(vms)
    positions = [_random_candidate(task_count, vm_count, rng) for _ in range(particle_count)]
    seeds = (fcfs(tasks, vms), _min_min(tasks, vms), round_robin(tasks, vms))
    for index, assignment in enumerate(seeds[:particle_count]):
        positions[index] = assignment[:]

    # Each task has one categorical velocity per VM. The position itself always
    # remains a valid integer task-to-VM assignment.
    velocities = [[[0.0] * vm_count for _ in range(task_count)] for _ in range(particle_count)]
    personal_best = [position[:] for position in positions]
    score = lambda candidate: _score(tasks, vms, candidate, config.weights).fitness
    personal_scores = [score(position) for position in positions]
    global_index = min(range(particle_count), key=lambda i: personal_scores[i])
    global_best = personal_best[global_index][:]
    global_score = personal_scores[global_index]
    stale_iterations = 0

    for _ in range(config.iterations):
        improved_global = False
        for particle in range(particle_count):
            current = positions[particle]
            for task_index in range(task_count):
                current_vm = current[task_index]
                personal_vm = personal_best[particle][task_index]
                global_vm = global_best[task_index]
                logits = velocities[particle][task_index]
                for vm_index in range(vm_count):
                    current_bit = 1.0 if vm_index == current_vm else 0.0
                    personal_bit = 1.0 if vm_index == personal_vm else 0.0
                    global_bit = 1.0 if vm_index == global_vm else 0.0
                    logits[vm_index] = max(-6.0, min(6.0,
                        config.inertia * logits[vm_index]
                        + config.cognitive * rng.random() * (personal_bit - current_bit)
                        + config.social * rng.random() * (global_bit - current_bit)
                        + 2.0 * current_bit
                    ))
                current[task_index] = _categorical_sample(logits, rng)

            current_score = score(current)
            if current_score < personal_scores[particle]:
                personal_best[particle] = current[:]
                personal_scores[particle] = current_score
                if current_score < global_score:
                    global_best, global_score = current[:], current_score
                    improved_global = True

        stale_iterations = 0 if improved_global else stale_iterations + 1

        # Use GA operators only after the swarm has stopped making progress.
        if stale_iterations >= config.hybrid_interval:
            ranked = sorted(range(particle_count), key=lambda i: score(positions[i]))
            parent_pool = ranked[:max(2, particle_count // 3)]
            children: list[Assignment] = []
            child_target = max(2, particle_count // 3)
            while len(children) < child_target:
                parent1 = positions[rng.choice(parent_pool)]
                parent2 = positions[rng.choice(parent_pool)]
                if rng.random() < config.crossover_rate:
                    child, _ = _crossover(parent1, parent2, rng)
                else:
                    child = parent1[:]
                _mutate(child, vm_count, config.mutation_rate, rng)
                children.append(child)

            worst_first = sorted(range(particle_count), key=lambda i: score(positions[i]), reverse=True)
            for particle, child in zip(worst_first, children):
                child_score = score(child)
                if child_score < score(positions[particle]):
                    positions[particle] = child
                    if child_score < personal_scores[particle]:
                        personal_best[particle] = child[:]
                        personal_scores[particle] = child_score
                    if child_score < global_score:
                        global_best, global_score = child[:], child_score
            stale_iterations = 0

    # Finish with a bounded, deterministic local search around the best swarm
    # candidate. It removes simple one-task-to-another-VM improvements.
    refined = _local_improve(tasks, vms, global_best, config.weights)
    return refined


def particle_swarm(
    tasks: Sequence[Task], vms: Sequence[VM], config: SearchConfig = SearchConfig(), seed: int = 0
) -> Assignment:
    return _pso_search(tasks, vms, config, seed)


def hybrid_ga_pso(
    tasks: Sequence[Task], vms: Sequence[VM], config: SearchConfig = SearchConfig(), seed: int = 0
) -> Assignment:
    return _hybrid_discrete_search(tasks, vms, config, seed)


def hybrid_ga_pso_pareto(
    tasks: Sequence[Task], vms: Sequence[VM], config: SearchConfig = SearchConfig(), seed: int = 0
) -> list[Assignment]:
    """Return a non-dominated set found by hybrid searches with diverse objectives.

    The returned set is an empirical approximation, not a guarantee of the
    complete Pareto front. The configured weighted objective and each individual
    metric are optimized in separate seeded runs before dominated results are
    removed.
    """
    objective_weights = dict.fromkeys((
        config.weights,
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    ))
    candidates: dict[tuple[int, ...], tuple[Assignment, tuple[float, float, float]]] = {}

    for run_index, weights in enumerate(objective_weights):
        run_config = replace(config, weights=weights)
        assignment = _hybrid_discrete_search(tasks, vms, run_config, seed + run_index)
        metrics = evaluate_schedule(tasks, vms, assignment, weights)
        objectives = (
            metrics.makespan_seconds,
            metrics.load_imbalance_seconds,
            metrics.energy_proxy_joules,
        )
        candidates[tuple(assignment)] = assignment, objectives

    pareto_front: list[tuple[Assignment, tuple[float, float, float]]] = []
    for candidate, objectives in candidates.values():
        dominated = any(
            all(other <= value for other, value in zip(other_objectives, objectives))
            and any(other < value for other, value in zip(other_objectives, objectives))
            for _, other_objectives in candidates.values()
        )
        if not dominated:
            pareto_front.append((candidate, objectives))

    return [assignment for assignment, _ in pareto_front]
