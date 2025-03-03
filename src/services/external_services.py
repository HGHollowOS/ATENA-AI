"""
External Services Module

This module implements a comprehensive external services integration system that manages
API interactions, rate limiting, and error handling.

Features:
1. API Integration
   - Unified API interface
   - Rate limiting
   - Error handling
   - Retry mechanisms

2. Service Management
   - Service configuration
   - Authentication
   - Connection pooling
   - Health monitoring

3. Performance Optimizations
   - Request caching
   - Connection reuse
   - Batch operations
   - Resource management
"""

from typing import Dict, List, Optional, Any, Set, Tuple, Union
from datetime import datetime
from pydantic import BaseModel, Field
import asyncio
from dataclasses import dataclass
from enum import Enum
import hashlib
import time
import json
from pathlib import Path
import aiohttp
import logging
from collections import defaultdict
import backoff
from tenacity import retry, stop_after_attempt, wait_exponential

class ServiceType(Enum):
    """Enum for service types."""
    API = "api"
    DATABASE = "database"
    CACHE = "cache"
    STORAGE = "storage"
    AUTH = "auth"
    ANALYTICS = "analytics"

class ServiceStatus(Enum):
    """Enum for service status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    MAINTENANCE = "maintenance"

@dataclass
class ServiceMetrics:
    """Data class for service metrics."""
    start_time: datetime
    end_time: Optional[datetime] = None
    request_count: int = 0
    error_count: int = 0
    total_latency: float = 0.0
    rate_limit_hits: int = 0
    retry_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

class ServiceConfig(BaseModel):
    """Model for service configuration."""
    name: str = Field(..., description="Service name")
    type: ServiceType = Field(..., description="Service type")
    base_url: str = Field(..., description="Service base URL")
    api_key: Optional[str] = Field(None, description="API key")
    secret: Optional[str] = Field(None, description="API secret")
    timeout: float = Field(30.0, description="Request timeout")
    max_retries: int = Field(3, description="Maximum retries")
    rate_limit: int = Field(100, description="Requests per minute")
    cache_ttl: int = Field(300, description="Cache TTL in seconds")
    headers: Dict[str, str] = Field(default_factory=dict, description="Custom headers")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class ServiceResponse(BaseModel):
    """Model for service response."""
    status_code: int = Field(..., description="HTTP status code")
    data: Any = Field(..., description="Response data")
    headers: Dict[str, str] = Field(default_factory=dict, description="Response headers")
    latency: float = Field(..., description="Request latency")
    cached: bool = Field(False, description="Whether response was cached")
    error: Optional[str] = Field(None, description="Error message")

class ExternalServices:
    """
    External services integration system that manages API interactions.
    
    Features:
    - Unified API interface
    - Rate limiting and throttling
    - Error handling and retries
    - Response caching
    - Health monitoring
    
    Attributes:
        services: Dictionary of configured services
        session: aiohttp ClientSession
        rate_limits: Rate limit tracking
        metrics: Service metrics
        _processing_lock: Lock for concurrent operations
    """
    
    def __init__(self):
        # Setup services
        self.services: Dict[str, ServiceConfig] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Setup rate limiting
        self.rate_limits: Dict[str, List[float]] = defaultdict(list)
        
        # Setup metrics
        self.metrics: Dict[str, ServiceMetrics] = {}
        
        # Setup processing
        self._processing_lock = asyncio.Lock()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> None:
        """Initialize the external services system."""
        try:
            # Create aiohttp session
            self.session = aiohttp.ClientSession()
            
            # Load service configurations
            await self._load_service_configs()
            
            # Initialize metrics
            await self._initialize_metrics()
            
        except Exception as e:
            self.logger.error(f"Error initializing external services: {str(e)}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the external services system."""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            
            # Save metrics
            await self._save_metrics()
            
        except Exception as e:
            self.logger.error(f"Error shutting down external services: {str(e)}")
            raise
    
    async def register_service(self, config: ServiceConfig) -> None:
        """
        Register a new service.
        
        Args:
            config: Service configuration
            
        Raises:
            ValueError: If service registration fails
        """
        try:
            # Validate configuration
            self._validate_service_config(config)
            
            # Add service
            self.services[config.name] = config
            
            # Initialize metrics
            self.metrics[config.name] = ServiceMetrics(start_time=datetime.now())
            
            self.logger.info(f"Registered service: {config.name}")
            
        except Exception as e:
            self.logger.error(f"Error registering service: {str(e)}")
            raise ValueError(f"Failed to register service: {str(e)}")
    
    async def make_request(self, service_name: str, method: str, endpoint: str,
                         params: Optional[Dict[str, Any]] = None,
                         data: Optional[Dict[str, Any]] = None,
                         headers: Optional[Dict[str, str]] = None,
                         use_cache: bool = True) -> ServiceResponse:
        """
        Make a request to an external service.
        
        Args:
            service_name: Name of the service
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request data
            headers: Custom headers
            use_cache: Whether to use caching
            
        Returns:
            ServiceResponse object
            
        Raises:
            ValueError: If request fails
        """
        try:
            # Get service config
            service = self.services.get(service_name)
            if not service:
                raise ValueError(f"Service not found: {service_name}")
            
            # Check rate limit
            if not await self._check_rate_limit(service_name):
                raise ValueError("Rate limit exceeded")
            
            # Prepare request
            url = f"{service.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            request_headers = self._prepare_headers(service, headers)
            
            # Check cache
            if use_cache and method == "GET":
                cached_response = await self._get_cached_response(service_name, url, params)
                if cached_response:
                    return cached_response
            
            # Make request
            start_time = time.time()
            async with self.session.request(
                method, url,
                params=params,
                json=data,
                headers=request_headers,
                timeout=service.timeout
            ) as response:
                # Read response
                response_data = await response.json()
                
                # Create response object
                service_response = ServiceResponse(
                    status_code=response.status,
                    data=response_data,
                    headers=dict(response.headers),
                    latency=time.time() - start_time
                )
                
                # Handle errors
                if response.status >= 400:
                    service_response.error = str(response_data)
                    raise ValueError(f"Request failed: {service_response.error}")
                
                # Cache response
                if use_cache and method == "GET":
                    await self._cache_response(service_name, url, params, service_response)
                
                return service_response
            
        except Exception as e:
            self.logger.error(f"Error making request: {str(e)}")
            raise ValueError(f"Failed to make request: {str(e)}")
    
    async def get_service_status(self, service_name: str) -> ServiceStatus:
        """
        Get the current status of a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Current service status
            
        Raises:
            ValueError: If service not found
        """
        try:
            # Get service config
            service = self.services.get(service_name)
            if not service:
                raise ValueError(f"Service not found: {service_name}")
            
            # Check rate limit
            if await self._is_rate_limited(service_name):
                return ServiceStatus.RATE_LIMITED
            
            # Check health
            try:
                await self.make_request(service_name, "GET", "health")
                return ServiceStatus.ACTIVE
            except Exception:
                return ServiceStatus.ERROR
            
        except Exception as e:
            self.logger.error(f"Error getting service status: {str(e)}")
            raise ValueError(f"Failed to get service status: {str(e)}")
    
    async def get_service_metrics(self, service_name: str) -> Optional[ServiceMetrics]:
        """
        Get the metrics for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service metrics if available
            
        Raises:
            ValueError: If service not found
        """
        try:
            return self.metrics.get(service_name)
        except Exception as e:
            self.logger.error(f"Error getting service metrics: {str(e)}")
            raise ValueError(f"Failed to get service metrics: {str(e)}")
    
    async def cleanup(self) -> None:
        """Clean up expired data and reset metrics."""
        try:
            async with self._processing_lock:
                # Clean up rate limits
                current_time = time.time()
                for service_name in self.rate_limits:
                    self.rate_limits[service_name] = [
                        t for t in self.rate_limits[service_name]
                        if current_time - t < 60  # Keep last minute
                    ]
                
                # Clean up metrics
                for service_name in self.metrics:
                    metrics = self.metrics[service_name]
                    if metrics.end_time and (datetime.now() - metrics.end_time).days > 7:
                        del self.metrics[service_name]
                
        except Exception as e:
            self.logger.error(f"Error cleaning up: {str(e)}")
    
    def _validate_service_config(self, config: ServiceConfig) -> None:
        """Validate service configuration."""
        if not config.name:
            raise ValueError("Service name is required")
        if not config.base_url:
            raise ValueError("Service base URL is required")
        if config.type not in ServiceType:
            raise ValueError("Invalid service type")
    
    def _prepare_headers(self, service: ServiceConfig,
                        custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Prepare request headers."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ATENAAI/1.0.0"
        }
        
        # Add service headers
        headers.update(service.headers)
        
        # Add authentication
        if service.api_key:
            headers["Authorization"] = f"Bearer {service.api_key}"
        
        # Add custom headers
        if custom_headers:
            headers.update(custom_headers)
        
        return headers
    
    async def _check_rate_limit(self, service_name: str) -> bool:
        """Check if rate limit is exceeded."""
        try:
            service = self.services[service_name]
            current_time = time.time()
            
            # Remove old timestamps
            self.rate_limits[service_name] = [
                t for t in self.rate_limits[service_name]
                if current_time - t < 60  # Last minute
            ]
            
            # Check rate limit
            if len(self.rate_limits[service_name]) >= service.rate_limit:
                return False
            
            # Add new timestamp
            self.rate_limits[service_name].append(current_time)
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking rate limit: {str(e)}")
            return False
    
    async def _is_rate_limited(self, service_name: str) -> bool:
        """Check if service is rate limited."""
        try:
            return len(self.rate_limits[service_name]) >= self.services[service_name].rate_limit
        except Exception:
            return False
    
    async def _get_cached_response(self, service_name: str, url: str,
                                 params: Optional[Dict[str, Any]] = None) -> Optional[ServiceResponse]:
        """Get cached response if available."""
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(service_name, url, params)
            
            # Check cache
            cached_data = await self._get_from_cache(cache_key)
            if cached_data:
                return ServiceResponse(**cached_data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting cached response: {str(e)}")
            return None
    
    async def _cache_response(self, service_name: str, url: str,
                            params: Optional[Dict[str, Any]], response: ServiceResponse) -> None:
        """Cache response data."""
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(service_name, url, params)
            
            # Cache response
            await self._store_in_cache(cache_key, response.dict())
            
        except Exception as e:
            self.logger.error(f"Error caching response: {str(e)}")
    
    def _generate_cache_key(self, service_name: str, url: str,
                          params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key."""
        key_parts = [service_name, url]
        if params:
            key_parts.append(json.dumps(params, sort_keys=True))
        return hashlib.sha256(":".join(key_parts).encode()).hexdigest()
    
    async def _load_service_configs(self) -> None:
        """Load service configurations."""
        try:
            # Implementation for loading service configs
            # This should be implemented based on your configuration storage
            pass
        except Exception as e:
            self.logger.error(f"Error loading service configs: {str(e)}")
            raise
    
    async def _initialize_metrics(self) -> None:
        """Initialize service metrics."""
        try:
            for service_name in self.services:
                self.metrics[service_name] = ServiceMetrics(start_time=datetime.now())
        except Exception as e:
            self.logger.error(f"Error initializing metrics: {str(e)}")
            raise
    
    async def _save_metrics(self) -> None:
        """Save service metrics."""
        try:
            # Implementation for saving metrics
            # This should be implemented based on your metrics storage
            pass
        except Exception as e:
            self.logger.error(f"Error saving metrics: {str(e)}")
            raise
    
    async def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache."""
        try:
            # Implementation for cache retrieval
            # This should be implemented based on your caching system
            pass
        except Exception as e:
            self.logger.error(f"Error getting from cache: {str(e)}")
            return None
    
    async def _store_in_cache(self, key: str, data: Dict[str, Any]) -> None:
        """Store data in cache."""
        try:
            # Implementation for cache storage
            # This should be implemented based on your caching system
            pass
        except Exception as e:
            self.logger.error(f"Error storing in cache: {str(e)}")
            raise 