"""
Main Application Module

This module implements the main application entry point that initializes and manages
all system components, including lifecycle management, configuration, and error handling.

Features:
1. Component Management
   - Component initialization
   - Lifecycle management
   - Dependency injection
   - Resource cleanup

2. Configuration Management
   - Environment variables
   - Configuration validation
   - Dynamic configuration
   - Secret management

3. Error Handling
   - Graceful shutdown
   - Error recovery
   - Health monitoring
   - State persistence
"""

from typing import Dict, List, Optional, Any, Type
from pathlib import Path
import asyncio
import signal
import sys
from datetime import datetime
import json
from dataclasses import dataclass
from enum import Enum
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import psutil
import structlog

from logging.logger import Logger, LogLevel, LogCategory
from meta_agent.meta_agent import MetaAgent
from input_processor.input_processor import InputProcessor
from nlu.intent_analyzer import IntentAnalyzer
from dialogue.context_manager import DialogueContext
from knowledge.knowledge_base import KnowledgeBase
from executor.task_executor import TaskExecutor
from services.external_services import ExternalServices

class ComponentStatus(Enum):
    """Enum for component status."""
    INITIALIZED = "initialized"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class ComponentInfo:
    """Data class for component information."""
    name: str
    status: ComponentStatus
    start_time: Optional[datetime] = None
    error: Optional[str] = None
    metrics: Dict[str, Any] = None

class AppConfig(BaseModel):
    """Model for application configuration."""
    log_dir: str = Field("logs", description="Log directory")
    max_log_size: int = Field(10 * 1024 * 1024, description="Maximum log size")
    backup_count: int = Field(5, description="Number of backup files")
    debug_mode: bool = Field(False, description="Debug mode")
    components: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Component configurations")

