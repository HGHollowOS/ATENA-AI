"""
External Services Module

This module provides a unified interface for external service integrations,
including web APIs, databases, and other external resources.
"""

from typing import Dict, List, Optional, Any
import aiohttp
import json
from datetime import datetime
from pydantic import BaseModel
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

class ServiceConfig(BaseModel):
    """Model for service configuration."""
    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    enabled: bool = True

class ExternalServices:
    """
    External services integration system that provides a unified interface
    for interacting with various external services.
    
    Features:
    - Web API integration
    - Google Workspace integration
    - Database connections
    - Service configuration management
    """
    
    def __init__(self):
        self.services: Dict[str, ServiceConfig] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.google_services: Dict[str, Any] = {}
        
        # Load service configurations
        self._load_service_configs()
    
    def _load_service_configs(self):
        """Load service configurations from environment variables."""
        # Load OpenAI configuration
        if os.getenv("OPENAI_API_KEY"):
            self.services["openai"] = ServiceConfig(
                name="openai",
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url="https://api.openai.com/v1"
            )
        
        # Load Google Workspace configuration
        if all([
            os.getenv("GOOGLE_CLIENT_ID"),
            os.getenv("GOOGLE_CLIENT_SECRET"),
            os.getenv("GOOGLE_REDIRECT_URI")
        ]):
            self.services["google"] = ServiceConfig(
                name="google",
                credentials={
                    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                    "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                    "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI")
                }
            )
    
    async def initialize(self):
        """Initialize external service connections."""
        # Initialize aiohttp session
        self.session = aiohttp.ClientSession()
        
        # Initialize Google services
        if "google" in self.services:
            await self._initialize_google_services()
    
    async def close(self):
        """Close external service connections."""
        if self.session:
            await self.session.close()
    
    async def _initialize_google_services(self):
        """Initialize Google Workspace services."""
        try:
            creds = None
            if os.path.exists('token.json'):
                with open('token.json') as token:
                    creds = Credentials.from_authorized_user_info(json.load(token))
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_config(
                        self.services["google"].credentials,
                        ['https://www.googleapis.com/auth/calendar.readonly',
                         'https://www.googleapis.com/auth/drive.readonly',
                         'https://www.googleapis.com/auth/docs.readonly']
                    )
                    creds = flow.run_local_server(port=0)
                
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
            
            # Initialize Google services
            self.google_services["calendar"] = build('calendar', 'v3', credentials=creds)
            self.google_services["drive"] = build('drive', 'v3', credentials=creds)
            self.google_services["docs"] = build('docs', 'v1', credentials=creds)
            
        except Exception as e:
            print(f"Error initializing Google services: {str(e)}")
    
    async def make_request(self, service: str, endpoint: str,
                          method: str = "GET", data: Optional[Dict[str, Any]] = None,
                          headers: Optional[Dict[str, str]] = None) -> Any:
        """
        Make a request to an external service.
        
        Args:
            service: Service name
            endpoint: API endpoint
            method: HTTP method
            data: Request data
            headers: Request headers
            
        Returns:
            Response data
        """
        if service not in self.services:
            raise ValueError(f"Service {service} not configured")
        
        service_config = self.services[service]
        if not service_config.enabled:
            raise ValueError(f"Service {service} is disabled")
        
        if not self.session:
            raise RuntimeError("ExternalServices not initialized")
        
        url = f"{service_config.base_url}/{endpoint}"
        
        # Add service-specific headers
        request_headers = headers or {}
        if service_config.api_key:
            request_headers["Authorization"] = f"Bearer {service_config.api_key}"
        
        try:
            async with self.session.request(method, url, json=data, headers=request_headers) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            raise ValueError(f"Error making request to {service}: {str(e)}")
    
    async def get_calendar_events(self, time_min: Optional[datetime] = None,
                                time_max: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get calendar events from Google Calendar.
        
        Args:
            time_min: Start time
            time_max: End time
            
        Returns:
            List of calendar events
        """
        if "calendar" not in self.google_services:
            raise ValueError("Google Calendar service not initialized")
        
        try:
            events_result = self.google_services["calendar"].events().list(
                calendarId='primary',
                timeMin=time_min.isoformat() if time_min else None,
                timeMax=time_max.isoformat() if time_max else None,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
        except Exception as e:
            raise ValueError(f"Error getting calendar events: {str(e)}")
    
    async def search_drive(self, query: str) -> List[Dict[str, Any]]:
        """
        Search Google Drive files.
        
        Args:
            query: Search query
            
        Returns:
            List of matching files
        """
        if "drive" not in self.google_services:
            raise ValueError("Google Drive service not initialized")
        
        try:
            results = self.google_services["drive"].files().list(
                q=query,
                pageSize=10,
                fields="files(id, name, mimeType, modifiedTime)"
            ).execute()
            
            return results.get('files', [])
        except Exception as e:
            raise ValueError(f"Error searching Drive: {str(e)}")
    
    async def get_doc_content(self, doc_id: str) -> str:
        """
        Get content from a Google Doc.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document content
        """
        if "docs" not in self.google_services:
            raise ValueError("Google Docs service not initialized")
        
        try:
            document = self.google_services["docs"].documents().get(
                documentId=doc_id
            ).execute()
            
            # Extract text content
            content = []
            for element in document.get('body', {}).get('content', []):
                if 'paragraph' in element:
                    for part in element['paragraph'].get('elements', []):
                        if 'textRun' in part:
                            content.append(part['textRun'].get('content', ''))
            
            return ''.join(content)
        except Exception as e:
            raise ValueError(f"Error getting document content: {str(e)}")
    
    def enable_service(self, service: str) -> None:
        """
        Enable a service.
        
        Args:
            service: Service name
        """
        if service in self.services:
            self.services[service].enabled = True
    
    def disable_service(self, service: str) -> None:
        """
        Disable a service.
        
        Args:
            service: Service name
        """
        if service in self.services:
            self.services[service].enabled = False
    
    def get_service_status(self, service: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a service.
        
        Args:
            service: Service name
            
        Returns:
            Service status information
        """
        if service not in self.services:
            return None
        
        service_config = self.services[service]
        return {
            "name": service_config.name,
            "enabled": service_config.enabled,
            "configured": bool(service_config.api_key or service_config.credentials)
        } 