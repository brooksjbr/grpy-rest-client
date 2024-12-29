import pytest

from grpy.async_rest_client import AsyncRestClient

MOCK_URL = "https://api.example.com"
MOCK_ENDPOINT = "/api/v1"
DEFAULT_TIMEOUT = 60
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "grpy-rest-client/1.0",
}


@pytest.fixture
async def rest_client():
    async with AsyncRestClient(MOCK_URL) as client:
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
        assert rest_client.timeout.total == DEFAULT_TIMEOUT
        assert rest_client.headers == {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "grpy-rest-client/1.0",
        }

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
            AsyncRestClient(MOCK_URL, method="INVALID")

    @pytest.mark.asyncio
    async def test_update_request_method(self, rest_client):
        rest_client.method = "POST"
        assert rest_client.method == "POST"
