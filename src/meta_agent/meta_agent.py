"""
Meta-Agent module for ATENA-AI.
Handles performance monitoring, decision evaluation, and self-improvement triggers.
Focuses on optimizing business intelligence and research outcomes.
"""

import logging
from typing import Dict, List, Optional, Any, Set, Tuple
import json
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass
from enum import Enum
import numpy as np
from collections import deque, defaultdict

logger = logging.getLogger(__name__)

class PerformanceMetric(Enum):
    """Types of performance metrics to monitor."""
    API_LATENCY = "api_latency"
    RESEARCH_ACCURACY = "research_accuracy"
    ALERT_RELEVANCE = "alert_relevance"
    CONVERSATION_QUALITY = "conversation_quality"
    PARTNERSHIP_MATCH = "partnership_match"

@dataclass
class MetricSnapshot:
    """Data structure for performance metric snapshots."""
    metric_type: PerformanceMetric
    value: float
    timestamp: datetime
    context: Dict[str, Any]
    source_module: str

@dataclass
class DecisionOutcome:
    """Data structure for tracking decision outcomes."""
    decision_id: str
    decision_type: str
    context: Dict[str, Any]
    timestamp: datetime
    outcome: Dict[str, Any]
    feedback: Dict[str, float]

@dataclass
class ImprovementAction:
    """Data structure for self-improvement actions."""
    action_type: str
    target_module: str
    parameters: Dict[str, Any]
    reason: str
    priority: int
    timestamp: datetime

class MetaAgent:
    """Meta-Agent for monitoring and improving ATENA-AI's performance."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Meta-Agent."""
        self.config = config
        self.performance_history = defaultdict(list)
        self.decision_history: List[DecisionOutcome] = []
        self.improvement_queue: List[ImprovementAction] = []
        self.thresholds = config['thresholds']
        self.analysis_interval = config['analysis_interval']
        self.last_analysis = datetime.now()
    
    async def start_monitoring(self):
        """Start the performance monitoring process."""
        while True:
            try:
                await self._analyze_performance()
                await asyncio.sleep(self.analysis_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)
    
    def record_metric(self, snapshot: MetricSnapshot) -> None:
        """Record a performance metric and check for immediate action if needed."""
        self.performance_history[snapshot.metric_type].append(snapshot)
        
        # Check if metric is significantly worse than threshold
        threshold = self.thresholds[snapshot.metric_type.value]
        if snapshot.metric_type in [PerformanceMetric.API_LATENCY]:
            # For latency, higher is worse
            if snapshot.value > threshold * 1.5:  # 50% worse than threshold
                self._create_emergency_action(snapshot)
        else:
            # For accuracy/quality metrics, lower is worse
            if snapshot.value < threshold * 0.7:  # 30% worse than threshold
                self._create_emergency_action(snapshot)
    
    def record_decision(self, decision: DecisionOutcome) -> None:
        """Record a decision outcome for analysis."""
        self.decision_history.append(decision)
    
    async def _analyze_performance(self) -> None:
        """Analyze performance metrics and create improvement actions."""
        current_time = datetime.now()
        
        # Analyze each metric type
        for metric_type in PerformanceMetric:
            metrics = self.performance_history[metric_type]
            if not metrics:
                continue
                
            # Get recent metrics
            recent_metrics = [m for m in metrics 
                            if (current_time - m.timestamp).total_seconds() < self.analysis_interval]
            
            if not recent_metrics:
                continue
                
            # Calculate average performance
            avg_value = np.mean([m.value for m in recent_metrics])
            threshold = self.thresholds[metric_type.value]
            
            # Check if performance is below threshold
            if ((metric_type in [PerformanceMetric.API_LATENCY] and avg_value > threshold) or
                (metric_type not in [PerformanceMetric.API_LATENCY] and avg_value < threshold)):
                
                # Create improvement action
                action = ImprovementAction(
                    action_type='optimize_performance',
                    target_module=recent_metrics[0].source_module,
                    parameters={'metric': metric_type.value, 'current_value': avg_value},
                    reason=f'Sustained poor performance in {metric_type.value}',
                    priority=3,  # Medium priority
                    timestamp=current_time
                )
                self.improvement_queue.append(action)
    
    def _create_emergency_action(self, snapshot: MetricSnapshot) -> None:
        """Create an emergency improvement action for critical performance issues."""
        action = ImprovementAction(
            action_type='emergency_optimization',
            target_module=snapshot.source_module,
            parameters={'metric': snapshot.metric_type.value, 'value': snapshot.value},
            reason=f'Critical performance degradation in {snapshot.metric_type.value}',
            priority=5,  # Highest priority
            timestamp=datetime.now()
        )
        self.improvement_queue.append(action)
    
    async def get_pending_improvements(self) -> List[ImprovementAction]:
        """Get and clear the queue of pending improvements."""
        improvements = sorted(self.improvement_queue, key=lambda x: (-x.priority, x.timestamp))
        self.improvement_queue = []
        return improvements
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate the trend in a series of values."""
        if not values or len(values) < 2:
            return 0.0
        x = np.arange(len(values))
        y = np.array(values)
        slope, _ = np.polyfit(x, y, 1)
        return slope
    
    def _extract_common_factors(self, contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract common factors from a list of contexts."""
        if not contexts:
            return {}
            
        result = {}
        # Get all keys from first context
        keys = set(contexts[0].keys())
        
        for key in keys:
            values = [ctx[key] for ctx in contexts if key in ctx]
            if not values:
                continue
                
            # If all values are the same, store the common value
            if all(v == values[0] for v in values):
                result[key] = values[0]
            # If values are numeric, store statistics
            elif all(isinstance(v, (int, float)) for v in values):
                result[key] = {
                    'min': min(values),
                    'max': max(values),
                    'mean': np.mean(values)
                }
                
        return result 