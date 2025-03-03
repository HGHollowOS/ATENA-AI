"""
Test suite for the error handling system.

This module contains tests for:
1. Error handling and categorization
2. Circuit breaker functionality
3. Retry mechanisms
4. Error metrics collection
5. Recovery strategies
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import json
from pathlib import Path

from src.utils.error_handler import (
    ErrorHandler, ErrorSeverity, ErrorCategory,
    CircuitBreaker, RetryStrategy, handle_errors
)
from src.logging.logger import Logger, LogLevel, LogCategory

@pytest_asyncio.fixture
async def mock_logger():
    """Create a mock logger for testing."""
    logger = Mock(spec=Logger)
    logger.log = AsyncMock()
    return logger

@pytest_asyncio.fixture
async def error_handler(mock_logger):
    """Create an error handler instance for testing."""
    handler = ErrorHandler(mock_logger)
    return handler

@pytest.mark.asyncio
async def test_error_categorization(error_handler):
    """Test error categorization and severity levels."""
    # Test error handling with different severities
    test_error = ValueError("Test error")
    
    # Test low severity
    await error_handler.handle_error(
        error=test_error,
        component="test_component",
        operation="test_operation",
        severity=ErrorSeverity.LOW,
        category=ErrorCategory.SYSTEM
    )
    
    # Test high severity
    await error_handler.handle_error(
        error=test_error,
        component="test_component",
        operation="test_operation",
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.SYSTEM
    )
    
    # Verify error patterns
    metrics = await error_handler.get_error_metrics()
    assert metrics["total_errors"] == 2
    assert "test_component:test_operation:ValueError" in metrics["error_patterns"]
    assert metrics["error_patterns"]["test_component:test_operation:ValueError"] == 2

@pytest.mark.asyncio
async def test_circuit_breaker(error_handler):
    """Test circuit breaker functionality."""
    # Register circuit breaker
    error_handler.register_circuit_breaker(
        component="test_component",
        failure_threshold=3,
        reset_timeout=1
    )
    
    # Test failures
    for _ in range(3):
        await error_handler.handle_error(
            error=ValueError("Test error"),
            component="test_component",
            operation="test_operation",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.SYSTEM
        )
    
    # Verify circuit breaker state
    metrics = await error_handler.get_error_metrics()
    assert metrics["circuit_breakers"]["test_component"]["state"] == "OPEN"
    assert metrics["circuit_breakers"]["test_component"]["failures"] == 3
    
    # Wait for reset
    await asyncio.sleep(1)
    
    # Test recovery
    await error_handler.handle_error(
        error=ValueError("Test error"),
        component="test_component",
        operation="test_operation",
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.SYSTEM
    )
    
    # Verify circuit breaker reset
    metrics = await error_handler.get_error_metrics()
    assert metrics["circuit_breakers"]["test_component"]["state"] == "OPEN"  # State remains OPEN until success

@pytest.mark.asyncio
async def test_retry_strategy(error_handler):
    """Test retry strategy functionality."""
    # Register retry strategy
    error_handler.register_retry_strategy(
        component="test_component",
        max_attempts=3,
        base_delay=0.1,
        max_delay=1.0
    )
    
    # Test retry attempts
    start_time = datetime.now()
    await error_handler.handle_error(
        error=ValueError("Test error"),
        component="test_component",
        operation="test_operation",
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.SYSTEM,
        retry=True
    )
    end_time = datetime.now()
    
    # Verify retry timing
    duration = (end_time - start_time).total_seconds()
    assert duration >= 0.1  # At least one retry with base delay
    
    # Verify metrics
    metrics = await error_handler.get_error_metrics()
    assert metrics["recovery_stats"]["attempted"] == 1
    assert metrics["recovery_stats"]["successful"] == 1

@pytest.mark.asyncio
async def test_error_handler_decorator(error_handler):
    """Test error handler decorator."""
    @handle_errors(
        component="test_component",
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.SYSTEM,
        retry=True
    )
    async def test_function(error_handler=None):
        raise ValueError("Test error")
    
    # Test decorated function
    await test_function(error_handler=error_handler)
    
    # Verify error handling
    metrics = await error_handler.get_error_metrics()
    assert metrics["total_errors"] == 1
    assert "test_component:test_function:ValueError" in metrics["error_patterns"]

@pytest.mark.asyncio
async def test_error_metrics(error_handler):
    """Test error metrics collection."""
    # Generate test errors
    for i in range(5):
        await error_handler.handle_error(
            error=ValueError(f"Test error {i}"),
            component="test_component",
            operation="test_operation",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.SYSTEM
        )
    
    # Get metrics
    metrics = await error_handler.get_error_metrics()
    
    # Verify metrics
    assert metrics["total_errors"] == 5
    assert metrics["error_patterns"]["test_component:test_operation:ValueError"] == 5
    assert metrics["recovery_stats"]["attempted"] == 0
    assert metrics["recovery_stats"]["successful"] == 0

@pytest.mark.asyncio
async def test_error_persistence(error_handler, tmp_path):
    """Test error context persistence."""
    # Create test error
    await error_handler.handle_error(
        error=ValueError("Test error"),
        component="test_component",
        operation="test_operation",
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.SYSTEM
    )
    
    # Set up test directory
    test_log_dir = tmp_path / "logs"
    test_log_dir.mkdir()
    
    # Mock Path
    with patch("src.utils.error_handler.Path") as mock_path:
        mock_path.return_value = test_log_dir / "errors.json"
        
        # Clean up (saves errors to file)
        await error_handler.cleanup()
        
        # Verify file creation
        assert (test_log_dir / "errors.json").exists()
        
        # Verify file contents
        with open(test_log_dir / "errors.json") as f:
            saved_errors = json.load(f)
            assert len(saved_errors) == 1
            assert saved_errors[0]["component"] == "test_component"
            assert saved_errors[0]["operation"] == "test_operation"
            assert saved_errors[0]["severity"] == ErrorSeverity.MEDIUM.value
            assert saved_errors[0]["category"] == ErrorCategory.SYSTEM.value

@pytest.mark.asyncio
async def test_error_logging(error_handler, mock_logger):
    """Test error logging functionality."""
    # Create test error
    test_error = ValueError("Test error")
    await error_handler.handle_error(
        error=test_error,
        component="test_component",
        operation="test_operation",
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.SYSTEM
    )
    
    # Verify logging calls
    mock_logger.log.assert_called_with(
        LogLevel.ERROR,
        LogCategory.ERROR,
        "Error in test_component during test_operation",
        error=str(test_error),
        severity=ErrorSeverity.MEDIUM.value,
        category=ErrorCategory.SYSTEM.value,
        context=None
    )

@pytest.mark.asyncio
async def test_concurrent_error_handling(error_handler):
    """Test concurrent error handling."""
    # Create multiple concurrent error handling tasks
    tasks = []
    for i in range(10):
        tasks.append(
            error_handler.handle_error(
                error=ValueError(f"Test error {i}"),
                component="test_component",
                operation="test_operation",
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.SYSTEM
            )
        )
    
    # Run tasks concurrently
    await asyncio.gather(*tasks)
    
    # Verify metrics
    metrics = await error_handler.get_error_metrics()
    assert metrics["total_errors"] == 10
    assert metrics["error_patterns"]["test_component:test_operation:ValueError"] == 10 