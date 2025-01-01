from asyncio import TimeoutError
from typing import AsyncContextManager, Optional
from urllib.parse import urljoin

from aiohttp import ClientSession, ClientTimeout

from grpy.rest_client_base import RestClientBase


class RestClient(RestClientBase, AsyncContextManager["RestClient"]):
    """Async REST client for making HTTP requests."""

    def __init__(
        self,
        url: str,
        method: str = "GET",
        endpoint: str = "",
        timeout: Optional[float] = RestClientBase.DEFAULT_TIMEOUT,
        session: Optional[ClientSession] = None,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
    ):
        self._validate_http_method(method)
        self._validate_timeout(timeout)
        self.url = url
        self.method = method.upper()
        self.endpoint = endpoint
        self.headers = RestClientBase.DEFAULT_HEADERS.copy()
        if headers:
            self.headers.update(headers)
        self.session = session
        self.timeout = ClientTimeout(total=timeout)
        self.params = params or {}

    async def __aenter__(self):
        """Enter the context manager."""
        self.session = ClientSession(
            timeout=self.timeout, raise_for_status=True
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        await self.session.close()

    def handle_exception(method):
        async def wrapper(self, *args, **kwargs):
            try:
                return await method(self, *args, **kwargs)
            except TimeoutError as e:
                raise TimeoutError(f"Request timed out: {e}") from e
            except Exception as exc:
                raise exc from exc

        return wrapper

    @handle_exception
    async def handle_request(self, **kwargs):
        """Make a REST request with specified parameters."""
        request_url = (
            urljoin(self.url, self.endpoint) if self.endpoint else self.url
        )
        response = await self.session.request(
            method=self.method,
            url=request_url,
            headers=self.headers,
            params=self.params,
            timeout=self.timeout,
            **kwargs,
        )

        return response

    def update_headers(self, headers: dict):
        """Update headers for the request."""
        self.headers.update(headers)

    def update_params(self, params: dict):
        """Update request parameters.

        Args:
            params (dict): Dictionary of query parameters to update or add
        """
        self.params.update(params)

    def update_timeout(self, timeout: float):
        """Update the client timeout value.

        Args:
            timeout (float): New timeout value in seconds
        """
        self.timeout = ClientTimeout(total=timeout)
        if self.session:
            self.session._timeout = self.timeout
