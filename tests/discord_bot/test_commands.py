"""
Tests for Discord bot commands
"""

import pytest
import discord
from discord.ext import commands
from src.discord_bot.cogs.commands import BusinessCommands

class MockBot:
    """Mock bot class for testing."""
    def __init__(self):
        self.business_intelligence = MockBusinessIntelligence()

class MockBusinessIntelligence:
    """Mock business intelligence class for testing."""
    async def research(self, topic: str, depth: str = "medium") -> dict:
        return {
            'summary': f'Research results for {topic}',
            'details': {
                'Market Size': '$1B',
                'Growth Rate': '10%'
            }
        }
    
    async def setup_monitor(self, target: str, metric: str, threshold: float) -> dict:
        return {
            'id': 'mon_123',
            'status': 'active'
        }
    
    async def analyze_metric(self, metric: str, timeframe: str = "1d") -> dict:
        return {
            'summary': f'Analysis of {metric}',
            'current': 100,
            'trend': 'up'
        }
    
    async def generate_report(self, report_type: str, timeframe: str = "1w") -> dict:
        return {
            'summary': f'{report_type} report',
            'sections': []
        }

class MockInteraction:
    """Mock Discord interaction."""
    def __init__(self):
        self.response = MockResponse()
        self.followup = MockFollowup()

class MockResponse:
    """Mock interaction response."""
    async def defer(self):
        pass

class MockFollowup:
    """Mock interaction followup."""
    async def send(self, content=None, embed=None, ephemeral=False):
        return MockMessage()

class MockMessage:
    """Mock Discord message."""
    async def edit(self, embed=None):
        pass

class MockContext:
    """Mock Discord context."""
    async def send(self, content=None, embed=None):
        pass

@pytest.fixture
def bot():
    """Create a mock bot instance."""
    return MockBot()

@pytest.fixture
def cog(bot):
    """Create a BusinessCommands cog instance."""
    return BusinessCommands(bot)

@pytest.fixture
def interaction():
    """Create a mock interaction."""
    return MockInteraction()

@pytest.fixture
def ctx():
    """Create a mock context."""
    return MockContext()

@pytest.mark.asyncio
async def test_help_command(cog, ctx):
    """Test the help command."""
    await cog.help_command.callback(cog, ctx)

@pytest.mark.asyncio
async def test_research_command_validation(cog, interaction):
    """Test research command input validation."""
    # Test with invalid topic (too short)
    await cog.research.callback(cog, interaction, topic="a")
    
    # Test with invalid depth
    await cog.research.callback(cog, interaction, topic="AI Technology", depth="invalid")
    
    # Test with valid inputs
    await cog.research.callback(cog, interaction, topic="AI Technology", depth="deep")

@pytest.mark.asyncio
async def test_monitor_command_validation(cog, interaction):
    """Test monitor command input validation."""
    # Test with invalid target (too short)
    await cog.monitor.callback(cog, interaction, target="a", metric="test", threshold=75.0)
    
    # Test with invalid metric (too short)
    await cog.monitor.callback(cog, interaction, target="Market Share", metric="", threshold=75.0)
    
    # Test with invalid threshold
    await cog.monitor.callback(cog, interaction, target="Market Share", metric="percentage", threshold=-1.0)
    
    # Test with valid inputs
    await cog.monitor.callback(cog, interaction, target="Market Share", metric="percentage", threshold=75.0)

@pytest.mark.asyncio
async def test_analyze_command_validation(cog, interaction):
    """Test analyze command input validation."""
    # Test with invalid metric (too short)
    await cog.analyze.callback(cog, interaction, metric="")
    
    # Test with invalid timeframe
    await cog.analyze.callback(cog, interaction, metric="Revenue", timeframe="invalid")
    
    # Test with valid inputs
    await cog.analyze.callback(cog, interaction, metric="Revenue", timeframe="1w")

@pytest.mark.asyncio
async def test_report_command_validation(cog, interaction):
    """Test report command input validation."""
    # Test with invalid report type
    await cog.report.callback(cog, interaction, report_type="invalid")
    
    # Test with invalid timeframe
    await cog.report.callback(cog, interaction, report_type="performance", timeframe="invalid")
    
    # Test with valid inputs
    await cog.report.callback(cog, interaction, report_type="performance", timeframe="1w")

@pytest.mark.asyncio
async def test_error_handling(cog, interaction, ctx):
    """Test error handling in commands."""
    # Test command not found error
    error = commands.CommandNotFound()
    await cog.on_command_error(ctx, error)
    
    # Test general error
    error = Exception("Test error")
    await cog.on_command_error(ctx, error)
    
    # Test business intelligence error
    class ErrorBusinessIntelligence:
        async def research(self, *args, **kwargs):
            raise Exception("Test error")
    
    cog.bot.business_intelligence = ErrorBusinessIntelligence()
    await cog.research.callback(cog, interaction, topic="Test")

@pytest.mark.asyncio
async def test_command_metadata(cog):
    """Test command metadata and descriptions."""
    assert cog.research.name == "research"
    assert cog.monitor.name == "monitor"
    assert cog.analyze.name == "analyze"
    assert cog.report.name == "report"
    
    # Verify command descriptions
    assert "Research a company or industry" in cog.research.description
    assert "Set up business monitoring alerts" in cog.monitor.description
    assert "Analyze business performance metrics" in cog.analyze.description
    assert "Generate a business intelligence report" in cog.report.description 