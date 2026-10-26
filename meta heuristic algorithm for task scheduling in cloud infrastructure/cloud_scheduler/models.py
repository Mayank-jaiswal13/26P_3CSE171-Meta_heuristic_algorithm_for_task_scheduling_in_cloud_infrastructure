"""Core data models and schedule evaluation formulas."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import pstdev
from typing import Sequence


@dataclass(frozen=True)
class Task:
    """An independent task whose size is measured in Million Instructions (MI)."""

    task_id: int
    length_mi: float

    def __post_init__(self) -> None:
        if self.task_id < 0 or self.length_mi <= 0:
            raise ValueError("Task ID must be non-negative and task length must be positive")


@dataclass(frozen=True)
class VM:
    """A VM with processing speed in MIPS and illustrative power parameters."""

    vm_id: int
    mips: float
    idle_power_w: float = 50.0
    max_power_w: float = 100.0

    def __post_init__(self) -> None:
        if self.vm_id < 0 or self.mips <= 0:
            raise ValueError("VM ID must be non-negative and MIPS must be positive")
        if self.idle_power_w < 0 or self.max_power_w < self.idle_power_w:
            raise ValueError("Power must satisfy 0 <= idle_power_w <= max_power_w")


@dataclass(frozen=True)
class ScheduleMetrics:
    makespan_seconds: float
    load_imbalance_seconds: float
    energy_proxy_joules: float
    vm_completion_times: tuple[float, ...]
    fitness: float


def evaluate_schedule(
    tasks: Sequence[Task],
    vms: Sequence[VM],
    assignment: Sequence[int],
    weights: tuple[float, float, float] = (0.5, 0.25, 0.25),
) -> ScheduleMetrics:
    """Evaluate a task-to-VM mapping using makespan, balance, and an energy proxy.

    Tasks on each VM execute sequentially. The energy proxy is an estimate in
    joules: each VM draws max_power_w while busy and idle_power_w until the
    schedule makespan. These are illustrative model parameters, not measured
    hardware energy values.
    """
    if not tasks or not vms:
        raise ValueError("At least one task and one VM are required")
    if len(assignment) != len(tasks):
        raise ValueError("There must be exactly one VM assignment per task")
    if any(not isinstance(vm_index, int) or not 0 <= vm_index < len(vms) for vm_index in assignment):
        raise ValueError("Every assignment must be a valid zero-based VM index")
    if any(weight < 0 for weight in weights) or sum(weights) <= 0:
        raise ValueError("Fitness weights must be non-negative with a positive sum")

    loads = [0.0] * len(vms)
    for task, vm_index in zip(tasks, assignment):
        loads[vm_index] += task.length_mi / vms[vm_index].mips

    makespan = max(loads)
    imbalance = pstdev(loads) if len(loads) > 1 else 0.0
    energy = sum(
        vm.max_power_w * busy + vm.idle_power_w * (makespan - busy)
        for vm, busy in zip(vms, loads)
    )

    # Stable normalizers for comparisons across candidate schedules in one workload.
    serial_bound = sum(task.length_mi / min(vm.mips for vm in vms) for task in tasks)
    energy_bound = sum(vm.max_power_w * serial_bound for vm in vms)
    normalized = (
        makespan / serial_bound,
        imbalance / serial_bound,
        energy / energy_bound if energy_bound else 0.0,
    )
    weight_total = sum(weights)
    fitness = sum(w * metric for w, metric in zip(weights, normalized)) / weight_total

    return ScheduleMetrics(
        makespan_seconds=makespan,
        load_imbalance_seconds=imbalance,
        energy_proxy_joules=energy,
        vm_completion_times=tuple(loads),
        fitness=fitness,
    )
