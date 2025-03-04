"""
Self-Improvement module for ATENA-AI.
Handles performance evaluation, automatic updates, and system optimization
based on business intelligence outcomes and meta-agent insights.
"""

import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass
from enum import Enum
import json
import numpy as np

from .meta_agent import (
    MetaAgent,
    PerformanceMetric,
    MetricSnapshot,
    DecisionOutcome,
    ImprovementAction
)

logger = logging.getLogger(__name__)

class OptimizationType(Enum):
    """Types of system optimizations."""
    PARAMETER_TUNING = "parameter_tuning"
    MODEL_UPDATE = "model_update"
    CACHE_OPTIMIZATION = "cache_optimization"
    API_OPTIMIZATION = "api_optimization"
    RESOURCE_ALLOCATION = "resource_allocation"

@dataclass
class OptimizationResult:
    """Data structure for optimization results."""
    optimization_type: OptimizationType
    target_module: str
    changes_made: Dict[str, Any]
    performance_impact: Dict[str, float]
    timestamp: datetime
    success: bool
    rollback_data: Optional[Dict[str, Any]] = None

class SelfImprovement:
    """Self-Improvement system for ATENA-AI."""
    
    def __init__(self, config: Dict[str, Any], meta_agent: MetaAgent):
        """Initialize the Self-Improvement system."""
        self.config = config
        self.meta_agent = meta_agent
        self.optimization_history: List[OptimizationResult] = []
        self.improvement_interval = 3600  # 1 hour
        self.last_improvement = datetime.now()
        self.min_improvement_threshold = 0.05  # 5% improvement required
        
        # Module-specific optimization configs
        self.optimization_configs = {
            'business_intelligence': {
                'cache_timeout': (300, 7200),  # 5 min to 2 hours
                'min_alert_priority': (2, 4),
                'monitoring_interval': (60, 600),  # 1 min to 10 min
                'max_concurrent_requests': (5, 20)
            },
            'dialogue_manager': {
                'context_timeout': (300, 900),  # 5 min to 15 min
                'max_conversation_turns': (5, 15),
                'confidence_threshold': (0.6, 0.9)
            },
            'api_client': {
                'request_timeout': (5, 30),
                'retry_attempts': (2, 5),
                'backoff_factor': (1.0, 4.0)
            }
        }
    
    async def start(self):
        """Start the self-improvement process."""
        while True:
            try:
                await self._check_and_improve()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in self-improvement loop: {e}")
                await asyncio.sleep(60)
    
    async def _check_and_improve(self):
        """Check for needed improvements and apply them."""
        try:
            current_time = datetime.now()
            
            # Only check if enough time has passed
            if (current_time - self.last_improvement).seconds < self.improvement_interval:
                return
            
            # Get pending improvements from meta-agent
            improvements = await self.meta_agent.get_pending_improvements()
            
            if not improvements:
                return
            
            # Group improvements by module
            module_improvements: Dict[str, List[ImprovementAction]] = {}
            for action in improvements:
                if action.target_module not in module_improvements:
                    module_improvements[action.target_module] = []
                module_improvements[action.target_module].append(action)
            
            # Process improvements by module
            for module, actions in module_improvements.items():
                await self._process_module_improvements(module, actions)
            
            self.last_improvement = current_time
            
        except Exception as e:
            logger.error(f"Error checking improvements: {e}")
    
    async def _process_module_improvements(
        self,
        module: str,
        actions: List[ImprovementAction]
    ):
        """Process improvements for a specific module."""
        try:
            # Analyze current performance
            current_performance = self._get_module_performance(module)
            
            # Determine optimization type
            opt_type = self._determine_optimization_type(actions)
            
            # Generate optimization plan
            optimization = await self._generate_optimization(
                module,
                opt_type,
                actions,
                current_performance
            )
            
            if optimization:
                # Apply optimization
                result = await self._apply_optimization(optimization)
                
                if result.success:
                    # Monitor impact
                    impact = await self._monitor_optimization_impact(
                        module,
                        result,
                        current_performance
                    )
                    
                    # Rollback if impact is negative
                    if self._should_rollback(impact):
                        await self._rollback_optimization(result)
                    else:
                        # Record successful optimization
                        self.optimization_history.append(result)
            
        except Exception as e:
            logger.error(f"Error processing improvements for {module}: {e}")
    
    def _get_module_performance(self, module: str) -> Dict[str, float]:
        """Get current performance metrics for a module."""
        try:
            performance = {}
            
            # Get relevant metrics from meta-agent
            for metric_type in PerformanceMetric:
                if self.meta_agent._get_target_module(metric_type) == module:
                    metrics = list(self.meta_agent.performance_history[metric_type])
                    if metrics:
                        # Calculate average of recent metrics
                        recent_values = [
                            m.value for m in metrics[-10:]
                        ]
                        performance[metric_type.value] = np.mean(recent_values)
            
            return performance
            
        except Exception as e:
            logger.error(f"Error getting module performance: {e}")
            return {}
    
    def _determine_optimization_type(
        self,
        actions: List[ImprovementAction]
    ) -> OptimizationType:
        """Determine the type of optimization needed."""
        try:
            # Count action types
            action_types = [action.action_type for action in actions]
            
            if 'emergency_optimization' in action_types:
                # For emergency actions, focus on immediate impact
                return OptimizationType.PARAMETER_TUNING
            
            if 'update_decision_weights' in action_types:
                return OptimizationType.MODEL_UPDATE
            
            # Check performance metrics
            metrics = set()
            for action in actions:
                if 'metric' in action.parameters:
                    metrics.add(action.parameters['metric'])
            
            if 'api_latency' in metrics:
                return OptimizationType.API_OPTIMIZATION
            
            if len(actions) >= 3:
                # Multiple issues might need resource reallocation
                return OptimizationType.RESOURCE_ALLOCATION
            
            # Default to parameter tuning
            return OptimizationType.PARAMETER_TUNING
            
        except Exception as e:
            logger.error(f"Error determining optimization type: {e}")
            return OptimizationType.PARAMETER_TUNING
    
    async def _generate_optimization(
        self,
        module: str,
        opt_type: OptimizationType,
        actions: List[ImprovementAction],
        current_performance: Dict[str, float]
    ) -> Optional[Dict[str, Any]]:
        """Generate optimization parameters based on type and context."""
        try:
            if module not in self.optimization_configs:
                return None
            
            config = self.optimization_configs[module]
            optimization = {
                'type': opt_type,
                'module': module,
                'parameters': {},
                'rollback_data': {}
            }
            
            if opt_type == OptimizationType.PARAMETER_TUNING:
                # Adjust parameters based on performance
                for param, (min_val, max_val) in config.items():
                    current_val = self.config.get(f"{module}_{param}")
                    if current_val is None:
                        continue
                    
                    # Store current value for rollback
                    optimization['rollback_data'][param] = current_val
                    
                    # Calculate new value
                    if any(a.priority >= 4 for a in actions):
                        # Aggressive adjustment for high-priority issues
                        adjustment = 0.3
                    else:
                        adjustment = 0.1
                    
                    if param.endswith('timeout'):
                        # Decrease timeouts for latency issues
                        new_val = max(
                            min_val,
                            current_val * (1 - adjustment)
                        )
                    else:
                        # Increase other parameters
                        new_val = min(
                            max_val,
                            current_val * (1 + adjustment)
                        )
                    
                    optimization['parameters'][param] = new_val
            
            elif opt_type == OptimizationType.CACHE_OPTIMIZATION:
                # Optimize cache settings
                optimization['parameters'] = {
                    'cache_timeout': min(
                        config['cache_timeout'][1],
                        self.config.get(f"{module}_cache_timeout", 3600) * 0.8
                    ),
                    'cache_size': self.config.get(f"{module}_cache_size", 1000) * 1.2
                }
            
            elif opt_type == OptimizationType.API_OPTIMIZATION:
                # Optimize API-related settings
                optimization['parameters'] = {
                    'request_timeout': max(
                        config['request_timeout'][0],
                        self.config.get(f"{module}_request_timeout", 10) * 0.8
                    ),
                    'retry_attempts': min(
                        config['retry_attempts'][1],
                        self.config.get(f"{module}_retry_attempts", 3) + 1
                    )
                }
            
            return optimization
            
        except Exception as e:
            logger.error(f"Error generating optimization: {e}")
            return None
    
    async def _apply_optimization(
        self,
        optimization: Dict[str, Any]
    ) -> OptimizationResult:
        """Apply optimization changes to the system."""
        try:
            module = optimization['module']
            changes_made = {}
            
            # Apply changes
            for param, value in optimization['parameters'].items():
                config_key = f"{module}_{param}"
                old_value = self.config.get(config_key)
                self.config[config_key] = value
                changes_made[param] = {
                    'old': old_value,
                    'new': value
                }
            
            result = OptimizationResult(
                optimization_type=OptimizationType(optimization['type']),
                target_module=module,
                changes_made=changes_made,
                performance_impact={},
                timestamp=datetime.now(),
                success=True,
                rollback_data=optimization['rollback_data']
            )
            
            logger.info(
                f"Applied optimization to {module}: "
                f"type={optimization['type']}, changes={changes_made}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error applying optimization: {e}")
            return OptimizationResult(
                optimization_type=OptimizationType(optimization['type']),
                target_module=module,
                changes_made={},
                performance_impact={},
                timestamp=datetime.now(),
                success=False
            )
    
    async def _monitor_optimization_impact(
        self,
        module: str,
        optimization: OptimizationResult,
        baseline_performance: Dict[str, float]
    ) -> Dict[str, float]:
        """Monitor the impact of applied optimization."""
        try:
            # Wait for some time to observe impact
            await asyncio.sleep(300)  # 5 minutes
            
            # Get current performance
            current_performance = self._get_module_performance(module)
            
            # Calculate impact
            impact = {}
            for metric, current_value in current_performance.items():
                if metric in baseline_performance:
                    baseline = baseline_performance[metric]
                    if baseline > 0:
                        impact[metric] = (current_value - baseline) / baseline
                    else:
                        impact[metric] = 0.0
            
            # Update optimization result
            optimization.performance_impact = impact
            
            return impact
            
        except Exception as e:
            logger.error(f"Error monitoring optimization impact: {e}")
            return {}
    
    def _should_rollback(self, impact: Dict[str, float]) -> bool:
        """Determine if optimization should be rolled back."""
        try:
            if not impact:
                return True
            
            # Calculate average impact
            avg_impact = sum(impact.values()) / len(impact)
            
            # Rollback if average impact is negative
            # or improvement is below threshold
            return avg_impact < 0 or avg_impact < self.min_improvement_threshold
            
        except Exception as e:
            logger.error(f"Error checking rollback condition: {e}")
            return True
    
    async def _rollback_optimization(self, optimization: OptimizationResult):
        """Rollback optimization changes."""
        try:
            if not optimization.rollback_data:
                return
            
            module = optimization.target_module
            
            # Restore previous values
            for param, value in optimization.rollback_data.items():
                config_key = f"{module}_{param}"
                self.config[config_key] = value
            
            logger.info(
                f"Rolled back optimization for {module} due to insufficient improvement"
            )
            
        except Exception as e:
            logger.error(f"Error rolling back optimization: {e}")
    
    def get_optimization_history(
        self,
        module: Optional[str] = None,
        days: int = 7
    ) -> List[OptimizationResult]:
        """Get optimization history for analysis."""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            history = [
                opt for opt in self.optimization_history
                if opt.timestamp >= cutoff_time
                and (module is None or opt.target_module == module)
            ]
            
            return sorted(history, key=lambda x: x.timestamp, reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting optimization history: {e}")
            return [] 