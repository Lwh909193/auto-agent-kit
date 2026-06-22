"""AccessControl — 访问控制模块

4 级权限策略 + 操作审批。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional


class PermissionLevel(Enum):
    """权限等级"""
    SAFE = auto()  # 安全操作 — 自动允许
    NORMAL = auto()  # 普通操作 — 自动允许，记录日志
    SENSITIVE = auto()  # 敏感操作 — 需要审批
    DANGEROUS = auto()  # 危险操作 — 需要审批 + 二次确认


class OperationType(Enum):
    """操作类型"""
    READ = auto()
    WRITE = auto()
    DELETE = auto()
    EXECUTE = auto()
    NETWORK = auto()
    CONFIG = auto()
    ADMIN = auto()


# 操作类型 → 默认权限等级
DEFAULT_LEVELS: dict[OperationType, PermissionLevel] = {
    OperationType.READ: PermissionLevel.SAFE,
    OperationType.WRITE: PermissionLevel.NORMAL,
    OperationType.DELETE: PermissionLevel.DANGEROUS,
    OperationType.EXECUTE: PermissionLevel.SENSITIVE,
    OperationType.NETWORK: PermissionLevel.NORMAL,
    OperationType.CONFIG: PermissionLevel.SENSITIVE,
    OperationType.ADMIN: PermissionLevel.DANGEROUS,
}


@dataclass
class AccessRule:
    """访问规则"""
    pattern: str  # 路径/命令模式，支持 * 通配符
    level: PermissionLevel
    operation: Optional[OperationType] = None


@dataclass
class AccessLog:
    """访问日志"""
    timestamp: float
    operation: str
    level: PermissionLevel
    granted: bool
    reason: str = ""


class AccessControl:
    """访问控制 — 4 级权限策略"""

    def __init__(self):
        self._rules: list[AccessRule] = []
        self._logs: list[AccessLog] = []
        self._max_logs: int = 1000
        self._pending_approvals: list[dict] = []

    def add_rule(self, pattern: str, level: PermissionLevel,
                 operation: Optional[OperationType] = None):
        """添加访问规则"""
        self._rules.append(AccessRule(pattern=pattern, level=level, operation=operation))

    def add_default_rules(self):
        """添加默认规则"""
        # 安全操作
        self.add_rule("read:*", PermissionLevel.SAFE, OperationType.READ)
        self.add_rule("list:*", PermissionLevel.SAFE, OperationType.READ)
        self.add_rule("search:*", PermissionLevel.SAFE, OperationType.READ)

        # 普通操作
        self.add_rule("write:workspace/*", PermissionLevel.NORMAL, OperationType.WRITE)
        self.add_rule("write:memory/*", PermissionLevel.NORMAL, OperationType.WRITE)
        self.add_rule("network:fetch:*", PermissionLevel.NORMAL, OperationType.NETWORK)

        # 敏感操作
        self.add_rule("execute:python*", PermissionLevel.SENSITIVE, OperationType.EXECUTE)
        self.add_rule("write:config/*", PermissionLevel.SENSITIVE, OperationType.WRITE)
        self.add_rule("network:send:*", PermissionLevel.SENSITIVE, OperationType.NETWORK)

        # 危险操作
        self.add_rule("delete:*", PermissionLevel.DANGEROUS, OperationType.DELETE)
        self.add_rule("execute:rm*", PermissionLevel.DANGEROUS, OperationType.EXECUTE)
        self.add_rule("execute:format*", PermissionLevel.DANGEROUS, OperationType.EXECUTE)
        self.add_rule("config:system:*", PermissionLevel.DANGEROUS, OperationType.CONFIG)

    def check(self, operation: str, op_type: Optional[OperationType] = None) -> dict:
        """检查操作权限"""
        # 查找匹配规则
        matched_rule = None
        for rule in self._rules:
            if self._match_pattern(rule.pattern, operation):
                if op_type is None or rule.operation is None or rule.operation == op_type:
                    matched_rule = rule
                    break

        level = matched_rule.level if matched_rule else PermissionLevel.SENSITIVE

        import time
        result = {
            "operation": operation,
            "level": level.name,
            "granted": False,
            "needs_approval": level in (PermissionLevel.SENSITIVE, PermissionLevel.DANGEROUS),
            "matched_rule": matched_rule.pattern if matched_rule else None,
        }

        # SAFE 和 NORMAL 自动允许
        if level == PermissionLevel.SAFE:
            result["granted"] = True
        elif level == PermissionLevel.NORMAL:
            result["granted"] = True

        self._log(operation, level, result["granted"])
        return result

    def request_approval(self, operation: str, reason: str = "") -> dict:
        """请求审批"""
        import time
        approval = {
            "id": f"app_{int(time.time())}_{len(self._pending_approvals)}",
            "operation": operation,
            "reason": reason,
            "timestamp": time.time(),
            "status": "pending",
        }
        self._pending_approvals.append(approval)
        return approval

    def approve(self, approval_id: str) -> bool:
        """批准操作"""
        for a in self._pending_approvals:
            if a["id"] == approval_id and a["status"] == "pending":
                a["status"] = "approved"
                self._log(a["operation"], PermissionLevel.SENSITIVE, True, "approved")
                return True
        return False

    def reject(self, approval_id: str) -> bool:
        """拒绝操作"""
        for a in self._pending_approvals:
            if a["id"] == approval_id and a["status"] == "pending":
                a["status"] = "rejected"
                self._log(a["operation"], PermissionLevel.SENSITIVE, False, "rejected")
                return True
        return False

    def get_pending_approvals(self) -> list[dict]:
        """获取待审批列表"""
        return [a for a in self._pending_approvals if a["status"] == "pending"]

    def get_logs(self, limit: int = 50) -> list[dict]:
        """获取访问日志"""
        return [
            {"timestamp": l.timestamp, "operation": l.operation,
             "level": l.level.name, "granted": l.granted, "reason": l.reason}
            for l in self._logs[-limit:]
        ]

    def get_stats(self) -> dict:
        """获取统计"""
        total = len(self._logs)
        granted = sum(1 for l in self._logs if l.granted)
        return {
            "total_checks": total,
            "granted": granted,
            "denied": total - granted,
            "rules_count": len(self._rules),
            "pending_approvals": len(self.get_pending_approvals()),
        }

    def _log(self, operation: str, level: PermissionLevel, granted: bool, reason: str = ""):
        import time
        self._logs.append(AccessLog(
            timestamp=time.time(),
            operation=operation,
            level=level,
            granted=granted,
            reason=reason,
        ))
        if len(self._logs) > self._max_logs:
            self._logs = self._logs[-self._max_logs:]

    @staticmethod
    def _match_pattern(pattern: str, operation: str) -> bool:
        """简单的通配符匹配"""
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return operation.startswith(prefix)
        return pattern == operation
