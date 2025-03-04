"""
Meta-agent module for monitoring and improving system performance.
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio
import psutil

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Types of metrics that can be monitored."""
    RESPONSE_TIME = "response_time"
    LATENCY = "latency"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    ACCURACY = "accuracy"
    SUCCESS_RATE = "success_rate"
    USER_SATISFACTION = "user_satisfaction"

@dataclass
class MetricSnapshot:
    """Snapshot of a performance metric."""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    type: MetricType
    value: float
    timestamp: datetime
    context: Optional[Dict] = None

@dataclass
class SystemMetrics:
    """Collection of system performance metrics."""
    response_time: float
    accuracy: float
    error_rate: float
    success_rate: float
    latency: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    throughput: float = 0.0
    user_satisfaction: float = 0.0
    resource_usage: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, float]:
        """Convert metrics to dictionary."""
        return {
            "response_time": self.response_time,
            "accuracy": self.accuracy,
            "error_rate": self.error_rate,
            "success_rate": self.success_rate,
            "latency": self.latency,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "throughput": self.throughput,
            "user_satisfaction": self.user_satisfaction,
            **self.resource_usage
        }

    def get_metric_value(self, metric_type: MetricType) -> float:
        """Get metric value by MetricType."""
        metric_map = {
            MetricType.RESPONSE_TIME: self.response_time,
            MetricType.ACCURACY: self.accuracy,
            MetricType.ERROR_RATE: self.error_rate,
            MetricType.SUCCESS_RATE: self.success_rate,
            MetricType.LATENCY: self.latency,
            MetricType.CPU_USAGE: self.cpu_usage,
            MetricType.MEMORY_USAGE: self.memory_usage,
            MetricType.THROUGHPUT: self.throughput,
            MetricType.USER_SATISFACTION: self.user_satisfaction
        }
        return metric_map[metric_type]

@dataclass
class DecisionOutcome:
    """Outcome of a business decision or action."""
    decision_id: str
    action_type: str
    impact: float
    success: bool
    metrics: Dict[str, float] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ImprovementAction:
    """Action taken to improve system performance."""
    action_id: str
    metric_type: MetricType
    action_type: str
    target_metric: MetricType
    parameters: Dict[str, Any]
    changes: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

