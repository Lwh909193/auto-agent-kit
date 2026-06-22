"""ToolRouter — 语义工具路由器

阶段性工具暴露，每阶段 ≤ 8 工具，防止上下文膨胀。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ToolPhase(Enum):
    """工具阶段"""
    INIT = "init"  # 初始阶段 — 核心工具
    EXPLORE = "explore"  # 探索阶段 — 搜索/读取工具
    EXECUTE = "execute"  # 执行阶段 — 全部工具
    REVIEW = "review"  # 审查阶段 — 验证/检查工具


@dataclass
class ToolDef:
    """工具定义"""
    name: str
    description: str
    phase: ToolPhase = ToolPhase.INIT
    usage_count: int = 0
    last_used: Optional[float] = None
    is_active: bool = True


class ToolRouter:
    """语义工具路由器 — 阶段性暴露工具，防止上下文膨胀"""

    PHASE_LIMITS = {
        ToolPhase.INIT: 5,
        ToolPhase.EXPLORE: 6,
        ToolPhase.EXECUTE: 8,
        ToolPhase.REVIEW: 5,
    }

    def __init__(self):
        self._tools: dict[str, ToolDef] = {}
        self._current_phase: ToolPhase = ToolPhase.INIT
        self._phase_history: list[ToolPhase] = []

    def register(self, name: str, description: str, phase: ToolPhase = ToolPhase.INIT) -> ToolDef:
        """注册一个工具"""
        tool = ToolDef(name=name, description=description, phase=phase)
        self._tools[name] = tool
        return tool

    def register_batch(self, tools: list[dict]) -> list[ToolDef]:
        """批量注册工具"""
        results = []
        for t in tools:
            results.append(self.register(
                name=t["name"],
                description=t["description"],
                phase=ToolPhase(t.get("phase", "init")),
            ))
        return results

    def set_phase(self, phase: ToolPhase) -> list[ToolDef]:
        """切换阶段，返回当前阶段可用工具"""
        self._phase_history.append(self._current_phase)
        self._current_phase = phase
        return self.get_active_tools()

    def get_active_tools(self) -> list[ToolDef]:
        """获取当前阶段可用工具"""
        active = [
            t for t in self._tools.values()
            if t.phase == self._current_phase and t.is_active
        ]
        limit = self.PHASE_LIMITS.get(self._current_phase, 8)
        return active[:limit]

    def get_all_tools(self) -> list[ToolDef]:
        """获取所有注册工具"""
        return list(self._tools.values())

    def use_tool(self, name: str) -> Optional[ToolDef]:
        """记录工具使用"""
        import time
        tool = self._tools.get(name)
        if tool:
            tool.usage_count += 1
            tool.last_used = time.time()
        return tool

    def deactivate(self, name: str) -> bool:
        """停用工具"""
        tool = self._tools.get(name)
        if tool:
            tool.is_active = False
            return True
        return False

    def activate(self, name: str) -> bool:
        """启用工具"""
        tool = self._tools.get(name)
        if tool:
            tool.is_active = True
            return True
        return False

    def get_stats(self) -> dict:
        """获取工具使用统计"""
        return {
            "total_tools": len(self._tools),
            "current_phase": self._current_phase.value,
            "active_tools": len(self.get_active_tools()),
            "phase_history": [p.value for p in self._phase_history],
            "usage": {
                name: {"count": t.usage_count, "phase": t.phase.value}
                for name, t in self._tools.items()
            },
        }

    def find_dead_tools(self, threshold_days: float = 30) -> list[str]:
        """查找长期未使用的工具"""
        import time
        now = time.time()
        threshold_seconds = threshold_days * 86400
        dead = []
        for name, tool in self._tools.items():
            if tool.last_used and (now - tool.last_used) > threshold_seconds:
                dead.append(name)
        return dead
