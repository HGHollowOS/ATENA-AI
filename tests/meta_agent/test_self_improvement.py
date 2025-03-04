import pytest
import asyncio
from datetime import datetime, timedelta
from src.meta_agent.meta_agent import (
    MetaAgent,
    PerformanceMetric,
    MetricSnapshot,
    ImprovementAction
)
from src.meta_agent.self_improvement import (
    SelfImprovement,
    OptimizationType,
    OptimizationResult
)

@pytest.fixture
def meta_agent():
    """Create a MetaAgent instance for testing."""
    config = {
        'analysis_interval': 60,
        'thresholds': {
            'api_latency': 2.0,
            'research_accuracy': 0.8,
            'alert_relevance': 0.7,
            'conversation_quality': 0.75,
            'partnership_match': 0.8,
        }
    }
    return MetaAgent(config)

@pytest.fixture
def self_improvement(meta_agent):
    """Create a SelfImprovement instance for testing."""
    config = {
        'business_intelligence_cache_timeout': 3600,
        'business_intelligence_min_alert_priority': 3,
        'business_intelligence_monitoring_interval': 300,
        'business_intelligence_max_concurrent_requests': 10,
        'dialogue_manager_context_timeout': 600,
        'dialogue_manager_max_conversation_turns': 10,
        'dialogue_manager_confidence_threshold': 0.75,
        'api_client_request_timeout': 10,
        'api_client_retry_attempts': 3,
        'api_client_backoff_factor': 2.0
    }
    return SelfImprovement(config, meta_agent)

@pytest.mark.asyncio
async def test_determine_optimization_type(self_improvement):
    """Test optimization type determination."""
    # Test emergency optimization
    actions = [
        ImprovementAction(
            action_type='emergency_optimization',
            target_module='api_client',
            parameters={'metric': 'api_latency'},
            reason='Emergency test',
            priority=5,
            timestamp=datetime.now()
        )
    ]
    opt_type = self_improvement._determine_optimization_type(actions)
    assert opt_type == OptimizationType.PARAMETER_TUNING
    
    # Test model update
    actions = [
        ImprovementAction(
            action_type='update_decision_weights',
            target_module='business_intelligence',
            parameters={'patterns': {}},
            reason='Update test',
            priority=3,
            timestamp=datetime.now()
        )
    ]
    opt_type = self_improvement._determine_optimization_type(actions)
    assert opt_type == OptimizationType.MODEL_UPDATE

@pytest.mark.asyncio
async def test_generate_optimization(self_improvement):
    """Test optimization generation."""
    actions = [
        ImprovementAction(
            action_type='optimize_performance',
            target_module='business_intelligence',
            parameters={'metric': 'research_accuracy'},
            reason='Test optimization',
            priority=4,
            timestamp=datetime.now()
        )
    ]
    
    current_performance = {'research_accuracy': 0.7}
    
    optimization = await self_improvement._generate_optimization(
        'business_intelligence',
        OptimizationType.PARAMETER_TUNING,
        actions,
        current_performance
    )
    
    assert optimization is not None
    assert optimization['type'] == OptimizationType.PARAMETER_TUNING
    assert optimization['module'] == 'business_intelligence'
    assert len(optimization['parameters']) > 0
    assert len(optimization['rollback_data']) > 0

@pytest.mark.asyncio
async def test_apply_optimization(self_improvement):
    """Test applying optimization changes."""
    optimization = {
        'type': OptimizationType.PARAMETER_TUNING,
        'module': 'business_intelligence',
        'parameters': {
            'cache_timeout': 1800,
            'min_alert_priority': 2
        },
        'rollback_data': {
            'cache_timeout': 3600,
            'min_alert_priority': 3
        }
    }
    
    result = await self_improvement._apply_optimization(optimization)
    
    assert result.success
    assert result.optimization_type == OptimizationType.PARAMETER_TUNING
    assert result.target_module == 'business_intelligence'
    assert len(result.changes_made) == 2
    assert result.rollback_data is not None

