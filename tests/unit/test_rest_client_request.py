import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientSession

from grpy.rest_client import RestClient

TEST_URL = "https://api.example.com"


@pytest.fixture
async def rest_client(mock_client_session):
    """Fixture that provides a RestClient instance with mocked session"""
    with patch("aiohttp.ClientSession", return_value=mock_client_session):
        async with RestClient(TEST_URL) as client:
            client.session = mock_client_session
            yield client


@pytest.fixture
def mock_client_session(mock_response):
    """Create a mock client session."""
    session = AsyncMock(spec=ClientSession)
    session.request = AsyncMock(return_value=mock_response)
    session.close = AsyncMock()
    session.closed = False
    return session


@pytest.fixture
def mock_response():
    """Create a mock response object."""
    mock = AsyncMock()
    mock.status = 200
    mock.json = AsyncMock(return_value={"data": "Mocked response"})
    mock.headers = {"Content-Type": "application/json", "X-Custom": "value"}
    mock.raise_for_status = AsyncMock()
    return mock


class TestRestClienRequest:
    """Test the RestClient class."""

    @pytest.mark.parametrize(
        "method", ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]
    )
    async def test_http_methods_success(self, rest_client, method):
        rest_client.method = method
        response = await rest_client.handle_request()
        assert response.status == 200
        assert await response.json() == {"data": "Mocked response"}

    @pytest.mark.asyncio
    async def test_response_header_handling(self, rest_client):
        """Test handling of various response headers"""
        response = await rest_client.handle_request()
        assert response.headers["Content-Type"] == "application/json"
        assert response.headers["X-Custom"] == "value"

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, rest_client):
        """Test multiple concurrent requests"""
        tasks = [rest_client.handle_request() for _ in range(3)]
        responses = await asyncio.gather(*tasks)
        assert len(responses) == 3
        assert all(r.status == 200 for r in responses)

    @pytest.mark.asyncio
    async def test_request_with_params(self, rest_client, mock_client_session):
        """Test request handling with query parameters"""
        test_params = {"key1": "value1", "key2": "value2"}
        rest_client.params = test_params

        await rest_client.handle_request()

        mock_client_session.request.assert_called_once()
        call_kwargs = mock_client_session.request.call_args.kwargs
        assert call_kwargs["params"] == test_params
        assert call_kwargs["url"] == TEST_URL
