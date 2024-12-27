from asyncio import TimeoutError
from unittest.mock import patch

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
