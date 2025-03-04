"""
Tests for the News Integration module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.integrations.news import NewsIntegration

@pytest.fixture
def mock_openai():
    return Mock()

@pytest.fixture
def mock_google_workspace():
    return Mock()

@pytest.fixture
def news_integration(mock_openai, mock_google_workspace):
    return NewsIntegration("test-key", mock_google_workspace)

@pytest.fixture
def test_docs():
    """Sample test documents."""
    return [
        {
            "title": "Test Document 1",
            "summary": "This is a test summary for document 1"
        },
        {
            "title": "Test Document 2",
            "summary": "This is a test summary for document 2"
        }
    ]

@pytest.mark.asyncio
async def test_get_relevant_news(news_integration):
    """Test getting relevant news articles."""
    # Mock data
    mock_docs = [
        {"title": "AI Advances", "summary": "New developments in AI"},
        {"title": "Market Trends", "summary": "Latest market analysis"}
    ]
    
    mock_google_workspace.listDocuments.return_value = mock_docs
    
    # Test
    result = await news_integration.get_relevant_news()
    
    # Verify
    assert isinstance(result, list)
    mock_google_workspace.listDocuments.assert_called_once()

@pytest.mark.asyncio
async def test_optimize_documents(news_integration, test_docs):
    """Test document optimization."""
    result = news_integration.optimize_documents(test_docs)
    assert len(result) == len(test_docs)
    for doc in result:
        assert len(doc["title"]) <= 100
        assert len(doc["summary"]) <= 200

@pytest.mark.asyncio
async def test_process_with_retry(news_integration):
    """Test retry mechanism."""
    mock_operation = Mock()
    mock_operation.side_effect = [
        {"error": {"code": "rate_limit_exceeded"}},
        {"success": True}
    ]
    
    result = await news_integration.process_with_retry(mock_operation)
    
    assert result == {"success": True}
    assert mock_operation.call_count == 2

@pytest.mark.asyncio
async def test_test_connection(news_integration):
    """Test API connection test."""
    with patch("src.integrations.news.fetch") as mock_fetch:
        mock_fetch.return_value = MagicMock(
            json=MagicMock(return_value={"status": "ok"})
        )
        result = await news_integration.test_connection()
        assert result is True 