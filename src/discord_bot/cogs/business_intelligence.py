"""
Business Intelligence cog for ATENA-AI Discord bot.
Handles partnership research, opportunity monitoring, and business analytics.
"""

import discord
from discord.ext import commands
import asyncio
import logging
from typing import Dict, List, Optional, Any
import json
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class BusinessIntelligence(commands.Cog):
    """Business Intelligence cog for ATENA-AI."""
    
    def __init__(self, bot):
        """Initialize the Business Intelligence cog."""
        self.bot = bot
        self.config = self._load_config()
        self.opportunities: Dict[str, List[Dict[str, Any]]] = {}
        self.research_tasks: Dict[str, asyncio.Task] = {}
    
    def _load_config(self) -> Dict[str, Any]:
        """Load business intelligence configuration."""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                return config.get('business_intelligence', {
                    'research_interval': 3600,  # 1 hour
                    'min_opportunity_score': 0.7,
                    'max_opportunities_per_industry': 5,
                    'partnership_criteria': {
                        'min_revenue': '10M',
                        'tech_stack': ['Python', 'AI/ML'],
                        'market_presence': 'global'
                    }
                })
        except FileNotFoundError:
            logger.warning("config.json not found, using default configuration")
            return {
                'research_interval': 3600,
                'min_opportunity_score': 0.7,
                'max_opportunities_per_industry': 5,
                'partnership_criteria': {
                    'min_revenue': '10M',
                    'tech_stack': ['Python', 'AI/ML'],
                    'market_presence': 'global'
                }
            }
    
    @commands.group(name='business')
    async def business_group(self, ctx):
        """Business intelligence command group."""
        if ctx.invoked_subcommand is None:
            await ctx.send(
                "Available business commands:\n"
                "`!business research` - Research partnership opportunities\n"
                "`!business opportunities` - List current opportunities\n"
                "`!business analyze <company>` - Analyze a specific company\n"
                "`!business monitor <industry>` - Monitor an industry for opportunities"
            )
    
    @business_group.command(name='research')
    async def research_opportunities(self, ctx, industry: Optional[str] = None):
        """Research partnership opportunities in specified industry or all industries."""
        await ctx.send("🔍 Starting partnership research...")
        
        try:
            # Start research task
            task = asyncio.create_task(
                self._research_opportunities(industry)
            )
            
            # Store task for tracking
            self.research_tasks[f"{ctx.guild.id}_{industry or 'all'}"] = task
            
            # Wait for initial results
            opportunities = await asyncio.wait_for(task, timeout=30)
            
            if not opportunities:
                await ctx.send("No immediate opportunities found. I'll continue monitoring in the background.")
                return
            
            # Format and send results
            embed = discord.Embed(
                title="Partnership Opportunities",
                description=f"Found {len(opportunities)} potential opportunities",
                color=discord.Color.blue()
            )
            
            for opp in opportunities[:5]:  # Show top 5
                embed.add_field(
                    name=f"🏢 {opp['company']}",
                    value=f"Score: {opp['score']:.2f}\n"
                          f"Industry: {opp['industry']}\n"
                          f"Details: {opp['description'][:100]}...",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except asyncio.TimeoutError:
            await ctx.send("Research is taking longer than expected. I'll notify you when I find opportunities.")
        except Exception as e:
            logger.error(f"Error in research: {e}")
            await ctx.send("An error occurred during research. Please try again later.")
    
    @business_group.command(name='opportunities')
    async def list_opportunities(self, ctx, industry: Optional[str] = None):
        """List current partnership opportunities."""
        try:
            opportunities = self.opportunities.get(industry or 'all', [])
            
            if not opportunities:
                await ctx.send("No current opportunities found.")
                return
            
            # Sort by score
            opportunities.sort(key=lambda x: x['score'], reverse=True)
            
            # Create embed
            embed = discord.Embed(
                title="Current Partnership Opportunities",
                description=f"Found {len(opportunities)} opportunities",
                color=discord.Color.green()
            )
            
            for opp in opportunities[:10]:  # Show top 10
                embed.add_field(
                    name=f"🏢 {opp['company']}",
                    value=f"Score: {opp['score']:.2f}\n"
                          f"Industry: {opp['industry']}\n"
                          f"Last Updated: {opp['last_updated'].strftime('%Y-%m-%d %H:%M')}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing opportunities: {e}")
            await ctx.send("An error occurred while fetching opportunities.")
    
    @business_group.command(name='analyze')
    async def analyze_company(self, ctx, company: str):
        """Analyze a specific company for partnership potential."""
        await ctx.send(f"🔍 Analyzing {company}...")
        
        try:
            analysis = await self._analyze_company(company)
            
            if not analysis:
                await ctx.send(f"No data found for {company}.")
                return
            
            # Create detailed embed
            embed = discord.Embed(
                title=f"Company Analysis: {company}",
                color=discord.Color.blue()
            )
            
            # Add analysis fields
            embed.add_field(
                name="Partnership Score",
                value=f"{analysis['score']:.2f}/1.00",
                inline=True
            )
            
            embed.add_field(
                name="Industry",
                value=analysis['industry'],
                inline=True
            )
            
            embed.add_field(
                name="Market Presence",
                value=analysis['market_presence'],
                inline=True
            )
            
            embed.add_field(
                name="Tech Stack Match",
                value=f"{analysis['tech_match']:.1%}",
                inline=True
            )
            
            embed.add_field(
                name="Key Strengths",
                value="\n".join(f"• {s}" for s in analysis['strengths']),
                inline=False
            )
            
            embed.add_field(
                name="Potential Challenges",
                value="\n".join(f"• {c}" for c in analysis['challenges']),
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error analyzing company: {e}")
            await ctx.send("An error occurred during company analysis.")
    
    @business_group.command(name='monitor')
    async def monitor_industry(self, ctx, industry: str):
        """Start monitoring an industry for opportunities."""
        try:
            # Check if already monitoring
            if industry in self.research_tasks:
                await ctx.send(f"Already monitoring {industry} for opportunities.")
                return
            
            # Start monitoring task
            task = asyncio.create_task(
                self._monitor_industry(industry)
            )
            
            self.research_tasks[industry] = task
            await ctx.send(f"✅ Started monitoring {industry} for opportunities.")
            
        except Exception as e:
            logger.error(f"Error starting industry monitoring: {e}")
            await ctx.send("Failed to start industry monitoring.")
    
    async def _research_opportunities(self, industry: Optional[str] = None) -> List[Dict[str, Any]]:
        """Research partnership opportunities."""
        try:
            # TODO: Implement actual research logic
            # This is a placeholder that simulates research
            opportunities = []
            
            # Simulate API calls and data processing
            await asyncio.sleep(2)
            
            # Generate sample opportunities
            industries = [industry] if industry else ['AI', 'Cloud', 'Cybersecurity']
            
            for ind in industries:
                for i in range(3):
                    opp = {
                        'company': f"TechCorp{i+1}",
                        'industry': ind,
                        'score': 0.7 + (i * 0.1),
                        'description': f"Leading provider of {ind} solutions",
                        'last_updated': datetime.now()
                    }
                    opportunities.append(opp)
            
            # Update stored opportunities
            self.opportunities[industry or 'all'] = opportunities
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error in opportunity research: {e}")
            return []
    
    async def _analyze_company(self, company: str) -> Optional[Dict[str, Any]]:
        """Analyze a specific company."""
        try:
            # TODO: Implement actual company analysis
            # This is a placeholder that simulates analysis
            await asyncio.sleep(1)
            
            return {
                'score': 0.85,
                'industry': 'AI/ML',
                'market_presence': 'Global',
                'tech_match': 0.9,
                'strengths': [
                    'Strong AI capabilities',
                    'Global presence',
                    'Innovative solutions'
                ],
                'challenges': [
                    'Competitive market',
                    'Integration complexity'
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in company analysis: {e}")
            return None
    
    async def _monitor_industry(self, industry: str):
        """Monitor an industry for opportunities."""
        while True:
            try:
                # Research opportunities
                opportunities = await self._research_opportunities(industry)
                
                # Check for high-priority opportunities
                high_priority = [
                    opp for opp in opportunities
                    if opp['score'] >= self.config['min_opportunity_score']
                ]
                
                if high_priority:
                    # Get notification channel
                    channel_id = self.bot.notification_channels.get(self.bot.guilds[0].id)
                    if channel_id:
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            await channel.send(
                                f"🔔 **New High-Priority Opportunity in {industry}**\n"
                                f"Found {len(high_priority)} potential partners"
                            )
                
                # Wait before next check
                await asyncio.sleep(self.config['research_interval'])
                
            except Exception as e:
                logger.error(f"Error in industry monitoring: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def check_opportunities(self) -> List[Dict[str, Any]]:
        """Check for new business opportunities."""
        try:
            opportunities = []
            
            # Check all monitored industries
            for industry, task in self.research_tasks.items():
                if not task.done():
                    continue
                
                # Get opportunities for industry
                industry_opps = self.opportunities.get(industry, [])
                
                # Filter high-priority opportunities
                high_priority = [
                    opp for opp in industry_opps
                    if opp['score'] >= self.config['min_opportunity_score']
                ]
                
                opportunities.extend(high_priority)
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error checking opportunities: {e}")
            return []

def setup(bot):
    """Set up the Business Intelligence cog."""
    bot.add_cog(BusinessIntelligence(bot)) 