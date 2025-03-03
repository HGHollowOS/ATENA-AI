"""
Tests for the MetaAgent component.

This module contains tests to verify the functionality of the MetaAgent,
including metrics gathering, performance evaluation, and self-improvement.
"""

import pytest
from datetime import datetime
from src.meta_agent.meta_agent import MetaAgent, SystemMetrics

@pytest.fixture
def meta_agent():
    """Create a MetaAgent instance for testing."""
    return MetaAgent()

@pytest.mark.asyncio
async def test_meta_agent_initialization(meta_agent):
    """Test MetaAgent initialization."""
    assert meta_agent is not None
    assert meta_agent.improvement_threshold == 0.7
    assert len(meta_agent.metrics_history) == 0

@pytest.mark.asyncio
async def test_gather_metrics(meta_agent):
    """Test metrics gathering functionality."""
    metrics = await meta_agent.gather_metrics()
    
    assert isinstance(metrics, SystemMetrics)
    assert isinstance(metrics.response_time, float)
    assert isinstance(metrics.accuracy, float)
    assert isinstance(metrics.user_satisfaction, float)
    assert isinstance(metrics.error_rate, float)
    assert isinstance(metrics.resource_usage, dict)
    assert isinstance(metrics.timestamp, datetime)
    
    assert len(meta_agent.metrics_history) == 1
    assert meta_agent.metrics_history[0] == metrics

@pytest.mark.asyncio
async def test_evaluate_performance(meta_agent):
    """Test performance evaluation functionality."""
    # Gather some metrics first
    await meta_agent.gather_metrics()
    await meta_agent.gather_metrics()
    
    evaluation = await meta_agent.evaluate_performance()
    
    assert isinstance(evaluation, dict)
    assert "overall_score" in evaluation
    assert "trends" in evaluation
    assert "decision_quality" in evaluation
    
    assert isinstance(evaluation["overall_score"], float)
    assert isinstance(evaluation["trends"], dict)
    assert isinstance(evaluation["decision_quality"], float)

@pytest.mark.asyncio
async def test_trigger_improvement(meta_agent):
    """Test self-improvement triggering functionality."""
    # Set up some metrics that would trigger improvement
    metrics = SystemMetrics(
        response_time=1.0,
        accuracy=0.5,
        user_satisfaction=0.6,
        error_rate=0.3,
        resource_usage={"cpu": 0.8, "memory": 0.7},
        timestamp=datetime.now()
    )
    meta_agent.metrics_history.append(metrics)
    
    success = await meta_agent.trigger_improvement()
    assert isinstance(success, bool)

@pytest.mark.asyncio
async def test_measure_response_time(meta_agent):
    """Test response time measurement."""
    response_time = await meta_agent._measure_response_time()
    assert isinstance(response_time, float)
    assert response_time >= 0

@pytest.mark.asyncio
async def test_calculate_accuracy(meta_agent):
    """Test accuracy calculation."""
    accuracy = await meta_agent._calculate_accuracy()
    assert isinstance(accuracy, float)
    assert 0 <= accuracy <= 1

@pytest.mark.asyncio
async def test_get_user_satisfaction(meta_agent):
    """Test user satisfaction calculation."""
    satisfaction = await meta_agent._get_user_satisfaction()
    assert isinstance(satisfaction, float)
    assert 0 <= satisfaction <= 1

@pytest.mark.asyncio
async def test_calculate_error_rate(meta_agent):
    """Test error rate calculation."""
    error_rate = await meta_agent._calculate_error_rate()
    assert isinstance(error_rate, float)
    assert 0 <= error_rate <= 1

@pytest.mark.asyncio
async def test_get_resource_usage(meta_agent):
    """Test resource usage measurement."""
    usage = await meta_agent._get_resource_usage()
    assert isinstance(usage, dict)
    assert all(isinstance(v, float) for v in usage.values())
    assert all(0 <= v <= 1 for v in usage.values())

def test_analyze_trends(meta_agent):
    """Test trend analysis functionality."""
    # Add some test metrics
    for i in range(5):
        metrics = SystemMetrics(
            response_time=1.0 + i * 0.1,
            accuracy=0.5 + i * 0.1,
            user_satisfaction=0.6 + i * 0.1,
            error_rate=0.3 - i * 0.05,
            resource_usage={"cpu": 0.8, "memory": 0.7},
            timestamp=datetime.now()
        )
        meta_agent.metrics_history.append(metrics)
    
    trends = meta_agent._analyze_trends(meta_agent.metrics_history)
    assert isinstance(trends, dict)
    assert all(isinstance(v, float) for v in trends.values())

@pytest.mark.asyncio
async def test_evaluate_decisions(meta_agent):
    """Test decision evaluation functionality."""
    decisions = await meta_agent._evaluate_decisions()
    assert isinstance(decisions, float)
    assert 0 <= decisions <= 1

def test_calculate_performance_score(meta_agent):
    """Test performance score calculation."""
    trends = {"response_time": 0.8, "accuracy": 0.7}
    decisions = 0.75
    
    score = meta_agent._calculate_performance_score(trends, decisions)
    assert isinstance(score, float)
    assert 0 <= score <= 1

def test_identify_improvement_areas(meta_agent):
    """Test improvement area identification."""
    evaluation = {
        "overall_score": 0.6,
        "trends": {"response_time": 0.8, "accuracy": 0.7},
        "decision_quality": 0.75
    }
    
    areas = meta_agent._identify_improvement_areas(evaluation)
    assert isinstance(areas, list)
    assert all(isinstance(area, str) for area in areas)

@pytest.mark.asyncio
async def test_generate_improvement_plan(meta_agent):
    """Test improvement plan generation."""
    areas = ["response_time", "accuracy"]
    
    plan = await meta_agent._generate_improvement_plan(areas)
    assert isinstance(plan, dict)
    assert all(isinstance(v, str) for v in plan.values())

@pytest.mark.asyncio
async def test_execute_improvements(meta_agent):
    """Test improvement execution."""
    plan = {
        "response_time": "optimize processing",
        "accuracy": "update model"
    }
    
    success = await meta_agent._execute_improvements(plan)
    assert isinstance(success, bool) 