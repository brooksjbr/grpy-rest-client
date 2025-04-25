import asyncio
from unittest.mock import MagicMock
from urllib.parse import urljoin

import pytest
from aiohttp import ClientResponseError, ClientTimeout
from aiohttp import ContentTypeError as AiohttpContentTypeError

from src.grpy.rest_client import RestClient, RestClientError


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
        session = None
        async with RestClient(url=base_url) as client:
            assert client.session is not None
            assert not client.session.closed
            session = client.session

        # After exiting context, session should be closed
        assert session.closed


class TestRestClientRequests:
    @pytest.mark.asyncio
    async def test_handle_request_get(
        self, base_url, endpoint, mock_client_session, enhanced_mock_response_factory
    ):
        # Create a mock response
        mock_response = enhanced_mock_response_factory(json_data={"data": "test"})

        # Create a mock session
        mock_session = mock_client_session(response=mock_response)

        # Create a client and set the mock session
        client = RestClient(url=base_url, endpoint=endpoint)
        client.session = mock_session

        # Execute the request
        response = await client.handle_request()

        # Verify the request was made correctly
        mock_session.request.assert_called_once_with(
            method="GET",
            url=urljoin(base_url, endpoint),
            headers=client.headers,
            params={},
            timeout=client.timeout_obj,
        )

        assert response == mock_response

    @pytest.mark.asyncio
    async def test_handle_request_post_with_json(
        self, base_url, mock_client_session, enhanced_mock_response_factory
    ):
        # Create a mock response
        mock_response = enhanced_mock_response_factory(status=201, json_data={"id": "123"})

        # Create a mock session
        mock_session = mock_client_session(response=mock_response)

        # Create a client and set the mock session
        client = RestClient(url=base_url, method="POST")
        client.session = mock_session

        # JSON data to send
        json_data = {"name": "test", "value": 42}

        # Execute the request
        response = await client.handle_request(json=json_data)

        # Verify the request was made correctly
        mock_session.request.assert_called_once_with(
            method="POST",
            url=base_url,
            headers=client.headers,
            params={},
            timeout=client.timeout_obj,
            json=json_data,
        )

        assert response == mock_response

    @pytest.mark.asyncio
    async def test_handle_request_timeout(self, base_url, mock_client_session):
        """Test that timeout errors are properly handled"""

        # Create a mock session that raises a timeout error
        async def timeout_side_effect(*args, **kwargs):
            raise asyncio.TimeoutError("Connection timed out")

        mock_session = mock_client_session(side_effect=timeout_side_effect)

        # Create a client and set the mock session
        client = RestClient(url=base_url)
        client.session = mock_session

        # Test the handle_request method
        with pytest.raises(asyncio.TimeoutError) as excinfo:
            await client.handle_request()

        # Verify the error message
        assert "Connection timed out" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_handle_request_error(
        self, base_url, mock_client_session, enhanced_mock_response_factory
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

        # Test the handle_request method
        with pytest.raises(ClientResponseError) as excinfo:
            await client.handle_request()

        # Verify the error details
        assert excinfo.value.status == 404


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

        # Test the paginate method
        with pytest.raises(RestClientError) as excinfo:
            async for _ in client.paginate():
                pass  # This should not execute

        # Verify the error message
        assert "Failed to parse JSON response" in str(excinfo.value)
        assert "Attempt to decode JSON with unexpected mimetype" in str(excinfo.value)
