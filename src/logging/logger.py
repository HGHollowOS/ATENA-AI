"""
Logging System Module

This module implements a comprehensive logging system that provides structured logging,
log rotation, and performance monitoring capabilities.

Features:
1. Structured Logging
   - JSON formatting
   - Contextual information
   - Log levels
   - Log categories

2. Log Management
   - Log rotation
   - Log compression
   - Log cleanup
   - Log analysis

3. Performance Monitoring
   - Metrics collection
   - Performance tracking
   - Resource usage
   - Error tracking
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path
import logging
import logging.handlers
import json
import structlog
import psutil
import time
from dataclasses import dataclass
from enum import Enum
import asyncio
import gzip
import shutil
from concurrent.futures import ThreadPoolExecutor
import os

class LogLevel(Enum):
    """Enum for log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogCategory(Enum):
    """Enum for log categories."""
    SYSTEM = "system"
    PERFORMANCE = "performance"
    ERROR = "error"
    SECURITY = "security"
    AUDIT = "audit"
    USER = "user"

@dataclass
class LogMetrics:
    """Data class for log metrics."""
    total_logs: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    debug_count: int = 0
    total_size: int = 0
    rotation_count: int = 0
    compression_count: int = 0
    last_cleanup: Optional[datetime] = None

class Logger:
    """
    Enhanced logging system with structured logging and performance monitoring.
    
    Features:
    - Structured logging with JSON format
    - Log rotation and compression
    - Performance metrics collection
    - Resource usage monitoring
    - Error tracking and analysis
    
    Attributes:
        log_dir: Directory for log files
        max_size: Maximum size for log files
        backup_count: Number of backup files to keep
        metrics: Log metrics
        _processing_lock: Lock for concurrent operations
    """
    
    def __init__(self, log_dir: str = "logs", max_size: int = 10 * 1024 * 1024,
                 backup_count: int = 5):
        # Setup logging directory
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup log rotation
        self.max_size = max_size
        self.backup_count = backup_count
        
        # Setup metrics
        self.metrics = LogMetrics()
        
        # Setup processing
        self._processing_lock = asyncio.Lock()
        
        # Setup thread pool
        self._thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # Initialize loggers
        self._setup_loggers()
        
        # Start monitoring
        asyncio.create_task(self._monitor_resources())
    
    def _setup_loggers(self) -> None:
        """Setup structured loggers for different categories."""
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            wrapper_class=structlog.BoundLogger
        )
        
        # Create loggers for each category
        self.loggers: Dict[LogCategory, structlog.BoundLogger] = {}
        for category in LogCategory:
            logger = structlog.get_logger(category=category.value)
            self.loggers[category] = logger
    
    async def log(self, level: LogLevel, category: LogCategory,
                 message: str, **context: Any) -> None:
        """
        Log a message with context.
        
        Args:
            level: Log level
            category: Log category
            message: Log message
            **context: Additional context
        """
        try:
            # Get logger
            logger = self.loggers[category]
            
            # Add context
            context.update({
                "timestamp": datetime.now().isoformat(),
                "level": level.value,
                "category": category.value
            })
            
            # Log message
            log_func = getattr(logger, level.value.lower())
            log_func(message, **context)
            
            # Update metrics
            await self._update_metrics(level, len(message))
            
            # Check rotation
            await self._check_rotation()
            
        except Exception as e:
            print(f"Error logging message: {str(e)}")
    
    async def _update_metrics(self, level: LogLevel, message_size: int) -> None:
        """Update log metrics."""
        try:
            self.metrics.total_logs += 1
            self.metrics.total_size += message_size
            
            if level == LogLevel.ERROR:
                self.metrics.error_count += 1
            elif level == LogLevel.WARNING:
                self.metrics.warning_count += 1
            elif level == LogLevel.INFO:
                self.metrics.info_count += 1
            elif level == LogLevel.DEBUG:
                self.metrics.debug_count += 1
                
        except Exception as e:
            print(f"Error updating metrics: {str(e)}")
    
    async def _check_rotation(self) -> None:
        """Check if log rotation is needed."""
        try:
            log_file = self.log_dir / "app.log"
            if log_file.exists() and log_file.stat().st_size >= self.max_size:
                await self._rotate_logs()
                
        except Exception as e:
            print(f"Error checking rotation: {str(e)}")
    
    async def _rotate_logs(self) -> None:
        """Rotate log files."""
        try:
            async with self._processing_lock:
                # Rotate main log file
                log_file = self.log_dir / "app.log"
                if log_file.exists():
                    # Create backup
                    backup_file = log_file.with_suffix(f".{self.metrics.rotation_count}.log")
                    shutil.move(str(log_file), str(backup_file))
                    
                    # Compress old backups
                    await self._compress_old_backups()
                    
                    # Update metrics
                    self.metrics.rotation_count += 1
                    
                    # Cleanup old backups
                    await self._cleanup_old_backups()
                    
        except Exception as e:
            print(f"Error rotating logs: {str(e)}")
    
    async def _compress_old_backups(self) -> None:
        """Compress old log backups."""
        try:
            for backup_file in self.log_dir.glob("*.log"):
                if backup_file != self.log_dir / "app.log":
                    gz_file = backup_file.with_suffix(".log.gz")
                    with open(backup_file, "rb") as f_in:
                        with gzip.open(gz_file, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    backup_file.unlink()
                    self.metrics.compression_count += 1
                    
        except Exception as e:
            print(f"Error compressing backups: {str(e)}")
    
    async def _cleanup_old_backups(self) -> None:
        """Clean up old log backups."""
        try:
            # Get all compressed backups
            backups = sorted(self.log_dir.glob("*.log.gz"))
            
            # Remove excess backups
            while len(backups) > self.backup_count:
                backups[0].unlink()
                backups = backups[1:]
                
            # Update cleanup timestamp
            self.metrics.last_cleanup = datetime.now()
            
        except Exception as e:
            print(f"Error cleaning up backups: {str(e)}")
    
    async def _monitor_resources(self) -> None:
        """Monitor system resources."""
        while True:
            try:
                # Get resource usage
                cpu_percent = psutil.cpu_percent()
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage("/")
                
                # Log resource metrics
                await self.log(
                    LogLevel.INFO,
                    LogCategory.PERFORMANCE,
                    "Resource usage metrics",
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    disk_percent=disk.percent
                )
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                print(f"Error monitoring resources: {str(e)}")
                await asyncio.sleep(60)
    
    async def get_metrics(self) -> LogMetrics:
        """Get current log metrics."""
        return self.metrics
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Stop monitoring
            self._thread_pool.shutdown(wait=True)
            
            # Final cleanup
            await self._cleanup_old_backups()
            
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
    
    def __del__(self):
        """Cleanup on deletion."""
        self._thread_pool.shutdown(wait=True) 