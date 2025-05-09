import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urljoin

import pytest
from aiohttp import ClientResponseError, ClientTimeout
from aiohttp import ContentTypeError as AiohttpContentTypeError

from src.grpy.pagination_strategy_protocol import PaginationStrategy
from src.grpy.rest_client import RestClient, RestClientError
from src.grpy.retry_manager import RetryPolicy


# Add fixtures for pagination and retry components
@pytest.fixture
def mock_pagination_strategy():
    """Create a mock pagination strategy."""
    strategy = MagicMock(spec=PaginationStrategy)
    strategy.extract_items.return_value = ["item1", "item2"]
    strategy.get_next_page_info.return_value = (False, {})
    return strategy


@pytest.fixture
def mock_retry_policy():
    """Create a mock retry policy."""
    policy = MagicMock(spec=RetryPolicy)

    async def execute_with_retry(func, *args, **kwargs):
        return await func(*args, **kwargs)

    policy.execute_with_retry = AsyncMock(side_effect=execute_with_retry)
    return policy


class TestRestClientInitialization:
    def test_init_with_defaults(self, base_url):
        client = RestClient(url=base_url)
        assert client.url == base_url
        assert client.method == "GET"
        assert client.endpoint == ""
        assert client.timeout == 60
        assert client.session is None
        assert client.params == {}
        assert client.headers == RestClient.DEFAULT_HEADERS.copy()
        assert isinstance(client.timeout_obj, ClientTimeout)
        assert client.timeout_obj.total == 60
        # New assertions for managers and strategies
        assert client._pagination_manager is not None
        assert client._retry_manager is not None
        assert client.pagination_strategy is not None
        assert client.retry_policy is not None

    def test_init_with_custom_values(self, base_url, endpoint):
        custom_headers = {"X-Custom-Header": "value"}
        custom_params = {"param1": "value1"}

        client = RestClient(
            url=base_url,
            method="POST",
            endpoint=endpoint,
            timeout=30,
            params=custom_params,
            headers=custom_headers,
        )

        assert client.url == base_url
        assert client.method == "POST"
        assert client.endpoint == endpoint
        assert client.timeout == 30
        assert client.params == custom_params

        # Headers should be merged with defaults
        for key, value in RestClient.DEFAULT_HEADERS.items():
            if key not in custom_headers:
                assert client.headers[key] == value
        assert client.headers["X-Custom-Header"] == "value"

        assert client.timeout_obj.total == 30

    def test_init_includes_exit_stack(self, base_url):
        client = RestClient(url=base_url)
        assert client._exit_stack is None  # Now None until context is entered
        assert client.session is None

    def test_init_with_custom_pagination_strategy(self, base_url, mock_pagination_strategy):
        """Test initialization with a custom pagination strategy."""
        client = RestClient(url=base_url, pagination_strategy=mock_pagination_strategy)
        assert client.pagination_strategy is mock_pagination_strategy

    def test_init_with_custom_retry_policy(self, base_url, mock_retry_policy):
        """Test initialization with a custom retry policy."""
        client = RestClient(url=base_url, retry_policy=mock_retry_policy)
        assert client.retry_policy is mock_retry_policy

    def test_init_with_strategy_name(self, base_url):
        """Test initialization with a pagination strategy name."""
        with patch(
            "src.grpy.pagination_manager.PaginationManager.get_strategy"
        ) as mock_get_strategy:
            mock_strategy = MagicMock(spec=PaginationStrategy)
            mock_get_strategy.return_value = mock_strategy

            client = RestClient(url=base_url, pagination_strategy="page_number")

            mock_get_strategy.assert_called_once_with("page_number")
            assert client.pagination_strategy is mock_strategy

    def test_init_with_policy_name(self, base_url):
        """Test initialization with a retry policy name."""
        with patch("src.grpy.retry_manager.RetryManager.get_policy") as mock_get_policy:
            mock_policy = MagicMock(spec=RetryPolicy)
            mock_get_policy.return_value = mock_policy

            client = RestClient(url=base_url, retry_policy="exponential")

            mock_get_policy.assert_called_once_with("exponential")
            assert client.retry_policy is mock_policy


