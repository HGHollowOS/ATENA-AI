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

@dataclass
class SystemMetrics:
    """System performance metrics."""
    cpu_usage: float
    memory_usage: float
    api_latency: float
    error_rate: float
    request_count: int
    timestamp: datetime

class MetaAgent:
    """Meta-Agent for monitoring and improving ATENA-AI's performance."""
    
    def __init__(self):
        self.metrics_history: List[SystemMetrics] = []
        self.improvement_actions: List[Dict[str, Any]] = []
        self.performance_thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'api_latency': 2000,
            'error_rate': 0.05
        }
        
    def record_metrics(self, metrics: SystemMetrics) -> None:
        """Record system metrics."""
        self.metrics_history.append(metrics)
        self._analyze_performance(metrics)
        
    def _analyze_performance(self, metrics: SystemMetrics) -> None:
        """Analyze current performance metrics."""
        issues = []
        
        if metrics.cpu_usage > self.performance_thresholds['cpu_usage']:
            issues.append(f"High CPU usage: {metrics.cpu_usage}%")
            
        if metrics.memory_usage > self.performance_thresholds['memory_usage']:
            issues.append(f"High memory usage: {metrics.memory_usage}%")
            
        if metrics.api_latency > self.performance_thresholds['api_latency']:
            issues.append(f"High API latency: {metrics.api_latency}ms")
            
        if metrics.error_rate > self.performance_thresholds['error_rate']:
            issues.append(f"High error rate: {metrics.error_rate * 100}%")

        if issues:
            self._trigger_optimization(issues)
        
    def _trigger_optimization(self, issues: List[str]) -> None:
        """Trigger system optimization based on identified issues."""
        for issue in issues:
            print(f"[MetaAgent] Performance issue detected: {issue}")
            # Implement optimization logic here

    def get_performance_report(self) -> Dict:
        """Generate a performance report."""
        if not self.metrics_history:
            return {"status": "No metrics recorded"}

        latest = self.metrics_history[-1]
        return {
            "current_metrics": {
                "cpu_usage": f"{latest.cpu_usage}%",
                "memory_usage": f"{latest.memory_usage}%",
                "api_latency": f"{latest.api_latency}ms",
                "error_rate": f"{latest.error_rate * 100}%",
                "request_count": latest.request_count
            },
            "timestamp": latest.timestamp.isoformat(),
            "status": "healthy" if not self._has_issues(latest) else "issues_detected"
        }

    def _has_issues(self, metrics: SystemMetrics) -> bool:
        """Check if current metrics indicate any issues."""
        return any([
            metrics.cpu_usage > self.performance_thresholds['cpu_usage'],
            metrics.memory_usage > self.performance_thresholds['memory_usage'],
            metrics.api_latency > self.performance_thresholds['api_latency'],
            metrics.error_rate > self.performance_thresholds['error_rate']
        ])
        
    async def analyze_performance(self) -> Dict[str, Any]:
        """Analyze performance metrics and identify trends."""
        if not self.metrics_history:
            return {}
            
        analysis = {}
        metrics = ["response_time", "token_usage", "success_rate"]
        
        for metric in metrics:
            values = [m[metric] for m in self.metrics_history if metric in m]
            if values:
                analysis[metric] = {
                    "current": values[-1],
                    "mean": sum(values) / len(values),
                    "trend": self._calculate_trend(values)
                }
                
        return analysis
        
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a series of values."""
        if len(values) < 2:
            return "stable"
            
        recent = values[-3:] if len(values) >= 3 else values
        slope = (recent[-1] - recent[0]) / len(recent)
        
        if abs(slope) < 0.05:
            return "stable"
        return "increasing" if slope > 0 else "decreasing"
        
    async def trigger_improvement(self, analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Trigger improvement action based on performance analysis."""
        for metric, data in analysis.items():
            if "threshold" in data and data["current"] > data["threshold"]:
                action = {
                    "action": "optimize",
                    "target": metric,
                    "current_value": data["current"],
                    "threshold": data["threshold"],
                    "timestamp": datetime.now()
                }
                self.improvement_actions.append(action)
                return action
        return None

    def record_metric(self, snapshot: MetricSnapshot) -> None:
        """Record a performance metric and check for immediate action if needed."""
        self.metrics_history.append({
            **snapshot.__dict__,
            "timestamp": snapshot.timestamp
        })
        
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
            metrics = [m for m in self.metrics_history if m['metric_type'] == metric_type.value]
            if not metrics:
                continue
                
            # Get recent metrics
            recent_metrics = [m for m in metrics 
                            if (current_time - m['timestamp']).total_seconds() < self.analysis_interval]
            
            if not recent_metrics:
                continue
                
            # Calculate average performance
            avg_value = np.mean([m['value'] for m in recent_metrics])
            threshold = self.thresholds[metric_type.value]
            
            # Check if performance is below threshold
            if ((metric_type in [PerformanceMetric.API_LATENCY] and avg_value > threshold) or
                (metric_type not in [PerformanceMetric.API_LATENCY] and avg_value < threshold)):
                
                # Create improvement action
                action = ImprovementAction(
                    action_type='optimize_performance',
                    target_module=recent_metrics[0]['source_module'],
                    parameters={'metric': metric_type.value, 'current_value': avg_value},
                    reason=f'Sustained poor performance in {metric_type.value}',
                    priority=3,  # Medium priority
                    timestamp=current_time
                )
                self.improvement_actions.append({
                    **action.__dict__,
                    "timestamp": action.timestamp
                })
    
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
        self.improvement_actions.append({
            **action.__dict__,
            "timestamp": action.timestamp
        })
    
    async def get_pending_improvements(self) -> List[ImprovementAction]:
        """Get and clear the queue of pending improvements."""
        improvements = sorted(self.improvement_actions, key=lambda x: (-x['priority'], x['timestamp']))
        self.improvement_actions = []
        return [ImprovementAction(**action) for action in improvements]
    
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