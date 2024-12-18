"""
Unit tests for RequestClient class

Usage:
    Run with pytest:
    $ pytest tests/

Dependencies:
    - pytest
"""

import pytest
import requests_mock

from grpy.rest_client import MissingRequestURL, RestClient


class TestRestClient:
    """
    Test cases for core client functionality.

    Tests the basic operations of the client including:
    - Initialization
    """

    @pytest.fixture
    def mock(self):
        """Setup fixture for requests_mock."""
        with requests_mock.Mocker() as m:
            yield m

    @pytest.fixture
    def client(self):
        """Setup fixture for RequestClient initialization"""
        url = "https://api.example.com/"
        return RestClient(url)

    # Use the fixture only in tests that need it
    def test_client_url(self, client):
        """Test client initialization with default parameters."""
        assert client.url == "https://api.example.com/"

    def test_default_headers(self, client):
        """Test client initialization with custom headers."""
        assert client.headers["Accept"] == "*/*"

    # Tests without the fixture parameter won't use it
    def test_client_missing_url(self):
        """Test client initialization with missing base URL."""
        url = ""
        with pytest.raises(MissingRequestURL):
            RestClient(url)

    def test_update_accept(self, client):
        """Test client initialization with custom headers."""
        assert client.headers["Accept"] == "*/*"
        client.headers["Accept"] = "application/json"
        assert client.headers["Accept"] == "application/json"

    def test_missing_content_type_header_key(self, client):
        """Test missing header key raises KeyError."""
        with pytest.raises(KeyError):
            _ = client.headers["Content-Type"]

    def test_add_content_type_header(self, client):
        """Test client initialization with custom headers."""
        headers = {"Content-Type": "application/xml"}
        client.headers.update(headers)
        assert client.headers["Content-Type"] == headers["Content-Type"]

    def test_add_custom_header(self, client):
        """Test client initialization with custom headers."""
        headers = {"Custom-Header": "My Custom Header"}
        client.headers.update(headers)
        assert client.headers["Custom-Header"] == headers["Custom-Header"]

    def test_multiple_header_updates(self, client):
        """Test multiple header updates maintain correct state."""

        # First update
        client.headers.update({"X-Custom-1": "Value1"})
        assert client.headers["X-Custom-1"] == "Value1"

        # Second update
        client.headers.update({"X-Custom-2": "Value2"})
        assert client.headers["X-Custom-1"] == "Value1"
        assert client.headers["X-Custom-2"] == "Value2"

    def test_override_existing_header(self, client):
        """Test overriding existing header values."""
        original_user_agent = client.headers["User-Agent"]

        client.headers["User-Agent"] = "CustomAgent/1.0"
        assert client.headers["User-Agent"] == "CustomAgent/1.0"
        assert client.headers["User-Agent"] != original_user_agent

    def test_clear_custom_header(self, client):
        """Test removing custom header."""
        client.headers["X-Custom"] = "Value"
        assert "X-Custom" in client.headers

        del client.headers["X-Custom"]
        with pytest.raises(KeyError):
            _ = client.headers["X-Custom"]

    def test_client_context_manager(self):
        """Test RequestClient works properly as a context manager."""
        url = "https://api.example.com"
        with RestClient(url) as client:
            assert client.url == url

            assert client.headers["Accept"] == "*/*"

    def test_get_request(self, mock, client):
        """Test GET request with mocked response."""
        expected_response = {"id": 1, "name": "Test"}
        mock.get("https://api.example.com/", json=expected_response)

        response = client.get("https://api.example.com/")
        assert response.json() == expected_response
        assert response.status_code == 200

    def test_post_request(self, mock, client):
        """Test POST request with mocked response."""
        request_data = {"name": "Test"}
        expected_response = {"id": 1, "name": "Test"}
        mock.post("https://api.example.com/", json=expected_response)

        response = client.post("https://api.example.com/", json=request_data)
        assert response.json() == expected_response
        assert response.status_code == 200

    def test_failed_request(self, mock, client):
        """Test failed request handling."""
        mock.get("https://api.example.com/error", status_code=404)

        response = client.get("https://api.example.com/error")
        assert response.status_code == 404

    def test_request_headers(self, mock, client):
        """Test custom headers in request."""
        client.headers.update({"X-Custom-Header": "test"})
        mock.get("https://api.example.com/headers", text="ok")

        client.get("https://api.example.com/headers")
        assert mock.last_request.headers["X-Custom-Header"] == "test"
