"""
Business Intelligence module for ATENA-AI.
Handles company research, market analysis, and partnership opportunities,
with a focus on the space industry and satellite servicing sector.
"""

import logging
from typing import Dict, List, Optional, Any, Set, Tuple
import json
from datetime import datetime, timedelta
import aiohttp
import asyncio
from dataclasses import dataclass
from enum import Enum
import re

logger = logging.getLogger(__name__)

class CompanyType(Enum):
    """Types of companies that can be analyzed."""
    STARTUP = "startup"
    ENTERPRISE = "enterprise"
    SME = "sme"
    RESEARCH_INSTITUTION = "research_institution"
    SPACE_AGENCY = "space_agency"
    UNKNOWN = "unknown"

class IndustrySegment(Enum):
    """Space industry segments for focused monitoring."""
    SATELLITE_SERVICING = "satellite_servicing"
    POWER_SYSTEMS = "power_systems"
    PROPULSION = "propulsion"
    COMMUNICATIONS = "communications"
    EARTH_OBSERVATION = "earth_observation"
    SPACE_MANUFACTURING = "space_manufacturing"
    DEBRIS_REMOVAL = "debris_removal"

@dataclass
class CompanyProfile:
    """Data structure for company information."""
    name: str
    type: CompanyType
    industry: str
    industry_segments: List[IndustrySegment]
    size: Optional[int]
    founded: Optional[int]
    description: str
    website: Optional[str]
    location: Optional[str]
    technologies: List[str]
    funding: Optional[Dict[str, Any]]
    metrics: Dict[str, Any]
    last_news_check: Optional[datetime] = None
    recent_developments: List[Dict[str, Any]] = None

@dataclass
class MarketAnalysis:
    """Data structure for market analysis."""
    industry: str
    segment: IndustrySegment
    market_size: Optional[float]
    growth_rate: Optional[float]
    trends: List[str]
    competitors: List[str]
    opportunities: List[str]
    risks: List[str]
    last_updated: datetime

@dataclass
class BusinessAlert:
    """Data structure for business alerts and notifications."""
    alert_type: str  # 'partnership', 'market_trend', 'company_update', 'technology'
    priority: int  # 1-5, with 5 being highest
    title: str
    description: str
    source_data: Dict[str, Any]
    timestamp: datetime
    requires_action: bool
    suggested_actions: List[str]

