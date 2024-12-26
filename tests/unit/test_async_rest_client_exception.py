from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientSession, ClientTimeout

from grpy.async_rest_client import AsyncRestClient

MOCK_URL = "https://test.api.com"


@pytest.mark.asyncio
class TestAsyncRestClientException:
    """Test cases for the AsyncRestClient exceptions."""

    async def test_async_rest_client_timeout(self):
        """Test handling of request timeout."""
        mock_response = AsyncMock()
        mock_response.side_effect = ClientTimeout()

        mock_session = AsyncMock(ClientSession)
        mock_session.request.return_value = mock_response

        async def main():
            async with AsyncRestClient(MOCK_URL) as client:
                with pytest.raises(TimeoutError):
                    await client.handle_exception()
