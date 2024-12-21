import pytest
import requests
import requests_mock

from src.grpy.rest_client import RestClient
from tests.unit.test_rest_client_base import TestRestClientBase

MOCK_URL = "https://api.example.com"


class TestRestClientExceptions(TestRestClientBase):
    """
    Test cases for RequestClient exception handling.
    """

    @pytest.fixture
    def client(self):
        """Setup fixture for RequestClient initialization"""
        return RestClient(MOCK_URL)

    @pytest.fixture
    def mock(self):
        """Setup fixture for requests_mock."""
        with requests_mock.Mocker() as m:
            yield m

    def test_post_request(self, mock, client):
        """Test POST request with mocked response."""
        request_data = {"name": "Test"}
        expected_response = {"id": 1, "name": "Test"}
        mock.post(MOCK_URL, json=expected_response)

        client.method = "POST"
        response = client.make_request(json=request_data)
        assert response.json() == expected_response
        assert response.status_code == 200

    def test_failed_request(self, mock, client):
        """Test failed request handling."""
        mock.get(MOCK_URL, exc=requests.exceptions.HTTPError)
        with pytest.raises(requests.exceptions.HTTPError):
            client.make_request()

    def test_request_timeout(self, mock, client):
        """Test request timeout handling."""
        mock.get(MOCK_URL, exc=requests.exceptions.Timeout)
        with pytest.raises(requests.exceptions.Timeout):
            client.make_request()

    def test_request_connection_error(self, mock, client):
        """Test connection error handling."""
        mock.get(MOCK_URL, exc=requests.exceptions.ConnectionError)
        with pytest.raises(requests.exceptions.ConnectionError):
            client.make_request()
