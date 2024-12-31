from asyncio import TimeoutError
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from grpy.rest_client import RestClient

TEST_URL = "https://api.example.com"


@pytest.fixture
def mock_request_error():
    def _create_mock(error_type, status_code=None):
        if status_code:

            async def mock_request(*args, **kwargs):
                raise aiohttp.ClientResponseError(
                    request_info=AsyncMock(), history=(), status=status_code
                )

            return mock_request
        else:
            return AsyncMock(side_effect=error_type)

    return _create_mock


@pytest.fixture
def mock_client_session():
    def _patch_session(mock_request):
        return patch("aiohttp.ClientSession.request", mock_request)

    return _patch_session


class TestRestClientExceptions:
    """
    Test cases for RestClient exception handling.
    """

    @pytest.mark.asyncio
    async def test_timeout_handling(
        self, mock_request_error, mock_client_session
    ):
        with mock_client_session(mock_request_error(TimeoutError)):
            async with RestClient(TEST_URL) as client:
                with pytest.raises(TimeoutError):
                    await client.handle_request()

    @pytest.mark.asyncio
    async def test_timeout_with_custom_duration(self):
        """Test timeout behavior with different duration settings"""
        with patch("aiohttp.ClientSession.request", side_effect=TimeoutError):
            async with RestClient(TEST_URL, timeout=1) as client:
                with pytest.raises(TimeoutError):
                    await client.handle_request()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [500, 502, 503, 504])
    async def test_server_error_handling(
        self, mock_request_error, mock_client_session, status_code
    ):
        with mock_client_session(
            mock_request_error(
                aiohttp.ClientResponseError, status_code=status_code
            )
        ):
            async with RestClient(TEST_URL) as client:
                with pytest.raises(aiohttp.ClientResponseError):
                    await client.handle_request()

    @pytest.mark.asyncio
    async def test_connection_error_handling(
        self, mock_request_error, mock_client_session
    ):
        """Test handling of connection errors"""
        with mock_client_session(
            mock_request_error(aiohttp.ClientConnectionError)
        ):
            async with RestClient(TEST_URL) as client:
                with pytest.raises(aiohttp.ClientConnectionError):
                    await client.handle_request()

    @pytest.mark.asyncio
    async def test_invalid_json_handling(self):
        """Test handling of invalid JSON responses"""
        mock_response = AsyncMock()
        # Create ContentTypeError with required request_info and history parameters
        content_error = aiohttp.ContentTypeError(
            request_info=aiohttp.RequestInfo(
                url="https://api.example.com",
                method="GET",
                headers={},
                real_url="https://api.example.com",
            ),
            history=(),
        )
        mock_response.json.side_effect = content_error
        mock_response.raise_for_status = AsyncMock()

        mock_session_request = AsyncMock(return_value=mock_response)

        with patch("aiohttp.ClientSession.request", mock_session_request):
            async with RestClient(TEST_URL) as client:
                response = await client.handle_request()
                with pytest.raises(aiohttp.ContentTypeError):
                    await response.json()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 429])
    async def test_client_error_handling(
        self, mock_request_error, mock_client_session, status_code
    ):
        """Test handling of 4xx client errors"""
        with mock_client_session(
            mock_request_error(
                aiohttp.ClientResponseError, status_code=status_code
            )
        ):
            async with RestClient(TEST_URL) as client:
                with pytest.raises(aiohttp.ClientResponseError):
                    await client.handle_request()

    @pytest.mark.asyncio
    async def test_ssl_error_handling(
        self, mock_request_error, mock_client_session
    ):
        """Test SSL certificate verification errors"""
        with mock_client_session(
            mock_request_error(
                aiohttp.ClientConnectorSSLError(AsyncMock(), OSError())
            )
        ):
            async with RestClient(TEST_URL) as client:
                with pytest.raises(aiohttp.ClientConnectorSSLError):
                    await client.handle_request()
