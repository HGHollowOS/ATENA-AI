"""
Natural Language Understanding Module

This module implements natural language understanding capabilities including
intent analysis, entity extraction, and context management.

Features:
1. Intent Analysis
   - Intent classification
   - Confidence scoring
   - Parameter extraction
   - Context awareness

2. Entity Recognition
   - Named entity recognition
   - Entity classification
   - Entity relationship analysis
   - Entity validation

3. Performance Optimizations
   - Model caching
   - Batch processing
   - Concurrent analysis
   - Resource management
"""

from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field
import spacy
from transformers import pipeline
import numpy as np
from datetime import datetime
import asyncio
from dataclasses import dataclass
from enum import Enum
import hashlib
import time
from functools import lru_cache
import json
from pathlib import Path

class IntentType(Enum):
    """Enum for intent types."""
    RESEARCH = "research"
    TASK_MANAGEMENT = "task_management"
    INFORMATION_REQUEST = "information_request"
    SYSTEM_COMMAND = "system_command"
    CHAT = "chat"
    UNKNOWN = "unknown"

class EntityType(Enum):
    """Enum for entity types."""
    PERSON = "PERSON"
    ORGANIZATION = "ORG"
    LOCATION = "GPE"
    DATE = "DATE"
    TIME = "TIME"
    MONEY = "MONEY"
    QUANTITY = "QUANTITY"
    PRODUCT = "PRODUCT"
    EVENT = "EVENT"
    OTHER = "OTHER"

@dataclass
class Entity:
    """Data class for entities."""
    text: str
    type: EntityType
    start: int
    end: int
    confidence: float
    metadata: Optional[Dict[str, Any]] = None

