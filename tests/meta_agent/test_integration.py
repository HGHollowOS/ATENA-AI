import pytest
import asyncio
from datetime import datetime, timedelta
from src.meta_agent.meta_agent import (
    MetaAgent,
    PerformanceMetric,
    MetricSnapshot,
    DecisionOutcome,
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
async def test_performance_degradation_triggers_optimization(meta_agent, self_improvement):
    """Test that performance degradation triggers optimization process."""
    # Record multiple poor performance metrics
    for _ in range(5):
        snapshot = MetricSnapshot(
            metric_type=PerformanceMetric.API_LATENCY,
            value=3.0,  # Well above threshold
            timestamp=datetime.now(),
            context={'endpoint': 'test_api'},
            source_module='api_client'
        )
        meta_agent.record_metric(snapshot)
    
    # Analyze performance and get improvements
    await meta_agent._analyze_performance()
    improvements = await meta_agent.get_pending_improvements()
    
    # Verify improvements were created
    assert len(improvements) > 0
    
    # Process improvements through self-improvement module
    for improvement in improvements:
        optimization = await self_improvement._generate_optimization(
            improvement.target_module,
            OptimizationType.PARAMETER_TUNING,
            [improvement],
            {'api_latency': 3.0}
        )
        
        # Apply optimization
        result = await self_improvement._apply_optimization(optimization)
        assert result.success
        assert result.target_module == 'api_client'

@pytest.mark.asyncio
async def test_optimization_rollback_on_poor_performance(meta_agent, self_improvement):
    """Test that optimizations are rolled back if they don't improve performance."""
    # Initial state
    original_timeout = self_improvement.config['api_client_request_timeout']
    
    # Create and apply an optimization
    optimization = {
        'type': OptimizationType.PARAMETER_TUNING,
        'module': 'api_client',
        'parameters': {
            'request_timeout': 5  # Reduced timeout
        },
        'rollback_data': {
            'request_timeout': original_timeout
        }
    }
    
    result = await self_improvement._apply_optimization(optimization)
    assert result.success
    
    # Record poor performance after optimization
    for _ in range(3):
        snapshot = MetricSnapshot(
            metric_type=PerformanceMetric.API_LATENCY,
            value=4.0,  # Worse performance
            timestamp=datetime.now(),
            context={'endpoint': 'test_api'},
            source_module='api_client'
        )
        meta_agent.record_metric(snapshot)
    
    # Monitor impact and trigger rollback
    impact = await self_improvement._monitor_optimization_impact(
        'api_client',
        result,
        {'api_latency': 2.0}  # Previous baseline
    )
    
    assert self_improvement._should_rollback(impact)
    await self_improvement._rollback_optimization(result)
    
    # Verify original configuration was restored
    assert self_improvement.config['api_client_request_timeout'] == original_timeout

@pytest.mark.asyncio
async def test_continuous_improvement_cycle(meta_agent, self_improvement):
    """Test the complete cycle of monitoring, optimization, and evaluation."""
    # Initial poor performance
    for _ in range(3):
        snapshot = MetricSnapshot(
            metric_type=PerformanceMetric.RESEARCH_ACCURACY,
            value=0.6,
            timestamp=datetime.now(),
            context={'query': 'test'},
            source_module='business_intelligence'
        )
        meta_agent.record_metric(snapshot)
    
    # First improvement cycle
    await meta_agent._analyze_performance()
    improvements = await meta_agent.get_pending_improvements()
    assert len(improvements) > 0
    
    # Apply first optimization
    first_optimization = await self_improvement._generate_optimization(
        improvements[0].target_module,
        OptimizationType.PARAMETER_TUNING,
        improvements,
        {'research_accuracy': 0.6}
    )
    first_result = await self_improvement._apply_optimization(first_optimization)
    assert first_result.success
    
    # Record improved performance
    for _ in range(3):
        snapshot = MetricSnapshot(
            metric_type=PerformanceMetric.RESEARCH_ACCURACY,
            value=0.85,
            timestamp=datetime.now(),
            context={'query': 'test'},
            source_module='business_intelligence'
        )
        meta_agent.record_metric(snapshot)
    
    # Verify improvement
    impact = await self_improvement._monitor_optimization_impact(
        'business_intelligence',
        first_result,
        {'research_accuracy': 0.6}
    )
    assert not self_improvement._should_rollback(impact)
    
    # Check optimization history
    history = self_improvement.get_optimization_history()
    assert len(history) > 0
    assert history[0].success
    assert history[0].target_module == 'business_intelligence'

@pytest.mark.asyncio
async def test_multi_module_optimization(meta_agent, self_improvement):
    """Test optimization across multiple modules simultaneously."""
    # Record issues in multiple modules
    modules = {
        'api_client': (PerformanceMetric.API_LATENCY, 3.0),
        'business_intelligence': (PerformanceMetric.RESEARCH_ACCURACY, 0.6)
    }
    
    for module, (metric, value) in modules.items():
        for _ in range(3):
            snapshot = MetricSnapshot(
                metric_type=metric,
                value=value,
                timestamp=datetime.now(),
                context={'test': True},
                source_module=module
            )
            meta_agent.record_metric(snapshot)
    
    # Analyze and get improvements
    await meta_agent._analyze_performance()
    improvements = await meta_agent.get_pending_improvements()
    
    # Verify multiple modules are targeted
    targeted_modules = {imp.target_module for imp in improvements}
    assert len(targeted_modules) == 2
    
    # Apply optimizations
    results = []
    for improvement in improvements:
        optimization = await self_improvement._generate_optimization(
            improvement.target_module,
            OptimizationType.PARAMETER_TUNING,
            [improvement],
            {str(metric).split('.')[-1].lower(): value for module, (metric, value) in modules.items()}
        )
        result = await self_improvement._apply_optimization(optimization)
        results.append(result)
    
    # Verify all optimizations were successful
    assert all(result.success for result in results)
    assert len(results) == 2
    
    # Verify optimization history contains all changes
    history = self_improvement.get_optimization_history()
    assert len(history) == 2
    assert len({entry.target_module for entry in history}) == 2 