import asyncio
from unittest.mock import MagicMock, patch
from urllib.parse import urljoin

import pytest
from aiohttp import ClientResponseError, ClientSession

from grpy.rest_client import RestClient


class TestRestClient:
    @pytest.fixture
    def base_url(self):
        return "https://api.example.com"

    @pytest.fixture
    def endpoint(self):
        return "/v1/resource"

    @pytest.fixture
    def mock_response_factory(self):
        """
        Factory fixture to create mock HTTP responses with
        customizable properties.
        """

        def _create_response(
            status=200,
            json_data=None,
            headers=None,
            text=None,
            raise_error=None,
        ):
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
    def mock_client_session(self):
        """
        Fixture to create a mock ClientSession with
        configurable request responses.
        """

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
            close_future = asyncio.Future()
            close_future.set_result(None)
            mock_session.close = MagicMock(return_value=close_future)
            mock_session.closed = False

            return mock_session

        return _create_session

    @pytest.mark.asyncio
    async def test_handle_request_with_mocked_session(
        self, base_url, endpoint, mock_response_factory, mock_client_session
    ):
        # Create a mock response
        mock_response = mock_response_factory(
            status=200, json_data={"success": True, "data": {"id": 123}}
        )

        # Create a mock session that returns our mock response
        mock_session = mock_client_session(response=mock_response)

        # Patch the ClientSession to return our mock
        with patch("grpy.rest_client.ClientSession", return_value=mock_session):
            async with RestClient(url=base_url, endpoint=endpoint) as client:
                response = await client.handle_request()

                # Verify the request was made with correct parameters
                mock_session.request.assert_called_once_with(
                    method="GET",
                    url=urljoin(base_url, endpoint),
                    headers=client.headers,
                    params={},
                    timeout=client.timeout_obj,
                )

                # Verify response
                assert response.status == 200
                json_data = await response.json()
                assert json_data["success"] is True
                assert json_data["data"]["id"] == 123

    @pytest.mark.asyncio
    async def test_handle_request_with_error(
        self, base_url, mock_client_session
    ):
        # Create an error to be raised
        error = ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=404,
            message="Not Found",
        )

        # Create a mock session that raises our error
        async def raise_error(*args, **kwargs):
            raise error

        mock_session = mock_client_session(side_effect=raise_error)

        # Patch the ClientSession to return our mock
        with patch("grpy.rest_client.ClientSession", return_value=mock_session):
            async with RestClient(url=base_url) as client:
                with pytest.raises(ClientResponseError) as excinfo:
                    await client.handle_request()

                assert excinfo.value == error

    @pytest.mark.asyncio
    async def test_timeout_handling(self, base_url, mock_client_session):
        # Create a mock session that times out
        async def timeout_error(*args, **kwargs):
            raise asyncio.TimeoutError("Connection timed out")

        mock_session = mock_client_session(side_effect=timeout_error)

        # Patch the ClientSession to return our mock
        with patch("grpy.rest_client.ClientSession", return_value=mock_session):
            async with RestClient(url=base_url) as client:
                with pytest.raises(asyncio.TimeoutError) as excinfo:
                    await client.handle_request()

                assert "Request timed out" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_context_manager_session_lifecycle(self, base_url):
        # Test that session is created and closed properly
        with patch("grpy.rest_client.ClientSession") as mock_session_class:
            # Setup mock session
            mock_session = MagicMock()
            mock_session.closed = False
            close_future = asyncio.Future()
            close_future.set_result(None)
            mock_session.close.return_value = close_future
            mock_session_class.return_value = mock_session

            # Use context manager
            async with RestClient(url=base_url) as client:
                assert client.session is mock_session
                assert not client.session.closed
                mock_session_class.assert_called_once()

            # After context exit, session should be closed
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_request_with_json_data(
        self, base_url, mock_response_factory, mock_client_session
    ):
        # Create a mock response
        mock_response = mock_response_factory(
            status=201, json_data={"id": "new-resource-id"}
        )

        # Create a mock session
        mock_session = mock_client_session(response=mock_response)

        # JSON data to send
        json_data = {"name": "test resource", "type": "example"}

        # Patch the ClientSession
        with patch("grpy.rest_client.ClientSession", return_value=mock_session):
            async with RestClient(url=base_url, method="POST") as client:
                response = await client.handle_request(json=json_data)

                # Verify request
                mock_session.request.assert_called_once_with(
                    method="POST",
                    url=base_url,
                    headers=client.headers,
                    params={},
                    timeout=client.timeout_obj,
                    json=json_data,
                )

                # Verify response
                assert response.status == 201
                json_response = await response.json()
                assert json_response["id"] == "new-resource-id"

    @pytest.mark.asyncio
    async def test_update_headers_during_request(
        self, base_url, mock_response_factory, mock_client_session
    ):
        # Create a mock response
        mock_response = mock_response_factory(status=200, json_data={})

        # Create a mock session
        mock_session = mock_client_session(response=mock_response)

        # Patch the ClientSession
        with patch("grpy.rest_client.ClientSession", return_value=mock_session):
            async with RestClient(url=base_url) as client:
                # Update headers
                client.update_headers({"Authorization": "Bearer token123"})

                # Make request
                await client.handle_request()

                # Verify headers were used in request
                called_kwargs = mock_session.request.call_args[1]
                assert (
                    called_kwargs["headers"]["Authorization"]
                    == "Bearer token123"
                )

    @pytest.mark.asyncio
    async def test_with_mocked_instance_methods(self, base_url):
        # Create a client
        client = RestClient(url=base_url)

        # Mock the handle_request method
        mock_response = MagicMock()
        mock_response.status = 200
        json_future = asyncio.Future()
        json_future.set_result({"mocked": True})
        mock_response.json = lambda: json_future

        # Directly return the mock_response instead of wrapping it in a Future
        # This is the key change to fix the error
        async def mock_handle_request(*args, **kwargs):
            return mock_response

        # Patch the instance method
        with patch.object(
            RestClient, "handle_request", side_effect=mock_handle_request
        ) as mock_method:
            # Create a session for the client
            client.session = MagicMock()

            # Call the mocked method
            response = await client.handle_request(custom_param="value")

            # Verify the method was called with expected args
            mock_method.assert_called_once_with(custom_param="value")

            # Verify we got our mocked response
            assert response.status == 200
            json_data = await response.json()
            assert json_data["mocked"] is True

    @pytest.mark.asyncio
    async def test_request_with_custom_parameters(
        self, base_url, mock_response_factory, mock_client_session
    ):
        # Create a mock response
        mock_response = mock_response_factory(status=200, json_data={})

        # Create a mock session
        mock_session = mock_client_session(response=mock_response)

        # Patch the ClientSession
        with patch("grpy.rest_client.ClientSession", return_value=mock_session):
            async with RestClient(url=base_url) as client:
                # Update params
                client.update_params({"filter": "active", "page": 1})

                # Make request with additional parameters
                await client.handle_request(
                    data="raw data", allow_redirects=False, ssl=False
                )

                # Verify all parameters were passed correctly
                mock_session.request.assert_called_once_with(
                    method="GET",
                    url=base_url,
                    headers=client.headers,
                    params={"filter": "active", "page": 1},
                    timeout=client.timeout_obj,
                    data="raw data",
                    allow_redirects=False,
                    ssl=False,
                )
