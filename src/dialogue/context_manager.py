"""
Dialogue Management Module

This module implements dialogue management functionality including context tracking,
conversation flow control, and multi-turn dialogue handling.

Features:
1. Context Management
   - Multi-turn dialogue tracking
   - Context window management
   - Topic tracking
   - State management

2. Dialogue Analysis
   - Turn analysis
   - Topic analysis
   - Participant analysis
   - Sentiment analysis

3. Performance Optimizations
   - Dialogue caching
   - Efficient storage
   - Concurrent processing
   - Resource management
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
import json
import asyncio
from dataclasses import dataclass
from enum import Enum
import hashlib
import time
from pathlib import Path
import numpy as np
from collections import defaultdict
import re

class DialogueState(Enum):
    """Enum for dialogue states."""
    INITIAL = "initial"
    ACTIVE = "active"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"

class DialogueType(Enum):
    """Enum for dialogue types."""
    CHAT = "chat"
    TASK = "task"
    Q&A = "qa"
    COMMAND = "command"
    OTHER = "other"

@dataclass
class TurnMetadata:
    """Data class for turn metadata."""
    processing_time: float
    sentiment_score: float
    topic_confidence: float
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None

class DialogueTurn(BaseModel):
    """Model for a single turn in a dialogue."""
    timestamp: datetime = Field(..., description="Turn timestamp")
    speaker: str = Field(..., description="Speaker identifier")
    text: str = Field(..., description="Turn text")
    intent: Optional[Dict[str, Any]] = Field(default=None, description="Detected intent")
    entities: Optional[List[Dict[str, Any]]] = Field(default=None, description="Extracted entities")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    turn_metadata: Optional[TurnMetadata] = None
    processing_time: float = Field(..., description="Processing time in seconds")
    hash: str = Field(..., description="Hash of turn content")

class DialogueContext:
    """
    Dialogue management system that maintains conversation context and controls
    conversation flow.
    
    Features:
    - Multi-turn dialogue tracking
    - Context window management
    - Topic tracking
    - Conversation state management
    
    Attributes:
        max_context_turns: Maximum number of turns to keep in context
        turns: List of dialogue turns
        current_topic: Current conversation topic
        state: Current dialogue state
        metadata: Dialogue metadata
        cache_dir: Directory for caching dialogues
        max_cache_size: Maximum size of cache in MB
        _processing_lock: Lock for concurrent processing
        _cache: LRU cache for processed turns
    """
    
    def __init__(self, max_context_turns: int = 10,
                 cache_dir: str = "cache/dialogue",
                 max_cache_size: int = 100):
        self.max_context_turns = max_context_turns
        self.turns: List[DialogueTurn] = []
        self.current_topic: Optional[str] = None
        self.state: DialogueState = DialogueState.INITIAL
        self.metadata: Dict[str, Any] = {
            "start_time": datetime.now(),
            "participants": set(),
            "topics": set(),
            "dialogue_type": DialogueType.CHAT,
            "turn_count": 0,
            "total_duration": 0.0
        }
        
        # Setup caching
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_cache_size = max_cache_size * 1024 * 1024  # Convert to bytes
        self._cache = {}
        
        # Setup processing
        self._processing_lock = asyncio.Lock()
        self._topic_history: List[Tuple[str, float]] = []
        self._sentiment_history: List[float] = []
    
    def add_turn(self, speaker: str, text: str, intent: Optional[Dict[str, Any]] = None,
                 entities: Optional[List[Dict[str, Any]]] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a new turn to the dialogue.
        
        Args:
            speaker: Speaker identifier
            text: Spoken text
            intent: Detected intent
            entities: Extracted entities
            metadata: Additional metadata
            
        Raises:
            ValueError: If turn addition fails
        """
        try:
            start_time = time.time()
            
            # Generate turn hash
            turn_hash = self._generate_hash(f"{speaker}:{text}")
            
            # Process turn
            turn_metadata = self._process_turn(text, intent, entities)
            
            # Create turn
            turn = DialogueTurn(
                timestamp=datetime.now(),
                speaker=speaker,
                text=text,
                intent=intent,
                entities=entities,
                metadata=metadata,
                turn_metadata=turn_metadata,
                processing_time=time.time() - start_time,
                hash=turn_hash
            )
            
            # Add turn to dialogue
            self.turns.append(turn)
            self.metadata["participants"].add(speaker)
            self.metadata["turn_count"] += 1
            
            # Update context window
            if len(self.turns) > self.max_context_turns:
                self.turns.pop(0)
            
            # Update topic if available
            if intent and "topic" in intent.get("parameters", {}):
                self.current_topic = intent["parameters"]["topic"]
                self.metadata["topics"].add(self.current_topic)
                self._topic_history.append((self.current_topic, time.time()))
            
            # Update sentiment history
            if turn_metadata:
                self._sentiment_history.append(turn_metadata.sentiment_score)
            
            # Update total duration
            self.metadata["total_duration"] = (
                datetime.now() - self.metadata["start_time"]
            ).total_seconds()
            
            # Update state
            self._update_state()
            
        except Exception as e:
            raise ValueError(f"Error adding turn: {str(e)}")
    
    def _process_turn(self, text: str, intent: Optional[Dict[str, Any]],
                     entities: Optional[List[Dict[str, Any]]]) -> TurnMetadata:
        """Process turn to extract metadata."""
        try:
            # Calculate sentiment score
            sentiment_score = self._calculate_sentiment(text)
            
            # Calculate topic confidence
            topic_confidence = self._calculate_topic_confidence(text, intent)
            
            # Extract additional metadata
            metadata = {
                "length": len(text),
                "word_count": len(text.split()),
                "has_entities": bool(entities),
                "has_intent": bool(intent),
                "language": self._detect_language(text)
            }
            
            return TurnMetadata(
                processing_time=0.0,  # Will be updated by caller
                sentiment_score=sentiment_score,
                topic_confidence=topic_confidence,
                timestamp=time.time(),
                metadata=metadata
            )
        except Exception as e:
            raise ValueError(f"Error processing turn: {str(e)}")
    
    def _calculate_sentiment(self, text: str) -> float:
        """Calculate sentiment score for text."""
        try:
            # Simple sentiment calculation based on word patterns
            positive_words = {"good", "great", "excellent", "happy", "love", "like"}
            negative_words = {"bad", "terrible", "awful", "hate", "dislike", "poor"}
            
            words = set(text.lower().split())
            positive_count = len(words & positive_words)
            negative_count = len(words & negative_words)
            
            if positive_count + negative_count == 0:
                return 0.0
            
            return (positive_count - negative_count) / (positive_count + negative_count)
        except Exception as e:
            raise ValueError(f"Error calculating sentiment: {str(e)}")
    
    def _calculate_topic_confidence(self, text: str, intent: Optional[Dict[str, Any]]) -> float:
        """Calculate confidence in topic detection."""
        try:
            confidence = 1.0
            
            # Penalize for very short text
            if len(text) < 10:
                confidence *= 0.8
            
            # Penalize for no intent
            if not intent:
                confidence *= 0.7
            
            # Penalize for mixed topics
            if intent and "topic" in intent.get("parameters", {}):
                topic = intent["parameters"]["topic"]
                if topic != self.current_topic:
                    confidence *= 0.6
            
            return max(0.0, min(1.0, confidence))
        except Exception as e:
            raise ValueError(f"Error calculating topic confidence: {str(e)}")
    
    def _detect_language(self, text: str) -> str:
        """Detect the language of the text."""
        try:
            # Simple language detection based on character sets
            if re.search(r'[\u4e00-\u9fff]', text):
                return 'zh'
            elif re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
                return 'ja'
            elif re.search(r'[\uac00-\ud7af]', text):
                return 'ko'
            elif re.search(r'[а-яА-Я]', text):
                return 'ru'
            else:
                return 'en'
        except Exception as e:
            raise ValueError(f"Error detecting language: {str(e)}")
    
    def _update_state(self) -> None:
        """Update dialogue state based on current conditions."""
        try:
            if not self.turns:
                self.state = DialogueState.INITIAL
            elif self.state == DialogueState.INITIAL:
                self.state = DialogueState.ACTIVE
            elif self.state == DialogueState.ACTIVE:
                # Check if waiting for response
                last_turn = self.turns[-1]
                if last_turn.intent and "requires_response" in last_turn.intent:
                    self.state = DialogueState.WAITING
            elif self.state == DialogueState.WAITING:
                # Check if response received
                if len(self.turns) > 1:
                    last_turn = self.turns[-1]
                    prev_turn = self.turns[-2]
                    if last_turn.speaker != prev_turn.speaker:
                        self.state = DialogueState.ACTIVE
        except Exception as e:
            raise ValueError(f"Error updating state: {str(e)}")
    
    def get_recent_turns(self, n: int = 5) -> List[DialogueTurn]:
        """
        Get the n most recent turns.
        
        Args:
            n: Number of turns to retrieve
            
        Returns:
            List of recent turns
        """
        return self.turns[-n:]
    
    def get_context_window(self) -> List[DialogueTurn]:
        """
        Get the current context window.
        
        Returns:
            List of turns in the context window
        """
        return self.turns
    
    def get_current_topic(self) -> Optional[str]:
        """Get the current conversation topic."""
        return self.current_topic
    
    def get_participants(self) -> List[str]:
        """Get list of conversation participants."""
        return list(self.metadata["participants"])
    
    def get_topics(self) -> List[str]:
        """Get list of discussed topics."""
        return list(self.metadata["topics"])
    
    def update_state(self, key: str, value: Any) -> None:
        """
        Update the conversation state.
        
        Args:
            key: State key
            value: State value
            
        Raises:
            ValueError: If state update fails
        """
        try:
            self.state[key] = value
        except Exception as e:
            raise ValueError(f"Error updating state: {str(e)}")
    
    def get_state(self, key: str) -> Optional[Any]:
        """
        Get a value from the conversation state.
        
        Args:
            key: State key
            
        Returns:
            State value if found, None otherwise
        """
        return self.state.get(key)
    
    def clear_state(self) -> None:
        """Clear the conversation state."""
        self.state.clear()
    
    def get_dialogue_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the dialogue.
        
        Returns:
            Dictionary containing dialogue summary
        """
        try:
            return {
                "duration": self.metadata["total_duration"],
                "turns": self.metadata["turn_count"],
                "participants": list(self.metadata["participants"]),
                "topics": list(self.metadata["topics"]),
                "current_topic": self.current_topic,
                "state": self.state,
                "sentiment": self._calculate_average_sentiment(),
                "topic_confidence": self._calculate_average_topic_confidence()
            }
        except Exception as e:
            raise ValueError(f"Error getting dialogue summary: {str(e)}")
    
    def _calculate_average_sentiment(self) -> float:
        """Calculate average sentiment score."""
        try:
            if not self._sentiment_history:
                return 0.0
            return sum(self._sentiment_history) / len(self._sentiment_history)
        except Exception as e:
            raise ValueError(f"Error calculating average sentiment: {str(e)}")
    
    def _calculate_average_topic_confidence(self) -> float:
        """Calculate average topic confidence."""
        try:
            if not self._topic_history:
                return 0.0
            return sum(conf for _, conf in self._topic_history) / len(self._topic_history)
        except Exception as e:
            raise ValueError(f"Error calculating average topic confidence: {str(e)}")
    
    def export_dialogue(self) -> Dict[str, Any]:
        """
        Export the complete dialogue history.
        
        Returns:
            Dictionary containing complete dialogue data
        """
        try:
            return {
                "turns": [turn.dict() for turn in self.turns],
                "metadata": self.metadata,
                "state": self.state,
                "current_topic": self.current_topic,
                "sentiment_history": self._sentiment_history,
                "topic_history": self._topic_history
            }
        except Exception as e:
            raise ValueError(f"Error exporting dialogue: {str(e)}")
    
    def load_dialogue(self, data: Dict[str, Any]) -> None:
        """
        Load dialogue data from a dictionary.
        
        Args:
            data: Dialogue data to load
            
        Raises:
            ValueError: If dialogue loading fails
        """
        try:
            self.turns = [DialogueTurn(**turn) for turn in data["turns"]]
            self.metadata = data["metadata"]
            self.state = data["state"]
            self.current_topic = data["current_topic"]
            self._sentiment_history = data.get("sentiment_history", [])
            self._topic_history = data.get("topic_history", [])
        except Exception as e:
            raise ValueError(f"Error loading dialogue: {str(e)}")
    
    def save_to_file(self, filepath: str) -> None:
        """
        Save dialogue to a file.
        
        Args:
            filepath: Path to save the dialogue
            
        Raises:
            ValueError: If file saving fails
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(self.export_dialogue(), f, default=str)
        except Exception as e:
            raise ValueError(f"Error saving dialogue to file: {str(e)}")
    
    def load_from_file(self, filepath: str) -> None:
        """
        Load dialogue from a file.
        
        Args:
            filepath: Path to load the dialogue from
            
        Raises:
            ValueError: If file loading fails
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                self.load_dialogue(data)
        except Exception as e:
            raise ValueError(f"Error loading dialogue from file: {str(e)}")
    
    def reset(self) -> None:
        """Reset the dialogue context."""
        self.turns.clear()
        self.current_topic = None
        self.state.clear()
        self.metadata = {
            "start_time": datetime.now(),
            "participants": set(),
            "topics": set(),
            "dialogue_type": DialogueType.CHAT,
            "turn_count": 0,
            "total_duration": 0.0
        }
        self._topic_history.clear()
        self._sentiment_history.clear()
    
    def _generate_hash(self, text: str) -> str:
        """Generate hash for text."""
        return hashlib.sha256(text.encode()).hexdigest() 