import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientSession

from src.grpy.rest_client import RestClient
from src.grpy.retry import ExponentialBackoffRetry


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
def enhanced_mock_response_factory():
    """
    Enhanced factory fixture to create mock HTTP responses with pagination support.
    """

    def _create_response(
        status=200,
        json_data=None,
        headers=None,
        text=None,
        raise_error=None,
        pagination_type=None,
        page_number=0,
        has_next=True,
        total_pages=3,
    ):
        mock_response = MagicMock()
        mock_response.status = status
        mock_response.headers = headers or {}

        # Generate pagination data if requested
        if pagination_type == "page_number" and json_data is None:
            json_data = {
                "items": [{"id": f"item{i}", "name": f"Item {i}"} for i in range(1, 3)],
                "page": {
                    "size": 2,
                    "totalElements": 5,
                    "totalPages": total_pages,
                    "number": page_number,
                },
            }
        elif pagination_type == "hateoas" and json_data is None:
            json_data = {
                "_embedded": {
                    "events": [{"id": f"event{i}", "name": f"Event {i}"} for i in range(1, 3)]
                },
                "page": {
                    "size": 2,
                    "totalElements": 5,
                    "totalPages": total_pages,
                    "number": page_number,
                },
            }

            # Add HATEOAS links
            links = {"self": {"href": f"/events?page={page_number}&size=2"}}
            if has_next:
                links["next"] = {"href": f"/events?page={page_number + 1}&size=2"}
            if page_number > 0:
                links["prev"] = {"href": f"/events?page={page_number - 1}&size=2"}

            json_data["_links"] = links

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
    def _create_session(response=None, side_effect=None):
        mock_session = MagicMock(spec=ClientSession)
        mock_session.closed = False

        # Mock the close method
        async def mock_close():
            mock_session.closed = True

        mock_session.close = mock_close

        # Mock the request method
        if side_effect:
            mock_session.request = AsyncMock(side_effect=side_effect)
        else:
            mock_session.request = AsyncMock(return_value=response)

        # Make session work as an async context manager
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        return mock_session

    return _create_session


@pytest.fixture
async def rest_client_factory(base_url):
    """
    Factory fixture that provides configurable RestClient instances.

    This allows tests to create clients with different configurations while
    ensuring proper cleanup.
    """
    clients = []

    async def _create_client(
        method="GET", endpoint="", timeout=60, params=None, headers=None, data=None
    ):
        client = RestClient(
            url=base_url,
            method=method,
            endpoint=endpoint,
            timeout=timeout,
            params=params,
            headers=headers,
            data=data,
        )
        await client.__aenter__()
        clients.append(client)
        return client

    yield _create_client

    # Clean up all created clients
    for client in clients:
        if client.session and not client.session.closed:
            await client.__aexit__(None, None, None)


# Page Number Pagination Fixtures
@pytest.fixture
def page_number_response():
    """Sample response with page number pagination."""
    return {
        "items": [
            {"id": "item1", "name": "Item 1"},
            {"id": "item2", "name": "Item 2"},
        ],
        "page": {
            "size": 2,
            "totalElements": 5,
            "totalPages": 3,
            "number": 0,  # First page (0-indexed)
        },
    }


@pytest.fixture
def last_page_response():
    """Sample response for the last page."""
    return {
        "items": [
            {"id": "item5", "name": "Item 5"},
        ],
        "page": {
            "size": 2,
            "totalElements": 5,
            "totalPages": 3,
            "number": 2,  # Last page (0-indexed)
        },
    }


# HATEOAS Pagination Fixtures
@pytest.fixture
def hateoas_page1_response():
    """Sample response for first page with HATEOAS links."""
    return {
        "_embedded": {
            "events": [
                {"id": "event1", "name": "Concert 1"},
                {"id": "event2", "name": "Concert 2"},
            ]
        },
        "_links": {
            "self": {"href": "/events?page=0&size=2"},
            "next": {"href": "/events?page=1&size=2"},
        },
        "page": {
            "size": 2,
            "totalElements": 5,
            "totalPages": 3,
            "number": 0,
        },
    }


@pytest.fixture
def hateoas_page2_response():
    """Sample response for middle page with HATEOAS links."""
    return {
        "_embedded": {
            "events": [
                {"id": "event3", "name": "Concert 3"},
                {"id": "event4", "name": "Concert 4"},
            ]
        },
        "_links": {
            "self": {"href": "/events?page=1&size=2"},
            "next": {"href": "/events?page=2&size=2"},
            "prev": {"href": "/events?page=0&size=2"},
        },
        "page": {
            "size": 2,
            "totalElements": 5,
            "totalPages": 3,
            "number": 1,
        },
    }


@pytest.fixture
def hateoas_last_page_response():
    """Sample response for last page with HATEOAS links."""
    return {
        "_embedded": {
            "events": [
                {"id": "event5", "name": "Concert 5"},
            ]
        },
        "_links": {
            "self": {"href": "/events?page=2&size=2"},
            "prev": {"href": "/events?page=1&size=2"},
        },
        "page": {
            "size": 2,
            "totalElements": 5,
            "totalPages": 3,
            "number": 2,
        },
    }


@pytest.fixture
def pagination_strategy_factory():
    """
    Factory fixture to create pagination strategy instances with configurable parameters.
    """

    def _create_strategy(strategy_class, **kwargs):
        return strategy_class(**kwargs)

    return _create_strategy


@pytest.fixture
def retry_strategy_factory():
    """
    Factory fixture to create retry strategy instances with configurable parameters.
    """

    def _create_strategy(
        strategy_class=ExponentialBackoffRetry,
        max_retries=3,
        initial_delay=0.01,  # Fast for testing
        max_delay=1.0,  # Fast for testing
        backoff_factor=2.0,
        jitter=False,  # Deterministic for testing
    ):
        return strategy_class(
            max_retries=max_retries,
            initial_delay=initial_delay,
            max_delay=max_delay,
            backoff_factor=backoff_factor,
            jitter=jitter,
        )

    return _create_strategy
