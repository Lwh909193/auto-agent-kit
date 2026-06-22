"""Plugin — 插件系统

支持插件注册、生命周期钩子、事件系统。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


class Plugin:
    """插件基类"""

    name: str = ""
    version: str = "0.1.0"
    description: str = ""

    def on_register(self, kit: "PluginManager"):
        """注册时调用"""
        pass

    def on_unregister(self):
        """注销时调用"""
        pass

    def on_before_step(self, step: dict) -> dict:
        """步骤执行前调用，可修改步骤"""
        return step

    def on_after_step(self, step: dict, result: Any) -> None:
        """步骤执行后调用"""
        pass

    def on_error(self, error: Exception, context: dict) -> Optional[dict]:
        """错误发生时调用，返回恢复建议或 None"""
        return None

    def on_metric(self, name: str, value: float) -> None:
        """指标记录时调用"""
        pass


@dataclass
class Hook:
    """钩子定义"""
    name: str
    handler: Callable
    priority: int = 0  # 数字越小优先级越高
    plugin_name: str = ""


class PluginManager:
    """插件管理器"""

    def __init__(self):
        self._plugins: dict[str, Plugin] = {}
        self._hooks: dict[str, list[Hook]] = {}
        self._events: list[dict] = []
        self._max_events: int = 200

    # ── 插件生命周期 ──

    def register(self, plugin: Plugin) -> bool:
        """注册插件"""
        if plugin.name in self._plugins:
            return False
        self._plugins[plugin.name] = plugin
        plugin.on_register(self)
        self._record_event("plugin_register", {"name": plugin.name, "version": plugin.version})
        return True

    def unregister(self, name: str) -> bool:
        """注销插件"""
        plugin = self._plugins.pop(name, None)
        if plugin is None:
            return False
        plugin.on_unregister()
        # 清理该插件的钩子
        for hook_list in self._hooks.values():
            hook_list[:] = [h for h in hook_list if h.plugin_name != name]
        self._record_event("plugin_unregister", {"name": name})
        return True

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """获取插件"""
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict]:
        """列出所有插件"""
        return [
            {"name": p.name, "version": p.version, "description": p.description}
            for p in self._plugins.values()
        ]

    def is_registered(self, name: str) -> bool:
        """检查插件是否已注册"""
        return name in self._plugins

    # ── 钩子系统 ──

    def add_hook(self, hook_name: str, handler: Callable, plugin_name: str = "", priority: int = 0):
        """添加钩子"""
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(Hook(
            name=hook_name,
            handler=handler,
            priority=priority,
            plugin_name=plugin_name,
        ))
        # 按优先级排序
        self._hooks[hook_name].sort(key=lambda h: h.priority)

    def remove_hook(self, hook_name: str, handler: Callable) -> bool:
        """移除钩子"""
        hook_list = self._hooks.get(hook_name, [])
        before = len(hook_list)
        hook_list[:] = [h for h in hook_list if h.handler != handler]
        return len(hook_list) < before

    def emit(self, hook_name: str, **kwargs) -> list[Any]:
        """触发钩子，返回所有处理结果"""
        results = []
        for hook in self._hooks.get(hook_name, []):
            try:
                result = hook.handler(**kwargs)
                results.append(result)
            except Exception as e:
                self._record_event("hook_error", {
                    "hook": hook_name,
                    "plugin": hook.plugin_name,
                    "error": str(e),
                })
        return results

    def has_hooks(self, hook_name: str) -> bool:
        """检查是否有钩子"""
        return bool(self._hooks.get(hook_name))

    # ── 内置钩子快捷方式 ──

    def on_before_step(self, step: dict) -> dict:
        """触发 before_step 钩子"""
        if self.has_hooks("before_step"):
            results = self.emit("before_step", step=step)
            for r in results:
                if isinstance(r, dict):
                    step = r
        return step

    def on_after_step(self, step: dict, result: Any):
        """触发 after_step 钩子"""
        if self.has_hooks("after_step"):
            self.emit("after_step", step=step, result=result)

    def on_error(self, error: Exception, context: dict) -> Optional[dict]:
        """触发 error 钩子，返回第一个非 None 的恢复建议"""
        if self.has_hooks("error"):
            results = self.emit("error", error=error, context=context)
            for r in results:
                if r is not None:
                    return r
        return None

    # ── 事件记录 ──

    def _record_event(self, event_type: str, data: dict):
        self._events.append({
            "timestamp": time.time(),
            "type": event_type,
            "data": data,
        })
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

    def get_events(self, limit: int = 20) -> list[dict]:
        """获取最近事件"""
        return self._events[-limit:]

    def get_stats(self) -> dict:
        """获取插件统计"""
        return {
            "total_plugins": len(self._plugins),
            "total_hooks": sum(len(h) for h in self._hooks.values()),
            "hook_names": list(self._hooks.keys()),
            "plugins": self.list_plugins(),
        }


# ── 内置插件 ──

class LoggingPlugin(Plugin):
    """日志插件 — 记录所有步骤和错误"""

    name = "logging"
    version = "1.0.0"
    description = "记录所有步骤执行和错误信息"

    def __init__(self):
        self.logs: list[dict] = []
        self._max_logs = 500

    def on_before_step(self, step: dict) -> dict:
        self.logs.append({
            "time": time.time(),
            "type": "step_start",
            "step_id": step.get("id", ""),
            "description": step.get("description", ""),
        })
        if len(self.logs) > self._max_logs:
            self.logs = self.logs[-self._max_logs:]
        return step

    def on_after_step(self, step: dict, result: Any):
        self.logs.append({
            "time": time.time(),
            "type": "step_end",
            "step_id": step.get("id", ""),
            "result": str(result)[:200],
        })

    def on_error(self, error: Exception, context: dict) -> None:
        self.logs.append({
            "time": time.time(),
            "type": "error",
            "error": str(error),
            "context": context,
        })

    def get_recent_logs(self, limit: int = 10) -> list[dict]:
        return self.logs[-limit:]


class MetricsPlugin(Plugin):
    """指标插件 — 自动收集 Dashboard 指标"""

    name = "metrics"
    version = "1.0.0"
    description = "自动收集步骤耗时和错误率指标"

    def __init__(self):
        self.step_durations: list[float] = []
        self.error_count = 0
        self.step_count = 0

    def on_after_step(self, step: dict, result: Any):
        self.step_count += 1
        if "duration" in step:
            self.step_durations.append(step["duration"])

    def on_error(self, error: Exception, context: dict) -> None:
        self.error_count += 1

    @property
    def avg_duration(self) -> float:
        if not self.step_durations:
            return 0.0
        return sum(self.step_durations) / len(self.step_durations)

    @property
    def error_rate(self) -> float:
        if self.step_count == 0:
            return 0.0
        return self.error_count / self.step_count

    def get_report(self) -> dict:
        return {
            "total_steps": self.step_count,
            "total_errors": self.error_count,
            "error_rate": self.error_rate,
            "avg_duration_ms": self.avg_duration * 1000,
            "total_duration_ms": sum(self.step_durations) * 1000,
        }
