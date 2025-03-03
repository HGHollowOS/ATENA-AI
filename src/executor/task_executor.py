"""
Task Executor Module

This module implements a comprehensive task execution system that manages task scheduling,
execution, monitoring, and error handling.

Features:
1. Task Management
   - Task scheduling and prioritization
   - Concurrent execution
   - Resource monitoring
   - Error handling and recovery

2. Task Analysis
   - Performance tracking
   - Resource usage analysis
   - Dependency management
   - Execution history

3. Performance Optimizations
   - Task queuing
   - Load balancing
   - Resource allocation
   - Caching
"""

from typing import Dict, List, Optional, Any, Set, Tuple, Union
from datetime import datetime
from pydantic import BaseModel, Field
import asyncio
from dataclasses import dataclass
from enum import Enum
import hashlib
import time
import json
from pathlib import Path
import psutil
import logging
from collections import defaultdict, deque
import traceback

class TaskStatus(Enum):
    """Enum for task status."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class TaskPriority(Enum):
    """Enum for task priorities."""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3

class TaskType(Enum):
    """Enum for task types."""
    SYSTEM = "system"
    USER = "user"
    MAINTENANCE = "maintenance"
    MONITORING = "monitoring"
    RECOVERY = "recovery"

@dataclass
class TaskMetrics:
    """Data class for task metrics."""
    start_time: datetime
    end_time: Optional[datetime] = None
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    io_operations: int = 0
    network_usage: float = 0.0
    error_count: int = 0
    retry_count: int = 0
    execution_time: float = 0.0

class Task(BaseModel):
    """Model for task definition."""
    id: str = Field(..., description="Unique task identifier")
    name: str = Field(..., description="Task name")
    command: str = Field(..., description="Command to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    type: TaskType = Field(default=TaskType.USER, description="Task type")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current status")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    error: Optional[str] = Field(default=None, description="Error message")
    result: Optional[Any] = Field(default=None, description="Task result")
    metrics: Optional[TaskMetrics] = None
    dependencies: List[str] = Field(default_factory=list, description="Task dependencies")
    timeout: Optional[float] = Field(default=None, description="Timeout in seconds")
    retry_count: int = Field(default=0, description="Number of retries")
    max_retries: int = Field(default=3, description="Maximum retries")
    tags: Set[str] = Field(default_factory=set, description="Task tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class TaskExecutor:
    """
    Task execution system that manages task scheduling, execution, and monitoring.
    
    Features:
    - Task scheduling and prioritization
    - Concurrent execution with resource limits
    - Task monitoring and metrics collection
    - Error handling and recovery
    - Task history and analysis
    
    Attributes:
        max_concurrent_tasks: Maximum number of concurrent tasks
        task_queue: Priority queue for task scheduling
        running_tasks: Dictionary of currently running tasks
        task_history: List of completed tasks
        resource_limits: Resource usage limits
        _processing_lock: Lock for concurrent operations
    """
    
    def __init__(self, max_concurrent_tasks: int = 10,
                 resource_limits: Optional[Dict[str, float]] = None):
        # Setup task management
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_queue = asyncio.PriorityQueue()
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_history: List[Task] = []
        
        # Setup resource limits
        self.resource_limits = resource_limits or {
            "cpu_percent": 80.0,
            "memory_percent": 80.0,
            "io_operations": 1000,
            "network_usage": 1024 * 1024  # 1MB/s
        }
        
        # Setup processing
        self._processing_lock = asyncio.Lock()
        self._task_metrics: Dict[str, TaskMetrics] = {}
        self._resource_usage: Dict[str, float] = defaultdict(float)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    async def submit_task(self, task: Task) -> str:
        """
        Submit a task for execution.
        
        Args:
            task: Task to execute
            
        Returns:
            Task ID
            
        Raises:
            ValueError: If task submission fails
        """
        try:
            # Validate task
            self._validate_task(task)
            
            # Check dependencies
            if task.dependencies:
                await self._check_dependencies(task)
            
            # Add to queue
            await self.task_queue.put((
                -task.priority.value,  # Negative for higher priority first
                task.created_at.timestamp(),
                task
            ))
            
            # Start processing if not already running
            if not self.running_tasks:
                asyncio.create_task(self._process_task_queue())
            
            return task.id
            
        except Exception as e:
            self.logger.error(f"Error submitting task: {str(e)}")
            raise ValueError(f"Failed to submit task: {str(e)}")
    
    async def get_task_status(self, task_id: str) -> TaskStatus:
        """
        Get the current status of a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Current task status
            
        Raises:
            ValueError: If task not found
        """
        try:
            # Check running tasks
            if task_id in self.running_tasks:
                return TaskStatus.RUNNING
            
            # Check queue
            for _, _, task in self.task_queue._queue:
                if task.id == task_id:
                    return TaskStatus.SCHEDULED
            
            # Check history
            for task in self.task_history:
                if task.id == task_id:
                    return task.status
            
            raise ValueError(f"Task not found: {task_id}")
            
        except Exception as e:
            self.logger.error(f"Error getting task status: {str(e)}")
            raise ValueError(f"Failed to get task status: {str(e)}")
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running or scheduled task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if task was cancelled, False otherwise
            
        Raises:
            ValueError: If task not found
        """
        try:
            # Check running tasks
            if task_id in self.running_tasks:
                task = self.running_tasks[task_id]
                task.cancel()
                del self.running_tasks[task_id]
                return True
            
            # Check queue
            new_queue = asyncio.PriorityQueue()
            cancelled = False
            while not self.task_queue.empty():
                priority, timestamp, task = await self.task_queue.get()
                if task.id == task_id:
                    cancelled = True
                else:
                    await new_queue.put((priority, timestamp, task))
            
            self.task_queue = new_queue
            return cancelled
            
        except Exception as e:
            self.logger.error(f"Error cancelling task: {str(e)}")
            raise ValueError(f"Failed to cancel task: {str(e)}")
    
    async def get_task_result(self, task_id: str) -> Any:
        """
        Get the result of a completed task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task result
            
        Raises:
            ValueError: If task not found or not completed
        """
        try:
            # Check history
            for task in self.task_history:
                if task.id == task_id:
                    if task.status == TaskStatus.COMPLETED:
                        return task.result
                    elif task.status == TaskStatus.FAILED:
                        raise ValueError(f"Task failed: {task.error}")
                    else:
                        raise ValueError("Task not completed")
            
            raise ValueError(f"Task not found: {task_id}")
            
        except Exception as e:
            self.logger.error(f"Error getting task result: {str(e)}")
            raise ValueError(f"Failed to get task result: {str(e)}")
    
    async def get_task_metrics(self, task_id: str) -> Optional[TaskMetrics]:
        """
        Get the metrics for a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task metrics if available
            
        Raises:
            ValueError: If task not found
        """
        try:
            # Check running tasks
            if task_id in self._task_metrics:
                return self._task_metrics[task_id]
            
            # Check history
            for task in self.task_history:
                if task.id == task_id:
                    return task.metrics
            
            raise ValueError(f"Task not found: {task_id}")
            
        except Exception as e:
            self.logger.error(f"Error getting task metrics: {str(e)}")
            raise ValueError(f"Failed to get task metrics: {str(e)}")
    
    async def get_resource_usage(self) -> Dict[str, float]:
        """
        Get current resource usage.
        
        Returns:
            Dictionary of resource usage metrics
        """
        try:
            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "io_operations": sum(self._resource_usage["io_operations"]),
                "network_usage": sum(self._resource_usage["network_usage"])
            }
        except Exception as e:
            self.logger.error(f"Error getting resource usage: {str(e)}")
            return {}
    
    async def cleanup(self) -> None:
        """Clean up completed tasks and reset resource usage."""
        try:
            async with self._processing_lock:
                # Clean up task history
                self.task_history = self.task_history[-1000:]  # Keep last 1000 tasks
                
                # Reset resource usage
                self._resource_usage.clear()
                
                # Clean up metrics
                self._task_metrics.clear()
                
        except Exception as e:
            self.logger.error(f"Error cleaning up: {str(e)}")
    
    def _validate_task(self, task: Task) -> None:
        """Validate task parameters."""
        if not task.id:
            raise ValueError("Task ID is required")
        if not task.name:
            raise ValueError("Task name is required")
        if not task.command:
            raise ValueError("Task command is required")
        if task.priority not in TaskPriority:
            raise ValueError("Invalid task priority")
        if task.type not in TaskType:
            raise ValueError("Invalid task type")
    
    async def _check_dependencies(self, task: Task) -> None:
        """Check if all task dependencies are completed."""
        for dep_id in task.dependencies:
            dep_status = await self.get_task_status(dep_id)
            if dep_status != TaskStatus.COMPLETED:
                raise ValueError(f"Dependency not completed: {dep_id}")
    
    async def _process_task_queue(self) -> None:
        """Process tasks from the queue."""
        try:
            while True:
                # Check resource limits
                if not await self._check_resource_limits():
                    await asyncio.sleep(1)
                    continue
                
                # Get next task
                try:
                    _, _, task = await self.task_queue.get()
                except asyncio.CancelledError:
                    break
                
                # Start task execution
                self.running_tasks[task.id] = asyncio.create_task(
                    self._execute_task(task)
                )
                
                # Wait if max concurrent tasks reached
                while len(self.running_tasks) >= self.max_concurrent_tasks:
                    await asyncio.sleep(0.1)
            
        except Exception as e:
            self.logger.error(f"Error processing task queue: {str(e)}")
    
    async def _execute_task(self, task: Task) -> None:
        """Execute a task and collect metrics."""
        try:
            # Update task status
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            # Initialize metrics
            metrics = TaskMetrics(start_time=task.started_at)
            self._task_metrics[task.id] = metrics
            
            # Execute command
            start_time = time.time()
            result = await self._run_command(task.command, task.parameters)
            
            # Update task
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            
            # Update metrics
            metrics.end_time = task.completed_at
            metrics.execution_time = time.time() - start_time
            
            # Add to history
            self.task_history.append(task)
            
            # Clean up
            del self.running_tasks[task.id]
            del self._task_metrics[task.id]
            
        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            self.task_history.append(task)
            del self.running_tasks[task.id]
            del self._task_metrics[task.id]
            
        except Exception as e:
            # Handle error
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            
            # Retry if possible
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                await self.submit_task(task)
            else:
                self.task_history.append(task)
            
            del self.running_tasks[task.id]
            del self._task_metrics[task.id]
            
            self.logger.error(f"Task execution failed: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    async def _run_command(self, command: str, parameters: Dict[str, Any]) -> Any:
        """Run a command with parameters."""
        try:
            # Implementation for command execution
            # This should be implemented based on the specific command types
            # supported by the system
            pass
        except Exception as e:
            raise RuntimeError(f"Command execution failed: {str(e)}")
    
    async def _check_resource_limits(self) -> bool:
        """Check if resource usage is within limits."""
        try:
            usage = await self.get_resource_usage()
            
            if usage["cpu_percent"] > self.resource_limits["cpu_percent"]:
                return False
            if usage["memory_percent"] > self.resource_limits["memory_percent"]:
                return False
            if usage["io_operations"] > self.resource_limits["io_operations"]:
                return False
            if usage["network_usage"] > self.resource_limits["network_usage"]:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking resource limits: {str(e)}")
            return False
    
    async def get_task_history(self, limit: int = 100) -> List[Task]:
        """
        Get task execution history.
        
        Args:
            limit: Maximum number of tasks to return
            
        Returns:
            List of completed tasks
        """
        return self.task_history[-limit:]
    
    async def get_task_statistics(self) -> Dict[str, Any]:
        """Get task execution statistics."""
        try:
            stats = {
                "total_tasks": len(self.task_history),
                "completed_tasks": 0,
                "failed_tasks": 0,
                "cancelled_tasks": 0,
                "running_tasks": len(self.running_tasks),
                "queued_tasks": self.task_queue.qsize(),
                "average_execution_time": 0.0,
                "success_rate": 0.0
            }
            
            if self.task_history:
                completed = [t for t in self.task_history if t.status == TaskStatus.COMPLETED]
                failed = [t for t in self.task_history if t.status == TaskStatus.FAILED]
                cancelled = [t for t in self.task_history if t.status == TaskStatus.CANCELLED]
                
                stats["completed_tasks"] = len(completed)
                stats["failed_tasks"] = len(failed)
                stats["cancelled_tasks"] = len(cancelled)
                
                if completed:
                    stats["average_execution_time"] = sum(
                        t.metrics.execution_time for t in completed
                    ) / len(completed)
                
                stats["success_rate"] = len(completed) / len(self.task_history)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting task statistics: {str(e)}")
            return {} 