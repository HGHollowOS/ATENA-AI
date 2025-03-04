"""
Tests for the meta-agent module.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
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
    """Create a MetaAgent instance for testing."""
    return MetaAgent()

@pytest.fixture
def system_metrics():
    """Create a SystemMetrics instance for testing."""
    return SystemMetrics(
        response_time=0.1,
        accuracy=0.95,
        error_rate=0.05,
        success_rate=0.95,
        latency=0.1,
        cpu_usage=30.0,
        memory_usage=50.0,
        throughput=100,
        user_satisfaction=0.8
    )

@pytest.fixture
def poor_system_metrics():
    """Create sample system metrics with poor performance."""
    return SystemMetrics(
        response_time=3.0,
        accuracy=0.7,
        error_rate=0.4,
        success_rate=0.6,
        latency=2.0,
        cpu_usage=80.0,
        memory_usage=90.0,
        throughput=50,
        user_satisfaction=0.5,
        timestamp=datetime.now()
    )

@pytest.fixture
def decision_outcome():
    """Create a DecisionOutcome instance for testing."""
    return DecisionOutcome(
        decision_id="test_decision",
        action_type="optimization",
        impact=0.8,
        success=True,
        metrics={"accuracy": 0.95},
        context={"environment": "test"}
    )

@pytest.fixture
def improvement_action():
    """Create an ImprovementAction instance for testing."""
    return ImprovementAction(
        action_id="test_action",
        metric_type=MetricType.ACCURACY,
        action_type="optimization",
        target_metric=MetricType.ACCURACY,
        parameters={"learning_rate": 0.01},
        changes={"accuracy": 0.05}
    )

@pytest.mark.asyncio
async def test_meta_agent_initialization():
    """Test MetaAgent initialization."""
    agent = MetaAgent()
    assert agent.improvement_threshold == 0.7
    assert agent.evaluation_window == 10
    assert agent.min_samples_for_evaluation == 5

@pytest.mark.asyncio
async def test_gather_metrics(meta_agent):
    """Test gathering system metrics."""
    metrics = await meta_agent.gather_metrics()
    assert isinstance(metrics, SystemMetrics)
    assert 0 <= metrics.response_time <= 1
    assert 0 <= metrics.accuracy <= 1
    assert 0 <= metrics.error_rate <= 1

@pytest.mark.asyncio
async def test_evaluate_performance(meta_agent, system_metrics):
    """Test performance evaluation."""
    await meta_agent.record_metrics(system_metrics)
    evaluation = await meta_agent.evaluate_performance()
    assert isinstance(evaluation, dict)
    assert "accuracy" in evaluation
    assert "error_rate" in evaluation
    assert "response_time" in evaluation

@pytest.mark.asyncio
async def test_trigger_improvement(meta_agent, system_metrics):
    """Test improvement triggering."""
    await meta_agent.record_metrics(system_metrics)
    stats = meta_agent._calculate_metric_stats(MetricType.ACCURACY)
    await meta_agent._trigger_improvement(MetricType.ACCURACY, stats)
    assert len(meta_agent.improvement_history) > 0

@pytest.mark.asyncio
async def test_record_metrics(meta_agent, system_metrics):
    """Test recording metrics."""
    await meta_agent.record_metrics(system_metrics)
    assert len(meta_agent.metrics_history) == 1
    assert len(meta_agent.performance_history) == 1

@pytest.mark.asyncio
async def test_record_decision(meta_agent, decision_outcome):
    """Test recording decision outcomes."""
    await meta_agent.record_decision(decision_outcome)
    assert len(meta_agent.decision_history) == 1

@pytest.mark.asyncio
async def test_record_improvement(meta_agent, improvement_action):
    """Test recording improvement actions."""
    await meta_agent.record_improvement(improvement_action)
    assert len(meta_agent.improvement_history) == 1

@pytest.mark.asyncio
async def test_evaluate_performance_triggers_improvement(meta_agent, poor_system_metrics):
    """Test that poor performance triggers improvement."""
    # Record multiple poor metrics to ensure evaluation
    # Add metrics that show a declining trend and are above the improvement threshold
    for i in range(meta_agent.min_samples_for_evaluation + 1):
        metrics = SystemMetrics(
            response_time=2.0 + i * 0.1,  # Increasing (worse) response time
            accuracy=0.9 - i * 0.02,      # Decreasing accuracy
            error_rate=0.2 + i * 0.02,    # Increasing error rate
            success_rate=0.8 - i * 0.02,  # Decreasing success rate
            latency=0.5 + i * 0.1,        # Increasing latency
            cpu_usage=80.0 + i * 1.0,     # Increasing CPU usage
            memory_usage=70.0 + i * 1.0,  # Increasing memory usage
            throughput=100 - i * 5,       # Decreasing throughput
            user_satisfaction=0.7 - i * 0.02,  # Decreasing satisfaction
            resource_usage={"cpu": 0.8, "memory": 0.7},
            timestamp=datetime.now()
        )
        await meta_agent.record_metrics(metrics)
    
    # Evaluate performance which should trigger improvement
    await meta_agent._evaluate_performance()
    
    # Verify that improvement was triggered
    assert len(meta_agent.improvement_history) > 0
    improvement = meta_agent.improvement_history[0]
    assert isinstance(improvement, ImprovementAction)
    assert improvement.action_type == "optimization"

@pytest.mark.asyncio
async def test_analyze_decision_impact(meta_agent, system_metrics):
    """Test analyzing decision impact."""
    # First record some metrics to avoid index error
    await meta_agent.record_metrics(system_metrics)
    
    negative_outcome = DecisionOutcome(
        decision_id="test_negative",
        action_type="optimization",
        impact=-0.2,
        success=False,
        metrics={"accuracy": 0.7},
        context={"environment": "test"}
    )
    await meta_agent.record_decision(negative_outcome)
    assert len(meta_agent.improvement_history) > 0

@pytest.mark.asyncio
async def test_get_performance_metrics(meta_agent, system_metrics):
    """Test retrieving performance metrics."""
    await meta_agent.record_metrics(system_metrics)
    metrics = meta_agent.get_performance_metrics()
    assert len(metrics) == 1
    assert isinstance(metrics[0], SystemMetrics)

@pytest.mark.asyncio
async def test_get_decision_history(meta_agent, decision_outcome):
    """Test retrieving decision history."""
    await meta_agent.record_decision(decision_outcome)
    decisions = meta_agent.get_decision_history()
    assert len(decisions) == 1
    assert isinstance(decisions[0], DecisionOutcome)

@pytest.mark.asyncio
async def test_get_improvement_history(meta_agent, improvement_action):
    """Test retrieving improvement history."""
    await meta_agent.record_improvement(improvement_action)
    improvements = meta_agent.get_improvement_history()
    assert len(improvements) == 1
    assert isinstance(improvements[0], ImprovementAction)

def test_metric_type_enum():
    """Test MetricType enum values."""
    assert MetricType.RESPONSE_TIME.value == "response_time"
    assert MetricType.ACCURACY.value == "accuracy"
    assert MetricType.ERROR_RATE.value == "error_rate"

def test_performance_metric_creation():
    """Test creating performance metrics."""
    metrics = SystemMetrics(
        response_time=0.1,
        accuracy=0.95,
        error_rate=0.05,
        success_rate=0.95,
        latency=0.1,
        cpu_usage=30.0,
        memory_usage=50.0,
        throughput=100,
        user_satisfaction=0.8
    )
    assert isinstance(metrics, SystemMetrics)
    assert metrics.response_time == 0.1
    assert metrics.accuracy == 0.95

@pytest.mark.asyncio
async def test_calculate_performance_score(meta_agent, system_metrics):
    """Test calculating performance score."""
    await meta_agent.record_metrics(system_metrics)
    metrics = meta_agent.get_performance_metrics()
    trends = await meta_agent.analyze_trends(metrics)
    decisions = meta_agent.get_decision_history()
    score = await meta_agent.calculate_performance_score(trends, decisions)
    assert isinstance(score, float)
    assert 0 <= score <= 1

@pytest.mark.asyncio
async def test_identify_improvement_areas(meta_agent, system_metrics):
    """Test identifying areas for improvement."""
    await meta_agent.record_metrics(system_metrics)
    areas = await meta_agent.identify_improvement_areas()
    assert isinstance(areas, list)

@pytest.mark.asyncio
async def test_generate_improvement_plan(meta_agent, system_metrics):
    """Test generating improvement plan."""
    await meta_agent.record_metrics(system_metrics)
    plan = await meta_agent.generate_improvement_plan()
    assert isinstance(plan, dict)

@pytest.mark.asyncio
async def test_execute_improvements(meta_agent, system_metrics):
    """Test executing improvements."""
    await meta_agent.record_metrics(system_metrics)
    plan = await meta_agent.generate_improvement_plan()
    result = await meta_agent.execute_improvements(plan)
    assert isinstance(result, bool) 