import pytest

from src.grpy.rest_client import MissingRequestURL, RestClient
from tests.unit.test_rest_client_base import TestRestClientBase

MOCK_URL = "https://api.example.com"


class TestRestClientAttributes(TestRestClientBase):
    """
    Test cases for RequestClient attributes.
    """

    @pytest.fixture
    def client(self):
        """Setup fixture for RequestClient initialization"""
        return RestClient(MOCK_URL)

    @pytest.fixture
    def mock(self):
        """Setup fixture for requests_mock."""

    # Use the fixture only in tests that need it
    def test_client_url(self, client):
        """Test client initialization with default parameters."""
        assert client.url == MOCK_URL

    # Tests without the fixture parameter won't use it
    def test_client_missing_url(self):
        """Test client initialization with missing base URL."""
        with pytest.raises(MissingRequestURL):
            RestClient("")

    def test_client_context_manager(self):
        """Test RequestClient works properly as a context manager."""
        with RestClient(MOCK_URL) as client:
            assert client.url == MOCK_URL

            assert client.headers["Accept"] == "*/*"
