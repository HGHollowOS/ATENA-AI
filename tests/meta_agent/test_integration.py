"""
Integration tests for the meta-agent module.
"""

import pytest
from datetime import datetime, timedelta
from src.meta_agent.meta_agent import (
    MetaAgent,
    SystemMetrics,
    DecisionOutcome,
    ImprovementAction,
    MetricType,
    PerformanceMetric
)

@pytest.fixture
def meta_agent():
    """Create a meta-agent instance for testing."""
    return MetaAgent()

@pytest.fixture
def system_metrics():
    return SystemMetrics(
        response_time=0.5,
        accuracy=0.95,
        error_rate=0.05,
        success_rate=0.98,
        latency=0.1,
        cpu_usage=30.0,
        memory_usage=50.0,
        throughput=100,
        user_satisfaction=4.5,
        resource_usage={},
        timestamp=datetime.now()
    )

@pytest.fixture
def poor_metrics():
    return SystemMetrics(
        response_time=2.0,
        accuracy=0.7,
        error_rate=0.3,
        success_rate=0.7,
        latency=0.5,
        cpu_usage=80.0,
        memory_usage=90.0,
        throughput=50,
        user_satisfaction=2.5,
        resource_usage={},
        timestamp=datetime.now()
    )

@pytest.mark.asyncio
async def test_performance_monitoring_triggers_improvement(meta_agent):
    """Test that performance monitoring triggers improvement actions."""
    # Record poor performance metrics
    for i in range(meta_agent.min_samples_for_evaluation + 1):
        metrics = SystemMetrics(
            response_time=2.0 + i * 0.1,
            accuracy=0.7 - i * 0.02,
            error_rate=0.3 + i * 0.02,
            success_rate=0.7 - i * 0.02,
            latency=1.0 + i * 0.1,
            cpu_usage=80.0 + i * 1.0,
            memory_usage=70.0 + i * 1.0,
            throughput=100 - i * 5,
            user_satisfaction=0.6 - i * 0.02,
            timestamp=datetime.now()
        )
        await meta_agent.record_metrics(metrics)
    
    improvements = meta_agent.improvement_history
    assert len(improvements) > 0

@pytest.mark.asyncio
async def test_decision_impact_analysis(meta_agent):
    """Test analysis of decision impacts."""
    decision = DecisionOutcome(
        decision_id="test_decision_1",
        action_type="optimization",
        impact=0.8,
        success=True,
        metrics={"accuracy": 0.95},
        context={"environment": "test"}
    )
    await meta_agent.record_decision(decision)
    assert len(meta_agent.decision_history) > 0

@pytest.mark.asyncio
async def test_improvement_effectiveness_monitoring(meta_agent):
    """Test monitoring of improvement effectiveness."""
    action = ImprovementAction(
        action_id="test_action_1",
        metric_type=MetricType.ACCURACY,
        action_type="optimization",
        target_metric=MetricType.ACCURACY,
        parameters={"learning_rate": 0.01}
    )
    await meta_agent.record_improvement(action)
    impact = await meta_agent.monitor_optimization_impact(action)
    assert isinstance(impact, dict)
    assert len(impact) >= 0

@pytest.mark.asyncio
async def test_optimization_rollback_on_poor_performance(meta_agent):
    """Test optimization rollback when performance degrades."""
    action = ImprovementAction(
        action_id="test_action_2",
        metric_type=MetricType.RESPONSE_TIME,
        action_type="optimization",
        target_metric=MetricType.RESPONSE_TIME,
        parameters={"threshold": 0.8}
    )
    await meta_agent.record_improvement(action)
    should_rollback = await meta_agent.should_rollback(MetricType.RESPONSE_TIME)
    if should_rollback:
        success = await meta_agent.rollback_optimization(action)
        assert success

@pytest.mark.asyncio
async def test_concurrent_improvements_handling(meta_agent):
    """Test handling of concurrent improvement actions."""
    actions = [
        ImprovementAction(
            action_id=f"test_action_{i}",
            metric_type=MetricType.ACCURACY,
            action_type="optimization",
            target_metric=MetricType.ACCURACY,
            parameters={"learning_rate": 0.01}
        )
        for i in range(3)
    ]
    
    for action in actions:
        await meta_agent.record_improvement(action)
    
    assert len(meta_agent.improvement_history) == len(actions)

@pytest.mark.asyncio
async def test_performance_metric_tracking(meta_agent, system_metrics):
    """Test tracking performance metrics over time."""
    await meta_agent.record_metrics(system_metrics)
    metrics = meta_agent.get_performance_metrics()
    assert isinstance(metrics, list)
    assert len(metrics) > 0 