class BusinessIntelligence:
    """Business Intelligence service for ATENA-AI."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Business Intelligence service."""
        self.config = config
        self.api_keys = self._load_api_keys()
        self.cache = {}
        self.cache_timeout = 3600  # 1 hour
        self.monitored_companies: Set[str] = set()
        self.monitored_segments: Set[IndustrySegment] = {
            IndustrySegment.SATELLITE_SERVICING,
            IndustrySegment.POWER_SYSTEMS
        }
        self.alert_queue: List[BusinessAlert] = []
        self.last_monitoring_check = datetime.now()
        self.monitoring_interval = 300  # 5 minutes
    
    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from environment variables."""
        return {
            'alpha_vantage': self.config.get('ALPHA_VANTAGE_API_KEY'),
            'crunchbase': self.config.get('CRUNCHBASE_API_KEY'),
            'linkedin': self.config.get('LINKEDIN_API_KEY'),
            'spacenews_api': self.config.get('SPACENEWS_API_KEY'),
            'nasa_api': self.config.get('NASA_API_KEY')
        }
    
    async def start_monitoring(self):
        """Start the background monitoring process."""
        while True:
            try:
                await self._check_for_updates()
                await asyncio.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _check_for_updates(self):
        """Check for updates across all monitored entities."""
        try:
            current_time = datetime.now()
            
            # Only check if enough time has passed
            if (current_time - self.last_monitoring_check).seconds < self.monitoring_interval:
                return
            
            async with aiohttp.ClientSession() as session:
                tasks = []
                
                # Check company updates
                for company in self.monitored_companies:
                    tasks.append(self._check_company_updates(session, company))
                
                # Check industry segments
                for segment in self.monitored_segments:
                    tasks.append(self._check_segment_updates(session, segment))
                
                # Check partnership opportunities
                tasks.append(self._check_partnership_opportunities(session))
                
                # Wait for all checks to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results and generate alerts
                await self._process_monitoring_results(results)
            
            self.last_monitoring_check = current_time
            
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            raise
    
    async def _check_company_updates(
        self,
        session: aiohttp.ClientSession,
        company_name: str
    ) -> List[Dict[str, Any]]:
        """Check for updates about a specific company."""
        try:
            updates = []
            
            # Check news
            news = await self._fetch_company_news(session, company_name)
            if news:
                updates.extend([
                    {
                        'type': 'company_update',
                        'subtype': 'news',
                        'content': item
                    } for item in news
                ])
            
            # Check funding rounds
            funding = await self._fetch_company_funding(session, company_name)
            if funding:
                updates.extend([
                    {
                        'type': 'company_update',
                        'subtype': 'funding',
                        'content': item
                    } for item in funding
                ])
            
            return updates
            
        except Exception as e:
            logger.error(f"Error checking company updates for {company_name}: {e}")
            return []
    
    async def _check_segment_updates(
        self,
        session: aiohttp.ClientSession,
        segment: IndustrySegment
    ) -> List[Dict[str, Any]]:
        """Check for updates in a specific industry segment."""
        try:
            updates = []
            
            # Check industry news
            news = await self._fetch_industry_news(session, segment)
            if news:
                updates.extend([
                    {
                        'type': 'market_trend',
                        'subtype': 'news',
                        'segment': segment,
                        'content': item
                    } for item in news
                ])
            
            # Check technology developments
            tech_updates = await self._fetch_technology_updates(session, segment)
            if tech_updates:
                updates.extend([
                    {
                        'type': 'technology',
                        'subtype': 'development',
                        'segment': segment,
                        'content': item
                    } for item in tech_updates
                ])
            
            return updates
            
        except Exception as e:
            logger.error(f"Error checking segment updates for {segment}: {e}")
            return []
    
    async def _process_monitoring_results(self, results: List[Any]):
        """Process monitoring results and generate alerts."""
        try:
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error in monitoring result: {result}")
                    continue
                
                if not result:
                    continue
                
                for update in result:
                    alert = self._create_alert_from_update(update)
                    if alert and self._should_notify(alert):
                        self.alert_queue.append(alert)
            
        except Exception as e:
            logger.error(f"Error processing monitoring results: {e}")
    
    def _create_alert_from_update(self, update: Dict[str, Any]) -> Optional[BusinessAlert]:
        """Create a BusinessAlert from an update."""
        try:
            content = update['content']
            
            if update['type'] == 'company_update':
                if update['subtype'] == 'funding':
                    return BusinessAlert(
                        alert_type='company_update',
                        priority=4,
                        title=f"New Funding Round: {content['company']}",
                        description=f"${content['amount']:,.2f} {content['round_type']} round",
                        source_data=content,
                        timestamp=datetime.now(),
                        requires_action=True,
                        suggested_actions=['Research partnership opportunity', 'Draft outreach email']
                    )
                elif update['subtype'] == 'news':
                    return BusinessAlert(
                        alert_type='company_update',
                        priority=3,
                        title=f"Company News: {content['company']}",
                        description=content['headline'],
                        source_data=content,
                        timestamp=datetime.now(),
                        requires_action=False,
                        suggested_actions=['Monitor developments', 'Update company profile']
                    )
            
            elif update['type'] == 'market_trend':
                return BusinessAlert(
                    alert_type='market_trend',
                    priority=3,
                    title=f"Market Update: {update['segment'].value}",
                    description=content['summary'],
                    source_data=content,
                    timestamp=datetime.now(),
                    requires_action=False,
                    suggested_actions=['Update market analysis', 'Review strategy alignment']
                )
            
            elif update['type'] == 'technology':
                return BusinessAlert(
                    alert_type='technology',
                    priority=4,
                    title=f"Technology Development: {update['segment'].value}",
                    description=content['summary'],
                    source_data=content,
                    timestamp=datetime.now(),
                    requires_action=True,
                    suggested_actions=['Assess technical impact', 'Update product roadmap']
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating alert from update: {e}")
            return None
    
    def _should_notify(self, alert: BusinessAlert) -> bool:
        """Determine if an alert should trigger a notification."""
        try:
            # Check if similar alert was recently sent
            recent_similar = [
                a for a in self.alert_queue[-10:]
                if (
                    a.alert_type == alert.alert_type
                    and a.title == alert.title
                    and (datetime.now() - a.timestamp).hours < 24
                )
            ]
            
            if recent_similar:
                return False
            
            # Check priority threshold
            if alert.priority < self.config.get('min_alert_priority', 3):
                return False
            
            # Check business hours if configured
            if self.config.get('business_hours_only', False):
                current_hour = datetime.now().hour
                if not (9 <= current_hour <= 17):  # 9 AM to 5 PM
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking notification criteria: {e}")
            return False
    
    async def get_pending_alerts(self) -> List[BusinessAlert]:
        """Get pending alerts and clear the queue."""
        alerts = self.alert_queue.copy()
        self.alert_queue.clear()
        return alerts
    
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
            segment=IndustrySegment.SATELLITE_SERVICING,  # This should be calculated
            market_size=market_size,
            growth_rate=0.1,  # This should be calculated
            trends=trends,
            competitors=competitors,
            opportunities=['Market Expansion', 'Product Innovation'],
            risks=['Competition', 'Regulatory Changes'],
            last_updated=datetime.now()
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