class TestRestClientValidation:
    def test_validate_http_method_valid(self):
        for method in RestClient.VALID_METHODS:
            client = RestClient(url="https://example.com", method=method)
            assert client.method == method

            # Test lowercase methods are converted to uppercase
            if method != method.lower():
                client = RestClient(url="https://example.com", method=method.lower())
                assert client.method == method

    def test_validate_http_method_invalid(self):
        with pytest.raises(ValueError) as excinfo:
            RestClient(url="https://example.com", method="INVALID")
        assert "Invalid HTTP method" in str(excinfo.value)

    def test_validate_timeout_valid(self):
        client = RestClient(url="https://example.com", timeout=10)
        assert client.timeout == 10

        client = RestClient(url="https://example.com", timeout=0.5)
        assert client.timeout == 0.5

    def test_validate_timeout_invalid(self):
        with pytest.raises(ValueError) as excinfo:
            RestClient(url="https://example.com", timeout=0)
        assert "Timeout must be a positive number" in str(excinfo.value)

        with pytest.raises(ValueError):
            RestClient(url="https://example.com", timeout=-1)

        with pytest.raises(ValueError):
            RestClient(url="https://example.com", timeout="invalid")


class TestRestClientContextManager:
    @pytest.mark.asyncio
    async def test_context_manager(self, base_url):
        session = None

        async with RestClient(url=base_url) as client:
            assert client.session is not None
            assert not client.session.closed
            assert client._exit_stack is not None
            session = client.session

        # After exiting context, session should be closed
        assert session.closed
        # Exit stack should be None after context exit
        assert client._exit_stack is None
        assert client.session is None

    @pytest.mark.asyncio
    async def test_external_session_reuse(self, base_url, mock_client_session):
        # Create a mock session
        mock_session = mock_client_session()

        # Use the session with a client
        async with RestClient(url=base_url, session=mock_session) as client:
            assert client.session is mock_session
            assert not mock_session.closed

        # After client context exits, external session should still be open
        # This is the key test - the RestClient should not close an external session
        assert not mock_session.closed

        # Manually close the session
        await mock_session.close()
        assert mock_session.closed

    @pytest.mark.asyncio
    async def test_cleanup_after_context_exit(self, base_url):
        """Test that resources are cleaned up after context exit."""
        # Create a client
        client = RestClient(url=base_url)

        # Enter the client context
        async with client:
            # Verify resources are created
            assert client.session is not None
            assert client._exit_stack is not None

        # Verify resources are cleaned up
        assert client.session is None
        assert client._exit_stack is None


