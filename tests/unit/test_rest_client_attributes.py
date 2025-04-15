import pytest
from pydantic import ValidationError

from src.grpy.rest_client import RestClient

TEST_URL = "https://api.example.com"


@pytest.fixture
def rest_client():
    return RestClient(url=TEST_URL)


def test_endpoint_with_leading_slash(rest_client):
    rest_client.endpoint = "/test"
    assert rest_client.endpoint == "/test"


def test_endpoint_without_leading_slash(rest_client):
    rest_client.endpoint = "test"
    assert rest_client.endpoint == "test"


def test_invalid_method():
    with pytest.raises(ValidationError):
        RestClient(url=TEST_URL, method="INVALID")


def test_valid_methods():
    for method in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]:
        client = RestClient(url=TEST_URL, method=method)
        assert client.method == method


def test_default_headers():
    client = RestClient(url=TEST_URL)
    assert "Accept" in client.headers
    assert "Content-Type" in client.headers
    assert "User-Agent" in client.headers
    assert client.headers["Accept"] == "application/json"
    assert client.headers["Content-Type"] == "application/json"
    assert "grpy-rest-client" in client.headers["User-Agent"]


def test_custom_headers():
    custom_headers = {"X-Custom": "Test", "Authorization": "Bearer token"}
    client = RestClient(url=TEST_URL, headers=custom_headers)

    # Default headers should still be present
    assert "Accept" in client.headers
    assert "Content-Type" in client.headers

    # Custom headers should be added
    assert "X-Custom" in client.headers
    assert client.headers["X-Custom"] == "Test"
    assert client.headers["Authorization"] == "Bearer token"


def test_update_headers(rest_client):
    new_headers = {"X-New": "Value"}
    rest_client.update_headers(new_headers)
    assert rest_client.headers["X-New"] == "Value"


def test_update_params(rest_client):
    new_params = {"query": "test"}
    rest_client.update_params(new_params)
    assert rest_client.params["query"] == "test"


def test_invalid_timeout():
    with pytest.raises(ValidationError):
        RestClient(url=TEST_URL, timeout=-1)


def test_update_timeout(rest_client):
    new_timeout = 30
    rest_client.update_timeout(new_timeout)
    assert rest_client.timeout == new_timeout
    assert rest_client.timeout_obj.total == new_timeout
