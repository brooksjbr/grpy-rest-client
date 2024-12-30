from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientSession

from grpy.rest_client import RestClient

TEST_URL = "https://api.example.com"


class TestRestClient:
    """Test the RestClient class."""

    @pytest.fixture
    def mock_response(self):
        """Create a mock response object."""
        mock = AsyncMock(
            spec=ClientSession,
            status=200,
            data={"data": "Mocked response"},
            raise_for_status=AsyncMock(),  # Add awaitable raise_for_status
        )
        return mock

    @pytest.fixture
    def mock_client_session(self, mock_response):
        """Create a mock client session."""
        with patch(
            "aiohttp.ClientSession.request",
            new=AsyncMock(return_value=mock_response),
        ):
            yield

    @pytest.mark.parametrize(
        "method", ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]
    )
    async def test_http_methods_sucess(self, mock_client_session, method):
        async with RestClient(TEST_URL, method=method) as client:
            response = await client.handle_request()
            assert response.status == 200
