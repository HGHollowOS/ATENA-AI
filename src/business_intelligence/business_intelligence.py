"""
Business Intelligence module for ATENA-AI.
Handles company research, market analysis, and partnership opportunities.
"""

import logging
from typing import Dict, List, Optional, Any
import json
from datetime import datetime
import aiohttp
import asyncio
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class CompanyType(Enum):
    """Types of companies that can be analyzed."""
    STARTUP = "startup"
    ENTERPRISE = "enterprise"
    SME = "sme"
    UNKNOWN = "unknown"

@dataclass
class CompanyProfile:
    """Data structure for company information."""
    name: str
    type: CompanyType
    industry: str
    size: Optional[int]
    founded: Optional[int]
    description: str
    website: Optional[str]
    location: Optional[str]
    technologies: List[str]
    funding: Optional[Dict[str, Any]]
    metrics: Dict[str, Any]

@dataclass
class MarketAnalysis:
    """Data structure for market analysis."""
    industry: str
    market_size: Optional[float]
    growth_rate: Optional[float]
    trends: List[str]
    competitors: List[str]
    opportunities: List[str]
    risks: List[str]

class BusinessIntelligence:
    """Business Intelligence service for ATENA-AI."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Business Intelligence service."""
        self.config = config
        self.api_keys = self._load_api_keys()
        self.cache = {}
        self.cache_timeout = 3600  # 1 hour
    
    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from environment variables."""
        return {
            'alpha_vantage': self.config.get('ALPHA_VANTAGE_API_KEY'),
            'crunchbase': self.config.get('CRUNCHBASE_API_KEY'),
            'linkedin': self.config.get('LINKEDIN_API_KEY')
        }
    
    async def research_company(self, company_name: str) -> CompanyProfile:
        """Research a company and return detailed profile."""
        try:
            # Check cache first
            if company_name in self.cache:
                cached_data = self.cache[company_name]
                if (datetime.now() - cached_data['timestamp']).seconds < self.cache_timeout:
                    return cached_data['profile']
            
            # Gather data from multiple sources
            async with aiohttp.ClientSession() as session:
                tasks = [
                    self._fetch_company_basic_info(session, company_name),
                    self._fetch_company_financials(session, company_name),
                    self._fetch_company_technologies(session, company_name)
                ]
                results = await asyncio.gather(*tasks)
            
            # Combine results into profile
            profile = self._create_company_profile(results)
            
            # Cache the results
            self.cache[company_name] = {
                'profile': profile,
                'timestamp': datetime.now()
            }
            
            return profile
            
        except Exception as e:
            logger.error(f"Error researching company {company_name}: {e}")
            raise
    
    async def analyze_market(self, industry: str) -> MarketAnalysis:
        """Analyze market conditions for a specific industry."""
        try:
            # Check cache first
            if industry in self.cache:
                cached_data = self.cache[industry]
                if (datetime.now() - cached_data['timestamp']).seconds < self.cache_timeout:
                    return cached_data['analysis']
            
            # Gather market data
            async with aiohttp.ClientSession() as session:
                tasks = [
                    self._fetch_market_size(session, industry),
                    self._fetch_market_trends(session, industry),
                    self._fetch_competitors(session, industry)
                ]
                results = await asyncio.gather(*tasks)
            
            # Create market analysis
            analysis = self._create_market_analysis(results)
            
            # Cache the results
            self.cache[industry] = {
                'analysis': analysis,
                'timestamp': datetime.now()
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing market for {industry}: {e}")
            raise
    
    async def find_partnership_opportunities(
        self,
        company_profile: CompanyProfile,
        criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Find potential partnership opportunities based on company profile and criteria."""
        try:
            # Define search parameters
            search_params = self._build_search_params(company_profile, criteria)
            
            # Search for potential partners
            async with aiohttp.ClientSession() as session:
                opportunities = await self._search_partners(session, search_params)
            
            # Filter and rank opportunities
            ranked_opportunities = self._rank_opportunities(opportunities, criteria)
            
            return ranked_opportunities[:10]  # Return top 10 opportunities
            
        except Exception as e:
            logger.error(f"Error finding partnership opportunities: {e}")
            raise
    
    async def _fetch_company_basic_info(
        self,
        session: aiohttp.ClientSession,
        company_name: str
    ) -> Dict[str, Any]:
        """Fetch basic company information from various sources."""
        # Implementation would use actual API calls
        return {
            'name': company_name,
            'type': CompanyType.UNKNOWN,
            'industry': 'Technology',
            'size': 100,
            'founded': 2020,
            'description': 'Sample company description',
            'website': 'https://example.com',
            'location': 'San Francisco, CA'
        }
    
    async def _fetch_company_financials(
        self,
        session: aiohttp.ClientSession,
        company_name: str
    ) -> Dict[str, Any]:
        """Fetch company financial information."""
        # Implementation would use actual API calls
        return {
            'funding': {
                'total': 1000000,
                'rounds': [
                    {'date': '2020-01-01', 'amount': 500000, 'type': 'Seed'}
                ]
            },
            'metrics': {
                'revenue': 500000,
                'growth_rate': 0.5,
                'employees': 50
            }
        }
    
    async def _fetch_company_technologies(
        self,
        session: aiohttp.ClientSession,
        company_name: str
    ) -> List[str]:
        """Fetch company technology stack information."""
        # Implementation would use actual API calls
        return ['Python', 'React', 'AWS']
    
    async def _fetch_market_size(
        self,
        session: aiohttp.ClientSession,
        industry: str
    ) -> float:
        """Fetch market size data for an industry."""
        # Implementation would use actual API calls
        return 1000000000.0
    
    async def _fetch_market_trends(
        self,
        session: aiohttp.ClientSession,
        industry: str
    ) -> List[str]:
        """Fetch market trends for an industry."""
        # Implementation would use actual API calls
        return ['AI Adoption', 'Remote Work', 'Digital Transformation']
    
    async def _fetch_competitors(
        self,
        session: aiohttp.ClientSession,
        industry: str
    ) -> List[str]:
        """Fetch competitor information for an industry."""
        # Implementation would use actual API calls
        return ['Competitor 1', 'Competitor 2', 'Competitor 3']
    
    def _create_company_profile(self, results: List[Dict[str, Any]]) -> CompanyProfile:
        """Create a CompanyProfile from gathered data."""
        basic_info, financials, technologies = results
        
        return CompanyProfile(
            name=basic_info['name'],
            type=basic_info['type'],
            industry=basic_info['industry'],
            size=basic_info['size'],
            founded=basic_info['founded'],
            description=basic_info['description'],
            website=basic_info['website'],
            location=basic_info['location'],
            technologies=technologies,
            funding=financials['funding'],
            metrics=financials['metrics']
        )
    
    def _create_market_analysis(self, results: List[Any]) -> MarketAnalysis:
        """Create a MarketAnalysis from gathered data."""
        market_size, trends, competitors = results
        
        return MarketAnalysis(
            industry='Technology',  # This should come from the search
            market_size=market_size,
            growth_rate=0.1,  # This should be calculated
            trends=trends,
            competitors=competitors,
            opportunities=['Market Expansion', 'Product Innovation'],
            risks=['Competition', 'Regulatory Changes']
        )
    
    def _build_search_params(
        self,
        company_profile: CompanyProfile,
        criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build search parameters for partnership opportunities."""
        return {
            'industry': company_profile.industry,
            'technologies': company_profile.technologies,
            'size_range': criteria.get('size_range', 'any'),
            'location': criteria.get('location', 'any'),
            'funding_stage': criteria.get('funding_stage', 'any')
        }
    
    async def _search_partners(
        self,
        session: aiohttp.ClientSession,
        search_params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Search for potential partners based on criteria."""
        # Implementation would use actual API calls
        return [
            {
                'name': 'Partner 1',
                'match_score': 0.85,
                'complementary_technologies': ['Docker', 'Kubernetes'],
                'potential_synergies': ['Cloud Infrastructure', 'DevOps']
            }
        ]
    
    def _rank_opportunities(
        self,
        opportunities: List[Dict[str, Any]],
        criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Rank partnership opportunities based on criteria."""
        # Sort by match score
        return sorted(opportunities, key=lambda x: x['match_score'], reverse=True) 