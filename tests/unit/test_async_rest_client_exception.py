from asyncio import TimeoutError
from unittest.mock import AsyncMock, patch

import pytest

from grpy.async_rest_client import AsyncRestClient

TEST_URL = "https://api.example.com"


class TestAsyncRestClientExceptions:
    """
    Test cases for AsyncRestClient exception handling.
    """

    @pytest.mark.parametrize(
        "status, exception_type",
        [
            (408, TimeoutError),
        ],
    )
    async def test_request_timeout_exception(self, status, exception_type):
        """Test that request timeout is properly handled"""

        with patch(
            "aiohttp.ClientSession.request",
            new=AsyncMock(side_effect=exception_type),
        ):
            with pytest.raises(exception_type):
                async with AsyncRestClient(TEST_URL) as client:
                    response = await client.handle_request()
                    assert response.status == status
                    assert response.exception_type == exception_type
