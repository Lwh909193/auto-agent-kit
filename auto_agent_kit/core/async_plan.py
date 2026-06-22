"""AsyncPlan — 异步计划执行模式

支持异步步骤执行、并发步骤、超时控制。
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from auto_agent_kit.core.plan_mode import ExecutionPlan, PlanStep, PlanMode, StepStatus


@dataclass
class AsyncStepResult:
    """异步步骤执行结果"""
    step_id: str
    status: str
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0


class AsyncPlanMode(PlanMode):
    """异步计划执行模式 — 支持异步步骤和并发执行"""

    def __init__(self, max_retries: int = 2, concurrency_limit: int = 3):
        super().__init__(max_retries)
        self.concurrency_limit = concurrency_limit
        self._semaphore = asyncio.Semaphore(concurrency_limit)

    async def execute_step_async(
        self,
        step: PlanStep,
        executor: Callable[[str], Any],
    ) -> AsyncStepResult:
        """异步执行单个步骤"""
        start = time.time()
        self.start_step(step.id)

        for attempt in range(self.max_retries + 1):
            try:
                async with self._semaphore:
                    if asyncio.iscoroutinefunction(executor):
                        result = await executor(step.description)
                    else:
                        result = executor(step.description)
                self.complete_step(step.id, result)
                duration_ms = (time.time() - start) * 1000
                return AsyncStepResult(
                    step_id=step.id,
                    status="ok",
                    result=result,
                    duration_ms=duration_ms,
                )
            except Exception as e:
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                    continue
                self.fail_step(step.id, str(e))
                duration_ms = (time.time() - start) * 1000
                return AsyncStepResult(
                    step_id=step.id,
                    status="failed",
                    error=str(e),
                    duration_ms=duration_ms,
                )

    async def execute_sequentially_async(
        self,
        executor: Callable[[str], Any],
        plan: Optional[ExecutionPlan] = None,
    ) -> list[AsyncStepResult]:
        """异步顺序执行所有步骤"""
        plan = plan or self.current_plan
        if not plan:
            return []

        results = []
        for step in plan.steps:
            result = await self.execute_step_async(step, executor)
            results.append(result)
        return results

    async def execute_concurrently_async(
        self,
        executor: Callable[[str], Any],
        plan: Optional[ExecutionPlan] = None,
    ) -> list[AsyncStepResult]:
        """并发执行无依赖的步骤

        按依赖关系分批执行：同一批次的步骤可以并发运行。
        """
        plan = plan or self.current_plan
        if not plan:
            return []

        results: list[AsyncStepResult] = []
        completed_ids: set[str] = set()
        pending = list(plan.steps)

        while pending:
            # 找出当前批次可执行的步骤（依赖已完成的）
            batch = []
            remaining = []
            for step in pending:
                deps = set(step.dependencies)
                if deps.issubset(completed_ids):
                    batch.append(step)
                else:
                    remaining.append(step)

            if not batch:
                # 死锁检测：有步骤但都不满足依赖
                for step in remaining:
                    results.append(AsyncStepResult(
                        step_id=step.id,
                        status="failed",
                        error=f"Deadlock: dependencies {step.dependencies} never completed",
                    ))
                break

            # 并发执行批次
            batch_results = await asyncio.gather(*[
                self.execute_step_async(step, executor) for step in batch
            ])

            for r in batch_results:
                results.append(r)
                if r.status == "ok":
                    completed_ids.add(r.step_id)

            pending = remaining

        return results

    async def execute_with_timeout(
        self,
        executor: Callable[[str], Any],
        step_description: str,
        timeout_seconds: float = 30.0,
    ) -> AsyncStepResult:
        """带超时控制的步骤执行"""
        step = PlanStep(id="timeout_step", description=step_description)
        self.current_plan = ExecutionPlan(goal=step_description)
        self.current_plan.steps = [step]

        try:
            result = await asyncio.wait_for(
                self.execute_step_async(step, executor),
                timeout=timeout_seconds,
            )
            return result
        except asyncio.TimeoutError:
            return AsyncStepResult(
                step_id=step.id,
                status="timeout",
                error=f"Step timed out after {timeout_seconds}s",
                duration_ms=timeout_seconds * 1000,
            )


# ── 辅助函数 ──

async def run_plan(
    plan_mode: AsyncPlanMode,
    steps: list[str],
    executor: Callable[[str], Any],
    concurrent: bool = False,
) -> list[AsyncStepResult]:
    """便捷函数：创建计划并执行"""
    plan = plan_mode.create_plan("async_plan", steps)
    if concurrent:
        return await plan_mode.execute_concurrently_async(executor, plan)
    return await plan_mode.execute_sequentially_async(executor, plan)
