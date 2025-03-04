import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from src.meta_agent.meta_agent import (
    MetaAgent,
    PerformanceMetric,
    MetricSnapshot,
    DecisionOutcome,
    ImprovementAction
)

@pytest.fixture
def meta_agent():
    """Create a MetaAgent instance for testing."""
    config = {
        'analysis_interval': 60,  # 1 minute for testing
        'thresholds': {
            'api_latency': 2.0,
            'research_accuracy': 0.8,
            'alert_relevance': 0.7,
            'conversation_quality': 0.75,
            'partnership_match': 0.8,
        }
    }
    return MetaAgent(config)

@pytest.mark.asyncio
async def test_record_metrics(meta_agent):
    metrics = {
        "response_time": 1.5,
        "token_usage": 1000,
        "success_rate": 0.95
    }
    
    await meta_agent.record_metrics(metrics)
    assert len(meta_agent.metrics_history) == 1
    assert meta_agent.metrics_history[0]["response_time"] == 1.5

@pytest.mark.asyncio
async def test_analyze_performance(meta_agent):
    # Add test metrics
    metrics_list = [
        {
            "response_time": 1.5,
            "token_usage": 1000,
            "success_rate": 0.95,
            "timestamp": datetime.now()
        },
        {
            "response_time": 1.8,
            "token_usage": 1200,
            "success_rate": 0.90,
            "timestamp": datetime.now()
        }
    ]
    
    meta_agent.metrics_history.extend(metrics_list)
    analysis = await meta_agent.analyze_performance()
    
    assert "response_time" in analysis
    assert "token_usage" in analysis
    assert "success_rate" in analysis

@pytest.mark.asyncio
async def test_trigger_improvement(meta_agent):
    analysis = {
        "response_time": {
            "trend": "increasing",
            "current": 2.0,
            "threshold": 1.5
        }
    }
    
    improvement = await meta_agent.trigger_improvement(analysis)
    assert improvement is not None
    assert "action" in improvement
    assert "target" in improvement

@pytest.mark.asyncio
async def test_record_metric(meta_agent):
    """Test recording performance metrics."""
    # Create test metric
    snapshot = MetricSnapshot(
        metric_type=PerformanceMetric.API_LATENCY,
        value=1.5,
        timestamp=datetime.now(),
        context={'endpoint': 'test_api'},
        source_module='api_client'
    )
    
    # Record metric
    meta_agent.record_metric(snapshot)
    
    # Verify metric was recorded
    assert len(meta_agent.performance_history[PerformanceMetric.API_LATENCY]) == 1
    recorded = meta_agent.performance_history[PerformanceMetric.API_LATENCY][0]
    assert recorded.value == 1.5
    assert recorded.source_module == 'api_client'

@pytest.mark.asyncio
async def test_record_poor_metric_triggers_action(meta_agent):
    """Test that recording a poor metric triggers immediate action."""
    # Create test metric with very poor performance
    snapshot = MetricSnapshot(
        metric_type=PerformanceMetric.API_LATENCY,
        value=5.0,  # Well above threshold
        timestamp=datetime.now(),
        context={'endpoint': 'test_api'},
        source_module='api_client'
    )
    
    # Record metric
    meta_agent.record_metric(snapshot)
    
    # Verify immediate action was triggered
    assert len(meta_agent.improvement_queue) == 1
    action = meta_agent.improvement_queue[0]
    assert action.priority == 5  # Highest priority
    assert action.action_type == 'emergency_optimization'
    assert action.target_module == 'api_client'

@pytest.mark.asyncio
async def test_record_decision(meta_agent):
    """Test recording and analyzing decision outcomes."""
    # Create test decision
    decision = DecisionOutcome(
        decision_id='test_1',
        decision_type='partnership_recommendation',
        context={'industry': 'tech', 'size': 'large'},
        timestamp=datetime.now(),
        outcome={'success': True},
        feedback={'relevance': 0.9}
    )
    
    # Record decision
    meta_agent.record_decision(decision)
    
    # Verify decision was recorded
    assert len(meta_agent.decision_history) == 1
    recorded = meta_agent.decision_history[0]
    assert recorded.decision_id == 'test_1'
    assert recorded.outcome['success'] is True

@pytest.mark.asyncio
async def test_calculate_trend(meta_agent):
    """Test trend calculation for performance metrics."""
    values = [1.0, 1.2, 1.4, 1.6, 1.8]  # Increasing trend
    trend = meta_agent._calculate_trend(values)
    assert trend > 0
    
    values = [1.8, 1.6, 1.4, 1.2, 1.0]  # Decreasing trend
    trend = meta_agent._calculate_trend(values)
    assert trend < 0

@pytest.mark.asyncio
async def test_get_pending_improvements(meta_agent):
    """Test retrieving and prioritizing pending improvements."""
    # Add multiple improvement actions
    actions = [
        ImprovementAction(
            action_type='optimize_performance',
            target_module='api_client',
            parameters={'metric': 'api_latency'},
            reason='Test improvement 1',
            priority=3,
            timestamp=datetime.now()
        ),
        ImprovementAction(
            action_type='emergency_optimization',
            target_module='business_intelligence',
            parameters={'metric': 'research_accuracy'},
            reason='Test improvement 2',
            priority=5,
            timestamp=datetime.now()
        )
    ]
    
    meta_agent.improvement_queue.extend(actions)
    
    # Get pending improvements
    pending = await meta_agent.get_pending_improvements()
    
    # Verify prioritization
    assert len(pending) == 2
    assert pending[0].priority == 5  # Highest priority first
    assert pending[1].priority == 3
    
    # Verify queue was cleared
    assert len(meta_agent.improvement_queue) == 0

@pytest.mark.asyncio
async def test_extract_common_factors(meta_agent):
    """Test extraction of common factors from decision contexts."""
    contexts = [
        {'industry': 'tech', 'size': 'large', 'score': 0.8},
        {'industry': 'tech', 'size': 'large', 'score': 0.9},
        {'industry': 'tech', 'size': 'large', 'score': 0.85}
    ]
    
    factors = meta_agent._extract_common_factors(contexts)
    
    assert 'industry' in factors
    assert factors['industry'] == 'tech'
    assert 'size' in factors
    assert factors['size'] == 'large'
    assert 'score' in factors
    assert factors['score'] == 0.85
    assert 'min' in factors['score']
    assert factors['score'] == 0.8
    assert 'max' in factors['score']
    assert 'mean' in factors['score'] 