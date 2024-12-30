import pytest

from grpy.rest_client import RestClient
from grpy.rest_client_base import RestClientBase

MOCK_URL = "https://api.example.com"
MOCK_ENDPOINT = "/api/v1"


@pytest.fixture
async def rest_client():
    async with RestClient(MOCK_URL) as client:
        yield client


@pytest.fixture(autouse=True)
async def reset_client(rest_client):
    yield


class TestRestClientAttributes:
    @pytest.mark.asyncio
    async def test_client_default_parameters(self, rest_client):
        assert rest_client.url == MOCK_URL
        assert rest_client.method == "GET"
        assert rest_client.endpoint == ""
        assert rest_client.timeout.total == RestClientBase.DEFAULT_TIMEOUT
        assert rest_client.headers == RestClientBase.DEFAULT_HEADERS

    @pytest.mark.asyncio
    async def test_update_headers(self, rest_client):
        rest_client.update_headers({"Authorization": "Bearer token"})
        rest_client.update_headers({"User-Agent": "new-user-agent"})
        assert "Authorization" in rest_client.headers
        assert rest_client.headers["Authorization"] == "Bearer token"
        assert rest_client.headers["User-Agent"] == "new-user-agent"

    @pytest.mark.asyncio
    async def test_custom_timeout(self, rest_client):
        assert rest_client.timeout.total == 60
        rest_client.update_timeout(120)
        assert rest_client.timeout.total == 120

    @pytest.mark.asyncio
    async def test_invalid_method(self):
        with pytest.raises(ValueError):
            RestClient(MOCK_URL, method="INVALID")

    @pytest.mark.asyncio
    async def test_update_request_method(self, rest_client):
        rest_client.method = "POST"
        assert rest_client.method == "POST"

    @pytest.mark.asyncio
    async def test_rest_client_headers_inheritance(self, rest_client):
        # Verify base headers are inherited
        assert isinstance(rest_client.headers, dict)
        assert "User-Agent" in rest_client.headers
        assert "Accept" in rest_client.headers
