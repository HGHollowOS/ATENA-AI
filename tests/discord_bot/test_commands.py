"""Tests for Discord business commands."""

import pytest
import discord
from discord.ext import commands
from unittest.mock import AsyncMock, MagicMock, patch
from src.discord_bot.cogs.commands import BusinessCommands

class MockBot:
    def __init__(self):
        self.business_intelligence = MagicMock()

class MockInteraction:
    def __init__(self):
        self.response = AsyncMock()
        self.followup = AsyncMock()
        self.client = MockBot()

@pytest.fixture
def bot():
    return MockBot()

@pytest.fixture
def cog(bot):
    return BusinessCommands(bot)

@pytest.fixture
def interaction():
    return MockInteraction()

@pytest.mark.asyncio
async def test_help_command(cog):
    """Test the help command."""
    ctx = MagicMock(spec=commands.Context)
    ctx.send = AsyncMock()
    
    # Get the actual callback function from the command
    help_command = cog.help_command.callback
    await help_command(cog, ctx)
    
    ctx.send.assert_called_once()
    embed = ctx.send.call_args[1]['embed']
    assert isinstance(embed, discord.Embed)
    assert embed.title == "ATENA-AI Command Help"
    assert len(embed.fields) == 4  # Check all command fields are present

@pytest.mark.asyncio
async def test_research_command(cog, interaction):
    """Test the research command with valid input."""
    cog.bot.business_intelligence.research = AsyncMock(return_value={
        'summary': 'Test summary',
        'details': {'key1': 'value1', 'key2': 'value2'}
    })
    
    # Get the actual callback function from the command
    research_command = cog.research.callback
    await research_command(cog, interaction, "test_topic", "quick")
    
    interaction.response.defer.assert_called_once()
    interaction.followup.send.assert_called_once()
    assert isinstance(interaction.followup.send.call_args[1]['embed'], discord.Embed)

@pytest.mark.asyncio
async def test_research_command_invalid_input(cog, interaction):
    """Test the research command with invalid input."""
    research_command = cog.research.callback
    await research_command(cog, interaction, "t", "quick")
    
    interaction.response.send_message.assert_called_once_with(
        "Topic must be at least 2 characters long.",
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_monitor_command(cog, interaction):
    """Test the monitor command with valid input."""
    cog.bot.business_intelligence.setup_monitor = AsyncMock(return_value={
        'id': 'test_id',
        'status': 'active'
    })
    
    monitor_command = cog.monitor.callback
    await monitor_command(cog, interaction, "test_target", "test_metric", 10.0)
    
    interaction.response.defer.assert_called_once()
    interaction.followup.send.assert_called_once()
    assert isinstance(interaction.followup.send.call_args[1]['embed'], discord.Embed)

@pytest.mark.asyncio
async def test_monitor_command_invalid_input(cog, interaction):
    """Test the monitor command with invalid input."""
    monitor_command = cog.monitor.callback
    await monitor_command(cog, interaction, "t", "test_metric", 10.0)
    
    interaction.response.send_message.assert_called_once_with(
        "Target must be at least 2 characters long.",
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_analyze_command(cog, interaction):
    """Test the analyze command with valid input."""
    cog.bot.business_intelligence.analyze_metric = AsyncMock(return_value={
        'summary': 'Test analysis',
        'current': 100,
        'trend': 'upward'
    })
    
    analyze_command = cog.analyze.callback
    await analyze_command(cog, interaction, "test_metric", "1d")
    
    interaction.response.defer.assert_called_once()
    interaction.followup.send.assert_called_once()
    assert isinstance(interaction.followup.send.call_args[1]['embed'], discord.Embed)

@pytest.mark.asyncio
async def test_analyze_command_invalid_input(cog, interaction):
    """Test the analyze command with invalid input."""
    analyze_command = cog.analyze.callback
    await analyze_command(cog, interaction, "t", "1d")
    
    interaction.response.send_message.assert_called_once_with(
        "Metric must be at least 2 characters long.",
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_report_command(cog, interaction):
    """Test the report command with valid input."""
    cog.bot.business_intelligence.generate_report = AsyncMock(return_value={
        'summary': 'Test report',
        'sections': [
            {'title': 'Section 1', 'content': 'Content 1'},
            {'title': 'Section 2', 'content': 'Content 2'}
        ]
    })
    
    report_command = cog.report.callback
    await report_command(cog, interaction, "performance", "1w")
    
    interaction.response.defer.assert_called_once()
    interaction.followup.send.assert_called_once()
    assert isinstance(interaction.followup.send.call_args[1]['embed'], discord.Embed)

@pytest.mark.asyncio
async def test_command_error_handling(cog):
    """Test command error handling."""
    ctx = MagicMock(spec=commands.Context)
    ctx.send = AsyncMock()
    
    # Test CommandNotFound error
    error = commands.CommandNotFound()
    await cog.on_command_error(ctx, error)
    ctx.send.assert_called_with("Command not found. Use !atena help to see available commands.")
    
    # Test generic error
    ctx.send.reset_mock()
    error = Exception("Test error")
    await cog.on_command_error(ctx, error)
    ctx.send.assert_called_with("An error occurred while processing your command. Please try again later.") 