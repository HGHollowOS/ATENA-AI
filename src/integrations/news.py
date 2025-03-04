from typing import List, Dict, Any
import openai
from openai import OpenAI
import json
from src.utils.helpers import sleep

class NewsIntegration:
    def __init__(self, api_key: str, google_workspace: Any):
        self.openai = OpenAI(api_key=api_key)
        self.google_workspace = google_workspace
        self.max_tokens_per_request = 4000
        self.retry_delay = 2000
        self.max_retries = 3

    async def get_relevant_news(self) -> List[Dict[str, Any]]:
        try:
            docs = await self.google_workspace.list_documents()
            return await self.process_batched_docs(self.optimize_documents(docs))
        except Exception as error:
            print('[News] Error:', error)
            return []

    def optimize_documents(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                'title': doc.get('title', '')[:100],
                'summary': doc.get('summary', '')[:200]
            }
            for doc in docs
            if doc.get('title') and doc.get('summary')
        ]

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

    async def process_with_retry(self, operation: callable, retries: int = None) -> Any:
        if retries is None:
            retries = self.max_retries
            
        try:
            return await operation()
        except Exception as error:
            if getattr(error, 'code', None) == 'rate_limit_exceeded' and retries > 0:
                await sleep(self.retry_delay * (self.max_retries - retries + 1))
                return await self.process_with_retry(operation, retries - 1)
            raise error

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

    async def test_connection(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://newsapi.org/v2/top-headlines',
                    params={'country': 'us', 'pageSize': 1},
                    headers={'Authorization': f"Bearer {os.getenv('NEWS_API_KEY')}"}
                ) as response:
                    data = await response.json()
                    return data.get('status') == 'ok'
        except:
            return False 