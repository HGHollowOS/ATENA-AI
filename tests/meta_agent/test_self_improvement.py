"""
Tests for the self-improvement functionality of the meta-agent.
"""

import pytest
from datetime import datetime
from src.meta_agent.meta_agent import (
    MetaAgent,
    SystemMetrics,
    DecisionOutcome,
    ImprovementAction,
    MetricType
)

@pytest.fixture
def meta_agent():
    """Create a MetaAgent instance for testing."""
    return MetaAgent()

@pytest.fixture
def system_metrics():
    """Create test system metrics."""
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
def decision_outcome():
    """Create test decision outcome."""
    return DecisionOutcome(
        decision_id="test_decision",
        action_type="test_action",
        impact=0.8
    )

@pytest.fixture
def improvement_action():
    """Create test improvement action."""
    return ImprovementAction(
        action_id="test_action",
        metric_type=MetricType.RESPONSE_TIME,
        action_type="optimization",
        target_metric=MetricType.RESPONSE_TIME,
        parameters={"threshold": 0.5},
        timestamp=datetime.now()
    )

@pytest.mark.asyncio
async def test_determine_optimization_type(meta_agent, system_metrics):
    """Test determining optimization type based on metrics."""
    await meta_agent.record_metrics(system_metrics)
    optimization_type = await meta_agent.determine_optimization_type()
    assert isinstance(optimization_type, str)

@pytest.mark.asyncio
async def test_generate_optimization(meta_agent, system_metrics):
    """Test generating optimization plan."""
    await meta_agent.record_metrics(system_metrics)
    optimization = await meta_agent.generate_optimization(MetricType.RESPONSE_TIME)
    assert isinstance(optimization, dict)

@pytest.mark.asyncio
async def test_apply_optimization(meta_agent, improvement_action):
    """Test applying optimization action."""
    await meta_agent.record_improvement(improvement_action)
    assert len(meta_agent.improvement_history) == 1

@pytest.mark.asyncio
async def test_monitor_optimization_impact(meta_agent, improvement_action):
    """Test monitoring optimization impact."""
    impact = await meta_agent.monitor_optimization_impact(improvement_action)
    assert isinstance(impact, dict)
    # The impact dictionary might be empty if there's not enough history
    assert isinstance(impact, dict)

@pytest.mark.asyncio
async def test_should_rollback(meta_agent, system_metrics):
    """Test determining if optimization should be rolled back."""
    await meta_agent.record_metrics(system_metrics)
    should_rollback = await meta_agent.should_rollback(MetricType.RESPONSE_TIME)
    assert isinstance(should_rollback, bool)

@pytest.mark.asyncio
async def test_rollback_optimization(meta_agent, improvement_action):
    """Test rolling back optimization."""
    await meta_agent.record_improvement(improvement_action)
    success = await meta_agent.rollback_optimization(improvement_action)
    assert isinstance(success, bool)

@pytest.mark.asyncio
async def test_get_optimization_history(meta_agent, improvement_action):
    """Test retrieving optimization history."""
    await meta_agent.record_improvement(improvement_action)
    history = await meta_agent.get_optimization_history()
    assert isinstance(history, list)
    assert len(history) == 1 