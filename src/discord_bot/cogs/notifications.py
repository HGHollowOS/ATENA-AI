"""
Notifications cog for ATENA-AI Discord bot.
Handles proactive notifications and alerts.
"""

import discord
from discord.ext import commands
import asyncio
import logging
from typing import Dict, List, Optional, Any
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class Notifications(commands.Cog):
    """Notifications cog for ATENA-AI."""
    
    def __init__(self, bot):
        """Initialize the Notifications cog."""
        self.bot = bot
        self.config = self._load_config()
        self.notification_channels: Dict[int, int] = {}
        self.notification_tasks: Dict[str, asyncio.Task] = {}
        self.notification_history: Dict[int, List[Dict[str, Any]]] = {}
    
    def _load_config(self) -> Dict[str, Any]:
        """Load notifications configuration."""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                return config.get('notifications', {
                    'max_history': 100,
                    'cooldown': 300,  # 5 minutes
                    'priority_levels': {
                        'high': 0.8,
                        'medium': 0.6,
                        'low': 0.4
                    }
                })
        except FileNotFoundError:
            logger.warning("config.json not found, using default configuration")
            return {
                'max_history': 100,
                'cooldown': 300,
                'priority_levels': {
                    'high': 0.8,
                    'medium': 0.6,
                    'low': 0.4
                }
            }
    
    @commands.group(name='notifications')
    async def notifications_group(self, ctx):
        """Notifications command group."""
        if ctx.invoked_subcommand is None:
            await ctx.send(
                "Available notification commands:\n"
                "`!notifications setup` - Set up notification channel\n"
                "`!notifications history` - View notification history\n"
                "`!notifications settings` - Configure notification settings"
            )
    
    @notifications_group.command(name='setup')
    async def setup_channel(self, ctx):
        """Set up a notification channel."""
        try:
            # Create or get notification channel
            channel = discord.utils.get(ctx.guild.channels, name='atena-notifications')
            if not channel:
                channel = await ctx.guild.create_text_channel('atena-notifications')
            
            # Store channel ID
            self.notification_channels[ctx.guild.id] = channel.id
            
            # Initialize history for guild
            if ctx.guild.id not in self.notification_history:
                self.notification_history[ctx.guild.id] = []
            
            await ctx.send(f"✅ Notification channel set up: {channel.mention}")
            
        except Exception as e:
            logger.error(f"Error setting up notification channel: {e}")
            await ctx.send("Failed to set up notification channel.")
    
    @notifications_group.command(name='history')
    async def show_history(self, ctx):
        """Show notification history."""
        try:
            history = self.notification_history.get(ctx.guild.id, [])
            
            if not history:
                await ctx.send("No notification history found.")
                return
            
            # Create embed
            embed = discord.Embed(
                title="Notification History",
                description=f"Last {len(history)} notifications",
                color=discord.Color.blue()
            )
            
            # Add recent notifications
            for notif in history[-10:]:  # Show last 10
                priority = self._get_priority_level(notif['priority'])
                embed.add_field(
                    name=f"{priority['emoji']} {notif['title']}",
                    value=f"Priority: {priority['name']}\n"
                          f"Time: {notif['timestamp'].strftime('%Y-%m-%d %H:%M')}\n"
                          f"{notif['message']}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing notification history: {e}")
            await ctx.send("Failed to retrieve notification history.")
    
    @notifications_group.command(name='settings')
    async def show_settings(self, ctx):
        """Show current notification settings."""
        try:
            embed = discord.Embed(
                title="Notification Settings",
                color=discord.Color.green()
            )
            
            # Add settings
            embed.add_field(
                name="Priority Levels",
                value="\n".join(
                    f"• {level}: {threshold:.1%}"
                    for level, threshold in self.config['priority_levels'].items()
                ),
                inline=False
            )
            
            embed.add_field(
                name="Cooldown",
                value=f"{self.config['cooldown']} seconds",
                inline=True
            )
            
            embed.add_field(
                name="Max History",
                value=str(self.config['max_history']),
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing settings: {e}")
            await ctx.send("Failed to retrieve notification settings.")
    
    async def send_notification(
        self,
        guild_id: int,
        title: str,
        message: str,
        priority: float = 0.5,
        category: str = "general"
    ):
        """Send a notification to the specified guild."""
        try:
            # Check cooldown
            if not await self._check_cooldown(guild_id):
                return
            
            # Get notification channel
            channel_id = self.notification_channels.get(guild_id)
            if not channel_id:
                return
            
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return
            
            # Create notification
            notification = {
                'title': title,
                'message': message,
                'priority': priority,
                'category': category,
                'timestamp': datetime.now()
            }
            
            # Add to history
            if guild_id not in self.notification_history:
                self.notification_history[guild_id] = []
            
            self.notification_history[guild_id].append(notification)
            
            # Keep history within limit
            if len(self.notification_history[guild_id]) > self.config['max_history']:
                self.notification_history[guild_id] = self.notification_history[guild_id][-self.config['max_history']:]
            
            # Get priority level
            priority_info = self._get_priority_level(priority)
            
            # Create embed
            embed = discord.Embed(
                title=f"{priority_info['emoji']} {title}",
                description=message,
                color=priority_info['color'],
                timestamp=notification['timestamp']
            )
            
            embed.add_field(
                name="Priority",
                value=priority_info['name'],
                inline=True
            )
            
            embed.add_field(
                name="Category",
                value=category.title(),
                inline=True
            )
            
            # Send notification
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    def _get_priority_level(self, priority: float) -> Dict[str, Any]:
        """Get priority level information."""
        if priority >= self.config['priority_levels']['high']:
            return {
                'name': 'High',
                'emoji': '🔴',
                'color': discord.Color.red()
            }
        elif priority >= self.config['priority_levels']['medium']:
            return {
                'name': 'Medium',
                'emoji': '🟡',
                'color': discord.Color.gold()
            }
        else:
            return {
                'name': 'Low',
                'emoji': '🟢',
                'color': discord.Color.green()
            }
    
    async def _check_cooldown(self, guild_id: int) -> bool:
        """Check if enough time has passed since last notification."""
        try:
            history = self.notification_history.get(guild_id, [])
            if not history:
                return True
            
            last_notif = history[-1]
            time_since = (datetime.now() - last_notif['timestamp']).total_seconds()
            
            return time_since >= self.config['cooldown']
            
        except Exception as e:
            logger.error(f"Error checking cooldown: {e}")
            return True
    
    async def start_monitoring(self):
        """Start monitoring for notifications."""
        try:
            # Monitor business opportunities
            self.notification_tasks['opportunities'] = asyncio.create_task(
                self._monitor_opportunities()
            )
            
            # Monitor system health
            self.notification_tasks['health'] = asyncio.create_task(
                self._monitor_health()
            )
            
        except Exception as e:
            logger.error(f"Error starting monitoring: {e}")
    
    async def _monitor_opportunities(self):
        """Monitor for business opportunities."""
        while True:
            try:
                # Get business module
                business_cog = self.bot.get_cog('BusinessIntelligence')
                if not business_cog:
                    continue
                
                # Check for opportunities
                opportunities = await business_cog.check_opportunities()
                
                # Send notifications for high-priority opportunities
                for opp in opportunities:
                    if opp['score'] >= self.config['priority_levels']['high']:
                        for guild_id in self.notification_channels:
                            await self.send_notification(
                                guild_id=guild_id,
                                title="New Business Opportunity",
                                message=f"Company: {opp['company']}\n"
                                       f"Industry: {opp['industry']}\n"
                                       f"Score: {opp['score']:.2f}\n"
                                       f"Details: {opp['description']}",
                                priority=opp['score'],
                                category="business"
                            )
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error monitoring opportunities: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_health(self):
        """Monitor system health."""
        while True:
            try:
                # Get meta agent
                meta_cog = self.bot.get_cog('MetaAgent')
                if not meta_cog:
                    continue
                
                # Check health
                health = await meta_cog.check_health()
                
                # Send notification if health is poor
                if health['status'] != 'healthy':
                    for guild_id in self.notification_channels:
                        await self.send_notification(
                            guild_id=guild_id,
                            title="System Health Alert",
                            message=f"Status: {health['status']}\n"
                                   f"Details: {health['message']}",
                            priority=0.9,  # High priority for health issues
                            category="system"
                        )
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error monitoring health: {e}")
                await asyncio.sleep(60)

def setup(bot):
    """Set up the Notifications cog."""
    bot.add_cog(Notifications(bot)) 