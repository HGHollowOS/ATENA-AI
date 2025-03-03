"""
Error Handling System

This module implements a comprehensive error handling system with retry mechanisms,
circuit breakers, and recovery strategies.

Features:
1. Error Management
   - Custom exception classes
   - Error categorization
   - Error tracking
   - Error reporting

2. Recovery Mechanisms
   - Retry strategies
   - Circuit breakers
   - Fallback mechanisms
   - State recovery

3. Monitoring
   - Error metrics
   - Error patterns
   - Error reporting
   - Health checks
"""

from typing import Dict, List, Optional, Any, Callable, Type, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncio
import traceback
import logging
from functools import wraps
import time
from collections import defaultdict
import json
from pathlib import Path

from logging.logger import Logger, LogLevel, LogCategory

class ErrorSeverity(Enum):
    """Enum for error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Enum for error categories."""
    SYSTEM = "system"
    NETWORK = "network"
    DATABASE = "database"
    VALIDATION = "validation"
    SECURITY = "security"
    BUSINESS = "business"
    EXTERNAL = "external"

@dataclass
class ErrorContext:
    """Data class for error context."""
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    component: str
    operation: str
    error: Exception
    stack_trace: str
    context: Dict[str, Any]
    retry_count: int = 0
    recovery_attempted: bool = False
    recovered: bool = False

class CircuitBreaker:
    """Circuit breaker implementation for error handling."""
    
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "CLOSED"
        self._lock = asyncio.Lock()
    
    async def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        async with self._lock:
            self.failures += 1
            self.last_failure_time = datetime.now()
            
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
    
    async def record_success(self) -> None:
        """Record a success and reset the circuit breaker."""
        async with self._lock:
            self.failures = 0
            self.state = "CLOSED"
    
    async def can_execute(self) -> bool:
        """Check if execution is allowed."""
        async with self._lock:
            if self.state == "CLOSED":
                return True
            
            if self.state == "OPEN":
                if (datetime.now() - self.last_failure_time).seconds >= self.reset_timeout:
                    self.state = "HALF-OPEN"
                    return True
                return False
            
            return True

