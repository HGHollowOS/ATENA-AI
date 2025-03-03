"""
Input Processing Module

This module handles input processing and normalization for various input types,
including text and voice input.

Features:
1. Text Processing
   - Text normalization
   - Metadata extraction
   - Language detection
   - Input validation

2. Voice Processing
   - Speech-to-text conversion
   - Text-to-speech synthesis
   - Voice property configuration
   - Audio format handling

3. Performance Optimizations
   - Input caching
   - Concurrent processing
   - Resource management
   - Rate limiting
"""

import speech_recognition as sr
import pyttsx3
from typing import Optional, Dict, Any, List, Tuple
import re
import unicodedata
from pydantic import BaseModel, Field
import asyncio
from dataclasses import dataclass
from enum import Enum
import hashlib
import time
from functools import lru_cache
import json
from pathlib import Path

class InputType(Enum):
    """Enum for input types."""
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    VIDEO = "video"

class ProcessingStatus(Enum):
    """Enum for processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ProcessingMetadata:
    """Data class for processing metadata."""
    processing_time: float
    cache_hit: bool
    language: str
    confidence: float
    timestamp: float

class ProcessedInput(BaseModel):
    """Model for processed input data."""
    text: str = Field(..., description="Processed text content")
    input_type: InputType = Field(..., description="Type of input")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING, description="Processing status")
    processing_metadata: Optional[ProcessingMetadata] = None
    original_hash: str = Field(..., description="Hash of original input")
    processed_hash: str = Field(..., description="Hash of processed input")

class InputProcessor:
    """
    Input processing system that handles various input types and normalizes them
    for further processing.
    
    Features:
    - Text input processing
    - Voice input processing
    - Input normalization
    - Metadata extraction
    - Caching
    - Rate limiting
    - Resource management
    
    Attributes:
        recognizer: Speech recognition instance
        tts_engine: Text-to-speech engine
        cache_dir: Directory for caching processed inputs
        max_cache_size: Maximum size of cache in MB
        rate_limit: Maximum requests per second
        _processing_lock: Lock for concurrent processing
        _cache: LRU cache for processed inputs
    """
    
    def __init__(self, cache_dir: str = "cache/input",
                 max_cache_size: int = 100,
                 rate_limit: int = 10):
        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
        
        # Initialize text-to-speech engine
        self.tts_engine = pyttsx3.init()
        
        # Configure text-to-speech properties
        self.tts_engine.setProperty('rate', 150)
        self.tts_engine.setProperty('volume', 0.9)
        
        # Setup caching
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_cache_size = max_cache_size * 1024 * 1024  # Convert to bytes
        self._cache = {}
        
        # Setup rate limiting
        self.rate_limit = rate_limit
        self._request_times: List[float] = []
        self._processing_lock = asyncio.Lock()
        
        # Initialize processing queue
        self._processing_queue = asyncio.Queue()
        self._is_processing = False
    
    async def process(self, input_data: str, input_type: InputType = InputType.TEXT) -> ProcessedInput:
        """
        Process input data based on its type.
        
        Args:
            input_data: Raw input data
            input_type: Type of input
            
        Returns:
            ProcessedInput object containing normalized text and metadata
            
        Raises:
            ValueError: If input processing fails
            RateLimitError: If rate limit is exceeded
        """
        try:
            # Check rate limit
            await self._check_rate_limit()
            
            # Generate input hash
            input_hash = self._generate_hash(input_data)
            
            # Check cache
            cached_result = await self._get_from_cache(input_hash)
            if cached_result:
                return cached_result
            
            # Process input
            start_time = time.time()
            processed_input = await self._process_input(input_data, input_type)
            
            # Update processing metadata
            processing_time = time.time() - start_time
            processed_input.processing_metadata = ProcessingMetadata(
                processing_time=processing_time,
                cache_hit=False,
                language=processed_input.metadata.get("language", "unknown"),
                confidence=processed_input.metadata.get("confidence", 0.0),
                timestamp=time.time()
            )
            
            # Cache result
            await self._add_to_cache(input_hash, processed_input)
            
            return processed_input
            
        except Exception as e:
            raise ValueError(f"Error processing input: {str(e)}")
    
    async def _process_input(self, input_data: str, input_type: InputType) -> ProcessedInput:
        """Process input based on type."""
        async with self._processing_lock:
            try:
                if input_type == InputType.VOICE:
                    return await self._process_voice(input_data)
                else:
                    return await self._process_text(input_data)
            except Exception as e:
                raise ValueError(f"Error processing {input_type.value} input: {str(e)}")
    
    async def _process_text(self, text: str) -> ProcessedInput:
        """Process text input."""
        try:
            # Normalize text
            normalized_text = self._normalize_text(text)
            
            # Extract metadata
            metadata = self._extract_metadata(text)
            
            # Generate hashes
            original_hash = self._generate_hash(text)
            processed_hash = self._generate_hash(normalized_text)
            
            return ProcessedInput(
                text=normalized_text,
                input_type=InputType.TEXT,
                metadata=metadata,
                status=ProcessingStatus.COMPLETED,
                original_hash=original_hash,
                processed_hash=processed_hash
            )
        except Exception as e:
            raise ValueError(f"Error processing text: {str(e)}")
    
    async def _process_voice(self, audio_data: str) -> ProcessedInput:
        """Process voice input."""
        try:
            # Convert audio to text
            text = await self._speech_to_text(audio_data)
            
            # Process the text
            processed_input = await self._process_text(text)
            processed_input.input_type = InputType.VOICE
            
            return processed_input
        except Exception as e:
            raise ValueError(f"Error processing voice input: {str(e)}")
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text."""
        try:
            # Convert to lowercase
            text = text.lower()
            
            # Normalize unicode characters
            text = unicodedata.normalize('NFKC', text)
            
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text)
            
            # Remove special characters but keep basic punctuation
            text = re.sub(r'[^\w\s.,!?-]', '', text)
            
            return text.strip()
        except Exception as e:
            raise ValueError(f"Error normalizing text: {str(e)}")
    
    def _extract_metadata(self, text: str) -> Dict[str, Any]:
        """Extract metadata from text."""
        try:
            metadata = {
                "length": len(text),
                "word_count": len(text.split()),
                "has_numbers": bool(re.search(r'\d', text)),
                "has_punctuation": bool(re.search(r'[.,!?-]', text)),
                "language": self._detect_language(text),
                "confidence": self._calculate_confidence(text)
            }
            return metadata
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
    
    def _calculate_confidence(self, text: str) -> float:
        """Calculate confidence score for text processing."""
        try:
            # Simple confidence calculation based on text properties
            confidence = 1.0
            
            # Penalize for very short text
            if len(text) < 10:
                confidence *= 0.8
            
            # Penalize for excessive special characters
            special_chars = len(re.findall(r'[^\w\s]', text))
            if special_chars > len(text) * 0.3:
                confidence *= 0.7
            
            # Penalize for mixed languages
            if len(set(self._detect_language(text))) > 1:
                confidence *= 0.6
            
            return max(0.0, min(1.0, confidence))
        except Exception as e:
            raise ValueError(f"Error calculating confidence: {str(e)}")
    
    async def _speech_to_text(self, audio_data: str) -> str:
        """Convert speech to text."""
        try:
            # Convert audio data to AudioData object
            audio = sr.AudioData(audio_data, sample_rate=16000, sample_width=2)
            
            # Recognize speech
            text = self.recognizer.recognize_google(audio)
            
            return text
        except sr.UnknownValueError:
            raise ValueError("Could not understand audio")
        except sr.RequestError as e:
            raise ValueError(f"Could not request results: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error in speech-to-text conversion: {str(e)}")
    
    def text_to_speech(self, text: str, output_file: Optional[str] = None) -> None:
        """Convert text to speech."""
        try:
            if output_file:
                self.tts_engine.save_to_file(text, output_file)
                self.tts_engine.runAndWait()
            else:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
        except Exception as e:
            raise ValueError(f"Error converting text to speech: {str(e)}")
    
    def set_voice_properties(self, rate: Optional[int] = None,
                           volume: Optional[float] = None) -> None:
        """Set text-to-speech voice properties."""
        try:
            if rate is not None:
                self.tts_engine.setProperty('rate', rate)
            if volume is not None:
                self.tts_engine.setProperty('volume', max(0.0, min(1.0, volume)))
        except Exception as e:
            raise ValueError(f"Error setting voice properties: {str(e)}")
    
    async def _check_rate_limit(self) -> None:
        """Check if rate limit is exceeded."""
        current_time = time.time()
        
        # Remove old request times
        self._request_times = [t for t in self._request_times
                             if current_time - t < 1.0]
        
        # Check if rate limit is exceeded
        if len(self._request_times) >= self.rate_limit:
            raise ValueError("Rate limit exceeded")
        
        # Add current request time
        self._request_times.append(current_time)
    
    def _generate_hash(self, data: str) -> str:
        """Generate hash for input data."""
        return hashlib.sha256(data.encode()).hexdigest()
    
    async def _get_from_cache(self, input_hash: str) -> Optional[ProcessedInput]:
        """Get processed input from cache."""
        try:
            cache_file = self.cache_dir / f"{input_hash}.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    return ProcessedInput(**data)
            return None
        except Exception as e:
            self.logger.error(f"Error reading from cache: {str(e)}")
            return None
    
    async def _add_to_cache(self, input_hash: str, processed_input: ProcessedInput) -> None:
        """Add processed input to cache."""
        try:
            # Check cache size
            await self._cleanup_cache()
            
            # Save to cache
            cache_file = self.cache_dir / f"{input_hash}.json"
            with open(cache_file, 'w') as f:
                json.dump(processed_input.dict(), f)
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