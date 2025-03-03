"""
Logging Module

This module provides standardized logging functionality for the entire system,
including structured logging, performance metrics, and error tracking.
"""

import logging
import structlog
from typing import Any, Dict, Optional
from datetime import datetime
import json
from pathlib import Path

class SystemLogger:
    """
    System-wide logger that provides structured logging with different levels
    and automatic context tracking.
    """
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer()
            ],
            logger_factory=structlog.PrintLoggerFactory(),
            wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
            cache_logger_on_first_use=True,
        )
        
        # Create different loggers for different purposes
        self.logger = structlog.get_logger()
        self.error_logger = structlog.get_logger("error")
        self.performance_logger = structlog.get_logger("performance")
        self.security_logger = structlog.get_logger("security")
        
        # Initialize context
        self.context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs) -> None:
        """Set logging context for the current session."""
        self.context.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear the current logging context."""
        self.context.clear()
    
    def info(self, message: str, **kwargs) -> None:
        """Log an informational message."""
        self.logger.info(message, **{**self.context, **kwargs})
    
    def warning(self, message: str, **kwargs) -> None:
        """Log a warning message."""
        self.logger.warning(message, **{**self.context, **kwargs})
    
    def error(self, message: str, **kwargs) -> None:
        """Log an error message."""
        self.error_logger.error(message, **{**self.context, **kwargs})
    
    def debug(self, message: str, **kwargs) -> None:
        """Log a debug message."""
        self.logger.debug(message, **{**self.context, **kwargs})
    
    def log_performance(self, metric_name: str, value: float, **kwargs) -> None:
        """Log a performance metric."""
        self.performance_logger.info(
            "performance_metric",
            metric=metric_name,
            value=value,
            timestamp=datetime.now().isoformat(),
            **{**self.context, **kwargs}
        )
    
    def log_security(self, event_type: str, details: Dict[str, Any], **kwargs) -> None:
        """Log a security-related event."""
        self.security_logger.info(
            "security_event",
            event_type=event_type,
            details=details,
            timestamp=datetime.now().isoformat(),
            **{**self.context, **kwargs}
        )
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """Log an error with full context and stack trace."""
        error_context = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": self._get_stack_trace(error),
            "timestamp": datetime.now().isoformat(),
            **(context or {}),
            **self.context
        }
        self.error_logger.error("error_occurred", **error_context)
    
    def _get_stack_trace(self, error: Exception) -> str:
        """Get the stack trace of an error."""
        import traceback
        return "".join(traceback.format_exception(type(error), error, error.__traceback__))
    
    def export_logs(self, log_type: str = "all", start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Export logs of a specific type within a time range."""
        # Implementation for log export
        return {}
    
    def rotate_logs(self) -> None:
        """Rotate log files to prevent them from growing too large."""
        # Implementation for log rotation
        pass 