class TestRestClientRequests:
    @pytest.mark.asyncio
    async def test_request_get(
        self,
        base_url,
        endpoint,
        mock_client_session,
        enhanced_mock_response_factory,
        mock_retry_policy,
    ):
        # Create a mock response
        mock_response = enhanced_mock_response_factory(json_data={"data": "test"})

        # Create a mock session
        mock_session = mock_client_session(response=mock_response)

        # Create a client and set the mock session and retry policy
        client = RestClient(url=base_url, endpoint=endpoint)
        client.session = mock_session
        client.retry_policy = mock_retry_policy

        # Execute the request
        response = await client.request()

        # Verify the request was made correctly
        mock_session.request.assert_called_once_with(
            method="GET",
            url=urljoin(base_url, endpoint),
            headers=client.headers,
            params={},
            timeout=client.timeout_obj,
            json=None,
        )

        # Verify retry policy was used
        mock_retry_policy.execute_with_retry.assert_called_once()

        assert response == mock_response

    @pytest.mark.asyncio
    async def test_request_post_with_json(
        self, base_url, mock_client_session, enhanced_mock_response_factory, mock_retry_policy
    ):
        # Create a mock response
        mock_response = enhanced_mock_response_factory(status=201, json_data={"id": "123"})

        # Create a mock session
        mock_session = mock_client_session(response=mock_response)

        # Create a client and set the mock session and retry policy
        client = RestClient(url=base_url, method="POST")
        client.session = mock_session
        client.retry_policy = mock_retry_policy

        # JSON data to send
        json_data = {"name": "test", "value": 42}

        # Execute the request
        response = await client.request(data=json_data)

        # Verify the request was made correctly
        mock_session.request.assert_called_once_with(
            method="POST",
            url=base_url,
            headers=client.headers,
            params={},
            timeout=client.timeout_obj,
            json=json_data,
        )

        # Verify retry policy was used
        mock_retry_policy.execute_with_retry.assert_called_once()

        assert response == mock_response

    @pytest.mark.asyncio
    async def test_request_timeout(self, base_url, mock_client_session, mock_retry_policy):
        """Test that timeout errors are properly handled"""

        # Create a mock session that raises a timeout error
        async def timeout_side_effect(*args, **kwargs):
            raise asyncio.TimeoutError("Connection timed out")

        mock_session = mock_client_session(side_effect=timeout_side_effect)

        # Create a client and set the mock session and retry policy
        client = RestClient(url=base_url)
        client.session = mock_session

        # Configure retry policy to pass through the exception
        async def execute_with_retry_raising_timeout(func, *args, **kwargs):
            raise asyncio.TimeoutError("Connection timed out")

        mock_retry_policy.execute_with_retry = AsyncMock(
            side_effect=execute_with_retry_raising_timeout
        )
        client.retry_policy = mock_retry_policy

        # Test the request method
        with pytest.raises(asyncio.TimeoutError) as excinfo:
            await client.request()

        # Verify the error message
        assert "Connection timed out" in str(excinfo.value)

        # Verify retry policy was used
        mock_retry_policy.execute_with_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_error(
        self, base_url, mock_client_session, enhanced_mock_response_factory, mock_retry_policy
    ):
        """Test that HTTP errors are properly handled"""
        # Create a request_info mock with a real_url attribute
        request_info_mock = MagicMock()
        request_info_mock.real_url = f"{base_url}/resource"

        # Create a mock response with 404 status
        mock_response = enhanced_mock_response_factory(status=404, text="Not Found")
        mock_response.request_info = request_info_mock

        # Configure raise_for_status to raise an error
        async def raise_error():
            error = ClientResponseError(
                request_info=request_info_mock,
                history=(),
                status=404,
                message="Not Found",
                headers={},
            )
            raise error

        mock_response.raise_for_status = raise_error

        # Create a mock session
        mock_session = mock_client_session(response=mock_response)

        # Create a client and set the mock session
        client = RestClient(url=base_url)
        client.session = mock_session

        # Configure retry policy to pass through the exception
        async def execute_with_retry_raising_http_error(func, *args, **kwargs):
            error = ClientResponseError(
                request_info=request_info_mock,
                history=(),
                status=404,
                message="Not Found",
                headers={},
            )
            raise error

        mock_retry_policy.execute_with_retry = AsyncMock(
            side_effect=execute_with_retry_raising_http_error
        )
        client.retry_policy = mock_retry_policy

        # Test the request method
        with pytest.raises(ClientResponseError) as excinfo:
            await client.request()

        # Verify the error details
        assert excinfo.value.status == 404

    @pytest.mark.asyncio
    async def test_request_with_context_manager(
        self, base_url, endpoint, enhanced_mock_response_factory, mock_client_session
    ):
        """Test that request works properly with the context manager."""
        # Create a mock response
        mock_response = enhanced_mock_response_factory(json_data={"data": "test"})

        # Create a mock session
        mock_session = mock_client_session(response=mock_response)

        # Create a client without setting the session
        client = RestClient(url=base_url, endpoint=endpoint)

        # Use the client in a context manager
        async with client:
            # Replace the auto-created session with our mock for testing
            original_session = client.session
            client.session = mock_session

            # Execute the request
            response = await client.request()

            # Verify the request was made correctly
            mock_session.request.assert_called_once_with(
                method="GET",
                url=urljoin(base_url, endpoint),
                headers=client.headers,
                params={},
                timeout=client.timeout_obj,
                json=None,
            )

            assert response == mock_response

            # Restore the original session to avoid cleanup issues
            client.session = original_session

    @pytest.mark.asyncio
    async def test_exit_stack_session_management(self, base_url):
        """Test that AsyncExitStack properly manages the session lifecycle."""
        # Create a client
        client = RestClient(url=base_url)

        # Enter the client context
        async with client:
            # Verify the exit stack and session are created
            assert client._exit_stack is not None
            assert client.session is not None
            assert not client.session.closed

            # Store references for verification after context exit
            session = client.session

            # Mark the session as internal (not external)
            assert not hasattr(session, "_external")

        # After exiting the context, resources should be cleaned up
        assert client._exit_stack is None
        assert client.session is None
        assert session.closed


