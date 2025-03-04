"""
Enhanced Discord bot module for ATENA-AI business assistant.
Provides natural conversation, proactive notifications, and business intelligence features.
"""

import discord
from discord.ext import commands, tasks
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ATENADiscordBot(commands.Bot):
    """Enhanced Discord bot for ATENA-AI business assistant."""
    
    def __init__(self):
        """Initialize the Discord bot with enhanced features."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            case_insensitive=True
        )
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize state
        self.conversation_contexts: Dict[int, Dict[str, Any]] = {}
        self.notification_channels: Dict[int, int] = {}
        self.proactive_tasks: List[asyncio.Task] = []
        
        # Load cogs
        self._load_cogs()
        
        # Start background tasks
        self.background_tasks.start()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load bot configuration from config.json."""
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("config.json not found, using default configuration")
            return {
                "proactive_check_interval": 3600,  # 1 hour
                "notification_threshold": 0.8,
                "max_conversation_history": 10,
                "command_cooldown": 3
            }
    
    def _load_cogs(self):
        """Load all bot cogs."""
        cogs = [
            'src.discord_bot.cogs.business_intelligence',
            'src.discord_bot.cogs.conversation',
            'src.discord_bot.cogs.notifications',
            'src.discord_bot.cogs.admin'
        ]
        
        for cog in cogs:
            try:
                self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")
    
    async def on_ready(self):
        """Handle bot ready event."""
        logger.info(f"Logged in as {self.user.name} ({self.user.id})")
        
        # Set up notification channels
        await self._setup_notification_channels()
        
        # Start proactive monitoring
        self.start_proactive_monitoring()
    
    async def _setup_notification_channels(self):
        """Set up notification channels for each guild."""
        for guild in self.guilds:
            # Create or get notification channel
            channel = discord.utils.get(guild.channels, name='atena-notifications')
            if not channel:
                channel = await guild.create_text_channel('atena-notifications')
            
            self.notification_channels[guild.id] = channel.id
    
    @tasks.loop(minutes=5)
    async def background_tasks(self):
        """Run background tasks."""
        try:
            # Update conversation contexts
            await self._cleanup_old_contexts()
            
            # Check for new business opportunities
            await self._check_business_opportunities()
            
            # Update system status
            await self._update_status()
            
        except Exception as e:
            logger.error(f"Error in background tasks: {e}")
    
    async def _cleanup_old_contexts(self):
        """Clean up old conversation contexts."""
        current_time = datetime.now()
        for user_id, context in list(self.conversation_contexts.items()):
            if (current_time - context['last_updated']).seconds > 3600:  # 1 hour
                del self.conversation_contexts[user_id]
    
    async def _check_business_opportunities(self):
        """Check for new business opportunities."""
        for guild_id, channel_id in self.notification_channels.items():
            try:
                # Get business module
                business_cog = self.get_cog('BusinessIntelligence')
                if not business_cog:
                    continue
                
                # Check for opportunities
                opportunities = await business_cog.check_opportunities()
                
                # Send notifications for high-priority opportunities
                for opp in opportunities:
                    if opp['priority'] >= self.config['notification_threshold']:
                        channel = self.get_channel(channel_id)
                        if channel:
                            await channel.send(
                                f"🔔 **New Business Opportunity**\n"
                                f"Company: {opp['company']}\n"
                                f"Type: {opp['type']}\n"
                                f"Priority: {opp['priority']}\n"
                                f"Details: {opp['description']}"
                            )
                
            except Exception as e:
                logger.error(f"Error checking opportunities for guild {guild_id}: {e}")
    
    async def _update_status(self):
        """Update bot status with current metrics."""
        try:
            # Get metrics from meta agent
            meta_cog = self.get_cog('MetaAgent')
            if not meta_cog:
                return
            
            metrics = await meta_cog.get_metrics()
            
            # Update status with key metrics
            status = f"Monitoring {len(self.guilds)} servers | {metrics['active_conversations']} conversations"
            await self.change_presence(activity=discord.Game(name=status))
            
        except Exception as e:
            logger.error(f"Error updating status: {e}")
    
    async def on_message(self, message):
        """Handle incoming messages."""
        if message.author == self.user:
            return
        
        # Process commands
        await self.process_commands(message)
        
        # Handle mentions
        if self.user.mentioned_in(message):
            await self._handle_mention(message)
    
    async def _handle_mention(self, message):
        """Handle bot mentions with natural conversation."""
        try:
            # Get or create conversation context
            context = self.conversation_contexts.get(message.author.id, {
                'history': [],
                'last_updated': datetime.now()
            })
            
            # Update context
            context['last_updated'] = datetime.now()
            context['history'].append({
                'role': 'user',
                'content': message.content
            })
            
            # Keep history within limit
            if len(context['history']) > self.config['max_conversation_history']:
                context['history'] = context['history'][-self.config['max_conversation_history']:]
            
            # Get response from dialogue manager
            dialogue_cog = self.get_cog('DialogueManager')
            if not dialogue_cog:
                await message.reply("I'm having trouble processing your request right now.")
                return
            
            response = await dialogue_cog.generate_response(
                message.content,
                context['history']
            )
            
            # Update context with response
            context['history'].append({
                'role': 'assistant',
                'content': response
            })
            
            # Save updated context
            self.conversation_contexts[message.author.id] = context
            
            # Send response
            await message.reply(response)
            
        except Exception as e:
            logger.error(f"Error handling mention: {e}")
            await message.reply("I encountered an error while processing your request.")
    
    def start_proactive_monitoring(self):
        """Start proactive monitoring tasks."""
        # Monitor business opportunities
        self.proactive_tasks.append(
            asyncio.create_task(self._monitor_opportunities())
        )
        
        # Monitor system health
        self.proactive_tasks.append(
            asyncio.create_task(self._monitor_system_health())
        )
    
    async def _monitor_opportunities(self):
        """Monitor for business opportunities."""
        while True:
            try:
                await self._check_business_opportunities()
                await asyncio.sleep(self.config['proactive_check_interval'])
            except Exception as e:
                logger.error(f"Error in opportunity monitoring: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _monitor_system_health(self):
        """Monitor system health and performance."""
        while True:
            try:
                # Get health metrics
                meta_cog = self.get_cog('MetaAgent')
                if not meta_cog:
                    continue
                
                health = await meta_cog.check_health()
                
                # Alert if health is poor
                if health['status'] != 'healthy':
                    for channel_id in self.notification_channels.values():
                        channel = self.get_channel(channel_id)
                        if channel:
                            await channel.send(
                                f"⚠️ **System Health Alert**\n"
                                f"Status: {health['status']}\n"
                                f"Details: {health['message']}"
                            )
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(60)

def run_bot():
    """Run the Discord bot."""
    bot = ATENADiscordBot()
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))

if __name__ == "__main__":
    run_bot() 