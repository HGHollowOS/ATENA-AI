"""
Dialogue Manager cog for ATENA-AI Discord bot.
Handles natural language processing, context management, and response generation.
"""

import discord
from discord.ext import commands
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
import json
from datetime import datetime
import re
from collections import defaultdict

logger = logging.getLogger(__name__)

class DialogueManager(commands.Cog):
    """Dialogue Manager cog for ATENA-AI."""
    
    def __init__(self, bot):
        """Initialize the Dialogue Manager cog."""
        self.bot = bot
        self.config = self._load_config()
        self.conversation_contexts: Dict[int, Dict[str, Any]] = {}
        self.intent_patterns: Dict[str, List[str]] = self._load_intent_patterns()
        self.response_templates: Dict[str, List[str]] = self._load_response_templates()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load dialogue manager configuration."""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                return config.get('dialogue_manager', {
                    'max_context_length': 10,
                    'context_timeout': 3600,  # 1 hour
                    'confidence_threshold': 0.7,
                    'response_timeout': 30
                })
        except FileNotFoundError:
            logger.warning("config.json not found, using default configuration")
            return {
                'max_context_length': 10,
                'context_timeout': 3600,
                'confidence_threshold': 0.7,
                'response_timeout': 30
            }
    
    def _load_intent_patterns(self) -> Dict[str, List[str]]:
        """Load intent recognition patterns."""
        return {
            'greeting': [
                r'hi|hello|hey|greetings',
                r'good (morning|afternoon|evening)',
                r'how are you'
            ],
            'business_research': [
                r'research|find|look for|search',
                r'partnership|opportunity|company',
                r'industry|market|sector'
            ],
            'company_analysis': [
                r'analyze|evaluate|assess',
                r'company|business|organization',
                r'performance|metrics|stats'
            ],
            'help_request': [
                r'help|assist|support',
                r'what can you do',
                r'capabilities|features'
            ],
            'clarification': [
                r'what do you mean',
                r'explain|clarify',
                r'could you elaborate'
            ],
            'confirmation': [
                r'yes|yeah|correct|right',
                r'confirm|verify',
                r'that\'s right'
            ],
            'negation': [
                r'no|nope|incorrect|wrong',
                r'deny|reject',
                r'that\'s not right'
            ]
        }
    
    def _load_response_templates(self) -> Dict[str, List[str]]:
        """Load response templates for different intents."""
        return {
            'greeting': [
                "Hello! I'm ATENA-AI, your business assistant. How can I help you today?",
                "Hi there! I'm ready to help with your business needs. What would you like to know?",
                "Greetings! I can assist you with business research, analysis, and more. What's on your mind?"
            ],
            'business_research': [
                "I'll help you research that. What specific industry or criteria should I focus on?",
                "I can help find business opportunities. Would you like me to start with a particular sector?",
                "I'll search for relevant information. Are there any specific requirements or preferences?"
            ],
            'company_analysis': [
                "I can analyze that company for you. What aspects would you like me to focus on?",
                "I'll evaluate the company's performance. Would you like specific metrics or a comprehensive analysis?",
                "I can assess the company's potential. What criteria should I consider?"
            ],
            'help_request': [
                "I can help you with:\n• Business research and analysis\n• Partnership opportunities\n• Company analysis\n• Industry monitoring\n\nWhat would you like to know more about?",
                "Here are my main capabilities:\n• Research business opportunities\n• Analyze companies\n• Monitor industries\n• Generate reports\n\nHow can I assist you?",
                "I'm your business intelligence assistant. I can:\n• Find partnership opportunities\n• Evaluate companies\n• Track market trends\n• Provide insights\n\nWhat would you like to explore?"
            ],
            'clarification': [
                "Let me explain that in more detail...",
                "I'll clarify that for you...",
                "Here's what I mean..."
            ],
            'confirmation': [
                "Great! I'll proceed with that.",
                "Perfect, I'll continue with your request.",
                "Excellent, I'll take care of that."
            ],
            'negation': [
                "I understand. Let me adjust my approach.",
                "I see. I'll modify my response accordingly.",
                "Understood. I'll revise my suggestion."
            ],
            'default': [
                "I understand you're asking about something. Could you please provide more details?",
                "I'm not sure I understand. Could you rephrase that?",
                "I need more information to help you effectively. Could you elaborate?"
            ]
        }
    
    async def generate_response(
        self,
        message: str,
        history: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a response based on the message and context."""
        try:
            # Get intent and confidence
            intent, confidence = self._detect_intent(message)
            
            # Update context if provided
            if context:
                context['last_intent'] = intent
                context['last_confidence'] = confidence
            
            # Get relevant response
            response = self._get_response(intent, confidence, message, history)
            
            # Add follow-up if needed
            if self._should_add_follow_up(intent, confidence):
                response += self._generate_follow_up(intent)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I encountered an error while processing your request."
    
    def _detect_intent(self, message: str) -> Tuple[str, float]:
        """Detect the intent of a message and return confidence score."""
        message = message.lower()
        max_confidence = 0.0
        detected_intent = 'default'
        
        for intent, patterns in self.intent_patterns.items():
            matches = 0
            for pattern in patterns:
                if re.search(pattern, message):
                    matches += 1
            
            if matches > 0:
                confidence = matches / len(patterns)
                if confidence > max_confidence:
                    max_confidence = confidence
                    detected_intent = intent
        
        return detected_intent, max_confidence
    
    def _get_response(
        self,
        intent: str,
        confidence: float,
        message: str,
        history: List[Dict[str, Any]]
    ) -> str:
        """Get appropriate response based on intent and confidence."""
        # Check if we have templates for this intent
        if intent not in self.response_templates:
            intent = 'default'
        
        # Get templates for this intent
        templates = self.response_templates[intent]
        
        # If confidence is low, use default response
        if confidence < self.config['confidence_threshold']:
            templates = self.response_templates['default']
        
        # Select template based on context
        template = self._select_template(templates, message, history)
        
        # Customize response if needed
        response = self._customize_response(template, message, history)
        
        return response
    
    def _select_template(
        self,
        templates: List[str],
        message: str,
        history: List[Dict[str, Any]]
    ) -> str:
        """Select the most appropriate response template."""
        # Simple round-robin selection for now
        # Could be enhanced with more sophisticated selection logic
        return templates[0]
    
    def _customize_response(
        self,
        template: str,
        message: str,
        history: List[Dict[str, Any]]
    ) -> str:
        """Customize the response template based on context."""
        # Extract relevant information from message
        company_match = re.search(r'company\s+(\w+)', message.lower())
        industry_match = re.search(r'industry\s+(\w+)', message.lower())
        
        # Replace placeholders if found
        if company_match:
            template = template.replace('{company}', company_match.group(1))
        if industry_match:
            template = template.replace('{industry}', industry_match.group(1))
        
        return template
    
    def _should_add_follow_up(self, intent: str, confidence: float) -> bool:
        """Determine if a follow-up question should be added."""
        return (
            intent in ['business_research', 'company_analysis'] and
            confidence >= self.config['confidence_threshold']
        )
    
    def _generate_follow_up(self, intent: str) -> str:
        """Generate a follow-up question based on intent."""
        follow_ups = {
            'business_research': "\nWould you like me to focus on any specific aspects or criteria?",
            'company_analysis': "\nWould you like me to include market comparison or industry benchmarks?"
        }
        return follow_ups.get(intent, "")
    
    def _update_context(
        self,
        context: Dict[str, Any],
        message: str,
        intent: str,
        confidence: float
    ):
        """Update conversation context with new information."""
        context['last_message'] = message
        context['last_intent'] = intent
        context['last_confidence'] = confidence
        context['last_updated'] = datetime.now()
        
        # Keep history within limit
        if len(context['history']) > self.config['max_context_length']:
            context['history'] = context['history'][-self.config['max_context_length']:]
    
    def _cleanup_old_contexts(self):
        """Remove expired conversation contexts."""
        current_time = datetime.now()
        for user_id, context in list(self.conversation_contexts.items()):
            if (current_time - context['last_updated']).seconds > self.config['context_timeout']:
                del self.conversation_contexts[user_id]

def setup(bot):
    """Set up the Dialogue Manager cog."""
    bot.add_cog(DialogueManager(bot)) 