class TestRestClientUtilities:
    def test_update_headers(self, base_url):
        client = RestClient(url=base_url)
        original_headers = client.headers.copy()

        new_headers = {
            "Authorization": "Bearer token123",
            "X-Custom-Header": "value",
        }

        client.update_headers(new_headers)

        # Original headers should be preserved
        for key, value in original_headers.items():
            if key not in new_headers:
                assert client.headers[key] == value

        # New headers should be added
        for key, value in new_headers.items():
            assert client.headers[key] == value

    def test_update_params(self, base_url):
        client = RestClient(url=base_url, params={"existing": "param"})

        client.update_params({"new": "value", "page": 1})

        assert client.params == {"existing": "param", "new": "value", "page": 1}

    def test_update_timeout(self, base_url):
        client = RestClient(url=base_url)
        original_timeout = client.timeout

        client.update_timeout(120)

        assert client.timeout == 120
        assert client.timeout_obj.total == 120
        assert client.timeout != original_timeout

        # Test with active session
        client.session = MagicMock()
        client.update_timeout(30)

        assert client.timeout == 30
        assert client.timeout_obj.total == 30
        assert client.session._timeout == client.timeout_obj

    def test_update_data_with_none_data(self, base_url):
        client = RestClient(url=base_url)
        assert client.data is None

        client.update_data({"new": "data", "count": 42})

        assert client.data == {"new": "data", "count": 42}

    def test_update_data_overwrites_existing_keys(self, base_url):
        client = RestClient(url=base_url, data={"key1": "original", "key2": "value"})

        client.update_data({"key1": "updated"})

        assert client.data == {"key1": "updated", "key2": "value"}


class TestRestClientPagination:
    @pytest.mark.asyncio
    async def test_paginate_json_parse_error(
        self, base_url, mock_client_session, enhanced_mock_response_factory
    ):
        """Test that JSON parsing errors in paginate are properly handled."""
        # Create a mock response that will raise a ContentTypeError when json() is called
        mock_response = enhanced_mock_response_factory(status=200, text="Not JSON data")

        # Create a request_info mock with a real_url attribute
        request_info_mock = MagicMock()
        request_info_mock.real_url = f"{base_url}/resource"

        # Override the json method to raise ContentTypeError with proper request_info
        async def json_error():
            raise AiohttpContentTypeError(
                request_info=request_info_mock,
                history=(),
                message="Attempt to decode JSON with unexpected mimetype: text/plain",
                headers={"Content-Type": "text/plain"},
            )

        mock_response.json = json_error
        mock_response.request_info = request_info_mock

        # Create a mock session
        mock_session = mock_client_session(response=mock_response)

        # Create a client and set the mock session
        client = RestClient(url=base_url)
        client.session = mock_session

        # Test the paginate method - use await instead of async for
        with pytest.raises(RestClientError) as excinfo:
            await client.get_all_pages()

        # Verify the error message
        assert "Failed to parse JSON response" in str(excinfo.value)
        assert "Attempt to decode JSON with unexpected mimetype" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_get_all_pages_json_parse_error(
        self, base_url, mock_client_session, enhanced_mock_response_factory
    ):
        """Test that JSON parsing errors in get_all_pages are properly handled."""
        # Create a mock response that will raise a ContentTypeError when json() is called
        mock_response = enhanced_mock_response_factory(status=200, text="Not JSON data")

        # Create a request_info mock with a real_url attribute
        request_info_mock = MagicMock()
        request_info_mock.real_url = f"{base_url}/resource"

        # Override the json method to raise ContentTypeError with proper request_info
        async def json_error():
            raise AiohttpContentTypeError(
                request_info=request_info_mock,
                history=(),
                message="Attempt to decode JSON with unexpected mimetype: text/plain",
                headers={"Content-Type": "text/plain"},
            )

        mock_response.json = json_error
        mock_response.request_info = request_info_mock

        # Create a mock session
        mock_session = mock_client_session(response=mock_response)

        # Create a client and set the mock session
        client = RestClient(url=base_url)
        client.session = mock_session

        # Test the get_all_pages method - use await instead of async for
        with pytest.raises(RestClientError) as excinfo:
            await client.get_all_pages()

        # Verify the error message
        assert "Failed to parse JSON response" in str(excinfo.value)
        assert "Attempt to decode JSON with unexpected mimetype" in str(excinfo.value)
