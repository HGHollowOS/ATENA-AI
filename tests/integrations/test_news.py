"""
Tests for the News Integration module
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from src.integrations.news import NewsIntegration

@pytest.fixture
def mock_openai():
    return AsyncMock()

@pytest.fixture
def mock_google_workspace():
    mock = MagicMock()
    async def async_list_documents():
        return [
            {"id": "1", "title": "Test News Article"},
            {"id": "2", "title": "Another Test Article"}
        ]
    mock.list_documents = AsyncMock(side_effect=async_list_documents)
    return mock

@pytest.fixture
def news_integration(mock_openai, mock_google_workspace):
    integration = NewsIntegration("test-key", mock_google_workspace)
    async def async_fetch(*args, **kwargs):
        return {"status": "ok", "data": {}}
    integration._fetch = AsyncMock(side_effect=async_fetch)
    return integration

@pytest.fixture
def test_docs():
    """Create test documents."""
    return [
        {"title": "Test News 1", "content": "Test content 1"},
        {"title": "Test News 2", "content": "Test content 2"}
    ]

@pytest.mark.asyncio
async def test_get_relevant_news(news_integration):
    """Test retrieving relevant news."""
    # Mock the process_with_retry to directly return the documents
    async def mock_process(*args, **kwargs):
        return await news_integration.google_workspace.list_documents()
    
    with patch.object(news_integration, 'process_with_retry', side_effect=mock_process):
        result = await news_integration.get_relevant_news("Test")
        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]["title"] == "Test News Article"

@pytest.mark.asyncio
async def test_optimize_documents(news_integration, test_docs):
    """Test document optimization."""
    result = await news_integration.optimize_documents(test_docs)
    assert len(result) == len(test_docs)
    assert all("title" in doc for doc in result)

@pytest.mark.asyncio
async def test_process_with_retry(news_integration):
    """Test processing with retry mechanism."""
    async def operation():
        return {"success": True}
    
    result = await news_integration.process_with_retry(operation)
    assert result["success"] is True

@pytest.mark.asyncio
async def test_test_connection(news_integration):
    """Test connection testing."""
    # Mock process_with_retry to directly return the fetch result
    async def mock_process(*args, **kwargs):
        return await news_integration._fetch("/status")
    
    with patch.object(news_integration, 'process_with_retry', side_effect=mock_process):
        result = await news_integration.test_connection()
        assert isinstance(result, dict)
        assert result["status"] == "ok"
        assert news_integration._fetch.await_count == 1 