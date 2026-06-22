"""ErrorReflection — 错误反射模块

工具失败自动分类（20+类型），精确恢复策略。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ErrorCategory(Enum):
    """错误分类（20+ 类型）"""
    # 认证/授权
    AUTH_INVALID = "auth_invalid"
    AUTH_EXPIRED = "auth_expired"
    PERMISSION_DENIED = "permission_denied"
    # 计费/配额
    BILLING_ERROR = "billing_error"
    RATE_LIMIT = "rate_limit"
    QUOTA_EXCEEDED = "quota_exceeded"
    # 网络/超时
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    DNS_FAILURE = "dns_failure"
    CONNECTION_REFUSED = "connection_refused"
    # 服务端
    SERVER_ERROR = "server_error"  # 5xx
    SERVICE_UNAVAILABLE = "service_unavailable"
    # 客户端
    BAD_REQUEST = "bad_request"  # 4xx
    NOT_FOUND = "not_found"
    VALIDATION_ERROR = "validation_error"
    # 数据
    PARSE_ERROR = "parse_error"
    ENCODING_ERROR = "encoding_error"
    DATA_INTEGRITY = "data_integrity"
    # 上下文
    CONTEXT_OVERFLOW = "context_overflow"
    CONTENT_FILTER = "content_filter"
    # 系统
    RESOURCE_EXHAUSTED = "resource_exhausted"
    INTERNAL_ERROR = "internal_error"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """恢复策略"""
    RETRY = "retry"  # 直接重试
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # 指数退避重试
    ROTATE_CREDENTIAL = "rotate_credential"  # 轮换凭证
    COMPRESS_CONTEXT = "compress_context"  # 压缩上下文
    FALLBACK_MODEL = "fallback_model"  # 切换备用模型
    FALLBACK_PROVIDER = "fallback_provider"  # 切换备用提供商
    DEGRADE = "degrade"  # 降级返回部分结果
    ABORT = "abort"  # 放弃
    RETRY_WITH_DELAY = "retry_with_delay"  # 延迟后重试
    CLEAR_CACHE = "clear_cache"  # 清除缓存


@dataclass
class ErrorRecord:
    """错误记录"""
    timestamp: float = field(default_factory=time.time)
    category: ErrorCategory = ErrorCategory.UNKNOWN
    message: str = ""
    source: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    recovery_used: Optional[RecoveryStrategy] = None
    recovered: bool = False


class ErrorReflection:
    """错误反射 — 自动分类错误并选择恢复策略"""

    # 错误 → 恢复策略映射
    STRATEGY_MAP: dict[ErrorCategory, RecoveryStrategy] = {
        ErrorCategory.AUTH_INVALID: RecoveryStrategy.ROTATE_CREDENTIAL,
        ErrorCategory.AUTH_EXPIRED: RecoveryStrategy.ROTATE_CREDENTIAL,
        ErrorCategory.PERMISSION_DENIED: RecoveryStrategy.ABORT,
        ErrorCategory.BILLING_ERROR: RecoveryStrategy.ABORT,
        ErrorCategory.RATE_LIMIT: RecoveryStrategy.EXPONENTIAL_BACKOFF,
        ErrorCategory.QUOTA_EXCEEDED: RecoveryStrategy.FALLBACK_PROVIDER,
        ErrorCategory.TIMEOUT: RecoveryStrategy.EXPONENTIAL_BACKOFF,
        ErrorCategory.NETWORK_ERROR: RecoveryStrategy.RETRY,
        ErrorCategory.DNS_FAILURE: RecoveryStrategy.RETRY_WITH_DELAY,
        ErrorCategory.CONNECTION_REFUSED: RecoveryStrategy.RETRY_WITH_DELAY,
        ErrorCategory.SERVER_ERROR: RecoveryStrategy.EXPONENTIAL_BACKOFF,
        ErrorCategory.SERVICE_UNAVAILABLE: RecoveryStrategy.FALLBACK_PROVIDER,
        ErrorCategory.BAD_REQUEST: RecoveryStrategy.ABORT,
        ErrorCategory.NOT_FOUND: RecoveryStrategy.ABORT,
        ErrorCategory.VALIDATION_ERROR: RecoveryStrategy.ABORT,
        ErrorCategory.PARSE_ERROR: RecoveryStrategy.RETRY,
        ErrorCategory.ENCODING_ERROR: RecoveryStrategy.RETRY,
        ErrorCategory.DATA_INTEGRITY: RecoveryStrategy.ABORT,
        ErrorCategory.CONTEXT_OVERFLOW: RecoveryStrategy.COMPRESS_CONTEXT,
        ErrorCategory.CONTENT_FILTER: RecoveryStrategy.DEGRADE,
        ErrorCategory.RESOURCE_EXHAUSTED: RecoveryStrategy.FALLBACK_MODEL,
        ErrorCategory.INTERNAL_ERROR: RecoveryStrategy.RETRY,
        ErrorCategory.UNKNOWN: RecoveryStrategy.RETRY,
    }

    # 关键词 → 错误分类映射
    KEYWORD_MAP: list[tuple[list[str], ErrorCategory]] = [
        (["rate limit", "too many requests", "429"], ErrorCategory.RATE_LIMIT),
        (["timeout", "timed out", "deadline exceeded"], ErrorCategory.TIMEOUT),
        (["auth", "unauthorized", "401", "403", "api key"], ErrorCategory.AUTH_INVALID),
        (["expired", "token expired"], ErrorCategory.AUTH_EXPIRED),
        (["permission", "forbidden", "not allowed"], ErrorCategory.PERMISSION_DENIED),
        (["billing", "quota", "insufficient"], ErrorCategory.BILLING_ERROR),
        (["context length", "context window", "token limit"], ErrorCategory.CONTEXT_OVERFLOW),
        (["content filter", "content policy", "safety"], ErrorCategory.CONTENT_FILTER),
        (["not found", "404"], ErrorCategory.NOT_FOUND),
        (["server error", "500", "502", "503"], ErrorCategory.SERVER_ERROR),
        (["connection refused", "econnrefused"], ErrorCategory.CONNECTION_REFUSED),
        (["dns", "enotfound", "getaddrinfo"], ErrorCategory.DNS_FAILURE),
        (["parse", "json decode", "unexpected token"], ErrorCategory.PARSE_ERROR),
        (["encoding", "unicode", "utf"], ErrorCategory.ENCODING_ERROR),
        (["validation", "invalid"], ErrorCategory.VALIDATION_ERROR),
        (["resource exhausted", "memory", "disk"], ErrorCategory.RESOURCE_EXHAUSTED),
    ]

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.history: list[ErrorRecord] = []
        self._consecutive_failures: dict[str, int] = {}

    def classify(self, error: Exception | str, source: str = "") -> ErrorCategory:
        """分类错误"""
        msg = str(error).lower()
        for keywords, category in self.KEYWORD_MAP:
            if any(kw in msg for kw in keywords):
                return category
        return ErrorCategory.UNKNOWN

    def get_strategy(self, category: ErrorCategory) -> RecoveryStrategy:
        """获取恢复策略"""
        return self.STRATEGY_MAP.get(category, RecoveryStrategy.RETRY)

    def classify_and_recover(
        self,
        error: Exception | str,
        source: str = "",
        context: Optional[dict] = None,
    ) -> dict:
        """分类错误并返回恢复建议"""
        category = self.classify(error, source)
        strategy = self.get_strategy(category)

        record = ErrorRecord(
            category=category,
            message=str(error),
            source=source,
            context=context or {},
            recovery_used=strategy,
        )
        self.history.append(record)

        # 追踪连续失败
        key = f"{source}:{category.value}"
        self._consecutive_failures[key] = self._consecutive_failures.get(key, 0) + 1
        consecutive = self._consecutive_failures[key]

        # 连续失败升级策略
        if consecutive >= 3 and strategy in (RecoveryStrategy.RETRY, RecoveryStrategy.EXPONENTIAL_BACKOFF):
            upgraded = RecoveryStrategy.FALLBACK_PROVIDER
            record.recovery_used = upgraded
            return {
                "category": category.value,
                "strategy": upgraded.value,
                "consecutive_failures": consecutive,
                "message": str(error),
                "upgraded": True,
            }

        return {
            "category": category.value,
            "strategy": strategy.value,
            "consecutive_failures": consecutive,
            "message": str(error),
            "upgraded": False,
        }

    def report_recovery(self, success: bool, error_ref: Optional[str] = None):
        """报告恢复结果"""
        if self.history:
            self.history[-1].recovered = success
            if success:
                key = f"{self.history[-1].source}:{self.history[-1].category.value}"
                self._consecutive_failures[key] = 0

    def get_stats(self) -> dict:
        """获取错误统计"""
        total = len(self.history)
        if total == 0:
            return {"total": 0}
        by_category: dict[str, int] = {}
        recovered = 0
        for r in self.history:
            by_category[r.category.value] = by_category.get(r.category.value, 0) + 1
            if r.recovered:
                recovered += 1
        return {
            "total": total,
            "by_category": by_category,
            "recovered": recovered,
            "recovery_rate": recovered / total if total > 0 else 0,
        }
