from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientSession

from grpy.async_rest_client import AsyncRestClient

MOCK_URL = "https://test.api.com "


@pytest.mark.asyncio
class TestAsyncRestClientRequest:
    """Test cases for the AsyncRestClient class."""

    async def test_async_rest_client_request(self):
        """Test the AsyncRestClient class."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.status = 200

        mock_session = AsyncMock(ClientSession)
        mock_session.request.return_value = mock_response

        async def main():
            async with AsyncRestClient(MOCK_URL) as client:
                response = await client.handle_request()
                assert response.status == 200
                assert response.json() == {"data": "test"}
