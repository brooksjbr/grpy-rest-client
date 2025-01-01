import pytest

from grpy.rest_client import RestClient, RestClientBase

MOCK_URL = "https://api.example.com"
MOCK_ENDPOINT = "/api/v1"
DEFAULT_TIMEOUT = RestClientBase.DEFAULT_TIMEOUT


@pytest.fixture
def rest_client():
    return RestClient(MOCK_URL)


class TestRestClientAttributes:
    """Test the RestClient class attributes."""

    def test_client_default_parameters(self, rest_client):
        assert rest_client.url == MOCK_URL
        assert rest_client.method == "GET"
        assert rest_client.endpoint == ""
        assert rest_client.timeout.total == DEFAULT_TIMEOUT
        assert rest_client.headers == RestClientBase.DEFAULT_HEADERS

    def test_update_headers(self, rest_client):
        rest_client.update_headers(
            {"Authorization": "Bearer token", "User-Agent": "new-user-agent"}
        )
        assert "Authorization" in rest_client.headers
        assert rest_client.headers["Authorization"] == "Bearer token"
        assert rest_client.headers["User-Agent"] == "new-user-agent"

    def test_custom_timeout(self, rest_client):
        assert rest_client.timeout.total == 60
        rest_client.update_timeout(120)
        assert rest_client.timeout.total == 120

    def test_invalid_method(self):
        with pytest.raises(ValueError):
            RestClient(MOCK_URL, method="INVALID")

    def test_update_request_method(self, rest_client):
        rest_client.method = "POST"
        assert rest_client.method == "POST"

    def test_request_params(self, rest_client):
        """Test request parameters are correctly passed"""
        assert rest_client.params == {}
        params = {"param1": "value1", "param2": "value2"}
        rest_client.update_params(params)
        assert rest_client.params == params

    def test_endpoint_with_leading_slash(self, rest_client):
        rest_client.endpoint = "/test"
        assert rest_client.endpoint == "/test"

    def test_endpoint_without_leading_slash(self, rest_client):
        rest_client.endpoint = "test"
        assert rest_client.endpoint == "test"

    def test_clear_headers(self, rest_client):
        original_headers = rest_client.headers.copy()
        rest_client.update_headers({})
        assert rest_client.headers == original_headers

    def test_update_partial_headers(self, rest_client):
        original_headers = rest_client.headers.copy()
        new_header = {"New-Header": "value"}
        rest_client.update_headers(new_header)
        assert all(
            item in rest_client.headers.items()
            for item in original_headers.items()
        )
        assert rest_client.headers["New-Header"] == "value"

    def test_invalid_timeout_type(self):
        with pytest.raises(ValueError, match="Timeout must be a number"):
            RestClient(MOCK_URL, timeout="invalid")

    def test_negative_timeout(self):
        with pytest.raises(ValueError, match="Timeout must be greater than 0"):
            RestClient(MOCK_URL, timeout=-1)
