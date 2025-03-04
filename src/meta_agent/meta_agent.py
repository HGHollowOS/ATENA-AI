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
from collections import deque

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
    outcome: Optional[Dict[str, Any]] = None
    feedback: Optional[Dict[str, Any]] = None

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
        self.performance_history: Dict[PerformanceMetric, deque] = {
            metric: deque(maxlen=1000)
            for metric in PerformanceMetric
        }
        self.decision_history: List[DecisionOutcome] = []
        self.improvement_queue: List[ImprovementAction] = []
        self.analysis_interval = 300  # 5 minutes
        self.last_analysis = datetime.now()
        
        # Performance thresholds
        self.thresholds = {
            PerformanceMetric.API_LATENCY: 2.0,  # seconds
            PerformanceMetric.RESEARCH_ACCURACY: 0.8,  # 80%
            PerformanceMetric.ALERT_RELEVANCE: 0.7,  # 70%
            PerformanceMetric.CONVERSATION_QUALITY: 0.75,  # 75%
            PerformanceMetric.PARTNERSHIP_MATCH: 0.8,  # 80%
        }
    
    async def start_monitoring(self):
        """Start the performance monitoring process."""
        while True:
            try:
                await self._analyze_performance()
                await asyncio.sleep(self.analysis_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)
    
    def record_metric(self, snapshot: MetricSnapshot):
        """Record a performance metric snapshot."""
        try:
            self.performance_history[snapshot.metric_type].append(snapshot)
            
            # Check for immediate action if metric is significantly below threshold
            threshold = self.thresholds[snapshot.metric_type]
            if snapshot.value < threshold * 0.7:  # 30% below threshold
                self._trigger_immediate_action(snapshot)
            
        except Exception as e:
            logger.error(f"Error recording metric: {e}")
    
    def record_decision(self, decision: DecisionOutcome):
        """Record a decision outcome for analysis."""
        try:
            self.decision_history.append(decision)
            
            # Analyze recent similar decisions
            similar_decisions = [
                d for d in self.decision_history[-100:]
                if d.decision_type == decision.decision_type
            ]
            
            if len(similar_decisions) >= 10:
                self._analyze_decision_pattern(similar_decisions)
            
        except Exception as e:
            logger.error(f"Error recording decision: {e}")
    
    async def _analyze_performance(self):
        """Analyze performance metrics and trigger improvements."""
        try:
            current_time = datetime.now()
            
            # Only analyze if enough time has passed
            if (current_time - self.last_analysis).seconds < self.analysis_interval:
                return
            
            for metric_type in PerformanceMetric:
                metrics = list(self.performance_history[metric_type])
                if not metrics:
                    continue
                
                # Calculate key statistics
                values = [m.value for m in metrics]
                avg_value = np.mean(values)
                trend = self._calculate_trend(values)
                
                # Check against threshold
                threshold = self.thresholds[metric_type]
                if avg_value < threshold or trend < -0.1:  # Negative trend
                    self._create_improvement_action(
                        metric_type,
                        avg_value,
                        trend,
                        [m.context for m in metrics]
                    )
            
            self.last_analysis = current_time
            
        except Exception as e:
            logger.error(f"Error analyzing performance: {e}")
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate the trend in a series of values."""
        try:
            if len(values) < 2:
                return 0.0
            
            # Use simple linear regression
            x = np.arange(len(values))
            y = np.array(values)
            
            slope = np.polyfit(x, y, 1)[0]
            return slope
            
        except Exception as e:
            logger.error(f"Error calculating trend: {e}")
            return 0.0
    
    def _analyze_decision_pattern(self, decisions: List[DecisionOutcome]):
        """Analyze patterns in similar decisions."""
        try:
            # Group by outcome success
            successful = [d for d in decisions if d.outcome and d.outcome.get('success', False)]
            success_rate = len(successful) / len(decisions)
            
            # Analyze context patterns in successful decisions
            if successful:
                common_factors = self._extract_common_factors(
                    [d.context for d in successful]
                )
                
                if common_factors:
                    self._create_improvement_action(
                        'decision_pattern',
                        success_rate,
                        0.0,  # No trend for patterns
                        {'common_factors': common_factors}
                    )
            
        except Exception as e:
            logger.error(f"Error analyzing decision pattern: {e}")
    
    def _extract_common_factors(self, contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract common factors from successful decision contexts."""
        try:
            common_factors = {}
            
            # Find common keys first
            common_keys = set.intersection(*[set(ctx.keys()) for ctx in contexts])
            
            for key in common_keys:
                values = [ctx[key] for ctx in contexts]
                
                # For numeric values, find ranges
                if all(isinstance(v, (int, float)) for v in values):
                    common_factors[key] = {
                        'min': min(values),
                        'max': max(values),
                        'mean': sum(values) / len(values)
                    }
                # For strings/enums, find most common
                elif all(isinstance(v, str) for v in values):
                    from collections import Counter
                    counter = Counter(values)
                    most_common = counter.most_common(1)[0]
                    if most_common[1] >= len(values) * 0.7:  # 70% threshold
                        common_factors[key] = most_common[0]
            
            return common_factors
            
        except Exception as e:
            logger.error(f"Error extracting common factors: {e}")
            return {}
    
    def _create_improvement_action(
        self,
        source_type: str,
        current_value: float,
        trend: float,
        context: Dict[str, Any]
    ):
        """Create an improvement action based on analysis."""
        try:
            if source_type == 'decision_pattern':
                action = ImprovementAction(
                    action_type='update_decision_weights',
                    target_module='business_intelligence',
                    parameters={
                        'success_patterns': context['common_factors'],
                        'current_success_rate': current_value
                    },
                    reason=f"Identified successful decision patterns with {current_value:.1%} success rate",
                    priority=3,
                    timestamp=datetime.now()
                )
            else:
                metric_type = PerformanceMetric(source_type)
                threshold = self.thresholds[metric_type]
                
                action = ImprovementAction(
                    action_type='optimize_performance',
                    target_module=self._get_target_module(metric_type),
                    parameters={
                        'metric': metric_type.value,
                        'current_value': current_value,
                        'target_value': threshold,
                        'trend': trend
                    },
                    reason=f"Performance below threshold: {current_value:.2f} vs {threshold:.2f}",
                    priority=4 if current_value < threshold * 0.7 else 2,
                    timestamp=datetime.now()
                )
            
            self.improvement_queue.append(action)
            
        except Exception as e:
            logger.error(f"Error creating improvement action: {e}")
    
    def _get_target_module(self, metric_type: PerformanceMetric) -> str:
        """Map metric types to target modules."""
        mapping = {
            PerformanceMetric.API_LATENCY: 'api_client',
            PerformanceMetric.RESEARCH_ACCURACY: 'business_intelligence',
            PerformanceMetric.ALERT_RELEVANCE: 'business_intelligence',
            PerformanceMetric.CONVERSATION_QUALITY: 'dialogue_manager',
            PerformanceMetric.PARTNERSHIP_MATCH: 'business_intelligence'
        }
        return mapping.get(metric_type, 'unknown')
    
    def _trigger_immediate_action(self, snapshot: MetricSnapshot):
        """Trigger immediate action for severely degraded performance."""
        try:
            action = ImprovementAction(
                action_type='emergency_optimization',
                target_module=self._get_target_module(snapshot.metric_type),
                parameters={
                    'metric': snapshot.metric_type.value,
                    'current_value': snapshot.value,
                    'threshold': self.thresholds[snapshot.metric_type],
                    'context': snapshot.context
                },
                reason=f"Severe performance degradation: {snapshot.value:.2f}",
                priority=5,  # Highest priority
                timestamp=datetime.now()
            )
            
            # Insert at the beginning of the queue
            self.improvement_queue.insert(0, action)
            
            logger.warning(
                f"Triggered immediate action for {snapshot.metric_type.value}: "
                f"value={snapshot.value:.2f}, threshold={self.thresholds[snapshot.metric_type]:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Error triggering immediate action: {e}")
    
    async def get_pending_improvements(self) -> List[ImprovementAction]:
        """Get pending improvement actions."""
        try:
            # Sort by priority (highest first) and timestamp (newest first)
            sorted_actions = sorted(
                self.improvement_queue,
                key=lambda x: (-x.priority, -x.timestamp.timestamp())
            )
            
            # Clear the queue
            self.improvement_queue = []
            
            return sorted_actions
            
        except Exception as e:
            logger.error(f"Error getting pending improvements: {e}")
            return [] 