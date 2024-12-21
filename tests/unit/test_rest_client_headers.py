import pytest

from src.grpy.rest_client import RestClient
from tests.unit.test_rest_client_base import TestRestClientBase

MOCK_URL = "https://api.example.com"


class TestRestClientHeaders(TestRestClientBase):
    """
    Test cases for RequestClient header functionality.
    """

    @pytest.fixture
    def client(self):
        """Setup fixture for RequestClient initialization"""
        return RestClient(MOCK_URL)

    @pytest.fixture
    def mock(self):
        """Setup fixture for requests_mock."""

    def test_default_headers(self, client):
        """Test client initialization with custom headers."""
        print(client.headers)
        assert client.headers["Accept"] == "*/*"

    def test_update_accept_headers(self, client):
        """Test client initialization with custom headers."""
        assert client.headers["Accept"] == "*/*"
        client.headers["Accept"] = "application/json"
        assert client.headers["Accept"] == "application/json"

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

    def test_clear_custom_header(self, client):
        """Test removing custom header."""
        client.headers["X-Custom"] = "Value"
        assert "X-Custom" in client.headers

        del client.headers["X-Custom"]
        with pytest.raises(KeyError):
            _ = client.headers["X-Custom"]
