"""CrewRole — 基于角色的多 Agent 协作系统

借鉴 CrewAI 的角色定义模式，增强 L6 分层团队支持。
纯 Python，零外部依赖。

核心概念：
- Role: Agent 角色（名称/目标/背景/工具/委托权限）
- Task: 任务（描述/期望输出/分配角色）
- Crew: 团队（角色列表/任务列表/流程类型）
- Process: 流程（顺序/层级/自定义）
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("auto_agent_kit.crew_role")


class ProcessType(str, Enum):
    """流程类型"""
    SEQUENTIAL = "sequential"      # 顺序执行：角色按顺序处理任务
    HIERARCHICAL = "hierarchical"  # 层级执行：主管分配任务给下属
    PARALLEL = "parallel"          # 并行执行：所有角色同时处理
    CUSTOM = "custom"              # 自定义流程


@dataclass
class Role:
    """Agent 角色定义"""
    name: str
    goal: str
    backstory: str = ""
    tools: list[str] = field(default_factory=list)
    allow_delegation: bool = False
    max_iterations: int = 10
    verbose: bool = False
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "goal": self.goal,
            "backstory": self.backstory,
            "tools": self.tools,
            "allow_delegation": self.allow_delegation,
            "max_iterations": self.max_iterations,
            "verbose": self.verbose,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Role":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def build_system_prompt(self) -> str:
        """构建角色系统提示词"""
        parts = [f"你是 {self.name}。", f"目标：{self.goal}"]
        if self.backstory:
            parts.append(f"背景：{self.backstory}")
        if self.tools:
            parts.append(f"可用工具：{', '.join(self.tools)}")
        if self.allow_delegation:
            parts.append("你可以将任务委托给其他角色。")
        parts.append(f"每次任务最多 {self.max_iterations} 轮迭代。")
        return "\n".join(parts)


@dataclass
class Task:
    """任务定义"""
    description: str
    expected_output: str = ""
    agent_role: Optional[str] = None
    context: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    async_execution: bool = False
    callback: Optional[Callable] = None
    metadata: dict = field(default_factory=dict)
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "expected_output": self.expected_output,
            "agent_role": self.agent_role,
            "context": self.context,
            "tools": self.tools,
            "async_execution": self.async_execution,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CrewResult:
    """团队执行结果"""
    crew_name: str
    process_type: ProcessType
    task_results: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    duration_ms: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "crew_name": self.crew_name,
            "process_type": self.process_type.value,
            "task_results": self.task_results,
            "errors": self.errors,
            "duration_ms": round(self.duration_ms, 2),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def summary(self) -> str:
        total = len(self.task_results)
        done = sum(1 for r in self.task_results if r.get("status") == "completed")
        failed = len(self.errors)
        return f"{self.crew_name}: {done}/{total} 完成, {failed} 错误, {self.duration_ms:.0f}ms"


class Crew:
    """团队 — 角色 + 任务 + 流程编排"""

    def __init__(self, name: str = "default_crew",
                 process_type: ProcessType = ProcessType.SEQUENTIAL,
                 verbose: bool = False):
        self.name = name
        self.process_type = process_type
        self.verbose = verbose
        self._roles: dict[str, Role] = {}
        self._tasks: list[Task] = []
        self._role_order: list[str] = []  # 角色执行顺序

    # ---- 角色管理 ----

    def add_role(self, role: Role) -> "Crew":
        """添加角色"""
        self._roles[role.name] = role
        if role.name not in self._role_order:
            self._role_order.append(role.name)
        return self

    def add_roles(self, roles: list[Role]) -> "Crew":
        """批量添加角色"""
        for r in roles:
            self.add_role(r)
        return self

    def get_role(self, name: str) -> Optional[Role]:
        return self._roles.get(name)

    def remove_role(self, name: str) -> bool:
        if name in self._roles:
            del self._roles[name]
            if name in self._role_order:
                self._role_order.remove(name)
            return True
        return False

    @property
    def roles(self) -> list[Role]:
        return [self._roles[n] for n in self._role_order if n in self._roles]

    # ---- 任务管理 ----

    def add_task(self, task: Task) -> "Crew":
        """添加任务"""
        self._tasks.append(task)
        return self

    def add_tasks(self, tasks: list[Task]) -> "Crew":
        """批量添加任务"""
        for t in tasks:
            self.add_task(t)
        return self

    def get_task(self, task_id: str) -> Optional[Task]:
        for t in self._tasks:
            if t.task_id == task_id:
                return t
        return None

    def remove_task(self, task_id: str) -> bool:
        for i, t in enumerate(self._tasks):
            if t.task_id == task_id:
                self._tasks.pop(i)
                return True
        return False

    @property
    def tasks(self) -> list[Task]:
        return list(self._tasks)

    # ---- 任务分配 ----

    def assign_tasks(self) -> dict[str, list[Task]]:
        """将任务分配给角色"""
        assignment: dict[str, list[Task]] = {}
        for task in self._tasks:
            role_name = task.agent_role or self._role_order[0] if self._role_order else "default"
            if role_name not in assignment:
                assignment[role_name] = []
            assignment[role_name].append(task)
        return assignment

    def get_role_prompt(self, role_name: str, task: Task) -> str:
        """为角色构建完整任务提示"""
        role = self._roles.get(role_name)
        if not role:
            return f"执行任务：{task.description}"

        parts = [role.build_system_prompt()]
        if task.context:
            parts.append("上下文：")
            for ctx in task.context:
                parts.append(f"  - {ctx}")
        parts.append(f"\n当前任务：{task.description}")
        if task.expected_output:
            parts.append(f"期望输出：{task.expected_output}")
        return "\n".join(parts)

    # ---- 执行 ----

    def execute(self, task_handler: Optional[Callable] = None) -> CrewResult:
        """执行团队任务

        Args:
            task_handler: 可选的任务执行函数，接收 (role_name, task, crew) 参数
                          返回执行结果字符串。为 None 时返回提示词（供外部执行）
        """
        result = CrewResult(
            crew_name=self.name,
            process_type=self.process_type,
            started_at=time.time(),
        )

        assignment = self.assign_tasks()

        if self.process_type == ProcessType.SEQUENTIAL:
            self._execute_sequential(assignment, result, task_handler)
        elif self.process_type == ProcessType.HIERARCHICAL:
            self._execute_hierarchical(assignment, result, task_handler)
        elif self.process_type == ProcessType.PARALLEL:
            self._execute_parallel(assignment, result, task_handler)
        else:
            self._execute_sequential(assignment, result, task_handler)

        result.completed_at = time.time()
        result.duration_ms = (result.completed_at - result.started_at) * 1000

        if self.verbose:
            logger.info(f"Crew '{self.name}' completed: {result.summary}")

        return result

    def _execute_sequential(self, assignment: dict[str, list[Task]],
                            result: CrewResult, handler: Optional[Callable]):
        """顺序执行：按角色顺序逐个执行任务"""
        for role_name in self._role_order:
            if role_name not in assignment:
                continue
            for task in assignment[role_name]:
                self._execute_task(role_name, task, result, handler)

    def _execute_hierarchical(self, assignment: dict[str, list[Task]],
                              result: CrewResult, handler: Optional[Callable]):
        """层级执行：第一个角色是主管，分配任务给其他角色"""
        if not self._role_order:
            return

        manager = self._role_order[0]
        workers = self._role_order[1:]

        # 主管处理自己的任务
        if manager in assignment:
            for task in assignment[manager]:
                self._execute_task(manager, task, result, handler)

        # 主管分配任务给下属
        for worker in workers:
            if worker in assignment:
                for task in assignment[worker]:
                    self._execute_task(worker, task, result, handler)

    def _execute_parallel(self, assignment: dict[str, list[Task]],
                          result: CrewResult, handler: Optional[Callable]):
        """并行执行：所有角色同时执行（实际按顺序，但标记为并行）"""
        for role_name in self._role_order:
            if role_name not in assignment:
                continue
            for task in assignment[role_name]:
                self._execute_task(role_name, task, result, handler)

    def _execute_task(self, role_name: str, task: Task,
                      result: CrewResult, handler: Optional[Callable]):
        """执行单个任务"""
        if handler:
            try:
                prompt = self.get_role_prompt(role_name, task)
                output = handler(role_name, task, prompt)
                result.task_results.append({
                    "task_id": task.task_id,
                    "role": role_name,
                    "description": task.description[:100],
                    "status": "completed",
                    "output": str(output)[:500] if output else "",
                })
            except Exception as e:
                logger.error(f"Task {task.task_id} failed: {e}")
                result.errors.append({
                    "task_id": task.task_id,
                    "role": role_name,
                    "error": str(e),
                })
                result.task_results.append({
                    "task_id": task.task_id,
                    "role": role_name,
                    "description": task.description[:100],
                    "status": "failed",
                    "error": str(e),
                })
        else:
            # 无 handler：只返回提示词
            prompt = self.get_role_prompt(role_name, task)
            result.task_results.append({
                "task_id": task.task_id,
                "role": role_name,
                "description": task.description[:100],
                "status": "prompt_generated",
                "prompt": prompt,
            })

    # ---- 序列化 ----

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "process_type": self.process_type.value,
            "verbose": self.verbose,
            "roles": [r.to_dict() for r in self.roles],
            "tasks": [t.to_dict() for t in self._tasks],
            "role_order": self._role_order,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "Crew":
        crew = cls(
            name=data.get("name", "default_crew"),
            process_type=ProcessType(data.get("process_type", "sequential")),
            verbose=data.get("verbose", False),
        )
        for r_data in data.get("roles", []):
            crew.add_role(Role.from_dict(r_data))
        for t_data in data.get("tasks", []):
            crew.add_task(Task.from_dict(t_data))
        crew._role_order = data.get("role_order", [r.name for r in crew.roles])
        return crew

    @classmethod
    def from_json(cls, json_str: str) -> "Crew":
        return cls.from_dict(json.loads(json_str))

    # ---- 便捷工厂 ----

    @classmethod
    def create_analysis_team(cls, topic: str) -> "Crew":
        """创建分析团队（研究员 + 分析师 + 报告撰写者）"""
        crew = cls(name=f"analysis_team_{topic[:20]}", process_type=ProcessType.SEQUENTIAL)
        crew.add_roles([
            Role(
                name="研究员",
                goal=f"收集关于 {topic} 的全面信息",
                backstory="你是一名资深研究员，擅长从多源收集和整理信息。",
                tools=["web_search", "web_fetch"],
            ),
            Role(
                name="分析师",
                goal=f"分析 {topic} 的数据并提炼洞察",
                backstory="你是一名数据分析师，擅长从数据中发现模式和趋势。",
                tools=[],
            ),
            Role(
                name="报告撰写者",
                goal=f"撰写关于 {topic} 的完整报告",
                backstory="你是一名专业报告撰写者，擅长将复杂信息转化为清晰文档。",
                tools=[],
            ),
        ])
        crew.add_tasks([
            Task(
                description=f"收集 {topic} 的最新信息和数据",
                expected_output="结构化的信息集合，包含来源引用",
                agent_role="研究员",
            ),
            Task(
                description=f"分析收集到的 {topic} 数据，提炼关键洞察",
                expected_output="分析报告，包含趋势、模式和关键发现",
                agent_role="分析师",
                context=[f"研究员收集的 {topic} 信息"],
            ),
            Task(
                description=f"基于分析结果撰写 {topic} 的完整报告",
                expected_output="格式化的最终报告",
                agent_role="报告撰写者",
                context=[f"分析师对 {topic} 的分析报告"],
            ),
        ])
        return crew

    @classmethod
    def create_development_team(cls, project_name: str) -> "Crew":
        """创建开发团队（产品经理 + 开发者 + 测试者）"""
        crew = cls(name=f"dev_team_{project_name[:20]}", process_type=ProcessType.HIERARCHICAL)
        crew.add_roles([
            Role(
                name="产品经理",
                goal=f"规划 {project_name} 的功能和路线图",
                backstory="你是一名经验丰富的产品经理，擅长需求分析和优先级排序。",
                allow_delegation=True,
            ),
            Role(
                name="开发者",
                goal=f"实现 {project_name} 的功能",
                backstory="你是一名全栈开发者，擅长将需求转化为代码。",
                tools=["exec", "write", "edit"],
            ),
            Role(
                name="测试者",
                goal=f"测试 {project_name} 的功能质量",
                backstory="你是一名 QA 工程师，擅长发现和报告问题。",
                tools=["exec"],
            ),
        ])
        return crew
