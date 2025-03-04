"""
Discord commands cog for ATENA-AI.
Provides business-focused commands and interactions.
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class BusinessCommands(commands.Cog):
    """Business-focused commands for ATENA-AI."""
    
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(
        name="research",
        description="Research a company or industry"
    )
    async def research(
        self,
        interaction: discord.Interaction,
        topic: str,
        depth: Optional[str] = "medium"
    ):
        """
        Conduct business research on a company or industry.
        
        Parameters:
        -----------
        topic : str
            The company or industry to research
        depth : str, optional
            Research depth: "quick", "medium", or "deep"
        """
        await interaction.response.defer()
        
        try:
            # Create research embed
            embed = discord.Embed(
                title=f"Business Research: {topic}",
                description="Analyzing market data and trends...",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Status", value="🔍 Researching...", inline=False)
            
            message = await interaction.followup.send(embed=embed)
            
            # Simulate research process
            research_result = await self.bot.business_intelligence.research(topic, depth)
            
            # Update embed with results
            embed.description = research_result['summary']
            embed.clear_fields()
            
            for key, value in research_result['details'].items():
                embed.add_field(name=key, value=value, inline=False)
                
            embed.set_footer(text=f"Research depth: {depth}")
            await message.edit(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in research command: {e}")
            await interaction.followup.send(
                "An error occurred while conducting research. Please try again later.",
                ephemeral=True
            )

    @app_commands.command(
        name="monitor",
        description="Set up business monitoring alerts"
    )
    async def monitor(
        self,
        interaction: discord.Interaction,
        target: str,
        metric: str,
        threshold: float
    ):
        """
        Set up monitoring for business metrics.
        
        Parameters:
        -----------
        target : str
            The company or metric to monitor
        metric : str
            The specific metric to track
        threshold : float
            Alert threshold value
        """
        await interaction.response.defer()
        
        try:
            # Create monitor embed
            embed = discord.Embed(
                title=f"Business Monitor: {target}",
                description=f"Setting up monitoring for {metric}",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            # Set up monitoring
            monitor_config = await self.bot.business_intelligence.setup_monitor(
                target, metric, threshold
            )
            
            embed.add_field(
                name="Status",
                value="✅ Monitor configured successfully",
                inline=False
            )
            embed.add_field(
                name="Target",
                value=target,
                inline=True
            )
            embed.add_field(
                name="Metric",
                value=metric,
                inline=True
            )
            embed.add_field(
                name="Threshold",
                value=str(threshold),
                inline=True
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in monitor command: {e}")
            await interaction.followup.send(
                "An error occurred while setting up the monitor. Please try again later.",
                ephemeral=True
            )

    @app_commands.command(
        name="analyze",
        description="Analyze business performance metrics"
    )
    async def analyze(
        self,
        interaction: discord.Interaction,
        metric: str,
        timeframe: Optional[str] = "1d"
    ):
        """
        Analyze business performance metrics.
        
        Parameters:
        -----------
        metric : str
            The metric to analyze
        timeframe : str, optional
            Time period: "1h", "1d", "1w", "1m"
        """
        await interaction.response.defer()
        
        try:
            # Create analysis embed
            embed = discord.Embed(
                title=f"Performance Analysis: {metric}",
                description=f"Analyzing data for the past {timeframe}",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            message = await interaction.followup.send(embed=embed)
            
            # Perform analysis
            analysis = await self.bot.business_intelligence.analyze_metric(
                metric, timeframe
            )
            
            # Update embed with results
            embed.description = analysis['summary']
            
            embed.add_field(
                name="Current Value",
                value=str(analysis['current']),
                inline=True
            )
            embed.add_field(
                name="Trend",
                value=analysis['trend'],
                inline=True
            )
            embed.add_field(
                name="Change",
                value=analysis['change'],
                inline=True
            )
            
            if 'recommendations' in analysis:
                embed.add_field(
                    name="Recommendations",
                    value=analysis['recommendations'],
                    inline=False
                )
            
            await message.edit(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in analyze command: {e}")
            await interaction.followup.send(
                "An error occurred during analysis. Please try again later.",
                ephemeral=True
            )

    @app_commands.command(
        name="report",
        description="Generate a business intelligence report"
    )
    async def report(
        self,
        interaction: discord.Interaction,
        report_type: str,
        timeframe: Optional[str] = "1w"
    ):
        """
        Generate a business intelligence report.
        
        Parameters:
        -----------
        report_type : str
            Type of report to generate
        timeframe : str, optional
            Time period to cover: "1d", "1w", "1m", "3m"
        """
        await interaction.response.defer()
        
        try:
            # Create report embed
            embed = discord.Embed(
                title=f"Business Report: {report_type}",
                description=f"Generating report for {timeframe}",
                color=discord.Color.purple(),
                timestamp=datetime.now()
            )
            
            message = await interaction.followup.send(embed=embed)
            
            # Generate report
            report = await self.bot.business_intelligence.generate_report(
                report_type, timeframe
            )
            
            # Update embed with report
            embed.description = report['summary']
            
            for section in report['sections']:
                embed.add_field(
                    name=section['title'],
                    value=section['content'],
                    inline=False
                )
            
            # Add report metadata
            embed.set_footer(
                text=f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            await message.edit(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in report command: {e}")
            await interaction.followup.send(
                "An error occurred while generating the report. Please try again later.",
                ephemeral=True
            )

async def setup(bot):
    """Add the cog to the bot."""
    await bot.add_cog(BusinessCommands(bot)) 