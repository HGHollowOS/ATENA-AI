"""
ATENA AI Main Application

This module serves as the main entry point for the ATENA AI application,
initializing and coordinating all components.
"""

import asyncio
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from discord.ext import commands
import discord

from meta_agent.meta_agent import MetaAgent
from input_processor.input_processor import InputProcessor
from nlu.intent_analyzer import IntentAnalyzer
from dialogue.context_manager import DialogueContext
from knowledge.knowledge_base import KnowledgeBase
from logging.logger import SystemLogger
from services.external_services import ExternalServices
from executor.task_executor import TaskExecutor

# Load environment variables
load_dotenv()

class ATENA:
    """
    Main ATENA AI application class that coordinates all components.
    
    This class initializes and manages:
    - Meta-agent for system monitoring and self-improvement
    - Input processing for user interactions
    - Natural language understanding
    - Dialogue management
    - Knowledge base
    - External services integration
    - Task execution
    """
    
    def __init__(self):
        # Initialize logging
        self.logger = SystemLogger()
        self.logger.info("Initializing ATENA AI")
        
        # Initialize components
        self.meta_agent = MetaAgent()
        self.input_processor = InputProcessor()
        self.intent_analyzer = IntentAnalyzer()
        self.dialogue_context = DialogueContext()
        self.knowledge_base = KnowledgeBase()
        self.external_services = ExternalServices()
        self.task_executor = TaskExecutor()
        
        # Initialize Discord bot
        self.bot = commands.Bot(command_prefix="!atena")
        self._setup_discord_commands()
        
        # Initialize FastAPI for web interface
        self.app = FastAPI(title="ATENA AI")
        self._setup_api_routes()
        
        self.logger.info("ATENA AI initialization complete")
    
    def _setup_discord_commands(self):
        """Set up Discord bot commands."""
        @self.bot.event
        async def on_ready():
            self.logger.info(f"Discord bot logged in as {self.bot.user}")
        
        @self.bot.command(name="help")
        async def help(ctx):
            """Display help information."""
            help_text = """
            ATENA AI Commands:
            !atena help - Display this help message
            !atena status - Check system status
            !atena analyze - Request system analysis
            !atena improve - Trigger self-improvement
            """
            await ctx.send(help_text)
        
        @self.bot.command(name="status")
        async def status(ctx):
            """Check system status."""
            metrics = await self.meta_agent.gather_metrics()
            await ctx.send(f"System Status:\n{metrics}")
        
        @self.bot.command(name="analyze")
        async def analyze(ctx):
            """Request system analysis."""
            evaluation = await self.meta_agent.evaluate_performance()
            await ctx.send(f"System Analysis:\n{evaluation}")
        
        @self.bot.command(name="improve")
        async def improve(ctx):
            """Trigger self-improvement."""
            success = await self.meta_agent.trigger_improvement()
            if success:
                await ctx.send("Self-improvement completed successfully")
            else:
                await ctx.send("Self-improvement encountered issues")
    
    def _setup_api_routes(self):
        """Set up FastAPI routes."""
        @self.app.get("/")
        async def root():
            return {"status": "ATENA AI is running"}
        
        @self.app.get("/status")
        async def status():
            metrics = await self.meta_agent.gather_metrics()
            return metrics
        
        @self.app.get("/analysis")
        async def analysis():
            evaluation = await self.meta_agent.evaluate_performance()
            return evaluation
    
    async def process_input(self, text: str, speaker: str):
        """
        Process user input through the entire pipeline.
        
        Args:
            text: User input text
            speaker: Speaker identifier
        """
        try:
            # Process input
            processed_input = await self.input_processor.process(text)
            
            # Analyze intent
            intent = await self.intent_analyzer.analyze_text(processed_input)
            
            # Update dialogue context
            self.dialogue_context.add_turn(
                speaker=speaker,
                text=text,
                intent=intent.dict(),
                entities=intent.entities
            )
            
            # Execute task based on intent
            response = await self.task_executor.execute(intent)
            
            return response
        except Exception as e:
            self.logger.error(f"Error processing input: {str(e)}")
            return "I encountered an error processing your request."
    
    async def start(self):
        """Start the ATENA AI system."""
        try:
            # Start Discord bot
            discord_token = os.getenv("DISCORD_TOKEN")
            if not discord_token:
                raise ValueError("Discord token not found in environment variables")
            
            # Start FastAPI server
            import uvicorn
            config = uvicorn.Config(self.app, host="0.0.0.0", port=8000)
            server = uvicorn.Server(config)
            
            # Run both Discord bot and FastAPI server
            await asyncio.gather(
                self.bot.start(discord_token),
                server.serve()
            )
        except Exception as e:
            self.logger.error(f"Error starting ATENA AI: {str(e)}")
            raise

async def main():
    """Main entry point."""
    atena = ATENA()
    await atena.start()

if __name__ == "__main__":
    asyncio.run(main()) 