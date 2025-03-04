"""
Conversation cog for ATENA-AI Discord bot.
Handles natural language interactions and dialogue management.
"""

import discord
from discord.ext import commands
import asyncio
import logging
from typing import Dict, List, Optional, Any
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class Conversation(commands.Cog):
    """Conversation cog for ATENA-AI."""
    
    def __init__(self, bot):
        """Initialize the Conversation cog."""
        self.bot = bot
        self.config = self._load_config()
        self.conversation_contexts: Dict[int, Dict[str, Any]] = {}
        self.dialogue_manager = None  # Will be initialized when needed
    
    def _load_config(self) -> Dict[str, Any]:
        """Load conversation configuration."""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                return config.get('dialogue_context', {
                    'max_history': 10,
                    'context_timeout': 3600,  # 1 hour
                    'confidence_threshold': 0.7,
                    'response_timeout': 30
                })
        except FileNotFoundError:
            logger.warning("config.json not found, using default configuration")
            return {
                'max_history': 10,
                'context_timeout': 3600,
                'confidence_threshold': 0.7,
                'response_timeout': 30
            }
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle incoming messages."""
        if message.author == self.bot.user:
            return
        
        # Check if bot is mentioned
        if not self.bot.user.mentioned_in(message):
            return
        
        try:
            # Get or create conversation context
            context = self._get_context(message.author.id)
            
            # Process message
            response = await self._process_message(message.content, context)
            
            # Send response
            await message.reply(response)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await message.reply("I encountered an error while processing your message.")
    
    def _get_context(self, user_id: int) -> Dict[str, Any]:
        """Get or create conversation context for a user."""
        if user_id not in self.conversation_contexts:
            self.conversation_contexts[user_id] = {
                'history': [],
                'last_updated': datetime.now(),
                'current_topic': None,
                'intent': None
            }
        
        context = self.conversation_contexts[user_id]
        
        # Check if context is too old
        if (datetime.now() - context['last_updated']).seconds > self.config['context_timeout']:
            context = {
                'history': [],
                'last_updated': datetime.now(),
                'current_topic': None,
                'intent': None
            }
            self.conversation_contexts[user_id] = context
        
        return context
    
    async def _process_message(self, message: str, context: Dict[str, Any]) -> str:
        """Process a message and generate a response."""
        try:
            # Update context
            context['last_updated'] = datetime.now()
            context['history'].append({
                'role': 'user',
                'content': message,
                'timestamp': datetime.now()
            })
            
            # Keep history within limit
            if len(context['history']) > self.config['max_history']:
                context['history'] = context['history'][-self.config['max_history']:]
            
            # Get dialogue manager if not initialized
            if not self.dialogue_manager:
                self.dialogue_manager = self.bot.get_cog('DialogueManager')
                if not self.dialogue_manager:
                    return "I'm having trouble processing your request right now."
            
            # Generate response
            response = await self.dialogue_manager.generate_response(
                message,
                context['history']
            )
            
            # Update context with response
            context['history'].append({
                'role': 'assistant',
                'content': response,
                'timestamp': datetime.now()
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return "I encountered an error while processing your message."
    
    @commands.command(name='clear')
    async def clear_context(self, ctx):
        """Clear the conversation context."""
        try:
            if ctx.author.id in self.conversation_contexts:
                del self.conversation_contexts[ctx.author.id]
                await ctx.send("✅ Conversation context cleared.")
            else:
                await ctx.send("No active conversation context to clear.")
        except Exception as e:
            logger.error(f"Error clearing context: {e}")
            await ctx.send("Failed to clear conversation context.")
    
    @commands.command(name='topic')
    async def show_topic(self, ctx):
        """Show the current conversation topic."""
        try:
            context = self._get_context(ctx.author.id)
            if context['current_topic']:
                await ctx.send(f"Current topic: {context['current_topic']}")
            else:
                await ctx.send("No specific topic in the current conversation.")
        except Exception as e:
            logger.error(f"Error showing topic: {e}")
            await ctx.send("Failed to retrieve conversation topic.")
    
    async def generate_response(self, message: str, history: List[Dict[str, Any]]) -> str:
        """Generate a response to a message."""
        try:
            # TODO: Implement actual response generation
            # This is a placeholder that simulates response generation
            await asyncio.sleep(0.5)
            
            # Simple response based on message content
            if 'hello' in message.lower() or 'hi' in message.lower():
                return "Hello! How can I help you today?"
            elif 'help' in message.lower():
                return (
                    "I can help you with:\n"
                    "• Business research and analysis\n"
                    "• Partnership opportunities\n"
                    "• Company analysis\n"
                    "• Industry monitoring\n\n"
                    "Just ask me what you'd like to know!"
                )
            elif 'business' in message.lower():
                return "I can help you with business-related tasks. Would you like to research partnerships, analyze companies, or monitor industries?"
            else:
                return "I understand you're asking about something. Could you please provide more details about what you'd like to know?"
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I'm having trouble generating a response right now."

def setup(bot):
    """Set up the Conversation cog."""
    bot.add_cog(Conversation(bot)) 