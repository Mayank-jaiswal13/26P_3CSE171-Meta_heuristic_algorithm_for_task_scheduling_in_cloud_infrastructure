"""Reproducible synthetic workload generation."""

from __future__ import annotations

import random

from .models import Task, VM


def generate_workload(task_count: int, vm_count: int, seed: int = 42) -> tuple[list[Task], list[VM]]:
    """Generate independent tasks and heterogeneous VMs from a fixed seed."""
    if task_count < 1 or vm_count < 1:
        raise ValueError("task_count and vm_count must both be at least 1")
    rng = random.Random(seed)
    tasks = [Task(task_id=i, length_mi=rng.randint(1_000, 10_000)) for i in range(task_count)]
    vms = [
        VM(
            vm_id=i,
            mips=float(rng.choice((500, 750, 1_000, 1_500, 2_000))),
            idle_power_w=float(rng.choice((35, 45, 55, 65))),
            max_power_w=float(rng.choice((90, 110, 130, 150))),
        )
        for i in range(vm_count)
    ]
    return tasks, vms
