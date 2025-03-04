"""
Business Intelligence cog for ATENA-AI Discord bot.
Provides commands for company research, market analysis, and partnership opportunities,
with support for proactive notifications and natural conversation.
"""

import discord
from discord.ext import commands
import logging
from typing import Optional, Dict, Any, List
import asyncio
import re
from datetime import datetime, timedelta
from src.business_intelligence.business_intelligence import (
    BusinessIntelligence,
    CompanyProfile,
    MarketAnalysis,
    BusinessAlert,
    IndustrySegment
)

logger = logging.getLogger(__name__)

class BusinessIntelligenceCog(commands.Cog):
    """Business Intelligence cog for ATENA-AI."""
    
    def __init__(self, bot):
        """Initialize the Business Intelligence cog."""
        self.bot = bot
        self.bi_service = BusinessIntelligence(bot.config)
        self.notification_channels: Dict[int, int] = {}  # guild_id -> channel_id
        self.monitoring_task = None
        self.conversation_contexts: Dict[int, Dict[str, Any]] = {}  # channel_id -> context
        
        # Natural language patterns for commands
        self.nl_patterns = {
            'research': r'(?i)research|look up|tell me about|what do you know about|find info|company info',
            'market': r'(?i)market|industry|sector|segment analysis|trends',
            'partners': r'(?i)partners|partnerships|opportunities|collaboration|potential deals',
            'monitor': r'(?i)monitor|track|watch|follow|keep an eye on',
            'alert': r'(?i)alert|notify|inform|update me|let me know'
        }
    
    async def cog_load(self):
        """Start background tasks when cog is loaded."""
        self.monitoring_task = asyncio.create_task(self.monitor_and_notify())
    
    async def cog_unload(self):
        """Clean up when cog is unloaded."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle natural language interactions."""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Check if message mentions the bot or is in DM
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = self.bot.user in message.mentions
        
        if not (is_dm or is_mentioned):
            return
        
        # Remove bot mention from message
        content = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
        
        # Process natural language input
        await self._process_natural_language(message, content)
    
    async def _process_natural_language(self, message: discord.Message, content: str):
        """Process natural language input and route to appropriate handler."""
        try:
            # Check for conversation context
            context = self.conversation_contexts.get(message.channel.id, {})
            
            if context.get('expecting_response'):
                # Handle follow-up in conversation
                await self._handle_conversation_follow_up(message, content, context)
                return
            
            # Match against patterns
            if re.search(self.nl_patterns['research'], content):
                # Extract company name
                company_match = re.search(r'(?i)about\s+([a-zA-Z0-9\s]+)', content)
                if company_match:
                    company_name = company_match.group(1).strip()
                    await self.research_company(message.channel, company_name)
                else:
                    # Ask for company name
                    self.conversation_contexts[message.channel.id] = {
                        'expecting_response': True,
                        'intent': 'research',
                        'timestamp': datetime.now()
                    }
                    await message.channel.send("Which company would you like me to research?")
            
            elif re.search(self.nl_patterns['market'], content):
                # Extract industry/segment
                segment_match = re.search(r'(?i)(satellite|power|propulsion|communications|earth observation|manufacturing|debris)', content)
                if segment_match:
                    segment = segment_match.group(1).strip()
                    await self.analyze_market(message.channel, segment)
                else:
                    # Ask for segment
                    self.conversation_contexts[message.channel.id] = {
                        'expecting_response': True,
                        'intent': 'market',
                        'timestamp': datetime.now()
                    }
                    await message.channel.send(
                        "Which space industry segment would you like me to analyze?\n"
                        "Options: satellite servicing, power systems, propulsion, communications, "
                        "earth observation, space manufacturing, debris removal"
                    )
            
            elif re.search(self.nl_patterns['partners'], content):
                # Start partnership discovery conversation
                self.conversation_contexts[message.channel.id] = {
                    'expecting_response': True,
                    'intent': 'partners',
                    'step': 'company',
                    'timestamp': datetime.now()
                }
                await message.channel.send(
                    "I'll help you find partnership opportunities. "
                    "First, which company should we focus on?"
                )
            
            else:
                await message.channel.send(
                    "I can help you with:\n"
                    "• Company research\n"
                    "• Market analysis\n"
                    "• Finding partnership opportunities\n"
                    "Just let me know what you'd like to explore!"
                )
            
        except Exception as e:
            logger.error(f"Error processing natural language input: {e}")
            await message.channel.send("I encountered an error processing your request.")
    
    async def _handle_conversation_follow_up(
        self,
        message: discord.Message,
        content: str,
        context: Dict[str, Any]
    ):
        """Handle follow-up messages in a conversation."""
        try:
            # Check if context is too old
            if (datetime.now() - context['timestamp']) > timedelta(minutes=5):
                self.conversation_contexts.pop(message.channel.id, None)
                await message.channel.send(
                    "Our conversation timed out. Please start over with your request."
                )
                return
            
            if context['intent'] == 'research':
                await self.research_company(message.channel, content)
                self.conversation_contexts.pop(message.channel.id, None)
            
            elif context['intent'] == 'market':
                await self.analyze_market(message.channel, content)
                self.conversation_contexts.pop(message.channel.id, None)
            
            elif context['intent'] == 'partners':
                if context['step'] == 'company':
                    # Store company and ask for criteria
                    context.update({
                        'company': content,
                        'step': 'criteria',
                        'timestamp': datetime.now()
                    })
                    await message.channel.send(
                        "Great! Do you have any specific criteria for potential partners?\n"
                        "You can specify:\n"
                        "• Size range (e.g., startup, enterprise)\n"
                        "• Location\n"
                        "• Technology focus\n"
                        "Or just say 'no' to use default criteria."
                    )
                
                elif context['step'] == 'criteria':
                    criteria = None
                    if content.lower() != 'no':
                        criteria = content
                    
                    await self.find_partners(
                        message.channel,
                        context['company'],
                        criteria
                    )
                    self.conversation_contexts.pop(message.channel.id, None)
            
        except Exception as e:
            logger.error(f"Error handling conversation follow-up: {e}")
            await message.channel.send("I encountered an error processing your response.")
            self.conversation_contexts.pop(message.channel.id, None)
    
    async def monitor_and_notify(self):
        """Background task to monitor for updates and send notifications."""
        try:
            # Start the business intelligence monitoring
            await self.bi_service.start_monitoring()
            
            while True:
                try:
                    # Get pending alerts
                    alerts = await self.bi_service.get_pending_alerts()
                    
                    for alert in alerts:
                        await self._send_alert(alert)
                    
                    await asyncio.sleep(60)  # Check every minute
                    
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    await asyncio.sleep(60)
            
        except asyncio.CancelledError:
            logger.info("Monitoring task cancelled")
        except Exception as e:
            logger.error(f"Fatal error in monitoring task: {e}")
    
    async def _send_alert(self, alert: BusinessAlert):
        """Send an alert to notification channels."""
        try:
            embed = discord.Embed(
                title=alert.title,
                description=alert.description,
                color=discord.Color.gold() if alert.requires_action else discord.Color.blue(),
                timestamp=alert.timestamp
            )
            
            # Add suggested actions if any
            if alert.suggested_actions:
                embed.add_field(
                    name="Suggested Actions",
                    value="\n".join(f"• {action}" for action in alert.suggested_actions),
                    inline=False
                )
            
            # Add source data summary if available
            if alert.source_data.get('url'):
                embed.add_field(
                    name="Source",
                    value=alert.source_data['url'],
                    inline=False
                )
            
            # Send to all notification channels
            for guild_id, channel_id in self.notification_channels.items():
                try:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        await channel.send(
                            "🔔 **New Business Intelligence Alert**",
                            embed=embed
                        )
                except Exception as e:
                    logger.error(f"Error sending alert to channel {channel_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    @commands.command(name='set_notifications')
    @commands.has_permissions(administrator=True)
    async def set_notifications(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel] = None
    ):
        """Set the channel for business intelligence notifications."""
        try:
            target_channel = channel or ctx.channel
            self.notification_channels[ctx.guild.id] = target_channel.id
            
            await ctx.send(
                f"✅ Business intelligence notifications will be sent to {target_channel.mention}"
            )
            
        except Exception as e:
            logger.error(f"Error setting notification channel: {e}")
            await ctx.send("Failed to set notification channel.")
    
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