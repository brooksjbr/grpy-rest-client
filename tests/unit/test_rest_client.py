import asyncio
from unittest.mock import MagicMock, patch
from urllib.parse import urljoin

import pytest
from aiohttp import ClientResponseError, ClientSession, ClientTimeout

from grpy.rest_client import RestClient


@pytest.fixture
def base_url():
    return "https://api.example.com"


@pytest.fixture
def endpoint():
    return "/v1/resource"


@pytest.fixture
async def rest_client(base_url):
    async with RestClient(url=base_url) as client:
        yield client


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
        async with RestClient(url=base_url) as client:
            assert client.session is not None
            assert not client.session.closed

        # After exiting context, session should be closed
        assert client.session.closed


class TestRestClientRequests:
    @pytest.mark.asyncio
    async def test_handle_request_get(self, base_url, endpoint):
        # Create a Future to be returned by the request method
        future = asyncio.Future()
        mock_response = MagicMock()
        mock_response.status = 200

        # Create a separate future for the json method
        json_future = asyncio.Future()
        json_future.set_result({"data": "test"})
        mock_response.json = lambda: json_future

        future.set_result(mock_response)

        with patch.object(ClientSession, "request", return_value=future) as mock_request:
            async with RestClient(url=base_url, endpoint=endpoint) as client:
                response = await client.handle_request()

                mock_request.assert_called_once_with(
                    method="GET",
                    url=urljoin(base_url, endpoint),
                    headers=client.headers,
                    params={},
                    timeout=client.timeout_obj,
                )

                assert response == mock_response

    @pytest.mark.asyncio
    async def test_handle_request_post_with_json(self, base_url):
        # Create a Future to be returned by the request method
        future = asyncio.Future()
        mock_response = MagicMock()
        mock_response.status = 201

        # Create a separate future for the json method
        json_future = asyncio.Future()
        json_future.set_result({"id": "123"})
        mock_response.json = lambda: json_future

        future.set_result(mock_response)

        json_data = {"name": "test", "value": 42}

        with patch.object(ClientSession, "request", return_value=future) as mock_request:
            async with RestClient(url=base_url, method="POST") as client:
                response = await client.handle_request(json=json_data)

                mock_request.assert_called_once_with(
                    method="POST",
                    url=base_url,
                    headers=client.headers,
                    params={},
                    timeout=client.timeout_obj,
                    json=json_data,
                )

                assert response == mock_response

    @pytest.mark.asyncio
    async def test_handle_request_timeout(self, base_url):
        """Test that timeout errors are properly handled"""
        # Create a client
        client = RestClient(url=base_url)

        # Create a mock session
        mock_session = MagicMock()

        # Configure the mock session to raise a timeout error
        async def mock_request(*args, **kwargs):
            raise asyncio.TimeoutError("Connection timed out")

        mock_session.request = mock_request
        mock_session.closed = False

        # Set the mock session directly on the client
        client.session = mock_session

        # Test the handle_request method
        with pytest.raises(asyncio.TimeoutError) as excinfo:
            await client.handle_request()

        # Verify the error message
        assert "Request timed out" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_handle_request_error(self, base_url):
        """Test that HTTP errors are properly handled"""
        # Create a client
        client = RestClient(url=base_url)

        # Create a mock session
        mock_session = MagicMock()

        # Create an error to be raised
        error = ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=404,
            message="Not Found",
        )

        # Configure the mock session to raise the error
        async def mock_request(*args, **kwargs):
            raise error

        mock_session.request = mock_request
        mock_session.closed = False

        # Set the mock session directly on the client
        client.session = mock_session

        # Test the handle_request method
        with pytest.raises(ClientResponseError) as excinfo:
            await client.handle_request()

        # Verify the error
        assert excinfo.value == error


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