class Application:
    """
    Main application class that manages all system components.
    
    Features:
    - Component lifecycle management
    - Configuration management
    - Error handling and recovery
    - Health monitoring
    - Graceful shutdown
    
    Attributes:
        config: Application configuration
        logger: System logger
        components: Dictionary of system components
        component_info: Component status information
        _shutdown_event: Event for graceful shutdown
    """
    
    def __init__(self, config_path: str = "config.json"):
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize logger
        self.logger = Logger(
            log_dir=self.config.log_dir,
            max_size=self.config.max_log_size,
            backup_count=self.config.backup_count
        )
        
        # Initialize components
        self.components: Dict[str, Any] = {}
        self.component_info: Dict[str, ComponentInfo] = {}
        
        # Setup shutdown
        self._shutdown_event = asyncio.Event()
        
        # Setup signal handlers
        self._setup_signal_handlers()
    
    def _load_config(self, config_path: str) -> AppConfig:
        """Load application configuration."""
        try:
            # Load environment variables
            load_dotenv()
            
            # Load config file
            if os.path.exists(config_path):
                with open(config_path) as f:
                    config_data = json.load(f)
            else:
                config_data = {}
            
            # Create config object
            return AppConfig(**config_data)
            
        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
            sys.exit(1)
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        for sig in (signal.SIGTERM, signal.SIGINT):
            asyncio.get_event_loop().add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(self._handle_shutdown(s))
            )
    
    async def _handle_shutdown(self, sig: signal.Signals) -> None:
        """Handle shutdown signals."""
        try:
            await self.logger.log(
                LogLevel.INFO,
                LogCategory.SYSTEM,
                f"Received signal {sig.name}, initiating shutdown"
            )
            
            # Set shutdown event
            self._shutdown_event.set()
            
            # Stop components
            await self.stop()
            
            # Exit
            sys.exit(0)
            
        except Exception as e:
            await self.logger.log(
                LogLevel.ERROR,
                LogCategory.SYSTEM,
                f"Error during shutdown: {str(e)}"
            )
            sys.exit(1)
    
    async def initialize(self) -> None:
        """Initialize all system components."""
        try:
            # Initialize components in order
            components = [
                (MetaAgent, "meta_agent"),
                (InputProcessor, "input_processor"),
                (IntentAnalyzer, "intent_analyzer"),
                (DialogueContext, "dialogue_context"),
                (KnowledgeBase, "knowledge_base"),
                (TaskExecutor, "task_executor"),
                (ExternalServices, "external_services")
            ]
            
            for component_class, name in components:
                try:
                    # Get component config
                    config = self.config.components.get(name, {})
                    
                    # Initialize component
                    component = component_class(**config)
                    await component.initialize()
                    
                    # Store component
                    self.components[name] = component
                    self.component_info[name] = ComponentInfo(
                        name=name,
                        status=ComponentStatus.INITIALIZED,
                        start_time=datetime.now()
                    )
                    
                    await self.logger.log(
                        LogLevel.INFO,
                        LogCategory.SYSTEM,
                        f"Initialized component: {name}"
                    )
                    
                except Exception as e:
                    await self.logger.log(
                        LogLevel.ERROR,
                        LogCategory.SYSTEM,
                        f"Error initializing component {name}: {str(e)}"
                    )
                    self.component_info[name] = ComponentInfo(
                        name=name,
                        status=ComponentStatus.ERROR,
                        error=str(e)
                    )
                    raise
            
        except Exception as e:
            await self.logger.log(
                LogLevel.ERROR,
                LogCategory.SYSTEM,
                f"Error during initialization: {str(e)}"
            )
            await self.stop()
            raise
    
    async def start(self) -> None:
        """Start all system components."""
        try:
            # Start components
            for name, component in self.components.items():
                try:
                    # Start component
                    await component.start()
                    
                    # Update status
                    self.component_info[name].status = ComponentStatus.RUNNING
                    
                    await self.logger.log(
                        LogLevel.INFO,
                        LogCategory.SYSTEM,
                        f"Started component: {name}"
                    )
                    
                except Exception as e:
                    await self.logger.log(
                        LogLevel.ERROR,
                        LogCategory.SYSTEM,
                        f"Error starting component {name}: {str(e)}"
                    )
                    self.component_info[name].status = ComponentStatus.ERROR
                    self.component_info[name].error = str(e)
                    raise
            
            # Start health monitoring
            asyncio.create_task(self._monitor_health())
            
        except Exception as e:
            await self.logger.log(
                LogLevel.ERROR,
                LogCategory.SYSTEM,
                f"Error during startup: {str(e)}"
            )
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """Stop all system components."""
        try:
            # Stop components in reverse order
            for name, component in reversed(list(self.components.items())):
                try:
                    # Stop component
                    await component.stop()
                    
                    # Update status
                    self.component_info[name].status = ComponentStatus.STOPPED
                    
                    await self.logger.log(
                        LogLevel.INFO,
                        LogCategory.SYSTEM,
                        f"Stopped component: {name}"
                    )
                    
                except Exception as e:
                    await self.logger.log(
                        LogLevel.ERROR,
                        LogCategory.SYSTEM,
                        f"Error stopping component {name}: {str(e)}"
                    )
                    self.component_info[name].status = ComponentStatus.ERROR
                    self.component_info[name].error = str(e)
            
            # Stop logger
            await self.logger.cleanup()
            
        except Exception as e:
            await self.logger.log(
                LogLevel.ERROR,
                LogCategory.SYSTEM,
                f"Error during shutdown: {str(e)}"
            )
            raise
    
    async def _monitor_health(self) -> None:
        """Monitor system health."""
        while not self._shutdown_event.is_set():
            try:
                # Get system metrics
                cpu_percent = psutil.cpu_percent()
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage("/")
                
                # Check component health
                for name, component in self.components.items():
                    try:
                        # Get component metrics
                        metrics = await component.get_metrics()
                        
                        # Update component info
                        self.component_info[name].metrics = metrics
                        
                        # Log health status
                        await self.logger.log(
                            LogLevel.INFO,
                            LogCategory.PERFORMANCE,
                            f"Component health: {name}",
                            metrics=metrics,
                            cpu_percent=cpu_percent,
                            memory_percent=memory.percent,
                            disk_percent=disk.percent
                        )
                        
                    except Exception as e:
                        await self.logger.log(
                            LogLevel.ERROR,
                            LogCategory.SYSTEM,
                            f"Error monitoring component {name}: {str(e)}"
                        )
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                await self.logger.log(
                    LogLevel.ERROR,
                    LogCategory.SYSTEM,
                    f"Error during health monitoring: {str(e)}"
                )
                await asyncio.sleep(60)
    
    async def run(self) -> None:
        """Run the application."""
        try:
            # Initialize
            await self.initialize()
            
            # Start
            await self.start()
            
            # Wait for shutdown
            await self._shutdown_event.wait()
            
        except Exception as e:
            await self.logger.log(
                LogLevel.ERROR,
                LogCategory.SYSTEM,
                f"Error during application run: {str(e)}"
            )
            raise
        finally:
            # Stop
            await self.stop()

async def main():
    """Main entry point."""
    try:
        # Create application
        app = Application()
        
        # Run application
        await app.run()
        
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Run application
    asyncio.run(main()) 