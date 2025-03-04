"""
Business-focused Discord commands for ATENA-AI.
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal, Optional
import logging

logger = logging.getLogger(__name__)

class BusinessCommands(commands.Cog):
    """Business intelligence and research commands."""
    
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context):
        """Display help information for ATENA-AI commands."""
        embed = discord.Embed(
            title="ATENA-AI Command Help",
            description="Here are the available commands:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="/research [topic] [depth]",
            value="Research a company or industry. Depth can be 'quick', 'medium', or 'deep'.",
            inline=False
        )
        
        embed.add_field(
            name="/monitor [target] [metric] [threshold]",
            value="Set up monitoring for business metrics with alerts.",
            inline=False
        )
        
        embed.add_field(
            name="/analyze [metric] [timeframe]",
            value="Analyze business performance metrics. Timeframe examples: '1d', '1w', '1m'.",
            inline=False
        )
        
        embed.add_field(
            name="/report [type] [timeframe]",
            value="Generate business intelligence reports. Types: 'performance', 'market', 'competitor'.",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @app_commands.command()
    @app_commands.describe(
        topic="Company or industry to research",
        depth="Depth of research (quick/medium/deep)"
    )
    async def research(
        self,
        interaction: discord.Interaction,
        topic: str,
        depth: Literal["quick", "medium", "deep"] = "medium"
    ):
        """Research a company or industry."""
        if len(topic) < 2:
            await interaction.response.send_message("Topic must be at least 2 characters long.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            result = await self.bot.business_intelligence.research(topic, depth)
            
            embed = discord.Embed(
                title=f"Research Results: {topic}",
                description=result['summary'],
                color=discord.Color.green()
            )
            
            for key, value in result['details'].items():
                embed.add_field(name=key, value=value, inline=True)
                
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in research command: {str(e)}")
            await interaction.followup.send(
                "An error occurred while processing your request. Please try again later.",
                ephemeral=True
            )

    @app_commands.command()
    @app_commands.describe(
        target="Metric target to monitor",
        metric="Type of metric",
        threshold="Alert threshold value"
    )
    async def monitor(
        self,
        interaction: discord.Interaction,
        target: str,
        metric: str,
        threshold: float
    ):
        """Set up business monitoring alerts."""
        if len(target) < 2:
            await interaction.response.send_message("Target must be at least 2 characters long.", ephemeral=True)
            return
            
        if len(metric) < 2:
            await interaction.response.send_message("Metric must be at least 2 characters long.", ephemeral=True)
            return
            
        if threshold < 0:
            await interaction.response.send_message("Threshold must be a positive number.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            result = await self.bot.business_intelligence.setup_monitor(target, metric, threshold)
            
            embed = discord.Embed(
                title="Monitor Setup Complete",
                description=f"Monitoring configured for {target}",
                color=discord.Color.green()
            )
            
            embed.add_field(name="Monitor ID", value=result['id'])
            embed.add_field(name="Status", value=result['status'])
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in monitor command: {str(e)}")
            await interaction.followup.send(
                "An error occurred while setting up the monitor. Please try again later.",
                ephemeral=True
            )

    @app_commands.command()
    @app_commands.describe(
        metric="Metric to analyze",
        timeframe="Analysis timeframe (1d/1w/1m)"
    )
    async def analyze(
        self,
        interaction: discord.Interaction,
        metric: str,
        timeframe: Literal["1d", "1w", "1m"] = "1d"
    ):
        """Analyze business performance metrics."""
        if len(metric) < 2:
            await interaction.response.send_message("Metric must be at least 2 characters long.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            result = await self.bot.business_intelligence.analyze_metric(metric, timeframe)
            
            embed = discord.Embed(
                title=f"Analysis: {metric}",
                description=result['summary'],
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Current Value", value=str(result['current']))
            embed.add_field(name="Trend", value=result['trend'])
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in analyze command: {str(e)}")
            await interaction.followup.send(
                "An error occurred while analyzing the metric. Please try again later.",
                ephemeral=True
            )

    @app_commands.command()
    @app_commands.describe(
        report_type="Type of report to generate",
        timeframe="Report timeframe (1d/1w/1m)"
    )
    async def report(
        self,
        interaction: discord.Interaction,
        report_type: Literal["performance", "market", "competitor"],
        timeframe: Literal["1d", "1w", "1m"] = "1w"
    ):
        """Generate a business intelligence report."""
        await interaction.response.defer()
        
        try:
            result = await self.bot.business_intelligence.generate_report(report_type, timeframe)
            
            embed = discord.Embed(
                title=f"{report_type.title()} Report",
                description=result['summary'],
                color=discord.Color.gold()
            )
            
            for section in result['sections']:
                if isinstance(section, dict) and 'title' in section and 'content' in section:
                    embed.add_field(
                        name=section['title'],
                        value=section['content'],
                        inline=False
                    )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in report command: {str(e)}")
            await interaction.followup.send(
                "An error occurred while generating the report. Please try again later.",
                ephemeral=True
            )

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle command errors."""
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("Command not found. Use !atena help to see available commands.")
        else:
            logger.error(f"Command error: {str(error)}")
            await ctx.send("An error occurred while processing your command. Please try again later.")

async def setup(bot):
    """Add the cog to the bot."""
    await bot.add_cog(BusinessCommands(bot)) 