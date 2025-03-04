from typing import List, Dict, Any, Callable, Optional
import asyncio
from datetime import datetime, timedelta
import logging
import openai
from openai import OpenAI
import json
from src.utils.helpers import sleep

logger = logging.getLogger(__name__)

class NewsIntegration:
    """Integration with news and document services."""
    
    def __init__(self, api_key: str, google_workspace: Any):
        self.openai = OpenAI(api_key=api_key)
        self.google_workspace = google_workspace
        self.max_tokens_per_request = 4000
        self.retry_delay = 1  # seconds
        self.max_retries = 3

    async def get_relevant_news(self, topic: str) -> List[Dict[str, Any]]:
        """Get relevant news documents based on topic."""
        try:
            documents = await self.process_with_retry(lambda: self.google_workspace.list_documents())
            return [doc for doc in documents if topic.lower() in doc["title"].lower()]
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return []

    async def optimize_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimize documents for processing."""
        optimized = []
        for doc in documents:
            summary = await self._generate_summary(doc["content"])
            optimized.append({
                **doc,
                "summary": summary
            })
        return optimized

    async def process_with_retry(self, operation: Callable) -> Any:
        """Process operation with retry mechanism."""
        retries = 0
        last_error = None
        while retries < self.max_retries:
            try:
                if asyncio.iscoroutinefunction(operation):
                    return await operation()
                return operation()
            except Exception as e:
                last_error = e
                retries += 1
                if retries == self.max_retries:
                    logger.error(f"Operation failed after {retries} retries: {e}")
                    raise last_error
                await asyncio.sleep(self.retry_delay * retries)

    async def test_connection(self) -> Dict[str, str]:
        """Test connection to the news service."""
        try:
            result = await self.process_with_retry(lambda: self._fetch("/status"))
            return {"status": "ok", "message": "Connection successful"}
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {"status": "error", "message": str(e)}

    async def _fetch(self, endpoint: str) -> Dict[str, Any]:
        """Internal method to fetch data from the news service."""
        try:
            # Simulated fetch for testing
            await asyncio.sleep(0.1)  # Simulate network delay
            return {"status": "ok", "data": {}}
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            raise

    async def _generate_summary(self, content: str) -> str:
        """Generate a summary of the document content."""
        # Simple summary generation for testing
        return content[:200] + "..." if len(content) > 200 else content

    async def process_batched_docs(self, docs: List[Dict[str, Any]]) -> List[str]:
        all_topics = []
        batches = self.create_token_safe_batches(docs)

        for batch in batches:
            try:
                topics = await self.process_with_retry(lambda: self.extract_topics_from_docs(batch))
                all_topics.extend(topics)
                await sleep(self.retry_delay)
            except:
                continue

        return list(set(all_topics))

    def create_token_safe_batches(self, docs: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        batches = []
        current_batch = []
        current_tokens = 0

        for doc in docs:
            doc_tokens = len(json.dumps(doc))
            
            if current_tokens + doc_tokens > self.max_tokens_per_request:
                batches.append(current_batch)
                current_batch = [doc]
                current_tokens = doc_tokens
            else:
                current_batch.append(doc)
                current_tokens += doc_tokens

        if current_batch:
            batches.append(current_batch)
        return batches

    async def extract_topics_from_docs(self, docs: List[Dict[str, Any]]) -> List[str]:
        prompt = self.create_extract_prompt(docs)
        if len(prompt) > self.max_tokens_per_request:
            raise ValueError('Batch too large')

        response = await self.openai.chat.completions.create(
            model='gpt-4',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=1000,
            temperature=0.5,
            presence_penalty=-0.5,
            frequency_penalty=0.3
        )

        return self.parse_topics_response(response)

    def create_extract_prompt(self, docs: List[Dict[str, Any]]) -> str:
        return (
            'Extract core business topics, companies, and trends. Format: ["topic1","topic2"]:\n'
            f"{'|'.join(d['title'] for d in docs)}"
        )

    def parse_topics_response(self, response: Any) -> List[str]:
        try:
            return json.loads(response.choices[0].message.content)
        except:
            return [] 