@pytest.mark.asyncio
async def test_monitor_optimization_impact(self_improvement):
    """Test monitoring optimization impact."""
    optimization = OptimizationResult(
        optimization_type=OptimizationType.PARAMETER_TUNING,
        target_module='business_intelligence',
        changes_made={'cache_timeout': {'old': 3600, 'new': 1800}},
        performance_impact={},
        timestamp=datetime.now(),
        success=True,
        rollback_data={'cache_timeout': 3600}
    )
    
    baseline_performance = {
        'research_accuracy': 0.7,
        'alert_relevance': 0.6
    }
    
    # Add some performance metrics
    for metric_type in [PerformanceMetric.RESEARCH_ACCURACY, PerformanceMetric.ALERT_RELEVANCE]:
        snapshot = MetricSnapshot(
            metric_type=metric_type,
            value=0.8,  # Improved performance
            timestamp=datetime.now(),
            context={'test': True},
            source_module='business_intelligence'
        )
        self_improvement.meta_agent.record_metric(snapshot)
    
    impact = await self_improvement._monitor_optimization_impact(
        'business_intelligence',
        optimization,
        baseline_performance
    )
    
    assert len(impact) > 0
    assert all(v > 0 for v in impact.values())  # All metrics improved

@pytest.mark.asyncio
async def test_should_rollback(self_improvement):
    """Test rollback decision logic."""
    # Test case: good impact
    good_impact = {
        'research_accuracy': 0.1,  # 10% improvement
        'alert_relevance': 0.08    # 8% improvement
    }
    assert not self_improvement._should_rollback(good_impact)
    
    # Test case: poor impact
    poor_impact = {
        'research_accuracy': -0.05,  # 5% degradation
        'alert_relevance': 0.02     # 2% improvement
    }
    assert self_improvement._should_rollback(poor_impact)
    
    # Test case: minimal impact
    minimal_impact = {
        'research_accuracy': 0.02,  # 2% improvement
        'alert_relevance': 0.03     # 3% improvement
    }
    assert self_improvement._should_rollback(minimal_impact)

@pytest.mark.asyncio
async def test_rollback_optimization(self_improvement):
    """Test optimization rollback."""
    # Create an optimization result with rollback data
    optimization = OptimizationResult(
        optimization_type=OptimizationType.PARAMETER_TUNING,
        target_module='business_intelligence',
        changes_made={'cache_timeout': {'old': 3600, 'new': 1800}},
        performance_impact={'research_accuracy': -0.05},
        timestamp=datetime.now(),
        success=True,
        rollback_data={'cache_timeout': 3600}
    )
    
    # Store original value
    original_value = self_improvement.config['business_intelligence_cache_timeout']
    
    # Apply a change
    self_improvement.config['business_intelligence_cache_timeout'] = 1800
    
    # Rollback
    await self_improvement._rollback_optimization(optimization)
    
    # Verify rollback
    assert self_improvement.config['business_intelligence_cache_timeout'] == original_value

@pytest.mark.asyncio
async def test_get_optimization_history(self_improvement):
    """Test retrieving optimization history."""
    # Add some optimization results
    results = [
        OptimizationResult(
            optimization_type=OptimizationType.PARAMETER_TUNING,
            target_module='business_intelligence',
            changes_made={'param1': {'old': 1, 'new': 2}},
            performance_impact={'metric1': 0.1},
            timestamp=datetime.now() - timedelta(days=1),
            success=True
        ),
        OptimizationResult(
            optimization_type=OptimizationType.MODEL_UPDATE,
            target_module='dialogue_manager',
            changes_made={'param2': {'old': 3, 'new': 4}},
            performance_impact={'metric2': 0.2},
            timestamp=datetime.now() - timedelta(days=2),
            success=True
        )
    ]
    
    self_improvement.optimization_history.extend(results)
    
    # Get full history
    history = self_improvement.get_optimization_history()
    assert len(history) == 2
    assert history[0].timestamp > history[1].timestamp
    
    # Get filtered history
    bi_history = self_improvement.get_optimization_history(module='business_intelligence')
    assert len(bi_history) == 1
    assert bi_history[0].target_module == 'business_intelligence' 