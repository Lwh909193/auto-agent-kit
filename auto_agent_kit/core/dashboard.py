"""Dashboard — 仪表板

实时监控 Agent 运行指标。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class MetricPoint:
    """单个指标数据点"""
    timestamp: float
    value: float
    label: str = ""


@dataclass
class MetricSeries:
    """指标时间序列"""
    name: str
    points: list[MetricPoint] = field(default_factory=list)
    max_points: int = 1000

    def add(self, value: float, label: str = ""):
        self.points.append(MetricPoint(timestamp=time.time(), value=value, label=label))
        if len(self.points) > self.max_points:
            self.points = self.points[-self.max_points:]

    @property
    def last(self) -> Optional[float]:
        return self.points[-1].value if self.points else None

    @property
    def avg(self) -> float:
        if not self.points:
            return 0.0
        return sum(p.value for p in self.points) / len(self.points)

    @property
    def min(self) -> float:
        return min(p.value for p in self.points) if self.points else 0.0

    @property
    def max(self) -> float:
        return max(p.value for p in self.points) if self.points else 0.0


class Dashboard:
    """仪表板 — 实时监控 Agent 运行指标"""

    def __init__(self, max_series_points: int = 1000):
        self._series: dict[str, MetricSeries] = {}
        self._events: list[dict] = []
        self._max_events: int = 500
        self._max_series_points = max_series_points
        self._started_at: float = time.time()

    def _get_series(self, name: str) -> MetricSeries:
        if name not in self._series:
            self._series[name] = MetricSeries(name=name, max_points=self._max_series_points)
        return self._series[name]

    def record(self, metric: str, value: float, label: str = ""):
        """记录一个指标值"""
        self._get_series(metric).add(value, label)

    def record_event(self, event_type: str, data: Optional[dict] = None):
        """记录一个事件"""
        self._events.append({
            "timestamp": time.time(),
            "type": event_type,
            "data": data or {},
        })
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

    def record_tool_call(self, tool_name: str, success: bool, duration_ms: float):
        """记录工具调用"""
        self.record(f"tool.{tool_name}.duration", duration_ms)
        self.record("tool.calls", 1)
        if not success:
            self.record("tool.errors", 1)
        self.record_event("tool_call", {
            "tool": tool_name,
            "success": success,
            "duration_ms": duration_ms,
        })

    def get_metric(self, name: str) -> Optional[MetricSeries]:
        """获取指标序列"""
        return self._series.get(name)

    def get_snapshot(self) -> dict:
        """获取当前快照"""
        uptime = time.time() - self._started_at
        snapshot = {
            "uptime_seconds": uptime,
            "uptime_formatted": self._format_duration(uptime),
            "metrics": {},
            "recent_events": self._events[-20:],
        }
        for name, series in self._series.items():
            snapshot["metrics"][name] = {
                "last": series.last,
                "avg": series.avg,
                "min": series.min,
                "max": series.max,
                "count": len(series.points),
            }
        return snapshot

    def get_summary(self) -> str:
        """获取文本摘要"""
        s = self.get_snapshot()
        lines = [f"📊 Dashboard — 运行 {s['uptime_formatted']}"]
        for name, m in s["metrics"].items():
            lines.append(f"  {name}: last={m['last']:.2f} avg={m['avg']:.2f} count={m['count']}")
        return "\n".join(lines)

    def to_json(self, path: str):
        """导出到 JSON 文件"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.get_snapshot(), f, ensure_ascii=False, indent=2)

    def reset(self):
        """重置所有指标"""
        self._series.clear()
        self._events.clear()
        self._started_at = time.time()

    @staticmethod
    def _format_duration(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours}h{minutes}m{secs}s"
        elif minutes > 0:
            return f"{minutes}m{secs}s"
        return f"{secs}s"