class RetryStrategy:
    """Retry strategy implementation."""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0,
                 max_delay: float = 60.0, exponential_base: float = 2.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for the next retry attempt."""
        delay = min(
            self.base_delay * (self.exponential_base ** (attempt - 1)),
            self.max_delay
        )
        return delay

class ErrorHandler:
    """
    Comprehensive error handling system.
    
    Features:
    - Error tracking and categorization
    - Retry mechanisms
    - Circuit breakers
    - Recovery strategies
    - Error reporting
    
    Attributes:
        logger: System logger
        circuit_breakers: Dictionary of circuit breakers
        error_contexts: List of error contexts
        retry_strategies: Dictionary of retry strategies
    """
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_contexts: List[ErrorContext] = []
        self.retry_strategies: Dict[str, RetryStrategy] = {}
        self.error_patterns: Dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()
    
    def register_circuit_breaker(self, component: str,
                               failure_threshold: int = 5,
                               reset_timeout: int = 60) -> None:
        """Register a circuit breaker for a component."""
        self.circuit_breakers[component] = CircuitBreaker(
            failure_threshold=failure_threshold,
            reset_timeout=reset_timeout
        )
    
    def register_retry_strategy(self, component: str,
                              max_attempts: int = 3,
                              base_delay: float = 1.0,
                              max_delay: float = 60.0) -> None:
        """Register a retry strategy for a component."""
        self.retry_strategies[component] = RetryStrategy(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay
        )
    
    async def handle_error(self, error: Exception,
                          component: str,
                          operation: str,
                          severity: ErrorSeverity,
                          category: ErrorCategory,
                          context: Dict[str, Any] = None,
                          retry: bool = True) -> Any:
        """
        Handle an error with appropriate recovery mechanisms.
        
        Args:
            error: The exception that occurred
            component: Component where the error occurred
            operation: Operation that failed
            severity: Error severity
            category: Error category
            context: Additional context
            retry: Whether to attempt retry
            
        Returns:
            Result of recovery attempt if successful
        """
        try:
            # Create error context
            error_context = ErrorContext(
                timestamp=datetime.now(),
                severity=severity,
                category=category,
                component=component,
                operation=operation,
                error=error,
                stack_trace=traceback.format_exc(),
                context=context or {}
            )
            
            # Log error
            await self.logger.log(
                LogLevel.ERROR,
                LogCategory.ERROR,
                f"Error in {component} during {operation}",
                error=str(error),
                severity=severity.value,
                category=category.value,
                context=context
            )
            
            # Update error patterns
            error_key = f"{component}:{operation}:{type(error).__name__}"
            self.error_patterns[error_key] += 1
            
            # Check circuit breaker
            if component in self.circuit_breakers:
                circuit_breaker = self.circuit_breakers[component]
                await circuit_breaker.record_failure()
                
                if not await circuit_breaker.can_execute():
                    await self.logger.log(
                        LogLevel.WARNING,
                        LogCategory.SYSTEM,
                        f"Circuit breaker open for {component}"
                    )
                    return None
            
            # Attempt recovery if enabled
            if retry and component in self.retry_strategies:
                return await self._attempt_recovery(error_context)
            
            # Store error context
            async with self._lock:
                self.error_contexts.append(error_context)
            
            return None
            
        except Exception as e:
            await self.logger.log(
                LogLevel.ERROR,
                LogCategory.ERROR,
                f"Error in error handler: {str(e)}"
            )
            return None
    
    async def _attempt_recovery(self, error_context: ErrorContext) -> Any:
        """Attempt to recover from an error using retry strategy."""
        try:
            retry_strategy = self.retry_strategies[error_context.component]
            error_context.retry_count += 1
            
            if error_context.retry_count > retry_strategy.max_attempts:
                await self.logger.log(
                    LogLevel.ERROR,
                    LogCategory.ERROR,
                    f"Max retry attempts reached for {error_context.component}"
                )
                return None
            
            # Calculate delay
            delay = retry_strategy.get_delay(error_context.retry_count)
            
            # Log retry attempt
            await self.logger.log(
                LogLevel.INFO,
                LogCategory.SYSTEM,
                f"Retrying {error_context.component} operation",
                attempt=error_context.retry_count,
                delay=delay
            )
            
            # Wait before retry
            await asyncio.sleep(delay)
            
            # Attempt recovery
            error_context.recovery_attempted = True
            
            # Here you would implement the actual recovery logic
            # This is a placeholder for demonstration
            if error_context.retry_count <= retry_strategy.max_attempts:
                error_context.recovered = True
                return True
            
            return None
            
        except Exception as e:
            await self.logger.log(
                LogLevel.ERROR,
                LogCategory.ERROR,
                f"Error during recovery attempt: {str(e)}"
            )
            return None
    
    async def get_error_metrics(self) -> Dict[str, Any]:
        """Get error handling metrics."""
        try:
            async with self._lock:
                return {
                    "total_errors": len(self.error_contexts),
                    "error_patterns": dict(self.error_patterns),
                    "circuit_breakers": {
                        name: {
                            "state": breaker.state,
                            "failures": breaker.failures
                        }
                        for name, breaker in self.circuit_breakers.items()
                    },
                    "recovery_stats": {
                        "attempted": sum(1 for e in self.error_contexts if e.recovery_attempted),
                        "successful": sum(1 for e in self.error_contexts if e.recovered)
                    }
                }
        except Exception as e:
            await self.logger.log(
                LogLevel.ERROR,
                LogCategory.ERROR,
                f"Error getting metrics: {str(e)}"
            )
            return {}
    
    async def cleanup(self) -> None:
        """Clean up error handling resources."""
        try:
            # Save error contexts to file
            error_file = Path("logs/errors.json")
            error_file.parent.mkdir(parents=True, exist_ok=True)
            
            async with self._lock:
                with open(error_file, "w") as f:
                    json.dump(
                        [
                            {
                                "timestamp": e.timestamp.isoformat(),
                                "severity": e.severity.value,
                                "category": e.category.value,
                                "component": e.component,
                                "operation": e.operation,
                                "error": str(e.error),
                                "context": e.context,
                                "retry_count": e.retry_count,
                                "recovered": e.recovered
                            }
                            for e in self.error_contexts
                        ],
                        f,
                        indent=2
                    )
            
        except Exception as e:
            await self.logger.log(
                LogLevel.ERROR,
                LogCategory.ERROR,
                f"Error during cleanup: {str(e)}"
            )

def handle_errors(component: str,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 category: ErrorCategory = ErrorCategory.SYSTEM,
                 retry: bool = True):
    """
    Decorator for handling errors in functions.
    
    Args:
        component: Component name
        severity: Error severity
        category: Error category
        retry: Whether to attempt retry
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            error_handler = kwargs.get("error_handler")
            if not error_handler:
                return await func(*args, **kwargs)
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                return await error_handler.handle_error(
                    error=e,
                    component=component,
                    operation=func.__name__,
                    severity=severity,
                    category=category,
                    context={"args": args, "kwargs": kwargs},
                    retry=retry
                )
        return wrapper
    return decorator 