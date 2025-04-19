import asyncio
from unittest.mock import MagicMock

import pytest
from aiohttp import ClientSession

from grpy.rest_client import RestClient


@pytest.fixture
def base_url():
    return "https://api.example.com"


@pytest.fixture
def endpoint():
    return "/v1/resource"


@pytest.fixture
async def client_fixture(base_url):
    """
    Fixture that provides a RestClient instance within an async context manager.

    This ensures proper setup and cleanup of the client for each test.
    """
    async with RestClient(url=base_url) as client:
        yield client


@pytest.fixture
def mock_response_factory():
    """Factory fixture to create mock HTTP responses with customizable properties."""

    def _create_response(status=200, json_data=None, headers=None, text=None, raise_error=None):
        mock_response = MagicMock()
        mock_response.status = status
        mock_response.headers = headers or {}

        # Create async methods
        if json_data is not None:
            json_future = asyncio.Future()
            json_future.set_result(json_data)
            mock_response.json = lambda: json_future

        if text is not None:
            text_future = asyncio.Future()
            text_future.set_result(text)
            mock_response.text = lambda: text_future

        # For testing error cases
        if raise_error:

            async def raise_for_status():
                raise raise_error

            mock_response.raise_for_status = raise_for_status
        else:

            async def raise_for_status():
                return None

            mock_response.raise_for_status = raise_for_status

        return mock_response

    return _create_response


@pytest.fixture
def mock_client_session():
    """Fixture to create a mock ClientSession with configurable request responses."""

    def _create_session(response=None, side_effect=None):
        # Create a mock session
        mock_session = MagicMock(spec=ClientSession)

        # Configure the request method
        request_mock = MagicMock()

        if response:
            # Create a future to be returned by the request method
            future = asyncio.Future()
            future.set_result(response)
            request_mock.return_value = future
        elif side_effect:
            request_mock.side_effect = side_effect

        mock_session.request = request_mock
        mock_session.close = MagicMock(return_value=asyncio.Future())
        mock_session.closed = False

        return mock_session

    return _create_session
