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
    changes_made: Dict[str, Dict[str, Any]]
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
        """Determine the type of optimization needed based on improvement actions."""
        if not actions:
            return OptimizationType.PARAMETER_TUNING

        # Count action types
        action_types = [action.action_type for action in actions]
        emergency_count = action_types.count('emergency_optimization')
        model_update_count = action_types.count('update_decision_weights')
        
        if emergency_count > 0:
            return OptimizationType.PARAMETER_TUNING
        elif model_update_count > 0:
            return OptimizationType.MODEL_UPDATE
        else:
            return OptimizationType.PARAMETER_TUNING
    
    async def _generate_optimization(
        self,
        target_module: str,
        optimization_type: OptimizationType,
        actions: List[ImprovementAction],
        current_performance: Dict[str, float]
    ) -> Dict[str, Any]:
        """Generate optimization parameters based on current performance and history."""
        if optimization_type == OptimizationType.PARAMETER_TUNING:
            # Get current config for the module
            module_prefix = f"{target_module}_"
            current_params = {
                k.replace(module_prefix, ''): v
                for k, v in self.config.items()
                if k.startswith(module_prefix)
            }
            
            # Generate new parameters based on performance
            new_params = {}
            rollback_data = {}
            
            for param, value in current_params.items():
                if isinstance(value, (int, float)):
                    if 'timeout' in param or 'interval' in param:
                        # Adjust timeouts based on latency
                        if current_performance.get('api_latency', 0) > self.meta_agent.thresholds['api_latency']:
                            new_params[param] = value * 0.5  # Reduce timeout
                        rollback_data[param] = value
                    elif 'threshold' in param:
                        # Adjust thresholds based on accuracy metrics
                        if any(v < self.meta_agent.thresholds[k] for k, v in current_performance.items() if 'accuracy' in k or 'quality' in k):
                            new_params[param] = value * 0.9  # Reduce threshold
                        rollback_data[param] = value
            
            return {
                'type': optimization_type,
                'module': target_module,
                'parameters': new_params,
                'rollback_data': rollback_data
            }
        
        return {
            'type': optimization_type,
            'module': target_module,
            'parameters': {},
            'rollback_data': {}
        }
    
    async def _apply_optimization(
        self,
        optimization: Dict[str, Any]
    ) -> OptimizationResult:
        """Apply optimization changes and record the result."""
        module = optimization['module']
        changes_made = {}
        
        try:
            # Apply changes to configuration
            for param, value in optimization['parameters'].items():
                param_key = f"{module}_{param}"
                old_value = self.config.get(param_key)
                self.config[param_key] = value
                changes_made[param] = {'old': old_value, 'new': value}
            
            result = OptimizationResult(
                optimization_type=optimization['type'],
                target_module=module,
                changes_made=changes_made,
                performance_impact={},
                timestamp=datetime.now(),
                success=True,
                rollback_data=optimization['rollback_data']
            )
            
            self.optimization_history.append(result)
            return result
            
        except Exception as e:
            # Revert any changes made
            for param, values in changes_made.items():
                param_key = f"{module}_{param}"
                self.config[param_key] = values['old']
            
            return OptimizationResult(
                optimization_type=optimization['type'],
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
        """Monitor the impact of an optimization on performance metrics."""
        # Get recent metrics for the module
        impact = {}
        for metric_type, snapshots in self.meta_agent.performance_history.items():
            if not snapshots:
                continue
            
            # Get metrics after optimization
            post_opt_metrics = [
                s.value for s in snapshots
                if s.source_module == module and s.timestamp > optimization.timestamp
            ]
            
            if post_opt_metrics:
                # Calculate improvement
                current_value = np.mean(post_opt_metrics)
                baseline = baseline_performance.get(metric_type.value, 0)
                
                if metric_type == PerformanceMetric.API_LATENCY:
                    # For latency, improvement is reduction
                    impact[metric_type.value] = (baseline - current_value) / baseline
                else:
                    # For other metrics, improvement is increase
                    impact[metric_type.value] = (current_value - baseline) / baseline
        
        return impact
    
    def _should_rollback(self, impact: Dict[str, float]) -> bool:
        """Determine if an optimization should be rolled back based on its impact."""
        if not impact:
            return True
        
        # Check if any metric got significantly worse
        if any(imp < -0.1 for imp in impact.values()):  # 10% degradation
            return True
        
        # Check if improvement is insufficient
        avg_improvement = np.mean(list(impact.values()))
        return avg_improvement < self.min_improvement_threshold
    
    async def _rollback_optimization(self, optimization: OptimizationResult) -> None:
        """Roll back an optimization to its previous state."""
        if not optimization.rollback_data:
            return
        
        module = optimization.target_module
        for param, value in optimization.rollback_data.items():
            param_key = f"{module}_{param}"
            self.config[param_key] = value
    
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