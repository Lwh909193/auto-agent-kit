"""PlanMode — 计划执行模式

将复杂任务分解为可执行步骤，支持 Plan/Act 分离。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class StepStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """单个计划步骤"""
    id: str
    description: str
    status: StepStatus = StepStatus.PENDING
    dependencies: list[str] = field(default_factory=list)
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    @property
    def duration(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None


@dataclass
class ExecutionPlan:
    """完整的执行计划"""
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    context: dict[str, Any] = field(default_factory=dict)

    def add_step(self, description: str, dependencies: Optional[list[str]] = None) -> PlanStep:
        step_id = f"step_{len(self.steps) + 1}"
        step = PlanStep(
            id=step_id,
            description=description,
            dependencies=dependencies or [],
        )
        self.steps.append(step)
        return step

    def get_next_ready(self) -> Optional[PlanStep]:
        """获取下一个可执行的步骤（依赖已完成的步骤）"""
        completed_ids = {s.id for s in self.steps if s.status == StepStatus.COMPLETED}
        for step in self.steps:
            if step.status != StepStatus.PENDING:
                continue
            if all(dep in completed_ids for dep in step.dependencies):
                return step
        return None

    @property
    def progress(self) -> float:
        if not self.steps:
            return 0.0
        done = sum(1 for s in self.steps if s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED))
        return done / len(self.steps)

    @property
    def summary(self) -> str:
        total = len(self.steps)
        done = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)
        failed = sum(1 for s in self.steps if s.status == StepStatus.FAILED)
        return f"[{done}/{total} 完成, {failed} 失败, {self.progress*100:.0f}%]"


class PlanMode:
    """计划执行模式 — 将复杂任务分解为可执行步骤"""

    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries
        self.current_plan: Optional[ExecutionPlan] = None
        self._history: list[dict] = []

    def create_plan(self, goal: str, steps: Optional[list[str]] = None) -> ExecutionPlan:
        """创建执行计划"""
        plan = ExecutionPlan(goal=goal)
        if steps:
            for desc in steps:
                plan.add_step(desc)
        self.current_plan = plan
        self._history.append({"action": "create_plan", "goal": goal, "steps": len(steps or [])})
        return plan

    def start_step(self, step_id: str) -> Optional[PlanStep]:
        """开始执行一个步骤"""
        if not self.current_plan:
            return None
        for step in self.current_plan.steps:
            if step.id == step_id and step.status == StepStatus.PENDING:
                step.status = StepStatus.IN_PROGRESS
                step.started_at = time.time()
                return step
        return None

    def complete_step(self, step_id: str, result: Any = None) -> Optional[PlanStep]:
        """完成一个步骤"""
        if not self.current_plan:
            return None
        for step in self.current_plan.steps:
            if step.id == step_id and step.status == StepStatus.IN_PROGRESS:
                step.status = StepStatus.COMPLETED
                step.completed_at = time.time()
                step.result = result
                return step
        return None

    def fail_step(self, step_id: str, error: str) -> Optional[PlanStep]:
        """标记步骤失败"""
        if not self.current_plan:
            return None
        for step in self.current_plan.steps:
            if step.id == step_id and step.status == StepStatus.IN_PROGRESS:
                step.status = StepStatus.FAILED
                step.completed_at = time.time()
                step.error = error
                return step
        return None

    def execute_sequentially(self, executor: Callable[[str], Any]) -> list[dict]:
        """顺序执行所有步骤（无依赖）"""
        if not self.current_plan:
            return []
        results = []
        for step in self.current_plan.steps:
            self.start_step(step.id)
            for attempt in range(self.max_retries + 1):
                try:
                    result = executor(step.description)
                    self.complete_step(step.id, result)
                    results.append({"step": step.id, "status": "ok", "result": result})
                    break
                except Exception as e:
                    if attempt < self.max_retries:
                        continue
                    self.fail_step(step.id, str(e))
                    results.append({"step": step.id, "status": "failed", "error": str(e)})
        return results

    def get_plan_status(self) -> dict:
        """获取计划状态摘要"""
        if not self.current_plan:
            return {"status": "no_plan"}
        return {
            "goal": self.current_plan.goal,
            "progress": self.current_plan.progress,
            "summary": self.current_plan.summary,
            "steps": [
                {"id": s.id, "description": s.description, "status": s.status.value}
                for s in self.current_plan.steps
            ],
        }

    def reset(self):
        """重置计划"""
        self.current_plan = None
