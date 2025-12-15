# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Structured Logging Configuration
Enterprise-grade logging with correlation IDs and JSON output.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import logging
import threading
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Dict, Optional

# Correlation ID context variable (thread-safe)
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


class CorrelationContext:
    """Context manager for correlation ID propagation."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())[:8]
        self._token = None
    
    def __enter__(self) -> str:
        self._token = _correlation_id.set(self.correlation_id)
        return self.correlation_id
    
    def __exit__(self, *args):
        if self._token:
            _correlation_id.reset(self._token)


def correlation_context(correlation_id: Optional[str] = None) -> CorrelationContext:
    """Create a correlation context for request tracing."""
    return CorrelationContext(correlation_id)


def get_correlation_id() -> str:
    """Get current correlation ID."""
    return _correlation_id.get() or "-"


class StructuredFormatter(logging.Formatter):
    """
    JSON-structured log formatter for production environments.
    Falls back to readable format in debug mode.
    """
    
    def __init__(self, json_output: bool = False):
        super().__init__()
        self.json_output = json_output
    
    def format(self, record: logging.LogRecord) -> str:
        correlation_id = get_correlation_id()
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        # Add extra fields
        extra = getattr(record, "extra", {})
        
        if self.json_output:
            import json
            log_dict = {
                "timestamp": timestamp,
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "correlation_id": correlation_id,
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
            if extra:
                log_dict["extra"] = extra
            if record.exc_info:
                log_dict["exception"] = self.formatException(record.exc_info)
            return json.dumps(log_dict, ensure_ascii=False)
        else:
            # Human-readable format
            level_emoji = {
                "DEBUG": "🔍",
                "INFO": "ℹ️",
                "WARNING": "⚠️",
                "ERROR": "❌",
                "CRITICAL": "🚨",
            }.get(record.levelname, "")
            
            base = f"[{timestamp[11:19]}] [{correlation_id}] {level_emoji} {record.name}: {record.getMessage()}"
            
            if extra:
                extra_str = " | ".join(f"{k}={v}" for k, v in extra.items())
                base += f" | {extra_str}"
            
            if record.exc_info:
                base += "\n" + self.formatException(record.exc_info)
            
            return base


class ContextLogger(logging.Logger):
    """Logger that automatically includes correlation ID and extra context."""
    
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, **kwargs):
        if extra is None:
            extra = {}
        extra["correlation_id"] = get_correlation_id()
        super()._log(level, msg, args, exc_info, extra, stack_info)
    
    def bind(self, **context) -> "BoundLogger":
        """Create a bound logger with persistent context."""
        return BoundLogger(self, context)


class BoundLogger:
    """Logger with bound context that persists across calls."""
    
    def __init__(self, logger: ContextLogger, context: Dict[str, Any]):
        self._logger = logger
        self._context = context
    
    def _log(self, level: str, msg: str, *args, **kwargs):
        extra = kwargs.pop("extra", {})
        extra.update(self._context)
        kwargs["extra"] = {"extra": extra}
        getattr(self._logger, level)(msg, *args, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs):
        self._log("debug", msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self._log("info", msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self._log("warning", msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self._log("error", msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        self._log("critical", msg, *args, **kwargs)
    
    def bind(self, **context) -> "BoundLogger":
        """Create a new bound logger with additional context."""
        new_context = {**self._context, **context}
        return BoundLogger(self._logger, new_context)


# Logger cache
_loggers: Dict[str, ContextLogger] = {}
_configured = False


def configure_logging(
    level: str = "INFO",
    json_output: bool = False,
    log_file: Optional[str] = None
) -> None:
    """
    Configure the logging system.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: If True, output JSON format (for production)
        log_file: Optional file path for log output
    """
    global _configured
    
    if _configured:
        return
    
    # Set custom logger class
    logging.setLoggerClass(ContextLogger)
    
    # Root logger configuration
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Clear existing handlers
    root.handlers.clear()
    
    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(StructuredFormatter(json_output=json_output))
    root.addHandler(console)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(StructuredFormatter(json_output=True))
        root.addHandler(file_handler)
    
    _configured = True


def get_logger(name: str) -> ContextLogger:
    """
    Get or create a logger with the given name.
    
    Args:
        name: Logger name (usually __name__ of the module)
    
    Returns:
        ContextLogger instance with correlation ID support
    """
    if name not in _loggers:
        # Ensure logging is configured
        if not _configured:
            env_level = os.getenv("LOG_LEVEL", "INFO")
            env_json = os.getenv("LOG_JSON", "false").lower() == "true"
            configure_logging(level=env_level, json_output=env_json)
        
        logger = logging.getLogger(name)
        _loggers[name] = logger
    
    return _loggers[name]


def log_execution_time(logger_name: str = __name__):
    """Decorator to log function execution time."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name)
            start = datetime.now()
            try:
                result = func(*args, **kwargs)
                elapsed = (datetime.now() - start).total_seconds()
                logger.debug(f"{func.__name__} completed", extra={"extra": {"elapsed_sec": elapsed}})
                return result
            except Exception as e:
                elapsed = (datetime.now() - start).total_seconds()
                logger.error(f"{func.__name__} failed: {e}", extra={"extra": {"elapsed_sec": elapsed}})
                raise
        return wrapper
    return decorator
