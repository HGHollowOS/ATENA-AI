"""
Business Intelligence cog for ATENA-AI Discord bot.
Provides commands for company research, market analysis, and partnership opportunities.
"""

import discord
from discord.ext import commands
import logging
from typing import Optional, Dict, Any
from src.business_intelligence.business_intelligence import (
    BusinessIntelligence,
    CompanyProfile,
    MarketAnalysis
)

logger = logging.getLogger(__name__)

class BusinessIntelligenceCog(commands.Cog):
    """Business Intelligence cog for ATENA-AI."""
    
    def __init__(self, bot):
        """Initialize the Business Intelligence cog."""
        self.bot = bot
        self.bi_service = BusinessIntelligence(bot.config)
    
    @commands.command(name='research')
    async def research_company(
        self,
        ctx: commands.Context,
        company_name: str
    ):
        """Research a company and provide detailed information."""
        try:
            # Show typing indicator
            async with ctx.typing():
                # Research company
                profile = await self.bi_service.research_company(company_name)
                
                # Create embed
                embed = discord.Embed(
                    title=f"Company Research: {profile.name}",
                    color=discord.Color.blue()
                )
                
                # Add basic information
                embed.add_field(
                    name="Basic Information",
                    value=f"**Type:** {profile.type.value}\n"
                          f"**Industry:** {profile.industry}\n"
                          f"**Size:** {profile.size} employees\n"
                          f"**Founded:** {profile.founded}\n"
                          f"**Location:** {profile.location}",
                    inline=False
                )
                
                # Add description
                embed.add_field(
                    name="Description",
                    value=profile.description,
                    inline=False
                )
                
                # Add technologies
                embed.add_field(
                    name="Technologies",
                    value=", ".join(profile.technologies),
                    inline=False
                )
                
                # Add financial information
                if profile.funding:
                    funding_info = (
                        f"**Total Funding:** ${profile.funding['total']:,.2f}\n"
                        f"**Latest Round:** {profile.funding['rounds'][-1]['type']} "
                        f"(${profile.funding['rounds'][-1]['amount']:,.2f})"
                    )
                    embed.add_field(
                        name="Funding",
                        value=funding_info,
                        inline=False
                    )
                
                # Add metrics
                metrics_info = (
                    f"**Revenue:** ${profile.metrics['revenue']:,.2f}\n"
                    f"**Growth Rate:** {profile.metrics['growth_rate']*100:.1f}%\n"
                    f"**Employees:** {profile.metrics['employees']}"
                )
                embed.add_field(
                    name="Metrics",
                    value=metrics_info,
                    inline=False
                )
                
                # Add website if available
                if profile.website:
                    embed.add_field(
                        name="Website",
                        value=profile.website,
                        inline=False
                    )
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error researching company: {e}")
            await ctx.send("I encountered an error while researching the company.")
    
    @commands.command(name='market')
    async def analyze_market(
        self,
        ctx: commands.Context,
        industry: str
    ):
        """Analyze market conditions for a specific industry."""
        try:
            # Show typing indicator
            async with ctx.typing():
                # Analyze market
                analysis = await self.bi_service.analyze_market(industry)
                
                # Create embed
                embed = discord.Embed(
                    title=f"Market Analysis: {analysis.industry}",
                    color=discord.Color.green()
                )
                
                # Add market size and growth
                if analysis.market_size:
                    embed.add_field(
                        name="Market Size",
                        value=f"${analysis.market_size:,.2f}",
                        inline=True
                    )
                if analysis.growth_rate:
                    embed.add_field(
                        name="Growth Rate",
                        value=f"{analysis.growth_rate*100:.1f}%",
                        inline=True
                    )
                
                # Add trends
                embed.add_field(
                    name="Key Trends",
                    value="\n".join(f"• {trend}" for trend in analysis.trends),
                    inline=False
                )
                
                # Add competitors
                embed.add_field(
                    name="Major Competitors",
                    value="\n".join(f"• {comp}" for comp in analysis.competitors),
                    inline=False
                )
                
                # Add opportunities
                embed.add_field(
                    name="Opportunities",
                    value="\n".join(f"• {opp}" for opp in analysis.opportunities),
                    inline=False
                )
                
                # Add risks
                embed.add_field(
                    name="Risks",
                    value="\n".join(f"• {risk}" for risk in analysis.risks),
                    inline=False
                )
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error analyzing market: {e}")
            await ctx.send("I encountered an error while analyzing the market.")
    
    @commands.command(name='partners')
    async def find_partners(
        self,
        ctx: commands.Context,
        company_name: str,
        *,
        criteria: Optional[str] = None
    ):
        """Find potential partnership opportunities for a company."""
        try:
            # Show typing indicator
            async with ctx.typing():
                # Parse criteria if provided
                search_criteria = {}
                if criteria:
                    # Simple parsing of criteria string
                    # Format: "size_range:small location:US funding_stage:seed"
                    for item in criteria.split():
                        if ':' in item:
                            key, value = item.split(':')
                            search_criteria[key] = value
                
                # Research company first
                profile = await self.bi_service.research_company(company_name)
                
                # Find partnership opportunities
                opportunities = await self.bi_service.find_partnership_opportunities(
                    profile,
                    search_criteria
                )
                
                # Create embed
                embed = discord.Embed(
                    title=f"Partnership Opportunities for {profile.name}",
                    color=discord.Color.purple()
                )
                
                # Add opportunities
                for i, opp in enumerate(opportunities, 1):
                    opp_text = (
                        f"**Match Score:** {opp['match_score']*100:.1f}%\n"
                        f"**Complementary Technologies:** "
                        f"{', '.join(opp['complementary_technologies'])}\n"
                        f"**Potential Synergies:** "
                        f"{', '.join(opp['potential_synergies'])}"
                    )
                    embed.add_field(
                        name=f"Opportunity {i}",
                        value=opp_text,
                        inline=False
                    )
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error finding partners: {e}")
            await ctx.send("I encountered an error while finding partnership opportunities.")

def setup(bot):
    """Set up the Business Intelligence cog."""
    bot.add_cog(BusinessIntelligenceCog(bot)) 