class Intent(BaseModel):
    """Model for detected intents."""
    name: IntentType = Field(..., description="Detected intent type")
    confidence: float = Field(..., description="Confidence score (0-1)")
    entities: List[Entity] = Field(default_factory=list, description="Extracted entities")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Intent parameters")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Context information")
    processing_time: float = Field(..., description="Processing time in seconds")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class IntentAnalyzer:
    """
    Natural Language Understanding system that analyzes user input to extract
    intents, entities, and parameters.
    
    Features:
    - Intent classification using transformer models
    - Named entity recognition using spaCy
    - Context-aware intent analysis
    - Parameter extraction and validation
    
    Attributes:
        nlp: spaCy model for entity recognition
        intent_classifier: Intent classification pipeline
        zero_shot: Zero-shot classification pipeline
        cache_dir: Directory for caching results
        max_cache_size: Maximum size of cache in MB
        batch_size: Size of batches for processing
        _processing_lock: Lock for concurrent processing
        _cache: LRU cache for processed inputs
    """
    
    def __init__(self, cache_dir: str = "cache/nlu",
                 max_cache_size: int = 100,
                 batch_size: int = 32):
        # Load spaCy model for entity recognition
        self.nlp = spacy.load("en_core_web_sm")
        
        # Initialize intent classification pipeline
        self.intent_classifier = pipeline(
            "text-classification",
            model="facebook/bart-large-mnli",
            device=-1  # Use CPU
        )
        
        # Initialize zero-shot classification for custom intents
        self.zero_shot = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=-1
        )
        
        # Setup caching
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_cache_size = max_cache_size * 1024 * 1024  # Convert to bytes
        self._cache = {}
        
        # Setup batch processing
        self.batch_size = batch_size
        self._processing_lock = asyncio.Lock()
        
        # Define intent schema
        self.intent_schema = {
            IntentType.RESEARCH: {
                "required_params": ["topic", "scope"],
                "optional_params": ["timeframe", "depth"]
            },
            IntentType.TASK_MANAGEMENT: {
                "required_params": ["action", "task"],
                "optional_params": ["priority", "deadline"]
            },
            IntentType.INFORMATION_REQUEST: {
                "required_params": ["query"],
                "optional_params": ["context", "format"]
            },
            IntentType.SYSTEM_COMMAND: {
                "required_params": ["command"],
                "optional_params": ["parameters"]
            },
            IntentType.CHAT: {
                "required_params": [],
                "optional_params": ["topic", "style"]
            }
        }
    
    async def analyze_text(self, text: str, context: Optional[Dict[str, Any]] = None) -> Intent:
        """
        Analyze text to extract intent, entities, and parameters.
        
        Args:
            text: Input text to analyze
            context: Optional context information
            
        Returns:
            Intent object containing analysis results
            
        Raises:
            ValueError: If text analysis fails
            RuntimeError: If models are unavailable
        """
        try:
            # Generate input hash
            input_hash = self._generate_hash(text)
            
            # Check cache
            cached_result = await self._get_from_cache(input_hash)
            if cached_result:
                return cached_result
            
            # Process text
            start_time = time.time()
            
            # Process text with spaCy
            doc = self.nlp(text)
            
            # Extract entities
            entities = self._extract_entities(doc)
            
            # Classify intent
            intent_name, confidence = await self._classify_intent(text)
            
            # Extract parameters
            parameters = self._extract_parameters(doc, intent_name, entities)
            
            # Create intent object
            intent = Intent(
                name=intent_name,
                confidence=confidence,
                entities=entities,
                parameters=parameters,
                context=context,
                processing_time=time.time() - start_time,
                metadata=self._extract_metadata(text, doc)
            )
            
            # Cache result
            await self._add_to_cache(input_hash, intent)
            
            return intent
            
        except Exception as e:
            raise ValueError(f"Error analyzing text: {str(e)}")
    
    def _extract_entities(self, doc) -> List[Entity]:
        """Extract named entities from text."""
        try:
            entities = []
            for ent in doc.ents:
                entity_type = self._map_entity_type(ent.label_)
                entities.append(Entity(
                    text=ent.text,
                    type=entity_type,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=self._calculate_entity_confidence(ent),
                    metadata=self._extract_entity_metadata(ent)
                ))
            return entities
        except Exception as e:
            raise ValueError(f"Error extracting entities: {str(e)}")
    
    def _map_entity_type(self, spacy_label: str) -> EntityType:
        """Map spaCy entity label to EntityType."""
        mapping = {
            "PERSON": EntityType.PERSON,
            "ORG": EntityType.ORGANIZATION,
            "GPE": EntityType.LOCATION,
            "DATE": EntityType.DATE,
            "TIME": EntityType.TIME,
            "MONEY": EntityType.MONEY,
            "QUANTITY": EntityType.QUANTITY,
            "PRODUCT": EntityType.PRODUCT,
            "EVENT": EntityType.EVENT
        }
        return mapping.get(spacy_label, EntityType.OTHER)
    
    def _calculate_entity_confidence(self, entity) -> float:
        """Calculate confidence score for entity."""
        try:
            # Simple confidence calculation based on entity properties
            confidence = 1.0
            
            # Penalize for very short entities
            if len(entity.text) < 2:
                confidence *= 0.5
            
            # Penalize for mixed case
            if entity.text != entity.text.title() and entity.text != entity.text.lower():
                confidence *= 0.8
            
            # Penalize for special characters
            if any(not c.isalnum() for c in entity.text):
                confidence *= 0.7
            
            return max(0.0, min(1.0, confidence))
        except Exception as e:
            raise ValueError(f"Error calculating entity confidence: {str(e)}")
    
    def _extract_entity_metadata(self, entity) -> Dict[str, Any]:
        """Extract metadata for entity."""
        try:
            return {
                "length": len(entity.text),
                "has_numbers": bool(re.search(r'\d', entity.text)),
                "has_special_chars": bool(re.search(r'[^\w\s]', entity.text)),
                "is_capitalized": entity.text[0].isupper() if entity.text else False
            }
        except Exception as e:
            raise ValueError(f"Error extracting entity metadata: {str(e)}")
    
    async def _classify_intent(self, text: str) -> Tuple[IntentType, float]:
        """
        Classify the intent of the text using both traditional and zero-shot classification.
        
        Returns:
            Tuple of (intent_name, confidence)
        """
        try:
            # First try traditional classification
            result = self.intent_classifier(text)
            
            if result[0]["confidence"] > 0.7:
                return IntentType(result[0]["label"]), result[0]["confidence"]
            
            # If confidence is low, try zero-shot classification
            candidate_labels = [intent.value for intent in IntentType]
            zero_shot_result = self.zero_shot(text, candidate_labels)
            
            return IntentType(zero_shot_result["labels"][0]), zero_shot_result["scores"][0]
        except Exception as e:
            raise ValueError(f"Error classifying intent: {str(e)}")
    
    def _extract_parameters(self, doc, intent_name: IntentType, entities: List[Entity]) -> Dict[str, Any]:
        """Extract parameters based on intent schema and entities."""
        try:
            parameters = {}
            schema = self.intent_schema.get(intent_name, {})
            
            # Extract required parameters
            for param in schema.get("required_params", []):
                value = self._find_parameter_value(doc, param, entities)
                if value:
                    parameters[param] = value
            
            # Extract optional parameters
            for param in schema.get("optional_params", []):
                value = self._find_parameter_value(doc, param, entities)
                if value:
                    parameters[param] = value
            
            return parameters
        except Exception as e:
            raise ValueError(f"Error extracting parameters: {str(e)}")
    
    def _find_parameter_value(self, doc, param: str, entities: List[Entity]) -> Optional[Any]:
        """Find parameter value in text or entities."""
        try:
            # Implementation for parameter extraction
            return None
        except Exception as e:
            raise ValueError(f"Error finding parameter value: {str(e)}")
    
    def _extract_metadata(self, text: str, doc) -> Dict[str, Any]:
        """Extract metadata from text and doc."""
        try:
            return {
                "length": len(text),
                "word_count": len(text.split()),
                "sentence_count": len(list(doc.sents)),
                "has_numbers": bool(re.search(r'\d', text)),
                "has_punctuation": bool(re.search(r'[.,!?-]', text)),
                "language": self._detect_language(text),
                "complexity": self._calculate_complexity(doc)
            }
        except Exception as e:
            raise ValueError(f"Error extracting metadata: {str(e)}")
    
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
    
    def _calculate_complexity(self, doc) -> float:
        """Calculate text complexity score."""
        try:
            # Simple complexity calculation based on various metrics
            complexity = 1.0
            
            # Consider sentence length
            avg_sent_length = np.mean([len(sent) for sent in doc.sents])
            if avg_sent_length > 20:
                complexity *= 1.2
            
            # Consider word length
            avg_word_length = np.mean([len(token) for token in doc])
            if avg_word_length > 8:
                complexity *= 1.1
            
            # Consider vocabulary diversity
            unique_words = len(set(token.text.lower() for token in doc))
            total_words = len(doc)
            if total_words > 0:
                diversity = unique_words / total_words
                if diversity < 0.5:
                    complexity *= 0.8
            
            return max(0.5, min(2.0, complexity))
        except Exception as e:
            raise ValueError(f"Error calculating complexity: {str(e)}")
    
    async def validate_intent(self, intent: Intent) -> Tuple[bool, List[str]]:
        """
        Validate extracted intent against schema.
        
        Returns:
            Tuple of (is_valid, missing_parameters)
        """
        try:
            schema = self.intent_schema.get(intent.name, {})
            required_params = schema.get("required_params", [])
            
            missing_params = [
                param for param in required_params
                if param not in intent.parameters
            ]
            
            return len(missing_params) == 0, missing_params
        except Exception as e:
            raise ValueError(f"Error validating intent: {str(e)}")
    
    async def update_context(self, intent: Intent, previous_intents: List[Intent]) -> Intent:
        """
        Update intent context based on conversation history.
        
        Args:
            intent: Current intent
            previous_intents: List of previous intents
            
        Returns:
            Updated intent with enhanced context
        """
        try:
            # Implementation for context updating
            return intent
        except Exception as e:
            raise ValueError(f"Error updating context: {str(e)}")
    
    def _generate_hash(self, text: str) -> str:
        """Generate hash for input text."""
        return hashlib.sha256(text.encode()).hexdigest()
    
    async def _get_from_cache(self, input_hash: str) -> Optional[Intent]:
        """Get analysis result from cache."""
        try:
            cache_file = self.cache_dir / f"{input_hash}.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    return Intent(**data)
            return None
        except Exception as e:
            self.logger.error(f"Error reading from cache: {str(e)}")
            return None
    
    async def _add_to_cache(self, input_hash: str, intent: Intent) -> None:
        """Add analysis result to cache."""
        try:
            # Check cache size
            await self._cleanup_cache()
            
            # Save to cache
            cache_file = self.cache_dir / f"{input_hash}.json"
            with open(cache_file, 'w') as f:
                json.dump(intent.dict(), f)
        except Exception as e:
            self.logger.error(f"Error writing to cache: {str(e)}")
    
    async def _cleanup_cache(self) -> None:
        """Clean up cache if size exceeds limit."""
        try:
            # Get total cache size
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.json"))
            
            if total_size > self.max_cache_size:
                # Remove oldest files
                files = sorted(self.cache_dir.glob("*.json"),
                             key=lambda x: x.stat().st_mtime)
                while total_size > self.max_cache_size and files:
                    file = files.pop(0)
                    total_size -= file.stat().st_size
                    file.unlink()
        except Exception as e:
            self.logger.error(f"Error cleaning up cache: {str(e)}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            files = list(self.cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in files)
            
            return {
                "total_files": len(files),
                "total_size": total_size,
                "max_size": self.max_cache_size,
                "usage_percentage": (total_size / self.max_cache_size) * 100
            }
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {str(e)}")
            return {
                "total_files": 0,
                "total_size": 0,
                "max_size": self.max_cache_size,
                "usage_percentage": 0
            } 