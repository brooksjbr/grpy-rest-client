from unittest.mock import AsyncMock, Mock, patch

import pytest
from aiohttp import ClientSession

from grpy.rest_client import RestClient

TEST_URL = "https://api.example.com"
TEST_ENDPOINT = "/test"
TIMEOUT = 5


@pytest.fixture
def mock_client_session():
    session = Mock(spec=ClientSession)
    session.close = AsyncMock()
    session.closed = False
    return session


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE"])
@pytest.mark.asyncio
async def test_rest_client_context_manager_cleanup_multiple_methods(
    mock_client_session, method
):
    """Test conntext manager cleanup for multiple methods."""
    with patch("aiohttp.ClientSession", return_value=mock_client_session):
        async with RestClient(
            url=TEST_URL, method=method, endpoint=TEST_ENDPOINT, timeout=TIMEOUT
        ) as client:
            assert isinstance(client.session, ClientSession)
            assert not client.session.closed

        await mock_client_session.close()
        assert mock_client_session.close.called


@pytest.mark.asyncio
async def test_rest_client_context_manager_cleanup_with_exception(
    mock_client_session,
):
    """Test conntext manager cleanup with exception."""
    with patch("aiohttp.ClientSession", return_value=mock_client_session):
        with pytest.raises(ValueError):
            async with RestClient(
                url=TEST_URL, endpoint=TEST_ENDPOINT, timeout=TIMEOUT
            ) as client:
                assert isinstance(client.session, ClientSession)
                assert not client.session.closed
                raise ValueError("Test exception")

        await mock_client_session.close()
        assert mock_client_session.close.called