class MetaAgent:
    """Meta-agent for monitoring and improving system performance."""
    
    def __init__(self, config: Optional[Dict[str, Union[float, int]]] = None):
        """Initialize the meta-agent with configuration."""
        self.config = config or {
            "improvement_threshold": 0.7,
            "monitoring_interval": 60,
            "decision_weight": 0.5
        }
        self.metrics_history: List[SystemMetrics] = []
        self.performance_history: List[SystemMetrics] = []
        self.decision_history: List[DecisionOutcome] = []
        self.improvement_history: List[ImprovementAction] = []
        self.improvement_threshold = self.config["improvement_threshold"]
        self.logger = logging.getLogger(__name__)
        self.evaluation_window = 10
        self.min_samples_for_evaluation = 5

    async def gather_metrics(self) -> SystemMetrics:
        """Gather current system metrics."""
        response_time = await self._measure_response_time()
        accuracy = await self._calculate_accuracy()
        error_rate = await self._calculate_error_rate()
        success_rate = 1.0 - error_rate
        resource_usage = await self._get_resource_usage()
        user_satisfaction = await self._get_user_satisfaction()
        
        metrics = SystemMetrics(
            response_time=response_time,
            accuracy=accuracy,
            error_rate=error_rate,
            success_rate=success_rate,
            latency=resource_usage.get("latency", 0.0),
            cpu_usage=resource_usage.get("cpu_usage", 0.0),
            memory_usage=resource_usage.get("memory_usage", 0.0),
            throughput=resource_usage.get("throughput", 0.0),
            user_satisfaction=user_satisfaction,
            resource_usage=resource_usage
        )
        
        await self.record_metrics(metrics)
        return metrics

    async def record_metrics(self, metrics: SystemMetrics) -> None:
        """Record system metrics."""
        self.metrics_history.append(metrics)
        self.performance_history.append(metrics)
        await self._evaluate_performance()

    async def record_decision(self, outcome: DecisionOutcome) -> None:
        """Record decision outcome."""
        self.decision_history.append(outcome)
        await self._analyze_decision_impact(outcome)

    async def record_improvement(self, action: ImprovementAction) -> None:
        """Record improvement action."""
        self.improvement_history.append(action)

    async def evaluate_performance(self) -> Dict[str, Any]:
        """Evaluate current performance metrics."""
        if not self.metrics_history:
            return {"status": "no_data"}

        recent_metrics = self.metrics_history[-self.evaluation_window:]
        analysis = {}
        total_score = 0.0
        metric_count = 0

        for metric_type in MetricType:
            values = [m.get_metric_value(metric_type) for m in recent_metrics]
            if values:
                mean_value = np.mean(values)
                analysis[metric_type.value] = {
                    "mean": mean_value,
                    "min": min(values),
                    "max": max(values),
                    "trend": (values[-1] - values[0]) / len(values) if len(values) > 1 else 0
                }
                total_score += mean_value
                metric_count += 1

        # Add overall score
        analysis["overall_score"] = total_score / metric_count if metric_count > 0 else 0.0
        analysis["trends"] = {k: v["trend"] for k, v in analysis.items() if k != "overall_score"}
        analysis["decision_quality"] = self._calculate_decision_quality()

        return analysis

    def _calculate_decision_quality(self) -> float:
        """Calculate the quality of recent decisions."""
        if not self.decision_history:
            return 0.0
        recent_decisions = self.decision_history[-self.evaluation_window:]
        return sum(d.impact for d in recent_decisions) / len(recent_decisions)

    async def _measure_response_time(self) -> float:
        """Measure system response time."""
        return 0.1  # Placeholder implementation

    async def _calculate_accuracy(self) -> float:
        """Calculate system accuracy."""
        return 0.95  # Placeholder implementation

    async def _calculate_error_rate(self) -> float:
        """Calculate system error rate."""
        return 0.05  # Placeholder implementation

    async def _get_resource_usage(self) -> Dict[str, float]:
        """Get system resource usage."""
        return {
            "cpu": psutil.cpu_percent() / 100,
            "memory": psutil.virtual_memory().percent / 100,
            "disk": psutil.disk_usage('/').percent / 100
        }

    async def _get_user_satisfaction(self) -> float:
        """Get user satisfaction score."""
        return 0.8  # Placeholder implementation

    async def _evaluate_performance(self) -> None:
        """Evaluate system performance and trigger improvements if needed."""
        if not self.metrics_history:
            return

        if len(self.metrics_history) < self.min_samples_for_evaluation:
            return

        for metric_type in MetricType:
            stats = self._calculate_metric_stats(metric_type)
            if stats["trend"] < 0 and stats["mean"] > self.improvement_threshold:
                await self._trigger_improvement(metric_type, stats)

    async def _analyze_decision_impact(self, outcome: DecisionOutcome) -> None:
        """Analyze impact of decisions on system performance."""
        if outcome.impact < 0:
            self.logger.warning(f"Negative impact detected for decision {outcome.decision_id}")
            await self._trigger_improvement(MetricType.ACCURACY, {"mean": 0.5, "std": 0.1})

    def _calculate_metric_stats(self, metric_type: MetricType) -> Dict[str, float]:
        """Calculate statistics for a specific metric."""
        recent_metrics = self.metrics_history[-self.evaluation_window:]
        values = [m.get_metric_value(metric_type) for m in recent_metrics]
        
        return {
            "mean": sum(values) / len(values),
            "trend": (values[-1] - values[0]) / len(values) if len(values) > 1 else 0,
            "variance": sum((x - (sum(values) / len(values))) ** 2 for x in values) / len(values)
        }

    async def _trigger_improvement(self, metric_type: MetricType, stats: Dict[str, float]) -> None:
        """Trigger improvement action based on metric performance."""
        current_value = self.metrics_history[-1].get_metric_value(metric_type)
        
        improvement_action = ImprovementAction(
            action_id=f"improve_{metric_type.value}_{datetime.now().timestamp()}",
            metric_type=metric_type,
            action_type="optimization",
            target_metric=metric_type,
            parameters={
                "current_value": current_value,
                "target_value": stats.get("mean", 0) + stats.get("std", 0),
                "threshold": self.config["improvement_threshold"]
            }
        )
        
        await self.record_improvement(improvement_action)

    async def analyze_trends(self, metrics: List[SystemMetrics]) -> Dict[str, float]:
        """Analyze trends in system metrics."""
        if not metrics or len(metrics) < 2:
            return {}

        trends = {}
        for metric_type in MetricType:
            values = [m.get_metric_value(metric_type) for m in metrics]
            trends[metric_type.value] = (values[-1] - values[0]) / len(values)
        
        return trends

    async def evaluate_decisions(self) -> Dict[str, float]:
        """Evaluate the impact of past decisions."""
        if not self.decision_history:
            return {}

        impacts = {}
        recent_decisions = self.decision_history[-self.evaluation_window:]
        for decision in recent_decisions:
            impacts[decision.decision_id] = decision.impact

        return impacts

    async def calculate_performance_score(self, trends: Dict[str, float], decisions: Dict[str, float]) -> float:
        """Calculate overall performance score."""
        if not trends or not decisions:
            return 0.0

        trend_score = sum(trends.values()) / len(trends)
        decision_score = sum(decisions.values()) / len(decisions)
        return (trend_score + decision_score) / 2

    async def identify_improvement_areas(self) -> List[Dict[str, Any]]:
        """Identify areas needing improvement."""
        areas = []
        if not self.metrics_history:
            return areas

        recent_metrics = self.metrics_history[-self.evaluation_window:]
        
        for metric_type in MetricType:
            values = [m.get_metric_value(metric_type) for m in recent_metrics]
            if values:
                mean_value = sum(values) / len(values)
                if mean_value > self.improvement_threshold:
                    areas.append({
                        "metric": metric_type,
                        "current_value": mean_value,
                        "target": self.improvement_threshold
                    })
        
        return areas

    async def generate_improvement_plan(self, areas: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generate improvement plan based on current metrics."""
        if not areas:
            areas = await self.identify_improvement_areas()

        if not areas:
            return {}

        area = areas[0]  # Take the first area for improvement
        return {
            "target_metric": area["metric"].value,
            "action": "retrain_model",
            "parameters": {
                "learning_rate": 0.01,
                "current_value": area["current_value"],
                "target_value": area["target"]
            }
        }

    def get_performance_metrics(self) -> List[SystemMetrics]:
        """Get historical performance metrics."""
        return self.metrics_history

    def get_decision_history(self) -> List[DecisionOutcome]:
        """Get decision history."""
        return self.decision_history

    def get_improvement_history(self) -> List[ImprovementAction]:
        """Get improvement history."""
        return self.improvement_history

    def analyze_performance(self) -> Dict[str, Any]:
        """
        Analyze current performance metrics.
        
        Returns:
            Dictionary containing analysis results
        """
        if not self.metrics_history:
            return {"status": "no_data"}

        recent_metrics = self.metrics_history[-10:]
        analysis = {}

        for metric in recent_metrics:
            if metric.name not in analysis:
                analysis[metric.name] = []
            analysis[metric.name].append(metric.value)

        result = {}
        for name, values in analysis.items():
            result[name] = {
                "mean": np.mean(values),
                "min": min(values),
                "max": max(values)
            }

        return result

    async def _analyze_performance(self) -> None:
        """Internal method to analyze performance and trigger improvements."""
        analysis = self.analyze_performance()
        
        for metric_name, stats in analysis.items():
            if metric_name in self.performance_thresholds:
                threshold = self.performance_thresholds[metric_name]
                if stats["mean"] < threshold:
                    await self._trigger_improvement(MetricType(metric_name), stats)

    def calculate_trend(self, metric_name: str, window: int = 10) -> Optional[float]:
        """
        Calculate trend for a specific metric.
        
        Args:
            metric_name: Name of the metric
            window: Number of recent data points to consider
            
        Returns:
            Trend value or None if insufficient data
        """
        relevant_metrics = [
            m for m in self.metrics_history[-window:]
            if m.name == metric_name
        ]
        
        if len(relevant_metrics) < 2:
            return None
            
        values = [m.value for m in relevant_metrics]
        return np.polyfit(range(len(values)), values, 1)[0]

    def extract_common_factors(self, success_threshold: float = 0.8) -> Dict[str, Any]:
        """
        Extract common factors from successful decisions.
        
        Args:
            success_threshold: Minimum success rate to consider
            
        Returns:
            Dictionary of common factors
        """
        successful_decisions = [
            d for d in self.decision_history
            if d.success_rate >= success_threshold
        ]
        
        if not successful_decisions:
            return {}
            
        common_factors = {}
        for decision in successful_decisions:
            for key, value in decision.context.items():
                if key not in common_factors:
                    common_factors[key] = []
                common_factors[key].append(value)
        
        # Find most common values
        result = {}
        for key, values in common_factors.items():
            if len(values) >= len(successful_decisions) / 2:
                result[key] = max(set(values), key=values.count)
        
        return result

    async def determine_optimization_type(self) -> str:
        """Determine the type of optimization needed."""
        if not self.improvement_history:
            return "parameter_tuning"

        recent_actions = self.improvement_history[-self.evaluation_window:]
        
        # Check for emergency optimizations first
        if any(action.action_type == 'emergency_optimization' for action in recent_actions):
            return "parameter_tuning"

        # Check for model updates
        if any(action.action_type == 'update_decision_weights' for action in recent_actions):
            return "model_update"

        return "parameter_tuning"

    async def generate_optimization(self, metric_type: MetricType) -> Dict[str, Any]:
        """Generate optimization strategy for a specific metric."""
        if not self.metrics_history:
            return {}

        current_value = self.metrics_history[-1].get_metric_value(metric_type)
        stats = self._calculate_metric_stats(metric_type)

        return {
            "type": await self.determine_optimization_type(),
            "target_metric": metric_type.value,
            "parameters": {
                "current_value": current_value,
                "target_value": stats["mean"],
                "learning_rate": 0.01
            }
        }

    async def monitor_optimization_impact(self, action: ImprovementAction) -> Dict[str, float]:
        """Monitor the impact of an optimization action."""
        if not self.metrics_history:
            return {}

        # Get metrics before and after the improvement
        before_metrics = self.metrics_history[:-self.evaluation_window]
        after_metrics = self.metrics_history[-self.evaluation_window:]

        if not before_metrics or not after_metrics:
            return {}

        impact = {}
        metric_type = action.target_metric
        before_value = np.mean([m.get_metric_value(metric_type) for m in before_metrics])
        after_value = np.mean([m.get_metric_value(metric_type) for m in after_metrics])

        # Calculate relative improvement
        if before_value > 0:
            impact[metric_type.value] = (after_value - before_value) / before_value

        return impact

    async def should_rollback(self, metric_type: MetricType) -> bool:
        """Determine if optimization should be rolled back."""
        if not self.metrics_history:
            return False

        stats = self._calculate_metric_stats(metric_type)
        return stats["trend"] < 0 and stats["mean"] < self.improvement_threshold

    async def rollback_optimization(self, action: ImprovementAction) -> bool:
        """Rollback an optimization action."""
        if not action:
            return False

        # Record the rollback action
        rollback_action = ImprovementAction(
            action_id=f"rollback_{action.action_id}",
            metric_type=action.metric_type,
            action_type="rollback",
            target_metric=action.target_metric,
            parameters=action.parameters
        )
        await self.record_improvement(rollback_action)
        return True

    async def get_optimization_history(self) -> List[Dict[str, Any]]:
        """Get history of optimization actions and their impacts."""
        history = []
        for action in self.improvement_history:
            impact = await self.monitor_optimization_impact(action)
            history.append({
                "action": action,
                "impact": impact,
                "timestamp": datetime.now()
            })
        return history

    async def execute_improvements(self, plan: Dict[str, Any]) -> bool:
        """Execute the improvement plan."""
        if not plan:
            return False

        try:
            action = ImprovementAction(
                action_id=f"execute_{datetime.now().timestamp()}",
                metric_type=MetricType(plan["target_metric"]),
                action_type=plan["action"],
                target_metric=MetricType(plan["target_metric"]),
                parameters=plan["parameters"]
            )
            await self.record_improvement(action)
            return True
        except Exception as e:
            self.logger.error(f"Error executing improvements: {e}")
            return False 