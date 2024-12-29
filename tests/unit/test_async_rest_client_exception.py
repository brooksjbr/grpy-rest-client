from asyncio import TimeoutError
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from grpy.async_rest_client import AsyncRestClient

TEST_URL = "https://api.example.com"


class TestAsyncRestClientExceptions:
    """
    Test cases for AsyncRestClient exception handling.
    """

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test handling of request timeouts"""
        with patch("aiohttp.ClientSession.request", side_effect=TimeoutError):
            async with AsyncRestClient(TEST_URL) as client:
                with pytest.raises(TimeoutError):
                    await client.handle_request()

    @pytest.mark.asyncio
    async def test_timeout_with_custom_duration(self):
        """Test timeout behavior with different duration settings"""
        with patch("aiohttp.ClientSession.request", side_effect=TimeoutError):
            async with AsyncRestClient(TEST_URL, timeout=1) as client:
                with pytest.raises(TimeoutError):
                    await client.handle_request()

    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test handling of connection errors"""
        with patch(
            "aiohttp.ClientSession.request",
            side_effect=aiohttp.ClientConnectionError,
        ):
            async with AsyncRestClient(TEST_URL) as client:
                with pytest.raises(aiohttp.ClientConnectionError):
                    await client.handle_request()

    @pytest.mark.asyncio
    async def test_invalid_json_handling(self):
        """Test handling of invalid JSON responses"""
        mock_response = AsyncMock()
        mock_response.json.side_effect = aiohttp.ContentTypeError(None, None)
        mock_response.raise_for_status = AsyncMock()

        mock_session_request = AsyncMock(return_value=mock_response)

        with patch("aiohttp.ClientSession.request", mock_session_request):
            async with AsyncRestClient(TEST_URL) as client:
                response = await client.handle_request()
                with pytest.raises(aiohttp.ContentTypeError):
                    await response.json()

    @pytest.mark.asyncio
    async def test_server_error_handling(self):
        """Test handling of 5xx server errors"""

        async def mock_request(*args, **kwargs):
            raise aiohttp.ClientResponseError(
                request_info=AsyncMock(), history=(), status=500
            )

        with patch("aiohttp.ClientSession.request", side_effect=mock_request):
            async with AsyncRestClient(TEST_URL) as client:
                with pytest.raises(aiohttp.ClientResponseError):
                    await client.handle_request()

    @pytest.mark.asyncio
    async def test_client_error_handling(self):
        """Test handling of 4xx client errors"""

        async def mock_request(*args, **kwargs):
            raise aiohttp.ClientResponseError(
                request_info=AsyncMock(), history=(), status=404
            )

        with patch("aiohttp.ClientSession.request", side_effect=mock_request):
            async with AsyncRestClient(TEST_URL) as client:
                with pytest.raises(aiohttp.ClientResponseError):
                    await client.handle_request()

    @pytest.mark.asyncio
    async def test_ssl_error_handling(self):
        """Test SSL certificate verification errors"""
        with patch(
            "aiohttp.ClientSession.request",
            side_effect=aiohttp.ClientConnectorSSLError(AsyncMock(), OSError()),
        ):
            async with AsyncRestClient(TEST_URL) as client:
                with pytest.raises(aiohttp.ClientConnectorSSLError):
                    await client.handle_request()
